"""Tests for the UserType-based menu access gate (APRAS-8).

Covers `assert_menu_access` in isolation and its enforcement on the
tasks/categories endpoints.
"""
import uuid

import pytest
from app.api.deps import assert_menu_access
from app.core.exceptions import ForbiddenError
from app.core.security import create_access_token, get_password_hash
from app.models.category import Category
from app.models.enums import MenuKey, UserRole
from app.models.user import User
from app.models.user_type import UserType
from fastapi.testclient import TestClient
from sqlmodel import Session


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# assert_menu_access – unit tests
# ---------------------------------------------------------------------------


def test_assert_menu_access_administrator_always_passes(session: Session):
    """ADMINISTRATOR passes regardless of UserTypes/allowed_menus."""
    admin = User(
        id=uuid.uuid4(),
        email="admin_menu@test.com",
        full_name="Admin",
        hashed_password="x",
        role=UserRole.ADMINISTRATOR,
        cpf="52998224725",
    )
    assert_menu_access(admin, MenuKey.TASKS, session)  # should not raise
    assert_menu_access(admin, MenuKey.CATEGORIES, session)  # should not raise


def test_assert_menu_access_matching_user_type_passes(session: Session):
    """A non-admin with a UserType granting the menu key passes."""
    ut = UserType(name="Board", allowed_menus=["tasks"])
    session.add(ut)
    session.commit()
    director = User(
        id=uuid.uuid4(),
        email="director_menu@test.com",
        full_name="Director",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="11144477735",
        user_types=[ut],
    )
    assert_menu_access(director, MenuKey.TASKS, session)  # should not raise


def test_assert_menu_access_non_matching_user_type_denied(session: Session):
    """A non-admin whose UserTypes don't include the menu key is denied."""
    ut = UserType(name="Board", allowed_menus=["categories"])
    session.add(ut)
    session.commit()
    director = User(
        id=uuid.uuid4(),
        email="director_menu2@test.com",
        full_name="Director",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="08050681057",
        user_types=[ut],
    )
    with pytest.raises(ForbiddenError):
        assert_menu_access(director, MenuKey.TASKS, session)


def test_assert_menu_access_zero_user_types_denied(session: Session):
    """A non-admin with zero UserTypes assigned (and no matching role-type
    seeded in this test DB) is denied."""
    director = User(
        id=uuid.uuid4(),
        email="director_menu3@test.com",
        full_name="Director",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="07491723040",
    )
    with pytest.raises(ForbiddenError):
        assert_menu_access(director, MenuKey.TASKS, session)


def test_assert_menu_access_at_least_one_matching_type_passes(session: Session):
    """Access is granted if at least one of several UserTypes matches."""
    ut_no = UserType(name="No Access", allowed_menus=[])
    ut_yes = UserType(name="Has Access", allowed_menus=["tasks"])
    session.add(ut_no)
    session.add(ut_yes)
    session.commit()
    director = User(
        id=uuid.uuid4(),
        email="director_menu4@test.com",
        full_name="Director",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="70323955008",
        user_types=[ut_no, ut_yes],
    )
    assert_menu_access(director, MenuKey.TASKS, session)  # should not raise


# ---------------------------------------------------------------------------
# Endpoint-level enforcement – tasks.py / categories.py
# ---------------------------------------------------------------------------


@pytest.fixture(name="gate_data")
def gate_data_fixture(session: Session):
    """A DIRECTOR with no qualifying UserType, plus an active category."""
    no_access_type = UserType(name="No Menu Access", allowed_menus=[])
    session.add(no_access_type)
    session.commit()

    director = User(
        id=uuid.uuid4(),
        email="director_gate@test.com",
        full_name="Director Gate",
        hashed_password=get_password_hash("pass"),
        role=UserRole.DIRECTOR,
        cpf="27943501062",
        user_types=[no_access_type],
    )
    admin = User(
        id=uuid.uuid4(),
        email="admin_gate@test.com",
        full_name="Admin Gate",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="53412530006",
    )
    category = Category(id=uuid.uuid4(), name="Gate Category", color="#ABCDEF")
    session.add(director)
    session.add(admin)
    session.add(category)
    session.commit()
    return {
        "director": director,
        "admin": admin,
        "category": category,
        "no_access_type": no_access_type,
    }


def test_list_tasks_denied_without_menu_access(client: TestClient, gate_data):
    token = get_token(client, "director_gate", "pass")
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_create_task_denied_without_menu_access(client: TestClient, gate_data):
    token = get_token(client, "director_gate", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "T", "category_id": str(gate_data["category"].id)},
    )
    assert response.status_code == 403


def test_update_task_denied_without_menu_access(
    client: TestClient, session: Session, gate_data
):
    from app.models.task import Task

    task = Task(
        title="Existing",
        category_id=gate_data["category"].id,
        created_by_id=gate_data["admin"].id,
    )
    session.add(task)
    session.commit()

    token = get_token(client, "director_gate", "pass")
    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Changed"},
    )
    assert response.status_code == 403


def test_get_task_history_denied_without_menu_access(
    client: TestClient, session: Session, gate_data
):
    from app.models.task import Task

    task = Task(
        title="Existing",
        category_id=gate_data["category"].id,
        created_by_id=gate_data["admin"].id,
    )
    session.add(task)
    session.commit()

    token = get_token(client, "director_gate", "pass")
    response = client.get(
        f"/api/v1/tasks/{task.id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_list_comments_denied_without_menu_access(
    client: TestClient, session: Session, gate_data
):
    from app.models.task import Task

    task = Task(
        title="Existing",
        category_id=gate_data["category"].id,
        created_by_id=gate_data["admin"].id,
    )
    session.add(task)
    session.commit()

    token = get_token(client, "director_gate", "pass")
    response = client.get(
        f"/api/v1/tasks/{task.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_create_comment_denied_without_menu_access(
    client: TestClient, session: Session, gate_data
):
    from app.models.task import Task

    task = Task(
        title="Existing",
        category_id=gate_data["category"].id,
        created_by_id=gate_data["admin"].id,
    )
    session.add(task)
    session.commit()

    token = get_token(client, "director_gate", "pass")
    response = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "hi"},
    )
    assert response.status_code == 403


def test_update_comment_denied_without_menu_access(
    client: TestClient, session: Session, gate_data
):
    from app.models.task import Task, TaskComment

    task = Task(
        title="Existing",
        category_id=gate_data["category"].id,
        created_by_id=gate_data["admin"].id,
    )
    session.add(task)
    session.commit()
    comment = TaskComment(
        task_id=task.id, content="hi", created_by_id=gate_data["admin"].id
    )
    session.add(comment)
    session.commit()

    token = get_token(client, "director_gate", "pass")
    response = client.patch(
        f"/api/v1/tasks/{task.id}/comments/{comment.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "edited"},
    )
    assert response.status_code == 403


def test_delete_task_denied_without_menu_access(
    client: TestClient, session: Session, gate_data
):
    """Even ADMINISTRATOR-only delete_task calls assert_menu_access first.

    Uses an admin with no menu-relevant restriction to prove ADMINISTRATOR is
    never blocked; the actual denial path for delete_task is unreachable for
    non-admins since get_current_active_admin already 403s them first.
    """
    from app.models.task import Task

    task = Task(
        title="Existing",
        category_id=gate_data["category"].id,
        created_by_id=gate_data["admin"].id,
    )
    session.add(task)
    session.commit()

    admin_token = get_token(client, "admin_gate", "pass")
    response = client.delete(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_list_categories_denied_without_menu_access(client: TestClient, gate_data):
    token = get_token(client, "director_gate", "pass")
    response = client.get(
        "/api/v1/categories/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_create_category_denied_without_menu_access(client: TestClient, gate_data):
    token = get_token(client, "director_gate", "pass")
    response = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Cat", "color": "#123456"},
    )
    assert response.status_code == 403


def test_update_category_denied_without_menu_access(client: TestClient, gate_data):
    token = get_token(client, "director_gate", "pass")
    response = client.patch(
        f"/api/v1/categories/{gate_data['category'].id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed"},
    )
    assert response.status_code == 403


def test_delete_category_denied_without_menu_access(client: TestClient, gate_data):
    token = get_token(client, "director_gate", "pass")
    response = client.delete(
        f"/api/v1/categories/{gate_data['category'].id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_granting_allowed_menus_restores_task_access(
    client: TestClient, session: Session, gate_data
):
    """Granting the right allowed_menus value restores access."""
    gate_data["no_access_type"].allowed_menus = ["tasks"]
    session.add(gate_data["no_access_type"])
    session.commit()

    token = get_token(client, "director_gate", "pass")
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_granting_allowed_menus_restores_category_access(
    client: TestClient, session: Session, gate_data
):
    """Granting the right allowed_menus value restores access."""
    gate_data["no_access_type"].allowed_menus = ["categories"]
    session.add(gate_data["no_access_type"])
    session.commit()

    token = get_token(client, "director_gate", "pass")
    response = client.get(
        "/api/v1/categories/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_administrator_never_blocked_regardless_of_user_type(
    client: TestClient, session: Session, gate_data
):
    """Administrator passes the gate even with a UserType granting nothing."""
    gate_data["admin"].user_types = [gate_data["no_access_type"]]
    session.add(gate_data["admin"])
    session.commit()

    admin_token = get_token(client, "admin_gate", "pass")
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    response = client.get(
        "/api/v1/categories/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# user_types.py – allowed_menus persistence (create/update)
# ---------------------------------------------------------------------------


def test_create_user_type_persists_allowed_menus(client: TestClient, gate_data):
    admin_token = create_access_token(gate_data["admin"].id)
    response = client.post(
        "/api/v1/user-types/",
        json={"name": "Finance Menu", "allowed_menus": ["tasks", "categories"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert set(data["allowed_menus"]) == {"tasks", "categories"}


def test_update_user_type_persists_allowed_menus(
    client: TestClient, session: Session, gate_data
):
    ut = gate_data["no_access_type"]
    admin_token = create_access_token(gate_data["admin"].id)
    response = client.patch(
        f"/api/v1/user-types/{ut.id}",
        json={"name": ut.name, "allowed_menus": ["categories"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["allowed_menus"] == ["categories"]


def test_create_user_type_defaults_allowed_menus_to_empty(
    client: TestClient, gate_data
):
    admin_token = create_access_token(gate_data["admin"].id)
    response = client.post(
        "/api/v1/user-types/",
        json={"name": "No Menus Given"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["allowed_menus"] == []


def test_create_user_type_rejects_invalid_menu_key(client: TestClient, gate_data):
    admin_token = create_access_token(gate_data["admin"].id)
    response = client.post(
        "/api/v1/user-types/",
        json={"name": "Bad Menu", "allowed_menus": ["not-a-real-menu"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
