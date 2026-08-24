"""RBAC security unit and integration tests for Lot management endpoints."""

import uuid
import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.lot import LotCreate
from app.services.lot_service import LotService
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.fixture
def director_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="director@test.com",
        full_name="Director User",
        hashed_password=get_password_hash("password"),
        role=UserRole.DIRECTOR,
        cpf="68093836069",
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
        hashed_password=get_password_hash("password"),
        role=UserRole.MANAGER,
        cpf="85638204090",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def guest_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="guest@test.com",
        full_name="Guest User",
        hashed_password=get_password_hash("password"),
        role=UserRole.GUEST,
        cpf="48574698083",
    )
    session.add(user)
    session.commit()
    return user


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_list_lots_rbac(
    client: TestClient,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    # Admin
    assert client.get("/api/v1/lots/", headers=_auth_header(admin_user)).status_code == 200
    # Director
    assert client.get("/api/v1/lots/", headers=_auth_header(director_user)).status_code == 200
    # Manager
    assert client.get("/api/v1/lots/", headers=_auth_header(manager_user)).status_code == 200
    # Guest -> Forbidden
    assert client.get("/api/v1/lots/", headers=_auth_header(guest_user)).status_code == 403


def test_create_lot_rbac(
    client: TestClient,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    payload = {"block": "R1", "lot_number": "1"}

    # Admin -> Allowed (201)
    res_admin = client.post("/api/v1/lots/", json=payload, headers=_auth_header(admin_user))
    assert res_admin.status_code == 201

    # Director -> Allowed (201)
    payload_dir = {"block": "R1", "lot_number": "2"}
    res_dir = client.post("/api/v1/lots/", json=payload_dir, headers=_auth_header(director_user))
    assert res_dir.status_code == 201

    # Manager -> Forbidden (403)
    payload_mgr = {"block": "R1", "lot_number": "3"}
    res_mgr = client.post("/api/v1/lots/", json=payload_mgr, headers=_auth_header(manager_user))
    assert res_mgr.status_code == 403

    # Guest -> Forbidden (403)
    res_gst = client.post("/api/v1/lots/", json=payload_mgr, headers=_auth_header(guest_user))
    assert res_gst.status_code == 403


def test_get_lot_detail_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot = LotService.create_lot(session, LotCreate(block="R2", lot_number="1"))

    # Admin, Director, Manager -> 200
    assert client.get(f"/api/v1/lots/{lot.id}", headers=_auth_header(admin_user)).status_code == 200
    assert client.get(f"/api/v1/lots/{lot.id}", headers=_auth_header(director_user)).status_code == 200
    assert client.get(f"/api/v1/lots/{lot.id}", headers=_auth_header(manager_user)).status_code == 200

    # Guest -> 403
    assert client.get(f"/api/v1/lots/{lot.id}", headers=_auth_header(guest_user)).status_code == 403


def test_update_lot_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot = LotService.create_lot(session, LotCreate(block="R3", lot_number="1"))

    payload = {"notes": "Updated"}
    # Admin -> 200
    assert client.put(f"/api/v1/lots/{lot.id}", json=payload, headers=_auth_header(admin_user)).status_code == 200
    # Director -> 200
    assert client.put(f"/api/v1/lots/{lot.id}", json=payload, headers=_auth_header(director_user)).status_code == 200
    # Manager -> 403
    assert client.put(f"/api/v1/lots/{lot.id}", json=payload, headers=_auth_header(manager_user)).status_code == 403
    # Guest -> 403
    assert client.put(f"/api/v1/lots/{lot.id}", json=payload, headers=_auth_header(guest_user)).status_code == 403


def test_delete_lot_rbac_strictly_administrator_only(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot = LotService.create_lot(session, LotCreate(block="R4", lot_number="1"))

    # Director -> Forbidden (403)
    res_dir = client.delete(f"/api/v1/lots/{lot.id}", headers=_auth_header(director_user))
    assert res_dir.status_code == 403

    # Manager -> Forbidden (403)
    res_mgr = client.delete(f"/api/v1/lots/{lot.id}", headers=_auth_header(manager_user))
    assert res_mgr.status_code == 403

    # Guest -> Forbidden (403)
    res_gst = client.delete(f"/api/v1/lots/{lot.id}", headers=_auth_header(guest_user))
    assert res_gst.status_code == 403

    # Admin -> Allowed (204)
    res_adm = client.delete(f"/api/v1/lots/{lot.id}", headers=_auth_header(admin_user))
    assert res_adm.status_code == 204


def test_user_lot_linking_rbac(
    client: TestClient,
    session: Session,
    admin_user: User,
    director_user: User,
    manager_user: User,
    guest_user: User,
):
    lot1 = LotService.create_lot(session, LotCreate(block="R5", lot_number="1"))
    lot2 = LotService.create_lot(session, LotCreate(block="R5", lot_number="2"))

    link_payload = {"user_id": str(manager_user.id), "association_type": "PROPRIETARIO"}

    # Manager -> 403
    assert client.post(f"/api/v1/lots/{lot1.id}/users", json=link_payload, headers=_auth_header(manager_user)).status_code == 403
    # Guest -> 403
    assert client.post(f"/api/v1/lots/{lot1.id}/users", json=link_payload, headers=_auth_header(guest_user)).status_code == 403

    # Director -> 201
    assert client.post(f"/api/v1/lots/{lot1.id}/users", json=link_payload, headers=_auth_header(director_user)).status_code == 201

    # Admin -> 201
    assert client.post(f"/api/v1/lots/{lot2.id}/users", json=link_payload, headers=_auth_header(admin_user)).status_code == 201

    # Unlink: Manager/Guest -> 403
    assert client.delete(f"/api/v1/lots/{lot1.id}/users/{manager_user.id}", headers=_auth_header(manager_user)).status_code == 403
    assert client.delete(f"/api/v1/lots/{lot1.id}/users/{manager_user.id}", headers=_auth_header(guest_user)).status_code == 403

    # Unlink: Director -> 204
    assert client.delete(f"/api/v1/lots/{lot1.id}/users/{manager_user.id}", headers=_auth_header(director_user)).status_code == 204
    # Unlink: Admin -> 204
    assert client.delete(f"/api/v1/lots/{lot2.id}/users/{manager_user.id}", headers=_auth_header(admin_user)).status_code == 204
