"""Tenant schemas for Pydantic validation (APRAS-41)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class TenantBase(BaseModel):
    """Base tenant schema with common fields."""

    name: str = Field(..., min_length=1, max_length=120)


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""

    is_active: bool = True


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant. All fields are optional.

    There is no ``DELETE /api/v1/tenants/{id}``: every tenant-scoped foreign
    key is ``ondelete="RESTRICT"``, and deactivation (``is_active: false``)
    is the intended operation.
    """

    name: str | None = Field(None, min_length=1, max_length=120)
    is_active: bool | None = None


class TenantRead(TenantBase):
    """Schema for reading tenant data."""

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantMemberCreate(BaseModel):
    """Schema for linking an existing user to a tenant."""

    user_id: UUID


class TenantMemberRead(BaseModel):
    """Schema for reading one membership, flattened with the user's details."""

    user_id: UUID
    email: str
    full_name: str
    role: UserRole
    linked_at: datetime

    model_config = ConfigDict(from_attributes=True)
