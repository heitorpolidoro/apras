"""Module bundles (APRAS-128): declaration, and the four writers that enforce it."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import permissions
from app.core.permissions import (
    CORE_MODULES,
    MODULE_BUNDLES,
    MODULES,
    bundle_of,
    split_bundles,
)
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    disabled_of,
    make_plan,
    make_superuser,
    make_tenant_admin,
    module_row,
    subscribe,
)

TENANT_MODULES = f"/api/v1/tenants/{TENANT_A}/modules"
COURTESY = f"/api/v1/tenants/{TENANT_A}/subscription/courtesy"
OWN_MODULES = "/api/v1/subscription/modules"
PLANS = "/api/v1/plans/"


def test_the_bundles_are_exactly_the_four_coupled_groups():
    assert {
        "tasks": {"tasks", "categories"},
        "reservations": {"reservations", "spaces"},
        "assets": {"assets", "inventory"},
        "visitors": {"visitors", "authorizations", "gate"},
    } == MODULE_BUNDLES
    for unbundled in ("assemblies", "votes", "uploads", "access_control"):
        assert bundle_of(unbundled) is None


def test_every_member_exists_no_overlap_no_core_no_singletons():
    seen: set[str] = set()
    for members in MODULE_BUNDLES.values():
        assert len(members) > 1
        assert members <= MODULES
        assert not members & CORE_MODULES
        assert not members & seen
        seen |= members


def test_split_bundles_names_the_missing_members():
    assert split_bundles({"tasks"}) == {"tasks": ["categories"]}
    assert split_bundles({"tasks", "categories", "finance"}) == {}
    assert split_bundles(set()) == {}


@pytest.mark.parametrize(
    ("bundles", "message"),
    [
        ({"x": frozenset({"tasks"})}, "at least two"),
        ({"x": frozenset({"tasks", "nope"})}, "unknown"),
        ({"x": frozenset({"tasks", "users"})}, "core"),
        (
            {
                "x": frozenset({"tasks", "categories"}),
                "y": frozenset({"tasks", "gate"}),
            },
            "two bundles",
        ),
    ],
)
def test_an_invalid_declaration_is_refused(bundles, message):
    with pytest.raises(ValueError, match=message):
        permissions._validate_bundles(bundles)


@pytest.fixture(name="superuser")
def superuser_fixture(session: Session):
    return make_superuser(session)


# -- PUT /tenants/{id}/modules ------------------------------------------------


def test_tenant_modules_put(tenant_client: TestClient, superuser, session):
    split = tenant_client.put(
        TENANT_MODULES,
        json={"disabled_modules": ["categories"]},
        headers=auth(superuser),
    )
    assert split.status_code == 400
    assert "tasks" in split.json()["detail"]
    assert disabled_of(session, TENANT_A) == []

    whole = tenant_client.put(
        TENANT_MODULES,
        json={"disabled_modules": ["tasks", "categories"]},
        headers=auth(superuser),
    )
    assert whole.status_code == 200
    assert disabled_of(session, TENANT_A) == ["categories", "tasks"]
    rows = {r["module"]: r["bundle"] for r in whole.json()["modules"]}
    assert rows["gate"] == "visitors"
    assert rows["finance"] is None


# -- PUT /subscription/modules ------------------------------------------------


def test_subscription_modules_put(tenant_client: TestClient, session):
    actor = make_tenant_admin(session)
    plan = make_plan(session, included=["tasks", "categories", "finance"])
    subscribe(session, tenant_id=TENANT_A, plan=plan, active=[])
    before = disabled_of(session, TENANT_A)

    split = tenant_client.put(
        OWN_MODULES, json={"active_modules": ["tasks"]}, headers=auth(actor, TENANT_A)
    )
    assert split.status_code == 400
    assert disabled_of(session, TENANT_A) == before

    whole = tenant_client.put(
        OWN_MODULES,
        json={"active_modules": ["tasks", "categories"]},
        headers=auth(actor, TENANT_A),
    )
    assert whole.status_code == 200
    assert module_row(whole.json(), "tasks")["is_active"] is True
    assert module_row(whole.json(), "tasks")["bundle"] == "tasks"
    assert module_row(whole.json(), "finance")["bundle"] is None


# -- PUT /tenants/{id}/subscription/courtesy ----------------------------------


def test_courtesy_whole_bundle_and_split(tenant_client: TestClient, superuser, session):
    plan = make_plan(session, included=["finance"])
    subscribe(session, tenant_id=TENANT_A, plan=plan, active=["finance"])
    before = disabled_of(session, TENANT_A)

    split = tenant_client.put(
        COURTESY, json={"courtesy_modules": ["tasks"]}, headers=auth(superuser)
    )
    assert split.status_code == 400
    assert disabled_of(session, TENANT_A) == before

    whole = tenant_client.put(
        COURTESY,
        json={"courtesy_modules": ["tasks", "categories"]},
        headers=auth(superuser),
    )
    assert whole.status_code == 200
    disabled = disabled_of(session, TENANT_A)
    assert "tasks" not in disabled
    assert "categories" not in disabled


def test_courtesy_of_one_member_while_the_plan_has_the_other(
    tenant_client: TestClient, superuser, session
):
    plan = make_plan(session, included=["categories"])
    subscribe(session, tenant_id=TENANT_A, plan=plan, active=[])
    before = disabled_of(session, TENANT_A)

    refused = tenant_client.put(
        COURTESY, json={"courtesy_modules": ["tasks"]}, headers=auth(superuser)
    )
    assert refused.status_code == 400
    assert disabled_of(session, TENANT_A) == before


def test_courtesy_of_one_member_passes_when_the_other_is_already_on(
    tenant_client: TestClient, superuser, session
):
    plan = make_plan(session, included=["categories"])
    subscribe(session, tenant_id=TENANT_A, plan=plan, active=["categories"])

    ok = tenant_client.put(
        COURTESY, json={"courtesy_modules": ["tasks"]}, headers=auth(superuser)
    )
    assert ok.status_code == 200


def test_revoking_one_member_of_a_courtesy_bundle_is_refused(
    tenant_client: TestClient, superuser, session
):
    plan = make_plan(session, included=["finance"])
    subscribe(
        session,
        tenant_id=TENANT_A,
        plan=plan,
        courtesy=["tasks", "categories"],
    )
    refused = tenant_client.put(
        COURTESY, json={"courtesy_modules": ["tasks"]}, headers=auth(superuser)
    )
    assert refused.status_code == 400


# -- plan create / update -----------------------------------------------------


def test_plan_create_and_update(tenant_client: TestClient, superuser):
    split = tenant_client.post(
        PLANS,
        json={"name": "Split", "included_modules": ["assets"]},
        headers=auth(superuser),
    )
    assert split.status_code == 400

    created = tenant_client.post(
        PLANS,
        json={"name": "Whole", "included_modules": ["assets", "inventory"]},
        headers=auth(superuser),
    )
    assert created.status_code == 201
    assert created.json()["included_modules"] == ["assets", "inventory"]
    url = f"{PLANS}{created.json()['id']}"

    bad = tenant_client.patch(
        url, json={"included_modules": ["assets", "gate"]}, headers=auth(superuser)
    )
    assert bad.status_code == 400

    good = tenant_client.patch(
        url,
        json={"included_modules": ["visitors", "authorizations", "gate"]},
        headers=auth(superuser),
    )
    assert good.status_code == 200
