import io
import uuid
import pytest
from PIL import Image
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import get_password_hash, create_access_token
from app.models.enums import UserRole, EntityType, PhotoApprovalStatus
from app.models.user import User


def create_test_image_bytes(format: str = "JPEG", size: tuple[int, int] = (200, 200), color: str = "red") -> bytes:
    """Generate in-memory image bytes for testing."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture
def resident_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="resident@test.com",
        full_name="Resident User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="11122233344",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_token(resident_user: User) -> str:
    return create_access_token(subject=str(resident_user.id))


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(subject=str(admin_user.id))


def test_upload_photo_resident_pending(client: TestClient, resident_token: str):
    """Test photo upload by a RESIDENT user enters PENDING_APPROVAL status."""
    image_bytes = create_test_image_bytes(format="JPEG", size=(400, 400))
    headers = {"Authorization": f"Bearer {resident_token}"}
    files = {"file": ("test.jpg", image_bytes, "image/jpeg")}
    data = {"entity_type": "RESIDENT", "entity_id": str(uuid.uuid4())}

    response = client.post("/api/v1/uploads/photo", headers=headers, files=files, data=data)
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert body["mime_type"] == "image/jpeg"
    assert body["width"] == 400
    assert body["height"] == 400
    assert body["url"].startswith("/static/uploads/")
    assert body["thumbnail_url"].startswith("/static/uploads/")
    assert body["rejection_reason"] is None


def test_upload_photo_admin_auto_approved(client: TestClient, admin_token: str):
    """Test photo upload by an ADMINISTRATOR user auto-approves immediately."""
    image_bytes = create_test_image_bytes(format="PNG", size=(300, 300))
    headers = {"Authorization": f"Bearer {admin_token}"}
    files = {"file": ("test.png", image_bytes, "image/png")}
    data = {"entity_type": "VISITOR"}

    response = client.post("/api/v1/uploads/photo", headers=headers, files=files, data=data)
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["approved_by_id"] is not None
    assert body["approved_at"] is not None


def test_upload_photo_file_too_large(client: TestClient, resident_token: str):
    """Test photo upload exceeding 5MB returns 400 Bad Request."""
    large_bytes = b"0" * (5 * 1024 * 1024 + 1)
    headers = {"Authorization": f"Bearer {resident_token}"}
    files = {"file": ("large.jpg", large_bytes, "image/jpeg")}
    data = {"entity_type": "RESIDENT"}

    response = client.post("/api/v1/uploads/photo", headers=headers, files=files, data=data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "excede o limite" in response.json()["detail"]


def test_upload_photo_invalid_format(client: TestClient, resident_token: str):
    """Test uploading non-image file returns 400 Bad Request."""
    invalid_bytes = b"Hello world text file payload"
    headers = {"Authorization": f"Bearer {resident_token}"}
    files = {"file": ("test.txt", invalid_bytes, "text/plain")}
    data = {"entity_type": "RESIDENT"}

    response = client.post("/api/v1/uploads/photo", headers=headers, files=files, data=data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Formato de imagem inválido" in response.json()["detail"]


def test_list_pending_photos_and_approval_workflow(client: TestClient, resident_token: str, admin_token: str):
    """Test listing pending photos, approving a photo, and rejecting a photo."""
    # 1. Resident uploads photo
    image_bytes = create_test_image_bytes()
    headers_res = {"Authorization": f"Bearer {resident_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    files = {"file": ("pending.jpg", image_bytes, "image/jpeg")}
    data = {"entity_type": "RESIDENT"}
    res_upload = client.post("/api/v1/uploads/photo", headers=headers_res, files=files, data=data)
    assert res_upload.status_code == status.HTTP_201_CREATED
    photo_id = res_upload.json()["id"]

    # 2. Admin lists pending queue
    pending_res = client.get("/api/v1/uploads/photos/pending", headers=headers_admin)
    assert pending_res.status_code == status.HTTP_200_OK
    pending_body = pending_res.json()
    assert pending_body["total"] >= 1
    assert pending_body["pending_count"] >= 1
    item_ids = [item["id"] for item in pending_body["items"]]
    assert photo_id in item_ids

    # 3. Get metadata
    meta_res = client.get(f"/api/v1/uploads/photos/{photo_id}", headers=headers_res)
    assert meta_res.status_code == status.HTTP_200_OK
    assert meta_res.json()["id"] == photo_id

    # 4. Admin approves photo
    approve_res = client.put(f"/api/v1/uploads/photos/{photo_id}/approve", headers=headers_admin)
    assert approve_res.status_code == status.HTTP_200_OK
    assert approve_res.json()["status"] == "APPROVED"
    assert approve_res.json()["approved_by_id"] is not None

    # 5. Resident uploads another photo to reject
    files2 = {"file": ("reject.jpg", image_bytes, "image/jpeg")}
    res_upload2 = client.post("/api/v1/uploads/photo", headers=headers_res, files=files2, data=data)
    photo_id2 = res_upload2.json()["id"]

    # Reject without reason -> 400
    reject_bad = client.put(f"/api/v1/uploads/photos/{photo_id2}/reject", headers=headers_admin, json={"rejection_reason": ""})
    assert reject_bad.status_code == status.HTTP_400_BAD_REQUEST

    # Reject with reason -> 200
    reject_res = client.put(f"/api/v1/uploads/photos/{photo_id2}/reject", headers=headers_admin, json={"rejection_reason": "Foto desfocada"})
    assert reject_res.status_code == status.HTTP_200_OK
    assert reject_res.json()["status"] == "REJECTED"
    assert reject_res.json()["rejection_reason"] == "Foto desfocada"


def test_delete_photo(client: TestClient, resident_token: str, admin_token: str):
    """Test photo deletion by uploader."""
    image_bytes = create_test_image_bytes()
    headers = {"Authorization": f"Bearer {resident_token}"}
    files = {"file": ("todelete.jpg", image_bytes, "image/jpeg")}
    data = {"entity_type": "RESIDENT"}

    res = client.post("/api/v1/uploads/photo", headers=headers, files=files, data=data)
    photo_id = res.json()["id"]

    del_res = client.delete(f"/api/v1/uploads/photos/{photo_id}", headers=headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/api/v1/uploads/photos/{photo_id}", headers=headers)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
