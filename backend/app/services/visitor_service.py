"""Service layer for Visitor, Authorization, and AccessLog management."""

from datetime import datetime, timedelta
import json
import logging
from typing import Optional
from uuid import UUID

from app.core.exceptions import (
    AccessLogNotFoundError,
    AuthorizationExpiredError,
    AuthorizationInvalidDayError,
    AuthorizationInvalidShiftError,
    AuthorizationNotFoundError,
    AuthorizationRevokedError,
    DomainError,
    ForbiddenError,
    LotNotFoundError,
    OpenEntryExistsError,
    VisitorNotFoundError,
)
from app.models.enums import AuthorizationStatus, AuthorizationType, DayOfWeek, ShiftType, UserRole
from app.models.lot import Lot, UserLotLink
from app.models.resident import Resident
from app.models.user import User
from app.models.visitor import AccessLog, Visitor, VisitorAuthorization
from app.schemas.visitor import (
    AccessLogCheckIn,
    AccessLogCheckOut,
    VisitorAuthorizationCreate,
    VisitorCreate,
    VisitorUpdate,
)
from sqlmodel import Session, func, select

logger = logging.getLogger(__name__)

DAY_MAP = {
    0: DayOfWeek.MON.value,
    1: DayOfWeek.TUE.value,
    2: DayOfWeek.WED.value,
    3: DayOfWeek.THU.value,
    4: DayOfWeek.FRI.value,
    5: DayOfWeek.SAT.value,
    6: DayOfWeek.SUN.value,
}


def _get_shift_for_datetime(dt: datetime) -> str:
    hour = dt.hour
    if 6 <= hour < 12:
        return ShiftType.MORNING.value
    elif 12 <= hour < 18:
        return ShiftType.AFTERNOON.value
    else:
        return ShiftType.NIGHT.value


class VisitorService:
    @staticmethod
    def _check_lot_access(session: Session, lot_id: UUID, current_user: User) -> None:
        """Check if current user is allowed to access or manage authorizations for lot_id."""
        if current_user.role in (
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
            UserRole.MANAGER,
        ):
            return

        # Check if user is linked to lot via UserLotLink
        user_lot_link = session.exec(
            select(UserLotLink).where(
                UserLotLink.user_id == current_user.id,
                UserLotLink.lot_id == lot_id,
            )
        ).first()
        if user_lot_link:
            return

        # Check if user is linked to lot via Resident table
        resident_link = session.exec(
            select(Resident).where(
                Resident.user_id == current_user.id,
                Resident.lot_id == lot_id,
                Resident.is_active == True,  # noqa: E712
            )
        ).first()
        if resident_link:
            return

        raise ForbiddenError("You do not have access to manage authorizations for this lot")

    @staticmethod
    def get_user_linked_lot_ids(session: Session, current_user: User) -> list[UUID]:
        """Return list of lot IDs linked to the current user."""
        if current_user.role in (
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
            UserRole.MANAGER,
        ):
            all_lots = session.exec(select(Lot.id)).all()
            return list(all_lots)

        linked_ids: set[UUID] = set()
        user_links = session.exec(
            select(UserLotLink.lot_id).where(UserLotLink.user_id == current_user.id)
        ).all()
        linked_ids.update(user_links)

        res_links = session.exec(
            select(Resident.lot_id).where(
                Resident.user_id == current_user.id, Resident.is_active == True  # noqa: E712
            )
        ).all()
        linked_ids.update(res_links)

        return list(linked_ids)

    # -------------------------------------------------------------------------
    # Visitor Management
    # -------------------------------------------------------------------------

    @staticmethod
    def search_visitors(
        session: Session,
        q: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Visitor], int]:
        """Search visitors by name, CPF, company, or vehicle plate."""
        query = select(Visitor)
        if q:
            term = f"%{q.strip()}%"
            query = query.where(
                (Visitor.full_name.ilike(term))  # type: ignore[attr-defined]
                | (Visitor.cpf.ilike(term))  # type: ignore[attr-defined]
                | (Visitor.company_name.ilike(term))  # type: ignore[attr-defined]
                | (Visitor.vehicle_plate.ilike(term))  # type: ignore[attr-defined]
            )

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        visitors = session.exec(
            query.offset(skip).limit(limit).order_by(Visitor.full_name)
        ).all()

        return list(visitors), total

    @staticmethod
    def create_visitor(session: Session, visitor_in: VisitorCreate) -> Visitor:
        """Create a new visitor record."""
        visitor = Visitor(
            full_name=visitor_in.full_name,
            cpf=visitor_in.cpf,
            rg=visitor_in.rg,
            phone=visitor_in.phone,
            company_name=visitor_in.company_name,
            vehicle_plate=visitor_in.vehicle_plate,
            vehicle_model=visitor_in.vehicle_model,
            notes=visitor_in.notes,
        )
        session.add(visitor)
        session.commit()
        session.refresh(visitor)
        return visitor

    @staticmethod
    def get_visitor_by_id(session: Session, visitor_id: UUID) -> Visitor:
        """Get visitor by ID or raise VisitorNotFoundError."""
        visitor = session.get(Visitor, visitor_id)
        if not visitor:
            raise VisitorNotFoundError(visitor_id)
        return visitor

    @staticmethod
    def update_visitor(
        session: Session, visitor_id: UUID, visitor_in: VisitorUpdate
    ) -> Visitor:
        """Update visitor details."""
        visitor = VisitorService.get_visitor_by_id(session, visitor_id)
        update_data = visitor_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(visitor, key, value)
        visitor.updated_at = datetime.utcnow()
        session.add(visitor)
        session.commit()
        session.refresh(visitor)
        return visitor

    # -------------------------------------------------------------------------
    # Authorization Management
    # -------------------------------------------------------------------------

    @staticmethod
    def create_authorization(
        session: Session,
        lot_id: UUID,
        auth_in: VisitorAuthorizationCreate,
        current_user: User,
    ) -> VisitorAuthorization:
        """Create a visitor pre-authorization for a lot."""
        lot = session.get(Lot, lot_id)
        if not lot:
            raise LotNotFoundError(lot_id)

        VisitorService._check_lot_access(session, lot_id, current_user)
        VisitorService.get_visitor_by_id(session, auth_in.visitor_id)

        # Enforce max 1 year validity for PERMANENT type
        if auth_in.auth_type == AuthorizationType.PERMANENT and auth_in.valid_until:
            start_ref = auth_in.valid_from or datetime.utcnow()
            if auth_in.valid_until - start_ref > timedelta(days=366):
                raise DomainError("Permanent authorization cannot exceed 1 year validity")

        days_str_list = [d.value if hasattr(d, "value") else str(d) for d in auth_in.allowed_days]
        shifts_str_list = [s.value if hasattr(s, "value") else str(s) for s in auth_in.allowed_shifts]

        authorization = VisitorAuthorization(
            visitor_id=auth_in.visitor_id,
            lot_id=lot_id,
            authorizer_user_id=current_user.id,
            auth_type=auth_in.auth_type,
            allowed_days_json=json.dumps(days_str_list),
            allowed_shifts_json=json.dumps(shifts_str_list),
            valid_from=auth_in.valid_from,
            valid_until=auth_in.valid_until,
            status=AuthorizationStatus.ACTIVE,
            notes=auth_in.notes,
        )
        session.add(authorization)
        session.commit()
        session.refresh(authorization)
        return authorization

    @staticmethod
    def get_lot_authorizations(
        session: Session,
        lot_id: UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        status: AuthorizationStatus | None = None,
    ) -> tuple[list[VisitorAuthorization], int]:
        """List pre-authorizations for a specific lot."""
        lot = session.get(Lot, lot_id)
        if not lot:
            raise LotNotFoundError(lot_id)

        VisitorService._check_lot_access(session, lot_id, current_user)

        query = select(VisitorAuthorization).where(VisitorAuthorization.lot_id == lot_id)
        if status:
            query = query.where(VisitorAuthorization.status == status)

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        auths = session.exec(
            query.offset(skip).limit(limit).order_by(VisitorAuthorization.created_at.desc())  # type: ignore[attr-defined]
        ).all()

        return list(auths), total

    @staticmethod
    def get_authorization_by_id(session: Session, auth_id: UUID) -> VisitorAuthorization:
        """Get authorization by ID or raise AuthorizationNotFoundError."""
        auth = session.get(VisitorAuthorization, auth_id)
        if not auth:
            raise AuthorizationNotFoundError(auth_id)
        return auth

    @staticmethod
    def get_authorization_for_user(
        session: Session, auth_id: UUID, current_user: User
    ) -> VisitorAuthorization:
        """Get an authorization by ID, enforcing the same lot-scoping rule as the other routes."""
        auth = VisitorService.get_authorization_by_id(session, auth_id)
        VisitorService._check_lot_access(session, auth.lot_id, current_user)
        return auth

    @staticmethod
    def revoke_authorization(
        session: Session, auth_id: UUID, current_user: User
    ) -> VisitorAuthorization:
        """Revoke a pre-authorization."""
        auth = VisitorService.get_authorization_by_id(session, auth_id)

        if current_user.role not in (
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
            UserRole.MANAGER,
        ) and auth.authorizer_user_id != current_user.id:
            # Check if current user is linked to the lot
            VisitorService._check_lot_access(session, auth.lot_id, current_user)

        auth.status = AuthorizationStatus.REVOKED
        auth.updated_at = datetime.utcnow()
        session.add(auth)
        session.commit()
        session.refresh(auth)
        return auth

    # -------------------------------------------------------------------------
    # Gatekeeper Check-In / Check-Out
    # -------------------------------------------------------------------------

    @staticmethod
    def check_in(
        session: Session,
        check_in_in: AccessLogCheckIn,
        current_user: User,
        check_time: datetime | None = None,
    ) -> AccessLog:
        """Register visitor entry at gate after validating pre-authorization constraints."""
        now = check_time or datetime.utcnow()

        # Rejects visitors who already have an active open AccessLog
        open_log = session.exec(
            select(AccessLog).where(
                AccessLog.visitor_id == check_in_in.visitor_id,
                AccessLog.exit_time.is_(None),  # type: ignore[attr-defined]
            )
        ).first()
        if open_log:
            raise OpenEntryExistsError("Visitor already has an active check-in")

        # Locate authorization
        auth: VisitorAuthorization | None = None
        if check_in_in.authorization_id:
            auth = session.get(VisitorAuthorization, check_in_in.authorization_id)
            if not auth:
                raise AuthorizationNotFoundError(check_in_in.authorization_id)
        else:
            auth = session.exec(
                select(VisitorAuthorization).where(
                    VisitorAuthorization.visitor_id == check_in_in.visitor_id,
                    VisitorAuthorization.lot_id == check_in_in.lot_id,
                    VisitorAuthorization.status == AuthorizationStatus.ACTIVE,
                ).order_by(VisitorAuthorization.created_at.desc())  # type: ignore[attr-defined]
            ).first()
            if not auth:
                raise AuthorizationNotFoundError("No active authorization found for visitor")

        # Validate authorization status
        if auth.status == AuthorizationStatus.REVOKED:
            raise AuthorizationRevokedError("Authorization has been revoked")

        if auth.status == AuthorizationStatus.EXPIRED:
            raise AuthorizationExpiredError("Authorization has expired")

        # Validate date window
        if auth.valid_from and now < auth.valid_from:
            raise AuthorizationExpiredError("Authorization not yet valid")

        if auth.valid_until and now > auth.valid_until:
            auth.status = AuthorizationStatus.EXPIRED
            auth.updated_at = now
            session.add(auth)
            session.commit()
            raise AuthorizationExpiredError("Authorization has expired")

        # Validate day of week
        current_day_str = DAY_MAP[now.weekday()]
        allowed_days = json.loads(auth.allowed_days_json)
        if current_day_str not in allowed_days:
            raise AuthorizationInvalidDayError("Entry denied: day of week not allowed")

        # Validate shift
        current_shift_str = _get_shift_for_datetime(now)
        allowed_shifts = json.loads(auth.allowed_shifts_json)
        if (
            ShiftType.FULL_DAY.value not in allowed_shifts
            and current_shift_str not in allowed_shifts
        ):
            raise AuthorizationInvalidShiftError("Entry denied: shift window not allowed")

        # Register entry log
        access_log = AccessLog(
            authorization_id=auth.id,
            visitor_id=check_in_in.visitor_id,
            lot_id=check_in_in.lot_id,
            entry_time=now,
            gatekeeper_user_id=current_user.id,
            entry_notes=check_in_in.entry_notes,
        )
        session.add(access_log)

        # Single-entry auto-expiration
        if auth.auth_type == AuthorizationType.SINGLE:
            auth.status = AuthorizationStatus.EXPIRED
            auth.updated_at = now
            session.add(auth)

        session.commit()
        session.refresh(access_log)

        # Trigger notification log
        visitor = session.get(Visitor, check_in_in.visitor_id)
        visitor_name = visitor.full_name if visitor else str(check_in_in.visitor_id)
        logger.info(
            f"[In-App Notification] Visitor '{visitor_name}' checked in at lot {check_in_in.lot_id} (gatekeeper: {current_user.id})"
        )

        return access_log

    @staticmethod
    def check_out(
        session: Session,
        check_out_in: AccessLogCheckOut,
        current_user: User,
        check_time: datetime | None = None,
    ) -> AccessLog:
        """Register visitor exit at gate."""
        now = check_time or datetime.utcnow()
        log: AccessLog | None = None

        if check_out_in.access_log_id:
            log = session.get(AccessLog, check_out_in.access_log_id)
            if not log or log.exit_time is not None:
                raise AccessLogNotFoundError("No active open check-in found for given ID")
        elif check_out_in.visitor_id:
            log = session.exec(
                select(AccessLog).where(
                    AccessLog.visitor_id == check_out_in.visitor_id,
                    AccessLog.exit_time.is_(None),  # type: ignore[attr-defined]
                )
            ).first()
            if not log:
                raise AccessLogNotFoundError("No active open check-in found for visitor")
        else:
            raise AccessLogNotFoundError("Must provide access_log_id or visitor_id for check-out")

        log.exit_time = now
        log.exit_notes = check_out_in.exit_notes
        log.gatekeeper_user_id = current_user.id
        session.add(log)
        session.commit()
        session.refresh(log)
        return log

    @staticmethod
    def get_access_logs(
        session: Session,
        current_user: User,
        lot_id: UUID | None = None,
        visitor_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AccessLog], int]:
        """Query access log timeline history."""
        query = select(AccessLog)

        # RBAC check: non-admin/director/manager restricted to their own linked lots
        if current_user.role not in (
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
            UserRole.MANAGER,
        ):
            linked_lot_ids = VisitorService.get_user_linked_lot_ids(session, current_user)
            if lot_id:
                if lot_id not in linked_lot_ids:
                    raise ForbiddenError("You do not have access to view logs for this lot")
                query = query.where(AccessLog.lot_id == lot_id)
            else:
                query = query.where(AccessLog.lot_id.in_(linked_lot_ids))  # type: ignore[attr-defined]
        else:
            if lot_id:
                query = query.where(AccessLog.lot_id == lot_id)

        if visitor_id:
            query = query.where(AccessLog.visitor_id == visitor_id)

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        logs = session.exec(
            query.offset(skip).limit(limit).order_by(AccessLog.entry_time.desc())  # type: ignore[attr-defined]
        ).all()

        return list(logs), total
