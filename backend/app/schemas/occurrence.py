"""Pydantic schemas for Occurrence data transfer objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OccurrenceCategory, OccurrencePriority, OccurrenceStatus


class OccurrenceCreate(BaseModel):
    """Schema for creating a new occurrence."""

    lot_id: UUID | None = None
    is_anonymous: bool = False
    is_public: bool = False
    category: OccurrenceCategory
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    photo_urls: list[str] | None = None


class OccurrenceStatusUpdate(BaseModel):
    """Schema for updating occurrence status, priority, assignment, or resolution."""

    status: OccurrenceStatus | None = None
    priority: OccurrencePriority | None = None
    assigned_to_id: UUID | None = None
    resolution_notes: str | None = None


class TimelineNoteCreate(BaseModel):
    """Schema for appending a timeline note or status transition log."""

    note: str = Field(min_length=1)
    is_internal_only: bool = False
    status_to: OccurrenceStatus | None = None


class OccurrenceTimelineRead(BaseModel):
    """Schema for reading timeline log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    occurrence_id: UUID
    actor_id: UUID
    actor_name: str | None = None
    status_from: OccurrenceStatus | None = None
    status_to: OccurrenceStatus | None = None
    note: str
    is_internal_only: bool
    created_at: datetime


class OccurrenceRead(BaseModel):
    """Schema for reading basic occurrence details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    protocol_number: str
    lot_id: UUID | None = None
    lot_summary: str | None = None
    reporter_user_id: UUID | None = None
    reporter_name: str | None = None
    is_anonymous: bool
    is_public: bool
    category: OccurrenceCategory
    title: str
    description: str
    photo_urls: list[str] = Field(default_factory=list)
    status: OccurrenceStatus
    priority: OccurrencePriority
    assigned_to_id: UUID | None = None
    assigned_to_name: str | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class OccurrenceDetailRead(OccurrenceRead):
    """Schema for reading full occurrence details with timeline history."""

    timeline: list[OccurrenceTimelineRead] = Field(default_factory=list)


class PaginatedOccurrenceRead(BaseModel):
    """Schema for paginated occurrence listings."""

    items: list[OccurrenceRead]
    total: int
    skip: int
    limit: int
