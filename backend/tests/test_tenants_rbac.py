"""RBAC matrix for /api/v1/tenants (APRAS-41).

Tenant administration is install-level, so every write is behind the
existing `deps.get_current_active_admin` guard: ADMINISTRATOR succeeds,
every other role gets 403. `GET /api/v1/tenants` is the one asymmetric read
— all tenants for an administrator, only the caller's own memberships for
everyone else.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.models.tenant import DEFAULT_TENANT_ID, DEFAULT_TENANT_NAME
from app.models.user import User
from tests.conftest import make_user

NON_ADMIN_ROLES = [
    "DIRECTOR",
    "MANAGER",
    "RESIDENT",
    "PORTEIRO",
    "GUEST",
]


def _make_user(session: Session, role: str) -> User:
    identifier = uuid.uuid4()
    user = make_user(
        session,
        id=identifier,
        email=f"{role.lower()}-{identifier}@test.com",
        full_name=f"{role} User",
        hashed_password="hash",
        profile=role,
        cpf=str(identifier.int % 10**11).zfill(11),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def admin(session: Session) -> User:
    return _make_user(session, "ADMINISTRATOR")


@pytest.mark.parametrize("role", NON_ADMIN_ROLES)
def test_create_tenant_is_403_for_non_admin(
    client: TestClient, session: Session, role: str
):
    user = _make_user(session, role)

    response = client.post(
        "/api/v1/tenants", json={"name": f"Nope {role}"}, headers=_headers(user)
    )

    assert response.status_code == 403


def test_create_tenant_is_201_for_admin(client: TestClient, admin: User):
    response = client.post(
        "/api/v1/tenants", json={"name": "Sim"}, headers=_headers(admin)
    )

    assert response.status_code == 201


@pytest.mark.parametrize("role", NON_ADMIN_ROLES)
def test_update_tenant_is_403_for_non_admin(
    client: TestClient, session: Session, role: str
):
    user = _make_user(session, role)

    response = client.patch(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}",
        json={"is_active": False},
        headers=_headers(user),
    )

    assert response.status_code == 403


def test_update_tenant_is_200_for_admin(client: TestClient, admin: User):
    response = client.patch(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}",
        json={"is_active": False},
        headers=_headers(admin),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("role", NON_ADMIN_ROLES)
def test_add_member_is_403_for_non_admin(
    client: TestClient, session: Session, role: str
):
    user = _make_user(session, role)

    response = client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(user.id)},
        headers=_headers(user),
    )

    assert response.status_code == 403


def test_add_member_is_201_for_admin(
    client: TestClient, session: Session, admin: User
):
    member = _make_user(session, "RESIDENT")

    response = client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(member.id)},
        headers=_headers(admin),
    )

    assert response.status_code == 201


@pytest.mark.parametrize("role", NON_ADMIN_ROLES)
def test_remove_member_is_403_for_non_admin(
    client: TestClient, session: Session, admin: User, role: str
):
    user = _make_user(session, role)
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(user.id)},
        headers=_headers(admin),
    )

    response = client.delete(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members/{user.id}",
        headers=_headers(user),
    )

    assert response.status_code == 403


def test_remove_member_is_204_for_admin(
    client: TestClient, session: Session, admin: User
):
    member = _make_user(session, "RESIDENT")
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(member.id)},
        headers=_headers(admin),
    )

    response = client.delete(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members/{member.id}",
        headers=_headers(admin),
    )

    assert response.status_code == 204


def test_list_tenants_is_global_for_admin(client: TestClient, admin: User):
    client.post("/api/v1/tenants", json={"name": "Outro"}, headers=_headers(admin))

    names = {
        tenant["name"]
        for tenant in client.get("/api/v1/tenants", headers=_headers(admin)).json()
    }

    assert names == {DEFAULT_TENANT_NAME, "Outro"}


@pytest.mark.parametrize("role", NON_ADMIN_ROLES)
def test_list_tenants_is_own_memberships_only_for_non_admin(
    client: TestClient, session: Session, admin: User, role: str
):
    user = _make_user(session, role)
    client.post("/api/v1/tenants", json={"name": "Invisível"}, headers=_headers(admin))
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(user.id)},
        headers=_headers(admin),
    )

    names = [
        tenant["name"]
        for tenant in client.get("/api/v1/tenants", headers=_headers(user)).json()
    ]

    assert names == [DEFAULT_TENANT_NAME]


def test_tenant_routes_require_authentication(client: TestClient):
    assert client.get("/api/v1/tenants").status_code == 401
    assert client.post("/api/v1/tenants", json={"name": "x"}).status_code == 401
