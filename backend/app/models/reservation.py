"""Database models for ReservableSpace and SpaceReservation."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ReservationStatus

if TYPE_CHECKING:
    from app.models.lot import Lot
    from app.models.user import User


class ReservableSpace(SQLModel, table=True):
    """Admin-managed definition of a bookable shared amenity."""

    __tablename__ = "reservable_space"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, nullable=False)
    description: str | None = Field(default=None)
    capacity: int | None = Field(default=None)
    requires_approval: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    reservations: list["SpaceReservation"] = Relationship(back_populates="space")


class SpaceReservation(SQLModel, table=True):
    """A resident/staff booking of a ReservableSpace for a specific time window."""

    __tablename__ = "space_reservation"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    space_id: UUID = Field(
        foreign_key="reservable_space.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    reserved_by_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    lot_id: UUID | None = Field(
        default=None,
        foreign_key="lot.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    start_time: datetime = Field(nullable=False, index=True)
    end_time: datetime = Field(nullable=False)
    status: ReservationStatus = Field(
        default=ReservationStatus.PENDING, nullable=False, index=True
    )
    notes: str | None = Field(default=None)
    decided_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    decided_at: datetime | None = Field(default=None)
    cancelled_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    space: "ReservableSpace" = Relationship(back_populates="reservations")
    reserved_by: "User" = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[SpaceReservation.reserved_by_id]"
        }
    )
    decided_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[SpaceReservation.decided_by_id]"
        }
    )
    lot: Optional["Lot"] = Relationship()
