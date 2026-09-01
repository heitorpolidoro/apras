"""UserType schemas."""

from uuid import UUID

from app.core.permissions import PERMISSIONS
from app.models.enums import MenuKey, UserRole
from pydantic import BaseModel, ConfigDict, field_validator


def _validate_permissions(values: list[str] | None) -> list[str] | None:
    """Reject any string that is not in the catalogue (APRAS-46 §9.1).

    Write-side only. `deps.get_effective_permissions` deliberately keeps
    tolerating unknown strings already stored in a row: a hand-edited row
    must stay visible, not vanish.
    """
    if values is None:
        return None
    unknown = sorted(set(values) - PERMISSIONS)
    if unknown:
        raise ValueError("Unknown permissions: " + ", ".join(unknown))
    return values


class UserTypeCreate(BaseModel):
    """Schema for creating a new user type."""

    name: str
    allowed_menus: list[MenuKey] = []
    permissions: list[str] = []

    _check_permissions = field_validator("permissions")(_validate_permissions)


class UserTypeRead(BaseModel):
    """Schema for reading user type data."""

    id: UUID
    name: str
    allowed_menus: list[MenuKey] = []
    # Set only for the 5 role-linked types seeded by the APRAS-9 migration;
    # None for regular admin-created types. Read-only: never settable via
    # UserTypeCreate/UserTypeUpdate.
    role: UserRole | None = None
    permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class UserTypeUpdate(BaseModel):
    """Schema for updating an existing user type."""

    name: str
    allowed_menus: list[MenuKey] = []
    # Optional with a `None` sentinel, unlike its two siblings, and the
    # asymmetry is deliberate: `update_user_type` overwrites `allowed_menus`
    # unconditionally, so a plain `list[str] = []` would silently wipe a
    # group's bundle on every save from the current frontend, which does not
    # send the field until IAM F4.
    permissions: list[str] | None = None

    _check_permissions = field_validator("permissions")(_validate_permissions)
