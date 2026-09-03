"""Tests for roles endpoints and related exceptions/handlers."""
import asyncio
import uuid

from fastapi import status

from app.core.exception_handlers import domain_exception_handler
from app.core.exceptions import ForbiddenError, TaskNotFoundError
from app.core.security import create_access_token
from app.models.role import Role

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_token(admin_user):
    return create_access_token(admin_user.id)


def _director_token(normal_user):
    return create_access_token(normal_user.id)


# ---------------------------------------------------------------------------
# exceptions.py coverage
# ---------------------------------------------------------------------------

def test_forbidden_error_default_message():
    exc = ForbiddenError()
    assert exc.message == "Not enough privileges"


def test_forbidden_error_custom_message():
    exc = ForbiddenError("Custom forbidden")
    assert exc.message == "Custom forbidden"


def test_task_not_found_error_message():
    tid = uuid.uuid4()
    exc = TaskNotFoundError(tid)
    assert str(tid) in exc.message


# ---------------------------------------------------------------------------
# exception_handlers.py coverage
# ---------------------------------------------------------------------------

def test_domain_exception_handler_forbidden():
    exc = ForbiddenError()
    response = asyncio.run(domain_exception_handler(None, exc))
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_domain_exception_handler_task_not_found():
    exc = TaskNotFoundError(uuid.uuid4())
    response = asyncio.run(domain_exception_handler(None, exc))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_domain_exception_handler_generic_domain_error():
    from app.core.exceptions import DomainError
    exc = DomainError("something went wrong")
    response = asyncio.run(domain_exception_handler(None, exc))
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# roles.py – read
# ---------------------------------------------------------------------------

def test_read_roles_lists_only_what_exists(client, admin_user):
    """`admin_user` carries the `Administrador (papel)` profile row.

    It used to be an empty list because the enum supplied the membership and
    nothing had to exist for it. Since IAM F5 a user's power *is* a row, so
    the fixture creates one and the listing shows it.
    """
    token = _admin_token(admin_user)
    response = client.get(
        "/api/v1/roles/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert [row["name"] for row in response.json()] == ["Administrador (papel)"]


def test_read_roles_with_data(client, session, admin_user):
    ut = Role(name="Manager")
    session.add(ut)
    session.commit()

    token = _admin_token(admin_user)
    response = client.get(
        "/api/v1/roles/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    names = [t["name"] for t in response.json()]
    assert "Manager" in names


def test_read_roles_director_allowed(client, normal_user):
    """Any authenticated user can read roles."""
    token = _director_token(normal_user)
    response = client.get(
        "/api/v1/roles/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# roles.py – create
# ---------------------------------------------------------------------------

def test_create_role(client, admin_user):
    token = _admin_token(admin_user)
    response = client.post(
        "/api/v1/roles/",
        json={"name": "Finance"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Finance"
    assert "id" in data


def test_create_role_duplicate_name(client, session, admin_user):
    ut = Role(name="Legal")
    session.add(ut)
    session.commit()

    token = _admin_token(admin_user)
    response = client.post(
        "/api/v1/roles/",
        json={"name": "Legal"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]


def test_create_role_director_forbidden(client, normal_user):
    token = _director_token(normal_user)
    response = client.post(
        "/api/v1/roles/",
        json={"name": "HR"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# roles.py – update
# ---------------------------------------------------------------------------

def test_update_role(client, session, admin_user):
    ut = Role(name="OldName")
    session.add(ut)
    session.commit()
    session.refresh(ut)

    token = _admin_token(admin_user)
    response = client.patch(
        f"/api/v1/roles/{ut.id}",
        json={"name": "NewName"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "NewName"


def test_update_role_not_found(client, admin_user):
    token = _admin_token(admin_user)
    response = client.patch(
        f"/api/v1/roles/{uuid.uuid4()}",
        json={"name": "Anything"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_update_role_director_forbidden(client, session, normal_user):
    ut = Role(name="SomeType")
    session.add(ut)
    session.commit()
    session.refresh(ut)

    token = _director_token(normal_user)
    response = client.patch(
        f"/api/v1/roles/{ut.id}",
        json={"name": "Changed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# roles.py – delete
# ---------------------------------------------------------------------------

def test_delete_role(client, session, admin_user):
    ut = Role(name="ToDelete")
    session.add(ut)
    session.commit()
    session.refresh(ut)

    token = _admin_token(admin_user)
    response = client.delete(
        f"/api/v1/roles/{ut.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_role_not_found(client, admin_user):
    token = _admin_token(admin_user)
    response = client.delete(
        f"/api/v1/roles/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_delete_role_director_forbidden(client, session, normal_user):
    ut = Role(name="Protected")
    session.add(ut)
    session.commit()
    session.refresh(ut)

    token = _director_token(normal_user)
    response = client.delete(
        f"/api/v1/roles/{ut.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
