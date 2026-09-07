"""Role schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.permissions import PERMISSIONS

#: The in-app paths a role may pin its members to (IAM F5, APRAS-49 §8.1).
#:
#: An allowlist and not an open string, and that is a **security** property
#: rather than a nicety: `RootRedirect` and `ProtectedRoute` navigate to this
#: value, so an arbitrary string would be an open redirect the moment the
#: frontend consumes it. Adding a path here is a reviewable decision.
LANDING_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/dashboard",
        "/tasks",
        "/gate",
        "/welcome",
        "/announcements",
        "/occurrences",
    }
)


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


def _validate_landing_path(value: str | None) -> str | None:
    """Reject any landing path outside `LANDING_PATHS`."""
    if value is None:
        return None
    if value not in LANDING_PATHS:
        allowed = ", ".join(sorted(LANDING_PATHS))
        raise ValueError(f"Unknown landing_path: {value}; allowed: {allowed}")
    return value


class RoleCreate(BaseModel):
    """Schema for creating a new role."""

    name: str
    permissions: list[str] = []
    landing_path: str | None = None

    _check_permissions = field_validator("permissions")(_validate_permissions)
    _check_landing_path = field_validator("landing_path")(_validate_landing_path)


class RoleRead(BaseModel):
    """Schema for reading role data."""

    id: UUID
    name: str
    permissions: list[str] = []
    landing_path: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    """Schema for updating an existing role."""

    name: str
    # Optional with a `None` sentinel, unlike `name`, and the asymmetry is
    # deliberate: `update_role` overwrites unconditionally, so a plain
    # `list[str] = []` would silently wipe a role's bundle on every save from
    # a client that does not send the field.
    permissions: list[str] | None = None
    # `None` here means "clear the landing preference", not "field absent",
    # so this one cannot use the sentinel above. `update_role` reads
    # `model_fields_set` instead, and an omitted field is a no-op.
    landing_path: str | None = None

    _check_permissions = field_validator("permissions")(_validate_permissions)
    _check_landing_path = field_validator("landing_path")(_validate_landing_path)
