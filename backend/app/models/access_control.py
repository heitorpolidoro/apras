"""Database models for AccessDevice, FacialTemplate, and FacialAccessEvent."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from .enums import AccessDeviceStatus, FacialTemplateSyncStatus

if TYPE_CHECKING:
    from .media_asset import MediaAsset
    from .resident import Resident
    from .user import User


class AccessDevice(SQLModel, table=True):
    """Registry of physical facial-recognition access-control devices."""

    __tablename__ = "access_device"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False, unique=True, index=True)
    location: str | None = Field(default=None)
    device_key: str = Field(nullable=False, unique=True, index=True)
    status: AccessDeviceStatus = Field(default=AccessDeviceStatus.OFFLINE, nullable=False, index=True)
    last_seen_at: datetime | None = Field(default=None)
    created_by_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    created_by: Optional["User"] = Relationship()
    events: list["FacialAccessEvent"] = Relationship(back_populates="device")


class FacialTemplate(SQLModel, table=True):
    """Sync record linking a Resident to their active biometric enrollment photo."""

    __tablename__ = "facial_template"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    resident_id: UUID = Field(
        foreign_key="resident.id", ondelete="CASCADE", nullable=False, unique=True, index=True
    )
    media_asset_id: UUID = Field(foreign_key="media_asset.id", ondelete="CASCADE", nullable=False)
    sync_status: FacialTemplateSyncStatus = Field(
        default=FacialTemplateSyncStatus.PENDING, nullable=False, index=True
    )
    synced_at: datetime | None = Field(default=None)
    failure_reason: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    resident: Optional["Resident"] = Relationship()
    media_asset: Optional["MediaAsset"] = Relationship()


class FacialAccessEvent(SQLModel, table=True):
    """Immutable log of verification attempts reported by an access device."""

    __tablename__ = "facial_access_event"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: UUID = Field(
        foreign_key="access_device.id", ondelete="CASCADE", nullable=False, index=True
    )
    resident_id: UUID | None = Field(
        default=None, foreign_key="resident.id", ondelete="SET NULL", nullable=True, index=True
    )
    matched: bool = Field(default=False, nullable=False)
    confidence_score: float | None = Field(default=None)
    access_granted: bool = Field(default=False, nullable=False)
    event_time: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    raw_payload: str | None = Field(default=None)

    # Relationships
    device: Optional["AccessDevice"] = Relationship(back_populates="events")
    resident: Optional["Resident"] = Relationship()
