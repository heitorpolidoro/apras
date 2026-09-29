"""Tests for Construction & Capital Improvement Project Tracking module (T007)."""

import base64
import logging
import uuid
from datetime import date
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import clock
from app.core.permissions import ROUTE_PERMISSIONS, UNGUARDED_ROUTES
from app.core.security import create_access_token, get_password_hash
from app.core.urls import public_project_cover_url
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
from app.models.user import User
from app.services import project_service as project_service_module
from app.services.media_service import MAX_FILE_SIZE
from app.services.storage_service import LocalStorageProvider
from tests.conftest import make_user


@pytest.fixture
def director_user(session: Session) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="director@test.com",
        full_name="Director User",
        hashed_password=get_password_hash("password123"),
        profile="DIRECTOR",
        cpf="84411604085",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def manager_user(session: Session) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="manager@test.com",
        full_name="Manager User",
        hashed_password=get_password_hash("password123"),
        profile="MANAGER",
        cpf="12260662058",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_user(session: Session) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="resident@test.com",
        full_name="Resident User",
        hashed_password=get_password_hash("password123"),
        profile="RESIDENT",
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
    resp = client.get(f"/api/v1/projects/{fake_id}", headers=_auth_headers(admin_token))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_project_success(client: TestClient, admin_token: str, session: Session):
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
    assert m_up_data["completion_date"] == clock.today_utc().isoformat()

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
        "photos": [
            "https://cdn.example.com/pole1.png",
            "https://cdn.example.com/pole2.png",
        ],
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


def test_detail_json_never_reaches_a_milestone_response_schema(
    client: TestClient, admin_token: str, session: Session
):
    """APRAS-114: the stage-detail column is invisible to the API.

    `detail_json` is written only by an operator script and read only by the
    report renderer, so no request or response schema lists it. All four
    milestone schemas enumerate their fields explicitly, which is what makes
    these four checks exhaustive.

    Two anti-vacuity guards, because both halves of this case are the shape
    that passes while asserting nothing: the serialized set is proven
    non-empty *before* it is quantified over, and `ProjectMilestone` is
    asserted to carry the column -- otherwise the whole test would pass on a
    branch where the column was never added.
    """
    from app.models.project import ProjectMilestone as MilestoneModel
    from app.schemas.project import (
        MilestoneBase,
        MilestoneCreate,
        MilestoneRead,
        MilestoneUpdate,
    )

    project = ConstructionProject(
        title="Sede Social",
        status=ProjectStatus.IN_PROGRESS,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    session.add_all(
        [
            ProjectMilestone(
                project_id=project.id,
                title="Demolições",
                status=MilestoneStatus.DONE,
                display_order=1,
                completion_date=date(2026, 9, 11),
                detail_json={
                    "pct": 49.55882352941177,
                    "start": "2026-09-25",
                    "leaves": [
                        {
                            "name": "DEMOLIÇÃO DE PAREDES",
                            "pct": 0.0,
                            "start": "2026-09-25",
                            "finish": "2026-10-06",
                        }
                    ],
                },
            ),
            ProjectMilestone(
                project_id=project.id,
                title="Instalações Hidraulicas",
                status=MilestoneStatus.NEXT_STEPS,
                display_order=2,
                detail_json=None,
            ),
        ]
    )
    session.commit()

    resp = client.get(
        f"/api/v1/projects/{project.id}", headers=_auth_headers(admin_token)
    )

    assert resp.status_code == status.HTTP_200_OK
    milestones = resp.json()["milestones"]
    assert len(milestones) >= 1
    for milestone in milestones:
        assert "detail_json" not in milestone

    for schema in (MilestoneBase, MilestoneCreate, MilestoneUpdate, MilestoneRead):
        assert "detail_json" not in schema.model_fields

    # The positive control: the column exists, so the four checks above are
    # about a key that could have leaked rather than one that never existed.
    assert "detail_json" in MilestoneModel.model_fields


# -----------------------------------------------------------------------------
# The cover photo, uploaded rather than pasted (APRAS-104)
#
# `PUT /api/v1/projects/{id}/cover-photo` and its `DELETE`, the derived
# `cover_photo_display_url`, and the orphan the replace leaves behind.
# -----------------------------------------------------------------------------


COVER_URL_TEMPLATE = "/api/v1/projects/{id}/cover-photo"

#: A real, Pillow-decodable 1x1 PNG. `set_cover_photo` opens the bytes, so a
#: `b"not-an-image"` payload would be refused for the wrong reason.
COVER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
    "IQAAAABJRU5ErkJggg=="
)

#: A second decodable PNG, distinguishable from the first by value: a replace
#: test that stored the same bytes twice could not tell one object from the
#: other.
COVER_PNG_B = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9"
    "awAAAABJRU5ErkJggg=="
)


@pytest.fixture(name="cover_storage")
def cover_storage_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A **real** `LocalStorageProvider` rooted in `tmp_path`.

    Real and not a stub, exactly as `test_tenant_profile.py`'s `storage`
    fixture is: "the previous file no longer exists on disk" is only worth
    asserting when a file was really written, and the production provider is
    part of what is under test.
    """
    provider = LocalStorageProvider(tmp_path / "uploads")
    monkeypatch.setattr(project_service_module, "_storage_provider", provider)
    return provider


def _stored_path(provider: LocalStorageProvider, url: str) -> Path:
    return provider.base_dir / url.removeprefix("/static/uploads/")


def _stored_files(provider: LocalStorageProvider) -> list[Path]:
    return sorted(p for p in provider.base_dir.rglob("*") if p.is_file())


def _new_project(session: Session, **kwargs) -> ConstructionProject:
    kwargs.setdefault("title", "Modernização das Portarias")
    project = ConstructionProject(**kwargs)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _put_cover(
    client: TestClient,
    token: str,
    project_id,
    *,
    payload: bytes = COVER_PNG,
    filename: str = "capa.png",
    content_type: str = "image/png",
):
    return client.put(
        COVER_URL_TEMPLATE.format(id=project_id),
        headers=_auth_headers(token),
        files={"file": (filename, payload, content_type)},
    )


def test_the_upload_stores_the_bytes_and_records_what_the_provider_returned(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
):
    """ER2. `cover_photo_url` is **storage truth**: it equals the second
    element `save_file` returned, captured off the provider rather than
    retyped, and the bytes really reached `base_dir`.

    The derived display URL is then asserted on **both** read routes. The
    detail route is named explicitly because it builds its payload inside
    `ProjectService.get_project_detail`, outside the router's `_project_read`
    helper, and that is exactly the shape that inherits the field and answers
    `null` forever.
    """
    project = _new_project(session)
    returned: list[tuple[str, str]] = []
    original_save = cover_storage.save_file

    def recording_save(*args, **kwargs):
        result = original_save(*args, **kwargs)
        returned.append(result)
        return result

    cover_storage.save_file = recording_save  # type: ignore[method-assign]

    resp = _put_cover(client, admin_token, project.id)

    assert resp.status_code == status.HTTP_200_OK
    assert len(returned) == 1
    _saved_path, saved_url = returned[0]
    assert resp.json()["cover_photo_url"] == saved_url

    session.expire_all()
    assert session.get(ConstructionProject, project.id).cover_photo_url == saved_url
    on_disk = _stored_path(cover_storage, saved_url)
    assert on_disk.exists()
    assert on_disk.read_bytes() == COVER_PNG

    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    expected_display = public_project_cover_url(tenant.slug, project.id)

    listed = client.get("/api/v1/projects", headers=_auth_headers(admin_token)).json()
    entry = next(item for item in listed["items"] if item["id"] == str(project.id))
    assert entry["cover_photo_display_url"] == expected_display

    detail = client.get(
        f"/api/v1/projects/{project.id}", headers=_auth_headers(admin_token)
    ).json()
    assert detail["cover_photo_display_url"] == expected_display
    # The two read routes answer the *same* value for the same project: the
    # detail route inheriting the field and answering `null` is the defect
    # this line exists for.
    assert detail["cover_photo_display_url"] == entry["cover_photo_display_url"]


def test_a_third_party_stored_value_is_its_own_display_url(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
):
    """The second rung of §A.2, and a live write path rather than a migration
    tail: `backend/scripts/sync_obras_from_drive.py` writes URLs of this shape
    on every run, and the provider cannot read them back."""
    project = _new_project(session, cover_photo_url="https://cdn.example/capa.jpg")

    detail = client.get(
        f"/api/v1/projects/{project.id}", headers=_auth_headers(admin_token)
    ).json()

    assert detail["cover_photo_display_url"] == "https://cdn.example/capa.jpg"


def test_a_project_with_no_cover_has_a_null_display_url(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
):
    project = _new_project(session, cover_photo_url=None)

    detail = client.get(
        f"/api/v1/projects/{project.id}", headers=_auth_headers(admin_token)
    ).json()

    assert detail["cover_photo_display_url"] is None


# ---------------------------------------------------------------------------
# ER6 -- the two refusals, both anchored on a cover that already existed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "filename", "content_type", "words"),
    [
        pytest.param(
            b"nao sou uma imagem",
            "notas.txt",
            "text/plain",
            "JPEG, PNG, WebP",
            id="type",
        ),
        pytest.param(
            b"\x00" * (MAX_FILE_SIZE + 1),
            "enorme.png",
            "image/png",
            "5MB",
            id="size",
        ),
    ],
)
def test_a_refused_cover_upload_leaves_the_previous_one_exactly_as_it_was(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
    payload: bytes,
    filename: str,
    content_type: str,
    words: str,
):
    """ER6, in three steps and in that order.

    The cover is set **first**, by value, so "unchanged" cannot be satisfied by
    there never having been anything: the assertion compares the column against
    the URL the successful upload stored, not against `None`.

    It also pins that validation runs **before** any write: exactly one file is
    in `base_dir` afterwards, so the refused upload wrote no object, and the
    first object was not deleted on the refusal path either.
    """
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200
    session.expire_all()
    original = session.get(ConstructionProject, project.id).cover_photo_url
    assert original is not None
    original_file = _stored_path(cover_storage, original)
    assert original_file.exists()

    resp = _put_cover(
        client,
        admin_token,
        project.id,
        payload=payload,
        filename=filename,
        content_type=content_type,
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert words in resp.json()["detail"]

    session.expire_all()
    assert session.get(ConstructionProject, project.id).cover_photo_url == original
    assert original_file.exists()
    assert _stored_files(cover_storage) == [original_file]


# ---------------------------------------------------------------------------
# ER7 -- exactly one stored object per project, and the ordering that holds it
# ---------------------------------------------------------------------------


def test_replacing_a_cover_photo_leaves_exactly_one_stored_object(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
):
    """ER7. A real `LocalStorageProvider`, so "no longer exists" is a real
    stat of a file that was really written."""
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200
    session.expire_all()
    first = _stored_path(
        cover_storage, session.get(ConstructionProject, project.id).cover_photo_url
    )
    assert first.exists()

    assert (
        _put_cover(client, admin_token, project.id, payload=COVER_PNG_B).status_code
        == 200
    )

    session.expire_all()
    second = _stored_path(
        cover_storage, session.get(ConstructionProject, project.id).cover_photo_url
    )
    assert second != first
    assert not first.exists()
    assert second.exists()
    assert second.read_bytes() == COVER_PNG_B
    assert _stored_files(cover_storage) == [second]


def test_a_third_party_previous_value_triggers_no_delete_at_all(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
    monkeypatch: pytest.MonkeyPatch,
):
    """Somebody else's file is left alone (APRAS-61): `resolve_stored_path`
    answers `None` for a value the provider did not mint, so `delete_file` is
    never reached."""
    project = _new_project(session, cover_photo_url="https://cdn.example/capa.jpg")
    deleted: list[str] = []
    monkeypatch.setattr(
        cover_storage,
        "delete_file",
        lambda file_path: deleted.append(file_path) or True,
    )

    assert _put_cover(client, admin_token, project.id).status_code == 200

    assert deleted == []


def test_a_failed_commit_leaves_the_previous_object_on_disk(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
    monkeypatch: pytest.MonkeyPatch,
):
    """The test that actually pins §C's ordering.

    "The old file is gone and the new one is there" holds just as well for a
    delete-first implementation, so it is not the ordering's evidence. This is:
    with the commit made to fail, a write-set-commit-delete implementation has
    not reached the delete yet and the previous object is still on disk, while
    delete-first has already removed the object the project still points at.
    """
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200
    session.expire_all()
    first = _stored_path(
        cover_storage, session.get(ConstructionProject, project.id).cover_photo_url
    )
    assert first.exists()

    def exploding_commit():
        raise RuntimeError("commit refused, deliberately")

    monkeypatch.setattr(session, "commit", exploding_commit)

    with pytest.raises(RuntimeError, match="commit refused"):
        _put_cover(client, admin_token, project.id, payload=COVER_PNG_B)

    assert first.exists()


def test_a_refused_cleanup_is_logged_and_does_not_fail_the_request(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """ER7's fourth test. Without it, §C's `logger.warning` is a line nobody
    would notice was never written -- `LocalStorageProvider.delete_file` is
    `except Exception: return False` with no log of its own, so on local disk a
    genuine failure is invisible today."""
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200
    session.expire_all()
    original = session.get(ConstructionProject, project.id).cover_photo_url
    monkeypatch.setattr(cover_storage, "delete_file", lambda _file_path: False)

    with caplog.at_level(logging.WARNING, logger="app.services.project_service"):
        resp = _put_cover(client, admin_token, project.id, payload=COVER_PNG_B)

    # The failed cleanup must not fail the call: the new object is stored and
    # the column points at it.
    assert resp.status_code == status.HTTP_200_OK

    records = [
        record
        for record in caplog.records
        if record.name == "app.services.project_service"
        and record.levelno == logging.WARNING
    ]
    assert len(records) == 1
    message = records[0].getMessage()
    assert str(project.id) in message
    assert original in message


# ---------------------------------------------------------------------------
# ER8 -- projects:read is not projects:update
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["put", "delete"])
def test_a_reader_without_projects_update_is_refused_both_cover_routes(
    client: TestClient,
    session: Session,
    admin_token: str,
    resident_token: str,
    cover_storage: LocalStorageProvider,
    method: str,
):
    """ER8. `resident_user` holds `projects:read` and not `projects:update`.

    The column is read back **by value** after `expire_all()`, so a refusal
    that still touched the column cannot hide behind a 403.
    """
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200
    session.expire_all()
    original = session.get(ConstructionProject, project.id).cover_photo_url
    assert original is not None

    if method == "put":
        resp = _put_cover(client, resident_token, project.id, payload=COVER_PNG_B)
    else:
        resp = client.delete(
            COVER_URL_TEMPLATE.format(id=project.id),
            headers=_auth_headers(resident_token),
        )

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    session.expire_all()
    assert session.get(ConstructionProject, project.id).cover_photo_url == original


def test_the_cover_routes_are_registered_the_way_the_catalogue_says():
    """The registry is the contract (§E): both writes map to `projects:update`
    and neither is unguarded, while the public read is the other way round."""
    put_key = ("PUT", "/api/v1/projects/{id}/cover-photo")
    delete_key = ("DELETE", "/api/v1/projects/{id}/cover-photo")
    public_key = ("GET", "/api/v1/public/tenants/{slug}/projects/{project_id}/cover")

    assert ROUTE_PERMISSIONS[put_key] == "projects:update"
    assert ROUTE_PERMISSIONS[delete_key] == "projects:update"
    assert put_key not in UNGUARDED_ROUTES
    assert delete_key not in UNGUARDED_ROUTES

    assert public_key in UNGUARDED_ROUTES
    assert public_key not in ROUTE_PERMISSIONS


# ---------------------------------------------------------------------------
# ER9 -- the DELETE's functional behaviour
# ---------------------------------------------------------------------------


def test_the_delete_route_clears_the_column_and_removes_the_object(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
):
    """ER9. 200 with `ProjectRead` (matching `DELETE /tenant-profile/logo`),
    both cover fields `null`, the object gone, and the public route now 404."""
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200
    session.expire_all()
    stored = session.get(ConstructionProject, project.id).cover_photo_url
    on_disk = _stored_path(cover_storage, stored)
    assert on_disk.exists()
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)

    resp = client.delete(
        COVER_URL_TEMPLATE.format(id=project.id), headers=_auth_headers(admin_token)
    )

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["cover_photo_url"] is None
    assert body["cover_photo_display_url"] is None
    # The read schema, not an empty 204 body: the id proves which body shape
    # came back.
    assert body["id"] == str(project.id)

    session.expire_all()
    assert session.get(ConstructionProject, project.id).cover_photo_url is None
    assert not on_disk.exists()

    public = client.get(
        f"/api/v1/public/tenants/{tenant.slug}/projects/{project.id}/cover"
    )
    assert public.status_code == status.HTTP_404_NOT_FOUND


def test_a_second_delete_of_the_same_cover_is_still_a_200(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
):
    """Idempotent: no 404 and no 500 on the second call, and the same body."""
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200

    first = client.delete(
        COVER_URL_TEMPLATE.format(id=project.id), headers=_auth_headers(admin_token)
    )
    second = client.delete(
        COVER_URL_TEMPLATE.format(id=project.id), headers=_auth_headers(admin_token)
    )

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert second.json()["cover_photo_url"] is None
    assert second.json()["cover_photo_display_url"] is None
    assert second.json()["id"] == first.json()["id"]


def test_undecodable_bytes_are_refused_even_with_an_accepted_mime_type(
    client: TestClient,
    session: Session,
    admin_token: str,
    cover_storage: LocalStorageProvider,
):
    """The third check in §B's sequence, and the only one the declared type
    cannot stand in for.

    The declared MIME type is a **claim the client makes**; Pillow is the
    check. A caller sending `image/png` with bytes that are not a PNG passes
    the size rule and the type rule and is refused by the decode -- still 400,
    still before any write, and with the previous cover still exactly as it was.
    """
    project = _new_project(session)
    assert _put_cover(client, admin_token, project.id).status_code == 200
    session.expire_all()
    original = session.get(ConstructionProject, project.id).cover_photo_url
    original_file = _stored_path(cover_storage, original)

    resp = _put_cover(
        client,
        admin_token,
        project.id,
        payload=b"esses bytes nao sao um PNG, apesar do cabecalho dizer que sao",
        filename="mentirosa.png",
        content_type="image/png",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "JPEG, PNG, WebP" in resp.json()["detail"]
    session.expire_all()
    assert session.get(ConstructionProject, project.id).cover_photo_url == original
    assert original_file.exists()
    assert _stored_files(cover_storage) == [original_file]
