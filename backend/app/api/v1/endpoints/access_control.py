"""API endpoints for Access Control devices, facial template sync, and verification webhook."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlmodel import Session

from app.api import deps
from app.models.access_control import AccessDevice, FacialAccessEvent, FacialTemplate
from app.models.user import User
from app.schemas.access_control import (
    AccessDeviceCreate,
    AccessDeviceKeyRead,
    AccessDeviceRead,
    AccessDeviceStatusUpdate,
    FacialAccessEventRead,
    FacialTemplateRead,
    FacialVerificationWebhookIn,
    PaginatedAccessDeviceRead,
    PaginatedFacialAccessEventRead,
)
from app.services.access_control_service import AccessControlService

router = APIRouter()


def _to_device_key_read(device: AccessDevice) -> AccessDeviceKeyRead:
    return AccessDeviceKeyRead(
        id=device.id,
        name=device.name,
        location=device.location,
        status=device.status,
        last_seen_at=device.last_seen_at,
        created_by_id=device.created_by_id,
        created_at=device.created_at,
        updated_at=device.updated_at,
        device_key=device.device_key,
    )


def _to_event_read(event: FacialAccessEvent) -> FacialAccessEventRead:
    return FacialAccessEventRead.model_validate(event)


@router.post(
    "/devices",
    response_model=AccessDeviceKeyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_device(
    device_in: AccessDeviceCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AccessDeviceKeyRead:
    """Register a new access-control device (Admin/Director only)."""
    device = AccessControlService.create_device(session, device_in, current_user)
    return _to_device_key_read(device)


@router.get(
    "/devices",
    response_model=PaginatedAccessDeviceRead,
    status_code=status.HTTP_200_OK,
)
def list_devices(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PaginatedAccessDeviceRead:
    """List all access-control devices (Admin/Director/Manager)."""
    devices = AccessControlService.list_devices(session, current_user)
    items = [AccessDeviceRead.model_validate(d) for d in devices]
    return PaginatedAccessDeviceRead(items=items, total=len(items))


@router.put(
    "/devices/{device_id}/status",
    response_model=AccessDeviceRead,
    status_code=status.HTTP_200_OK,
)
def update_device_status(
    device_id: UUID,
    status_in: AccessDeviceStatusUpdate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AccessDeviceRead:
    """Manually update a device's status (Admin/Director only)."""
    device = AccessControlService.update_device_status(session, device_id, status_in, current_user)
    return AccessDeviceRead.model_validate(device)


@router.post(
    "/devices/{device_id}/regenerate-key",
    response_model=AccessDeviceKeyRead,
    status_code=status.HTTP_200_OK,
)
def regenerate_device_key(
    device_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> AccessDeviceKeyRead:
    """Rotate a device's secret key (Admin/Director only)."""
    device = AccessControlService.regenerate_device_key(session, device_id, current_user)
    return _to_device_key_read(device)


@router.post(
    "/residents/{resident_id}/facial-template/sync",
    response_model=FacialTemplateRead,
    status_code=status.HTTP_200_OK,
)
def sync_facial_template(
    resident_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> FacialTemplateRead:
    """Trigger a (simulated) facial template sync from the resident's approved photo."""
    template = AccessControlService.sync_facial_template(session, resident_id, current_user)
    return FacialTemplateRead.model_validate(template)


@router.get(
    "/residents/{resident_id}/facial-template",
    response_model=FacialTemplateRead | None,
    status_code=status.HTTP_200_OK,
)
def get_facial_template(
    resident_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> FacialTemplateRead | None:
    """Get the current facial template sync status for a resident."""
    template: FacialTemplate | None = AccessControlService.get_facial_template(session, resident_id, current_user)
    return FacialTemplateRead.model_validate(template) if template else None


@router.post(
    "/webhook/verification",
    response_model=FacialAccessEventRead,
    status_code=status.HTTP_201_CREATED,
)
def facial_verification_webhook(
    payload: FacialVerificationWebhookIn,
    session: Annotated[Session, Depends(deps.get_session)],
    x_device_key: Annotated[str | None, Header()] = None,
) -> FacialAccessEventRead:
    """Ingest a facial-recognition verification event from a physical device.

    Authenticated via the `X-Device-Key` header (not a user JWT), since physical
    devices cannot obtain a user session token.
    """
    event = AccessControlService.process_verification_webhook(session, x_device_key, payload)
    return _to_event_read(event)


@router.get(
    "/events",
    response_model=PaginatedFacialAccessEventRead,
    status_code=status.HTTP_200_OK,
)
def list_events(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    device_id: UUID | None = None,
    resident_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> PaginatedFacialAccessEventRead:
    """List facial access events, most recent first (Admin/Director/Manager only)."""
    events, total = AccessControlService.list_events(
        session, current_user, device_id=device_id, resident_id=resident_id, skip=skip, limit=limit
    )
    items = [_to_event_read(e) for e in events]
    return PaginatedFacialAccessEventRead(items=items, total=total, skip=skip, limit=limit)
