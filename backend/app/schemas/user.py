"""User schemas for Pydantic validation."""

import re
from uuid import UUID

from app.schemas.tenant import TenantMembershipSummary
from app.schemas.role import RoleRead
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
    phone: str | None = None
    address: str | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
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
    cpf: str
    roles: list[RoleRead] = []

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def username(self) -> str:
        return self.email.split("@")[0]


class UserMeRead(UserRead):
    """``GET /api/v1/auth/me`` only: identity plus the caller's own memberships.

    An additive subclass on purpose, so ``UserRead`` — the response model of
    ``/users/``, ``/auth/signup``, ``/auth/dev-users`` and every admin user
    route — stays untouched and the membership graph is not exposed through
    the user directory (APRAS-38 §3.3).

    ``is_superuser`` is the caller's **own** flag on the caller's **own**
    record (IAM F5, APRAS-49 §8.3). ``UserRead`` still does not carry it:
    telling every authenticated caller of ``GET /users/`` who the superusers
    are is a leak, which is also why §8.4 ships no UI for the grant.
    ``context/tenantState.ts`` is the one consumer — it runs before an acting
    tenant exists and so cannot ask ``/permissions/me``.
    """

    is_superuser: bool = False
    tenants: list[TenantMembershipSummary] = []


class UserContactInfoUpdate(BaseModel):
    """Contact-info-only update schema, used by the Administrator/Manager
    contact-info endpoint. Deliberately has no role/is_active/role_ids/
    full_name/cpf fields so those cannot be set through this schema."""

    phone: str | None = None
    address: str | None = None


class UserUpdate(BaseModel):
    """The admin update surface.

    It carries **no** `role` and **no** `is_superuser` (IAM F5, APRAS-49
    §8.3): `role_ids` is the only field that can widen a target's
    permissions, and `role_service.assert_can_assign_roles` already guards
    it. The global flag has its own superuser-only route (§8.4), so it can
    never ride in on this payload.
    """

    is_active: bool | None = None
    role_ids: list[UUID] | None = None
    full_name: str | None = None
    cpf: str | None = None
    phone: str | None = None
    address: str | None = None

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


class SuperuserUpdate(BaseModel):
    """Body of ``PATCH /api/v1/users/{user_id}/superuser`` (§8.4).

    One field, deliberately its own schema, so the global flag never rides on
    ``UserUpdate`` again.
    """

    is_superuser: bool


class SuperuserRead(BaseModel):
    """Response of the superuser route -- deliberately **not** ``UserRead``.

    It confirms what the caller just wrote without making ``UserRead`` carry
    the flag for every reader of ``GET /users/`` (§8.3).
    """

    id: UUID
    email: EmailStr
    is_superuser: bool

    model_config = ConfigDict(from_attributes=True)
