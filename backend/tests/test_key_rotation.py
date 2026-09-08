from datetime import timedelta

import jwt
from fastapi.testclient import TestClient

from app.core import clock
from app.core.config import settings


def test_key_rotation_support(client: TestClient, admin_user):
    # 1. Create a token using an "old" key
    old_key = "test_rotation_key"
    settings.SECRET_KEYS = [old_key]

    now = clock.db_now()
    expire = now + timedelta(minutes=30)
    to_encode = {"exp": expire, "sub": str(admin_user.id), "iat": now}
    token = jwt.encode(to_encode, old_key, algorithm=settings.ALGORITHM)

    # 2. Try to access an endpoint with this token
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )

    # Should be successful because old_key is in settings.SECRET_KEYS
    assert response.status_code == 200

    # 3. Try with an invalid key
    invalid_token = jwt.encode(to_encode, "wrong-key", algorithm=settings.ALGORITHM)
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert response.status_code == 403
