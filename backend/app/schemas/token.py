"""Token schemas for authentication."""

from pydantic import BaseModel


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
    """Schema for resetting password using a token."""

    token: str
    new_password: str
