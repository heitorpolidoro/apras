"""Pydantic schemas for Lot and UserLotLink."""

from datetime import datetime
from uuid import UUID

from app.models.enums import LotAssociationType, LotStatus, UserRole
from pydantic import BaseModel, ConfigDict, Field


class UserSummaryRead(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class LotBase(BaseModel):
    block: str = Field(..., min_length=1)
    lot_number: str = Field(..., min_length=1)
    address: str | None = None
    postal_code: str | None = None
    area_sqm: float | None = None
    fraction_ideal: float | None = None
    status: LotStatus = LotStatus.VACANT
    notes: str | None = None


class LotCreate(LotBase):
    pass


class LotUpdate(BaseModel):
    block: str | None = None
    lot_number: str | None = None
    address: str | None = None
    postal_code: str | None = None
    area_sqm: float | None = None
    fraction_ideal: float | None = None
    status: LotStatus | None = None
    notes: str | None = None


class LotRead(LotBase):
    id: UUID
    is_deleted: bool
    is_delinquent: bool = False
    delinquency_updated_at: datetime | None = None
    delinquency_updated_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LotDelinquencyUpdate(BaseModel):
    """Body of ``PATCH /lots/{id}/delinquency``.

    Dedicated endpoint rather than a field on the generic lot update: this
    flag is what suspends the lot's assembly voting right (APRAS-33).
    """

    is_delinquent: bool


class UserLotLinkCreate(BaseModel):
    user_id: UUID
    association_type: LotAssociationType = LotAssociationType.PROPRIETARIO
    is_primary: bool = False
    start_date: datetime | None = None
    end_date: datetime | None = None


class UserLotLinkRead(BaseModel):
    id: UUID
    user_id: UUID
    lot_id: UUID
    association_type: LotAssociationType
    is_primary: bool
    start_date: datetime | None = None
    end_date: datetime | None = None
    created_at: datetime
    user: UserSummaryRead

    model_config = ConfigDict(from_attributes=True)


class LotDetailRead(LotRead):
    users: list[UserLotLinkRead] = []


class PaginatedLotRead(BaseModel):
    items: list[LotRead]
    total: int
    skip: int
    limit: int
