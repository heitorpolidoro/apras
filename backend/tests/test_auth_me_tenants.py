"""`GET /api/v1/auth/me` returns the caller's own memberships (APRAS-38 §3).

The frontend tenant switcher needs two things at boot that no single global
route provided before: the tenants the caller may act in (already
`GET /api/v1/tenants`) and, per membership, whether the caller holds the
`is_tenant_admin` capability there. This module pins the second one onto
`/auth/me`, which `AuthContext` already calls.

`/auth/me` stays on the global scope allowlist, so these assertions are about
the *caller's* membership graph and never about an acting tenant — hence
`test_me_ignores_tenant_header`.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.enums import UserRole
from app.models.tenant import (
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
    Tenant,
    UserTenantLink,
)
from app.models.user import User
from app.models.user_type import UserType

_CPF_COUNTER = iter(range(20_000, 99_999))


def _auth(user: User, tenant_id=None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


def _make_user(
    session: Session,
    email: str,
    role: UserRole = UserRole.RESIDENT,
    user_types: list[UserType] | None = None,
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=email.split("@", maxsplit=1)[0],
        hashed_password=get_password_hash("password"),
        role=role,
        cpf=f"9{next(_CPF_COUNTER):010d}"[:11],
        user_types=user_types or [],
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="tenant_alpha")
def tenant_alpha_fixture(session: Session):
    """A tenant whose name sorts before the default tenant's."""
    tenant = Tenant(name="Alpha Condominium")
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def test_me_returns_single_membership(session: Session, client: TestClient):
    """A user linked only to the default tenant gets exactly one entry."""
    user = _make_user(session, "me-single@test.com")
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    response = client.get("/api/v1/auth/me", headers=_auth(user))

    assert response.status_code == 200
    assert response.json()["tenants"] == [
        {
            "tenant_id": str(DEFAULT_TENANT_ID),
            "name": DEFAULT_TENANT_NAME,
            "is_active": True,
            "is_tenant_admin": False,
        }
    ]


def test_me_returns_both_memberships_ordered_by_name(
    session: Session, client: TestClient, tenant_alpha: Tenant
):
    """A dual-membership user gets 2 entries ordered by tenant name.

    The order is what makes "first active membership" of the frontend
    pre-selection ladder deterministic, so it is asserted, not incidental:
    "Alpha Condominium" < "Condomínio Padrão".
    """
    user = _make_user(session, "me-dual@test.com")
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_alpha.id))
    session.commit()

    response = client.get("/api/v1/auth/me", headers=_auth(user))

    assert response.status_code == 200
    assert [t["name"] for t in response.json()["tenants"]] == [
        "Alpha Condominium",
        DEFAULT_TENANT_NAME,
    ]
    assert [t["tenant_id"] for t in response.json()["tenants"]] == [
        str(tenant_alpha.id),
        str(DEFAULT_TENANT_ID),
    ]


def test_me_reports_is_tenant_admin_per_membership(
    session: Session, client: TestClient, tenant_alpha: Tenant
):
    """The capability is per membership, not per user: True in A, False in B."""
    user = _make_user(session, "me-syndic@test.com")
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=tenant_alpha.id, is_tenant_admin=True
        )
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    response = client.get("/api/v1/auth/me", headers=_auth(user))

    assert response.status_code == 200
    by_id = {t["tenant_id"]: t["is_tenant_admin"] for t in response.json()["tenants"]}
    assert by_id[str(tenant_alpha.id)] is True
    assert by_id[str(DEFAULT_TENANT_ID)] is False


def test_me_returns_empty_tenants_for_user_without_memberships(
    session: Session, client: TestClient
):
    """Zero memberships is `[]` and 200 — never an error, never a synthesised row.

    A zero-membership user must keep the backend's own header-less fallback
    rather than a client-invented default-tenant entry.
    """
    user = _make_user(session, "me-orphan@test.com")

    response = client.get("/api/v1/auth/me", headers=_auth(user))

    assert response.status_code == 200
    assert response.json()["tenants"] == []


def test_me_keeps_existing_fields(session: Session, client: TestClient):
    """Today's `/auth/me` body is unchanged; `tenants` is purely additive."""
    user_type = UserType(name="Me Fields Type", allowed_menus=["tasks"])
    session.add(user_type)
    session.commit()
    user = _make_user(
        session, "me-fields@test.com", UserRole.DIRECTOR, user_types=[user_type]
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    body = client.get("/api/v1/auth/me", headers=_auth(user)).json()

    assert body["email"] == "me-fields@test.com"
    assert body["role"] == UserRole.DIRECTOR.value
    assert body["username"] == "me-fields"
    assert [ut["name"] for ut in body["user_types"]] == ["Me Fields Type"]
    assert body["is_active"] is True
    assert body["cpf"] == user.cpf


def test_me_ignores_tenant_header(
    session: Session, client: TestClient, tenant_alpha: Tenant
):
    """The route is global: `X-Tenant-Id` cannot narrow or alter the body."""
    user = _make_user(session, "me-header@test.com")
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_alpha.id))
    session.commit()

    without_header = client.get("/api/v1/auth/me", headers=_auth(user))
    with_header = client.get(
        "/api/v1/auth/me", headers=_auth(user, tenant_id=tenant_alpha.id)
    )

    assert without_header.status_code == 200
    assert with_header.status_code == 200
    assert with_header.json() == without_header.json()
    assert len(with_header.json()["tenants"]) == 2
