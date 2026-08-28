"""HTTP surface and RBAC for the voting endpoints (APRAS-33).

Covers the numbered backend tests of `docs/tasks/APRAS-33-spec.md`
§Testing: 7, 10, 11, 17, 18, 19 and the "Complementares" paragraph.
"""

from datetime import datetime, timedelta

from app.models.enums import (
    AssemblyStatus,
    LotAssociationType,
    UserRole,
    VoteKind,
    VoteStatus,
    VoteType,
)
from app.services import voting_service
from fastapi.testclient import TestClient
from sqlmodel import Session
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
# Assembly + vote CRUD
# ---------------------------------------------------------------------------


def test_board_creates_assembly_with_agenda_votes(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    headers = auth_headers(client, admin)

    response = client.post(
        "/api/v1/assemblies/",
        headers=headers,
        json={"title": "AGO 2026", "type": "AGO", "held_on": "2026-03-01"},
    )
    assert response.status_code == 201
    assembly_id = response.json()["id"]
    assert response.json()["status"] == "DRAFT"

    for title in ("Orçamento", "Obra do playground"):
        created = client.post(
            "/api/v1/votes/",
            headers=headers,
            json={
                "assembly_id": assembly_id,
                "kind": "ASSEMBLEIA",
                "title": title,
                "vote_type": "SINGLE_CHOICE",
                "closes_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                "options": [{"label": "Sim"}, {"label": "Não"}],
            },
        )
        assert created.status_code == 201, created.text
        assert len(created.json()["options"]) == 2

    listed = client.get(
        f"/api/v1/votes/?assembly_id={assembly_id}", headers=headers
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 2


def test_manager_may_create_poll_but_not_assembly_vote(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    manager = make_user(session, UserRole.MANAGER)
    assembly = make_assembly(session, admin)
    headers = auth_headers(client, manager)
    closes_at = (datetime.utcnow() + timedelta(days=1)).isoformat()

    poll = client.post(
        "/api/v1/votes/",
        headers=headers,
        json={
            "kind": "ENQUETE",
            "title": "Cor da fachada",
            "vote_type": "SINGLE_CHOICE",
            "closes_at": closes_at,
            "options": [{"label": "Bege"}, {"label": "Cinza"}],
        },
    )
    assert poll.status_code == 201

    forbidden = client.post(
        "/api/v1/votes/",
        headers=headers,
        json={
            "assembly_id": str(assembly.id),
            "kind": "ASSEMBLEIA",
            "title": "Orçamento",
            "vote_type": "SINGLE_CHOICE",
            "closes_at": closes_at,
            "options": [{"label": "Sim"}, {"label": "Não"}],
        },
    )
    assert forbidden.status_code == 403


def test_anonymous_assembly_vote_is_rejected(client: TestClient, session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)

    response = client.post(
        "/api/v1/votes/",
        headers=auth_headers(client, admin),
        json={
            "assembly_id": str(assembly.id),
            "kind": "ASSEMBLEIA",
            "title": "Orçamento",
            "vote_type": "SINGLE_CHOICE",
            "is_anonymous": True,
            "closes_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "options": [{"label": "Sim"}, {"label": "Não"}],
        },
    )
    assert response.status_code == 400


def test_assembly_vote_requires_assembly_and_poll_forbids_it(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    headers = auth_headers(client, admin)
    closes_at = (datetime.utcnow() + timedelta(days=1)).isoformat()
    options = [{"label": "Sim"}, {"label": "Não"}]

    orphan = client.post(
        "/api/v1/votes/",
        headers=headers,
        json={
            "kind": "ASSEMBLEIA",
            "title": "Órfã",
            "vote_type": "SINGLE_CHOICE",
            "closes_at": closes_at,
            "options": options,
        },
    )
    assert orphan.status_code == 422

    bound_poll = client.post(
        "/api/v1/votes/",
        headers=headers,
        json={
            "assembly_id": str(assembly.id),
            "kind": "ENQUETE",
            "title": "Enquete presa",
            "vote_type": "SINGLE_CHOICE",
            "closes_at": closes_at,
            "options": options,
        },
    )
    assert bound_poll.status_code == 422


def test_patch_vote_after_first_ballot_returns_400(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    headers = auth_headers(client, admin)

    editable = client.patch(
        f"/api/v1/votes/{vote.id}", headers=headers, json={"title": "Novo título"}
    )
    assert editable.status_code == 200
    assert editable.json()["title"] == "Novo título"

    _cast(session, owner, vote, "Sim", lot)

    frozen = client.patch(
        f"/api/v1/votes/{vote.id}", headers=headers, json={"title": "Outro"}
    )
    assert frozen.status_code == 400


def test_patch_closed_assembly_returns_400(client: TestClient, session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin, status=AssemblyStatus.CLOSED)

    response = client.patch(
        f"/api/v1/assemblies/{assembly.id}",
        headers=auth_headers(client, admin),
        json={"title": "Renomeada"},
    )
    assert response.status_code == 400


def test_ballot_in_draft_assembly_returns_400(client: TestClient, session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin, status=AssemblyStatus.DRAFT)
    vote = make_vote(session, admin, assembly=assembly)

    response = client.post(
        f"/api/v1/votes/{vote.id}/ballots",
        headers=auth_headers(client, owner),
        json={
            "lot_id": str(lot.id),
            "selected_option_ids": [str(option_id(vote, "Sim"))],
        },
    )
    assert response.status_code == 400


def test_close_assembly_cascades_over_open_votes(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    headers = auth_headers(client, admin)

    response = client.post(f"/api/v1/assemblies/{assembly.id}/close", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"

    session.refresh(vote)
    assert vote.status == VoteStatus.CLOSED
    assert vote.tally_snapshot_json is not None


# ---------------------------------------------------------------------------
# 11 — GUEST/PORTEIRO never vote
# ---------------------------------------------------------------------------


def test_guest_and_porteiro_cannot_vote_in_either_modality(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    assembly_vote = make_vote(session, admin, assembly=assembly)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)
    lot = make_lot(session, "A", "1")

    for role in (UserRole.GUEST, UserRole.PORTEIRO):
        user = make_user(session, role)
        link_user_to_lot(session, user, lot)
        headers = auth_headers(client, user)

        assembly_attempt = client.post(
            f"/api/v1/votes/{assembly_vote.id}/ballots",
            headers=headers,
            json={
                "lot_id": str(lot.id),
                "selected_option_ids": [str(option_id(assembly_vote, "Sim"))],
            },
        )
        assert assembly_attempt.status_code == 403

        poll_attempt = client.post(
            f"/api/v1/votes/{poll.id}/ballots",
            headers=headers,
            json={"selected_option_ids": [str(option_id(poll, "Sim"))]},
        )
        assert poll_attempt.status_code == 403


# ---------------------------------------------------------------------------
# 7 / 10 / 17 / 18 — tally endpoint
# ---------------------------------------------------------------------------


def test_open_tally_returns_only_the_count_even_for_administrator(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    make_lot(session, "A", "2")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    _cast(session, owner, vote, "Sim", lot)

    response = client.get(
        f"/api/v1/votes/{vote.id}/tally", headers=auth_headers(client, admin)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["voters_count"] == 1
    assert body["total_lots"] == 2
    assert "results" not in body
    assert "attributions" not in body


def test_closed_poll_tally_has_no_total_lots_field(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)
    _cast(session, resident, poll, "Sim")
    headers = auth_headers(client, admin)

    client.post(f"/api/v1/votes/{poll.id}/close", headers=headers)
    body = client.get(f"/api/v1/votes/{poll.id}/tally", headers=headers).json()

    assert "total_lots" not in body
    assert body["voters_count"] == 1
    assert {r["label"]: r["count"] for r in body["results"]} == {"Sim": 1, "Não": 0}


def test_closed_anonymous_poll_tally_masks_identity_in_the_payload(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT, full_name="Ciclana")
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE, is_anonymous=True)
    _cast(session, resident, poll, "Sim")
    headers = auth_headers(client, admin)

    client.post(f"/api/v1/votes/{poll.id}/close", headers=headers)
    response = client.get(f"/api/v1/votes/{poll.id}/tally", headers=headers)

    assert "attributions" not in response.json()
    assert str(resident.id) not in response.text
    assert str(lot.id) not in response.text
    assert "Ciclana" not in response.text

    # ...and the voter still sees their own ballot.
    mine = client.get(
        f"/api/v1/votes/{poll.id}/my-ballot", headers=auth_headers(client, resident)
    )
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["can_edit"] is True
    assert str(resident.id) not in mine.text


def test_manager_without_lot_sees_counts_and_closed_assembly_tally(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    manager = make_user(session, UserRole.MANAGER)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)

    poll = make_vote(session, manager, kind=VoteKind.ENQUETE)
    _cast(session, owner, poll, "Sim")

    assembly = make_assembly(session, admin)
    assembly_vote = make_vote(session, admin, assembly=assembly)
    _cast(session, owner, assembly_vote, "Sim", lot)

    headers = auth_headers(client, manager)

    open_poll_tally = client.get(f"/api/v1/votes/{poll.id}/tally", headers=headers)
    assert open_poll_tally.status_code == 200
    assert open_poll_tally.json()["voters_count"] == 1
    assert "results" not in open_poll_tally.json()

    client.post(
        f"/api/v1/assemblies/{assembly.id}/close", headers=auth_headers(client, admin)
    )
    closed_tally = client.get(
        f"/api/v1/votes/{assembly_vote.id}/tally", headers=headers
    )
    assert closed_tally.status_code == 200
    assert closed_tally.json()["results"] is not None
    assert closed_tally.json()["attributions"][0]["lot_label"] == "A/1"


def test_guest_cannot_read_the_tally(client: TestClient, session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    guest = make_user(session, UserRole.GUEST)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)

    response = client.get(
        f"/api/v1/votes/{poll.id}/tally", headers=auth_headers(client, guest)
    )
    assert response.status_code == 403


def test_listing_votes_does_not_materialise_snapshots(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    assembly = make_assembly(session, admin)
    vote = make_vote(
        session,
        admin,
        assembly=assembly,
        opens_at=datetime.utcnow() - timedelta(days=2),
        closes_at=datetime.utcnow() - timedelta(minutes=5),
    )
    headers = auth_headers(client, admin)

    listing = client.get("/api/v1/votes/", headers=headers)
    assert listing.status_code == 200
    session.refresh(vote)
    assert vote.tally_snapshot_json is None
    assert vote.status == VoteStatus.OPEN

    detail = client.get(f"/api/v1/votes/{vote.id}", headers=headers)
    assert detail.status_code == 200
    session.refresh(vote)
    assert vote.status == VoteStatus.CLOSED
    assert vote.tally_snapshot_json is not None


# ---------------------------------------------------------------------------
# 19 — retract endpoint contract
# ---------------------------------------------------------------------------


def test_retract_endpoint_error_mapping(client: TestClient, session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner_a = make_user(session, UserRole.RESIDENT)
    owner_b = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner_a, lot)
    link_user_to_lot(session, owner_b, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)

    # Nothing cast yet -> 404
    empty = client.post(
        f"/api/v1/votes/{vote.id}/ballots/retract",
        headers=auth_headers(client, owner_a),
        json={"lot_id": str(lot.id)},
    )
    assert empty.status_code == 404

    _cast(session, owner_a, vote, "Sim", lot)

    # Someone else holds it -> 403
    other = client.post(
        f"/api/v1/votes/{vote.id}/ballots/retract",
        headers=auth_headers(client, owner_b),
        json={"lot_id": str(lot.id)},
    )
    assert other.status_code == 403

    ok = client.post(
        f"/api/v1/votes/{vote.id}/ballots/retract",
        headers=auth_headers(client, owner_a),
        json={"lot_id": str(lot.id)},
    )
    assert ok.status_code == 201
    assert ok.json()["is_retraction"] is True


def test_poll_retract_rejects_a_lot_id_and_assembly_requires_one(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    resident = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, resident, lot)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)
    _cast(session, resident, poll, "Sim")
    headers = auth_headers(client, resident)

    with_lot = client.post(
        f"/api/v1/votes/{poll.id}/ballots/retract",
        headers=headers,
        json={"lot_id": str(lot.id)},
    )
    assert with_lot.status_code == 422

    ok = client.post(
        f"/api/v1/votes/{poll.id}/ballots/retract", headers=headers, json={}
    )
    assert ok.status_code == 201

    assembly = make_assembly(session, admin)
    assembly_vote = make_vote(session, admin, assembly=assembly)
    missing_lot = client.post(
        f"/api/v1/votes/{assembly_vote.id}/ballots/retract", headers=headers, json={}
    )
    assert missing_lot.status_code == 422


def test_ballot_selection_arity_is_validated(client: TestClient, session: Session):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)
    headers = auth_headers(client, owner)

    too_many = client.post(
        f"/api/v1/votes/{vote.id}/ballots",
        headers=headers,
        json={
            "lot_id": str(lot.id),
            "selected_option_ids": [
                str(option_id(vote, "Sim")),
                str(option_id(vote, "Não")),
            ],
        },
    )
    assert too_many.status_code == 422

    foreign = client.post(
        f"/api/v1/votes/{vote.id}/ballots",
        headers=headers,
        json={
            "lot_id": str(lot.id),
            "selected_option_ids": ["11111111-1111-1111-1111-111111111111"],
        },
    )
    assert foreign.status_code == 422

    multi = make_vote(
        session,
        admin,
        assembly=assembly,
        vote_type=VoteType.MULTIPLE_CHOICE,
        title="Obras",
        option_labels=("A", "B", "C"),
    )
    ok = client.post(
        f"/api/v1/votes/{multi.id}/ballots",
        headers=headers,
        json={
            "lot_id": str(lot.id),
            "selected_option_ids": [
                str(option_id(multi, "A")),
                str(option_id(multi, "C")),
            ],
        },
    )
    assert ok.status_code == 201


# ---------------------------------------------------------------------------
# Lot delinquency + eligibility endpoints
# ---------------------------------------------------------------------------


def test_delinquency_endpoint_is_board_only_and_stamps_the_author(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    manager = make_user(session, UserRole.MANAGER)
    lot = make_lot(session, "A", "1")

    denied = client.patch(
        f"/api/v1/lots/{lot.id}/delinquency",
        headers=auth_headers(client, manager),
        json={"is_delinquent": True},
    )
    assert denied.status_code == 403

    allowed = client.patch(
        f"/api/v1/lots/{lot.id}/delinquency",
        headers=auth_headers(client, admin),
        json={"is_delinquent": True},
    )
    assert allowed.status_code == 200
    assert allowed.json()["is_delinquent"] is True

    session.refresh(lot)
    assert lot.is_delinquent is True
    assert lot.delinquency_updated_by_id == admin.id
    assert lot.delinquency_updated_at is not None


def test_voter_eligibility_endpoints_allow_manager_and_block_residents(
    client: TestClient, session: Session
):
    manager = make_user(session, UserRole.MANAGER)
    resident = make_user(session, UserRole.RESIDENT)
    spouse = make_user(session, UserRole.RESIDENT, full_name="Cônjuge")
    lot = make_lot(session, "A", "1")

    denied = client.post(
        f"/api/v1/lots/{lot.id}/voter-eligibility",
        headers=auth_headers(client, resident),
        json={"user_id": str(spouse.id)},
    )
    assert denied.status_code == 403

    headers = auth_headers(client, manager)
    created = client.post(
        f"/api/v1/lots/{lot.id}/voter-eligibility",
        headers=headers,
        json={"user_id": str(spouse.id)},
    )
    assert created.status_code == 201
    assert created.json()["user_name"] == "Cônjuge"

    listed = client.get(f"/api/v1/lots/{lot.id}/voter-eligibility", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    removed = client.delete(
        f"/api/v1/lots/{lot.id}/voter-eligibility/{spouse.id}", headers=headers
    )
    assert removed.status_code == 204


def test_delinquent_lot_is_refused_through_the_api(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    owner = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1", is_delinquent=True)
    link_user_to_lot(session, owner, lot)
    assembly = make_assembly(session, admin)
    vote = make_vote(session, admin, assembly=assembly)

    response = client.post(
        f"/api/v1/votes/{vote.id}/ballots",
        headers=auth_headers(client, owner),
        json={
            "lot_id": str(lot.id),
            "selected_option_ids": [str(option_id(vote, "Sim"))],
        },
    )
    assert response.status_code == 403

    client.patch(
        f"/api/v1/lots/{lot.id}/delinquency",
        headers=auth_headers(client, admin),
        json={"is_delinquent": False},
    )
    retry = client.post(
        f"/api/v1/votes/{vote.id}/ballots",
        headers=auth_headers(client, owner),
        json={
            "lot_id": str(lot.id),
            "selected_option_ids": [str(option_id(vote, "Sim"))],
        },
    )
    assert retry.status_code == 201


def test_tenant_can_vote_in_a_poll_through_the_api(
    client: TestClient, session: Session
):
    admin = make_user(session, UserRole.ADMINISTRATOR)
    tenant = make_user(session, UserRole.RESIDENT)
    lot = make_lot(session, "A", "1")
    link_user_to_lot(session, tenant, lot, LotAssociationType.INQUILINO)
    poll = make_vote(session, admin, kind=VoteKind.ENQUETE)

    response = client.post(
        f"/api/v1/votes/{poll.id}/ballots",
        headers=auth_headers(client, tenant),
        json={"selected_option_ids": [str(option_id(poll, "Sim"))]},
    )
    assert response.status_code == 201
    assert response.json()["lot_id"] is None
