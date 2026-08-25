"""Unit and integration tests for Resident management service and endpoints."""

import uuid
from datetime import date
import pytest
from app.core.exceptions import (
    ForbiddenError,
    ResidentAlreadyLinkedError,
    ResidentNotFoundError,
    ResidentCPFConflictError,
)
from app.models.enums import LotAssociationType, LotStatus, ResidentRelationship, UserRole
from app.models.lot import Lot, UserLotLink
from app.models.user import User
from app.models.resident import Resident
from app.schemas.lot import LotCreate
from app.schemas.resident import ResidentCreate, ResidentUpdate, LinkUserPayload

from app.services.lot_service import LotService
from app.services.resident_service import ResidentService
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_cpf_validation_in_resident_schema():
    # Valid CPF
    res_in = ResidentCreate(
        full_name="João Silva",
        cpf="111.444.777-35",
        relationship_type=ResidentRelationship.TITULAR,
    )
    assert res_in.cpf == "11144477735"

    # Invalid CPF digits
    with pytest.raises(ValueError, match="Invalid CPF"):
        ResidentCreate(
            full_name="João Silva",
            cpf="111.444.777-00",
            relationship_type=ResidentRelationship.TITULAR,
        )

    # Invalid CPF length
    with pytest.raises(ValueError, match="CPF must have exactly 11 digits"):
        ResidentCreate(
            full_name="João Silva",
            cpf="12345",
            relationship_type=ResidentRelationship.TITULAR,
        )


def test_create_resident_and_auto_match_existing_user(session: Session, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="A", lot_number="101"))

    # Resident created with same CPF as normal_user -> user_id should be auto-linked
    res_in = ResidentCreate(
        full_name="Normal User Resident",
        cpf=normal_user.cpf,
        relationship_type=ResidentRelationship.TITULAR,
    )
    resident = ResidentService.create_resident(session, lot.id, res_in)

    assert resident.id is not None
    assert resident.lot_id == lot.id
    assert resident.user_id == normal_user.id
    assert resident.full_name == "Normal User Resident"
    assert resident.cpf == normal_user.cpf
    assert resident.is_active is True


def test_create_resident_duplicate_cpf_in_same_lot_raises_error(session: Session):
    lot = LotService.create_lot(session, LotCreate(block="A", lot_number="102"))
    res_in = ResidentCreate(
        full_name="Resident 1",
        cpf="52998224725",
        relationship_type=ResidentRelationship.TITULAR,
    )
    ResidentService.create_resident(session, lot.id, res_in)

    with pytest.raises(ResidentCPFConflictError):
        ResidentService.create_resident(session, lot.id, res_in)


def test_get_resident_by_id_and_not_found(session: Session, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="B", lot_number="201"))
    res_in = ResidentCreate(
        full_name="Resident B",
        cpf="52998224725",
        relationship_type=ResidentRelationship.CONJUGE,
    )
    resident = ResidentService.create_resident(session, lot.id, res_in)

    found = ResidentService.get_resident_by_id(session, resident.id, current_user=admin_user)
    assert found.id == resident.id

    with pytest.raises(ResidentNotFoundError):
        ResidentService.get_resident_by_id(session, uuid.uuid4(), current_user=admin_user)


def test_update_and_deactivate_resident(session: Session, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="C", lot_number="301"))
    res_in = ResidentCreate(
        full_name="Resident C",
        cpf="52998224725",
        relationship_type=ResidentRelationship.FILHO_DEPENDENTE,
    )
    resident = ResidentService.create_resident(session, lot.id, res_in)

    updated = ResidentService.update_resident(
        session, resident, ResidentUpdate(full_name="Resident C Updated", phone="11999999999"), current_user=admin_user
    )
    assert updated.full_name == "Resident C Updated"
    assert updated.phone == "11999999999"

    deactivated = ResidentService.deactivate_resident(session, resident)
    assert deactivated.is_active is False


def test_link_and_unlink_user(session: Session, normal_user: User, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="D", lot_number="401"))
    res_in = ResidentCreate(
        full_name="Resident D",
        cpf="22233344405",
        relationship_type=ResidentRelationship.INQUILINO,
    )
    resident = ResidentService.create_resident(session, lot.id, res_in)
    assert resident.user_id is None

    linked = ResidentService.link_user(session, resident.id, normal_user.id)
    assert linked.user_id == normal_user.id

    # Duplicate link attempt
    with pytest.raises(ResidentAlreadyLinkedError):
        ResidentService.link_user(session, resident.id, normal_user.id)

    unlinked = ResidentService.unlink_user(session, resident.id)
    assert unlinked.user_id is None


def test_auto_link_user_on_signup(session: Session):
    lot = LotService.create_lot(session, LotCreate(block="E", lot_number="501"))
    res_in = ResidentCreate(
        full_name="Future User Resident",
        cpf="99988877714",
        email="future@example.com",
        relationship_type=ResidentRelationship.TITULAR,
    )
    resident = ResidentService.create_resident(session, lot.id, res_in)
    assert resident.user_id is None

    # Now create user with matching CPF or email
    from app.core.security import get_password_hash
    new_user = User(
        id=uuid.uuid4(),
        email="future@example.com",
        full_name="Future User",
        hashed_password=get_password_hash("pass"),
        role=UserRole.GUEST,
        cpf="99988877714",
    )
    session.add(new_user)
    session.commit()

    linked_count = ResidentService.auto_link_user(session, new_user)
    assert linked_count == 1

    session.refresh(resident)
    assert resident.user_id == new_user.id

