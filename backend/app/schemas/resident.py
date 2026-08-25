"""Pydantic schemas for Resident management."""

from datetime import date, datetime
import re
from uuid import UUID

from app.models.enums import ResidentRelationship, UserRole
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_cpf_digits(cpf_digits: str) -> bool:
    """Return True if the 11-digit CPF string passes the check-digit algorithm."""
    if len(cpf_digits) != 11 or not cpf_digits.isdigit():
        return False
    if len(set(cpf_digits)) == 1:
        return False
    total = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    d1 = 0 if (total % 11) < 2 else 11 - (total % 11)
    if d1 != int(cpf_digits[9]):
        return False
    total = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    d2 = 0 if (total % 11) < 2 else 11 - (total % 11)
    return d2 == int(cpf_digits[10])


class ResidentBase(BaseModel):
    full_name: str
    cpf: str
    rg: str | None = None
    birth_date: date | None = None
    phone: str | None = None
    email: str | None = None
    relationship_type: ResidentRelationship = ResidentRelationship.TITULAR
    notes: str | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("CPF must have exactly 11 digits")
        if not _validate_cpf_digits(digits):
            raise ValueError("Invalid CPF")
        return digits


class ResidentCreate(ResidentBase):
    pass


class ResidentUpdate(BaseModel):
    full_name: str | None = None
    cpf: str | None = None
    rg: str | None = None
    birth_date: date | None = None
    phone: str | None = None
    email: str | None = None
    relationship_type: ResidentRelationship | None = None
    is_active: bool | None = None
    notes: str | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("CPF must have exactly 11 digits")
        if not _validate_cpf_digits(digits):
            raise ValueError("Invalid CPF")
        return digits


class ResidentRead(ResidentBase):
    id: UUID
    lot_id: UUID
    user_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResidentUserSummary(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class ResidentLotSummary(BaseModel):
    id: UUID
    block: str
    lot_number: str

    model_config = ConfigDict(from_attributes=True)


class ResidentDetailRead(ResidentRead):
    user: ResidentUserSummary | None = None
    lot: ResidentLotSummary | None = None


class LinkUserPayload(BaseModel):
    user_id: UUID


class PaginatedResidentRead(BaseModel):
    items: list[ResidentRead]
    total: int
    skip: int
    limit: int
