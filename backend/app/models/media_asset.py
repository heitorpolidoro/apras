import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.core import clock
from app.models.enums import EntityType, PhotoApprovalStatus, StorageProvider
from app.models.tenant import tenant_id_field

if TYPE_CHECKING:
    from app.models.user import User


class MediaAsset(SQLModel, table=True):
    """SQLModel table representing stored photo/media assets."""

    __tablename__ = "media_asset"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Tenant boundary (APRAS-41). Defaults to DEFAULT_TENANT_ID so ORM
    # inserts that omit it keep working; APRAS-42 replaces this with a
    # request-scoped acting tenant.
    tenant_id: uuid.UUID = tenant_id_field()
    entity_type: EntityType = Field(index=True, nullable=False)
    entity_id: uuid.UUID | None = Field(default=None, index=True, nullable=True)
    storage_provider: StorageProvider = Field(
        default=StorageProvider.LOCAL_DISK, nullable=False
    )
    file_path: str = Field(nullable=False)
    url: str = Field(nullable=False)
    thumbnail_url: str | None = Field(default=None, nullable=True)
    file_size_bytes: int = Field(nullable=False)
    mime_type: str = Field(nullable=False)
    width: int | None = Field(default=None, nullable=True)
    height: int | None = Field(default=None, nullable=True)
    status: PhotoApprovalStatus = Field(
        default=PhotoApprovalStatus.PENDING_APPROVAL, index=True, nullable=False
    )
    rejection_reason: str | None = Field(default=None, nullable=True)

    uploaded_by_id: uuid.UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    approved_by_id: uuid.UUID | None = Field(
        foreign_key="user.id", ondelete="SET NULL", nullable=True
    )

    created_at: datetime = Field(default_factory=clock.db_now, nullable=False)
    updated_at: datetime = Field(default_factory=clock.db_now, nullable=False)
    approved_at: datetime | None = Field(default=None, nullable=True)

    uploaded_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MediaAsset.uploaded_by_id]"}
    )
    approved_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MediaAsset.approved_by_id]"}
    )
