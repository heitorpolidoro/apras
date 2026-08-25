import uuid

import jwt
import pytest
from fastapi import status

from app.core import security
from app.core.config import settings
from app.models.enums import UserRole
from app.models.user import User


@pytest.fixture
def director_token(session, admin_user):
    return security.create_access_token(admin_user.id)


@pytest.fixture
def employee_user(session, normal_user):
    return normal_user


def test_get_current_user_no_sub(client, session):
    """Test get_current_user with a token that has no 'sub'."""
    token = jwt.encode(
        {"not_sub": "value"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_current_user_invalid_uuid(client, session):
    """Test get_current_user with a token that has an invalid UUID in 'sub'."""
    token = jwt.encode(
        {"sub": "not-a-uuid"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_current_user_not_found(client, session):
    """Test get_current_user with a valid token but user not in DB."""
    random_id = str(uuid.uuid4())
    token = security.create_access_token(random_id)
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


def test_get_current_user_inactive(client, session):
    """Test get_current_user with an inactive user."""
    inactive_user = User(
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password="...",
        role=UserRole.DIRECTOR,
        is_active=False,
        cpf="70323955008",
    )
    session.add(inactive_user)
    session.commit()

    token = security.create_access_token(inactive_user.id)
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Inactive user"


def test_login_inactive_user(client, session):
    """Test login with an inactive user."""
    password = "testpassword"
    inactive_user = User(
        email="inactive_login@example.com",
        full_name="Inactive Login",
        hashed_password=security.get_password_hash(password),
        role=UserRole.DIRECTOR,
        is_active=False,
        cpf="27943501062",
    )
    session.add(inactive_user)
    session.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": inactive_user.username, "password": password},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Inactive user"


def test_delete_task_not_found(client, director_token):
    """Test deleting a task that does not exist."""
    random_id = uuid.uuid4()
    response = client.delete(
        f"/api/v1/tasks/{random_id}",
        headers={"Authorization": f"Bearer {director_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_update_task_not_found(client, director_token):
    """Test updating a task that does not exist."""
    random_id = uuid.uuid4()
    response = client.patch(
        f"/api/v1/tasks/{random_id}",
        json={"title": "New Title"},
        headers={"Authorization": f"Bearer {director_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_update_deleted_task(client, session, director_token, default_category):
    """Test updating a task that is soft-deleted."""
    from app.models.task import Task

    task = Task(
        title="Deleted Task",
        description="...",
        created_by_id=uuid.uuid4(),
        category_id=default_category.id,
        is_deleted=True,
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"title": "New Title"},
        headers={"Authorization": f"Bearer {director_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_delete_already_deleted_task(client, session, director_token, default_category):
    """Test deleting a task that is already soft-deleted."""
    from app.models.task import Task

    task = Task(
        title="Already Deleted",
        description="...",
        created_by_id=uuid.uuid4(),
        category_id=default_category.id,
        is_deleted=True,
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    response = client.delete(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {director_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_config_migration_database_url_fallback():
    """Test migration_database_url falls back to POSTGRES_URL when non-pooling not set."""
    url = settings.migration_database_url
    assert "postgresql://" in url or "sqlite://" in url


def test_config_migration_database_url_with_non_pooling():
    """Test migration_database_url uses POSTGRES_URL_NON_POOLING when set."""
    from app.core.config import Settings

    s = Settings(
        POSTGRES_URL="postgresql://user:pass@localhost/testdb",
        POSTGRES_URL_NON_POOLING="postgresql://user:pass@localhost/testdb?sslmode=require",
        SECRET_KEY="test-secret",
    )
    assert "sslmode=require" in s.migration_database_url
