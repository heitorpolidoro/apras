import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EntityType, PhotoApprovalStatus, StorageProvider


class MediaAssetRead(BaseModel):
    """Schema for reading media asset metadata."""

    id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID | None = None
    storage_provider: StorageProvider
    file_path: str
    url: str
    thumbnail_url: str | None = None
    file_size_bytes: int
    mime_type: str
    width: int | None = None
    height: int | None = None
    status: PhotoApprovalStatus
    rejection_reason: str | None = None
    uploaded_by_id: uuid.UUID
    uploaded_by_name: str | None = None
    approved_by_id: uuid.UUID | None = None
    approved_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PhotoRejectRequest(BaseModel):
    """Request schema for rejecting a photo asset."""

    rejection_reason: str


class MediaAssetListResponse(BaseModel):
    """Response schema for paginated/filtered media asset lists."""

    items: list[MediaAssetRead]
    total: int
    pending_count: int
