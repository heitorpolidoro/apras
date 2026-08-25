import io
import uuid
import pytest
from PIL import Image
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import get_password_hash, create_access_token
from app.models.enums import UserRole
from app.models.user import User


def create_test_image_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def resident_user1(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="resident1@test.com",
        full_name="Resident One",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="22233344455",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_user2(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="resident2@test.com",
        full_name="Resident Two",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="33344455566",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_token1(resident_user1: User) -> str:
    return create_access_token(subject=str(resident_user1.id))


@pytest.fixture
def resident_token2(resident_user2: User) -> str:
    return create_access_token(subject=str(resident_user2.id))


def test_unauthenticated_requests_rejected(client: TestClient):
    """Test unauthenticated endpoints return 401 Unauthorized."""
    fake_id = uuid.uuid4()
    assert client.get("/api/v1/uploads/photos/pending").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.put(f"/api/v1/uploads/photos/{fake_id}/approve").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.put(f"/api/v1/uploads/photos/{fake_id}/reject", json={"rejection_reason": "test"}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.delete(f"/api/v1/uploads/photos/{fake_id}").status_code == status.HTTP_401_UNAUTHORIZED


def test_resident_cannot_access_pending_queue(client: TestClient, resident_token1: str):
    """Test RESIDENT user cannot access pending photos queue (403 Forbidden)."""
    headers = {"Authorization": f"Bearer {resident_token1}"}
    response = client.get("/api/v1/uploads/photos/pending", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_resident_cannot_approve_or_reject_photo(client: TestClient, resident_token1: str, resident_token2: str):
    """Test RESIDENT user cannot approve or reject photos."""
    headers1 = {"Authorization": f"Bearer {resident_token1}"}
    headers2 = {"Authorization": f"Bearer {resident_token2}"}

    image_bytes = create_test_image_bytes()
    files = {"file": ("test.jpg", image_bytes, "image/jpeg")}
    data = {"entity_type": "RESIDENT"}
    upload_res = client.post("/api/v1/uploads/photo", headers=headers1, files=files, data=data)
    photo_id = upload_res.json()["id"]

    approve_res = client.put(f"/api/v1/uploads/photos/{photo_id}/approve", headers=headers2)
    assert approve_res.status_code == status.HTTP_403_FORBIDDEN

    reject_res = client.put(f"/api/v1/uploads/photos/{photo_id}/reject", headers=headers2, json={"rejection_reason": "Not allowed"})
    assert reject_res.status_code == status.HTTP_403_FORBIDDEN


def test_resident_cannot_delete_other_user_photo(client: TestClient, resident_token1: str, resident_token2: str):
    """Test RESIDENT user cannot delete photo uploaded by another user."""
    headers1 = {"Authorization": f"Bearer {resident_token1}"}
    headers2 = {"Authorization": f"Bearer {resident_token2}"}

    image_bytes = create_test_image_bytes()
    files = {"file": ("user1.jpg", image_bytes, "image/jpeg")}
    data = {"entity_type": "RESIDENT"}
    upload_res = client.post("/api/v1/uploads/photo", headers=headers1, files=files, data=data)
    photo_id = upload_res.json()["id"]

    del_res = client.delete(f"/api/v1/uploads/photos/{photo_id}", headers=headers2)
    assert del_res.status_code == status.HTTP_403_FORBIDDEN
