"""Tests for treating UserRole as an implicit UserType (APRAS-9).

Covers `get_effective_user_type_ids` in isolation, and its effect on the
menu-access gate (APRAS-8) and `Task.visible_to` targeting/visibility
once a role-linked UserType exists (normally seeded by the
`0018_add_role_to_user_type` migration; created directly here since the
backend test suite builds its schema via `SQLModel.metadata.create_all()`
against SQLite, not via Alembic).
"""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import assert_menu_access, get_effective_user_type_ids
from app.core.exceptions import ForbiddenError
from app.core.security import create_access_token, get_password_hash
from app.models.category import Category
from app.models.enums import MenuKey, UserRole
from app.models.task import Task
from app.models.user import User
from app.models.user_type import UserType


def _token(user: User) -> str:
    return create_access_token(user.id)


# ---------------------------------------------------------------------------
# get_effective_user_type_ids - unit tests
# ---------------------------------------------------------------------------


def test_effective_ids_explicit_only(session: Session):
    """A user with only explicitly-assigned UserTypes gets exactly those ids."""
    ut = UserType(name="Board", allowed_menus=[])
    session.add(ut)
    session.commit()

    user = User(
        id=uuid.uuid4(),
        email="explicit_only@test.com",
        full_name="Explicit Only",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="52998224725",
        user_types=[ut],
    )
    session.add(user)
    session.commit()

    assert get_effective_user_type_ids(user, session) == {ut.id}


def test_effective_ids_role_type_only(session: Session):
    """A user with zero explicit UserTypes still gets their role-type id."""
    role_type = UserType(
        name="Diretor (papel)", allowed_menus=[], role=UserRole.DIRECTOR
    )
    session.add(role_type)
    session.commit()

    user = User(
        id=uuid.uuid4(),
        email="role_only@test.com",
        full_name="Role Only",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="11144477735",
    )
    session.add(user)
    session.commit()

    assert get_effective_user_type_ids(user, session) == {role_type.id}


def test_effective_ids_explicit_and_role_combined(session: Session):
    """Explicit and role-implicit ids are unioned together."""
    explicit_type = UserType(name="Board", allowed_menus=[])
    role_type = UserType(
        name="Gerente (papel)", allowed_menus=[], role=UserRole.MANAGER
    )
    session.add(explicit_type)
    session.add(role_type)
    session.commit()

    user = User(
        id=uuid.uuid4(),
        email="both@test.com",
        full_name="Both",
        hashed_password="x",
        role=UserRole.MANAGER,
        cpf="08050681057",
        user_types=[explicit_type],
    )
    session.add(user)
    session.commit()

    assert get_effective_user_type_ids(user, session) == {
        explicit_type.id,
        role_type.id,
    }


def test_effective_ids_deduplicates_when_role_type_also_explicitly_assigned(
    session: Session,
):
    """If a user happens to have their role-type explicitly assigned too,
    the id appears once (a set, not a multiset)."""
    role_type = UserType(
        name="Convidado (papel)", allowed_menus=[], role=UserRole.GUEST
    )
    session.add(role_type)
    session.commit()

    user = User(
        id=uuid.uuid4(),
        email="dedup@test.com",
        full_name="Dedup",
        hashed_password="x",
        role=UserRole.GUEST,
        cpf="07491723040",
        user_types=[role_type],
    )
    session.add(user)
    session.commit()

    ids = get_effective_user_type_ids(user, session)
    assert ids == {role_type.id}
    assert len(ids) == 1


def test_effective_ids_no_explicit_and_no_role_type_row(session: Session):
    """A user with no explicit UserTypes and no seeded role-type row (e.g.
    a fresh SQLite test DB without the APRAS-9 migration applied) gets an
    empty effective set."""
    user = User(
        id=uuid.uuid4(),
        email="none@test.com",
        full_name="None",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="70323955008",
    )
    session.add(user)
    session.commit()

    assert get_effective_user_type_ids(user, session) == set()


# ---------------------------------------------------------------------------
# assert_menu_access - role-type fallback
# ---------------------------------------------------------------------------


def test_assert_menu_access_role_type_empty_allowed_menus_denies(session: Session):
    """A Director with zero explicit UserTypes is still denied while their
    role-type starts with allowed_menus == [] (APRAS-9 provides the
    mechanism, it does not restore access on its own)."""
    role_type = UserType(
        name="Diretor (papel)", allowed_menus=[], role=UserRole.DIRECTOR
    )
    session.add(role_type)
    session.commit()

    director = User(
        id=uuid.uuid4(),
        email="director_role_empty@test.com",
        full_name="Director",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="52998224725",
    )
    session.add(director)
    session.commit()

    with pytest.raises(ForbiddenError):
        assert_menu_access(director, MenuKey.TASKS, session)


def test_assert_menu_access_role_type_granted_allows(session: Session):
    """Once the role-type's allowed_menus is granted, the same zero-explicit
    -UserType Director passes."""
    role_type = UserType(
        name="Diretor (papel)", allowed_menus=["tasks"], role=UserRole.DIRECTOR
    )
    session.add(role_type)
    session.commit()

    director = User(
        id=uuid.uuid4(),
        email="director_role_granted@test.com",
        full_name="Director",
        hashed_password="x",
        role=UserRole.DIRECTOR,
        cpf="11144477735",
    )
    session.add(director)
    session.commit()

    assert_menu_access(director, MenuKey.TASKS, session)  # should not raise


# ---------------------------------------------------------------------------
# Endpoint-level: Director role-type fallback via /tasks and PATCH /user-types
# ---------------------------------------------------------------------------


@pytest.fixture(name="role_type_data")
def role_type_data_fixture(session: Session):
    """A Director role-type (starts empty), a zero-explicit-UserType
    Director, an Administrator, and a category."""
    director_role_type = UserType(
        name="Diretor (papel)", allowed_menus=[], role=UserRole.DIRECTOR
    )
    session.add(director_role_type)
    session.commit()

    director = User(
        id=uuid.uuid4(),
        email="director_fallback@test.com",
        full_name="Director Fallback",
        hashed_password=get_password_hash("pass"),
        role=UserRole.DIRECTOR,
        cpf="27943501062",
    )
    admin = User(
        id=uuid.uuid4(),
        email="admin_fallback@test.com",
        full_name="Admin Fallback",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="53412530006",
    )
    category = Category(id=uuid.uuid4(), name="Fallback Category", color="#112233")
    session.add(director)
    session.add(admin)
    session.add(category)
    session.commit()
    return {
        "director_role_type": director_role_type,
        "director": director,
        "admin": admin,
        "category": category,
    }


def test_director_with_zero_explicit_types_denied_by_default(
    client: TestClient, role_type_data
):
    """A Director with zero explicit UserTypes still gets 403 on /tasks/*
    while their role-type's allowed_menus is empty. This is NOT a
    regression: the role-type mechanism does not restore access on its
    own, so this must keep being true after APRAS-9 ships."""
    token = _token(role_type_data["director"])
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_director_gains_access_after_role_type_allowed_menus_patched(
    client: TestClient, role_type_data
):
    """After granting the role-type's allowed_menus via PATCH
    /user-types/{id}, the same zero-explicit-UserType Director succeeds."""
    admin_token = _token(role_type_data["admin"])
    patch_response = client.patch(
        f"/api/v1/user-types/{role_type_data['director_role_type'].id}",
        json={"name": "Diretor (papel)", "allowed_menus": ["tasks"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch_response.status_code == status.HTTP_200_OK

    director_token = _token(role_type_data["director"])
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {director_token}"}
    )
    assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Task.visible_to targeting a role-type
# ---------------------------------------------------------------------------


def test_task_visible_to_role_type_visible_to_manager_with_zero_explicit_types(
    client: TestClient, session: Session
):
    """A task with `visible_to` targeting a Manager role-type's UserType is
    visible to a Manager who has zero explicitly-assigned UserTypes."""
    manager_role_type = UserType(
        name="Gerente (papel)", allowed_menus=["tasks"], role=UserRole.MANAGER
    )
    session.add(manager_role_type)
    session.commit()

    admin = User(
        id=uuid.uuid4(),
        email="admin_vis@test.com",
        full_name="Admin Vis",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="94465542073",
    )
    manager = User(
        id=uuid.uuid4(),
        email="manager_vis@test.com",
        full_name="Manager Vis",
        hashed_password=get_password_hash("pass"),
        role=UserRole.MANAGER,
        cpf="98765432100",
    )
    category = Category(id=uuid.uuid4(), name="Vis Category", color="#445566")
    session.add(admin)
    session.add(manager)
    session.add(category)
    session.commit()

    task = Task(
        title="Visible via role-type",
        category_id=category.id,
        created_by_id=admin.id,
        visible_to=[manager_role_type],
    )
    session.add(task)
    session.commit()

    manager_token = _token(manager)
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    titles = [t["title"] for t in response.json()]
    assert "Visible via role-type" in titles


# ---------------------------------------------------------------------------
# Role-types cannot be deleted
# ---------------------------------------------------------------------------


def test_delete_role_type_forbidden(client: TestClient, session: Session):
    """DELETE /user-types/{id} on a role-type returns 403, not 204."""
    role_type = UserType(
        name="Morador (papel)", allowed_menus=[], role=UserRole.RESIDENT
    )
    session.add(role_type)
    session.commit()

    admin = User(
        id=uuid.uuid4(),
        email="admin_delete@test.com",
        full_name="Admin Delete",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="41940480038",
    )
    session.add(admin)
    session.commit()

    admin_token = _token(admin)
    response = client.delete(
        f"/api/v1/user-types/{role_type.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # The row must still exist afterwards.
    assert session.get(UserType, role_type.id) is not None


def test_delete_regular_type_still_allowed(client: TestClient, session: Session):
    """Regular (role=None) UserTypes are unaffected: they can still be
    deleted, as before APRAS-9."""
    regular_type = UserType(name="Board", allowed_menus=[])
    session.add(regular_type)
    session.commit()

    admin = User(
        id=uuid.uuid4(),
        email="admin_delete2@test.com",
        full_name="Admin Delete 2",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="96476331030",
    )
    session.add(admin)
    session.commit()

    admin_token = _token(admin)
    response = client.delete(
        f"/api/v1/user-types/{regular_type.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# UserTypeRead exposes `role`; UserTypeCreate/Update cannot set it
# ---------------------------------------------------------------------------


def test_user_type_read_exposes_role(client: TestClient, session: Session):
    role_type = UserType(
        name="Administrador (papel)", allowed_menus=[], role=UserRole.ADMINISTRATOR
    )
    session.add(role_type)
    session.commit()

    admin = User(
        id=uuid.uuid4(),
        email="admin_read@test.com",
        full_name="Admin Read",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="16899216085",
    )
    session.add(admin)
    session.commit()

    token = _token(admin)
    response = client.get(
        "/api/v1/user-types/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = next(t for t in response.json() if t["id"] == str(role_type.id))
    assert data["role"] == "ADMINISTRATOR"


def test_create_user_type_ignores_role_field(client: TestClient, session: Session):
    """UserTypeCreate has no `role` field: passing one is silently ignored,
    so an admin cannot mint a second role-linked type this way."""
    admin = User(
        id=uuid.uuid4(),
        email="admin_create_role@test.com",
        full_name="Admin Create Role",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="65970687003",
    )
    session.add(admin)
    session.commit()

    token = _token(admin)
    response = client.post(
        "/api/v1/user-types/",
        json={"name": "Sneaky Type", "role": "DIRECTOR"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["role"] is None
