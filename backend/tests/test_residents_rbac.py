"""RBAC security unit and integration tests for Resident management endpoints."""

import uuid
import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.enums import LotAssociationType, LotStatus, ResidentRelationship, UserRole
from app.models.lot import Lot, UserLotLink
from app.models.user import User
from app.schemas.lot import LotCreate
from app.schemas.resident import ResidentCreate
from app.services.lot_service import LotService
from app.services.resident_service import ResidentService
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.fixture
def director_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="director_res@test.com",
        full_name="Director User",
        hashed_password=get_password_hash("password"),
        role=UserRole.DIRECTOR,
        cpf="22233344405",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def manager_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="manager_res@test.com",
        full_name="Manager User",
        hashed_password=get_password_hash("password"),
        role=UserRole.MANAGER,
        cpf="99988877714",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def guest_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="guest_res@test.com",
        full_name="Guest User",
        hashed_password=get_password_hash("password"),
        role=UserRole.GUEST,
        cpf="33344455540",
    )
    session.add(user)
    session.commit()
    return user


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_list_residents_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot1 = LotService.create_lot(session, LotCreate(block="RBAC1", lot_number="1"))
    lot2 = LotService.create_lot(session, LotCreate(block="RBAC1", lot_number="2"))

    # Link guest_user to lot1 via UserLotLink
    LotService.link_user(session, lot1.id, UserLotLink(user_id=guest_user.id, lot_id=lot1.id))

    # Admin, Director, Manager -> 200 for any lot
    assert client.get(f"/api/v1/lots/{lot1.id}/residents", headers=_auth_header(admin_user)).status_code == 200
    assert client.get(f"/api/v1/lots/{lot1.id}/residents", headers=_auth_header(director_user)).status_code == 200
    assert client.get(f"/api/v1/lots/{lot1.id}/residents", headers=_auth_header(manager_user)).status_code == 200

    # User linked to lot1 can view lot1 residents
    assert client.get(f"/api/v1/lots/{lot1.id}/residents", headers=_auth_header(guest_user)).status_code == 200

    # User linked to lot1 CANNOT view lot2 residents (403)
    assert client.get(f"/api/v1/lots/{lot2.id}/residents", headers=_auth_header(guest_user)).status_code == 403


def test_create_resident_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot = LotService.create_lot(session, LotCreate(block="RBAC2", lot_number="1"))

    payload = {
        "full_name": "Resident New",
        "cpf": "52998224725",
        "relationship_type": "TITULAR",
    }

    # Manager -> Forbidden (403)
    assert client.post(f"/api/v1/lots/{lot.id}/residents", json=payload, headers=_auth_header(manager_user)).status_code == 403

    # Guest -> Forbidden (403)
    assert client.post(f"/api/v1/lots/{lot.id}/residents", json=payload, headers=_auth_header(guest_user)).status_code == 403

    # Director -> Allowed (201)
    res_dir = client.post(f"/api/v1/lots/{lot.id}/residents", json=payload, headers=_auth_header(director_user))
    assert res_dir.status_code == 201

    # Admin -> Allowed (201)
    payload_adm = {
        "full_name": "Resident Adm",
        "cpf": "11144477735",
        "relationship_type": "CONJUGE",
    }
    res_adm = client.post(f"/api/v1/lots/{lot.id}/residents", json=payload_adm, headers=_auth_header(admin_user))
    assert res_adm.status_code == 201


def test_get_resident_detail_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot = LotService.create_lot(session, LotCreate(block="RBAC3", lot_number="1"))
    resident = ResidentService.create_resident(
        session,
        lot.id,
        ResidentCreate(full_name="Resident Detail", cpf="52998224725", relationship_type=ResidentRelationship.TITULAR),
    )

    # Admin, Director, Manager -> 200
    assert client.get(f"/api/v1/residents/{resident.id}", headers=_auth_header(admin_user)).status_code == 200
    assert client.get(f"/api/v1/residents/{resident.id}", headers=_auth_header(director_user)).status_code == 200
    assert client.get(f"/api/v1/residents/{resident.id}", headers=_auth_header(manager_user)).status_code == 200

    # Unlinked guest -> 403
    assert client.get(f"/api/v1/residents/{resident.id}", headers=_auth_header(guest_user)).status_code == 403


def test_update_and_delete_resident_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot = LotService.create_lot(session, LotCreate(block="RBAC4", lot_number="1"))
    resident = ResidentService.create_resident(
        session,
        lot.id,
        ResidentCreate(full_name="Resident Update", cpf="52998224725", relationship_type=ResidentRelationship.TITULAR),
    )

    update_payload = {"full_name": "Resident Updated Name"}

    # Manager -> 403
    assert client.put(f"/api/v1/residents/{resident.id}", json=update_payload, headers=_auth_header(manager_user)).status_code == 403
    assert client.delete(f"/api/v1/residents/{resident.id}", headers=_auth_header(manager_user)).status_code == 403

    # Guest -> 403
    assert client.put(f"/api/v1/residents/{resident.id}", json=update_payload, headers=_auth_header(guest_user)).status_code == 403
    assert client.delete(f"/api/v1/residents/{resident.id}", headers=_auth_header(guest_user)).status_code == 403

    # Director -> 200 (update)
    assert client.put(f"/api/v1/residents/{resident.id}", json=update_payload, headers=_auth_header(director_user)).status_code == 200

    # Admin -> 204 (delete)
    assert client.delete(f"/api/v1/residents/{resident.id}", headers=_auth_header(admin_user)).status_code == 204


def test_link_and_unlink_user_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot = LotService.create_lot(session, LotCreate(block="RBAC5", lot_number="1"))
    resident = ResidentService.create_resident(
        session,
        lot.id,
        ResidentCreate(full_name="Resident Link", cpf="52998224725", relationship_type=ResidentRelationship.TITULAR),
    )

    link_payload = {"user_id": str(guest_user.id)}

    # Manager -> 403
    assert client.post(f"/api/v1/residents/{resident.id}/link-user", json=link_payload, headers=_auth_header(manager_user)).status_code == 403
    assert client.post(f"/api/v1/residents/{resident.id}/unlink-user", headers=_auth_header(manager_user)).status_code == 403

    # Director -> 200 (link)
    assert client.post(f"/api/v1/residents/{resident.id}/link-user", json=link_payload, headers=_auth_header(director_user)).status_code == 200

    # Admin -> 200 (unlink)
    assert client.post(f"/api/v1/residents/{resident.id}/unlink-user", headers=_auth_header(admin_user)).status_code == 200
