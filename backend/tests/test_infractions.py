"""The infraction process: registration, promotion, history, contestation.

Twenty-two behavioural cases (§12.1) plus §12.2's four **structural**
assertions, which are the ones that keep decision 5 of §2 from being quietly
undone: no ``status`` column, no ``current_stage`` column, no ``updated_at`` on
the append-only history, and no route that edits or deletes a stage.
"""

from __future__ import annotations

import itertools
import uuid
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import event, func
from sqlmodel import select

from app.core.permissions import ROUTE_PERMISSIONS
from app.main import app
from app.models.enums import OccurrenceCategory
from app.models.infraction import Infraction, InfractionContestation, InfractionStage
from app.models.occurrence import Occurrence, OccurrenceTimeline
from tests.infraction_helpers import (
    LADDER_THREE,
    create_infraction,
    create_rule,
    headers,
    make_lot,
    make_member,
    make_resident,
)

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app.models.user import User


# ---------------------------------------------------------------------------
# Two clocks, and which column each one belongs to (CR1)
# ---------------------------------------------------------------------------
#
# This module compares against columns written by **two different clocks**, and
# collapsing them into one module-level `TODAY = date.today()` is a bug that
# fires for real:
#
# * `Infraction.created_at` is `datetime.utcnow()`, so `?date_from=`/`?date_to=`
#   filter a **UTC** column. A local date is behind the UTC date every evening
#   in every negative-offset zone -- in `America/Sao_Paulo` (UTC-3) that is
#   21:00-23:59, *every day* -- and the window then matches nothing.
# * `applied_on` and `defense_due_on` are computed by the service with
#   `date.today()`, which is **local**. Asserting a UTC date against those
#   would fail in the mirror-image window.
#
# So there are two helpers, each named for the clock it follows, and **both are
# computed per call** rather than captured at import: a 15-minute suite that
# starts at 23:5x would otherwise straddle midnight and fail for a third
# reason.
def _utc_today() -> date:
    """The date the database stamps (`created_at`, `datetime.utcnow()`)."""
    return datetime.utcnow().date()


def _local_today() -> date:
    """The date the service computes (`applied_on`, `defense_due_on`)."""
    return date.today()



@pytest.fixture(name="staff")
def staff_fixture(session: Session) -> User:
    """The staff actor. ADMINISTRATOR is a superuser, so it holds everything."""
    return make_member(session, profile="ADMINISTRATOR", seed=1)


@pytest.fixture(name="world")
def world_fixture(client: TestClient, session: Session, staff: User) -> dict:
    """One lot, one resident (linked to a RESIDENT user), one three-rung rule."""
    lot = make_lot(session)
    # Post-F5 there are **no seeds**: a permission minted after the legacy
    # bundles were recorded is held by no role until an operator grants it.
    # So the resident's `infractions:*` come from an explicit ad-hoc role,
    # which is exactly how §8.3's recommended bundle would be configured.
    resident_user = make_member(
        session,
        profile="RESIDENT",
        seed=2,
        permissions=["infractions:contest", "infractions:my_lots_read"],
    )
    resident = make_resident(session, lot, seed=10, user=resident_user)
    rule_id = create_rule(client, staff, steps=LADDER_THREE)
    return {
        "lot": lot,
        "resident": resident,
        "resident_user": resident_user,
        "rule_id": rule_id,
    }


def _occurrence(session: Session, *, lot_id: uuid.UUID | None, protocol: str) -> Occurrence:
    occurrence = Occurrence(
        protocol_number=protocol,
        category=OccurrenceCategory.NOISE,
        title="Barulho no bloco A",
        description="Som alto depois das 23h, relatado por vizinhos.",
        lot_id=lot_id,
    )
    session.add(occurrence)
    session.commit()
    session.refresh(occurrence)
    return occurrence


# ---------------------------------------------------------------------------
# Registration (§7.7)
# ---------------------------------------------------------------------------


def test_register_an_infraction_directly(client: TestClient, staff: User, world: dict):
    """201, no source occurrence, and no stage yet."""
    body = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    assert body["source_occurrence_id"] is None
    assert body["source_occurrence_protocol"] is None
    assert body["current_stage"] is None
    assert body["current_stage_at"] is None
    assert body["defense_due_on"] is None
    assert body["timeline"] == []
    assert body["lot"]["id"] == str(world["lot"].id)
    assert body["responsible"]["id"] == str(world["resident"].id)


def test_register_against_a_deactivated_rule_is_422(
    client: TestClient, staff: User, world: dict
):
    """§7.7 (1). Deactivation is forward-looking: an existing process still
    advances along the very same ladder."""
    existing = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )

    assert (
        client.delete(
            f"/api/v1/infraction-rules/{world['rule_id']}", headers=headers(staff)
        ).status_code
        == 204
    )

    refused = client.post(
        "/api/v1/infractions",
        json={
            "rule_id": world["rule_id"],
            "lot_id": str(world["lot"].id),
            "responsible_resident_id": str(world["resident"].id),
            "occurred_on": _local_today().isoformat(),
            "description": "Reincidência.",
        },
        headers=headers(staff),
    )
    assert refused.status_code == 422
    assert refused.json()["detail"] == "The rule is not active"

    advanced = client.post(
        f"/api/v1/infractions/{existing['id']}/stages",
        json={"note": "Aviso entregue em mãos."},
        headers=headers(staff),
    )
    assert advanced.status_code == 201, advanced.text
    assert advanced.json()["current_stage"] == "AVISO"


def test_responsible_must_belong_to_the_lot(
    client: TestClient, session: Session, staff: User, world: dict
):
    """§7.7 (2), both halves: another lot's resident, and an inactive one.

    Two distinct details, deliberately: "belongs to another lot" and "is no
    longer active on this lot" are different corrections for the person
    reading the message.
    """
    other_lot = make_lot(session, block="B", number="2")
    stranger = make_resident(session, other_lot, seed=30)
    inactive = make_resident(session, world["lot"], seed=31, is_active=False)

    def _post(resident_id: uuid.UUID):
        return client.post(
            "/api/v1/infractions",
            json={
                "rule_id": world["rule_id"],
                "lot_id": str(world["lot"].id),
                "responsible_resident_id": str(resident_id),
                "occurred_on": _local_today().isoformat(),
                "description": "Som alto.",
            },
            headers=headers(staff),
        )

    wrong_lot = _post(stranger.id)
    assert wrong_lot.status_code == 422
    assert (
        wrong_lot.json()["detail"]
        == "The responsible resident does not belong to this lot"
    )

    not_active = _post(inactive.id)
    assert not_active.status_code == 422
    assert (
        not_active.json()["detail"]
        == "The responsible resident is not active on this lot"
    )


# ---------------------------------------------------------------------------
# Promotion (§7.4)
# ---------------------------------------------------------------------------


def test_promote_an_occurrence(
    client: TestClient, session: Session, staff: User, world: dict
):
    """201, both sides of the link, and an OccurrenceTimeline note."""
    occurrence = _occurrence(session, lot_id=world["lot"].id, protocol="OC-0001")

    promoted = client.post(
        f"/api/v1/infractions/from-occurrence/{occurrence.id}",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
        },
        headers=headers(staff),
    )
    assert promoted.status_code == 201, promoted.text
    body = promoted.json()
    assert body["source_occurrence_id"] == str(occurrence.id)
    assert body["source_occurrence_protocol"] == "OC-0001"
    # Defaults come from the occurrence when the body omits them.
    assert body["description"] == occurrence.description
    assert body["occurred_on"] == occurrence.created_at.date().isoformat()
    # The effective lot is the occurrence's.
    assert body["lot"]["id"] == str(world["lot"].id)

    detail = client.get(
        f"/api/v1/occurrences/{occurrence.id}", headers=headers(staff)
    )
    assert detail.status_code == 200
    assert body["id"] in detail.json()["infraction_ids"]

    notes = session.exec(
        select(OccurrenceTimeline).where(
            OccurrenceTimeline.occurrence_id == occurrence.id
        )
    ).all()
    assert any("infração" in note.note for note in notes)


def test_promote_a_lotless_occurrence_with_an_explicit_lot(
    client: TestClient, session: Session, staff: User, world: dict
):
    """B1: a common-area occurrence attributed to a unit."""
    occurrence = _occurrence(session, lot_id=None, protocol="OC-0002")

    promoted = client.post(
        f"/api/v1/infractions/from-occurrence/{occurrence.id}",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
            "lot_id": str(world["lot"].id),
        },
        headers=headers(staff),
    )
    assert promoted.status_code == 201, promoted.text
    assert promoted.json()["lot"]["id"] == str(world["lot"].id)


def test_promote_a_lotless_occurrence_without_a_lot_is_422(
    client: TestClient, session: Session, staff: User, world: dict
):
    """B1: both absent, so there is no unit to attribute responsibility to."""
    occurrence = _occurrence(session, lot_id=None, protocol="OC-0003")

    refused = client.post(
        f"/api/v1/infractions/from-occurrence/{occurrence.id}",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
        },
        headers=headers(staff),
    )
    assert refused.status_code == 422
    assert (
        refused.json()["detail"] == "The occurrence has no lot; lot_id is required"
    )


def test_promote_with_a_conflicting_lot_is_422(
    client: TestClient, session: Session, staff: User, world: dict
):
    """B1: a mismatch is refused, never silently overridden, and writes nothing."""
    other_lot = make_lot(session, block="B", number="2")
    occurrence = _occurrence(session, lot_id=world["lot"].id, protocol="OC-0004")
    before = session.exec(select(func.count()).select_from(Infraction)).one()

    conflicting = client.post(
        f"/api/v1/infractions/from-occurrence/{occurrence.id}",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
            "lot_id": str(other_lot.id),
        },
        headers=headers(staff),
    )
    assert conflicting.status_code == 422
    assert (
        conflicting.json()["detail"] == "lot_id does not match the occurrence's lot"
    )
    assert session.exec(select(func.count()).select_from(Infraction)).one() == before

    equal = client.post(
        f"/api/v1/infractions/from-occurrence/{occurrence.id}",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
            "lot_id": str(world["lot"].id),
        },
        headers=headers(staff),
    )
    assert equal.status_code == 201, equal.text


def test_one_occurrence_promotes_twice(
    client: TestClient, session: Session, staff: User, world: dict
):
    """One incident can breach two rules, so the link is 1:N."""
    second_rule = create_rule(
        client, staff, article="art. 30", origin="ESTATUTO", steps=LADDER_THREE
    )
    occurrence = _occurrence(session, lot_id=world["lot"].id, protocol="OC-0005")

    ids = []
    for rule_id in (world["rule_id"], second_rule):
        response = client.post(
            f"/api/v1/infractions/from-occurrence/{occurrence.id}",
            json={
                "rule_id": rule_id,
                "responsible_resident_id": str(world["resident"].id),
            },
            headers=headers(staff),
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])

    detail = client.get(
        f"/api/v1/occurrences/{occurrence.id}", headers=headers(staff)
    )
    assert sorted(detail.json()["infraction_ids"]) == sorted(ids)


# ---------------------------------------------------------------------------
# The list (§4.5)
# ---------------------------------------------------------------------------


def test_list_filters_by_rule_lot_and_responsible(
    client: TestClient, session: Session, staff: User, world: dict
):
    """Each filter alone narrows; two compose with AND; `total` is post-filter."""
    other_rule = create_rule(client, staff, article="art. 30", origin="ESTATUTO")
    other_resident = make_resident(session, world["lot"], seed=40)

    first = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    second = create_infraction(
        client,
        staff,
        rule_id=other_rule,
        lot=world["lot"],
        resident=other_resident,
    )

    def _ids(**params) -> set[str]:
        response = client.get(
            "/api/v1/infractions", params=params, headers=headers(staff)
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["total"] == len(payload["items"])
        return {item["id"] for item in payload["items"]}

    assert _ids(rule_id=world["rule_id"]) == {first["id"]}
    assert _ids(responsible_id=str(other_resident.id)) == {second["id"]}
    # The ER-4 half of §6.2 property 1: the lot's history stays whole.
    assert _ids(lot_id=str(world["lot"].id)) == {first["id"], second["id"]}
    # Composed with AND.
    assert (
        _ids(rule_id=world["rule_id"], responsible_id=str(other_resident.id)) == set()
    )


def test_list_filters_by_the_derived_current_stage(
    client: TestClient, staff: User, world: dict
):
    """`?stage=` reads the *latest* stage, and no `current_stage` column exists."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )

    def _ids(stage: str) -> set[str]:
        response = client.get(
            "/api/v1/infractions", params={"stage": stage}, headers=headers(staff)
        )
        assert response.status_code == 200, response.text
        return {item["id"] for item in response.json()["items"]}

    assert _ids("NONE") == {infraction["id"]}
    assert _ids("AVISO") == set()

    client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Aviso."},
        headers=headers(staff),
    )
    assert _ids("NONE") == set()
    assert _ids("AVISO") == {infraction["id"]}

    client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Notificação."},
        headers=headers(staff),
    )
    assert _ids("AVISO") == set()
    assert _ids("NOTIFICACAO") == {infraction["id"]}


def test_list_filters_by_date_range_and_paginates(
    client: TestClient, session: Session, staff: User, world: dict
):
    """Inclusive on both end days over `created_at`; paging is stable.

    **Anchored on the UTC date, not the local one**, and captured once inside
    the test: `created_at` is `datetime.utcnow()`, so a local anchor makes this
    case fail every evening in every negative-offset timezone (CR1).
    """
    utc_today = _utc_today()
    ids = [
        create_infraction(
            client,
            staff,
            rule_id=world["rule_id"],
            lot=world["lot"],
            resident=world["resident"],
            occurred_on=utc_today - timedelta(days=index + 1),
        )["id"]
        for index in range(5)
    ]

    inside = client.get(
        "/api/v1/infractions",
        params={
            "date_from": utc_today.isoformat(),
            "date_to": utc_today.isoformat(),
        },
        headers=headers(staff),
    )
    assert inside.status_code == 200
    assert inside.json()["total"] == 5

    # Yesterday's window excludes rows created today.
    outside = client.get(
        "/api/v1/infractions",
        params={
            "date_from": (utc_today - timedelta(days=2)).isoformat(),
            "date_to": (utc_today - timedelta(days=1)).isoformat(),
        },
        headers=headers(staff),
    )
    assert outside.json()["total"] == 0

    walked: list[str] = []
    for skip in (0, 2, 4):
        page = client.get(
            "/api/v1/infractions",
            params={"skip": skip, "limit": 2},
            headers=headers(staff),
        ).json()
        assert page["total"] == 5
        assert page["skip"] == skip
        assert page["limit"] == 2
        walked.extend(item["id"] for item in page["items"])
    assert len(walked) == len(set(walked)) == 5
    assert set(walked) == set(ids)

    over = client.get(
        "/api/v1/infractions", params={"limit": 101}, headers=headers(staff)
    )
    assert over.status_code == 422


# ---------------------------------------------------------------------------
# The append-only history (§7.3)
# ---------------------------------------------------------------------------


def test_stage_history_is_append_only_and_derives_the_current_stage(
    client: TestClient, staff: User, world: dict
):
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    for note in ("Aviso.", "Notificação."):
        response = client.post(
            f"/api/v1/infractions/{infraction['id']}/stages",
            json={"note": note},
            headers=headers(staff),
        )
        assert response.status_code == 201, response.text

    read = client.get(
        f"/api/v1/infractions/{infraction['id']}", headers=headers(staff)
    ).json()
    assert read["current_stage"] == "NOTIFICACAO"
    assert [entry["action"] for entry in read["timeline"]] == [
        "AVISO",
        "NOTIFICACAO",
    ]
    assert {entry["kind"] for entry in read["timeline"]} == {"STAGE"}


def test_no_route_edits_or_deletes_a_stage():
    """§12.2: the history is append-only in the *route table*, not by habit."""
    offenders = [
        key
        for key in ROUTE_PERMISSIONS
        if key[0] in {"PUT", "PATCH", "DELETE"} and "/stages" in key[1]
    ]
    assert not offenders, offenders


def test_notificacao_freezes_the_deadline(
    client: TestClient, staff: User, world: dict
):
    """`applied_on + days`, and a later change to the rule does not move it."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Aviso."},
        headers=headers(staff),
    )
    notified = client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Notificação."},
        headers=headers(staff),
    )
    assert notified.status_code == 201, notified.text
    expected = (_local_today() + timedelta(days=30)).isoformat()
    assert notified.json()["defense_due_on"] == expected

    # Rewriting the ladder with a different deadline must not move it.
    client.put(
        f"/api/v1/infraction-rules/{world['rule_id']}/policy",
        json={
            "steps": [
                {"step_order": 1, "action": "AVISO"},
                {
                    "step_order": 2,
                    "action": "NOTIFICACAO",
                    "defense_deadline_days": 5,
                },
            ]
        },
        headers=headers(staff),
    )
    after = client.get(
        f"/api/v1/infractions/{infraction['id']}", headers=headers(staff)
    ).json()
    assert after["defense_due_on"] == expected


# ---------------------------------------------------------------------------
# Contestation (§7.5)
# ---------------------------------------------------------------------------


def _notify(client: TestClient, staff: User, infraction_id: str) -> None:
    client.post(
        f"/api/v1/infractions/{infraction_id}/stages",
        json={"note": "Aviso."},
        headers=headers(staff),
    )
    client.post(
        f"/api/v1/infractions/{infraction_id}/stages",
        json={"note": "Notificação."},
        headers=headers(staff),
    )


def test_contestation_inside_the_deadline(
    client: TestClient, staff: User, world: dict
):
    """201 for the notified unit; it appears in the timeline and moves nothing."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    _notify(client, staff, infraction["id"])

    contested = client.post(
        f"/api/v1/infractions/{infraction['id']}/contestation",
        json={"body": "Estava em viagem na data indicada."},
        headers=headers(world["resident_user"]),
    )
    assert contested.status_code == 201, contested.text
    body = contested.json()
    assert body["current_stage"] == "NOTIFICACAO"
    kinds = [entry["kind"] for entry in body["timeline"]]
    assert kinds == ["STAGE", "STAGE", "CONTESTATION"]


def test_contestation_after_the_deadline(
    client: TestClient, session: Session, staff: User, world: dict
):
    """409 once `defense_due_on` is in the past."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    _notify(client, staff, infraction["id"])

    stage = session.exec(
        select(InfractionStage).where(InfractionStage.action == "NOTIFICACAO")
    ).one()
    stage.defense_due_on = _local_today() - timedelta(days=1)
    session.add(stage)
    session.commit()

    late = client.post(
        f"/api/v1/infractions/{infraction['id']}/contestation",
        json={"body": "Fora do prazo."},
        headers=headers(world["resident_user"]),
    )
    assert late.status_code == 409
    assert late.json()["detail"] == "The defense deadline has passed"


def test_contestation_without_a_notificacao(
    client: TestClient, staff: User, world: dict
):
    """409: there is no deadline to answer."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    response = client.post(
        f"/api/v1/infractions/{infraction['id']}/contestation",
        json={"body": "Sem notificação."},
        headers=headers(world["resident_user"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "No open defense deadline"


def test_contestation_from_an_unlinked_caller_is_403(
    client: TestClient, session: Session, staff: User, world: dict
):
    """B2: 403 **before** the deadline branch, and nothing is written.

    The order is what stops the answer leaking whether a neighbour's process
    has an open deadline.
    """
    neighbour_lot = make_lot(session, block="B", number="2")
    neighbour_user = make_member(
        session,
        profile="RESIDENT",
        seed=50,
        permissions=["infractions:contest", "infractions:my_lots_read"],
    )
    make_resident(session, neighbour_lot, seed=51, user=neighbour_user)

    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    _notify(client, staff, infraction["id"])
    stage = session.exec(
        select(InfractionStage).where(InfractionStage.action == "NOTIFICACAO")
    ).one()
    stage.defense_due_on = _local_today() - timedelta(days=1)
    session.add(stage)
    session.commit()

    refused = client.post(
        f"/api/v1/infractions/{infraction['id']}/contestation",
        json={"body": "Não é meu lote."},
        headers=headers(neighbour_user),
    )
    # 403 and not 409, even though the deadline has also passed.
    assert refused.status_code == 403
    assert (
        refused.json()["detail"]
        == "Only the notified unit may contest this infraction"
    )
    assert (
        session.exec(select(func.count()).select_from(InfractionContestation)).one()
        == 0
    )


def test_contestation_by_a_superuser_is_also_object_narrowed(
    client: TestClient, session: Session, staff: User, world: dict
):
    """B2: `is_superuser` and `is_tenant_admin` are narrowed too; linking fixes it.

    The check is not a permission check -- both short-circuit the permission
    resolver and therefore always hold `infractions:contest` -- it is an object
    check, and a contestation is the unit's own act.
    """
    superuser = make_member(
        session, profile="GUEST", seed=60, is_superuser=True
    )
    admin = make_member(
        session, profile="GUEST", seed=61, is_tenant_admin=True
    )

    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    _notify(client, staff, infraction["id"])

    for actor in (superuser, admin):
        refused = client.post(
            f"/api/v1/infractions/{infraction['id']}/contestation",
            json={"body": "Em nome da unidade."},
            headers=headers(actor),
        )
        assert refused.status_code == 403, refused.text

    # Linking either one makes the very same call succeed.
    make_resident(session, world["lot"], seed=62, user=superuser)
    allowed = client.post(
        f"/api/v1/infractions/{infraction['id']}/contestation",
        json={"body": "Agora moro aqui."},
        headers=headers(superuser),
    )
    assert allowed.status_code == 201, allowed.text


# ---------------------------------------------------------------------------
# The fine (§6.3)
# ---------------------------------------------------------------------------


def test_fine_amount_is_frozen_on_the_stage(
    client: TestClient, staff: User, world: dict
):
    """A later change to `condo_fee_amount` never rewrites history."""
    rule_id = create_rule(
        client,
        staff,
        article="art. 44",
        origin="CONVENCAO",
        steps=[
            {
                "step_order": 1,
                "action": "MULTA",
                "fine_mode": "MULTIPLE",
                "fine_fee_multiplier": 2.0,
            }
        ],
    )
    client.put(
        "/api/v1/infraction-settings",
        json={"condo_fee_amount": 100.0},
        headers=headers(staff),
    )
    infraction = create_infraction(
        client,
        staff,
        rule_id=rule_id,
        lot=world["lot"],
        resident=world["resident"],
    )
    applied = client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Multa aplicada."},
        headers=headers(staff),
    )
    assert applied.status_code == 201, applied.text
    assert applied.json()["timeline"][0]["fine_amount"] == 200.0

    client.put(
        "/api/v1/infraction-settings",
        json={"condo_fee_amount": 999.0},
        headers=headers(staff),
    )
    after = client.get(
        f"/api/v1/infractions/{infraction['id']}", headers=headers(staff)
    ).json()
    assert after["timeline"][0]["fine_amount"] == 200.0


def test_multa_without_a_fee_reference(client: TestClient, staff: User, world: dict):
    """409, and an explicit `fine_amount` is 201 with the override recorded."""
    rule_id = create_rule(
        client,
        staff,
        article="art. 45",
        origin="CONVENCAO",
        steps=[
            {
                "step_order": 1,
                "action": "MULTA",
                "fine_mode": "MULTIPLE",
                "fine_fee_multiplier": 3.0,
            }
        ],
    )
    infraction = create_infraction(
        client,
        staff,
        rule_id=rule_id,
        lot=world["lot"],
        resident=world["resident"],
    )

    suggestion = client.get(
        f"/api/v1/infractions/{infraction['id']}/next-step", headers=headers(staff)
    ).json()
    assert suggestion["fine_amount"] is None
    assert suggestion["fine_amount_unavailable_reason"] == "CONDO_FEE_NOT_SET"

    refused = client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Multa."},
        headers=headers(staff),
    )
    assert refused.status_code == 409
    assert refused.json()["detail"] == "The condominium fee reference is not set"

    explicit = client.post(
        f"/api/v1/infractions/{infraction['id']}/stages",
        json={"note": "Multa arbitrada pelo síndico.", "fine_amount": 300.0},
        headers=headers(staff),
    )
    assert explicit.status_code == 201, explicit.text
    entry = explicit.json()["timeline"][0]
    assert entry["fine_amount"] == 300.0
    assert entry["fine_amount_overridden"] is True


# ---------------------------------------------------------------------------
# Route ordering (§4.2)
# ---------------------------------------------------------------------------


def test_route_order_puts_the_literal_segments_first(
    client: TestClient, staff: User, world: dict
):
    """`/my-lots` and `/cycles` must never be matched as a `{infraction_id}`."""
    for path in ("/api/v1/infractions/my-lots", "/api/v1/infractions/cycles"):
        response = client.get(path, headers=headers(staff))
        assert response.status_code in {200, 403}, (path, response.status_code)
        assert response.status_code != 422, path


# ---------------------------------------------------------------------------
# §12.2 -- the structural assertions
# ---------------------------------------------------------------------------


def test_infraction_has_no_status_and_no_current_stage_column():
    """Decision 5 of §2, pinned so a convenience column is a test failure."""
    columns = set(Infraction.__table__.columns.keys())
    assert "status" not in columns
    assert "current_stage" not in columns
    assert "current_stage_at" not in columns


def test_infraction_stage_is_append_only_in_the_schema():
    """No `updated_at`: the history is append-only in the schema, not only in
    the handlers."""
    assert "updated_at" not in set(InfractionStage.__table__.columns.keys())


def test_cycle_close_justification_is_required_and_lot_id_is_optional(
    client: TestClient, staff: User, world: dict
):
    """ER-9's shape, and §6.2 property 5's optional audit context."""
    from app.models.infraction import InfractionCycleClose

    columns = InfractionCycleClose.__table__.columns
    assert columns["justification"].nullable is False
    assert columns["lot_id"].nullable is True

    blank = client.post(
        "/api/v1/infractions/cycles/close",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
            "justification": "   ",
        },
        headers=headers(staff),
    )
    assert blank.status_code == 422

    without_lot = client.post(
        "/api/v1/infractions/cycles/close",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
            "justification": "Troca de inquilino não refletida no cadastro.",
        },
        headers=headers(staff),
    )
    assert without_lot.status_code == 201, without_lot.text
    assert without_lot.json()["lot_id"] is None


def test_infraction_lot_id_is_not_null_while_occurrence_lot_id_is():
    """The asymmetry §7.4's effective-lot rule exists for, pinned both ways."""
    assert Infraction.__table__.columns["lot_id"].nullable is False
    assert Occurrence.__table__.columns["lot_id"].nullable is True


def test_created_at_is_a_naive_utc_datetime(client: TestClient, staff: User, world: dict):
    """The house shape: `datetime.utcnow()`, naive, like every other table."""
    body = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    parsed = datetime.fromisoformat(body["created_at"])
    assert parsed.tzinfo is None


# ---------------------------------------------------------------------------
# Evidence, and the references that do not resolve
# ---------------------------------------------------------------------------


def test_evidence_urls_round_trip_and_a_hand_edited_row_reads_as_empty(
    client: TestClient, session: Session, staff: User, world: dict
):
    """`evidence_urls` mirrors `Occurrence.photo_urls_json` -- a JSON string.

    The tolerance for a malformed payload is deliberate and is the same one
    `OccurrenceService` has: a row hand-edited in psql must degrade to "no
    evidence", not to a 500 on every read of the infraction.
    """
    created = client.post(
        "/api/v1/infractions",
        json={
            "rule_id": world["rule_id"],
            "lot_id": str(world["lot"].id),
            "responsible_resident_id": str(world["resident"].id),
            "occurred_on": _local_today().isoformat(),
            "description": "Com fotos.",
            "evidence_urls": ["http://null/a.jpg", "http://null/b.jpg"],
        },
        headers=headers(staff),
    )
    assert created.status_code == 201, created.text
    assert created.json()["evidence_urls"] == [
        "http://null/a.jpg",
        "http://null/b.jpg",
    ]

    row = session.get(Infraction, uuid.UUID(created.json()["id"]))
    row.evidence_urls_json = "{not json"
    session.add(row)
    session.commit()

    reread = client.get(
        f"/api/v1/infractions/{created.json()['id']}", headers=headers(staff)
    )
    assert reread.status_code == 200
    assert reread.json()["evidence_urls"] == []

    # A JSON scalar is well-formed and still not a list.
    row.evidence_urls_json = '"just a string"'
    session.add(row)
    session.commit()
    assert (
        client.get(
            f"/api/v1/infractions/{created.json()['id']}", headers=headers(staff)
        ).json()["evidence_urls"]
        == []
    )


def test_a_lot_that_does_not_exist_is_422(
    client: TestClient, staff: User, world: dict
):
    """Checked before the responsible, so the message names the first problem."""
    response = client.post(
        "/api/v1/infractions",
        json={
            "rule_id": world["rule_id"],
            "lot_id": str(uuid.uuid4()),
            "responsible_resident_id": str(world["resident"].id),
            "occurred_on": _local_today().isoformat(),
            "description": "x",
        },
        headers=headers(staff),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "The lot does not exist"


def test_promoting_an_occurrence_that_does_not_exist_is_404(
    client: TestClient, staff: User, world: dict
):
    """404 and not 422: the path parameter names no object in this tenant."""
    response = client.post(
        f"/api/v1/infractions/from-occurrence/{uuid.uuid4()}",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
        },
        headers=headers(staff),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("field", ["responsible_resident_id", "lot_id"])
def test_a_cycle_close_naming_a_missing_object_is_422(
    client: TestClient, staff: User, world: dict, field: str
):
    """ER-9's body names two objects, and both are resolved before anything is
    written -- a close recorded against a resident who does not exist would be
    an audit row nobody can read back."""
    body = {
        "rule_id": world["rule_id"],
        "responsible_resident_id": str(world["resident"].id),
        "justification": "Troca de inquilino.",
    }
    body[field] = str(uuid.uuid4())

    response = client.post(
        "/api/v1/infractions/cycles/close", json=body, headers=headers(staff)
    )
    assert response.status_code == 422, response.text
    assert "does not exist" in response.json()["detail"]


# ---------------------------------------------------------------------------
# The list path's query count (round-2 review N-1)
# ---------------------------------------------------------------------------


def test_a_page_costs_a_constant_number_of_queries(
    client: TestClient, session: Session, staff: User, world: dict
):
    """`GET /infractions` is O(1) in the page size, **including** the protocol.

    Measured, not asserted from the shape of the code: `_EAGER_RELATIONS`
    fixes the five relations `_infraction_read` walks, and
    `_source_protocols` fixes the sixth. Round 2 shipped the first without the
    second, which read `9 + N` — flat-looking in a docstring and linear in
    production.

    The assertion is deliberately "the count does not grow with N" rather than
    a magic number: the absolute figure moves with any unrelated change to the
    request pipeline, and it is the *slope* that is the property worth pinning.
    """
    # Built once, before any expiry: `headers()` reads `staff.id`, and doing
    # that inside the measured window would count a refresh of the actor.
    auth = headers(staff)
    counter = itertools.count(1)

    def _promote() -> None:
        # A **distinct** occurrence per row, and that is the whole point: eight
        # promotions of one occurrence are eight identity-map hits after the
        # first, so the fan-out hides and the measurement lies. The second
        # draft of this test passed with the batching removed for exactly that
        # reason.
        occurrence = _occurrence(
            session,
            lot_id=world["lot"].id,
            protocol=f"OC-N{next(counter)}",
        )
        response = client.post(
            f"/api/v1/infractions/from-occurrence/{occurrence.id}",
            json={
                "rule_id": world["rule_id"],
                "responsible_resident_id": str(world["resident"].id),
            },
            headers=auth,
        )
        assert response.status_code == 201, response.text

    def _count_queries_for_one_page() -> int:
        statements: list[str] = []

        # A cold identity map, which is what a real request has. Without it
        # the promoted occurrences are still resident in the session from the
        # `POST`s above, `session.get` is served from memory, and the
        # measurement reads "constant" however the code is written -- the first
        # draft of this test passed with the batching removed. `expire_all`
        # rather than `expunge_all`: it forces the re-SELECT without detaching
        # the fixtures the test itself still holds.
        session.expire_all()

        def _record(_conn, _cursor, statement, *_rest):
            statements.append(statement)

        event.listen(session.get_bind(), "before_cursor_execute", _record)
        try:
            response = client.get(
                "/api/v1/infractions", params={"limit": 100}, headers=auth
            )
            assert response.status_code == 200, response.text
        finally:
            event.remove(session.get_bind(), "before_cursor_execute", _record)
        return len(statements)

    # Every row on the page is promoted, so every row wants a protocol -- the
    # shape in which the residual fan-out was visible.
    _promote()
    one = _count_queries_for_one_page()
    for _ in range(7):
        _promote()
    eight = _count_queries_for_one_page()

    assert eight == one, (
        "the list path is linear in the page size: "
        f"{one} queries for 1 row, {eight} for 8"
    )

    # **And the batch must actually resolve.** Counting queries alone cannot
    # tell "one query that returns the protocols" from "no query and every
    # protocol null" -- a `_source_protocols` that returned `{}` would keep
    # this test flat and green, which is exactly what the round-3 reviewer
    # demonstrated by nulling its `wanted` set.
    listed = client.get(
        "/api/v1/infractions", params={"limit": 100}, headers=auth
    ).json()["items"]
    assert len(listed) == 8
    protocols = {item["source_occurrence_protocol"] for item in listed}
    assert None not in protocols, (
        "the list path batched the protocols away: "
        f"{[item['source_occurrence_protocol'] for item in listed]}"
    )
    # Eight distinct occurrences were promoted, so eight distinct protocols
    # must come back -- one shared value would mean the map keyed wrongly.
    assert protocols == {f"OC-N{index}" for index in range(1, 9)}
    for item in listed:
        assert item["source_occurrence_id"] is not None


def test_the_lots_route_ceiling_matches_the_lot_selects_limit():
    """The backend half of a two-sided pin (round-2 review CR3).

    `NewInfractionModal.tsx` exports `LOT_SELECT_LIMIT = 100` and asks
    `GET /api/v1/lots/` for that page size. Round 2 asked for **200** against a
    route bounded at `le=100`, so FastAPI answered 422 before the handler ran,
    the lot select was empty in production, and *no infraction could be
    registered from the UI at all* — invisible to the suite because every
    frontend test mocked `api/lots` wholesale.

    Neither side can import the other across the language boundary, so each
    states the constant and names the other, exactly as
    `test_module_vocabulary.py::test_the_catalogue_modules_are_the_ones_the_ui_labels`
    does for the module list. This half reads the **live route object** rather
    than the source text, so it follows a refactor of the signature.
    """
    route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/api/v1/lots/"
        and "GET" in candidate.methods
    )
    limit = next(
        param for param in route.dependant.query_params if param.name == "limit"
    )
    ceiling = limit.field_info.metadata

    declared = next(
        getattr(constraint, "le", None)
        for constraint in ceiling
        if getattr(constraint, "le", None) is not None
    )
    # A fully static message: pytest's assertion rewriting already prints the
    # observed and expected values, and building the string dynamically only
    # tripped ruff's SQL-injection heuristic on the word it contains.
    assert declared == 100, (
        "GET /api/v1/lots/ changed the page size it accepts. "
        "`LOT_SELECT_LIMIT` in "
        "frontend/src/features/infraction-management/components/"
        "NewInfractionModal.tsx must move with it (and its sibling constant in "
        "__tests__/lotSelectContract.test.tsx), or the lot select is rejected "
        "and no infraction can be registered from the UI."
    )
