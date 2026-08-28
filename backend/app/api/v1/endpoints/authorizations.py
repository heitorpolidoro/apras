"""API endpoints for Visitor pre-authorization management."""

import io
import json
from typing import Annotated
from uuid import UUID

import qrcode
from fastapi import APIRouter, Depends, Response, status
from sqlmodel import Session

from app.api import deps
from app.models.enums import AuthorizationStatus, DayOfWeek, ShiftType
from app.models.user import User
from app.models.visitor import VisitorAuthorization
from app.schemas.visitor import (
    PaginatedAuthorizationRead,
    VisitorAuthorizationCreate,
    VisitorAuthorizationRead,
    VisitorAuthorizationRevoke,
    VisitorRead,
)
from app.services.visitor_service import VisitorService

router = APIRouter()


def _to_authorization_read(auth: VisitorAuthorization) -> VisitorAuthorizationRead:
    days = [DayOfWeek(d) for d in json.loads(auth.allowed_days_json)] if auth.allowed_days_json else []
    shifts = [ShiftType(s) for s in json.loads(auth.allowed_shifts_json)] if auth.allowed_shifts_json else []
    visitor_read = VisitorRead.model_validate(auth.visitor) if auth.visitor else None
    return VisitorAuthorizationRead(
        id=auth.id,
        visitor_id=auth.visitor_id,
        lot_id=auth.lot_id,
        authorizer_user_id=auth.authorizer_user_id,
        auth_type=auth.auth_type,
        allowed_days_json=auth.allowed_days_json,
        allowed_shifts_json=auth.allowed_shifts_json,
        allowed_days=days,
        allowed_shifts=shifts,
        valid_from=auth.valid_from,
        valid_until=auth.valid_until,
        status=auth.status,
        notes=auth.notes,
        created_at=auth.created_at,
        updated_at=auth.updated_at,
        visitor=visitor_read,
    )


@router.get(
    "/lots/{lot_id}/authorizations",
    response_model=PaginatedAuthorizationRead,
    status_code=status.HTTP_200_OK,
)
def list_lot_authorizations(
    lot_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    status_filter: AuthorizationStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> PaginatedAuthorizationRead:
    """List visitor pre-authorizations for a specific lot."""
    auths, total = VisitorService.get_lot_authorizations(
        session, lot_id, current_user, skip=skip, limit=limit, status=status_filter
    )
    items = [_to_authorization_read(a) for a in auths]
    return PaginatedAuthorizationRead(items=items, total=total, skip=skip, limit=limit)


@router.post(
    "/lots/{lot_id}/authorizations",
    response_model=VisitorAuthorizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_lot_authorization(
    lot_id: UUID,
    auth_in: VisitorAuthorizationCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> VisitorAuthorizationRead:
    """Create a visitor pre-authorization for a lot."""
    auth = VisitorService.create_authorization(session, lot_id, auth_in, current_user)
    return _to_authorization_read(auth)


@router.put(
    "/authorizations/{auth_id}/revoke",
    response_model=VisitorAuthorizationRead,
    status_code=status.HTTP_200_OK,
)
def revoke_authorization(
    auth_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    payload: VisitorAuthorizationRevoke | None = None,
) -> VisitorAuthorizationRead:
    """Revoke an active pre-authorization immediately."""
    auth = VisitorService.revoke_authorization(session, auth_id, current_user)
    return _to_authorization_read(auth)


@router.get(
    "/authorizations/{authorization_id}",
    response_model=VisitorAuthorizationRead,
    status_code=status.HTTP_200_OK,
)
def get_authorization(
    authorization_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> VisitorAuthorizationRead:
    """Fetch a single visitor pre-authorization by ID.

    No extra *role* check beyond authentication (matches this module's
    convention), but the requester must still have lot access, same as
    every other route here (`_check_lot_access`) -- otherwise any
    authenticated user could pull another lot's visitor PII by guessing
    an authorization UUID.
    """
    auth = VisitorService.get_authorization_for_user(session, authorization_id, current_user)
    return _to_authorization_read(auth)


@router.get(
    "/authorizations/{authorization_id}/qr-code",
    status_code=status.HTTP_200_OK,
)
def get_authorization_qr_code(
    authorization_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Response:
    """Return a PNG QR code encoding the authorization's ID.

    Same lot-scoping rule as `get_authorization` above -- the QR image embeds
    visitor PII by reference, so it must not be fetchable for a lot the
    requester has no relationship to.
    """
    auth = VisitorService.get_authorization_for_user(session, authorization_id, current_user)
    image = qrcode.make(str(auth.id))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
