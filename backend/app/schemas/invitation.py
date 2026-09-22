"""Schemas for the administrator invitation (APRAS-71).

No schema here ever carries `token_hash`, and no **response** schema ever
carries a raw token: the raw value leaves the service exactly once, to the
mail sender, and is never persisted, logged to a column or serialised into a
body.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.user import normalize_cpf, validate_password_strength


class InvitationCreate(BaseModel):
    """What a superuser posts to invite an administrator.

    `full_name` is the courtesy greeting of the mail only: it is not stored,
    because the name the invitee types when accepting is the one that ends
    up on their account.
    """

    tenant_id: UUID
    email: EmailStr
    full_name: str | None = None


class InvitationRead(BaseModel):
    """One invitation as the superuser routes return it.

    Derived state, never a stored `status` column: `accepted_at` is the
    single-use marker and `expires_at` is the deadline.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: str
    expires_at: datetime
    accepted_at: datetime | None
    accepted_user_id: UUID | None
    invited_by_user_id: UUID
    created_at: datetime


class InvitationPreviewRequest(BaseModel):
    """The token, in a **body** and never in a URL (D5).

    A token in a path or a query string lands in access logs, in `Referer`
    headers and in browser history, which is why both public routes are
    `POST` -- the preview included, despite being a read.
    """

    token: str


class InvitationPreview(BaseModel):
    """What the invitee is shown before accepting, and the D8 accept answer.

    It carries **no credential of any kind**. `account_exists` lets the
    acceptance page drop the password field for an address that already has
    an account.
    """

    email: str
    tenant_name: str
    tenant_slug: str
    invited_by_name: str
    expires_at: datetime
    account_exists: bool


class InvitationAcceptRequest(BaseModel):
    """The acceptance body. Carries the same token, in the same place.

    When present, `cpf` and `password` are held to exactly the rules
    `UserCreate` enforces -- the check digits and the normalisation to 11
    digits, the 8-character floor with a letter, a digit and a symbol -- so
    this path cannot mint an account signup would refuse.

    `full_name`, `cpf` and `password` are required for a new account and are
    **ignored** when the address already has one (D8): silently resetting an
    existing account's password from an invitation somebody else issued is
    an account-takeover path, so they are optional here and the branch that
    ignores them says so. Missing them in the new-account branch is a 422
    from `InvitationService`, never a schema-level rejection that would
    break the branch that does not need them.
    """

    token: str
    full_name: str | None = None
    cpf: str | None = None
    password: str | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str | None) -> str | None:
        """`UserCreate`'s rule, reused, and `None` left alone.

        Reused rather than restated: the normalisation to 11 digits is what
        makes D9's duplicate-CPF `409` fire at all, since signup stores
        digits and an equality lookup against a typed `529.982.247-25` would
        simply miss.
        """
        return None if v is None else normalize_cpf(v)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str | None) -> str | None:
        """`UserCreate`'s rule, reused, and `None` left alone."""
        return None if v is None else validate_password_strength(v)
