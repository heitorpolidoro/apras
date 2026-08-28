"""Schemas for ReservableSpace and SpaceReservation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ReservationStatus


class ReservableSpaceBase(BaseModel):
    """Base fields shared by ReservableSpace create/read schemas."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    requires_approval: bool = False


class ReservableSpaceCreate(ReservableSpaceBase):
    """Schema for creating a new reservable space."""


class ReservableSpaceUpdate(BaseModel):
    """Schema for updating an existing reservable space. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    requires_approval: bool | None = None
    is_active: bool | None = None


class ReservableSpaceRead(ReservableSpaceBase):
    """Schema for reading a reservable space."""

    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpaceReservationCreate(BaseModel):
    """Schema for creating a new space reservation."""

    space_id: UUID
    lot_id: UUID | None = None
    start_time: datetime
    end_time: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_time_window(self) -> "SpaceReservationCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class SpaceReservationRead(BaseModel):
    """Schema for reading a space reservation (subject to viewer masking)."""

    id: UUID
    space_id: UUID
    space_name: str | None = None
    reserved_by_id: UUID | None = None
    reserved_by_name: str | None = None
    lot_id: UUID | None = None
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    notes: str | None = None
    decided_by_id: UUID | None = None
    decided_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpaceReservationDecision(BaseModel):
    """Body for the approve/reject endpoint.

    No fields needed today (kept as an empty model, not a bare 204, so a
    future rejection-reason field -- mirroring MediaAsset's
    rejection_reason -- can be added without a breaking route change).
    """
