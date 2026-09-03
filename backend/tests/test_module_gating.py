"""The composition of the module switch with the permission model (APRAS-39 §5).

*Access* requires `permission ∈ role bundles` **and**
`module_of(permission) ∉ tenant.disabled_modules`. The strip happens in
exactly one place — `deps.get_effective_permissions` — so route-level
`require_permission`, in-handler `has_permission`, the service-level checks
and `GET /api/v1/permissions/me` all follow from it with no second mechanism.

These cases assert that at the wire, on both guard shapes: `GET
/api/v1/finance/transactions` (an in-handler `has_permission`) and `DELETE
/api/v1/lots/{id}` (a route-level `require_permission`).
"""

import itertools
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api import deps
from app.core.permissions import PERMISSIONS, module_of
from app.core.security import create_access_token
from app.models.lot import Lot
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from tests.conftest import make_user

TENANT_A = DEFAULT_TENANT_ID

FINANCE_PERMISSIONS = frozenset(
    p for p in PERMISSIONS if module_of(p) == "finance"
)

_cpf_counter = itertools.count(1)


def _next_cpf() -> str:
    return str(next(_cpf_counter)).zfill(11)


def _make_user(
    session: Session, profile: str, tenant_id: uuid.UUID = TENANT_A, **kwargs
) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@modules.example.com",
        full_name=f"{profile} user",
        hashed_password="hash",
        profile=profile,
        tenant_id=tenant_id,
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


def _disable(session: Session, tenant_id: uuid.UUID, *modules: str) -> None:
    """Write `disabled_modules` straight onto the row.

    Deliberately not through `PUT /modules`: these cases are about the
    *strip*, and going through the API would make every one of them depend on
    §6's validation too. `test_tenant_modules_api.py` owns that surface.
    """
    tenant = session.get(Tenant, tenant_id)
    tenant.disabled_modules = list(modules)
    session.add(tenant)
    session.commit()


@pytest.fixture(name="resident")
def resident_fixture(session: Session) -> User:
    """A RESIDENT of tenant A. Their bundle carries `finance:read`."""
    user = _make_user(session, "RESIDENT", is_superuser=False)
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()
    return user


@pytest.fixture(name="lot_in_a")
def lot_in_a_fixture(session: Session) -> Lot:
    lot = Lot(block="A", lot_number="101", tenant_id=TENANT_A)
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


# ---------------------------------------------------------------------------
# The strip itself
# ---------------------------------------------------------------------------


def test_a_disabled_modules_permissions_leave_the_effective_set(
    session: Session, resident: User
):
    """`finance` off removes every `finance:*` and touches nothing else."""
    deps.tenant_context.set_acting_tenant(session, TENANT_A)
    before = deps.get_effective_permissions(resident, session)
    assert "finance:read" in before

    _disable(session, TENANT_A, "finance")
    after = deps.get_effective_permissions(resident, session)

    assert not (after & FINANCE_PERMISSIONS)
    assert after == before - FINANCE_PERMISSIONS


def test_no_acting_tenant_strips_nothing(session: Session, resident: User):
    """A bare `Session` (seed.py, Alembic, a unit test) resolves no tenant.

    The permissions that matter on those paths are the caller's own, so a
    module switch must never be the reason such a session grants *less*.
    """
    _disable(session, TENANT_A, "finance")

    assert deps.disabled_modules(session) == frozenset()
    assert "finance:read" in deps.get_effective_permissions(resident, session)


def test_an_absent_tenant_row_strips_nothing(session: Session, resident: User):
    """`get_current_tenant` guarantees the row exists on a real request."""
    deps.tenant_context.set_acting_tenant(session, uuid.uuid4())

    assert deps.disabled_modules(session) == frozenset()


def test_core_modules_cannot_be_stripped_even_by_a_hand_edited_row(
    session: Session, resident: User
):
    """`CORE_MODULES` is subtracted here rather than trusted from the row.

    The API refuses to write them (§6.3); this is the second line of defence,
    so a hand-edited row cannot lock a condominium out of its own user and
    role administration.
    """
    _disable(session, TENANT_A, "users", "roles", "tenants")
    deps.tenant_context.set_acting_tenant(session, TENANT_A)

    assert deps.disabled_modules(session) == frozenset()
    result = deps.get_effective_permissions(resident, session)
    assert {p for p in result if module_of(p) == "users"}
    assert {p for p in result if module_of(p) == "roles"}


# ---------------------------------------------------------------------------
# The wire: both guard shapes refuse
# ---------------------------------------------------------------------------


def test_a_disabled_module_endpoint_refuses_a_permitted_user(
    session: Session, tenant_client: TestClient, resident: User, lot_in_a: Lot
):
    """The in-handler check and the route-level guard both refuse.

    Nothing in the error path is touched: the refusal is byte-identical to
    the one a missing permission produces (§5.4).
    """
    admin = _make_user(session, "ADMINISTRATOR")
    session.add(UserTenantLink(user_id=admin.id, tenant_id=TENANT_A))
    session.commit()
    lot_id = lot_in_a.id

    _disable(session, TENANT_A, "finance", "lots")

    finance = tenant_client.get(
        "/api/v1/finance/transactions", headers=_auth(resident, TENANT_A)
    )
    assert finance.status_code == 403

    # `lots:delete` is a route-level `require_permission`; a tenant_admin
    # holds it through the whole-catalogue short-circuit, and is bounded by
    # the tenant's modules exactly like anybody else.
    tenant_admin = _make_user(session, "RESIDENT", is_superuser=False)
    session.add(
        UserTenantLink(
            user_id=tenant_admin.id, tenant_id=TENANT_A, is_tenant_admin=True
        )
    )
    session.commit()

    deleted = tenant_client.delete(
        f"/api/v1/lots/{lot_id}", headers=_auth(tenant_admin, TENANT_A)
    )
    assert deleted.status_code == 403
    assert deleted.json()["detail"] == "The user doesn't have enough privileges"


def test_permissions_me_omits_the_disabled_modules_permissions(
    session: Session, tenant_client: TestClient, resident: User
):
    """`/permissions/me` is stripped, and *says* which modules are off (§7)."""
    _disable(session, TENANT_A, "finance")

    response = tenant_client.get(
        "/api/v1/permissions/me", headers=_auth(resident, TENANT_A)
    )

    assert response.status_code == 200
    body = response.json()
    assert not [p for p in body["permissions"] if module_of(p) == "finance"]
    assert body["disabled_modules"] == ["finance"]


def test_permissions_me_reports_an_empty_list_by_default(
    session: Session, tenant_client: TestClient, resident: User
):
    """A fresh tenant is all-on, so the field is `[]` and nothing is stripped."""
    response = tenant_client.get(
        "/api/v1/permissions/me", headers=_auth(resident, TENANT_A)
    )

    assert response.status_code == 200
    assert response.json()["disabled_modules"] == []
    assert "finance:read" in response.json()["permissions"]


# ---------------------------------------------------------------------------
# §5.3 -- the four actor classes
# ---------------------------------------------------------------------------


def test_a_tenant_admin_is_bounded_by_the_tenants_modules(
    session: Session, tenant_client: TestClient
):
    """"Everything *this tenant* has", never more than the tenant has."""
    user = _make_user(session, "RESIDENT", is_superuser=False)
    session.add(
        UserTenantLink(user_id=user.id, tenant_id=TENANT_A, is_tenant_admin=True)
    )
    session.commit()
    _disable(session, TENANT_A, "finance")

    response = tenant_client.get(
        "/api/v1/permissions/me", headers=_auth(user, TENANT_A)
    )
    assert set(response.json()["permissions"]) == PERMISSIONS - FINANCE_PERMISSIONS
    assert len(FINANCE_PERMISSIONS) == 11

    refused = tenant_client.get(
        "/api/v1/finance/transactions", headers=_auth(user, TENANT_A)
    )
    assert refused.status_code == 403


def test_a_superuser_keeps_a_disabled_modules_permissions(
    session: Session, tenant_client: TestClient
):
    """The deliberate exemption (§5.3), pinned so it reads as a decision.

    The global operator is the one who *sets* the switch and must be able to
    inspect and repair a tenant whose module they just turned off. The flag
    is answered before any tenant is resolved (F3), and the switch is a
    commercial packaging control over a tenant's users, not a data boundary.
    """
    superuser = _make_user(session, "RESIDENT", is_superuser=True)
    session.add(UserTenantLink(user_id=superuser.id, tenant_id=TENANT_A))
    session.commit()
    _disable(session, TENANT_A, "finance")

    response = tenant_client.get(
        "/api/v1/permissions/me", headers=_auth(superuser, TENANT_A)
    )
    assert set(response.json()["permissions"]) == PERMISSIONS
    # Still *told* which modules are off, which is what lets a client
    # distinguish without parsing an error string.
    assert response.json()["disabled_modules"] == ["finance"]

    allowed = tenant_client.get(
        "/api/v1/finance/transactions", headers=_auth(superuser, TENANT_A)
    )
    assert allowed.status_code == 200


# ---------------------------------------------------------------------------
# Non-destructiveness and isolation
# ---------------------------------------------------------------------------


def test_re_enabling_restores_access_with_no_data_change(
    session: Session, tenant_client: TestClient, resident: User
):
    """Toggling edits no role row: "inertes" is exactly what the strip produces.

    Asserted against the **database**, not the API: reading the bundle back
    through `GET /api/v1/roles/{id}` would prove nothing, because that
    response is assembled from the same ORM object and would hide a rewrite
    that happened to round-trip.
    """
    role = resident.roles[0]
    role_id = role.id
    before = list(role.permissions)

    _disable(session, TENANT_A, "finance")
    refused = tenant_client.get(
        "/api/v1/finance/transactions", headers=_auth(resident, TENANT_A)
    )
    assert refused.status_code == 403

    _disable(session, TENANT_A)
    allowed = tenant_client.get(
        "/api/v1/finance/transactions", headers=_auth(resident, TENANT_A)
    )
    assert allowed.status_code == 200

    session.expire_all()
    reread = session.exec(select(Role).where(Role.id == role_id)).one()
    assert reread.permissions == before
    assert len(reread.permissions) == len(before)


def test_module_isolation_between_tenants(
    session: Session, tenant_client: TestClient, tenant_b: Tenant
):
    """One user, two tenants, one header of difference (§8).

    Tenant A's configuration can no more reach tenant B than A's roles can:
    the acting tenant comes from `session.info` (APRAS-42).
    """
    user = _make_user(session, "RESIDENT", is_superuser=False)
    role_b = Role(
        name="Morador B", tenant_id=tenant_b.id, permissions=["finance:read"]
    )
    session.add(role_b)
    session.commit()
    user.roles.append(role_b)
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_b.id))
    session.add(user)
    session.commit()
    _disable(session, TENANT_A, "finance")

    in_a = tenant_client.get(
        "/api/v1/finance/transactions", headers=_auth(user, TENANT_A)
    )
    assert in_a.status_code == 403
    me_in_a = tenant_client.get(
        "/api/v1/permissions/me", headers=_auth(user, TENANT_A)
    )
    assert "finance:read" not in me_in_a.json()["permissions"]

    in_b = tenant_client.get(
        "/api/v1/finance/transactions", headers=_auth(user, tenant_b.id)
    )
    assert in_b.status_code == 200
    me_in_b = tenant_client.get(
        "/api/v1/permissions/me", headers=_auth(user, tenant_b.id)
    )
    assert "finance:read" in me_in_b.json()["permissions"]
    assert me_in_b.json()["disabled_modules"] == []

    session.expire_all()
    assert session.get(Tenant, tenant_b.id).disabled_modules == []
