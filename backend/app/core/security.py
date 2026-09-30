"""Security utilities for password hashing and JWT tokens."""

from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from app.core import clock
from app.core.config import settings
from app.core.password_policy import BCRYPT_MAX_PASSWORD_BYTES

# The production bcrypt cost factor, and the floor below which it must never
# go (APRAS-108). 12 was passlib's default too, so making it explicit changed
# nothing operationally -- it gives the floor a single addressable name.
#
# It is deliberately *not* configurable: no `Settings` field, no environment
# read. A cost of 4 in production is a severe but silent defect -- every hash
# still verifies, no endpoint changes behaviour, nothing logs -- so the only way
# to lower it is to edit this line, which is a reviewable diff that
# `tests/test_bcrypt_cost.py` fails on. Declaring a `BCRYPT_ROUNDS` settings
# field is precisely what would create a deploy-time weakening route, because
# `Settings` ignores undeclared environment rows today.
#
# The test suite does not touch this constant. `tests/conftest.py` lowers the
# *hasher* instead, which affects only the test process.
BCRYPT_ROUNDS = 12

# `BCRYPT_MAX_PASSWORD_BYTES` is bcrypt's 72-byte key schedule, imported from
# `app.core.password_policy` so the schema layer and this module share one
# number. What is ours is what happens to a longer secret: bcrypt 4 truncated it
# in silence, which made two passwords differing only after byte 72 the same
# password -- both hashed alike, both verified -- and bcrypt 5 raises
# `ValueError` instead. Neither is acceptable at an API boundary, so
# `app/schemas/user.validate_password_strength` rejects an over-long password as
# a 422 before any hash is computed, and the methods below refuse to truncate if
# one ever reaches them anyway.


class BcryptHasher:
    """The one password hasher: bcrypt, at the cost this object carries.

    It replaces the passlib context this module used to build. passlib 1.7.4 is
    that project's last release, dated 2020-10-08, and it cannot drive bcrypt 5
    at all: at first use it probes its bcrypt backend for a historical
    implementation bug by hashing a deliberately over-long secret, which bcrypt 4
    truncated and bcrypt 5 rejects, and it reads a version attribute bcrypt 5 no
    longer defines. Both are inside passlib, so no call-site change avoids them,
    and passlib is unmaintained.

    The cost is a plain mutable attribute on purpose. `tests/conftest.py` lowers
    *this object's* cost to 4 for the test process, as it previously lowered the
    passlib context in place: every
    `from app.core.security import password_hasher` alias is the same object, so
    one assignment reaches all of them, including hashes computed during
    collection and inside session-scoped fixtures. bcrypt stores its cost inside
    the hash, so production hashes made at 12 still verify under a 4 hasher.

    There is deliberately no `needs_update` and no `verify_and_update`. passlib's
    `deprecated="auto"` gave the old context both, and under a cost-4 hasher they
    call a stored cost-12 hash stale -- so a single caller plus one production
    misconfiguration would have silently *downgraded* real users' stored hashes
    at login. Having no such method is a stronger guarantee than having no caller
    for one.
    """

    def __init__(self, rounds: int) -> None:
        self.rounds = rounds

    def hash(self, password: str) -> str:
        """Hash `password` at this hasher's cost.

        Raises:
            ValueError: if the password exceeds bcrypt's 72-byte limit. Raising
                is the point: silently hashing the first 72 bytes would store a
                credential the user did not choose.
        """
        secret = self._secret_bytes(password)
        salt = bcrypt.gensalt(rounds=self.rounds)
        return bcrypt.hashpw(secret, salt).decode("ascii")

    def verify(self, password: str, hashed_password: str) -> bool:
        """Return True if `password` is the secret behind `hashed_password`.

        An over-long candidate is False, never an exception and never a truncated
        comparison. `hash` refuses to create such a credential, so no hash this
        class made can correspond to one; comparing the first 72 bytes instead
        would mean two passwords differing only after byte 72 both authenticate,
        which is the bcrypt-4 collision this change exists to end.
        """
        try:
            secret = self._secret_bytes(password)
        except ValueError:
            return False
        return bcrypt.checkpw(secret, hashed_password.encode("utf-8"))

    @staticmethod
    def _secret_bytes(password: str) -> bytes:
        """UTF-8 encode `password` and hold it to bcrypt's byte limit.

        The limit is on *bytes*, not characters, which is why no character-count
        check can stand in for this one: 72 accented Latin-1 characters are 144
        UTF-8 bytes.
        """
        secret = password.encode("utf-8")
        if len(secret) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(
                f"password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes"
            )
        return secret


#: The process-wide hasher. Mutated in place by `tests/conftest.py`, never
#: rebound, so imported aliases cannot diverge from it.
password_hasher = BcryptHasher(rounds=BCRYPT_ROUNDS)


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
    now = clock.utc_now()
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
        plain_password: The plain text password. A candidate longer than
            `BCRYPT_MAX_PASSWORD_BYTES` is False, not an error: the login form
            is unbounded input and `POST /auth/login` must answer 400, never
            500.
        hashed_password: The hashed password.

    Returns:
        bool: True if password matches, False otherwise.
    """
    return password_hasher.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password, at most
            `BCRYPT_MAX_PASSWORD_BYTES` bytes. Every request-borne caller
            reaches this through a schema that has already rejected a longer
            one.

    Returns:
        str: The hashed password.

    Raises:
        ValueError: if the password is longer than bcrypt can hash.
    """
    return password_hasher.hash(password)


def create_password_reset_token(email: str) -> str:
    """Create a short-lived JWT token for password reset."""
    now = clock.utc_now()
    expire = now + timedelta(minutes=15)
    to_encode = {
        "exp": expire,
        "sub": str(email),
        "iat": now,
        "scope": "password-reset",
    }
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
