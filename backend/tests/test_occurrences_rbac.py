"""RBAC and visibility security tests for Occurrences."""

import pytest

from app.core.exceptions import OccurrenceAccessForbiddenError
from app.models.enums import OccurrenceCategory, OccurrenceStatus, UserRole
from app.models.user import User
from app.schemas.occurrence import (
    OccurrenceCreate,
    OccurrenceStatusUpdate,
    TimelineNoteCreate,
)
from app.services.occurrence_service import OccurrenceService
from sqlmodel import Session


def test_private_occurrence_visibility(
    session: Session, admin_user: User, normal_user: User
):
    # Create standard resident user
    resident = User(
        email="resident_private@example.com",
        full_name="Morador Privado",
        hashed_password="hash",
        role=UserRole.GUEST,
        cpf="11122233344",
    )
    other_resident = User(
        email="resident2@example.com",
        full_name="Outro Morador",
        hashed_password="hash",
        role=UserRole.GUEST,
        cpf="22233344455",
    )
    session.add(resident)
    session.add(other_resident)
    session.commit()

    # resident creates private occurrence
    occ_in = OccurrenceCreate(
        category=OccurrenceCategory.OTHER,
        title="Assunto Particular",
        description="Reclamação privada sobre infiltração",
        is_public=False,
        is_anonymous=False,
    )
    occ = OccurrenceService.create_occurrence(session, resident, occ_in)

    # Reporter can see it
    detail_reporter = OccurrenceService.get_occurrence_by_id(session, resident, occ.id)
    assert detail_reporter.id == occ.id

    # Admin can see it
    detail_admin = OccurrenceService.get_occurrence_by_id(session, admin_user, occ.id)
    assert detail_admin.id == occ.id

    # Other resident gets access forbidden
    with pytest.raises(OccurrenceAccessForbiddenError):
        OccurrenceService.get_occurrence_by_id(session, other_resident, occ.id)

    # Other resident list filter does NOT include private occurrence
    items, total = OccurrenceService.get_occurrences(session, other_resident)
    matching = [i for i in items if i.id == occ.id]
    assert len(matching) == 0


def test_anonymous_occurrence_masking(
    session: Session, admin_user: User, normal_user: User
):
    resident = User(
        email="resident_anon_reporter@example.com",
        full_name="Autor Anônimo",
        hashed_password="hash",
        role=UserRole.GUEST,
        cpf="33344455566",
    )
    other_resident = User(
        email="resident_anon_viewer@example.com",
        full_name="Leitor Residente",
        hashed_password="hash",
        role=UserRole.GUEST,
        cpf="44455566677",
    )
    session.add(resident)
    session.add(other_resident)
    session.commit()

    # resident creates ANONYMOUS PUBLIC occurrence
    occ_in = OccurrenceCreate(
        category=OccurrenceCategory.NOISE,
        title="Festa barulhenta na quadra",
        description="Música alta até 3h",
        is_public=True,
        is_anonymous=True,
    )
    occ = OccurrenceService.create_occurrence(session, resident, occ_in)

    # Other resident views occurrence: reporter info must be masked as 'Anônimo' and None
    read_other = OccurrenceService.get_occurrence_by_id(session, other_resident, occ.id)
    assert read_other.reporter_name == "Anônimo"
    assert read_other.reporter_user_id is None
    assert len(read_other.timeline) == 1
    assert read_other.timeline[0].actor_name == "Anônimo"

    # Admin views occurrence: reporter identity is revealed for audit
    read_admin = OccurrenceService.get_occurrence_by_id(session, admin_user, occ.id)
    assert read_admin.reporter_name == resident.full_name
    assert read_admin.reporter_user_id == resident.id
    assert read_admin.timeline[0].actor_name == resident.full_name


def test_internal_timeline_note_stripping(session: Session, admin_user: User):
    resident = User(
        email="resident_timeline@example.com",
        full_name="Morador Timeline",
        hashed_password="hash",
        role=UserRole.GUEST,
        cpf="55566677788",
    )
    session.add(resident)
    session.commit()

    # Public occurrence created by resident
    occ_in = OccurrenceCreate(
        category=OccurrenceCategory.MAINTENANCE,
        title="Lâmpada queimada na praça",
        description="Poste 12 sem luz",
        is_public=True,
    )
    occ = OccurrenceService.create_occurrence(session, resident, occ_in)

    # Admin adds internal note
    OccurrenceService.add_timeline_note(
        session,
        admin_user,
        occ.id,
        TimelineNoteCreate(
            note="Solicitada cotação emergencial com fornecedor XYZ",
            is_internal_only=True,
        ),
    )

    # Admin adds public note
    OccurrenceService.add_timeline_note(
        session,
        admin_user,
        occ.id,
        TimelineNoteCreate(
            note="Equipe técnica acionada para troca amanhã",
            is_internal_only=False,
        ),
    )

    # Admin sees 3 timeline entries (initial + internal + public)
    detail_admin = OccurrenceService.get_occurrence_by_id(session, admin_user, occ.id)
    assert len(detail_admin.timeline) == 3

    # Resident sees 2 timeline entries (internal stripped out)
    detail_resident = OccurrenceService.get_occurrence_by_id(session, resident, occ.id)
    assert len(detail_resident.timeline) == 2
    notes = [t.note for t in detail_resident.timeline]
    assert "Solicitada cotação emergencial com fornecedor XYZ" not in notes
    assert "Equipe técnica acionada para troca amanhã" in notes


def test_status_update_permissions(session: Session):
    resident = User(
        email="resident_update@example.com",
        full_name="Morador Sem Permissão",
        hashed_password="hash",
        role=UserRole.GUEST,
        cpf="66677788899",
    )
    session.add(resident)
    session.commit()

    # Resident attempts to update status without being admin or assigned
    occ_in = OccurrenceCreate(
        category=OccurrenceCategory.RULES_VIOLATION,
        title="Uso indevido da piscina",
        description="Garrafas de vidro na área molhada",
        is_public=True,
    )
    occ = OccurrenceService.create_occurrence(session, resident, occ_in)

    # Standard resident tries to change status -> forbidden
    update_in = OccurrenceStatusUpdate(status=OccurrenceStatus.RESOLVED)
    with pytest.raises(OccurrenceAccessForbiddenError):
        OccurrenceService.update_occurrence_status(session, resident, occ.id, update_in)
