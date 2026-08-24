"""Unit and integration tests for Lot management service and endpoints."""

import uuid
import pytest
from app.core.exceptions import (
    LotAlreadyExistsError,
    LotNotFoundError,
    UserLotLinkAlreadyExistsError,
    UserLotLinkNotFoundError,
)
from app.models.enums import LotAssociationType, LotStatus, UserRole
from app.models.lot import Lot, UserLotLink
from app.models.user import User
from app.schemas.lot import LotCreate, LotUpdate, UserLotLinkCreate
from app.services.lot_service import LotService
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_create_lot_success(session: Session):
    lot_in = LotCreate(
        block="A",
        lot_number="101",
        address="Rua A, 101",
        postal_code="12345-678",
        area_sqm=450.0,
        fraction_ideal=0.025,
        status=LotStatus.VACANT,
        notes="Corner lot",
    )
    lot = LotService.create_lot(session, lot_in)

    assert lot.id is not None
    assert lot.block == "A"
    assert lot.lot_number == "101"
    assert lot.status == LotStatus.VACANT
    assert lot.is_deleted is False


def test_create_lot_duplicate_raises_error(session: Session):
    lot_in = LotCreate(block="B", lot_number="202")
    LotService.create_lot(session, lot_in)

    with pytest.raises(LotAlreadyExistsError):
        LotService.create_lot(session, lot_in)


def test_get_lot_by_id_and_not_found(session: Session):
    lot = LotService.create_lot(session, LotCreate(block="C", lot_number="303"))
    found = LotService.get_lot_by_id(session, lot.id)
    assert found.id == lot.id

    with pytest.raises(LotNotFoundError):
        LotService.get_lot_by_id(session, uuid.uuid4())


def test_update_lot(session: Session):
    lot = LotService.create_lot(session, LotCreate(block="D", lot_number="404"))
    updated = LotService.update_lot(
        session, lot, LotUpdate(notes="Updated notes", area_sqm=500.0)
    )
    assert updated.notes == "Updated notes"
    assert updated.area_sqm == 500.0


def test_update_lot_duplicate_block_number_raises_error(session: Session):
    lot1 = LotService.create_lot(session, LotCreate(block="E", lot_number="1"))
    lot2 = LotService.create_lot(session, LotCreate(block="E", lot_number="2"))

    with pytest.raises(LotAlreadyExistsError):
        LotService.update_lot(session, lot2, LotUpdate(lot_number="1"))


def test_soft_delete_lot(session: Session):
    lot = LotService.create_lot(session, LotCreate(block="F", lot_number="505"))
    LotService.delete_lot(session, lot)

    with pytest.raises(LotNotFoundError):
        LotService.get_lot_by_id(session, lot.id)


def test_user_lot_linking_and_auto_status(session: Session, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="606", status=LotStatus.VACANT))
    assert lot.status == LotStatus.VACANT

    link_in = UserLotLinkCreate(
        user_id=normal_user.id,
        association_type=LotAssociationType.PROPRIETARIO,
        is_primary=True,
    )
    link = LotService.link_user(session, lot.id, link_in)

    assert link.user_id == normal_user.id
    assert link.lot_id == lot.id
    assert link.is_primary is True

    # Check status auto-updated to OCCUPIED
    updated_lot = LotService.get_lot_by_id(session, lot.id)
    assert updated_lot.status == LotStatus.OCCUPIED


def test_duplicate_user_lot_link_raises_error(session: Session, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="H", lot_number="707"))
    link_in = UserLotLinkCreate(user_id=normal_user.id)
    LotService.link_user(session, lot.id, link_in)

    with pytest.raises(UserLotLinkAlreadyExistsError):
        LotService.link_user(session, lot.id, link_in)


def test_unlink_user_auto_reverts_status_to_vacant(session: Session, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="I", lot_number="808"))
    link_in = UserLotLinkCreate(user_id=normal_user.id)
    LotService.link_user(session, lot.id, link_in)

    lot_detail = LotService.get_lot_detail(session, lot.id)
    assert len(lot_detail.users) == 1
    assert lot_detail.status == LotStatus.OCCUPIED

    LotService.unlink_user(session, lot.id, normal_user.id)

    updated_lot = LotService.get_lot_by_id(session, lot.id)
    assert updated_lot.status == LotStatus.VACANT

    with pytest.raises(UserLotLinkNotFoundError):
        LotService.unlink_user(session, lot.id, normal_user.id)


def test_single_user_linked_to_multiple_lots(session: Session, normal_user: User):
    lot1 = LotService.create_lot(session, LotCreate(block="J", lot_number="1"))
    lot2 = LotService.create_lot(session, LotCreate(block="J", lot_number="2"))

    link1 = LotService.link_user(session, lot1.id, UserLotLinkCreate(user_id=normal_user.id))
    link2 = LotService.link_user(session, lot2.id, UserLotLinkCreate(user_id=normal_user.id))

    assert link1.lot_id == lot1.id
    assert link2.lot_id == lot2.id


# API Endpoint Integration Tests
def test_api_list_lots(client: TestClient, admin_user: User, session: Session):
    LotService.create_lot(session, LotCreate(block="K", lot_number="1", status=LotStatus.VACANT))
    LotService.create_lot(session, LotCreate(block="K", lot_number="2", status=LotStatus.OCCUPIED))
    LotService.create_lot(session, LotCreate(block="L", lot_number="1", status=LotStatus.VACANT))

    from app.core.security import create_access_token
    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # All lots
    res = client.get("/api/v1/lots/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Filter by block K
    res_k = client.get("/api/v1/lots/?block=K", headers=headers)
    assert res_k.status_code == 200
    assert res_k.json()["total"] == 2

    # Filter by status VACANT
    res_vacant = client.get("/api/v1/lots/?status=VACANT", headers=headers)
    assert res_vacant.status_code == 200
    assert res_vacant.json()["total"] == 2


def test_api_create_get_update_delete_lot(client: TestClient, admin_user: User):
    from app.core.security import create_access_token
    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    create_payload = {
        "block": "M",
        "lot_number": "100",
        "address": "Alameda M",
        "postal_code": "99999-000",
        "area_sqm": 600.0,
        "fraction_ideal": 0.05,
        "status": "VACANT",
        "notes": "Test lot",
    }
    res_create = client.post("/api/v1/lots/", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    lot_data = res_create.json()
    lot_id = lot_data["id"]

    # Duplicate create attempt
    res_dup = client.post("/api/v1/lots/", json=create_payload, headers=headers)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]

    # Get Detail
    res_get = client.get(f"/api/v1/lots/{lot_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["block"] == "M"
    assert res_get.json()["users"] == []

    # Update
    res_put = client.put(f"/api/v1/lots/{lot_id}", json={"notes": "New notes"}, headers=headers)
    assert res_put.status_code == 200
    assert res_put.json()["notes"] == "New notes"

    # Delete
    res_del = client.delete(f"/api/v1/lots/{lot_id}", headers=headers)
    assert res_del.status_code == 204

    # Verify not found after delete
    res_get_after = client.get(f"/api/v1/lots/{lot_id}", headers=headers)
    assert res_get_after.status_code == 404


def test_api_link_and_unlink_user(client: TestClient, admin_user: User, normal_user: User, session: Session):
    lot = LotService.create_lot(session, LotCreate(block="N", lot_number="1"))

    from app.core.security import create_access_token
    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Link user
    link_payload = {
        "user_id": str(normal_user.id),
        "association_type": "PROPRIETARIO",
        "is_primary": True,
    }
    res_link = client.post(f"/api/v1/lots/{lot.id}/users", json=link_payload, headers=headers)
    assert res_link.status_code == 201
    link_data = res_link.json()
    assert link_data["user"]["id"] == str(normal_user.id)
    assert link_data["user"]["full_name"] == normal_user.full_name

    # Duplicate link
    res_link_dup = client.post(f"/api/v1/lots/{lot.id}/users", json=link_payload, headers=headers)
    assert res_link_dup.status_code == 400

    # Unlink user
    res_unlink = client.delete(f"/api/v1/lots/{lot.id}/users/{normal_user.id}", headers=headers)
    assert res_unlink.status_code == 204


def test_link_non_existent_user_raises_error(session: Session, client: TestClient, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="P", lot_number="1"))
    fake_user_id = uuid.uuid4()
    link_in = UserLotLinkCreate(user_id=fake_user_id)

    from app.core.exceptions import DomainError
    with pytest.raises(DomainError):
        LotService.link_user(session, lot.id, link_in)

    from app.core.security import create_access_token
    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post(
        f"/api/v1/lots/{lot.id}/users",
        json={"user_id": str(fake_user_id), "association_type": "PROPRIETARIO"},
        headers=headers,
    )
    assert res.status_code == 400

