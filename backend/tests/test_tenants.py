"""Endpoint tests for /api/v1/tenants (APRAS-41).

Covers all seven routes: the happy paths, the 409s, the 404-not-403 rule for
a non-member reader, the name ordering, the empty-membership `[]`, and
multi-membership (one user in two tenants).
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.models.tenant import DEFAULT_TENANT_ID, DEFAULT_TENANT_NAME, Tenant
from app.models.user import User
from tests.conftest import make_user


def _make_user(session: Session, role: str, email: str, cpf: str) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=email,
        full_name=f"User {email}",
        hashed_password="hash",
        profile=role,
        cpf=cpf,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def admin(session: Session) -> User:
    return _make_user(session, "ADMINISTRATOR", "tenant_admin@test.com", "11111111111")


@pytest.fixture
def resident(session: Session) -> User:
    return _make_user(session, "RESIDENT", "tenant_resident@test.com", "22222222222")


def test_create_tenant_returns_201(client: TestClient, admin: User):
    response = client.post(
        "/api/v1/tenants",
        json={"name": "Condomínio Alfa"},
        headers=_headers(admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Condomínio Alfa"
    assert body["is_active"] is True
    assert uuid.UUID(body["id"]) != DEFAULT_TENANT_ID
    assert body["created_at"]
    assert body["updated_at"]


def test_create_tenant_rejects_duplicate_name_with_409(client: TestClient, admin: User):
    client.post("/api/v1/tenants", json={"name": "Dup"}, headers=_headers(admin))
    response = client.post(
        "/api/v1/tenants", json={"name": "Dup"}, headers=_headers(admin)
    )

    assert response.status_code == 409


def test_create_tenant_rejects_empty_name_with_422(client: TestClient, admin: User):
    response = client.post(
        "/api/v1/tenants", json={"name": ""}, headers=_headers(admin)
    )

    assert response.status_code == 422


def test_list_tenants_returns_all_for_admin_ordered_by_name(
    client: TestClient, admin: User
):
    for name in ("Zulu", "Alfa", "Mike"):
        client.post("/api/v1/tenants", json={"name": name}, headers=_headers(admin))

    response = client.get("/api/v1/tenants", headers=_headers(admin))

    assert response.status_code == 200
    names = [tenant["name"] for tenant in response.json()]
    assert names == sorted(names)
    assert {"Alfa", "Mike", "Zulu", DEFAULT_TENANT_NAME} <= set(names)


def test_list_tenants_returns_empty_list_for_member_less_non_admin(
    client: TestClient, resident: User
):
    response = client.get("/api/v1/tenants", headers=_headers(resident))

    assert response.status_code == 200
    assert response.json() == []


def test_list_tenants_returns_only_own_memberships_for_non_admin(
    client: TestClient, session: Session, admin: User, resident: User
):
    other = client.post(
        "/api/v1/tenants", json={"name": "Beta"}, headers=_headers(admin)
    ).json()
    client.post(
        f"/api/v1/tenants/{other['id']}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    response = client.get("/api/v1/tenants", headers=_headers(resident))

    assert response.status_code == 200
    assert [tenant["name"] for tenant in response.json()] == ["Beta"]


def test_get_tenant_returns_200_for_admin(client: TestClient, admin: User):
    response = client.get(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}", headers=_headers(admin)
    )

    assert response.status_code == 200
    assert response.json()["name"] == DEFAULT_TENANT_NAME


def test_get_tenant_returns_404_for_unknown_id(client: TestClient, admin: User):
    response = client.get(f"/api/v1/tenants/{uuid.uuid4()}", headers=_headers(admin))

    assert response.status_code == 404


def test_get_tenant_returns_404_not_403_for_non_member_non_admin(
    client: TestClient, resident: User
):
    """Existence must not leak: a non-member gets 404, never 403."""
    response = client.get(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}", headers=_headers(resident)
    )

    assert response.status_code == 404


def test_get_tenant_returns_200_for_a_member(
    client: TestClient, admin: User, resident: User
):
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    response = client.get(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}", headers=_headers(resident)
    )

    assert response.status_code == 200


def test_update_tenant_returns_200(client: TestClient, admin: User):
    response = client.patch(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}",
        json={"name": "Renomeado", "is_active": False},
        headers=_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renomeado"
    assert response.json()["is_active"] is False


def test_update_tenant_returns_404_for_unknown_id(client: TestClient, admin: User):
    response = client.patch(
        f"/api/v1/tenants/{uuid.uuid4()}",
        json={"name": "Nope"},
        headers=_headers(admin),
    )

    assert response.status_code == 404


def test_update_tenant_returns_409_on_name_collision(client: TestClient, admin: User):
    created = client.post(
        "/api/v1/tenants", json={"name": "Gamma"}, headers=_headers(admin)
    ).json()

    response = client.patch(
        f"/api/v1/tenants/{created['id']}",
        json={"name": DEFAULT_TENANT_NAME},
        headers=_headers(admin),
    )

    assert response.status_code == 409


def test_update_tenant_keeping_its_own_name_is_not_a_collision(
    client: TestClient, admin: User
):
    created = client.post(
        "/api/v1/tenants", json={"name": "Delta"}, headers=_headers(admin)
    ).json()

    response = client.patch(
        f"/api/v1/tenants/{created['id']}",
        json={"name": "Delta", "is_active": False},
        headers=_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_add_member_returns_201_with_the_user_details(
    client: TestClient, admin: User, resident: User
):
    response = client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(resident.id)
    assert body["email"] == resident.email
    assert body["full_name"] == resident.full_name
    # `TenantMemberRead.role` became `roles: list[str]` (§8.2).
    assert body["roles"] == ["Morador (papel)"]
    assert body["linked_at"]


def test_add_member_twice_returns_409(
    client: TestClient, admin: User, resident: User
):
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )
    response = client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    assert response.status_code == 409


def test_add_member_to_a_second_tenant_succeeds(
    client: TestClient, admin: User, resident: User
):
    """Multi-membership is first class: same user, two tenants, both 201."""
    other = client.post(
        "/api/v1/tenants", json={"name": "Épsilon"}, headers=_headers(admin)
    ).json()

    first = client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )
    second = client.post(
        f"/api/v1/tenants/{other['id']}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    assert first.status_code == 201
    assert second.status_code == 201

    listed = client.get("/api/v1/tenants", headers=_headers(resident)).json()
    assert len(listed) == 2


def test_add_member_returns_404_for_unknown_tenant(
    client: TestClient, admin: User, resident: User
):
    response = client.post(
        f"/api/v1/tenants/{uuid.uuid4()}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    assert response.status_code == 404


def test_add_member_returns_404_for_unknown_user(client: TestClient, admin: User):
    response = client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(uuid.uuid4())},
        headers=_headers(admin),
    )

    assert response.status_code == 404


def test_list_members_returns_the_members(
    client: TestClient, admin: User, resident: User
):
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    response = client.get(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members", headers=_headers(admin)
    )

    assert response.status_code == 200
    assert [member["user_id"] for member in response.json()] == [str(resident.id)]


def test_list_members_is_visible_to_a_member(
    client: TestClient, admin: User, resident: User
):
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    response = client.get(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members", headers=_headers(resident)
    )

    assert response.status_code == 200


def test_list_members_returns_404_for_a_non_member_non_admin(
    client: TestClient, resident: User
):
    response = client.get(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members", headers=_headers(resident)
    )

    assert response.status_code == 404


def test_remove_member_returns_204(client: TestClient, admin: User, resident: User):
    client.post(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members",
        json={"user_id": str(resident.id)},
        headers=_headers(admin),
    )

    response = client.delete(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members/{resident.id}",
        headers=_headers(admin),
    )

    assert response.status_code == 204
    remaining = client.get(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members", headers=_headers(admin)
    ).json()
    assert remaining == []


def test_remove_member_returns_404_when_the_link_does_not_exist(
    client: TestClient, admin: User, resident: User
):
    response = client.delete(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/members/{resident.id}",
        headers=_headers(admin),
    )

    assert response.status_code == 404


def test_there_is_no_tenant_delete_route(client: TestClient, admin: User, session: Session):
    """Deactivation is a PATCH; deletion would fail on RESTRICT anyway."""
    session.add(Tenant(name="Sem Delete"))
    session.commit()

    response = client.delete(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}", headers=_headers(admin)
    )

    assert response.status_code == 405
