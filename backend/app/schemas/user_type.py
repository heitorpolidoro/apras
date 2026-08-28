"""UserType schemas."""

from uuid import UUID

from app.models.enums import MenuKey, UserRole
from pydantic import BaseModel, ConfigDict


class UserTypeCreate(BaseModel):
    """Schema for creating a new user type."""

    name: str
    allowed_menus: list[MenuKey] = []


class UserTypeRead(BaseModel):
    """Schema for reading user type data."""

    id: UUID
    name: str
    allowed_menus: list[MenuKey] = []
    # Set only for the 5 role-linked types seeded by the APRAS-9 migration;
    # None for regular admin-created types. Read-only: never settable via
    # UserTypeCreate/UserTypeUpdate.
    role: UserRole | None = None

    model_config = ConfigDict(from_attributes=True)


class UserTypeUpdate(BaseModel):
    """Schema for updating an existing user type."""

    name: str
    allowed_menus: list[MenuKey] = []
