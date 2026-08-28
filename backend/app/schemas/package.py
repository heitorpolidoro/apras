"""Pydantic schemas for Package (encomendas) tracking."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import PackageStatus


class PackageCreate(BaseModel):
    """Schema for logging a new package's arrival."""

    lot_id: UUID
    description: str | None = None
    carrier: str | None = None


class PackagePickup(BaseModel):
    """Schema for marking a package as picked up."""

    picked_up_by_notes: str | None = None


class LotSummaryRead(BaseModel):
    """Minimal lot identification used to group/link packages by lot."""

    id: UUID
    block: str
    lot_number: str

    model_config = ConfigDict(from_attributes=True)


class PackageRead(BaseModel):
    """Schema for reading package details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lot_id: UUID
    lot_summary: LotSummaryRead | None = None
    received_by_id: UUID | None = None
    received_by_name: str | None = None
    description: str | None = None
    carrier: str | None = None
    received_at: datetime
    status: PackageStatus
    picked_up_at: datetime | None = None
    picked_up_by_id: UUID | None = None
    picked_up_by_name: str | None = None
    picked_up_by_notes: str | None = None


class PaginatedPackageRead(BaseModel):
    """Schema for paginated package listings."""

    items: list[PackageRead]
    total: int
    skip: int
    limit: int
