"""User schemas for Pydantic validation."""

import re
from uuid import UUID

from app.models.enums import UserRole
from app.schemas.user_type import UserTypeRead
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, computed_field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.DIRECTOR


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
    type: UserTypeRead | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def username(self) -> str:
        return self.email.split("@")[0]


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    type_id: UUID | None = None
    full_name: str | None = None
