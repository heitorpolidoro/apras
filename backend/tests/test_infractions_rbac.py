"""§8.3's recommended bundle against the 18 routes (APRAS-44 §12.1).

Post-F5 **nothing is seeded**: a permission minted after the legacy bundles
were recorded is held by no role until an operator grants it. The role names
in the nine Expected Results are therefore read as the *recommended* bundle,
and this module builds real role rows to it rather than asserting that some
migration wrote them.

The two ER-8 halves, and the one property the parity matrix structurally
cannot show:

* a role with **no** ``infractions:*`` gets 403 on all 18 routes;
* a role with exactly ``{my_lots_read, contest}`` reaches ``/my-lots`` and is
  refused ``GET /infractions``;
* a *staff* caller holding ``my_lots_read`` with **no** ``UserLotLink`` and no
  active ``Resident`` row gets **200 with ``[]``** -- a filter, never a
  refusal. Every matrix profile is linked to ``world.lot``, so the matrix
  cannot express this one.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from app.core.permissions import ROUTE_PERMISSIONS, module_of
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


#: The 18 routes of the module, derived from the registry so a route added
#: without a test is impossible.
MODULE_ROUTES = sorted(
    key for key, permission in ROUTE_PERMISSIONS.items()
    if module_of(permission) == "infractions"
)

#: §8.3's table, transposed: `profile -> the permissions the bundle recommends`.
RECOMMENDED: dict[str, set[str]] = {
    "ADMINISTRATOR": {
        "infractions:read",
        "infractions:create",
        "infractions:advance",
        "infractions:promote",
        "infractions:cycle_close",
        "infractions:contest",
        "infractions:my_lots_read",
        "infractions:rule_read",
        "infractions:rule_create",
        "infractions:rule_update",
        "infractions:rule_deactivate",
        "infractions:policy_update",
        "infractions:settings_update",
    },
    "DIRECTOR": {
        "infractions:read",
        "infractions:create",
        "infractions:advance",
        "infractions:promote",
        "infractions:cycle_close",
        "infractions:contest",
        "infractions:my_lots_read",
        "infractions:rule_read",
        "infractions:rule_create",
        "infractions:rule_update",
        "infractions:rule_deactivate",
        "infractions:policy_update",
        "infractions:settings_update",
    },
    "MANAGER": {
        "infractions:read",
        "infractions:create",
        "infractions:advance",
        "infractions:promote",
        "infractions:cycle_close",
        "infractions:contest",
        "infractions:my_lots_read",
        "infractions:rule_read",
    },
    "RESIDENT": {"infractions:contest", "infractions:my_lots_read"},
    "PORTEIRO": set(),
    "GUEST": set(),
}


def test_the_module_has_exactly_eighteen_routes():
    """§1.1's `+18`, measured rather than predicted."""
    assert len(MODULE_ROUTES) == 18
    assert len({permission for _key, permission in ROUTE_PERMISSIONS.items()
                if module_of(permission) == "infractions"}) == 13


def test_the_recommended_bundle_covers_the_catalogue_exactly():
    """Every one of the 13 is recommended to somebody, and nothing else is."""
    union = set().union(*RECOMMENDED.values())
    assert union == {
        permission
        for permission in ROUTE_PERMISSIONS.values()
        if module_of(permission) == "infractions"
    }
    # ER-8: the two roles that hold nothing hold nothing.
    assert RECOMMENDED["PORTEIRO"] == set()
    assert RECOMMENDED["GUEST"] == set()


@pytest.fixture(name="staff")
def staff_fixture(session: Session) -> User:
    return make_member(session, profile="ADMINISTRATOR", seed=1)


def _request(client: TestClient, actor: User, method: str, path: str, ids: dict):
    """Issue one real request for a `(method, path)` of the module."""
    url = (
        path.replace("{rule_id}", ids["rule_id"])
        .replace("{infraction_id}", ids["infraction_id"])
        .replace("{occurrence_id}", ids["occurrence_id"])
    )
    bodies = {
        ("POST", "/api/v1/infraction-rules"): {
            "article": "art. 1",
            "origin": "ESTATUTO",
            "description": "x",
            "recidivism_window_days": 30,
        },
        ("PUT", "/api/v1/infraction-rules/{rule_id}"): {"description": "y"},
        ("PUT", "/api/v1/infraction-rules/{rule_id}/policy"): {
            "steps": [{"step_order": 1, "action": "AVISO"}]
        },
        ("PUT", "/api/v1/infraction-settings"): {"condo_fee_amount": 1.0},
        ("POST", "/api/v1/infractions"): {
            "rule_id": ids["rule_id"],
            "lot_id": ids["lot_id"],
            "responsible_resident_id": ids["resident_id"],
            "occurred_on": date.today().isoformat(),
            "description": "x",
        },
        ("POST", "/api/v1/infractions/from-occurrence/{occurrence_id}"): {
            "rule_id": ids["rule_id"],
            "responsible_resident_id": ids["resident_id"],
            "lot_id": ids["lot_id"],
        },
        ("POST", "/api/v1/infractions/{infraction_id}/stages"): {"note": "x"},
        ("POST", "/api/v1/infractions/{infraction_id}/contestation"): {"body": "x"},
        ("POST", "/api/v1/infractions/cycles/close"): {
            "rule_id": ids["rule_id"],
            "responsible_resident_id": ids["resident_id"],
            "justification": "x",
        },
    }
    kwargs = {}
    if (method, path) in bodies:
        kwargs["json"] = bodies[(method, path)]
    return client.request(method, url, headers=headers(actor), **kwargs)


@pytest.fixture(name="ids")
def ids_fixture(client: TestClient, session: Session, staff: User) -> dict:
    from app.models.enums import OccurrenceCategory
    from app.models.occurrence import Occurrence

    lot = make_lot(session)
    resident = make_resident(session, lot, seed=10)
    rule_id = create_rule(client, staff, steps=LADDER_THREE)
    infraction = create_infraction(
        client, staff, rule_id=rule_id, lot=lot, resident=resident
    )
    occurrence = Occurrence(
        protocol_number="OC-RBAC",
        category=OccurrenceCategory.OTHER,
        title="t",
        description="d",
        lot_id=lot.id,
    )
    session.add(occurrence)
    session.commit()
    session.refresh(occurrence)
    return {
        "rule_id": rule_id,
        "infraction_id": infraction["id"],
        "occurrence_id": str(occurrence.id),
        "lot_id": str(lot.id),
        "resident_id": str(resident.id),
    }


def test_a_role_with_no_infraction_permission_is_403_on_all_eighteen_routes(
    client: TestClient, session: Session, ids: dict
):
    """ER-8: the whole module, `/my-lots` and the contestation included."""
    porteiro = make_member(session, profile="PORTEIRO", seed=20, permissions=[])
    refused = {
        (method, path): _request(client, porteiro, method, path, ids).status_code
        for method, path in MODULE_ROUTES
    }
    assert set(refused.values()) == {403}, refused


def test_a_resident_bundle_reaches_my_lots_and_not_the_management_list(
    client: TestClient, session: Session, staff: User, ids: dict
):
    """ER-8's second half, with `defense_due_on` populated on the answer."""
    lot = make_lot(session, block="C", number="3")
    resident_user = make_member(
        session,
        profile="RESIDENT",
        seed=30,
        permissions=sorted(RECOMMENDED["RESIDENT"]),
    )
    resident = make_resident(session, lot, seed=31, user=resident_user)
    infraction = create_infraction(
        client, staff, rule_id=ids["rule_id"], lot=lot, resident=resident
    )
    for note in ("Aviso.", "Notificação."):
        client.post(
            f"/api/v1/infractions/{infraction['id']}/stages",
            json={"note": note},
            headers=headers(staff),
        )

    mine = client.get("/api/v1/infractions/my-lots", headers=headers(resident_user))
    assert mine.status_code == 200, mine.text
    payload = mine.json()
    assert [item["id"] for item in payload] == [infraction["id"]]
    assert payload[0]["defense_due_on"] is not None

    management = client.get("/api/v1/infractions", headers=headers(resident_user))
    assert management.status_code == 403


def test_an_unlinked_staff_caller_gets_an_empty_list_never_a_403(
    client: TestClient, session: Session, ids: dict
):
    """§3.4's `[]` case -- the property the parity matrix cannot show.

    `packages:my_lots_read` would answer 403 here; this permission is a
    filter, which is why `ADMIN_GAP_PERMISSIONS` stays a one-element set.
    """
    unlinked = make_member(
        session,
        profile="MANAGER",
        seed=40,
        permissions=sorted(RECOMMENDED["MANAGER"]),
    )
    response = client.get("/api/v1/infractions/my-lots", headers=headers(unlinked))
    assert response.status_code == 200
    assert response.json() == []


def test_the_manager_bundle_reaches_the_process_but_not_the_catalogue_writes(
    client: TestClient, session: Session, ids: dict
):
    """`cycle_close` is MANAGER-level; the catalogue writes are not (§8.3)."""
    manager = make_member(
        session,
        profile="MANAGER",
        seed=50,
        permissions=sorted(RECOMMENDED["MANAGER"]),
    )
    allowed = {
        ("GET", "/api/v1/infractions"),
        ("GET", "/api/v1/infractions/{infraction_id}"),
        ("GET", "/api/v1/infractions/{infraction_id}/next-step"),
        ("GET", "/api/v1/infractions/cycles"),
        ("GET", "/api/v1/infraction-rules"),
        ("GET", "/api/v1/infraction-settings"),
    }
    for method, path in sorted(allowed):
        response = _request(client, manager, method, path, ids)
        assert response.status_code == 200, (method, path, response.text)

    for method, path in (
        ("POST", "/api/v1/infraction-rules"),
        ("PUT", "/api/v1/infraction-rules/{rule_id}"),
        ("DELETE", "/api/v1/infraction-rules/{rule_id}"),
        ("PUT", "/api/v1/infraction-rules/{rule_id}/policy"),
        ("PUT", "/api/v1/infraction-settings"),
    ):
        response = _request(client, manager, method, path, ids)
        assert response.status_code == 403, (method, path, response.status_code)

    closed = _request(
        client, manager, "POST", "/api/v1/infractions/cycles/close", ids
    )
    assert closed.status_code == 201, closed.text


def test_the_director_bundle_reaches_every_route(
    client: TestClient, session: Session, ids: dict
):
    """The recommended síndico bundle: no 403 anywhere in the module."""
    director = make_member(
        session,
        profile="DIRECTOR",
        seed=60,
        permissions=sorted(RECOMMENDED["DIRECTOR"]),
        is_superuser=False,
    )
    # Linked to the lot, so the contestation's object check does not fire.
    import uuid

    from app.models.lot import UserLotLink

    session.add(
        UserLotLink(
            user_id=director.id,
            lot_id=uuid.UUID(ids["lot_id"]),
            start_date=None,
            end_date=None,
        )
    )
    session.commit()

    for method, path in MODULE_ROUTES:
        response = _request(client, director, method, path, ids)
        assert response.status_code != 403, (method, path, response.text)
