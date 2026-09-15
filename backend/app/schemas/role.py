"""Role schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.permissions import PERMISSIONS


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


class RoleCreate(BaseModel):
    """Schema for creating a new role."""

    name: str
    permissions: list[str] = []

    _check_permissions = field_validator("permissions")(_validate_permissions)


class RoleRead(BaseModel):
    """Schema for reading role data."""

    id: UUID
    name: str
    permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    """Schema for updating an existing role."""

    name: str
    # Optional with a `None` sentinel, unlike `name`, and the asymmetry is
    # deliberate: `update_role` overwrites unconditionally, so a plain
    # `list[str] = []` would silently wipe a role's bundle on every save from
    # a client that does not send the field.
    permissions: list[str] | None = None

    _check_permissions = field_validator("permissions")(_validate_permissions)
