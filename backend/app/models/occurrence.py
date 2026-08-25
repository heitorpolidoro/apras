"""Occurrence and OccurrenceTimeline SQLModel entity definitions."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import OccurrenceCategory, OccurrencePriority, OccurrenceStatus

if TYPE_CHECKING:
    from app.models.lot import Lot
    from app.models.user import User


class Occurrence(SQLModel, table=True):
    """SQLModel representing an occurrence ticket."""

    __tablename__ = "occurrence"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    protocol_number: str = Field(index=True, unique=True, nullable=False)
    lot_id: UUID | None = Field(
        default=None, foreign_key="lot.id", ondelete="SET NULL", nullable=True, index=True
    )
    reporter_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True
    )
    is_anonymous: bool = Field(default=False, nullable=False)
    is_public: bool = Field(default=False, nullable=False)
    category: OccurrenceCategory = Field(nullable=False, index=True)
    title: str = Field(nullable=False)
    description: str = Field(nullable=False)
    photo_urls_json: str | None = Field(default=None, nullable=True)
    status: OccurrenceStatus = Field(
        default=OccurrenceStatus.OPEN, nullable=False, index=True
    )
    priority: OccurrencePriority = Field(
        default=OccurrencePriority.MEDIUM, nullable=False, index=True
    )
    assigned_to_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True
    )
    resolution_notes: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    resolved_at: datetime | None = Field(default=None, nullable=True)

    # Relationships
    lot: Optional["Lot"] = Relationship()
    reporter: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Occurrence.reporter_user_id]"}
    )
    assigned_to: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Occurrence.assigned_to_id]"}
    )
    timeline_entries: list["OccurrenceTimeline"] = Relationship(
        back_populates="occurrence",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class OccurrenceTimeline(SQLModel, table=True):
    """SQLModel representing audit/timeline events for an occurrence."""

    __tablename__ = "occurrence_timeline"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    occurrence_id: UUID = Field(
        foreign_key="occurrence.id", ondelete="CASCADE", nullable=False, index=True
    )
    actor_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    status_from: OccurrenceStatus | None = Field(default=None, nullable=True)
    status_to: OccurrenceStatus | None = Field(default=None, nullable=True)
    note: str = Field(nullable=False)
    is_internal_only: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    occurrence: "Occurrence" = Relationship(back_populates="timeline_entries")
    actor: "User" = Relationship()
