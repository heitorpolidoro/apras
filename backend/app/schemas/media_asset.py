import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.models.enums import EntityType, StorageProvider, PhotoApprovalStatus


class MediaAssetRead(BaseModel):
    """Schema for reading media asset metadata."""

    id: uuid.UUID
    entity_type: EntityType
    entity_id: Optional[uuid.UUID] = None
    storage_provider: StorageProvider
    file_path: str
    url: str
    thumbnail_url: Optional[str] = None
    file_size_bytes: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    status: PhotoApprovalStatus
    rejection_reason: Optional[str] = None
    uploaded_by_id: uuid.UUID
    uploaded_by_name: Optional[str] = None
    approved_by_id: Optional[uuid.UUID] = None
    approved_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PhotoRejectRequest(BaseModel):
    """Request schema for rejecting a photo asset."""

    rejection_reason: str


class MediaAssetListResponse(BaseModel):
    """Response schema for paginated/filtered media asset lists."""

    items: List[MediaAssetRead]
    total: int
    pending_count: int
