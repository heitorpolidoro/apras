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
    """Schema for linking an existing user to a tenant.

    ``is_tenant_admin`` is optional so a link and a grant can be one call
    (APRAS-43); it defaults to ``False``, i.e. a plain member.
    """

    user_id: UUID
    is_tenant_admin: bool = False


class TenantMemberUpdate(BaseModel):
    """Schema for granting/revoking the tenant_admin capability (APRAS-43).

    Exactly one field, on purpose: this route grants a capability and must
    never become a general membership editor.
    """

    is_tenant_admin: bool


class TenantMemberRead(BaseModel):
    """Schema for reading one membership, flattened with the user's details."""

    user_id: UUID
    email: str
    full_name: str
    role: UserRole
    linked_at: datetime
    is_tenant_admin: bool

    model_config = ConfigDict(from_attributes=True)
