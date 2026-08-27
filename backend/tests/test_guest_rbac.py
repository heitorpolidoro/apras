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
from app.models.user_type import UserType
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_guest_role_value_exists():
    """GUEST must exist as a valid UserRole value."""
    assert UserRole.GUEST == "GUEST"


@pytest.fixture(name="guest_data")
def guest_data_fixture(session: Session):
    # GUEST intentionally gets zero UserTypes (and thus zero menu access,
    # per APRAS-8) since these tests exercise GUEST being blocked. The
    # helper director, however, needs standing "tasks" access so it can set
    # up tasks for the guest-focused assertions below.
    director_type = UserType(name="Director Guest RBAC Type", allowed_menus=["tasks"])
    session.add(director_type)
    session.commit()

    guest = User(
        id=uuid.uuid4(),
        email="guest_rbac@test.com",
        full_name="Guest Test",
        hashed_password=get_password_hash("pass"),
        role=UserRole.GUEST,
        cpf="32464177002",
    )
    director = User(
        id=uuid.uuid4(),
        email="director_guest_rbac@test.com",
        full_name="Director Test",
        hashed_password=get_password_hash("pass"),
        role=UserRole.DIRECTOR,
        cpf="14555816045",
        user_types=[director_type],
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
    """GUEST gets 403 listing tasks: no UserType grants "tasks" access.

    Before APRAS-8, GUEST's own role check made the list unconditionally
    empty (200 with `[]`). The new menu gate now runs first and denies the
    request outright, since GUEST has no UserType at all here.
    """
    _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_guest_cannot_edit_task(client: TestClient, session: Session, guest_data):
    """GUEST gets 403 editing a task: the menu gate runs before task visibility."""
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 403


def test_guest_cannot_see_task_history(
    client: TestClient, session: Session, guest_data
):
    """GUEST gets 403 accessing task history: the menu gate runs first."""
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.get(
        f"/api/v1/tasks/{task_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_guest_cannot_comment(client: TestClient, session: Session, guest_data):
    """GUEST gets 403 commenting on a task: the menu gate runs first."""
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "guest comment"},
    )
    assert resp.status_code == 403


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
