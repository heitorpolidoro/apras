"""bcrypt's 72-byte ceiling, enforced at the boundary instead of by accident.

`app/schemas/user.py` declared ``password`` with a minimum and no maximum. Under
bcrypt 4 that was not an error, it was a silent one: bcrypt hashes only the first
72 bytes of a secret and bcrypt 4 discarded the rest without a word, so two
passwords differing only after byte 72 were the *same credential* -- they hashed
alike and each verified against the other's hash. Nobody could notice.

bcrypt 5 raises ``ValueError`` on the same input, which converts that silent
defect into a 500 on ``POST /auth/signup``, ``POST /auth/reset-password`` and the
invitation-accept path. Neither answer is acceptable, so the limit is now stated
at the schema boundary and the over-long password is a 422.

This module pins all three layers, from the inside out:

1. the hasher refuses to truncate, and ``verify`` answers False rather than
   raising, because ``POST /auth/login`` reads an unbounded form field;
2. every schema that carries a password rejects an over-long one, including the
   accented case that a *character* count would wave through;
3. the endpoints answer 422/400, never 500.
"""

import pytest
from app.core import security
from app.core.password_policy import BCRYPT_MAX_PASSWORD_BYTES
from app.models.user import User
from app.schemas.invitation import InvitationAcceptRequest
from app.schemas.token import ResetPasswordRequest
from app.schemas.user import UserCreate
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session

#: A valid password of exactly `BCRYPT_MAX_PASSWORD_BYTES` bytes: the limit is
#: inclusive, and a test that only proves rejection above it would also pass if
#: the boundary were off by one in the safe direction.
AT_LIMIT = "A1!" + "a" * (BCRYPT_MAX_PASSWORD_BYTES - 3)

#: One byte over, in ASCII, where bytes and characters coincide.
OVER_LIMIT = "A1!" + "a" * (BCRYPT_MAX_PASSWORD_BYTES - 2)

#: 44 characters, 84 UTF-8 bytes. `Field(max_length=...)` counts characters and
#: lets this through; only the byte check in `validate_password_strength` stops
#: it. It is the whole reason the rule is written on `encode("utf-8")`, and any
#: rewrite that drops the byte check still passes every ASCII case above.
OVER_LIMIT_ACCENTED = "á" * 40 + "1!Ab"

#: A CPF that passes the check digits, so a password rejection is the only thing
#: these payloads can be rejected for.
VALID_CPF = "52998224725"


def test_the_fixtures_are_the_lengths_this_module_claims() -> None:
    """Anchor for every case below: the sizes are what the names say.

    Without it, a typo that made `OVER_LIMIT` 72 bytes would turn each rejection
    test below into an assertion about nothing in particular.
    """
    assert len(AT_LIMIT.encode("utf-8")) == BCRYPT_MAX_PASSWORD_BYTES
    assert len(OVER_LIMIT.encode("utf-8")) == BCRYPT_MAX_PASSWORD_BYTES + 1
    assert len(OVER_LIMIT_ACCENTED) <= BCRYPT_MAX_PASSWORD_BYTES, (
        "the accented case must be short enough in *characters* to pass "
        "Field(max_length=...), or it does not exercise the byte rule at all"
    )
    assert len(OVER_LIMIT_ACCENTED.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES


# ---------------------------------------------------------------------------
# 1. the hasher
# ---------------------------------------------------------------------------


def test_a_password_at_the_limit_hashes_and_verifies() -> None:
    """Anchor: the limit is inclusive, so the refusals below are about length."""
    hashed = security.get_password_hash(AT_LIMIT)
    assert security.verify_password(AT_LIMIT, hashed) is True


def test_hashing_an_over_long_password_raises_rather_than_truncating() -> None:
    """Storing the first 72 bytes would store a credential nobody chose."""
    with pytest.raises(ValueError, match="72 bytes"):
        security.get_password_hash(OVER_LIMIT)
    with pytest.raises(ValueError, match="72 bytes"):
        security.get_password_hash(OVER_LIMIT_ACCENTED)


def test_verifying_an_over_long_password_is_false_not_an_exception() -> None:
    """``POST /auth/login`` reads an unbounded form field and must answer 400.

    bcrypt 5 raises on the same input, so a bare ``checkpw`` here would be a 500
    reachable by any unauthenticated caller willing to post a long string.
    """
    hashed = security.get_password_hash(AT_LIMIT)
    assert security.verify_password(OVER_LIMIT, hashed) is False
    assert security.verify_password(OVER_LIMIT_ACCENTED, hashed) is False


def test_the_bcrypt_4_truncation_collision_is_gone() -> None:
    """The defect itself: a longer password must not match its own 72-byte head.

    Under bcrypt 4 this assertion was False -- ``AT_LIMIT + "extra"`` hashed to,
    and verified against, exactly ``AT_LIMIT``'s hash. That is what made two
    different passwords one credential.
    """
    hashed = security.get_password_hash(AT_LIMIT)
    assert security.verify_password(AT_LIMIT, hashed) is True
    assert security.verify_password(AT_LIMIT + "extra", hashed) is False


# ---------------------------------------------------------------------------
# 2. the schemas -- all three bodies that carry a password
# ---------------------------------------------------------------------------


def _user_create(password: str) -> UserCreate:
    return UserCreate(
        email="length@example.com",
        full_name="Length Test",
        password=password,
        cpf=VALID_CPF,
    )


def test_user_create_accepts_the_limit_and_rejects_past_it() -> None:
    assert _user_create(AT_LIMIT).password == AT_LIMIT

    with pytest.raises(ValidationError, match="at most 72"):
        _user_create(OVER_LIMIT)
    with pytest.raises(ValidationError, match="at most 72 bytes"):
        _user_create(OVER_LIMIT_ACCENTED)


def test_the_ceiling_is_published_in_the_openapi_schema() -> None:
    """`Field(max_length=...)` must not be decorative either.

    It is deliberately redundant with the byte rule -- it counts characters, and
    a 72-byte string is at most 72 characters, so it can never reject anything
    the byte rule allows. What it does is put the ceiling in the generated
    OpenAPI document, which is what the frontend's own form validation reads
    from, so a client can refuse the password before a round trip.
    """
    for model in (UserCreate, ResetPasswordRequest):
        field = "password" if model is UserCreate else "new_password"
        properties = model.model_json_schema()["properties"]
        assert field in properties, f"{model.__name__} has no {field!r} property"
        assert properties[field]["maxLength"] == BCRYPT_MAX_PASSWORD_BYTES, (
            f"{model.__name__}.{field} must publish maxLength "
            f"{BCRYPT_MAX_PASSWORD_BYTES} in its JSON schema; got "
            f"{properties[field].get('maxLength')!r}."
        )


def test_reset_password_request_accepts_the_limit_and_rejects_past_it() -> None:
    """``ResetPasswordRequest`` used to declare a bare ``str``.

    It was the one body that hashed a password no rule had inspected, so it is
    also the one that would have turned an over-long password into a 500.
    """
    assert ResetPasswordRequest(token="t", new_password=AT_LIMIT).new_password == (
        AT_LIMIT
    )

    with pytest.raises(ValidationError, match="at most 72"):
        ResetPasswordRequest(token="t", new_password=OVER_LIMIT)
    with pytest.raises(ValidationError, match="at most 72 bytes"):
        ResetPasswordRequest(token="t", new_password=OVER_LIMIT_ACCENTED)


def test_reset_password_request_enforces_the_same_complexity_as_signup() -> None:
    """A reset that accepts a password signup refuses is a way around signup."""
    with pytest.raises(ValidationError, match="at least one number"):
        ResetPasswordRequest(token="t", new_password="no-digits-here!")
    with pytest.raises(ValidationError, match="at least one symbol"):
        ResetPasswordRequest(token="t", new_password="NoSymbols123")
    with pytest.raises(ValidationError, match="at least 8"):
        ResetPasswordRequest(token="t", new_password="A1!b")


def test_invitation_accept_accepts_the_limit_and_rejects_past_it() -> None:
    assert InvitationAcceptRequest(token="t", password=AT_LIMIT).password == AT_LIMIT
    # `None` still means "existing account, ignore these fields" (D8).
    assert InvitationAcceptRequest(token="t", password=None).password is None

    with pytest.raises(ValidationError, match="at most 72 bytes"):
        InvitationAcceptRequest(token="t", password=OVER_LIMIT)
    with pytest.raises(ValidationError, match="at most 72 bytes"):
        InvitationAcceptRequest(token="t", password=OVER_LIMIT_ACCENTED)


# ---------------------------------------------------------------------------
# 3. the endpoints -- 422/400, never 500
# ---------------------------------------------------------------------------


def test_signup_answers_422_for_an_over_long_password(client: TestClient) -> None:
    payload = {
        "email": "toolong@test.com",
        "full_name": "Too Long",
        "password": OVER_LIMIT_ACCENTED,
        "cpf": VALID_CPF,
    }
    # Anchor: the same payload with a legal password is accepted, so the 422
    # below is about the password and not about the email or the CPF.
    ok = client.post("/api/v1/auth/signup", json={**payload, "password": AT_LIMIT})
    assert ok.status_code == status.HTTP_200_OK, ok.text

    response = client.post(
        "/api/v1/auth/signup", json={**payload, "email": "toolong2@test.com"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text


def test_login_answers_400_for_an_over_long_password(
    client: TestClient, normal_user: User
) -> None:
    """Not a 500: the login form is unbounded and unauthenticated."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": normal_user.email, "password": OVER_LIMIT},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.text
    assert response.json()["detail"] == "Incorrect email or password"


def test_reset_password_answers_422_for_an_over_long_password(
    client: TestClient, session: Session, normal_user: User
) -> None:
    token = security.create_password_reset_token(normal_user.email)

    # Anchor: this token really does work, so the 422 is the password's fault.
    ok = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": AT_LIMIT},
    )
    assert ok.status_code == status.HTTP_200_OK, ok.text

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": OVER_LIMIT_ACCENTED},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text

    # And the earlier, legal reset is the password that is actually stored.
    session.refresh(normal_user)
    assert security.verify_password(AT_LIMIT, normal_user.hashed_password) is True
