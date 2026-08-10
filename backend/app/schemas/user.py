"""User schemas for Pydantic validation."""

import re
from uuid import UUID

from app.models.enums import UserRole
from app.schemas.user_type import UserTypeRead
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, computed_field


def _validate_cpf_digits(cpf_digits: str) -> bool:
    """Return True if the 11-digit CPF string passes the check-digit algorithm."""
    if len(cpf_digits) != 11 or not cpf_digits.isdigit():
        return False
    # Reject all-same-digit CPFs
    if len(set(cpf_digits)) == 1:
        return False
    # First check digit
    total = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    d1 = 0 if (total % 11) < 2 else 11 - (total % 11)
    if d1 != int(cpf_digits[9]):
        return False
    # Second check digit
    total = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    d2 = 0 if (total % 11) < 2 else 11 - (total % 11)
    return d2 == int(cpf_digits[10])


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.DIRECTOR
    cpf: str

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("CPF must have exactly 11 digits")
        if not _validate_cpf_digits(digits):
            raise ValueError("Invalid CPF")
        return digits


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one symbol")
        return v


class UserRead(UserBase):
    id: UUID
    is_active: bool
    user_types: list[UserTypeRead] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def username(self) -> str:
        return self.email.split("@")[0]


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    user_type_ids: list[UUID] | None = None
    full_name: str | None = None
    cpf: str | None = None

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
