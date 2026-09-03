"""The install-wide plan catalogue (APRAS-40 §5.2, §6.2).

Four routes, all superuser-only, all on a **global** router: `plan` carries no
`tenant_id`, so there is no acting tenant to resolve and a tenant-scoped mount
would put a `get_current_superuser` guard on a tenant-scoped route -- exactly
what `test_tenant_admin.py::test_no_tenant_scoped_route_keeps_a_global_admin_guard`
forbids.

There is **no DELETE**, on purpose: `tenant_subscription.plan_id` is
`ON DELETE RESTRICT` and a plan a tenant is on must not vanish. Deactivation is
the operation, exactly as for `Tenant`.
"""

import uuid

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.permissions import CORE_MODULES, ROUTE_PERMISSIONS, UNGUARDED_ROUTES
from app.main import app
from app.models.plan import Plan
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    make_role_holder,
    make_superuser,
    make_tenant_admin,
)

PLANS = "/api/v1/plans/"

PLAN_ROUTES = (
    ("GET", "/api/v1/plans/"),
    ("POST", "/api/v1/plans/"),
    ("GET", "/api/v1/plans/{plan_id}"),
    ("PATCH", "/api/v1/plans/{plan_id}"),
)


@pytest.fixture(name="superuser")
def superuser_fixture(session: Session):
    return make_superuser(session)


def test_superuser_creates_and_lists_a_plan(
    tenant_client: TestClient, superuser
):
    """`included_modules` and `module_prices` come back sorted, so a `GET`
    after a `POST` is byte-stable."""
    created = tenant_client.post(
        PLANS,
        json={
            "name": "Plano Completo",
            "description": "Tudo incluído",
            "included_modules": ["finance", "assets", "finance"],
            "module_prices": {"finance": 49.0, "assets": 19.0},
            "base_price": 100.0,
        },
        headers=auth(superuser),
    )

    assert created.status_code == 201
    body = created.json()
    assert body["included_modules"] == ["assets", "finance"]
    assert list(body["module_prices"]) == ["assets", "finance"]
    assert body["currency"] == "BRL"
    assert body["is_active"] is True

    listed = tenant_client.get(PLANS, headers=auth(superuser))
    assert listed.status_code == 200
    assert [plan["name"] for plan in listed.json()] == ["Plano Completo"]

    one = tenant_client.get(
        f"/api/v1/plans/{body['id']}", headers=auth(superuser)
    )
    assert one.status_code == 200
    assert one.json() == body


def test_plan_rejects_an_unknown_module(tenant_client: TestClient, superuser):
    response = tenant_client.post(
        PLANS,
        json={"name": "Plano Ruim", "included_modules": ["not_a_module"]},
        headers=auth(superuser),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown module: 'not_a_module'"


@pytest.mark.parametrize("module", sorted(CORE_MODULES))
def test_plan_rejects_a_core_module(tenant_client: TestClient, superuser, module):
    """A plan cannot "include" what is always on. Four core modules now."""
    response = tenant_client.post(
        PLANS,
        json={"name": f"Plano {module}", "included_modules": [module]},
        headers=auth(superuser),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Core modules are always active: {module}"


def test_plan_rejects_a_price_for_an_uncovered_module(
    tenant_client: TestClient, superuser
):
    response = tenant_client.post(
        PLANS,
        json={
            "name": "Plano Torto",
            "included_modules": ["assets"],
            "module_prices": {"finance": 49.0},
        },
        headers=auth(superuser),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Priced modules must be included in the plan: finance"
    )


def test_plan_rejects_a_negative_price_and_a_bad_currency(
    tenant_client: TestClient, superuser
):
    """INERT values still have a shape: a negative price is a typo, not a
    discount, and the display layer formats against a three-letter code."""
    negative = tenant_client.post(
        PLANS,
        json={
            "name": "Plano Negativo",
            "included_modules": ["assets"],
            "module_prices": {"assets": -1.0},
        },
        headers=auth(superuser),
    )
    assert negative.status_code == 400
    assert "cannot be negative" in negative.json()["detail"]

    bad_currency = tenant_client.post(
        PLANS,
        json={"name": "Plano Moeda", "currency": "reais"},
        headers=auth(superuser),
    )
    assert bad_currency.status_code == 400
    assert "three uppercase letters" in bad_currency.json()["detail"]

    base = tenant_client.post(
        PLANS, json={"name": "Plano Base", "base_price": -5.0}, headers=auth(superuser)
    )
    assert base.status_code == 400
    assert base.json()["detail"] == "The base price cannot be negative"


def test_duplicate_plan_name_is_409(tenant_client: TestClient, superuser):
    """`plan.name` is globally unique for the same reason `tenant.name` is."""
    tenant_client.post(PLANS, json={"name": "Plano Único"}, headers=auth(superuser))

    duplicate = tenant_client.post(
        PLANS, json={"name": "Plano Único"}, headers=auth(superuser)
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A plan named 'Plano Único' already exists"


def test_patch_deactivates_a_plan_and_there_is_no_delete_route(
    tenant_client: TestClient, superuser
):
    created = tenant_client.post(
        PLANS,
        json={"name": "Plano Antigo", "included_modules": ["assets"]},
        headers=auth(superuser),
    ).json()

    patched = tenant_client.patch(
        f"/api/v1/plans/{created['id']}",
        json={"is_active": False, "description": "Descontinuado"},
        headers=auth(superuser),
    )

    assert patched.status_code == 200
    assert patched.json()["is_active"] is False
    assert patched.json()["description"] == "Descontinuado"
    # Deactivation is the operation that replaces a delete, so the deactivated
    # plan is still listed -- an operator has to be able to see and undo it.
    assert [plan["name"] for plan in tenant_client.get(
        PLANS, headers=auth(superuser)
    ).json()] == ["Plano Antigo"]

    live = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    assert ("DELETE", "/api/v1/plans/{plan_id}") not in live
    assert ("DELETE", "/api/v1/plans/{plan_id}") not in ROUTE_PERMISSIONS


def test_patch_revalidates_the_whole_plan(tenant_client: TestClient, superuser):
    """Prices are checked against the *resulting* module set, so narrowing a
    plan without dropping the price is a 400 rather than a silent orphan."""
    created = tenant_client.post(
        PLANS,
        json={
            "name": "Plano Estreitado",
            "included_modules": ["assets", "finance"],
            "module_prices": {"finance": 49.0},
        },
        headers=auth(superuser),
    ).json()

    narrowed = tenant_client.patch(
        f"/api/v1/plans/{created['id']}",
        json={"included_modules": ["assets"]},
        headers=auth(superuser),
    )

    assert narrowed.status_code == 400
    assert narrowed.json()["detail"] == (
        "Priced modules must be included in the plan: finance"
    )


def test_a_name_only_patch_does_not_rewrite_the_json_columns(
    session: Session, tenant_client: TestClient, superuser
):
    """Only the fields the body sent are written (round-1 review S-6).

    The two JSON columns are still *validated* together -- prices have to be
    checked against the resulting module set -- but a field absent from
    `model_dump(exclude_unset=True)` is not assigned.

    **What this case does and does not prove, stated because round 2 caught the
    round-1 version overstating it.** It asserts a real behavioural property:
    a name-only `PATCH` leaves both JSON columns byte-identical, including an
    un-normalised value written by hand or by an older revision -- so renaming
    a plan never silently re-sorts or dedupes its data.

    It does **not** discriminate the `exclude_unset` scoping, and no test can,
    because that scoping has no observable effect: the `else` branches below
    fall back to `plan.included_modules` / `plan.module_prices` *unvalidated*,
    so the value assigned is the value already stored, and SQLAlchemy compares
    those attributes by value on flush -- an equal-valued re-assignment never
    reaches the `UPDATE`. Round 2 measured both halves of that: the case passes
    with the scoping reverted, and the emitted statement is
    `UPDATE "plan" SET name=?, updated_at=?` either way. The scoping is a
    readability improvement, and it is documented as one in `PlanService`.

    The `widened -> 400` half at the end is a genuine pin and is the reason
    this case earns its place: validation still runs over the *resulting* plan
    even for fields the body did not send.
    """
    created = tenant_client.post(
        PLANS,
        json={
            "name": "Plano Estável",
            "included_modules": ["finance", "assets"],
            "module_prices": {"finance": 49.0},
        },
        headers=auth(superuser),
    ).json()

    # Written straight onto the row, bypassing the service's normalisation.
    session.expire_all()
    row = session.get(Plan, uuid.UUID(created["id"]))
    row.included_modules = ["finance", "assets", "finance"]
    session.add(row)
    session.commit()

    session.expire_all()
    modules_before = list(session.get(Plan, uuid.UUID(created["id"])).included_modules)
    assert modules_before == ["finance", "assets", "finance"]

    response = tenant_client.patch(
        f"/api/v1/plans/{created['id']}",
        json={"name": "Plano Renomeado"},
        headers=auth(superuser),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Plano Renomeado"
    session.expire_all()
    row = session.get(Plan, uuid.UUID(created["id"]))
    # Byte-identical, un-normalised: the body did not send it, so it was not
    # written. Without the fix this reads `["assets", "finance"]`.
    assert row.included_modules == modules_before
    assert row.module_prices == {"finance": 49.0}

    # ...and a body that *does* send them still normalises, so the scoping is
    # about what was omitted and never about skipping validation.
    widened = tenant_client.patch(
        f"/api/v1/plans/{created['id']}",
        json={"included_modules": ["projects", "assets", "assets"]},
        headers=auth(superuser),
    )
    assert widened.status_code == 400
    assert widened.json()["detail"] == (
        "Priced modules must be included in the plan: finance"
    )


def test_patch_rejects_a_duplicate_name(tenant_client: TestClient, superuser):
    tenant_client.post(PLANS, json={"name": "Plano A"}, headers=auth(superuser))
    other = tenant_client.post(
        PLANS, json={"name": "Plano B"}, headers=auth(superuser)
    ).json()

    response = tenant_client.patch(
        f"/api/v1/plans/{other['id']}",
        json={"name": "Plano A"},
        headers=auth(superuser),
    )

    assert response.status_code == 409


def test_a_tenant_admin_and_an_ordinary_user_get_403_on_every_plan_route(
    session: Session, tenant_client: TestClient, superuser
):
    """The catalogue is not a tenant-side surface: self-service plan change is
    out of scope, and `{anyOf: ["tenants:update"]}` would be exactly wrong --
    a tenant_admin holds it through the whole-catalogue short-circuit and the
    API answers 403 anyway."""
    plan = tenant_client.post(
        PLANS, json={"name": "Plano Fechado"}, headers=auth(superuser)
    ).json()
    tenant_admin = make_tenant_admin(session)
    director, _role = make_role_holder(
        session, ["billing:read", "billing:manage"]
    )

    for actor in (tenant_admin, director):
        headers = auth(actor, TENANT_A)
        assert tenant_client.get(PLANS, headers=headers).status_code == 403
        assert tenant_client.post(
            PLANS, json={"name": "x"}, headers=headers
        ).status_code == 403
        assert tenant_client.get(
            f"/api/v1/plans/{plan['id']}", headers=headers
        ).status_code == 403
        response = tenant_client.patch(
            f"/api/v1/plans/{plan['id']}", json={"name": "y"}, headers=headers
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "The user doesn't have enough privileges"


def test_unauthenticated_is_401(tenant_client: TestClient):
    assert tenant_client.get(PLANS).status_code == 401
    assert tenant_client.post(PLANS, json={"name": "x"}).status_code == 401


def test_unknown_plan_is_404(tenant_client: TestClient, superuser):
    missing = uuid.uuid4()

    response = tenant_client.get(f"/api/v1/plans/{missing}", headers=auth(superuser))

    assert response.status_code == 404
    assert response.json()["detail"] == f"Plan not found: {missing}"
    assert tenant_client.patch(
        f"/api/v1/plans/{missing}", json={"name": "x"}, headers=auth(superuser)
    ).status_code == 404


def test_the_four_plan_routes_are_unguarded_and_carry_no_permission():
    """Superuser-guarded routes mint no catalogue string (§6.4's convention).

    Minting four permissions whose only purpose is to be refused by
    `assert_can_grant` would cost 24 parity cells for nothing.
    """
    for key in PLAN_ROUTES:
        assert key in UNGUARDED_ROUTES, key
        assert key not in ROUTE_PERMISSIONS, key
