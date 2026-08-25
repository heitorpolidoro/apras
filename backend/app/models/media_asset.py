import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import EntityType, StorageProvider, PhotoApprovalStatus

if TYPE_CHECKING:
    from app.models.user import User


class MediaAsset(SQLModel, table=True):
    """SQLModel table representing stored photo/media assets."""

    __tablename__ = "media_asset"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entity_type: EntityType = Field(index=True, nullable=False)
    entity_id: Optional[uuid.UUID] = Field(default=None, index=True, nullable=True)
    storage_provider: StorageProvider = Field(default=StorageProvider.LOCAL_DISK, nullable=False)
    file_path: str = Field(nullable=False)
    url: str = Field(nullable=False)
    thumbnail_url: Optional[str] = Field(default=None, nullable=True)
    file_size_bytes: int = Field(nullable=False)
    mime_type: str = Field(nullable=False)
    width: Optional[int] = Field(default=None, nullable=True)
    height: Optional[int] = Field(default=None, nullable=True)
    status: PhotoApprovalStatus = Field(default=PhotoApprovalStatus.PENDING_APPROVAL, index=True, nullable=False)
    rejection_reason: Optional[str] = Field(default=None, nullable=True)

    uploaded_by_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    approved_by_id: Optional[uuid.UUID] = Field(foreign_key="user.id", ondelete="SET NULL", nullable=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    approved_at: Optional[datetime] = Field(default=None, nullable=True)

    uploaded_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MediaAsset.uploaded_by_id]"}
    )
    approved_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MediaAsset.approved_by_id]"}
    )
