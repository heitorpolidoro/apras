import io
import uuid

import pytest
from fastapi import status
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app.api import deps
from app.core.permissions import ROUTE_PERMISSIONS
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.enums import EntityType
from app.models.user import User
from app.services import media_service as media_service_module
from tests.conftest import make_user


def create_test_image_bytes(format: str = "JPEG", size: tuple[int, int] = (200, 200), color: str = "red") -> bytes:
    """Generate in-memory image bytes for testing."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture
def resident_user(session: Session) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="resident@test.com",
        full_name="Resident User",
        hashed_password=get_password_hash("password123"),
        profile="RESIDENT",
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


#: The other half of this pin, named in every failure message below. Neither
#: side can import the other across the language boundary, so each states the
#: constant and points at the other -- the shape
#: `lotSelectContract.test.tsx` ↔
#: `test_infractions.py::test_the_lots_route_ceiling_matches_the_lot_selects_limit`
#: and `i18n/__tests__/index.test.ts` ↔ `test_module_vocabulary.py` already use.
_FRONTEND_CLIENT = "frontend/src/api/uploads.ts"
_FRONTEND_TWIN = (
    "frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx"
)


def _permission_guards(dependant: Dependant) -> list[deps.PermissionRequired]:
    """Every `PermissionRequired` mounted anywhere under `dependant`.

    Same seven lines as `test_permission_enforcement.py::_permission_guards`,
    local to this file rather than imported across test modules.
    """
    found = []
    if isinstance(dependant.call, deps.PermissionRequired):
        found.append(dependant.call)
    for sub in dependant.dependencies:
        found.extend(_permission_guards(sub))
    return found


def _upload_photo_route() -> APIRoute:
    """The live `POST /api/v1/uploads/photo`, read off `app.main.app`."""
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == "/api/v1/uploads/photo"
            and "POST" in route.methods
        ):
            return route
    pytest.fail(
        "POST /api/v1/uploads/photo is not mounted on app.main.app. "
        f"The infraction uploader ({_FRONTEND_CLIENT}) posts to it on every "
        "evidence and contestation attachment; if the route moved, move the "
        f"client and the literal in {_FRONTEND_TWIN} with it."
    )
    raise AssertionError  # pragma: no cover - pytest.fail never returns


def test_the_upload_contract_matches_the_infraction_uploader():
    """The backend half of the APRAS-53 two-sided pin.

    The infraction module's attachment control (`AttachmentUploader.tsx`)
    reuses this route through the existing client, and declares five facts
    about it as local literals -- 5 MiB, the three MIME types, the
    `INFRACTION` entity vocabulary, the route and the permission it demands.
    This case states the same five against the **live objects**, so changing
    the server without changing the client fails here, and changing the client
    without changing the server fails over there.
    """
    assert media_service_module.MAX_FILE_SIZE == 5 * 1024 * 1024, (
        "media_service.MAX_FILE_SIZE changed. "
        f"`UPLOAD_MAX_FILE_SIZE_BYTES` in {_FRONTEND_CLIENT} pre-checks file "
        "size against this number and `infractions.attachments.hint` "
        f"interpolates it; update both, and the literal in {_FRONTEND_TWIN}."
    )

    documented_mime_types = {"image/jpeg", "image/png", "image/webp"}
    assert documented_mime_types == media_service_module.ALLOWED_MIME_TYPES, (
        "media_service.ALLOWED_MIME_TYPES changed. "
        f"`UPLOAD_ALLOWED_MIME_TYPES` in {_FRONTEND_CLIENT} feeds the "
        "`accept=` of the infraction attachment input and its client-side "
        f"pre-check; update it, and the literal in {_FRONTEND_TWIN}."
    )

    assert EntityType.INFRACTION.value == "INFRACTION", (
        "EntityType.INFRACTION changed value. Both infraction forms send it as "
        f"`entity_type`; a value outside this enum is a FastAPI 422 before the "
        f"handler runs. Update `INFRACTION_ENTITY_TYPE` "
        f"(frontend AttachmentUploader.tsx) and the literal in {_FRONTEND_TWIN}."
    )

    assert (
        ROUTE_PERMISSIONS[("POST", "/api/v1/uploads/photo")]
        == "uploads:photo_create"
    ), (
        "ROUTE_PERMISSIONS for POST /api/v1/uploads/photo changed. "
        f"`UPLOAD_PHOTO_PERMISSION` in {_FRONTEND_CLIENT} is what the "
        "attachment control asks `usePermissionSet().has()` before rendering; "
        f"update it, and the literal in {_FRONTEND_TWIN}."
    )

    guards = [
        guard.permission for guard in _permission_guards(_upload_photo_route().dependant)
    ]
    assert "uploads:photo_create" in guards, (
        "POST /api/v1/uploads/photo no longer carries "
        "PermissionRequired('uploads:photo_create') in its dependency tree "
        f"(found: {guards}). APRAS-51 put it there and APRAS-53 gates the "
        "infraction attachment control on it: without the guard the client is "
        "stricter than the server and hides a control the route would accept. "
        f"Either restore the guard or drop the gate in {_FRONTEND_TWIN}."
    )
