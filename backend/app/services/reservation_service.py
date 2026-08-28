"""Service layer for ReservableSpace and SpaceReservation business logic."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.core.exceptions import (
    ForbiddenError,
    ReservableSpaceNotFoundError,
    SpaceReservationConflictError,
    SpaceReservationNotFoundError,
)
from app.models.enums import ReservationStatus, UserRole
from app.models.reservation import ReservableSpace, SpaceReservation
from app.models.user import User
from app.schemas.reservation import (
    ReservableSpaceCreate,
    ReservableSpaceUpdate,
    SpaceReservationCreate,
    SpaceReservationRead,
)

_STAFF_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}
_BLOCKING_STATUSES = [ReservationStatus.CONFIRMED, ReservationStatus.PENDING]


class ReservableSpaceService:
    """Service class for ReservableSpace CRUD operations."""

    @staticmethod
    def create_space(
        session: Session, space_in: ReservableSpaceCreate
    ) -> ReservableSpace:
        """Create a new reservable space."""
        db_space = ReservableSpace.model_validate(space_in)
        session.add(db_space)
        session.commit()
        session.refresh(db_space)
        return db_space

    @staticmethod
    def get_spaces(
        session: Session, only_active: bool = True
    ) -> list[ReservableSpace]:
        """List reservable spaces."""
        statement = select(ReservableSpace)
        if only_active:
            statement = statement.where(ReservableSpace.is_active.is_(True))
        return session.exec(statement).all()

    @staticmethod
    def update_space(
        session: Session,
        db_space: ReservableSpace,
        space_in: ReservableSpaceUpdate,
    ) -> ReservableSpace:
        """Update an existing reservable space."""
        update_data = space_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_space, key, value)

        session.add(db_space)
        session.commit()
        session.refresh(db_space)
        return db_space

    @staticmethod
    def deactivate_space(session: Session, db_space: ReservableSpace) -> None:
        """Deactivate a reservable space (soft delete)."""
        db_space.is_active = False
        session.add(db_space)
        session.commit()


class SpaceReservationService:
    """Service class for SpaceReservation booking, RBAC and masking logic."""

    @staticmethod
    def check_conflict(
        session: Session,
        space_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_reservation_id: UUID | None = None,
        statuses: list[ReservationStatus] | None = None,
    ) -> bool:
        """Return True if the requested window overlaps a blocking reservation.

        A blocking reservation is one whose status is CONFIRMED or PENDING
        on the same space (the default `statuses`). Uses a standard
        half-open interval overlap test: two windows [a, b) and [c, d)
        overlap iff a < d and c < b.

        `statuses` may be narrowed by callers that need a different
        definition of "blocking" -- e.g. the approval re-check only
        considers already-CONFIRMED rows (see `decide_reservation`), since
        two PENDING requests are expected to be able to coexist until one
        of them is decided.
        """
        blocking_statuses = statuses if statuses is not None else _BLOCKING_STATUSES
        statement = (
            select(SpaceReservation)
            .where(SpaceReservation.space_id == space_id)
            .where(SpaceReservation.status.in_(blocking_statuses))
            .where(SpaceReservation.start_time < end_time)
            .where(SpaceReservation.end_time > start_time)
        )
        if exclude_reservation_id:
            statement = statement.where(
                SpaceReservation.id != exclude_reservation_id
            )
        return session.exec(statement).first() is not None

    @staticmethod
    def _build_read(
        session: Session,
        current_user: User,
        reservation: SpaceReservation,
        *,
        mask: bool,
    ) -> SpaceReservationRead:
        """Build a SpaceReservationRead, masking identity/notes if requested."""
        space = session.get(ReservableSpace, reservation.space_id)
        is_own = reservation.reserved_by_id == current_user.id

        if mask and not is_own:
            return SpaceReservationRead(
                id=reservation.id,
                space_id=reservation.space_id,
                space_name=space.name if space else None,
                reserved_by_id=None,
                reserved_by_name=None,
                lot_id=None,
                start_time=reservation.start_time,
                end_time=reservation.end_time,
                status=reservation.status,
                notes=None,
                decided_by_id=None,
                decided_at=None,
                cancelled_at=None,
                created_at=reservation.created_at,
            )

        reserved_by_name = None
        if reservation.reserved_by:
            reserved_by_name = (
                reservation.reserved_by.full_name or reservation.reserved_by.email
            )

        return SpaceReservationRead(
            id=reservation.id,
            space_id=reservation.space_id,
            space_name=space.name if space else None,
            reserved_by_id=reservation.reserved_by_id,
            reserved_by_name=reserved_by_name,
            lot_id=reservation.lot_id,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            status=reservation.status,
            notes=reservation.notes,
            decided_by_id=reservation.decided_by_id,
            decided_at=reservation.decided_at,
            cancelled_at=reservation.cancelled_at,
            created_at=reservation.created_at,
        )

    @classmethod
    def create_reservation(
        cls,
        session: Session,
        current_user: User,
        reservation_in: SpaceReservationCreate,
    ) -> SpaceReservation:
        """Create a new reservation, enforcing the double-booking check."""
        space = session.get(ReservableSpace, reservation_in.space_id)
        if not space or not space.is_active:
            raise ReservableSpaceNotFoundError(reservation_in.space_id)

        if cls.check_conflict(
            session,
            space_id=reservation_in.space_id,
            start_time=reservation_in.start_time,
            end_time=reservation_in.end_time,
        ):
            raise SpaceReservationConflictError

        status_value = (
            ReservationStatus.PENDING
            if space.requires_approval
            else ReservationStatus.CONFIRMED
        )

        reservation = SpaceReservation(
            space_id=reservation_in.space_id,
            reserved_by_id=current_user.id,
            lot_id=reservation_in.lot_id,
            start_time=reservation_in.start_time,
            end_time=reservation_in.end_time,
            status=status_value,
            notes=reservation_in.notes,
            created_at=datetime.utcnow(),
        )
        session.add(reservation)
        session.commit()
        session.refresh(reservation)
        return reservation

    @classmethod
    def list_reservations(
        cls,
        session: Session,
        current_user: User,
        space_id: UUID | None = None,
        mine: bool = False,
    ) -> list[SpaceReservationRead]:
        """List reservations, applying the exact visibility precedence rules.

        Precedence:
        - mine=True (with or without space_id): caller's own rows only,
          full detail, any status, for every role.
        - mine omitted/false, space_id omitted, staff: every reservation,
          full detail.
        - mine omitted/false, space_id omitted, non-staff: caller's own
          rows only, full detail.
        - mine omitted/false, space_id set, staff: every reservation for
          that space, full detail.
        - mine omitted/false, space_id set, non-staff: masked busy-slot
          calendar view (own row unmasked).
        """
        is_staff = current_user.role in _STAFF_ROLES
        statement = select(SpaceReservation)

        if mine:
            statement = statement.where(
                SpaceReservation.reserved_by_id == current_user.id
            )
            if space_id:
                statement = statement.where(SpaceReservation.space_id == space_id)
            mask = False
        elif space_id is None:
            if is_staff:
                mask = False
            else:
                statement = statement.where(
                    SpaceReservation.reserved_by_id == current_user.id
                )
                mask = False
        else:
            statement = statement.where(SpaceReservation.space_id == space_id)
            if is_staff:
                mask = False
            else:
                statement = statement.where(
                    SpaceReservation.status.in_(_BLOCKING_STATUSES)
                )
                mask = True

        statement = statement.order_by(SpaceReservation.start_time)
        reservations = session.exec(statement).all()
        return [
            cls._build_read(session, current_user, r, mask=mask)
            for r in reservations
        ]

    @classmethod
    def get_reservation(
        cls, session: Session, current_user: User, reservation_id: UUID
    ) -> SpaceReservationRead:
        """Get a single reservation by id, per visibility rules."""
        reservation = session.get(SpaceReservation, reservation_id)
        is_staff = current_user.role in _STAFF_ROLES
        if not reservation or (
            not is_staff and reservation.reserved_by_id != current_user.id
        ):
            raise SpaceReservationNotFoundError(reservation_id)
        return cls._build_read(session, current_user, reservation, mask=False)

    @classmethod
    def decide_reservation(
        cls,
        session: Session,
        current_user: User,
        reservation_id: UUID,
        approve: bool,
    ) -> SpaceReservation:
        """Approve or reject a PENDING reservation. Staff only."""
        if current_user.role not in _STAFF_ROLES:
            raise ForbiddenError(
                "Only ADMINISTRATOR and DIRECTOR can approve or reject reservations"
            )

        reservation = session.get(SpaceReservation, reservation_id)
        if not reservation:
            raise SpaceReservationNotFoundError(reservation_id)

        if approve and cls.check_conflict(
            session,
            space_id=reservation.space_id,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            exclude_reservation_id=reservation.id,
            statuses=[ReservationStatus.CONFIRMED],
        ):
            raise SpaceReservationConflictError

        reservation.status = (
            ReservationStatus.CONFIRMED if approve else ReservationStatus.REJECTED
        )
        reservation.decided_by_id = current_user.id
        reservation.decided_at = datetime.utcnow()

        session.add(reservation)
        session.commit()
        session.refresh(reservation)
        return reservation

    @classmethod
    def cancel_reservation(
        cls, session: Session, current_user: User, reservation_id: UUID
    ) -> SpaceReservation:
        """Cancel a PENDING/CONFIRMED reservation, per the ownership/timing rules."""
        reservation = session.get(SpaceReservation, reservation_id)
        if not reservation or reservation.status not in _BLOCKING_STATUSES:
            raise SpaceReservationNotFoundError(reservation_id)

        is_staff = current_user.role in _STAFF_ROLES
        is_owner = reservation.reserved_by_id == current_user.id

        if not is_staff:
            if not is_owner:
                raise ForbiddenError(
                    "You can only cancel your own reservations"
                )
            if reservation.start_time <= datetime.utcnow():
                raise ForbiddenError(
                    "Cannot cancel a reservation that has already started"
                )

        reservation.status = ReservationStatus.CANCELLED
        reservation.cancelled_at = datetime.utcnow()

        session.add(reservation)
        session.commit()
        session.refresh(reservation)
        return reservation
