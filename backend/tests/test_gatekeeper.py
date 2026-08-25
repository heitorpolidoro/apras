"""Unit and integration tests for Gatekeeper check-in/check-out and Access Logs."""

from datetime import datetime, timedelta
import logging
import uuid
import pytest
from app.core.exceptions import (
    AccessLogNotFoundError,
    AuthorizationExpiredError,
    AuthorizationInvalidDayError,
    AuthorizationInvalidShiftError,
    AuthorizationRevokedError,
    OpenEntryExistsError,
)
from app.models.enums import AuthorizationStatus, AuthorizationType, DayOfWeek, ShiftType, UserRole
from app.models.user import User
from app.schemas.lot import LotCreate
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
def gatekeeper_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="gatekeeper@test.com",
        full_name="Gatekeeper John",
        hashed_password="hashed_test_pass",
        role=UserRole.MANAGER,
        cpf="52998224725",
    )
    session.add(user)
    session.commit()
    return user



def test_check_in_and_check_out_successful_flow(session: Session, gatekeeper_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G1", lot_number="01"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Bruno Gomes"))

    # Create authorization active for all days and full day shift
    auth = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            auth_type=AuthorizationType.PERMANENT,
            allowed_days=[DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN],
            allowed_shifts=[ShiftType.FULL_DAY],
        ),
        gatekeeper_user,
    )

    # Check In
    check_in_in = AccessLogCheckIn(
        visitor_id=visitor.id,
        lot_id=lot.id,
        authorization_id=auth.id,
        entry_notes="Carried ladder",
    )
    log = VisitorService.check_in(session, check_in_in, gatekeeper_user)

    assert log.id is not None
    assert log.visitor_id == visitor.id
    assert log.lot_id == lot.id
    assert log.entry_time is not None
    assert log.exit_time is None
    assert log.gatekeeper_user_id == gatekeeper_user.id
    assert log.entry_notes == "Carried ladder"

    # Check Out
    check_out_in = AccessLogCheckOut(
        access_log_id=log.id,
        exit_notes="Work completed",
    )
    out_log = VisitorService.check_out(session, check_out_in, gatekeeper_user)

    assert out_log.exit_time is not None
    assert out_log.exit_notes == "Work completed"


def test_check_in_rejects_duplicate_open_entry(session: Session, gatekeeper_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G2", lot_number="02"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Renata Sorrah"))

    auth = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            auth_type=AuthorizationType.PERMANENT,
            allowed_days=[DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN],
            allowed_shifts=[ShiftType.FULL_DAY],
        ),
        gatekeeper_user,
    )

    # First check-in
    VisitorService.check_in(
        session,
        AccessLogCheckIn(visitor_id=visitor.id, lot_id=lot.id, authorization_id=auth.id),
        gatekeeper_user,
    )

    # Second check-in without checking out first
    with pytest.raises(OpenEntryExistsError, match="already has an active check-in"):
        VisitorService.check_in(
            session,
            AccessLogCheckIn(visitor_id=visitor.id, lot_id=lot.id, authorization_id=auth.id),
            gatekeeper_user,
        )


def test_single_authorization_auto_expires_on_check_in(session: Session, gatekeeper_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G3", lot_number="03"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Diego Alves"))

    auth = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            auth_type=AuthorizationType.SINGLE,
            allowed_days=[DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN],
            allowed_shifts=[ShiftType.FULL_DAY],
        ),
        gatekeeper_user,
    )
    assert auth.status == AuthorizationStatus.ACTIVE

    # Check In
    VisitorService.check_in(
        session,
        AccessLogCheckIn(visitor_id=visitor.id, lot_id=lot.id, authorization_id=auth.id),
        gatekeeper_user,
    )

    # Verify authorization status auto-updated to EXPIRED
    updated_auth = VisitorService.get_authorization_by_id(session, auth.id)
    assert updated_auth.status == AuthorizationStatus.EXPIRED


def test_check_in_validates_revoked_or_expired(session: Session, gatekeeper_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G4", lot_number="04"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Patricia Pillar"))

    now = datetime(2026, 8, 25, 10, 0, 0)

    # Expired by valid_until date
    auth_expired = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            valid_from=now - timedelta(days=10),
            valid_until=now - timedelta(days=1),
        ),
        gatekeeper_user,
    )

    with pytest.raises(AuthorizationExpiredError):
        VisitorService.check_in(
            session,
            AccessLogCheckIn(visitor_id=visitor.id, lot_id=lot.id, authorization_id=auth_expired.id),
            gatekeeper_user,
            check_time=now,
        )

    # Revoked authorization
    auth_revoked = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(visitor_id=visitor.id),
        gatekeeper_user,
    )
    VisitorService.revoke_authorization(session, auth_revoked.id, gatekeeper_user)

    with pytest.raises(AuthorizationRevokedError):
        VisitorService.check_in(
            session,
            AccessLogCheckIn(visitor_id=visitor.id, lot_id=lot.id, authorization_id=auth_revoked.id),
            gatekeeper_user,
            check_time=now,
        )


def test_check_in_validates_day_of_week(session: Session, gatekeeper_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G5", lot_number="05"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Tiago Lacerda"))

    # Tuesday = 2026-08-25 (weekday 1 = TUE)
    tuesday_dt = datetime(2026, 8, 25, 10, 0, 0)

    auth = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            allowed_days=[DayOfWeek.MON, DayOfWeek.WED],  # Tuesday NOT allowed
            allowed_shifts=[ShiftType.FULL_DAY],
        ),
        gatekeeper_user,
    )

    with pytest.raises(AuthorizationInvalidDayError, match="day of week not allowed"):
        VisitorService.check_in(
            session,
            AccessLogCheckIn(visitor_id=visitor.id, lot_id=lot.id, authorization_id=auth.id),
            gatekeeper_user,
            check_time=tuesday_dt,
        )


def test_check_in_validates_shift(session: Session, gatekeeper_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G6", lot_number="06"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Fabio Assuncao"))

    # 14:00 (AFTERNOON)
    afternoon_dt = datetime(2026, 8, 25, 14, 0, 0)

    auth = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            allowed_days=[DayOfWeek.TUE],
            allowed_shifts=[ShiftType.MORNING],  # AFTERNOON NOT allowed
        ),
        gatekeeper_user,
    )

    with pytest.raises(AuthorizationInvalidShiftError, match="shift window not allowed"):
        VisitorService.check_in(
            session,
            AccessLogCheckIn(visitor_id=visitor.id, lot_id=lot.id, authorization_id=auth.id),
            gatekeeper_user,
            check_time=afternoon_dt,
        )


def test_api_check_in_and_check_out(client: TestClient, gatekeeper_user: User, session: Session):
    lot = LotService.create_lot(session, LotCreate(block="G7", lot_number="07"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Claudia Abreu"))
    auth = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            allowed_days=[DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN],
            allowed_shifts=[ShiftType.FULL_DAY],
        ),
        gatekeeper_user,
    )

    from app.core.security import create_access_token
    token = create_access_token(gatekeeper_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # API Check-In
    res_in = client.post(
        "/api/v1/access-logs/check-in",
        json={"visitor_id": str(visitor.id), "lot_id": str(lot.id), "authorization_id": str(auth.id)},
        headers=headers,
    )
    assert res_in.status_code == 201
    log_data = res_in.json()
    log_id = log_data["id"]

    # API List Access Logs
    res_logs = client.get(f"/api/v1/access-logs?lot_id={lot.id}", headers=headers)
    assert res_logs.status_code == 200
    assert res_logs.json()["total"] == 1

    # API Check-Out
    res_out = client.post(
        "/api/v1/access-logs/check-out",
        json={"access_log_id": log_id, "exit_notes": "All clear"},
        headers=headers,
    )
    assert res_out.status_code == 200
    assert res_out.json()["exit_notes"] == "All clear"
