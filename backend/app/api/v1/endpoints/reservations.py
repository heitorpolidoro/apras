"""ReservableSpace and SpaceReservation API endpoints."""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.enums import UserRole
from app.models.reservation import ReservableSpace
from app.models.user import User
from app.schemas.reservation import (
    ReservableSpaceCreate,
    ReservableSpaceRead,
    ReservableSpaceUpdate,
    SpaceReservationCreate,
    SpaceReservationDecision,
    SpaceReservationRead,
)
from app.services.reservation_service import (
    ReservableSpaceService,
    SpaceReservationService,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

spaces_router = APIRouter()
reservations_router = APIRouter()

_SPACE_WRITE_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}


def _require_space_write_permission(current_user: User) -> None:
    """Raise 403 if the user does not have permission to write spaces."""
    if current_user.role not in _SPACE_WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMINISTRATOR and DIRECTOR can manage reservable spaces",
        )


def _require_non_guest(current_user: User) -> None:
    """Raise 403 if the user is a GUEST (cannot create reservations)."""
    if current_user.role == UserRole.GUEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GUEST cannot create reservations",
        )


# ---------------------------------------------------------------------------
# ReservableSpace endpoints
# ---------------------------------------------------------------------------


@spaces_router.get("/", response_model=list[ReservableSpaceRead])
def list_reservable_spaces(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[ReservableSpaceRead]:
    """List active reservable spaces. Any authenticated user, including GUEST."""
    _ = current_user
    return ReservableSpaceService.get_spaces(session=session)


@spaces_router.post(
    "/", response_model=ReservableSpaceRead, status_code=status.HTTP_201_CREATED
)
def create_reservable_space(
    space_in: ReservableSpaceCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ReservableSpaceRead:
    """Create a new reservable space. ADMINISTRATOR/DIRECTOR only."""
    _require_space_write_permission(current_user)
    return ReservableSpaceService.create_space(session=session, space_in=space_in)


@spaces_router.patch("/{space_id}", response_model=ReservableSpaceRead)
def update_reservable_space(
    space_id: UUID,
    space_in: ReservableSpaceUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ReservableSpaceRead:
    """Update a reservable space. ADMINISTRATOR/DIRECTOR only."""
    _require_space_write_permission(current_user)
    db_space = session.get(ReservableSpace, space_id)
    if not db_space:
        raise HTTPException(status_code=404, detail="Reservable space not found")
    return ReservableSpaceService.update_space(
        session=session, db_space=db_space, space_in=space_in
    )


@spaces_router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_reservable_space(
    space_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Deactivate a reservable space (soft delete). ADMINISTRATOR/DIRECTOR only."""
    _require_space_write_permission(current_user)
    db_space = session.get(ReservableSpace, space_id)
    if not db_space:
        raise HTTPException(status_code=404, detail="Reservable space not found")
    ReservableSpaceService.deactivate_space(session=session, db_space=db_space)


# ---------------------------------------------------------------------------
# SpaceReservation endpoints
# ---------------------------------------------------------------------------


@reservations_router.post(
    "/", response_model=SpaceReservationRead, status_code=status.HTTP_201_CREATED
)
def create_space_reservation(
    reservation_in: SpaceReservationCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> SpaceReservationRead:
    """Create a new space reservation. Any authenticated user except GUEST."""
    _require_non_guest(current_user)
    reservation = SpaceReservationService.create_reservation(
        session=session, current_user=current_user, reservation_in=reservation_in
    )
    return SpaceReservationService.get_reservation(
        session=session, current_user=current_user, reservation_id=reservation.id
    )


@reservations_router.get("/", response_model=list[SpaceReservationRead])
def list_space_reservations(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    space_id: UUID | None = None,
    mine: bool = False,
) -> list[SpaceReservationRead]:
    """List space reservations per the visibility/masking precedence rules."""
    _require_non_guest(current_user)
    return SpaceReservationService.list_reservations(
        session=session, current_user=current_user, space_id=space_id, mine=mine
    )


@reservations_router.get("/{reservation_id}", response_model=SpaceReservationRead)
def get_space_reservation(
    reservation_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> SpaceReservationRead:
    """Get a single space reservation by id, per visibility rules."""
    _require_non_guest(current_user)
    return SpaceReservationService.get_reservation(
        session=session, current_user=current_user, reservation_id=reservation_id
    )


@reservations_router.post(
    "/{reservation_id}/approve", response_model=SpaceReservationRead
)
def approve_space_reservation(
    reservation_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    _decision: SpaceReservationDecision | None = None,
) -> SpaceReservationRead:
    """Approve a PENDING reservation. ADMINISTRATOR/DIRECTOR only."""
    SpaceReservationService.decide_reservation(
        session=session,
        current_user=current_user,
        reservation_id=reservation_id,
        approve=True,
    )
    return SpaceReservationService.get_reservation(
        session=session, current_user=current_user, reservation_id=reservation_id
    )


@reservations_router.post(
    "/{reservation_id}/reject", response_model=SpaceReservationRead
)
def reject_space_reservation(
    reservation_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    _decision: SpaceReservationDecision | None = None,
) -> SpaceReservationRead:
    """Reject a PENDING reservation. ADMINISTRATOR/DIRECTOR only."""
    SpaceReservationService.decide_reservation(
        session=session,
        current_user=current_user,
        reservation_id=reservation_id,
        approve=False,
    )
    return SpaceReservationService.get_reservation(
        session=session, current_user=current_user, reservation_id=reservation_id
    )


@reservations_router.post(
    "/{reservation_id}/cancel", response_model=SpaceReservationRead
)
def cancel_space_reservation(
    reservation_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> SpaceReservationRead:
    """Cancel a PENDING/CONFIRMED reservation, per the cancellation rules."""
    SpaceReservationService.cancel_reservation(
        session=session, current_user=current_user, reservation_id=reservation_id
    )
    return SpaceReservationService.get_reservation(
        session=session, current_user=current_user, reservation_id=reservation_id
    )
