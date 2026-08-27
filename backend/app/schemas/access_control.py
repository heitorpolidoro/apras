"""Pydantic schemas for AccessDevice, FacialTemplate, and FacialAccessEvent."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AccessDeviceStatus, FacialTemplateSyncStatus


class AccessDeviceCreate(BaseModel):
    name: str
    location: str | None = None


class AccessDeviceStatusUpdate(BaseModel):
    status: AccessDeviceStatus


class AccessDeviceRead(BaseModel):
    id: UUID
    name: str
    location: str | None = None
    status: AccessDeviceStatus
    last_seen_at: datetime | None = None
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccessDeviceKeyRead(AccessDeviceRead):
    """Extends AccessDeviceRead to expose the secret key exactly once (create/regenerate)."""

    device_key: str


class PaginatedAccessDeviceRead(BaseModel):
    items: list[AccessDeviceRead]
    total: int


class FacialTemplateRead(BaseModel):
    id: UUID
    resident_id: UUID
    media_asset_id: UUID
    sync_status: FacialTemplateSyncStatus
    synced_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FacialVerificationWebhookIn(BaseModel):
    resident_id: UUID | None = None
    confidence_score: float | None = None


class FacialAccessEventRead(BaseModel):
    id: UUID
    device_id: UUID
    resident_id: UUID | None = None
    matched: bool
    confidence_score: float | None = None
    access_granted: bool
    event_time: datetime
    raw_payload: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedFacialAccessEventRead(BaseModel):
    items: list[FacialAccessEventRead]
    total: int
    skip: int
    limit: int
