"""Unit and API integration tests for Occurrence management."""

from datetime import datetime
import json
import pytest

from app.core.exceptions import OccurrenceNotFoundError
from app.models.enums import (
    OccurrenceCategory,
    OccurrencePriority,
    OccurrenceStatus,
    UserRole,
)
from app.models.lot import Lot
from app.models.user import User
from app.schemas.lot import LotCreate
from app.schemas.occurrence import (
    OccurrenceCreate,
    OccurrenceStatusUpdate,
    TimelineNoteCreate,
)
from app.services.lot_service import LotService
from app.services.occurrence_service import OccurrenceService
from app.services.protocol_generator import generate_occurrence_protocol
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_protocol_generator_sequential(session: Session):
    year = datetime.utcnow().year
    p1 = generate_occurrence_protocol(session)
    assert p1 == f"OCO-{year}-000001"

    # Simulate creation of first ticket
    occ1_create = OccurrenceCreate(
        category=OccurrenceCategory.NOISE,
        title="Barulho excessivo",
        description="Som alto após as 22h",
    )
    user = User(
        email="test_protocol@example.com",
        full_name="Tester",
        hashed_password="hash",
        role=UserRole.GUEST,
        cpf="11122233344",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    OccurrenceService.create_occurrence(session, user, occ1_create)

    p2 = generate_occurrence_protocol(session)
    assert p2 == f"OCO-{year}-000002"


def test_create_occurrence_success(session: Session, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="C", lot_number="15"))

    occ_in = OccurrenceCreate(
        lot_id=lot.id,
        category=OccurrenceCategory.MAINTENANCE,
        title="Vazamento na alameda",
        description="Vazamento de água limpa em frente ao lote 15",
        photo_urls=["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        is_public=True,
        is_anonymous=False,
    )

    created = OccurrenceService.create_occurrence(session, normal_user, occ_in)

    assert created.id is not None
    assert created.protocol_number.startswith("OCO-")
    assert created.lot_id == lot.id
    assert created.lot_summary == "Quadra C, Lote 15"
    assert created.reporter_user_id == normal_user.id
    assert created.reporter_name == normal_user.full_name
    assert created.status == OccurrenceStatus.OPEN
    assert created.priority == OccurrencePriority.MEDIUM
    assert len(created.photo_urls) == 2
    assert created.photo_urls[0] == "https://example.com/photo1.jpg"

    # Check detail read includes initial timeline log
    detail = OccurrenceService.get_occurrence_by_id(session, normal_user, created.id)
    assert len(detail.timeline) == 1
    assert detail.timeline[0].note == "Ocorrência registrada no sistema"
    assert detail.timeline[0].status_to == OccurrenceStatus.OPEN


def test_update_occurrence_status_and_resolution(
    session: Session, admin_user: User, normal_user: User
):
    occ_in = OccurrenceCreate(
        category=OccurrenceCategory.SECURITY,
        title="Portão com defeito",
        description="Portão social não trava corretamente",
    )
    created = OccurrenceService.create_occurrence(session, normal_user, occ_in)

    # Admin updates status to IN_PROGRESS and assigns to self
    update_1 = OccurrenceStatusUpdate(
        status=OccurrenceStatus.IN_PROGRESS,
        priority=OccurrencePriority.HIGH,
        assigned_to_id=admin_user.id,
    )
    updated_1 = OccurrenceService.update_occurrence_status(
        session, admin_user, created.id, update_1
    )

    assert updated_1.status == OccurrenceStatus.IN_PROGRESS
    assert updated_1.priority == OccurrencePriority.HIGH
    assert updated_1.assigned_to_id == admin_user.id
    assert updated_1.assigned_to_name == admin_user.full_name
    assert updated_1.resolved_at is None

    # Admin resolves occurrence with resolution notes
    update_2 = OccurrenceStatusUpdate(
        status=OccurrenceStatus.RESOLVED,
        resolution_notes="Manutenção realizada e trava substituída.",
    )
    updated_2 = OccurrenceService.update_occurrence_status(
        session, admin_user, created.id, update_2
    )

    assert updated_2.status == OccurrenceStatus.RESOLVED
    assert updated_2.resolution_notes == "Manutenção realizada e trava substituída."
    assert updated_2.resolved_at is not None

    # Detail view timeline check
    detail = OccurrenceService.get_occurrence_by_id(session, admin_user, created.id)
    assert len(detail.timeline) == 3
    assert detail.timeline[1].status_from == OccurrenceStatus.OPEN
    assert detail.timeline[1].status_to == OccurrenceStatus.IN_PROGRESS
    assert detail.timeline[2].status_from == OccurrenceStatus.IN_PROGRESS
    assert detail.timeline[2].status_to == OccurrenceStatus.RESOLVED


def test_add_timeline_note_and_not_found(session: Session, admin_user: User):
    occ_in = OccurrenceCreate(
        category=OccurrenceCategory.PARKING,
        title="Carro em vaga alheia",
        description="Veículo ABC-1234 estacionado no lote vizinho",
    )
    created = OccurrenceService.create_occurrence(session, admin_user, occ_in)

    note_in = TimelineNoteCreate(
        note="Notificado o morador responsável",
        is_internal_only=True,
    )
    timeline_entry = OccurrenceService.add_timeline_note(
        session, admin_user, created.id, note_in
    )

    assert timeline_entry.id is not None
    assert timeline_entry.note == "Notificado o morador responsável"
    assert timeline_entry.is_internal_only is True

    # Test not found exception
    fake_id = datetime.utcnow()
    with pytest.raises(OccurrenceNotFoundError):
        OccurrenceService.get_occurrence_by_id(session, admin_user, admin_user.id)


def test_occurrences_api_endpoints(
    client: TestClient, normal_user: User
):
    from app.core.security import create_access_token

    token = create_access_token(subject=normal_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Create via API
    payload = {
        "category": "RULES_VIOLATION",
        "title": "Lixo fora do horário",
        "description": "Sacolas de lixo colocadas na calçada no domingo",
        "is_public": True,
        "is_anonymous": False,
    }
    response = client.post(
        "/api/v1/occurrences", json=payload, headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["protocol_number"].startswith("OCO-")
    assert data["category"] == "RULES_VIOLATION"
    occ_id = data["id"]

    # List via API with search & category filter
    list_res = client.get(
        "/api/v1/occurrences?category=RULES_VIOLATION&search=Lixo",
        headers=headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert list_data["items"][0]["id"] == occ_id

    # Get details via API
    detail_res = client.get(
        f"/api/v1/occurrences/{occ_id}", headers=headers
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == occ_id
    assert len(detail_data["timeline"]) == 1

    # Add timeline note via API
    note_res = client.post(
        f"/api/v1/occurrences/{occ_id}/timeline",
        json={"note": "Fotos anexadas no grupo", "is_internal_only": False},
        headers=headers,
    )
    assert note_res.status_code == 201
    assert note_res.json()["note"] == "Fotos anexadas no grupo"
