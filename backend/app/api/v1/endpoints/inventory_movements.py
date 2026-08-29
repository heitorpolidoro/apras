"""API endpoints for global inventory movement logs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api import deps
from app.models.enums import MovementType
from app.models.user import User
from app.schemas.asset import PaginatedInventoryMovementRead
from app.services.asset_service import AssetService

router = APIRouter()


@router.get("")
def list_inventory_movements(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    asset_id: Annotated[UUID | None, Query()] = None,
    movement_type: Annotated[MovementType | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PaginatedInventoryMovementRead:
    """List inventory movement audit records across all assets."""
    return AssetService.list_inventory_movements(
        session=session,
        current_user=current_user,
        asset_id=asset_id,
        movement_type=movement_type,
        skip=skip,
        limit=limit,
    )
