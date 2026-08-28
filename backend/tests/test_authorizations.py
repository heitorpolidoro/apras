"""Unit and integration tests for Visitor pre-authorization management."""

import io
import uuid
from datetime import datetime, timedelta

import pytest
import zxingcpp
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app.core.exceptions import (
    AuthorizationNotFoundError,
    DomainError,
    LotNotFoundError,
)
from app.models.enums import (
    AuthorizationStatus,
    AuthorizationType,
    DayOfWeek,
    LotStatus,
    ShiftType,
)
from app.models.lot import Lot
from app.models.user import User
from app.schemas.lot import LotCreate
from app.schemas.visitor import VisitorAuthorizationCreate, VisitorCreate
from app.services.lot_service import LotService
from app.services.visitor_service import VisitorService


def test_create_single_authorization_success(session: Session, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="A", lot_number="10"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Lucas Moura"))

    auth_in = VisitorAuthorizationCreate(
        visitor_id=visitor.id,
        auth_type=AuthorizationType.SINGLE,
        allowed_days=[DayOfWeek.MON, DayOfWeek.WED, DayOfWeek.FRI],
        allowed_shifts=[ShiftType.MORNING, ShiftType.AFTERNOON],
        notes="One-time repair",
    )
    auth = VisitorService.create_authorization(session, lot.id, auth_in, admin_user)

    assert auth.id is not None
    assert auth.lot_id == lot.id
    assert auth.visitor_id == visitor.id
    assert auth.auth_type == AuthorizationType.SINGLE
    assert auth.status == AuthorizationStatus.ACTIVE
    assert "MON" in auth.allowed_days_json
    assert "WED" in auth.allowed_days_json
    assert "MORNING" in auth.allowed_shifts_json


def test_permanent_authorization_exceeding_1_year_raises_error(session: Session, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="B", lot_number="20"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Fernanda Lima"))

    now = datetime.utcnow()
    too_far = now + timedelta(days=400)

    auth_in = VisitorAuthorizationCreate(
        visitor_id=visitor.id,
        auth_type=AuthorizationType.PERMANENT,
        valid_from=now,
        valid_until=too_far,
    )

    with pytest.raises(DomainError, match="cannot exceed 1 year validity"):
        VisitorService.create_authorization(session, lot.id, auth_in, admin_user)


def test_permanent_authorization_within_1_year_succeeds(session: Session, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="B", lot_number="21"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Juliana Paes"))

    now = datetime.utcnow()
    valid_until = now + timedelta(days=360)

    auth_in = VisitorAuthorizationCreate(
        visitor_id=visitor.id,
        auth_type=AuthorizationType.PERMANENT,
        valid_from=now,
        valid_until=valid_until,
    )

    auth = VisitorService.create_authorization(session, lot.id, auth_in, admin_user)
    assert auth.status == AuthorizationStatus.ACTIVE


def test_revoke_authorization(session: Session, admin_user: User):
    lot = LotService.create_lot(session, LotCreate(block="C", lot_number="30"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Marcos Vinicius"))

    auth_in = VisitorAuthorizationCreate(visitor_id=visitor.id)
    auth = VisitorService.create_authorization(session, lot.id, auth_in, admin_user)
    assert auth.status == AuthorizationStatus.ACTIVE

    revoked = VisitorService.revoke_authorization(session, auth.id, admin_user)
    assert revoked.status == AuthorizationStatus.REVOKED


def test_get_authorization_not_found(session: Session):
    with pytest.raises(AuthorizationNotFoundError):
        VisitorService.get_authorization_by_id(session, uuid.uuid4())


def test_api_lot_authorizations_flow(client: TestClient, admin_user: User, session: Session):
    lot = LotService.create_lot(session, LotCreate(block="D", lot_number="40"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Camila Pitanga"))

    from app.core.security import create_access_token
    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Create Authorization
    create_payload = {
        "visitor_id": str(visitor.id),
        "auth_type": "PERMANENT",
        "allowed_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "allowed_shifts": ["MORNING", "AFTERNOON"],
        "notes": "Pool cleaning staff",
    }
    res_create = client.post(f"/api/v1/lots/{lot.id}/authorizations", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    auth_data = res_create.json()
    auth_id = auth_data["id"]
    assert auth_data["auth_type"] == "PERMANENT"
    assert auth_data["status"] == "ACTIVE"

    # List Authorizations
    res_list = client.get(f"/api/v1/lots/{lot.id}/authorizations", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1

    # Revoke Authorization
    res_revoke = client.put(f"/api/v1/authorizations/{auth_id}/revoke", json={}, headers=headers)
    assert res_revoke.status_code == 200
    assert res_revoke.json()["status"] == "REVOKED"


def test_get_authorization_by_id_success(client: TestClient, admin_user: User, session: Session):
    lot = LotService.create_lot(session, LotCreate(block="E", lot_number="50"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Rafael Souza"))
    auth_in = VisitorAuthorizationCreate(visitor_id=visitor.id)
    auth = VisitorService.create_authorization(session, lot.id, auth_in, admin_user)

    from app.core.security import create_access_token

    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/authorizations/{auth.id}", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(auth.id)
    assert body["visitor_id"] == str(visitor.id)
    assert body["lot_id"] == str(lot.id)


def test_get_authorization_by_id_not_found(client: TestClient, admin_user: User):
    from app.core.security import create_access_token

    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/authorizations/{uuid.uuid4()}", headers=headers)
    assert res.status_code == 404


def test_get_authorization_qr_code_success(client: TestClient, admin_user: User, session: Session):
    lot = LotService.create_lot(session, LotCreate(block="F", lot_number="60"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Bianca Torres"))
    auth_in = VisitorAuthorizationCreate(visitor_id=visitor.id)
    auth = VisitorService.create_authorization(session, lot.id, auth_in, admin_user)

    from app.core.security import create_access_token

    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/authorizations/{auth.id}/qr-code", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"

    image = Image.open(io.BytesIO(res.content))
    decoded = zxingcpp.read_barcodes(image)
    assert len(decoded) == 1
    assert decoded[0].text == str(auth.id)


def test_get_authorization_qr_code_not_found(client: TestClient, admin_user: User):
    from app.core.security import create_access_token

    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/authorizations/{uuid.uuid4()}/qr-code", headers=headers)
    assert res.status_code == 404
