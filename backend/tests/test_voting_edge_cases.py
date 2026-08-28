"""Edge cases and guard paths of the voting module (APRAS-33)."""

import uuid
from datetime import datetime, timedelta

import pytest
from app.core.exceptions import (
    AnonymousAssemblyError,
    ForbiddenError,
    LotNotFoundError,
    NoActiveBallotError,
    NoActiveLotLinkError,
    NotLotOwnerError,
    TallyNotAvailableError,
    VoteAlreadyClosedError,
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
from app.models.voting import BallotRejection
from app.schemas.voting import VoteCreate, VoteOptionCreate, VoteUpdate
from app.services import voting_service
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from tests.voting_helpers import (
    auth_headers,
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
# Guards
# ---------------------------------------------------------------------------


def test_resident_cannot_create_a_poll(session: Session):
    resident = make_user(session, UserRole.RESIDENT)
    vote_in = VoteCreate(
        kind=VoteKind.ENQUETE,
        title="Enquete proibida",
        vote_type=VoteType.SINGLE_CHOICE,
        closes_at=datetime.utcnow() + timedelta(days=1),
        options=[VoteOptionCreate(label="Sim"), VoteOptionCreate(label="Não")],
    )
    with pytest.raises(ForbiddenError):
        voting_service.create_vote(session, resident, vote_in)


def test_resident_without_lot_cannot_read_either_tally(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    stranger = make_user(session, UserRole.RESIDENT)
    assembly = make_assembly(session, admin)
    assembly_vote = make_vote(session, admin, assembly=assembly)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)

    with pytest.raises(TallyNotAvailableError):
        voting_service.get_tally(session, stranger, assembly_vote)
    with pytest.raises(TallyNotAvailableError):
        voting_service.get_tally(session, stranger, poll)


def test_resident_with_lot_can_read_the_tally(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)

    assert voting_service.get_tally(session, owner, vote).voters_count == 0
    assert voting_service.get_tally(session, owner, poll).voters_count == 0


def test_a_link_that_has_not_started_yet_does_not_grant_eligibility(
    session: Session,
):
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link = link_user_to_lot(session, owner, lot)
    link.start_date = datetime.utcnow() + timedelta(days=5)
    session.add(link)
    session.commit()

    assert voting_service.get_lot_eligible_user_ids(session, lot) == set()
    assert voting_service.get_user_eligible_lot_ids(session, owner) == set()


def test_expired_link_does_not_grant_eligibility(session: Session):
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(
        session, owner, lot, end_date=datetime.utcnow() - timedelta(days=1)
    )

    assert voting_service.get_lot_eligible_user_ids(session, lot) == set()


def test_deleted_lot_is_not_eligible(session: Session):
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    lot.is_deleted = True
    session.add(lot)
    session.commit()

    assert voting_service.get_user_eligible_lot_ids(session, owner) == set()


def test_poll_my_ballot_for_a_user_without_any_lot(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    stranger = make_user(session, UserRole.RESIDENT)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)

    assert voting_service.get_my_ballots(session, stranger, poll) == []


def test_guest_ballot_attempt_is_logged_as_role_forbidden(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    guest = make_user(session, UserRole.GUEST)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, guest, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)

    with pytest.raises(ForbiddenError):
        _cast(session, guest, vote, "Sim", lot)

    rejection = session.exec(select(BallotRejection)).one()
    assert rejection.reason == BallotRejectionReason.ROLE_FORBIDDEN


def test_assembly_ballot_without_lot_or_with_unknown_lot(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)

    with pytest.raises(NotLotOwnerError):
        _cast(session, owner, vote, "Sim", None)
    with pytest.raises(LotNotFoundError):
        voting_service.cast_ballot(
            session,
            owner,
            vote,
            lot_id=uuid.uuid4(),
            selected_option_ids=[option_id(vote, "Sim")],
        )


def test_assembly_retraction_without_lot_id(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot)

    with pytest.raises(NoActiveBallotError):
        voting_service.cast_ballot(session, owner, vote, is_retraction=True)


def test_poll_ballot_without_any_active_lot_link_is_logged(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    stranger = make_user(session, UserRole.RESIDENT)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)

    with pytest.raises(NoActiveLotLinkError):
        _cast(session, stranger, poll, "Sim")

    rejection = session.exec(select(BallotRejection)).one()
    assert rejection.reason == BallotRejectionReason.NO_ACTIVE_LOT_LINK


def test_cast_at_is_forced_to_increase_per_voter_key(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)

    first = _cast(session, owner, vote, "Sim", lot)
    # Simulate a clock that has not moved (or went backwards) since.
    first.cast_at = datetime.utcnow() + timedelta(hours=1)
    session.add(first)
    session.commit()

    second = _cast(session, owner, vote, "Não", lot)
    assert second.cast_at > first.cast_at
    assert voting_service.get_active_ballot_holder(session, vote, lot.id) == owner.id
    tally = voting_service.compute_tally(session, vote)
    assert {r["label"]: r["count"] for r in tally["results"]} == {"Sim": 0, "Não": 1}


def test_tally_of_a_closed_vote_without_snapshot_is_materialised(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly, status=VoteStatus.CLOSED)

    tally = voting_service.get_tally(session, admin, vote)
    assert vote.tally_snapshot_json is not None
    assert tally.results is not None


# ---------------------------------------------------------------------------
# Assembly and vote lifecycle
# ---------------------------------------------------------------------------


def test_assembly_and_vote_not_found_return_404(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    headers = auth_headers(client, admin)
    missing = uuid.uuid4()

    assert client.get(f"/api/v1/assemblies/{missing}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/votes/{missing}", headers=headers).status_code == 404


def test_assembly_listing_and_release_of_the_agenda(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    make_assembly(session, admin, status=AssemblyStatus.DRAFT, title="AGE 2026")
    headers = auth_headers(client, admin)

    listed = client.get("/api/v1/assemblies/", headers=headers)
    assert listed.status_code == 200
    assembly_id = listed.json()[0]["id"]

    released = client.patch(
        f"/api/v1/assemblies/{assembly_id}",
        headers=headers,
        json={"status": "OPEN", "agenda": "1. Obras"},
    )
    assert released.status_code == 200
    assert released.json()["status"] == "OPEN"
    assert released.json()["agenda"] == "1. Obras"


def test_closing_an_already_closed_assembly_returns_400(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin, status=AssemblyStatus.CLOSED)

    response = client.post(
        f"/api/v1/assemblies/{assembly.id}/close", headers=auth_headers(client, admin)
    )
    assert response.status_code == 400


def test_vote_listing_filters_by_kind_and_status(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    make_vote(session, admin, assembly=assembly)
    make_vote(session, admin, kind=VoteKind.ENQUETE, status=VoteStatus.CLOSED)
    headers = auth_headers(client, admin)

    polls = client.get("/api/v1/votes/?kind=ENQUETE", headers=headers)
    assert [item["kind"] for item in polls.json()] == ["ENQUETE"]

    closed = client.get("/api/v1/votes/?status=CLOSED", headers=headers)
    assert [item["status"] for item in closed.json()] == ["CLOSED"]


def test_updating_a_vote_replaces_its_options(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)

    updated = voting_service.update_vote(
        session,
        admin,
        vote,
        VoteUpdate(
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=[{"label": "Obra A"}, {"label": "Obra B"}],
        ),
    )

    assert updated.vote_type == VoteType.MULTIPLE_CHOICE
    assert sorted(opt.label for opt in updated.options) == ["Obra A", "Obra B"]


def test_updating_a_closed_vote_or_making_an_assembly_anonymous_fails(
    session: Session,
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)

    with pytest.raises(AnonymousAssemblyError):
        voting_service.update_vote(
            session, admin, vote, VoteUpdate(is_anonymous=True)
        )

    voting_service.close_vote(session, admin, vote)
    with pytest.raises(VoteAlreadyClosedError):
        voting_service.update_vote(session, admin, vote, VoteUpdate(title="X"))
    with pytest.raises(VoteAlreadyClosedError):
        voting_service.close_vote(session, admin, vote)


# ---------------------------------------------------------------------------
# Eligibility management errors
# ---------------------------------------------------------------------------


def test_eligibility_management_rejects_unknown_lot_or_user(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    spouse = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")

    with pytest.raises(LotNotFoundError):
        voting_service.set_lot_voter_eligibility(
            session, admin, uuid.uuid4(), spouse.id
        )
    with pytest.raises(ForbiddenError):
        voting_service.set_lot_voter_eligibility(
            session, admin, lot.id, uuid.uuid4()
        )
    with pytest.raises(LotNotFoundError):
        voting_service.remove_lot_voter_eligibility(
            session, admin, lot.id, spouse.id
        )


def test_minutes_of_an_assembly_without_votes(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin, status=AssemblyStatus.CLOSED)

    assert voting_service.get_delinquency_barred_lots(session, assembly) == []
    minutes = voting_service.render_minutes_html(session, assembly)
    assert "Assembleia Geral Ordinária (AGO)" in minutes


def test_poll_tally_attributes_by_voter_name(session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT, full_name="Beltrano")
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot, LotAssociationType.INQUILINO)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)
    _cast(session, resident, poll, "Sim")
    voting_service.close_vote(session, admin, poll)

    tally = voting_service.get_tally(session, admin, poll)
    assert tally.attributions[0].voter_name == "Beltrano"
    assert tally.attributions[0].voter_user_id == resident.id
    assert tally.attributions[0].lot_label is None


def test_guest_cannot_browse_the_voting_surface(
    client: TestClient, session: Session
):
    guest = make_user(session, UserRole.GUEST)
    headers = auth_headers(client, guest)

    assert client.get("/api/v1/votes/", headers=headers).status_code == 403
    assert client.get("/api/v1/assemblies/", headers=headers).status_code == 403


def test_eligible_lots_endpoint_lists_the_units_the_caller_may_vote_for(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot_b = make_lot(session, "B", "2")
    lot_a = make_lot(session, "A", "1")
    make_lot(session, "C", "3")
    link_user_to_lot(session, owner, lot_a)
    link_user_to_lot(session, owner, lot_b)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)
    headers = auth_headers(client, owner)

    listed = client.get(f"/api/v1/votes/{vote.id}/eligible-lots", headers=headers)
    assert listed.status_code == 200
    assert [item["label"] for item in listed.json()] == ["A/1", "B/2"]

    poll_lots = client.get(
        f"/api/v1/votes/{poll.id}/eligible-lots", headers=headers
    )
    assert poll_lots.json() == []


# ---------------------------------------------------------------------------
# Regressions
# ---------------------------------------------------------------------------


def test_patch_assembly_cannot_close_it_and_unlock_the_minutes(
    client: TestClient, session: Session
):
    """`PATCH {"status": "CLOSED"}` must not be a back door to the tally.

    Regression: the closed-window gate (Visibilidade, Regra 1) has no
    carve-out for the board, yet `PATCH /assemblies/{id}` accepted
    `status = CLOSED`, which made `GET /{id}/minutes` render the per-option
    result and the per-unit attribution of a vote that was still OPEN —
    and left `closed_at` NULL with no frozen snapshot.
    """
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot=lot)
    headers = auth_headers(client, admin)

    patched = client.patch(
        f"/api/v1/assemblies/{assembly.id}",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert patched.status_code == 400

    session.refresh(assembly)
    assert assembly.status == AssemblyStatus.OPEN
    assert assembly.closed_at is None

    minutes = client.get(f"/api/v1/assemblies/{assembly.id}/minutes", headers=headers)
    assert minutes.status_code == 400

    tally = client.get(f"/api/v1/votes/{vote.id}/tally", headers=headers)
    assert tally.status_code == 200
    assert "results" not in tally.json()
    assert "attributions" not in tally.json()


def test_patch_assembly_still_opens_a_draft(client: TestClient, session: Session):
    """Only CLOSED is refused — DRAFT → OPEN stays a normal PATCH."""
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin, status=AssemblyStatus.DRAFT)

    response = client.patch(
        f"/api/v1/assemblies/{assembly.id}",
        headers=auth_headers(client, admin),
        json={"status": "OPEN", "title": "AGE 2026"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "OPEN"
    assert response.json()["title"] == "AGE 2026"


def test_minutes_always_read_the_frozen_snapshot(session: Session):
    """A vote reaching the minutes without a snapshot is frozen, not recomputed."""
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot=lot)

    # Assembly forced closed without going through `close_assembly`.
    assembly.status = AssemblyStatus.CLOSED
    session.add(assembly)
    session.commit()

    voting_service.render_minutes_html(session, assembly)

    session.refresh(vote)
    assert vote.tally_snapshot_json is not None
    assert vote.status == VoteStatus.CLOSED


def test_repeated_option_in_one_ballot_does_not_inflate_the_count(
    client: TestClient, session: Session
):
    """One ballot is one vote per option, however often the id is repeated.

    Regression: a MULTIPLE_CHOICE ballot listing the same option five times
    was accepted and counted five times, breaking "um voto por lote" in the
    published result and in the minutes.
    """
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(
        session,
        admin,
        assembly=assembly,
        vote_type=VoteType.MULTIPLE_CHOICE,
        option_labels=("Sim", "Não"),
    )
    sim = str(option_id(vote, "Sim"))

    response = client.post(
        f"/api/v1/votes/{vote.id}/ballots",
        headers=auth_headers(client, owner),
        json={"lot_id": str(lot.id), "selected_option_ids": [sim] * 5},
    )

    assert response.status_code == 422

    tally = voting_service.compute_tally(session, vote)
    assert tally["voters_count"] == 0


def test_stored_duplicate_selections_are_counted_once_on_recount(session: Session):
    """Rows already carrying duplicates cannot skew a recount either."""
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(
        session,
        admin,
        assembly=assembly,
        vote_type=VoteType.MULTIPLE_CHOICE,
        option_labels=("Sim", "Não"),
    )
    sim = option_id(vote, "Sim")
    nao = option_id(vote, "Não")
    ballot = voting_service.cast_ballot(
        session,
        owner,
        vote,
        lot_id=lot.id,
        selected_option_ids=[sim, sim, nao, sim],
    )

    tally = voting_service.compute_tally(session, vote)

    assert tally["voters_count"] == 1
    assert {row["label"]: row["count"] for row in tally["results"]} == {
        "Sim": 1,
        "Não": 1,
    }
    assert tally["attributions"][0]["selected_labels"] == ["Sim", "Não"]
    assert voting_service.selected_option_ids(ballot) == [sim, nao]
