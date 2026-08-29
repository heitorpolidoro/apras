"""API endpoints for Asset and Inventory management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel import Session

from app.api import deps
from app.models.enums import AssetCategory, AssetCondition
from app.models.user import User
from app.schemas.asset import (
    AssetCreate,
    AssetDetailRead,
    AssetRead,
    AssetSummaryRead,
    AssetUpdate,
    InventoryMovementCreate,
    InventoryMovementRead,
    PaginatedAssetRead,
)
from app.services.asset_service import AssetService

router = APIRouter()


@router.get("")
def list_assets(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    category: Annotated[AssetCategory | None, Query()] = None,
    location: Annotated[str | None, Query()] = None,
    is_consumable: Annotated[bool | None, Query()] = None,
    condition: Annotated[AssetCondition | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    low_stock_only: Annotated[bool, Query()] = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PaginatedAssetRead:
    """List assets and inventory with search, filtering, and pagination."""
    return AssetService.list_assets(
        session=session,
        current_user=current_user,
        category=category,
        location=location,
        is_consumable=is_consumable,
        condition=condition,
        search=search,
        low_stock_only=low_stock_only,
        skip=skip,
        limit=limit,
    )


@router.get("/summary")
def get_asset_summary(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AssetSummaryRead:
    """Get aggregate metrics for the asset and inventory dashboard."""
    return AssetService.get_asset_summary(session=session, current_user=current_user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: AssetCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AssetRead:
    """Create a new asset or inventory item (Administrator / Director only)."""
    return AssetService.create_asset(
        session=session, current_user=current_user, asset_in=asset_in
    )


@router.get("/{asset_id}")
def get_asset_by_id(
    asset_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AssetDetailRead:
    """Get asset details with movement history."""
    return AssetService.get_asset_by_id(
        session=session, current_user=current_user, asset_id=asset_id
    )


@router.put("/{asset_id}")
def update_asset(
    asset_id: UUID,
    asset_in: AssetUpdate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AssetRead:
    """Update asset metadata (Administrator / Director only)."""
    return AssetService.update_asset(
        session=session,
        current_user=current_user,
        asset_id=asset_id,
        asset_in=asset_in,
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Response:
    """Delete an asset and its movement history (Administrator / Director only)."""
    AssetService.delete_asset(
        session=session, current_user=current_user, asset_id=asset_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{asset_id}/movements",
    status_code=status.HTTP_201_CREATED,
)
def record_movement(
    asset_id: UUID,
    movement_in: InventoryMovementCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> InventoryMovementRead:
    """Record an inventory or asset stock movement."""
    return AssetService.record_movement(
        session=session,
        current_user=current_user,
        asset_id=asset_id,
        movement_in=movement_in,
    )
