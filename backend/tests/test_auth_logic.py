import uuid

import jwt

from app.core import security
from app.core.config import settings


def test_password_hashing():
    password = "secret_password"
    hashed = security.get_password_hash(password)
    assert hashed != password
    assert security.verify_password(password, hashed) is True
    assert security.verify_password("wrong_password", hashed) is False


def test_create_access_token():
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert "exp" in payload


def test_password_reset_tokens():
    email = "user@test.com"
    token = security.create_password_reset_token(email)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == email
    assert payload["scope"] == "password-reset"
    
    verified_email = security.verify_password_reset_token(token)
    assert verified_email == email
    
    invalid_verified = security.verify_password_reset_token("invalid_token")
    assert invalid_verified is None
