"""Pydantic schemas for Visitor, VisitorAuthorization, and AccessLog management."""

import json
from datetime import datetime
import re
from typing import List, Optional
from uuid import UUID

from app.models.enums import AuthorizationStatus, AuthorizationType, DayOfWeek, ShiftType
from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class VisitorBase(BaseModel):
    full_name: str
    cpf: str | None = None
    rg: str | None = None
    phone: str | None = None
    company_name: str | None = None
    vehicle_plate: str | None = None
    vehicle_model: str | None = None
    notes: str | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str | None) -> str | None:
        if not v:
            return None
        digits = re.sub(r"\D", "", v)
        if not digits:
            return None
        if len(digits) != 11:
            raise ValueError("CPF must have exactly 11 digits")
        if not _validate_cpf_digits(digits):
            raise ValueError("Invalid CPF")
        return digits


class VisitorCreate(VisitorBase):
    pass


class VisitorUpdate(BaseModel):
    full_name: str | None = None
    cpf: str | None = None
    rg: str | None = None
    phone: str | None = None
    company_name: str | None = None
    vehicle_plate: str | None = None
    vehicle_model: str | None = None
    notes: str | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str | None) -> str | None:
        if v is None:
            return None
        digits = re.sub(r"\D", "", v)
        if not digits:
            return None
        if len(digits) != 11:
            raise ValueError("CPF must have exactly 11 digits")
        if not _validate_cpf_digits(digits):
            raise ValueError("Invalid CPF")
        return digits


class VisitorRead(VisitorBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedVisitorRead(BaseModel):
    items: list[VisitorRead]
    total: int
    skip: int
    limit: int


class VisitorAuthorizationCreate(BaseModel):
    visitor_id: UUID
    auth_type: AuthorizationType = AuthorizationType.SINGLE
    allowed_days: list[DayOfWeek] = Field(
        default_factory=lambda: [
            DayOfWeek.MON,
            DayOfWeek.TUE,
            DayOfWeek.WED,
            DayOfWeek.THU,
            DayOfWeek.FRI,
            DayOfWeek.SAT,
            DayOfWeek.SUN,
        ]
    )
    allowed_shifts: list[ShiftType] = Field(
        default_factory=lambda: [
            ShiftType.MORNING,
            ShiftType.AFTERNOON,
            ShiftType.NIGHT,
            ShiftType.FULL_DAY,
        ]
    )
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    notes: str | None = None


class VisitorAuthorizationRead(BaseModel):
    id: UUID
    visitor_id: UUID
    lot_id: UUID
    authorizer_user_id: UUID
    auth_type: AuthorizationType
    allowed_days_json: str
    allowed_shifts_json: str
    allowed_days: list[DayOfWeek] = Field(default_factory=list)
    allowed_shifts: list[ShiftType] = Field(default_factory=list)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: AuthorizationStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    visitor: VisitorRead | None = None

    model_config = ConfigDict(from_attributes=True)


class VisitorAuthorizationRevoke(BaseModel):
    reason: str | None = None


class PaginatedAuthorizationRead(BaseModel):
    items: list[VisitorAuthorizationRead]
    total: int
    skip: int
    limit: int


class AccessLogCheckIn(BaseModel):
    visitor_id: UUID
    lot_id: UUID
    authorization_id: UUID | None = None
    entry_notes: str | None = None


class AccessLogCheckOut(BaseModel):
    access_log_id: UUID | None = None
    visitor_id: UUID | None = None
    exit_notes: str | None = None


class AccessLogRead(BaseModel):
    id: UUID
    authorization_id: UUID | None = None
    visitor_id: UUID
    lot_id: UUID
    entry_time: datetime
    exit_time: datetime | None = None
    gatekeeper_user_id: UUID | None = None
    entry_notes: str | None = None
    exit_notes: str | None = None
    visitor: VisitorRead | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedAccessLogRead(BaseModel):
    items: list[AccessLogRead]
    total: int
    skip: int
    limit: int
