"""API endpoints for Gatekeeper check-in/check-out and Access Logs timeline."""

from typing import Annotated
from uuid import UUID

from app.api import deps
from app.core.exceptions import ForbiddenError
from app.models.enums import UserRole
from app.models.user import User
from app.models.visitor import AccessLog
from app.schemas.visitor import (
    AccessLogCheckIn,
    AccessLogCheckOut,
    AccessLogRead,
    PaginatedAccessLogRead,
    VisitorRead,
)
from app.services.visitor_service import VisitorService
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

router = APIRouter()


def _assert_gatekeeper_or_admin(current_user: User) -> None:
    if current_user.role not in (
        UserRole.ADMINISTRATOR,
        UserRole.DIRECTOR,
        UserRole.MANAGER,
    ):
        raise ForbiddenError("Only gatekeepers and administrators can perform check-in or check-out")


def _to_access_log_read(log: AccessLog) -> AccessLogRead:
    visitor_read = VisitorRead.model_validate(log.visitor) if log.visitor else None
    return AccessLogRead(
        id=log.id,
        authorization_id=log.authorization_id,
        visitor_id=log.visitor_id,
        lot_id=log.lot_id,
        entry_time=log.entry_time,
        exit_time=log.exit_time,
        gatekeeper_user_id=log.gatekeeper_user_id,
        entry_notes=log.entry_notes,
        exit_notes=log.exit_notes,
        visitor=visitor_read,
    )


@router.post(
    "/check-in",
    response_model=AccessLogRead,
    status_code=status.HTTP_201_CREATED,
)
def check_in_visitor(
    check_in_in: AccessLogCheckIn,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AccessLogRead:
    """Register visitor entry at gate."""
    _assert_gatekeeper_or_admin(current_user)
    log = VisitorService.check_in(session, check_in_in, current_user)
    return _to_access_log_read(log)


@router.post(
    "/check-out",
    response_model=AccessLogRead,
    status_code=status.HTTP_200_OK,
)
def check_out_visitor(
    check_out_in: AccessLogCheckOut,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AccessLogRead:
    """Register visitor exit at gate."""
    _assert_gatekeeper_or_admin(current_user)
    log = VisitorService.check_out(session, check_out_in, current_user)
    return _to_access_log_read(log)


@router.get(
    "",
    response_model=PaginatedAccessLogRead,
    status_code=status.HTTP_200_OK,
)
def list_access_logs(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    lot_id: UUID | None = None,
    visitor_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> PaginatedAccessLogRead:
    """Query access log timeline history."""
    logs, total = VisitorService.get_access_logs(
        session,
        current_user,
        lot_id=lot_id,
        visitor_id=visitor_id,
        skip=skip,
        limit=limit,
    )
    items = [_to_access_log_read(l) for l in logs]
    return PaginatedAccessLogRead(items=items, total=total, skip=skip, limit=limit)
