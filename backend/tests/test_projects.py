"""Tests for Construction & Capital Improvement Project Tracking module (T007)."""

from datetime import date
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
        email="director@test.com",
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
        email="manager@test.com",
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
        email="resident@test.com",
        full_name="Resident User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="46816405073",
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


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# Project CRUD Tests
# -----------------------------------------------------------------------------


def test_create_project_success(client: TestClient, admin_token: str):
    payload = {
        "title": "Reforma da Quadra Poliesportiva",
        "description": "Pintura epóxi e troca de redes",
        "contractor_name": "Construtora Alfa Ltda",
        "total_budget": 150000.0,
        "executed_budget": 25000.0,
        "physical_progress_pct": 16.5,
        "start_date": "2026-09-01",
        "estimated_completion_date": "2026-12-15",
        "status": "IN_PROGRESS",
        "cover_photo_url": "https://example.com/cover.jpg",
    }
    resp = client.post(
        "/api/v1/projects",
        headers=_auth_headers(admin_token),
        json=payload,
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["contractor_name"] == payload["contractor_name"]
    assert data["total_budget"] == 150000.0
    assert data["executed_budget"] == 25000.0
    assert data["physical_progress_pct"] == 16.5
    assert data["status"] == "IN_PROGRESS"
    assert data["cover_photo_url"] == payload["cover_photo_url"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_project_invalid_progress_pct(client: TestClient, admin_token: str):
    payload = {
        "title": "Invalid Project",
        "total_budget": 1000.0,
        "physical_progress_pct": 105.0,  # Invalid: > 100
    }
    resp = client.post(
        "/api/v1/projects",
        headers=_auth_headers(admin_token),
        json=payload,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_project_negative_budget(client: TestClient, admin_token: str):
    payload = {
        "title": "Invalid Project",
        "total_budget": -50.0,  # Invalid: < 0
    }
    resp = client.post(
        "/api/v1/projects",
        headers=_auth_headers(admin_token),
        json=payload,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_projects_with_filtering_and_pagination(
    client: TestClient, admin_token: str, session: Session
):
    # Setup test projects
    p1 = ConstructionProject(
        title="Project 1",
        status=ProjectStatus.PLANNED,
        total_budget=50000.0,
        executed_budget=0.0,
        physical_progress_pct=0.0,
    )
    p2 = ConstructionProject(
        title="Project 2",
        status=ProjectStatus.IN_PROGRESS,
        total_budget=80000.0,
        executed_budget=20000.0,
        physical_progress_pct=25.0,
    )
    p3 = ConstructionProject(
        title="Project 3",
        status=ProjectStatus.COMPLETED,
        total_budget=120000.0,
        executed_budget=120000.0,
        physical_progress_pct=100.0,
    )
    session.add_all([p1, p2, p3])
    session.commit()

    # List all
    resp = client.get("/api/v1/projects", headers=_auth_headers(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) >= 3

    # Filter by status
    resp_filtered = client.get(
        "/api/v1/projects?status=IN_PROGRESS", headers=_auth_headers(admin_token)
    )
    assert resp_filtered.status_code == status.HTTP_200_OK
    filtered_body = resp_filtered.json()
    assert filtered_body["total"] == 1
    assert filtered_body["items"][0]["title"] == "Project 2"


def test_get_project_detail_success(
    client: TestClient, admin_token: str, admin_user: User, session: Session
):
    project = ConstructionProject(
        title="Piscina Adulto",
        description="Troca de azulejos",
        total_budget=60000.0,
        status=ProjectStatus.IN_PROGRESS,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    m1 = ProjectMilestone(
        project_id=project.id,
        title="Demolição",
        status=MilestoneStatus.DONE,
        display_order=1,
        completion_date=date(2026, 8, 1),
    )
    m2 = ProjectMilestone(
        project_id=project.id,
        title="Impermeabilização",
        status=MilestoneStatus.IN_PROGRESS,
        display_order=2,
        due_date=date(2026, 9, 1),
    )
    session.add_all([m1, m2])

    u1 = ProjectUpdate(
        project_id=project.id,
        author_id=admin_user.id,
        title="Início dos trabalhos",
        content="Equipe no local",
        photos_json='["https://example.com/p1.jpg", "https://example.com/p2.jpg"]',
        cost_impact=5000.0,
    )
    session.add(u1)
    session.commit()

    resp = client.get(
        f"/api/v1/projects/{project.id}", headers=_auth_headers(admin_token)
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["id"] == str(project.id)
    assert data["title"] == "Piscina Adulto"
    assert len(data["milestones"]) == 2
    assert data["milestones"][0]["title"] == "Demolição"
    assert data["milestones"][0]["status"] == "DONE"
    assert len(data["updates"]) == 1
    assert data["updates"][0]["title"] == "Início dos trabalhos"
    assert data["updates"][0]["photos"] == [
        "https://example.com/p1.jpg",
        "https://example.com/p2.jpg",
    ]
    assert data["updates"][0]["author"]["email"] == admin_user.email


def test_get_project_not_found(client: TestClient, admin_token: str):
    fake_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/projects/{fake_id}", headers=_auth_headers(admin_token)
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_project_success(
    client: TestClient, admin_token: str, session: Session
):
    project = ConstructionProject(
        title="Academia Nova",
        total_budget=40000.0,
        status=ProjectStatus.PLANNED,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    update_payload = {
        "title": "Academia e Sala de Pilates",
        "total_budget": 55000.0,
        "physical_progress_pct": 50.0,
        "status": "IN_PROGRESS",
    }
    resp = client.put(
        f"/api/v1/projects/{project.id}",
        headers=_auth_headers(admin_token),
        json=update_payload,
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["title"] == "Academia e Sala de Pilates"
    assert body["total_budget"] == 55000.0
    assert body["physical_progress_pct"] == 50.0
    assert body["status"] == "IN_PROGRESS"


def test_delete_project_cascade(
    client: TestClient, admin_token: str, admin_user: User, session: Session
):
    project = ConstructionProject(
        title="Espaço Gourmet",
        total_budget=30000.0,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    milestone = ProjectMilestone(
        project_id=project.id,
        title="Fundação",
    )
    update = ProjectUpdate(
        project_id=project.id,
        author_id=admin_user.id,
        title="Log 1",
        content="Iniciado",
    )
    session.add_all([milestone, update])
    session.commit()

    resp = client.delete(
        f"/api/v1/projects/{project.id}",
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify deleted
    assert session.get(ConstructionProject, project.id) is None
    assert session.get(ProjectMilestone, milestone.id) is None
    assert session.get(ProjectUpdate, update.id) is None


# -----------------------------------------------------------------------------
# Milestone Management Tests
# -----------------------------------------------------------------------------


def test_milestone_crud_and_auto_completion_date(
    client: TestClient, admin_token: str, session: Session
):
    project = ConstructionProject(title="Portaria Eletrônica")
    session.add(project)
    session.commit()
    session.refresh(project)

    # 1. Create Milestone (NEXT_STEPS)
    m_payload = {
        "title": "Passagem de Cabos",
        "description": "Fiação de fibra",
        "status": "NEXT_STEPS",
        "due_date": "2026-09-10",
        "display_order": 1,
    }
    resp = client.post(
        f"/api/v1/projects/{project.id}/milestones",
        headers=_auth_headers(admin_token),
        json=m_payload,
    )
    assert resp.status_code == status.HTTP_201_CREATED
    m_data = resp.json()
    assert m_data["title"] == "Passagem de Cabos"
    assert m_data["status"] == "NEXT_STEPS"
    assert m_data["completion_date"] is None
    milestone_id = m_data["id"]

    # 2. Update Milestone to DONE without explicit completion_date -> should auto-set today
    update_payload = {
        "status": "DONE",
    }
    resp_up = client.put(
        f"/api/v1/projects/{project.id}/milestones/{milestone_id}",
        headers=_auth_headers(admin_token),
        json=update_payload,
    )
    assert resp_up.status_code == status.HTTP_200_OK
    m_up_data = resp_up.json()
    assert m_up_data["status"] == "DONE"
    assert m_up_data["completion_date"] == date.today().isoformat()

    # 3. Delete milestone
    resp_del = client.delete(
        f"/api/v1/projects/{project.id}/milestones/{milestone_id}",
        headers=_auth_headers(admin_token),
    )
    assert resp_del.status_code == status.HTTP_204_NO_CONTENT


# -----------------------------------------------------------------------------
# Project Update & Cost Impact Tests
# -----------------------------------------------------------------------------


def test_create_project_update_with_cost_impact(
    client: TestClient, manager_token: str, manager_user: User, session: Session
):
    project = ConstructionProject(
        title="Iluminação Solar",
        total_budget=50000.0,
        executed_budget=10000.0,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    update_payload = {
        "title": "Instalação de Postes Solares",
        "content": "5 postes instalados na alameda principal com fotos anexas.",
        "photos": ["https://cdn.example.com/pole1.png", "https://cdn.example.com/pole2.png"],
        "cost_impact": 7500.0,
    }
    resp = client.post(
        f"/api/v1/projects/{project.id}/updates",
        headers=_auth_headers(manager_token),
        json=update_payload,
    )
    assert resp.status_code == status.HTTP_201_CREATED
    u_data = resp.json()
    assert u_data["title"] == update_payload["title"]
    assert u_data["photos"] == update_payload["photos"]
    assert u_data["cost_impact"] == 7500.0
    assert u_data["author_id"] == str(manager_user.id)

    # Verify executed budget on project was incremented
    session.refresh(project)
    assert project.executed_budget == 17500.0


def test_delete_project_update(
    client: TestClient, admin_token: str, admin_user: User, session: Session
):
    project = ConstructionProject(title="Jardim Central")
    session.add(project)
    session.commit()
    session.refresh(project)

    update = ProjectUpdate(
        project_id=project.id,
        author_id=admin_user.id,
        title="Plantio",
        content="Mudas plantadas",
    )
    session.add(update)
    session.commit()
    session.refresh(update)

    resp = client.delete(
        f"/api/v1/projects/{project.id}/updates/{update.id}",
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ProjectUpdate, update.id) is None


def test_milestone_and_update_not_found_errors(
    client: TestClient, admin_token: str, session: Session
):
    project = ConstructionProject(title="Portaria Central")
    session.add(project)
    session.commit()
    session.refresh(project)

    fake_id = uuid.uuid4()

    # Create milestone for non-existent project
    resp = client.post(
        f"/api/v1/projects/{fake_id}/milestones",
        headers=_auth_headers(admin_token),
        json={"title": "Test"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Update non-existent milestone
    resp = client.put(
        f"/api/v1/projects/{project.id}/milestones/{fake_id}",
        headers=_auth_headers(admin_token),
        json={"title": "Test"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Delete non-existent milestone
    resp = client.delete(
        f"/api/v1/projects/{project.id}/milestones/{fake_id}",
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # Delete non-existent update
    resp = client.delete(
        f"/api/v1/projects/{project.id}/updates/{fake_id}",
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

