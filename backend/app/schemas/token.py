"""Token schemas for authentication."""

from pydantic import BaseModel, Field, field_validator

from app.core.password_policy import BCRYPT_MAX_PASSWORD_BYTES
from app.schemas.user import PASSWORD_MIN_LENGTH, validate_password_strength


class Token(BaseModel):
    """Schema for OAuth2 access token response."""

    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Schema for JWT token payload content."""

    sub: str | None = None


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting a password reset link."""

    email: str


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password using a token.

    `new_password` is held to `UserCreate`'s rule, not to a copy of it and no
    longer to nothing at all. This body used to declare a bare `str`, so
    `POST /auth/reset-password` was the one path that hashed a password the
    signup rule had never seen: it accepted a password too weak to register
    with, and -- once bcrypt 5 stopped truncating -- an over-long one would
    have reached `get_password_hash` and returned 500.
    """

    token: str
    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=BCRYPT_MAX_PASSWORD_BYTES,
    )

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """`UserCreate`'s rule, reused."""
        return validate_password_strength(v)
