"""RBAC permission tests for Construction & Capital Improvement Project Tracking module."""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.enums import MilestoneStatus, ProjectStatus, UserRole
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.user import User


@pytest.fixture
def director_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="director_rbac@test.com",
        full_name="Director User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.DIRECTOR,
        cpf="84411604085",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def manager_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="manager_rbac@test.com",
        full_name="Manager User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
        cpf="12260662058",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="resident_rbac@test.com",
        full_name="Resident User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="46816405073",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def guest_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="guest_rbac@test.com",
        full_name="Guest User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.GUEST,
        cpf="38411475019",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(subject=str(admin_user.id))


@pytest.fixture
def director_token(director_user: User) -> str:
    return create_access_token(subject=str(director_user.id))


@pytest.fixture
def manager_token(manager_user: User) -> str:
    return create_access_token(subject=str(manager_user.id))


@pytest.fixture
def resident_token(resident_user: User) -> str:
    return create_access_token(subject=str(resident_user.id))


@pytest.fixture
def guest_token(guest_user: User) -> str:
    return create_access_token(subject=str(guest_user.id))


@pytest.fixture
def sample_project(session: Session) -> ConstructionProject:
    project = ConstructionProject(
        title="Construção Guarita Norte",
        total_budget=80000.0,
        status=ProjectStatus.PLANNED,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# Read Access Tests
# -----------------------------------------------------------------------------


def test_list_projects_allowed_roles(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    guest_token: str,
    sample_project: ConstructionProject,
):
    # Admin, Director, Manager, Resident should all be allowed (200 OK)
    for token in [admin_token, director_token, manager_token, resident_token]:
        resp = client.get("/api/v1/projects", headers=_auth(token))
        assert resp.status_code == status.HTTP_200_OK

    # Guest should be forbidden (403)
    resp_guest = client.get("/api/v1/projects", headers=_auth(guest_token))
    assert resp_guest.status_code == status.HTTP_403_FORBIDDEN

    # Unauthenticated should be 401
    resp_unauth = client.get("/api/v1/projects")
    assert resp_unauth.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_project_detail_allowed_roles(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    guest_token: str,
    sample_project: ConstructionProject,
):
    for token in [admin_token, director_token, manager_token, resident_token]:
        resp = client.get(
            f"/api/v1/projects/{sample_project.id}", headers=_auth(token)
        )
        assert resp.status_code == status.HTTP_200_OK

    resp_guest = client.get(
        f"/api/v1/projects/{sample_project.id}", headers=_auth(guest_token)
    )
    assert resp_guest.status_code == status.HTTP_403_FORBIDDEN


# -----------------------------------------------------------------------------
# Mutation Access: Projects & Milestones (Admin & Director only)
# -----------------------------------------------------------------------------


def test_create_project_rbac(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
):
    payload = {"title": "Reforma Salão de Festas", "total_budget": 20000.0}

    # Admin & Director: 201 Created
    assert client.post("/api/v1/projects", headers=_auth(admin_token), json=payload).status_code == status.HTTP_201_CREATED
    assert client.post("/api/v1/projects", headers=_auth(director_token), json=payload).status_code == status.HTTP_201_CREATED

    # Manager & Resident: 403 Forbidden
    assert client.post("/api/v1/projects", headers=_auth(manager_token), json=payload).status_code == status.HTTP_403_FORBIDDEN
    assert client.post("/api/v1/projects", headers=_auth(resident_token), json=payload).status_code == status.HTTP_403_FORBIDDEN


def test_update_and_delete_project_rbac(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    sample_project: ConstructionProject,
):
    # Manager & Resident cannot update
    assert client.put(f"/api/v1/projects/{sample_project.id}", headers=_auth(manager_token), json={"title": "Test"}).status_code == status.HTTP_403_FORBIDDEN
    assert client.put(f"/api/v1/projects/{sample_project.id}", headers=_auth(resident_token), json={"title": "Test"}).status_code == status.HTTP_403_FORBIDDEN

    # Director can update
    assert client.put(f"/api/v1/projects/{sample_project.id}", headers=_auth(director_token), json={"title": "Updated"}).status_code == status.HTTP_200_OK

    # Manager & Resident cannot delete
    assert client.delete(f"/api/v1/projects/{sample_project.id}", headers=_auth(manager_token)).status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(f"/api/v1/projects/{sample_project.id}", headers=_auth(resident_token)).status_code == status.HTTP_403_FORBIDDEN

    # Admin can delete
    assert client.delete(f"/api/v1/projects/{sample_project.id}", headers=_auth(admin_token)).status_code == status.HTTP_204_NO_CONTENT


def test_milestone_mutations_rbac(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    sample_project: ConstructionProject,
):
    m_payload = {"title": "Fase 1", "status": "IN_PROGRESS"}

    # Manager & Resident cannot add milestone
    assert client.post(f"/api/v1/projects/{sample_project.id}/milestones", headers=_auth(manager_token), json=m_payload).status_code == status.HTTP_403_FORBIDDEN
    assert client.post(f"/api/v1/projects/{sample_project.id}/milestones", headers=_auth(resident_token), json=m_payload).status_code == status.HTTP_403_FORBIDDEN

    # Director can add milestone
    resp = client.post(f"/api/v1/projects/{sample_project.id}/milestones", headers=_auth(director_token), json=m_payload)
    assert resp.status_code == status.HTTP_201_CREATED
    m_id = resp.json()["id"]

    # Manager & Resident cannot update or delete milestone
    assert client.put(f"/api/v1/projects/{sample_project.id}/milestones/{m_id}", headers=_auth(manager_token), json={"status": "DONE"}).status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(f"/api/v1/projects/{sample_project.id}/milestones/{m_id}", headers=_auth(resident_token)).status_code == status.HTTP_403_FORBIDDEN

    # Admin can delete milestone
    assert client.delete(f"/api/v1/projects/{sample_project.id}/milestones/{m_id}", headers=_auth(admin_token)).status_code == status.HTTP_204_NO_CONTENT


# -----------------------------------------------------------------------------
# Progress Update RBAC: Manager can create, but not delete
# -----------------------------------------------------------------------------


def test_project_update_rbac(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    sample_project: ConstructionProject,
):
    u_payload = {"title": "Visita Técnica", "content": "Fiscalização realizada"}

    # Resident cannot create update
    assert client.post(f"/api/v1/projects/{sample_project.id}/updates", headers=_auth(resident_token), json=u_payload).status_code == status.HTTP_403_FORBIDDEN

    # Manager can create update
    resp_mgr = client.post(f"/api/v1/projects/{sample_project.id}/updates", headers=_auth(manager_token), json=u_payload)
    assert resp_mgr.status_code == status.HTTP_201_CREATED
    u_id = resp_mgr.json()["id"]

    # Manager cannot delete update
    assert client.delete(f"/api/v1/projects/{sample_project.id}/updates/{u_id}", headers=_auth(manager_token)).status_code == status.HTTP_403_FORBIDDEN

    # Director can delete update
    assert client.delete(f"/api/v1/projects/{sample_project.id}/updates/{u_id}", headers=_auth(director_token)).status_code == status.HTTP_204_NO_CONTENT
