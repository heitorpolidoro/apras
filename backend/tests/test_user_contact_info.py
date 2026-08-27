"""Tests for the PATCH /users/{user_id}/contact-info endpoint."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models.enums import UserRole
from app.models.user import User


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


@pytest.fixture(name="manager_user")
def manager_user_fixture(session: Session):
    """Create and persist a MANAGER user for tests."""
    user = User(
        id=uuid.uuid4(),
        email="manager@test.com",
        full_name="Manager User",
        hashed_password=get_password_hash("test_manager_password"),
        role=UserRole.MANAGER,
        cpf="11122233396",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture(name="guest_user")
def guest_user_fixture(session: Session):
    """Create and persist a GUEST user for tests."""
    user = User(
        id=uuid.uuid4(),
        email="guest@test.com",
        full_name="Guest User",
        hashed_password=get_password_hash("test_guest_password"),
        role=UserRole.GUEST,
        cpf="33344455508",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture(name="target_user")
def target_user_fixture(session: Session):
    """Create and persist a plain user whose contact info will be edited."""
    user = User(
        id=uuid.uuid4(),
        email="target@test.com",
        full_name="Target User",
        hashed_password=get_password_hash("test_target_password"),
        role=UserRole.DIRECTOR,
        cpf="44455566619",
    )
    session.add(user)
    session.commit()
    return user


def test_administrator_can_update_contact_info(
    client: TestClient, admin_user, target_user
):
    token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/users/{target_user.id}/contact-info",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "11999998888", "address": "Rua A, 123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "11999998888"
    assert data["address"] == "Rua A, 123"


def test_manager_can_update_contact_info(client: TestClient, manager_user, target_user):
    token = get_token(client, "manager", "test_manager_password")
    response = client.patch(
        f"/api/v1/users/{target_user.id}/contact-info",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "11988887777", "address": "Rua B, 456"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "11988887777"
    assert data["address"] == "Rua B, 456"


def test_director_forbidden_from_contact_info_update(
    client: TestClient, normal_user, target_user
):
    """normal_user fixture has DIRECTOR role."""
    token = get_token(client, "user1", "test_user_password")
    response = client.patch(
        f"/api/v1/users/{target_user.id}/contact-info",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "11977776666"},
    )
    assert response.status_code == 403


def test_guest_forbidden_from_contact_info_update(
    client: TestClient, guest_user, target_user
):
    token = get_token(client, "guest", "test_guest_password")
    response = client.patch(
        f"/api/v1/users/{target_user.id}/contact-info",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "11977776666"},
    )
    assert response.status_code == 403


def test_contact_info_update_ignores_extra_fields(
    client: TestClient, admin_user, target_user
):
    """Extra fields like role/is_active/user_type_ids are silently dropped."""
    token = get_token(client, "admin", "test_admin_password")
    original_role = target_user.role
    original_is_active = target_user.is_active

    response = client.patch(
        f"/api/v1/users/{target_user.id}/contact-info",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "phone": "11966665555",
            "address": "Rua C, 789",
            "role": UserRole.ADMINISTRATOR,
            "is_active": False,
            "user_type_ids": [str(uuid.uuid4())],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "11966665555"
    assert data["address"] == "Rua C, 789"
    assert data["role"] == original_role
    assert data["is_active"] == original_is_active
    assert data["user_types"] == []


def test_contact_info_update_404_for_missing_user(client: TestClient, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/users/{uuid.uuid4()}/contact-info",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "11955554444"},
    )
    assert response.status_code == 404
