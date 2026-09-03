"""The tenant-side subscription area (APRAS-40 §5.1, §4.6, §4.7, §6.4).

Three routes, no `{tenant_id}` in any of them: the subject is the acting
tenant, resolved from `X-Tenant-Id`. A path parameter would be a second,
forgeable source of truth and would hand a tenant_admin of A a way to name B.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.permissions import MODULES, ROUTE_PERMISSIONS
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    disabled_of,
    history_of,
    make_plan,
    make_superuser,
    make_tenant_admin,
    module_row,
    subscribe,
)

SUBSCRIPTION = "/api/v1/subscription"
MODULES_URL = "/api/v1/subscription/modules"
HISTORY_URL = "/api/v1/subscription/history"


@pytest.fixture(name="actor")
def actor_fixture(session: Session):
    """A tenant_admin of A: holds `billing:*` with **no special case** in the
    code, by APRAS-47's whole-catalogue short-circuit plus `billing` being
    core so APRAS-39's strip never removes it."""
    return make_tenant_admin(session)


# ---------------------------------------------------------------------------
# §4.6 -- no subscription
# ---------------------------------------------------------------------------


def test_get_without_a_subscription_is_200_and_unmanaged(
    tenant_client: TestClient, actor
):
    """Today's all-on behaviour is preserved; adopting billing is opt-in."""
    response = tenant_client.get(SUBSCRIPTION, headers=auth(actor, TENANT_A))

    assert response.status_code == 200
    body = response.json()
    assert body["plan"] is None
    assert body["status"] is None
    assert body["estimated_monthly_total"] is None
    assert body["currency"] is None
    assert len(body["modules"]) == len(MODULES)
    assert [row["module"] for row in body["modules"]] == sorted(MODULES)

    for row in body["modules"]:
        # `can_contract` is false for **every** module, core or not: the
        # contracting PUT is a 404 here, and a true would promise a button
        # that cannot work (§4.6).
        assert row["can_contract"] is False
        assert row["in_plan"] is False
        assert row["courtesy"] is False
        assert row["monthly_price"] is None
        assert row["source"] == ("CORE" if row["is_core"] else "UNMANAGED")


def test_history_without_a_subscription_is_an_empty_list(
    tenant_client: TestClient, actor
):
    response = tenant_client.get(HISTORY_URL, headers=auth(actor, TENANT_A))

    assert response.status_code == 200
    assert response.json() == []


def test_put_modules_without_a_subscription_is_404(tenant_client: TestClient, actor):
    """Contracting is meaningless without one, and a history row would have
    nowhere to live."""
    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["finance"]},
        headers=auth(actor, TENANT_A),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "This tenant has no subscription"


# ---------------------------------------------------------------------------
# §4.4 (a) -- contracting and cancelling
# ---------------------------------------------------------------------------


@pytest.fixture(name="managed")
def managed_fixture(session: Session):
    """Tenant A on a plan covering `finance` and `documents`, both inactive.

    Nothing is active to start with, so contracting is what turns a module on
    -- which is what makes the contracting screen meaningful (§4.4 b step 3).
    """
    plan = make_plan(
        session,
        name="Plano Básico",
        included=["finance", "documents"],
        prices={"finance": 49.0},
        base_price=100.0,
    )
    return subscribe(session, tenant_id=TENANT_A, plan=plan, active=[])


def test_contracting_a_covered_module_activates_it(
    session: Session, tenant_client: TestClient, actor, managed
):
    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["finance"]},
        headers=auth(actor, TENANT_A),
    )

    assert response.status_code == 200
    assert module_row(response.json(), "finance")["is_active"] is True
    assert module_row(response.json(), "finance")["source"] == "PLAN"
    assert "finance" not in disabled_of(session, TENANT_A)

    permissions = tenant_client.get(
        "/api/v1/permissions/me", headers=auth(actor, TENANT_A)
    ).json()
    assert {p for p in permissions["permissions"] if p.startswith("finance:")}


def test_cancelling_a_module_deactivates_it(
    session: Session, tenant_client: TestClient, actor, managed
):
    tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["finance"]},
        headers=auth(actor, TENANT_A),
    )

    response = tenant_client.put(
        MODULES_URL, json={"active_modules": []}, headers=auth(actor, TENANT_A)
    )

    assert response.status_code == 200
    assert module_row(response.json(), "finance")["is_active"] is False
    assert module_row(response.json(), "finance")["source"] is None
    assert "finance" in disabled_of(session, TENANT_A)

    refused = tenant_client.get(
        "/api/v1/finance/categories", headers=auth(actor, TENANT_A)
    )
    assert refused.status_code == 403


def test_contracting_an_uncovered_module_is_400(
    session: Session, tenant_client: TestClient, actor, managed
):
    """The row is **unchanged**: both validations run before any write."""
    before = disabled_of(session, TENANT_A)

    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["purchases", "finance", "assets"]},
        headers=auth(actor, TENANT_A),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Modules not covered by the subscription: assets, purchases"
    )
    assert disabled_of(session, TENANT_A) == before


def test_an_unknown_module_string_is_400(tenant_client: TestClient, actor, managed):
    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["not_a_module"]},
        headers=auth(actor, TENANT_A),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown module: 'not_a_module'"


def test_core_modules_in_the_body_are_ignored(
    session: Session, tenant_client: TestClient, actor, managed
):
    """`billing` in `active_modules` is simply true, so it is a 200 no-op.

    APRAS-39's `PUT /tenants/{id}/modules` rejects a core module because it
    appears in the *disabled* list; here it appears in the *active* list.
    """
    before = disabled_of(session, TENANT_A)

    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["billing", "users"]},
        headers=auth(actor, TENANT_A),
    )

    assert response.status_code == 200
    assert disabled_of(session, TENANT_A) == before
    assert module_row(response.json(), "billing")["is_active"] is True
    assert module_row(response.json(), "billing")["source"] == "CORE"


def test_a_no_op_put_writes_no_history_row(
    session: Session, tenant_client: TestClient, actor, managed
):
    """Idempotence is what lets the UI re-save safely."""
    tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["finance"]},
        headers=auth(actor, TENANT_A),
    )
    after_first = len(history_of(session, managed.id))

    response = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["finance"]},
        headers=auth(actor, TENANT_A),
    )

    assert response.status_code == 200
    assert after_first == 1
    assert len(history_of(session, managed.id)) == 1


# ---------------------------------------------------------------------------
# §4.7 -- source priority; §6.4 -- the inert total
# ---------------------------------------------------------------------------


def test_source_priority_is_plan_over_courtesy(
    session: Session, tenant_client: TestClient, actor
):
    """A module in both sets reads `"PLAN"` -- deterministic, top to bottom."""
    plan = make_plan(session, included=["finance"], prices={"finance": 49.0})
    subscribe(session, tenant_id=TENANT_A, plan=plan, courtesy=["finance"])

    body = tenant_client.get(SUBSCRIPTION, headers=auth(actor, TENANT_A)).json()
    row = module_row(body, "finance")

    assert row["in_plan"] is True
    assert row["courtesy"] is True
    assert row["source"] == "PLAN"


def test_contracting_a_module_raises_the_estimated_total(
    tenant_client: TestClient, actor, managed
):
    """`estimated_monthly_total` moves by exactly that module's price -- the
    board's "ajustando o que é cobrado", satisfied without charging anything."""
    before = tenant_client.get(SUBSCRIPTION, headers=auth(actor, TENANT_A)).json()
    assert module_row(before, "finance")["is_active"] is False
    assert before["estimated_monthly_total"] == 100.0
    assert before["currency"] == "BRL"

    after = tenant_client.put(
        MODULES_URL,
        json={"active_modules": ["finance"]},
        headers=auth(actor, TENANT_A),
    ).json()

    assert after["estimated_monthly_total"] == 149.0
    assert module_row(after, "finance")["monthly_price"] == 49.0


def test_a_courtesy_module_is_free(session: Session, tenant_client: TestClient, actor):
    """Courtesy is excluded from the total -- that is what "cortesia" means,
    and it is the second, independent way a courtesy grant is distinguishable
    from a contracted one."""
    plan = make_plan(
        session,
        included=["documents"],
        prices={"documents": 10.0},
        base_price=100.0,
    )
    subscribe(session, tenant_id=TENANT_A, plan=plan, courtesy=["finance"])

    body = tenant_client.get(SUBSCRIPTION, headers=auth(actor, TENANT_A)).json()

    assert module_row(body, "finance")["is_active"] is True
    assert module_row(body, "finance")["source"] == "COURTESY"
    assert module_row(body, "documents")["is_active"] is True
    # 100 base + 10 for the contracted `documents`; `finance` adds nothing.
    assert body["estimated_monthly_total"] == 110.0


# ---------------------------------------------------------------------------
# §9.1 -- the route mapping
# ---------------------------------------------------------------------------


def test_the_three_tenant_routes_are_route_mapped():
    """The exact `ROUTE_PERMISSIONS` keys and values of §9.1.

    Route templates are what FastAPI yields, not what a table guesses; these
    are the strings printed off `route.path` and the frontend writes them
    verbatim (a 307 would drop `X-Tenant-Id`).
    """
    assert ROUTE_PERMISSIONS[("GET", "/api/v1/subscription")] == "billing:read"
    assert (
        ROUTE_PERMISSIONS[("GET", "/api/v1/subscription/history")] == "billing:read"
    )
    assert (
        ROUTE_PERMISSIONS[("PUT", "/api/v1/subscription/modules")]
        == "billing:manage"
    )


def test_unauthenticated_is_401(tenant_client: TestClient):
    for method, url in (
        ("get", SUBSCRIPTION),
        ("get", HISTORY_URL),
        ("put", MODULES_URL),
    ):
        response = getattr(tenant_client, method)(url)
        assert response.status_code == 401, url


def test_a_superuser_of_another_tenant_cannot_name_this_one(
    session: Session, tenant_client: TestClient, tenant_b
):
    """There is no `{tenant_id}` to name: the subject is `X-Tenant-Id`, and
    `get_current_tenant` refuses a tenant the caller is not a member of."""
    superuser = make_superuser(session, tenant_id=tenant_b.id)

    response = tenant_client.get(SUBSCRIPTION, headers=auth(superuser, tenant_b.id))
    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(tenant_b.id)
