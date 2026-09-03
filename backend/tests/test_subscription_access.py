"""Who actually holds `billing:read` / `billing:manage` (APRAS-40 §2.3).

The board's framing is "tenant_admin **and** DIRECTOR". Post-APRAS-49 there is
no `DIRECTOR` enum, so "DIRECTOR" has to become a permission -- which is what
makes this module's story mechanical rather than a matter of who used to be
what:

* **`is_tenant_admin` reaches it for free**, with **no `or is_tenant_admin`
  clause anywhere in this task**: APRAS-47 gives an acting tenant_admin every
  permission in the catalogue in the granting tenant, and `billing` is core so
  APRAS-39's strip never removes it.
* **A superuser reaches it for free** by APRAS-47's short-circuit.
* **A "Diretor" reaches it only when the condominium grants it.** No role row
  anywhere holds either string on the day this task lands, and that is
  deliberate: seeding `billing:manage` into `Diretor (papel)` would violate
  F1's no-seeds decision, hand commercial authority to every director of every
  existing condominium without the síndico asking, and move
  `tests/data/legacy_role_bundles.json` -- the recorded artefact migration
  `0033` is verified against.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, select

from app.models.role import Role
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    make_plan,
    make_role_holder,
    make_superuser,
    make_tenant_admin,
    subscribe,
)

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parent.parent
BUNDLES_PATH = BACKEND_ROOT / "tests" / "data" / "legacy_role_bundles.json"

BILLING = ("billing:read", "billing:manage")
SUBSCRIPTION = "/api/v1/subscription"
HISTORY_URL = "/api/v1/subscription/history"
MODULES_URL = "/api/v1/subscription/modules"


@pytest.fixture(name="managed")
def managed_fixture(session: Session):
    plan = make_plan(session, included=["documents"])
    return subscribe(session, tenant_id=TENANT_A, plan=plan)


def test_no_role_row_holds_billing_permissions_on_a_fresh_install(
    session: Session,
):
    """§2.3, and it is a decision rather than a gap.

    A director gets the subscription area when a tenant_admin (or a superuser)
    ticks the two boxes in the role editor -- the same way a director gets
    every other post-F5 capability.
    """
    recorded = json.loads(BUNDLES_PATH.read_text(encoding="utf-8"))["bundles"]
    for profile, permissions in recorded.items():
        assert not set(BILLING) & set(permissions), (
            f"{profile}'s recorded legacy bundle carries a billing permission; "
            "seeding one would move the artefact migration 0033 is verified "
            "against"
        )

    for role in session.exec(select(Role)).all():
        assert not set(BILLING) & set(role.permissions), role.name


def test_a_tenant_admin_reaches_the_area_with_no_special_case(
    session: Session, tenant_client: TestClient, managed
):
    tenant_admin = make_tenant_admin(session)
    headers = auth(tenant_admin, TENANT_A)

    assert tenant_client.get(SUBSCRIPTION, headers=headers).status_code == 200
    assert tenant_client.get(HISTORY_URL, headers=headers).status_code == 200
    assert tenant_client.put(
        MODULES_URL, json={"active_modules": ["documents"]}, headers=headers
    ).status_code == 200


def test_a_director_reaches_the_area_once_the_role_grants_it(
    session: Session, tenant_client: TestClient, managed
):
    """403 before the grant, 200 after ticking the two boxes on the role."""
    director, role = make_role_holder(session, [])
    headers = auth(director, TENANT_A)

    assert tenant_client.get(SUBSCRIPTION, headers=headers).status_code == 403
    assert tenant_client.get(HISTORY_URL, headers=headers).status_code == 403
    assert tenant_client.put(
        MODULES_URL, json={"active_modules": []}, headers=headers
    ).status_code == 403

    role.permissions = list(BILLING)
    session.add(role)
    session.commit()

    assert tenant_client.get(SUBSCRIPTION, headers=headers).status_code == 200
    assert tenant_client.get(HISTORY_URL, headers=headers).status_code == 200
    assert tenant_client.put(
        MODULES_URL, json={"active_modules": ["documents"]}, headers=headers
    ).status_code == 200


def test_billing_read_alone_cannot_contract(
    session: Session, tenant_client: TestClient, managed
):
    """`billing:manage` does not follow from `billing:read`: the two are
    independent strings, as everywhere else in the catalogue. A condominium
    that wants its treasurer to see the plan without contracting needs exactly
    this split."""
    reader, _role = make_role_holder(session, ["billing:read"])
    headers = auth(reader, TENANT_A)

    assert tenant_client.get(SUBSCRIPTION, headers=headers).status_code == 200
    refused = tenant_client.put(
        MODULES_URL, json={"active_modules": []}, headers=headers
    )
    assert refused.status_code == 403
    assert refused.json()["detail"] == "The user doesn't have enough privileges"


def test_billing_manage_alone_reaches_the_page_and_the_read_refuses(
    session: Session, tenant_client: TestClient, managed
):
    """The documented degenerate configuration (§2.2): the frontend route rule
    is `{module: "billing"}`, which holds for *any* `billing:*`, so a
    manage-only holder reaches the page and the read endpoint is what refuses
    them. Documented rather than special-cased."""
    manager, _role = make_role_holder(session, ["billing:manage"])
    headers = auth(manager, TENANT_A)

    assert tenant_client.get(SUBSCRIPTION, headers=headers).status_code == 403
    assert tenant_client.put(
        MODULES_URL, json={"active_modules": ["documents"]}, headers=headers
    ).status_code == 200


def test_a_superuser_reaches_everything(
    session: Session, tenant_client: TestClient, managed
):
    """All ten routes: the three tenant-side ones through APRAS-47's
    whole-catalogue short-circuit, the seven operator ones through the flag."""
    superuser = make_superuser(session)
    plan = make_plan(session, name="Plano do Superusuário")

    assert tenant_client.get(
        SUBSCRIPTION, headers=auth(superuser, TENANT_A)
    ).status_code == 200
    assert tenant_client.get(
        HISTORY_URL, headers=auth(superuser, TENANT_A)
    ).status_code == 200
    assert tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["documents"]},
        headers=auth(superuser, TENANT_A),
    ).status_code == 200

    assert tenant_client.get("/api/v1/plans/", headers=auth(superuser)).status_code == 200
    assert tenant_client.post(
        "/api/v1/plans/", json={"name": "Novo"}, headers=auth(superuser)
    ).status_code == 201
    assert tenant_client.get(
        f"/api/v1/plans/{plan.id}", headers=auth(superuser)
    ).status_code == 200
    assert tenant_client.patch(
        f"/api/v1/plans/{plan.id}",
        json={"description": "x"},
        headers=auth(superuser),
    ).status_code == 200

    base = f"/api/v1/tenants/{TENANT_A}/subscription"
    assert tenant_client.get(base, headers=auth(superuser)).status_code == 200
    assert tenant_client.put(
        base, json={"plan_id": str(plan.id)}, headers=auth(superuser)
    ).status_code == 200
    assert tenant_client.put(
        f"{base}/courtesy",
        json={"courtesy_modules": ["finance"]},
        headers=auth(superuser),
    ).status_code == 200
