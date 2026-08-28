"""Lot management API endpoints."""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.enums import LotStatus, UserRole
from app.models.user import User
from app.schemas.lot import (
    LotCreate,
    LotDetailRead,
    LotRead,
    LotUpdate,
    PaginatedLotRead,
    UserLotLinkCreate,
    UserLotLinkRead,
    UserSummaryRead,
)
from app.services.lot_service import LotService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

router = APIRouter()

_LOT_READ_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.PORTEIRO}
_LOT_WRITE_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}


def _require_lot_read_permission(current_user: User) -> None:
    """Raise 403 if the user does not have permission to read lots."""
    if current_user.role not in _LOT_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges to access lots",
        )


def _require_lot_write_permission(current_user: User) -> None:
    """Raise 403 if the user does not have permission to write lots."""
    if current_user.role not in _LOT_WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMINISTRATOR and DIRECTOR can modify lots",
        )


@router.get("/", response_model=PaginatedLotRead)
def list_lots(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    block: str | None = Query(default=None),
    status_filter: LotStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> PaginatedLotRead:
    """List lots with optional filtering by block and status."""
    _require_lot_read_permission(current_user)
    items, total = LotService.get_lots(
        session=session,
        block=block,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    items_read = [LotRead.model_validate(item) for item in items]
    return PaginatedLotRead(items=items_read, total=total, skip=skip, limit=limit)


@router.post("/", response_model=LotRead, status_code=status.HTTP_201_CREATED)
def create_lot(
    lot_in: LotCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> LotRead:
    """Create a new lot. ADMINISTRATOR and DIRECTOR only."""
    _require_lot_write_permission(current_user)
    db_lot = LotService.create_lot(session=session, lot_in=lot_in)
    return LotRead.model_validate(db_lot)


@router.get("/{lot_id}", response_model=LotDetailRead)
def get_lot(
    lot_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> LotDetailRead:
    """Get detailed lot information along with linked users."""
    _require_lot_read_permission(current_user)
    return LotService.get_lot_detail(session=session, lot_id=lot_id)


@router.put("/{lot_id}", response_model=LotRead)
def update_lot(
    lot_id: UUID,
    lot_in: LotUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> LotRead:
    """Update a lot. ADMINISTRATOR and DIRECTOR only."""
    _require_lot_write_permission(current_user)
    db_lot = LotService.get_lot_by_id(session=session, lot_id=lot_id)
    updated_lot = LotService.update_lot(
        session=session, db_lot=db_lot, lot_in=lot_in
    )
    return LotRead.model_validate(updated_lot)


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lot(
    lot_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_active_admin)],
) -> None:
    """Soft delete a lot. ADMINISTRATOR only."""
    db_lot = LotService.get_lot_by_id(session=session, lot_id=lot_id)
    LotService.delete_lot(session=session, db_lot=db_lot)


@router.post(
    "/{lot_id}/users",
    response_model=UserLotLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def link_user_to_lot(
    lot_id: UUID,
    link_in: UserLotLinkCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> UserLotLinkRead:
    """Bind a user to a lot. ADMINISTRATOR and DIRECTOR only."""
    _require_lot_write_permission(current_user)
    link = LotService.link_user(session=session, lot_id=lot_id, link_in=link_in)
    user = session.get(User, link.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserLotLinkRead(
        id=link.id,
        user_id=link.user_id,
        lot_id=link.lot_id,
        association_type=link.association_type,
        is_primary=link.is_primary,
        start_date=link.start_date,
        end_date=link.end_date,
        created_at=link.created_at,
        user=UserSummaryRead(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
        ),
    )


@router.delete("/{lot_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_user_from_lot(
    lot_id: UUID,
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Unlink a user from a lot. ADMINISTRATOR and DIRECTOR only."""
    _require_lot_write_permission(current_user)
    LotService.unlink_user(session=session, lot_id=lot_id, user_id=user_id)
