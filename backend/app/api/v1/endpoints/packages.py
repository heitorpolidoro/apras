"""API endpoints for Package (encomendas) tracking."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api import deps
from app.models.enums import PackageStatus
from app.models.user import User
from app.schemas.package import (
    LotSummaryRead,
    PackageCreate,
    PackagePickup,
    PackageRead,
    PaginatedPackageRead,
)
from app.services.package_service import PackageService

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_package(
    package_in: PackageCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PackageRead:
    """Log a new package's arrival for a lot."""
    return PackageService.create_package(session, current_user, package_in)


@router.get("/queue")
def get_awaiting_pickup_queue(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PaginatedPackageRead:
    """List all packages awaiting pickup across all lots (gatekeeper queue)."""
    items, total = PackageService.get_awaiting_pickup_queue(
        session, current_user, skip=skip, limit=limit
    )
    return PaginatedPackageRead(items=items, total=total, skip=skip, limit=limit)


@router.get("/my-lots")
def get_my_lots(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> list[LotSummaryRead]:
    """Return the caller's own linked lot(s), for resident self-service lookup."""
    return PackageService.get_my_lots(session, current_user)


@router.get("")
def get_packages_for_lot(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    lot_id: UUID,
    status_filter: Annotated[PackageStatus | None, Query(alias="status")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PaginatedPackageRead:
    """List packages for a specific lot."""
    items, total = PackageService.get_packages_for_lot(
        session,
        current_user,
        lot_id=lot_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return PaginatedPackageRead(items=items, total=total, skip=skip, limit=limit)


@router.get("/{package_id}")
def get_package_by_id(
    package_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PackageRead:
    """Retrieve a single package by ID."""
    return PackageService.get_package_by_id(session, current_user, package_id)


@router.post("/{package_id}/pickup")
def mark_picked_up(
    package_id: UUID,
    pickup_in: PackagePickup,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PackageRead:
    """Mark a package as picked up."""
    return PackageService.mark_picked_up(session, current_user, package_id, pickup_in)
