"""Security utilities for password hashing and JWT tokens."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_token_expiration(remember_me: bool = False) -> timedelta:
    """
    Get the expiration timedelta based on remember_me flag.

    Args:
        remember_me: If True, returns 7 days, otherwise uses default from settings.

    Returns:
        timedelta: The expiration time delta.
    """
    if remember_me:
        return timedelta(days=7)
    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject of the token (usually user ID).
        expires_delta: Optional expiration time delta.

    Returns:
        str: Encoded JWT token.
    """
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "iat": now}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password.
        hashed_password: The hashed password.

    Returns:
        bool: True if password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def create_password_reset_token(email: str) -> str:
    """Create a short-lived JWT token for password reset."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": str(email), "iat": now, "scope": "password-reset"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> str | None:
    """Verify the password reset token and return the email if valid."""
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if decoded_token.get("scope") != "password-reset":
            return None
        return decoded_token.get("sub")
    except jwt.PyJWTError:
        return None
