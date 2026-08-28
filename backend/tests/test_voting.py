"""Core voting rules for APRAS-33 (service layer).

Covers the numbered backend tests of `docs/tasks/APRAS-33-spec.md`
§Testing: 1, 2, 4, 5, 6, 7, 8, 9, 10, 18, 20 plus the snapshot/closing
complements.
"""

import json
from datetime import datetime, timedelta

import pytest
from app.core.exceptions import (
    DelinquentLotError,
    NotLotOwnerError,
    VoteNotOpenError,
)
from app.models.enums import (
    AssemblyStatus,
    BallotRejectionReason,
    LotAssociationType,
    UserRole,
    VoteKind,
    VoteStatus,
    VoteType,
)
from app.models.voting import Ballot, BallotRejection
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


# ---------------------------------------------------------------------------
# 1 / 2 — one ballot per lot, an owner of two lots votes twice
# ---------------------------------------------------------------------------


def test_owner_of_two_lots_votes_on_both_and_tally_counts_two(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot_a = make_lot(session, "A", "1")
    lot_b = make_lot(session, "A", "2")
    link_user_to_lot(session, owner, lot_a)
    link_user_to_lot(session, owner, lot_b)

    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, owner, vote, "Sim", lot_a)
    _cast(session, owner, vote, "Não", lot_b)

    tally = voting_service.compute_tally(session, vote)
    assert tally["voters_count"] == 2
    counts = {r["label"]: r["count"] for r in tally["results"]}
    assert counts == {"Sim": 1, "Não": 1}


def test_eligible_by_extra_registration_on_second_lot_votes_on_both(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    voter = make_user(session, UserRole.RESIDENT)
    lot_a = make_lot(session, "A", "1")
    lot_b = make_lot(session, "B", "9")
    link_user_to_lot(session, voter, lot_a)
    add_extra_eligibility(session, voter, lot_b, added_by=board)

    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, voter, vote, "Sim", lot_a)
    _cast(session, voter, vote, "Sim", lot_b)

    tally = voting_service.compute_tally(session, vote)
    assert tally["voters_count"] == 2
    assert {r["label"]: r["count"] for r in tally["results"]}["Sim"] == 2


# ---------------------------------------------------------------------------
# 2 (spec list) — changing a vote appends a row, tally counts the latest
# ---------------------------------------------------------------------------


def test_holder_changes_choice_appends_row_and_tally_uses_latest(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, owner, vote, "Sim", lot)
    _cast(session, owner, vote, "Não", lot)

    rows = session.exec(select(Ballot).where(Ballot.vote_id == vote.id)).all()
    assert len(rows) == 2, "ballots are append-only; changing a vote inserts a row"

    tally = voting_service.compute_tally(session, vote)
    assert tally["voters_count"] == 1
    assert {r["label"]: r["count"] for r in tally["results"]} == {"Sim": 0, "Não": 1}


# ---------------------------------------------------------------------------
# 3 — tenants are refused in an assembly and accepted in a poll
# ---------------------------------------------------------------------------


def test_tenant_refused_in_assembly_and_accepted_in_poll(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    tenant = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, tenant, lot, LotAssociationType.INQUILINO)

    assembly = make_assembly(session, board)
    assembly_vote = make_vote(session, board, assembly=assembly)

    with pytest.raises(NotLotOwnerError):
        _cast(session, tenant, assembly_vote, "Sim", lot)

    rejection = session.exec(select(BallotRejection)).one()
    assert rejection.reason == BallotRejectionReason.NOT_OWNER
    assert rejection.user_id == tenant.id
    assert rejection.lot_id == lot.id

    poll = make_vote(session, board, kind=VoteKind.ENQUETE, assembly=None)
    ballot = _cast(session, tenant, poll, "Sim")
    assert ballot.voter_key == f"user:{tenant.id}"
    assert ballot.lot_id is None


# ---------------------------------------------------------------------------
# 4 / 5 / 6 — delinquency is checked at cast time
# ---------------------------------------------------------------------------


def test_delinquent_lot_is_refused_and_logs_rejection(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1", is_delinquent=True)
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    with pytest.raises(DelinquentLotError):
        _cast(session, owner, vote, "Sim", lot)

    rejection = session.exec(select(BallotRejection)).one()
    assert rejection.reason == BallotRejectionReason.DELINQUENT_LOT
    assert rejection.lot_id == lot.id


def test_becoming_delinquent_blocks_change_but_keeps_original_ballot(
    session: Session,
):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, owner, vote, "Sim", lot)

    lot.is_delinquent = True
    session.add(lot)
    session.commit()

    with pytest.raises(DelinquentLotError):
        _cast(session, owner, vote, "Não", lot)

    tally = voting_service.compute_tally(session, vote)
    assert tally["voters_count"] == 1
    assert {r["label"]: r["count"] for r in tally["results"]} == {"Sim": 1, "Não": 0}


def test_lot_that_settles_debt_during_window_can_vote(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1", is_delinquent=True)
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    with pytest.raises(DelinquentLotError):
        _cast(session, owner, vote, "Sim", lot)

    lot.is_delinquent = False
    session.add(lot)
    session.commit()

    ballot = _cast(session, owner, vote, "Sim", lot)
    assert ballot.voter_key == f"lot:{lot.id}"
    assert voting_service.compute_tally(session, vote)["voters_count"] == 1


# ---------------------------------------------------------------------------
# 8 / 9 — snapshot materialisation and frozen fraction
# ---------------------------------------------------------------------------


def test_closing_materialises_snapshot_and_reads_come_from_it(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot)

    voting_service.close_vote(session, board, vote)
    assert vote.status == VoteStatus.CLOSED
    assert vote.closed_at is not None
    snapshot = json.loads(vote.tally_snapshot_json)
    assert snapshot["voters_count"] == 1

    # A later ballot row inserted straight into the DB must NOT change the
    # already materialised tally: reads come from the snapshot.
    session.add(
        Ballot(
            vote_id=vote.id,
            voter_key="lot:sneaky",
            selected_option_ids_json=json.dumps([str(option_id(vote, "Não"))]),
        )
    )
    session.commit()

    tally = voting_service.get_tally(session, board, vote)
    assert tally.voters_count == 1


def test_fraction_ideal_is_frozen_at_cast_time(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1", fraction_ideal=0.25)
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    ballot = _cast(session, owner, vote, "Sim", lot)
    assert ballot.fraction_ideal_at_cast == 0.25

    lot.fraction_ideal = 0.5
    session.add(lot)
    session.commit()
    session.refresh(ballot)

    assert ballot.fraction_ideal_at_cast == 0.25


def test_lazy_materialisation_closes_vote_after_closes_at(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot)

    vote.closes_at = datetime.utcnow() - timedelta(minutes=1)
    session.add(vote)
    session.commit()

    tally = voting_service.get_tally(session, board, vote)
    assert vote.status == VoteStatus.CLOSED
    assert vote.tally_snapshot_json is not None
    assert tally.results is not None


# ---------------------------------------------------------------------------
# 7 / 10 / 18 — closed-window gate, anonymity masking, poll has no denominator
# ---------------------------------------------------------------------------


def test_open_vote_tally_hides_results_even_for_administrator(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    make_lot(session, "A", "2")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot)

    tally = voting_service.get_tally(session, board, vote)
    assert tally.voters_count == 1
    assert tally.results is None
    assert tally.attributions is None
    assert tally.total_lots == 2


def test_open_poll_tally_has_no_denominator(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot, LotAssociationType.INQUILINO)
    poll = make_vote(session, board, kind=VoteKind.ENQUETE)
    _cast(session, resident, poll, "Sim")

    tally = voting_service.get_tally(session, board, poll)
    assert tally.voters_count == 1
    assert tally.total_lots is None
    assert tally.results is None


def test_closed_poll_tally_has_results_but_still_no_denominator(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot)
    poll = make_vote(session, board, kind=VoteKind.ENQUETE)
    _cast(session, resident, poll, "Sim")
    voting_service.close_vote(session, board, poll)

    tally = voting_service.get_tally(session, board, poll)
    assert tally.results is not None
    assert tally.voters_count == 1
    assert tally.total_lots is None


def test_closed_anonymous_poll_never_exposes_voter_identity(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot)
    poll = make_vote(session, board, kind=VoteKind.ENQUETE, is_anonymous=True)
    _cast(session, resident, poll, "Sim")
    voting_service.close_vote(session, board, poll)

    tally = voting_service.get_tally(session, board, poll)
    assert tally.attributions is None
    payload = tally.model_dump_json()
    assert str(resident.id) not in payload
    assert str(lot.id) not in payload
    assert str(resident.id) not in (poll.tally_snapshot_json or "")


def test_closed_assembly_tally_attributes_by_block_and_lot(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT, full_name="Fulano de Tal")
    lot = make_lot(session, "B", "12")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot)
    voting_service.close_vote(session, board, vote)

    tally = voting_service.get_tally(session, board, vote)
    assert tally.attributions is not None
    entry = tally.attributions[0]
    assert entry.lot_label == "B/12"
    assert entry.selected_labels == ["Sim"]
    payload = tally.model_dump_json()
    assert "Fulano de Tal" not in payload, "assembly attributes by unit, not by person"


# ---------------------------------------------------------------------------
# 20 — retraction is per lot for a multi-lot voter
# ---------------------------------------------------------------------------


def test_retracting_one_lot_leaves_the_other_ballot_active(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot_a = make_lot(session, "A", "1")
    lot_b = make_lot(session, "A", "2")
    link_user_to_lot(session, owner, lot_a)
    link_user_to_lot(session, owner, lot_b)
    assembly = make_assembly(session, board)
    vote = make_vote(session, board, assembly=assembly)

    _cast(session, owner, vote, "Sim", lot_a)
    _cast(session, owner, vote, "Sim", lot_b)

    voting_service.cast_ballot(
        session, owner, vote, lot_id=lot_a.id, is_retraction=True
    )

    tally = voting_service.compute_tally(session, vote)
    assert tally["voters_count"] == 1
    assert voting_service.get_active_ballot_holder(session, vote, lot_a.id) is None
    assert voting_service.get_active_ballot_holder(session, vote, lot_b.id) == owner.id


# ---------------------------------------------------------------------------
# Assembly status semantics
# ---------------------------------------------------------------------------


def test_vote_in_draft_assembly_refuses_ballots(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board, status=AssemblyStatus.DRAFT)
    vote = make_vote(session, board, assembly=assembly)

    with pytest.raises(VoteNotOpenError):
        _cast(session, owner, vote, "Sim", lot)

    rejection = session.exec(select(BallotRejection)).one()
    assert rejection.reason == BallotRejectionReason.VOTE_NOT_OPEN


def test_closing_assembly_cascades_and_materialises_each_vote(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote_a = make_vote(session, board, assembly=assembly, title="Pauta 1")
    vote_b = make_vote(session, board, assembly=assembly, title="Pauta 2")
    _cast(session, owner, vote_a, "Sim", lot)

    voting_service.close_assembly(session, board, assembly)

    session.refresh(vote_a)
    session.refresh(vote_b)
    assert assembly.status == AssemblyStatus.CLOSED
    assert assembly.closed_at is not None
    assert vote_a.status == VoteStatus.CLOSED
    assert vote_b.status == VoteStatus.CLOSED
    assert vote_a.tally_snapshot_json is not None
    assert vote_b.tally_snapshot_json is not None


def test_multiple_choice_counts_every_selected_option(session: Session):
    board = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, board)
    vote = make_vote(
        session,
        board,
        assembly=assembly,
        vote_type=VoteType.MULTIPLE_CHOICE,
        option_labels=("Obra A", "Obra B", "Obra C"),
    )

    voting_service.cast_ballot(
        session,
        owner,
        vote,
        lot_id=lot.id,
        selected_option_ids=[
            option_id(vote, "Obra A"),
            option_id(vote, "Obra C"),
        ],
    )

    tally = voting_service.compute_tally(session, vote)
    counts = {r["label"]: r["count"] for r in tally["results"]}
    assert counts == {"Obra A": 1, "Obra B": 0, "Obra C": 1}
    assert tally["voters_count"] == 1
