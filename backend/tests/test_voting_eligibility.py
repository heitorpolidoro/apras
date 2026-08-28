"""Per-lot ballot ownership, retraction and shared visibility (APRAS-33).

Covers the numbered backend tests of `docs/tasks/APRAS-33-spec.md`
§Testing: 13, 14, 15, 15b, 16 and 19.
"""

import pytest
from app.core.exceptions import (
    LotAlreadyVotedError,
    NoActiveBallotError,
    NotLotOwnerError,
    VoteNotOpenError,
)
from app.models.enums import (
    BallotRejectionReason,
    LotAssociationType,
    UserRole,
    VoteKind,
    VoteStatus,
)
from app.models.lot import UserLotLink
from app.models.voting import BallotRejection, LotVoterEligibility
from app.services import voting_service
from sqlmodel import Session, select
from tests.voting_helpers import (
    add_extra_eligibility,
    link_user_to_lot,
    make_assembly,
    make_lot,
    make_user,
    make_vote,
    option_id,
)


def _cast(session, user, vote, label, lot=None):
    return voting_service.cast_ballot(
        session,
        user,
        vote,
        lot_id=lot.id if lot else None,
        selected_option_ids=[option_id(vote, label)],
    )


def _retract(session, user, vote, lot=None):
    return voting_service.cast_ballot(
        session, user, vote, lot_id=lot.id if lot else None, is_retraction=True
    )


# ---------------------------------------------------------------------------
# 13 — co-ownership: two PROPRIETARIO links, one active ballot
# ---------------------------------------------------------------------------


def test_second_co_owner_is_blocked_once_the_first_has_voted(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner_a = make_user(session, UserRole.RESIDENT, full_name="Owner A")
    owner_b = make_user(session, UserRole.RESIDENT, full_name="Owner B")
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner_a, lot)
    link_user_to_lot(session, owner_b, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, owner_b, vote, "Sim", lot)
    assert voting_service.get_active_ballot_holder(session, vote, lot.id) == owner_b.id

    with pytest.raises(LotAlreadyVotedError):
        _cast(session, owner_a, vote, "Não", lot)

    rejection = session.exec(select(BallotRejection)).one()
    assert rejection.reason == BallotRejectionReason.LOT_ALREADY_VOTED
    assert rejection.user_id == owner_a.id
    assert voting_service.compute_tally(session, vote)["voters_count"] == 1


# ---------------------------------------------------------------------------
# 14 — manually registered extra voter
# ---------------------------------------------------------------------------


def test_extra_eligible_can_vote_and_loses_the_right_when_removed(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    spouse = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    eligibility = add_extra_eligibility(session, spouse, lot, added_by=board)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, spouse, vote, "Sim", lot)
    assert voting_service.compute_tally(session, vote)["voters_count"] == 1

    session.delete(eligibility)
    session.commit()

    # The already-cast ballot stays in the tally...
    assert voting_service.compute_tally(session, vote)["voters_count"] == 1
    # ...but a new attempt is refused.
    with pytest.raises(NotLotOwnerError):
        _cast(session, spouse, vote, "Não", lot)
    assert (
        session.exec(select(BallotRejection)).one().reason
        == BallotRejectionReason.NOT_OWNER
    )


# ---------------------------------------------------------------------------
# 15 — retraction frees the lot
# ---------------------------------------------------------------------------


def test_retraction_frees_the_lot_for_another_eligible_voter(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    voter_a = make_user(session, UserRole.RESIDENT, full_name="A")
    voter_b = make_user(session, UserRole.RESIDENT, full_name="B")
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, voter_a, lot)
    link_user_to_lot(session, voter_b, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, voter_a, vote, "Sim", lot)
    _retract(session, voter_a, vote, lot)

    assert voting_service.get_active_ballot_holder(session, vote, lot.id) is None
    assert voting_service.compute_tally(session, vote)["voters_count"] == 0

    # A already retracted: nothing left to change or retract.
    with pytest.raises(NoActiveBallotError):
        _retract(session, voter_a, vote, lot)

    _cast(session, voter_b, vote, "Não", lot)
    assert voting_service.get_active_ballot_holder(session, vote, lot.id) == voter_b.id

    # Now B holds it, so A is locked out again.
    with pytest.raises(LotAlreadyVotedError):
        _cast(session, voter_a, vote, "Sim", lot)
    with pytest.raises(LotAlreadyVotedError):
        _retract(session, voter_a, vote, lot)

    tally = voting_service.compute_tally(session, vote)
    assert tally["voters_count"] == 1
    assert {r["label"]: r["count"] for r in tally["results"]} == {"Sim": 0, "Não": 1}


# ---------------------------------------------------------------------------
# 15b — retraction does not re-evaluate eligibility (otherwise the lot locks)
# ---------------------------------------------------------------------------


def test_holder_who_lost_eligibility_can_still_retract_and_unlock_the_lot(
    session: Session,
):
    board = make_user(session, UserRole.ADMINISTRATOR)
    voter_a = make_user(session, UserRole.RESIDENT, full_name="A")
    voter_b = make_user(session, UserRole.RESIDENT, full_name="B")
    lot = make_lot(session, "A", "1")
    link_a = link_user_to_lot(session, voter_a, lot)
    link_user_to_lot(session, voter_b, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, voter_a, vote, "Sim", lot)

    # A stops being an owner after voting.
    session.delete(link_a)
    session.commit()
    assert voter_a.id not in voting_service.get_lot_eligible_user_ids(session, lot)
    # The already-cast ballot survives the loss of eligibility.
    assert voting_service.compute_tally(session, vote)["voters_count"] == 1

    _retract(session, voter_a, vote, lot)
    assert voting_service.compute_tally(session, vote)["voters_count"] == 0

    _cast(session, voter_b, vote, "Não", lot)
    assert voting_service.get_active_ballot_holder(session, vote, lot.id) == voter_b.id


def test_window_check_wins_over_missing_active_ballot(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly, status=VoteStatus.CLOSED)

    with pytest.raises(VoteNotOpenError):
        _retract(session, owner, vote, lot)


# ---------------------------------------------------------------------------
# 16 — GET /my-ballot visibility
# ---------------------------------------------------------------------------


def test_assembly_my_ballot_is_visible_to_every_eligible_of_the_lot(
    session: Session,
):
    board = make_user(session, UserRole.ADMINISTRATOR)
    voter_a = make_user(session, UserRole.RESIDENT, full_name="A")
    voter_b = make_user(session, UserRole.RESIDENT, full_name="B")
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, voter_a, lot)
    link_user_to_lot(session, voter_b, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, voter_a, vote, "Sim", lot)

    holder_view = voting_service.get_my_ballots(session, voter_a, vote)
    assert len(holder_view) == 1
    assert holder_view[0].can_edit is True

    peer_view = voting_service.get_my_ballots(session, voter_b, vote)
    assert len(peer_view) == 1
    assert peer_view[0].can_edit is False
    assert peer_view[0].voter_name == "A"
    assert peer_view[0].lot_label == "A/1"


def test_poll_my_ballot_shows_neighbours_when_not_anonymous(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    resident_a = make_user(session, UserRole.RESIDENT, full_name="A")
    resident_b = make_user(session, UserRole.RESIDENT, full_name="B")
    outsider = make_user(session, UserRole.RESIDENT, full_name="C")
    lot = make_lot(session, "A", "1")
    other_lot = make_lot(session, "A", "2")
    link_user_to_lot(session, resident_a, lot)
    link_user_to_lot(session, resident_b, lot, LotAssociationType.INQUILINO)
    link_user_to_lot(session, outsider, other_lot)

    poll = make_vote(session, board, kind=VoteKind.ENQUETE)
    _cast(session, resident_a, poll, "Sim")
    _cast(session, resident_b, poll, "Não")
    _cast(session, outsider, poll, "Sim")

    view = voting_service.get_my_ballots(session, resident_a, poll)
    assert len(view) == 2
    by_name = {item.voter_name: item for item in view}
    assert set(by_name) == {"A", "B"}
    assert by_name["A"].can_edit is True
    assert by_name["B"].can_edit is False


def test_anonymous_poll_my_ballot_shows_only_own_masked_entry(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    resident_a = make_user(session, UserRole.RESIDENT, full_name="A")
    resident_b = make_user(session, UserRole.RESIDENT, full_name="B")
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident_a, lot)
    link_user_to_lot(session, resident_b, lot)

    poll = make_vote(session, board, kind=VoteKind.ENQUETE, is_anonymous=True)
    _cast(session, resident_a, poll, "Sim")
    _cast(session, resident_b, poll, "Não")

    view = voting_service.get_my_ballots(session, resident_a, poll)
    assert len(view) == 1
    item = view[0]
    assert item.can_edit is True
    assert item.voter_user_id is None
    assert item.voter_name is None
    assert item.lot_id is None
    assert item.selected_option_ids == [option_id(poll, "Sim")]


# ---------------------------------------------------------------------------
# 19 — poll retraction
# ---------------------------------------------------------------------------


def test_poll_retraction_removes_the_vote_and_is_not_repeatable(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot, LotAssociationType.INQUILINO)
    poll = make_vote(session, board, kind=VoteKind.ENQUETE)

    _cast(session, resident, poll, "Sim")
    assert voting_service.compute_tally(session, poll)["voters_count"] == 1

    _retract(session, resident, poll)
    assert voting_service.compute_tally(session, poll)["voters_count"] == 0

    with pytest.raises(NoActiveBallotError):
        _retract(session, resident, poll)


def test_poll_retraction_does_not_require_a_still_active_lot_link(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    tenant = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link = link_user_to_lot(session, tenant, lot, LotAssociationType.INQUILINO)
    poll = make_vote(session, board, kind=VoteKind.ENQUETE)

    _cast(session, tenant, poll, "Sim")

    # The tenant moves out: the lot link is gone.
    session.delete(link)
    session.commit()
    assert session.exec(select(UserLotLink)).all() == []

    _retract(session, tenant, poll)
    assert voting_service.compute_tally(session, poll)["voters_count"] == 0


def test_removing_extra_eligibility_deletes_the_row(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    manager = make_user(session, UserRole.MANAGER)
    spouse = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")

    created = voting_service.set_lot_voter_eligibility(
        session, manager, lot.id, spouse.id
    )
    assert created.added_by_id == manager.id
    # Idempotent
    again = voting_service.set_lot_voter_eligibility(
        session, manager, lot.id, spouse.id
    )
    assert again.id == created.id

    voting_service.remove_lot_voter_eligibility(session, board, lot.id, spouse.id)
    assert session.exec(select(LotVoterEligibility)).all() == []
