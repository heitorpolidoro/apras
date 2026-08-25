"""API endpoints for Resident management."""

from typing import Annotated
from uuid import UUID

from app.api import deps
from app.core.exceptions import ForbiddenError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.resident import (
    LinkUserPayload,
    PaginatedResidentRead,
    ResidentCreate,
    ResidentDetailRead,
    ResidentLotSummary,
    ResidentRead,
    ResidentUpdate,
    ResidentUserSummary,
)
from app.services.resident_service import ResidentService
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

router = APIRouter()


def assert_admin_or_director(current_user: User) -> None:
    if current_user.role not in (UserRole.ADMINISTRATOR, UserRole.DIRECTOR):
        raise ForbiddenError("Only Administrators and Directors can perform this action")


def _to_detail_read(resident) -> ResidentDetailRead:
    user_summary = None
    if resident.user:
        user_summary = ResidentUserSummary(
            id=resident.user.id,
            full_name=resident.user.full_name,
            email=resident.user.email,
            role=resident.user.role,
        )

    lot_summary = None
    if resident.lot:
        lot_summary = ResidentLotSummary(
            id=resident.lot.id,
            block=resident.lot.block,
            lot_number=resident.lot.lot_number,
        )

    return ResidentDetailRead(
        id=resident.id,
        lot_id=resident.lot_id,
        user_id=resident.user_id,
        full_name=resident.full_name,
        cpf=resident.cpf,
        rg=resident.rg,
        birth_date=resident.birth_date,
        phone=resident.phone,
        email=resident.email,
        relationship_type=resident.relationship_type,
        is_active=resident.is_active,
        notes=resident.notes,
        created_at=resident.created_at,
        updated_at=resident.updated_at,
        user=user_summary,
        lot=lot_summary,
    )


@router.get(
    "/lots/{lot_id}/residents",
    response_model=PaginatedResidentRead,
    status_code=status.HTTP_200_OK,
)
def list_residents_by_lot(
    lot_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> PaginatedResidentRead:
    residents, total = ResidentService.get_residents_by_lot(
        session, lot_id, current_user, skip, limit
    )
    items = [_to_detail_read(r) for r in residents]
    return PaginatedResidentRead(items=items, total=total, skip=skip, limit=limit)


@router.post(
    "/lots/{lot_id}/residents",
    response_model=ResidentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_resident(
    lot_id: UUID,
    resident_in: ResidentCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> ResidentRead:
    assert_admin_or_director(current_user)
    resident = ResidentService.create_resident(session, lot_id, resident_in)
    return ResidentRead.model_validate(resident)


@router.get(
    "/residents/{resident_id}",
    response_model=ResidentDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_resident(
    resident_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> ResidentDetailRead:
    resident = ResidentService.get_resident_by_id(session, resident_id, current_user)
    return _to_detail_read(resident)


@router.put(
    "/residents/{resident_id}",
    response_model=ResidentRead,
    status_code=status.HTTP_200_OK,
)
def update_resident(
    resident_id: UUID,
    resident_in: ResidentUpdate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> ResidentRead:
    assert_admin_or_director(current_user)
    resident = ResidentService.get_resident_by_id(session, resident_id, current_user)
    updated = ResidentService.update_resident(
        session, resident, resident_in, current_user
    )
    return ResidentRead.model_validate(updated)


@router.delete(
    "/residents/{resident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_resident(
    resident_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> None:
    assert_admin_or_director(current_user)
    resident = ResidentService.get_resident_by_id(session, resident_id, current_user)
    ResidentService.deactivate_resident(session, resident)


@router.post(
    "/residents/{resident_id}/link-user",
    response_model=ResidentRead,
    status_code=status.HTTP_200_OK,
)
def link_user_account(
    resident_id: UUID,
    payload: LinkUserPayload,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> ResidentRead:
    assert_admin_or_director(current_user)
    linked = ResidentService.link_user(session, resident_id, payload.user_id)
    return ResidentRead.model_validate(linked)


@router.post(
    "/residents/{resident_id}/unlink-user",
    response_model=ResidentRead,
    status_code=status.HTTP_200_OK,
)
def unlink_user_account(
    resident_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> ResidentRead:
    assert_admin_or_director(current_user)
    unlinked = ResidentService.unlink_user(session, resident_id)
    return ResidentRead.model_validate(unlinked)
