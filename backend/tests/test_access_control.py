"""Tests for the Access Control & Facial Recognition Integration module (T005)."""

import io
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.enums import UserRole
from app.models.lot import Lot
from app.models.resident import Resident
from app.models.user import User


def create_test_image_bytes() -> bytes:
    img = Image.new("RGB", (200, 200), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def manager_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="manager@test.com",
        full_name="Manager User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
        cpf="11144477735",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_role_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="residentrole@test.com",
        full_name="Resident Role User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="52998224725",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def manager_token(manager_user: User) -> str:
    return create_access_token(subject=str(manager_user.id))


@pytest.fixture
def resident_role_token(resident_role_user: User) -> str:
    return create_access_token(subject=str(resident_role_user.id))


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(subject=str(admin_user.id))


@pytest.fixture
def test_lot(session: Session) -> Lot:
    lot = Lot(block="A", lot_number="01")
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


@pytest.fixture
def test_resident(session: Session, test_lot: Lot) -> Resident:
    resident = Resident(
        lot_id=test_lot.id,
        full_name="Jane Resident",
        cpf="93541134780",
    )
    session.add(resident)
    session.commit()
    session.refresh(resident)
    return resident


def _admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


# -----------------------------------------------------------------------------
# Device Management
# -----------------------------------------------------------------------------


def test_create_device_success(client: TestClient, admin_token: str):
    resp = client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": "Portaria Principal", "location": "Gate 1"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["name"] == "Portaria Principal"
    assert body["status"] == "OFFLINE"
    assert "device_key" in body
    assert len(body["device_key"]) > 10


def test_create_device_forbidden_for_manager(client: TestClient, manager_token: str):
    resp = client.post(
        "/api/v1/access-control/devices",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"name": "Gate X"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_create_device_duplicate_name(client: TestClient, admin_token: str):
    client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": "Gate Dup"},
    )
    resp = client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": "Gate Dup"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_list_devices_manager_allowed(client: TestClient, admin_token: str, manager_token: str):
    client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": "Gate List"},
    )
    resp = client.get(
        "/api/v1/access-control/devices",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["total"] >= 1


def test_list_devices_forbidden_for_resident(client: TestClient, resident_role_token: str):
    resp = client.get(
        "/api/v1/access-control/devices",
        headers={"Authorization": f"Bearer {resident_role_token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_device_status(client: TestClient, admin_token: str):
    create_resp = client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": "Gate Status"},
    )
    device_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/v1/access-control/devices/{device_id}/status",
        headers=_admin_headers(admin_token),
        json={"status": "MAINTENANCE"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "MAINTENANCE"


def test_update_device_status_not_found(client: TestClient, admin_token: str):
    resp = client.put(
        f"/api/v1/access-control/devices/{uuid.uuid4()}/status",
        headers=_admin_headers(admin_token),
        json={"status": "ONLINE"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_regenerate_device_key(client: TestClient, admin_token: str):
    create_resp = client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": "Gate Regen"},
    )
    device_id = create_resp.json()["id"]
    old_key = create_resp.json()["device_key"]

    resp = client.post(
        f"/api/v1/access-control/devices/{device_id}/regenerate-key",
        headers=_admin_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["device_key"] != old_key


def test_regenerate_device_key_forbidden_for_manager(client: TestClient, admin_token: str, manager_token: str):
    create_resp = client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": "Gate Regen Forbidden"},
    )
    device_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/v1/access-control/devices/{device_id}/regenerate-key",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


# -----------------------------------------------------------------------------
# Facial Template Sync
# -----------------------------------------------------------------------------


def test_sync_facial_template_no_approved_photo(client: TestClient, admin_token: str, test_resident: Resident):
    resp = client.post(
        f"/api/v1/access-control/residents/{test_resident.id}/facial-template/sync",
        headers=_admin_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_sync_facial_template_resident_not_found(client: TestClient, admin_token: str):
    resp = client.post(
        f"/api/v1/access-control/residents/{uuid.uuid4()}/facial-template/sync",
        headers=_admin_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_sync_facial_template_success(client: TestClient, admin_token: str, test_resident: Resident):
    # Admin-uploaded photo auto-approves.
    image_bytes = create_test_image_bytes()
    upload_resp = client.post(
        "/api/v1/uploads/photo",
        headers=_admin_headers(admin_token),
        files={"file": ("resident.jpg", image_bytes, "image/jpeg")},
        data={"entity_type": "RESIDENT", "entity_id": str(test_resident.id)},
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    assert upload_resp.json()["status"] == "APPROVED"

    sync_resp = client.post(
        f"/api/v1/access-control/residents/{test_resident.id}/facial-template/sync",
        headers=_admin_headers(admin_token),
    )
    assert sync_resp.status_code == status.HTTP_200_OK
    body = sync_resp.json()
    assert body["sync_status"] == "SYNCED"
    assert body["resident_id"] == str(test_resident.id)
    assert body["synced_at"] is not None

    # Re-syncing (upsert) should keep a single template row.
    sync_resp_2 = client.post(
        f"/api/v1/access-control/residents/{test_resident.id}/facial-template/sync",
        headers=_admin_headers(admin_token),
    )
    assert sync_resp_2.status_code == status.HTTP_200_OK
    assert sync_resp_2.json()["id"] == body["id"]


def test_get_facial_template_status(client: TestClient, admin_token: str, test_resident: Resident):
    resp = client.get(
        f"/api/v1/access-control/residents/{test_resident.id}/facial-template",
        headers=_admin_headers(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() is None

    image_bytes = create_test_image_bytes()
    client.post(
        "/api/v1/uploads/photo",
        headers=_admin_headers(admin_token),
        files={"file": ("resident2.jpg", image_bytes, "image/jpeg")},
        data={"entity_type": "RESIDENT", "entity_id": str(test_resident.id)},
    )
    client.post(
        f"/api/v1/access-control/residents/{test_resident.id}/facial-template/sync",
        headers=_admin_headers(admin_token),
    )

    resp2 = client.get(
        f"/api/v1/access-control/residents/{test_resident.id}/facial-template",
        headers=_admin_headers(admin_token),
    )
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["sync_status"] == "SYNCED"


# -----------------------------------------------------------------------------
# Verification Webhook
# -----------------------------------------------------------------------------


def _register_device(client: TestClient, admin_token: str, name: str) -> tuple[str, str]:
    resp = client.post(
        "/api/v1/access-control/devices",
        headers=_admin_headers(admin_token),
        json={"name": name},
    )
    body = resp.json()
    return body["id"], body["device_key"]


def _sync_template_for_resident(client: TestClient, admin_token: str, resident_id: str) -> None:
    image_bytes = create_test_image_bytes()
    client.post(
        "/api/v1/uploads/photo",
        headers=_admin_headers(admin_token),
        files={"file": ("webhook_resident.jpg", image_bytes, "image/jpeg")},
        data={"entity_type": "RESIDENT", "entity_id": resident_id},
    )
    client.post(
        f"/api/v1/access-control/residents/{resident_id}/facial-template/sync",
        headers=_admin_headers(admin_token),
    )


def test_webhook_missing_device_key(client: TestClient):
    resp = client.post(
        "/api/v1/access-control/webhook/verification",
        json={"resident_id": None, "confidence_score": 0.9},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_webhook_invalid_device_key(client: TestClient):
    resp = client.post(
        "/api/v1/access-control/webhook/verification",
        headers={"X-Device-Key": "not-a-real-key"},
        json={"resident_id": None, "confidence_score": 0.9},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_webhook_unmatched_face(client: TestClient, admin_token: str):
    _, device_key = _register_device(client, admin_token, "Webhook Gate Unmatched")
    resp = client.post(
        "/api/v1/access-control/webhook/verification",
        headers={"X-Device-Key": device_key},
        json={"resident_id": None, "confidence_score": 0.2},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["matched"] is False
    assert body["access_granted"] is False


def test_webhook_matched_and_granted(client: TestClient, admin_token: str, test_resident: Resident):
    _, device_key = _register_device(client, admin_token, "Webhook Gate Matched")
    _sync_template_for_resident(client, admin_token, str(test_resident.id))

    resp = client.post(
        "/api/v1/access-control/webhook/verification",
        headers={"X-Device-Key": device_key},
        json={"resident_id": str(test_resident.id), "confidence_score": 0.98},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["matched"] is True
    assert body["access_granted"] is True
    assert body["confidence_score"] == 0.98


def test_webhook_matched_but_resident_inactive(
    client: TestClient, admin_token: str, test_resident: Resident, session: Session
):
    _, device_key = _register_device(client, admin_token, "Webhook Gate Inactive")
    _sync_template_for_resident(client, admin_token, str(test_resident.id))

    test_resident.is_active = False
    session.add(test_resident)
    session.commit()

    resp = client.post(
        "/api/v1/access-control/webhook/verification",
        headers={"X-Device-Key": device_key},
        json={"resident_id": str(test_resident.id), "confidence_score": 0.95},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["matched"] is True
    assert body["access_granted"] is False


def test_webhook_updates_device_status_and_last_seen(client: TestClient, admin_token: str):
    device_id, device_key = _register_device(client, admin_token, "Webhook Gate Heartbeat")

    client.post(
        "/api/v1/access-control/webhook/verification",
        headers={"X-Device-Key": device_key},
        json={"resident_id": None, "confidence_score": None},
    )

    devices_resp = client.get("/api/v1/access-control/devices", headers=_admin_headers(admin_token))
    device = next(d for d in devices_resp.json()["items"] if d["id"] == device_id)
    assert device["status"] == "ONLINE"
    assert device["last_seen_at"] is not None


# -----------------------------------------------------------------------------
# Event Feed
# -----------------------------------------------------------------------------


def test_list_events_pagination_and_filters(client: TestClient, admin_token: str, test_resident: Resident):
    device_id, device_key = _register_device(client, admin_token, "Webhook Gate Events")
    _sync_template_for_resident(client, admin_token, str(test_resident.id))

    for _ in range(3):
        client.post(
            "/api/v1/access-control/webhook/verification",
            headers={"X-Device-Key": device_key},
            json={"resident_id": str(test_resident.id), "confidence_score": 0.9},
        )

    resp = client.get(
        "/api/v1/access-control/events",
        headers=_admin_headers(admin_token),
        params={"device_id": device_id},
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["total"] >= 3
    assert all(item["device_id"] == device_id for item in body["items"])

    resp_by_resident = client.get(
        "/api/v1/access-control/events",
        headers=_admin_headers(admin_token),
        params={"resident_id": str(test_resident.id)},
    )
    assert resp_by_resident.status_code == status.HTTP_200_OK
    assert resp_by_resident.json()["total"] >= 3


def test_list_events_forbidden_for_resident_role(client: TestClient, resident_role_token: str):
    resp = client.get(
        "/api/v1/access-control/events",
        headers={"Authorization": f"Bearer {resident_role_token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
