"""Unit and integration tests for Visitor Management RBAC security policies."""

import uuid
import pytest
from app.core.exceptions import ForbiddenError
from app.models.enums import LotAssociationType, UserRole
from app.models.user import User
from app.schemas.lot import LotCreate, UserLotLinkCreate
from app.schemas.visitor import (
    AccessLogCheckIn,
    AccessLogCheckOut,
    VisitorAuthorizationCreate,
    VisitorCreate,
)
from app.services.lot_service import LotService
from app.services.visitor_service import VisitorService
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.fixture
def resident_user(session: Session) -> User:
    """Create a resident (GUEST role) user."""
    user = User(
        id=uuid.uuid4(),
        email="resident_rbac@test.com",
        full_name="Resident User",
        hashed_password="hashed_test_pass",
        role=UserRole.GUEST,
        cpf="11144477735",
    )
    session.add(user)
    session.commit()
    return user




def test_resident_cannot_access_unlinked_lot_authorizations(
    session: Session, client: TestClient, resident_user: User, admin_user: User
):
    lot_own = LotService.create_lot(session, LotCreate(block="R1", lot_number="101"))
    lot_other = LotService.create_lot(session, LotCreate(block="R1", lot_number="102"))

    # Link resident to lot_own
    LotService.link_user(
        session,
        lot_own.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Visitor RBAC"))

    from app.core.security import create_access_token
    token = create_access_token(resident_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Allowed for linked lot_own
    res_own = client.get(f"/api/v1/lots/{lot_own.id}/authorizations", headers=headers)
    assert res_own.status_code == 200

    # Create authorization allowed for lot_own
    res_create_own = client.post(
        f"/api/v1/lots/{lot_own.id}/authorizations",
        json={"visitor_id": str(visitor.id), "auth_type": "SINGLE"},
        headers=headers,
    )
    assert res_create_own.status_code == 201

    # Forbidden for unlinked lot_other
    res_other = client.get(f"/api/v1/lots/{lot_other.id}/authorizations", headers=headers)
    assert res_other.status_code == 403

    res_create_other = client.post(
        f"/api/v1/lots/{lot_other.id}/authorizations",
        json={"visitor_id": str(visitor.id), "auth_type": "SINGLE"},
        headers=headers,
    )
    assert res_create_other.status_code == 403


def test_resident_cannot_execute_check_in_or_check_out(
    session: Session, client: TestClient, resident_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="R2", lot_number="201"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="CheckIn Tester"))

    from app.core.security import create_access_token
    token = create_access_token(resident_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res_in = client.post(
        "/api/v1/access-logs/check-in",
        json={"visitor_id": str(visitor.id), "lot_id": str(lot.id)},
        headers=headers,
    )
    assert res_in.status_code == 403

    res_out = client.post(
        "/api/v1/access-logs/check-out",
        json={"visitor_id": str(visitor.id)},
        headers=headers,
    )
    assert res_out.status_code == 403


def test_resident_access_logs_restricted_to_linked_lot(
    session: Session, client: TestClient, resident_user: User, admin_user: User
):
    lot_own = LotService.create_lot(session, LotCreate(block="R3", lot_number="301"))
    lot_other = LotService.create_lot(session, LotCreate(block="R3", lot_number="302"))

    LotService.link_user(
        session,
        lot_own.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    from app.core.security import create_access_token
    token = create_access_token(resident_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Querying own lot logs -> 200
    res_own = client.get(f"/api/v1/access-logs?lot_id={lot_own.id}", headers=headers)
    assert res_own.status_code == 200

    # Querying other lot logs -> 403
    res_other = client.get(f"/api/v1/access-logs?lot_id={lot_other.id}", headers=headers)
    assert res_other.status_code == 403
