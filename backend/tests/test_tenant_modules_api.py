"""The superuser module switch: `GET`/`PUT /api/v1/tenants/{id}/modules` (§6).

`PUT`, not `PATCH`: the body is the *complete* desired state, so the
operation is idempotent, has no partial-update ambiguity and matches the one
checkbox list / one Save screen it drives. The response is the same body
`GET` returns, so the client re-renders from the server's answer.

Both routes are guarded by `deps.get_current_superuser` and map to **no**
catalogue permission — the convention APRAS-49 §8.4 established for
`PATCH /api/v1/users/{user_id}/superuser`, for its reason: minting catalogue
strings whose only purpose is to be refused by `assert_can_grant` would cost
12 parity cells that cannot exist at the baseline sha.
"""

import itertools
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.permissions import (
    CORE_MODULES,
    MODULES,
    ROUTE_PERMISSIONS,
    UNGUARDED_ROUTES,
)
from app.core.security import create_access_token
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from tests.conftest import make_user
from tests.test_tenant_route_scope import GLOBAL_ROUTES

TENANT_A = DEFAULT_TENANT_ID
MODULES_ROUTES = (
    ("GET", "/api/v1/tenants/{tenant_id}/modules"),
    ("PUT", "/api/v1/tenants/{tenant_id}/modules"),
)

_cpf_counter = itertools.count(1)


def _next_cpf() -> str:
    return str(next(_cpf_counter)).zfill(11)


def _make_user(session: Session, profile: str, **kwargs) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@switch.example.com",
        full_name=f"{profile} user",
        hashed_password="hash",
        profile=profile,
        cpf=_next_cpf(),
        **kwargs,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _auth(user: User, tenant_id=None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


def _url(tenant_id) -> str:
    return f"/api/v1/tenants/{tenant_id}/modules"


@pytest.fixture(name="superuser")
def superuser_fixture(session: Session) -> User:
    user = _make_user(session, "ADMINISTRATOR", is_superuser=True)
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()
    return user


@pytest.fixture(name="tenant_admin")
def tenant_admin_fixture(session: Session) -> User:
    """The tenant_admin of tenant A — the very tenant being written."""
    user = _make_user(session, "RESIDENT", is_superuser=False)
    session.add(
        UserTenantLink(user_id=user.id, tenant_id=TENANT_A, is_tenant_admin=True)
    )
    session.commit()
    return user


@pytest.fixture(name="ordinary")
def ordinary_fixture(session: Session) -> User:
    user = _make_user(session, "RESIDENT", is_superuser=False)
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()
    return user


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_get_lists_every_module_with_its_state(
    tenant_client: TestClient, superuser: User
):
    """All 28 rows, sorted by `module`, all active for a fresh tenant.

    Storage is negative (`[]` is "everything on") but the *read* is positive:
    the active set is enumerable per tenant, which is what ER-1 asks for.
    """
    response = tenant_client.get(_url(TENANT_A), headers=_auth(superuser))

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == str(TENANT_A)
    rows = body["modules"]
    assert len(rows) == 28
    assert [row["module"] for row in rows] == sorted(MODULES)
    assert all(row["is_active"] for row in rows)
    assert {row["module"] for row in rows if row["is_core"]} == CORE_MODULES


def test_put_disables_and_get_reflects_it(
    session: Session, tenant_client: TestClient, superuser: User
):
    response = tenant_client.put(
        _url(TENANT_A),
        headers=_auth(superuser),
        json={"disabled_modules": ["finance"]},
    )

    assert response.status_code == 200
    states = {row["module"]: row["is_active"] for row in response.json()["modules"]}
    assert states["finance"] is False
    assert states["tasks"] is True

    follow_up = tenant_client.get(_url(TENANT_A), headers=_auth(superuser))
    assert {
        row["module"] for row in follow_up.json()["modules"] if not row["is_active"]
    } == {"finance"}

    session.expire_all()
    assert session.get(Tenant, TENANT_A).disabled_modules == ["finance"]


def test_put_is_declarative_and_reenables(
    tenant_client: TestClient, superuser: User
):
    """The body is the complete desired state, so `[]` is a full re-enable."""
    tenant_client.put(
        _url(TENANT_A),
        headers=_auth(superuser),
        json={"disabled_modules": ["finance", "assets"]},
    )

    response = tenant_client.put(
        _url(TENANT_A), headers=_auth(superuser), json={"disabled_modules": []}
    )

    assert response.status_code == 200
    assert all(row["is_active"] for row in response.json()["modules"])


def test_put_deduplicates_and_sorts(
    session: Session, tenant_client: TestClient, superuser: User
):
    """Duplicates collapse silently; the stored list is canonical."""
    response = tenant_client.put(
        _url(TENANT_A),
        headers=_auth(superuser),
        json={"disabled_modules": ["finance", "finance", "assets"]},
    )

    assert response.status_code == 200
    session.expire_all()
    assert session.get(Tenant, TENANT_A).disabled_modules == ["assets", "finance"]


def test_a_new_tenant_starts_with_every_module_active(
    session: Session, tenant_client: TestClient, superuser: User
):
    """The `server_default` *is* the backfill: no seeding, no data step."""
    created = tenant_client.post(
        "/api/v1/tenants",
        headers=_auth(superuser),
        json={"name": "Condomínio Novo"},
    )
    assert created.status_code == 201
    tenant_id = uuid.UUID(created.json()["id"])

    response = tenant_client.get(_url(tenant_id), headers=_auth(superuser))

    assert response.status_code == 200
    assert len(response.json()["modules"]) == 28
    assert all(row["is_active"] for row in response.json()["modules"])
    session.expire_all()
    assert session.get(Tenant, tenant_id).disabled_modules == []


def test_the_switch_writes_only_the_named_tenant(
    session: Session, tenant_client: TestClient, superuser: User, tenant_b: Tenant
):
    """Writing A leaves B alone.

    The `tenant_id_field` default cannot apply here — `tenant` is not a
    scoped model — but the assertion is cheap and closes the class of bug.
    """
    tenant_b_id = tenant_b.id

    tenant_client.put(
        _url(TENANT_A),
        headers=_auth(superuser),
        json={"disabled_modules": ["finance"]},
    )

    session.expire_all()
    assert session.get(Tenant, tenant_b_id).disabled_modules == []


def test_the_read_agrees_with_the_strip_on_a_hand_edited_row(
    session: Session, tenant_client: TestClient, superuser: User
):
    """A core module in the row reads as **active**, because it is enforced so.

    `deps.disabled_modules` subtracts `CORE_MODULES` before enforcing, so a
    hand-edited row containing `"users"` strips nothing. If this read did not
    subtract it too, the operator's diagnostic view would report `users` as
    inactive while enforcement correctly ignored it -- the two would disagree
    in exactly the scenario
    `test_module_gating.test_core_modules_cannot_be_stripped_even_by_a_hand_edited_row`
    exists to cover.
    """
    tenant = session.get(Tenant, TENANT_A)
    tenant.disabled_modules = ["users", "roles", "finance"]
    session.add(tenant)
    session.commit()

    response = tenant_client.get(_url(TENANT_A), headers=_auth(superuser))

    assert response.status_code == 200
    inactive = {
        row["module"] for row in response.json()["modules"] if not row["is_active"]
    }
    assert inactive == {"finance"}


# ---------------------------------------------------------------------------
# §6.3 -- validation, both 400
# ---------------------------------------------------------------------------


def test_put_rejects_an_unknown_module(
    session: Session, tenant_client: TestClient, superuser: User
):
    """400, and the detail names the offending string. The row is untouched.

    Deliberately **not** a Pydantic `field_validator`: a schema-level
    rejection is answered 422 by FastAPI's `RequestValidationError` handler,
    and ER-2 pins 400. The schema validates *shape*; the service validates
    *vocabulary*, which is where the catalogue lives.
    """
    response = tenant_client.put(
        _url(TENANT_A),
        headers=_auth(superuser),
        json={"disabled_modules": ["financee"]},
    )

    assert response.status_code == 400
    assert "financee" in response.json()["detail"]
    session.expire_all()
    assert session.get(Tenant, TENANT_A).disabled_modules == []


@pytest.mark.parametrize("module", sorted(CORE_MODULES))
def test_put_rejects_a_core_module(
    session: Session, tenant_client: TestClient, superuser: User, module: str
):
    """Identity, membership and the authorization vocabulary stay on."""
    response = tenant_client.put(
        _url(TENANT_A),
        headers=_auth(superuser),
        json={"disabled_modules": [module]},
    )

    assert response.status_code == 400
    assert module in response.json()["detail"]
    session.expire_all()
    assert session.get(Tenant, TENANT_A).disabled_modules == []


def test_the_rejection_is_atomic_over_a_mixed_payload(
    session: Session, tenant_client: TestClient, superuser: User
):
    """Raised before the column assignment and before any commit."""
    response = tenant_client.put(
        _url(TENANT_A),
        headers=_auth(superuser),
        json={"disabled_modules": ["finance", "users"]},
    )

    assert response.status_code == 400
    session.expire_all()
    assert session.get(Tenant, TENANT_A).disabled_modules == []


def test_an_unknown_tenant_outranks_an_unknown_module(
    tenant_client: TestClient, superuser: User
):
    """404 wins over 400 when both are wrong (suggestion S7).

    `set_modules` resolves the tenant first, exactly as every other
    `TenantService` write does, so "which tenant" is answered before "which
    modules" — and an unknown tenant never leaks a vocabulary hint.
    """
    response = tenant_client.put(
        _url(uuid.uuid4()),
        headers=_auth(superuser),
        json={"disabled_modules": ["financee", "users"]},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Who may reach it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "put"])
def test_a_tenant_admin_cannot_read_or_write_the_switch(
    tenant_client: TestClient, tenant_admin: User, method: str
):
    """403 even for the tenant they administer: the switch is written from
    *outside* the tenant, on a global route that resolves no acting tenant."""
    call = getattr(tenant_client, method)
    kwargs = {"json": {"disabled_modules": []}} if method == "put" else {}

    response = call(_url(TENANT_A), headers=_auth(tenant_admin, TENANT_A), **kwargs)

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.parametrize("method", ["get", "put"])
def test_an_ordinary_user_cannot_read_or_write_the_switch(
    tenant_client: TestClient, ordinary: User, method: str
):
    call = getattr(tenant_client, method)
    kwargs = {"json": {"disabled_modules": []}} if method == "put" else {}

    response = call(_url(TENANT_A), headers=_auth(ordinary, TENANT_A), **kwargs)

    assert response.status_code == 403


@pytest.mark.parametrize("method", ["get", "put"])
def test_an_unauthenticated_caller_gets_401(
    tenant_client: TestClient, method: str
):
    call = getattr(tenant_client, method)
    kwargs = {"json": {"disabled_modules": []}} if method == "put" else {}

    response = call(_url(TENANT_A), **kwargs)

    assert response.status_code == 401


@pytest.mark.parametrize("method", ["get", "put"])
def test_unknown_tenant_is_404(
    tenant_client: TestClient, superuser: User, method: str
):
    call = getattr(tenant_client, method)
    kwargs = {"json": {"disabled_modules": []}} if method == "put" else {}

    response = call(_url(uuid.uuid4()), headers=_auth(superuser), **kwargs)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# §6.4 -- route accounting
# ---------------------------------------------------------------------------


def test_the_routes_are_unguarded_and_global():
    """No catalogue permission, no acting tenant, and still both allowlists.

    The *property* is what this case is about and it has not moved: these two
    routes map to no catalogue permission and depend on no acting tenant. The
    three totals below have moved, because APRAS-40 adds three
    permission-guarded routes and seven superuser-only ones -- and
    `tests/data/parity_matrix_baseline.json` stays byte-identical at 1080
    cells all the same, because the 18 new cells live in the additive
    `parity_matrix_baseline_40.json` (APRAS-40 §9.2).
    """
    for key in MODULES_ROUTES:
        assert key in UNGUARDED_ROUTES
        assert key in GLOBAL_ROUTES
        assert key not in ROUTE_PERMISSIONS

    assert len(ROUTE_PERMISSIONS) == 201
    # 23/28 since APRAS-52's operator-side subscription-history read, which
    # joins both allowlists and neither adds a mapping nor a parity cell.
    assert len(UNGUARDED_ROUTES) == 23
    assert len(GLOBAL_ROUTES) == 28
