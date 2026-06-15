"""RBAC tests for the GUEST role.

Guests are newly signed-up users awaiting promotion: they can authenticate
but cannot see or interact with any task.
"""

import uuid

import pytest
from app.core.security import get_password_hash
from app.models.category import Category
from app.models.enums import UserRole
from app.models.user import User
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_guest_role_value_exists():
    """GUEST must exist as a valid UserRole value."""
    assert UserRole.GUEST == "GUEST"


@pytest.fixture(name="guest_data")
def guest_data_fixture(session: Session):
    guest = User(
        id=uuid.uuid4(),
        username="guest_rbac",
        email="guest_rbac@test.com",
        full_name="Guest Test",
        hashed_password=get_password_hash("pass"),
        role=UserRole.GUEST,
    )
    director = User(
        id=uuid.uuid4(),
        username="director_guest_rbac",
        email="dir_guest_rbac@test.com",
        full_name="Director Test",
        hashed_password=get_password_hash("pass"),
        role=UserRole.DIRECTOR,
    )
    category = Category(id=uuid.uuid4(), name="Guest Test Category", color="#FFFFFF")
    session.add(guest)
    session.add(director)
    session.add(category)
    session.commit()
    return {"guest": guest, "director": director, "category": category}


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def _director_creates_task(client, guest_data) -> str:
    dir_token = get_token(client, "director_guest_rbac", "pass")
    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={
            "title": "Director Task",
            "category_id": str(guest_data["category"].id),
        },
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def test_guest_cannot_create_task(client: TestClient, session: Session, guest_data):
    """GUEST gets 403 when trying to create a task."""
    token = get_token(client, "guest_rbac", "pass")
    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Guest Task", "category_id": str(guest_data["category"].id)},
    )
    assert resp.status_code == 403


def test_guest_task_list_is_empty(client: TestClient, session: Session, guest_data):
    """GUEST sees an empty task list even when tasks exist."""
    _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_guest_cannot_edit_task(client: TestClient, session: Session, guest_data):
    """GUEST gets 404 when trying to edit a task (tasks are invisible to guests)."""
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 404


def test_guest_cannot_see_task_history(
    client: TestClient, session: Session, guest_data
):
    """GUEST gets 404 when accessing task history."""
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.get(
        f"/api/v1/tasks/{task_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_guest_cannot_comment(client: TestClient, session: Session, guest_data):
    """GUEST gets 404 when trying to comment on a task."""
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "guest comment"},
    )
    assert resp.status_code == 404


def test_guest_cannot_create_category(
    client: TestClient, session: Session, guest_data
):
    """GUEST gets 403 when trying to create a category."""
    token = get_token(client, "guest_rbac", "pass")
    resp = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Guest Category", "color": "#ff0000"},
    )
    assert resp.status_code == 403


def test_assert_can_edit_task_guest_raises(session: Session, guest_data):
    """assert_can_edit_task always raises ForbiddenError for GUEST."""
    from app.api.deps import assert_can_edit_task
    from app.core.exceptions import ForbiddenError
    from app.models.task import Task

    task = Task(
        title="T",
        category_id=guest_data["category"].id,
        created_by_id=guest_data["director"].id,
        assigned_to_id=None,
    )
    session.add(task)
    session.commit()
    with pytest.raises(ForbiddenError):
        assert_can_edit_task(guest_data["guest"], task)
