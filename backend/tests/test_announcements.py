"""Unit and API integration tests for the Announcement Feed module."""

import io
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.announcement import AnnouncementReadReceipt
from app.models.enums import UserRole
from app.models.user import User
from app.services import announcement_service


def _make_image_bytes(color: str = "blue") -> bytes:
    img = Image.new("RGB", (100, 100), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def admin_headers(admin_user: User):
    token = create_access_token(subject=str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def director_headers(normal_user: User):
    token = create_access_token(subject=str(normal_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def resident_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="resident_ann@test.com",
        full_name="Resident Ann",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="93641136095",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_headers(resident_user: User):
    token = create_access_token(subject=str(resident_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def guest_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="guest_ann@test.com",
        full_name="Guest User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.GUEST,
        cpf="96214676037",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def guest_headers(guest_user: User):
    token = create_access_token(subject=str(guest_user.id))
    return {"Authorization": f"Bearer {token}"}


def _create_announcement(client: TestClient, headers: dict) -> dict:
    res = client.post(
        "/api/v1/announcements",
        json={"title": "Assembleia Geral", "content": "Reunião marcada para dia 10."},
        headers=headers,
    )
    assert res.status_code == status.HTTP_201_CREATED
    return res.json()


# ---------------------------------------------------------------------------
# CRUD + publisher RBAC
# ---------------------------------------------------------------------------


def test_create_announcement_publisher_only(client: TestClient, admin_headers, resident_headers):
    created = _create_announcement(client, admin_headers)
    assert created["title"] == "Assembleia Geral"
    assert created["media"] == []
    assert created["comment_count"] == 0
    assert created["is_read"] is False

    res_forbidden = client.post(
        "/api/v1/announcements",
        json={"title": "X", "content": "Y"},
        headers=resident_headers,
    )
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN


def test_update_and_delete_announcement_publisher_only(
    client: TestClient, admin_headers, director_headers, resident_headers
):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]

    res_forbidden = client.put(
        f"/api/v1/announcements/{ann_id}", json={"title": "Hacked"}, headers=resident_headers
    )
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

    res_update = client.put(
        f"/api/v1/announcements/{ann_id}",
        json={"title": "Assembleia Geral - Atualizado", "content": "Novo conteúdo"},
        headers=director_headers,
    )
    assert res_update.status_code == status.HTTP_200_OK
    assert res_update.json()["title"] == "Assembleia Geral - Atualizado"
    assert res_update.json()["content"] == "Novo conteúdo"

    res_del_forbidden = client.delete(f"/api/v1/announcements/{ann_id}", headers=resident_headers)
    assert res_del_forbidden.status_code == status.HTTP_403_FORBIDDEN

    res_del = client.delete(f"/api/v1/announcements/{ann_id}", headers=admin_headers)
    assert res_del.status_code == status.HTTP_204_NO_CONTENT

    # Soft-deleted: no longer retrievable
    res_get = client.get(f"/api/v1/announcements/{ann_id}", headers=admin_headers)
    assert res_get.status_code == status.HTTP_404_NOT_FOUND


def test_feed_excludes_soft_deleted_and_orders_newest_first(
    client: TestClient, admin_headers, session: Session
):
    first = _create_announcement(client, admin_headers)
    second = _create_announcement(client, admin_headers)
    client.delete(f"/api/v1/announcements/{first['id']}", headers=admin_headers)

    res = client.get("/api/v1/announcements", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    ids = [item["id"] for item in body["items"]]
    assert first["id"] not in ids
    assert second["id"] == ids[0]


# ---------------------------------------------------------------------------
# Media upload
# ---------------------------------------------------------------------------


def test_upload_media_image_and_pdf(client: TestClient, admin_headers):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]

    img_res = client.post(
        f"/api/v1/announcements/{ann_id}/media",
        headers=admin_headers,
        files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert img_res.status_code == status.HTTP_201_CREATED
    assert img_res.json()["media_type"] == "IMAGE"
    assert img_res.json()["order_index"] == 0

    pdf_res = client.post(
        f"/api/v1/announcements/{ann_id}/media",
        headers=admin_headers,
        files={"file": ("doc.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")},
    )
    assert pdf_res.status_code == status.HTTP_201_CREATED
    assert pdf_res.json()["media_type"] == "PDF"
    assert pdf_res.json()["order_index"] == 1

    detail = client.get(f"/api/v1/announcements/{ann_id}", headers=admin_headers).json()
    assert len(detail["media"]) == 2


def test_upload_media_rejects_invalid_mime_and_oversized(client: TestClient, admin_headers):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]

    bad_mime = client.post(
        f"/api/v1/announcements/{ann_id}/media",
        headers=admin_headers,
        files={"file": ("evil.exe", b"binary", "application/x-msdownload")},
    )
    assert bad_mime.status_code == status.HTTP_400_BAD_REQUEST

    oversized = client.post(
        f"/api/v1/announcements/{ann_id}/media",
        headers=admin_headers,
        files={"file": ("big.jpg", b"0" * (10 * 1024 * 1024 + 1), "image/jpeg")},
    )
    assert oversized.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_media_publisher_only(client: TestClient, admin_headers, resident_headers):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]

    res = client.post(
        f"/api/v1/announcements/{ann_id}/media",
        headers=resident_headers,
        files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_delete_media(client: TestClient, admin_headers, resident_headers):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]
    media = client.post(
        f"/api/v1/announcements/{ann_id}/media",
        headers=admin_headers,
        files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
    ).json()

    forbidden = client.delete(
        f"/api/v1/announcements/{ann_id}/media/{media['id']}", headers=resident_headers
    )
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN

    ok = client.delete(f"/api/v1/announcements/{ann_id}/media/{media['id']}", headers=admin_headers)
    assert ok.status_code == status.HTTP_204_NO_CONTENT

    missing = client.delete(
        f"/api/v1/announcements/{ann_id}/media/{media['id']}", headers=admin_headers
    )
    assert missing.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def test_comment_flow_and_guest_forbidden(
    client: TestClient, admin_headers, resident_headers, guest_headers, resident_user
):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]

    guest_res = client.post(
        f"/api/v1/announcements/{ann_id}/comments",
        json={"content": "Não posso comentar"},
        headers=guest_headers,
    )
    assert guest_res.status_code == status.HTTP_403_FORBIDDEN

    resident_res = client.post(
        f"/api/v1/announcements/{ann_id}/comments",
        json={"content": "Confirmado presença"},
        headers=resident_headers,
    )
    assert resident_res.status_code == status.HTTP_201_CREATED
    comment = resident_res.json()
    assert comment["author_name"] == resident_user.full_name

    list_res = client.get(f"/api/v1/announcements/{ann_id}/comments", headers=admin_headers)
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1

    detail = client.get(f"/api/v1/announcements/{ann_id}", headers=admin_headers).json()
    assert detail["comment_count"] == 1


def test_delete_comment_author_or_publisher_only(
    client: TestClient, admin_headers, resident_headers, guest_headers
):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]
    comment = client.post(
        f"/api/v1/announcements/{ann_id}/comments",
        json={"content": "Meu comentário"},
        headers=resident_headers,
    ).json()

    forbidden = client.delete(f"/api/v1/announcements/comments/{comment['id']}", headers=guest_headers)
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN

    ok = client.delete(f"/api/v1/announcements/comments/{comment['id']}", headers=resident_headers)
    assert ok.status_code == status.HTTP_204_NO_CONTENT

    missing = client.delete(f"/api/v1/announcements/comments/{comment['id']}", headers=admin_headers)
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_publisher_can_delete_others_comment(client: TestClient, admin_headers, resident_headers):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]
    comment = client.post(
        f"/api/v1/announcements/{ann_id}/comments",
        json={"content": "Comentário do morador"},
        headers=resident_headers,
    ).json()

    res = client.delete(f"/api/v1/announcements/comments/{comment['id']}", headers=admin_headers)
    assert res.status_code == status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# Read receipts
# ---------------------------------------------------------------------------


def test_mark_read_is_idempotent(
    client: TestClient, admin_headers, resident_headers, session: Session
):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]

    first = client.post(f"/api/v1/announcements/{ann_id}/read", headers=resident_headers)
    assert first.status_code == status.HTTP_200_OK
    second = client.post(f"/api/v1/announcements/{ann_id}/read", headers=resident_headers)
    assert second.status_code == status.HTTP_200_OK
    assert first.json()["read_at"] == second.json()["read_at"]

    from sqlmodel import select

    count = len(
        session.exec(
            select(AnnouncementReadReceipt).where(
                AnnouncementReadReceipt.announcement_id == uuid.UUID(ann_id)
            )
        ).all()
    )
    assert count == 1

    feed = client.get("/api/v1/announcements", headers=resident_headers).json()
    item = next(i for i in feed["items"] if i["id"] == ann_id)
    assert item["is_read"] is True


def test_read_receipts_list_publisher_only(client: TestClient, admin_headers, resident_headers):
    created = _create_announcement(client, admin_headers)
    ann_id = created["id"]
    client.post(f"/api/v1/announcements/{ann_id}/read", headers=resident_headers)

    forbidden = client.get(f"/api/v1/announcements/{ann_id}/read-receipts", headers=resident_headers)
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN

    ok = client.get(f"/api/v1/announcements/{ann_id}/read-receipts", headers=admin_headers)
    assert ok.status_code == status.HTTP_200_OK
    assert len(ok.json()) == 1


# ---------------------------------------------------------------------------
# Not found paths
# ---------------------------------------------------------------------------


def test_operations_on_missing_announcement_return_404(client: TestClient, admin_headers):
    missing_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/announcements/{missing_id}", headers=admin_headers).status_code == 404
    assert (
        client.put(
            f"/api/v1/announcements/{missing_id}", json={"title": "X"}, headers=admin_headers
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/announcements/{missing_id}", headers=admin_headers).status_code == 404
    assert (
        client.post(f"/api/v1/announcements/{missing_id}/read", headers=admin_headers).status_code == 404
    )
    assert (
        client.get(f"/api/v1/announcements/{missing_id}/comments", headers=admin_headers).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/announcements/{missing_id}/comments",
            json={"content": "oi"},
            headers=admin_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/announcements/{missing_id}/media",
            headers=admin_headers,
            files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/announcements/{missing_id}/read-receipts", headers=admin_headers).status_code
        == 404
    )


def test_service_layer_direct_calls(session: Session, admin_user: User, normal_user: User):
    """Exercise service functions directly to cover edge branches."""
    from app.schemas.announcement import AnnouncementCreate

    created = announcement_service.create_announcement(
        session, admin_user, AnnouncementCreate(title="Direto", content="Conteúdo")
    )
    detail = announcement_service.get_announcement(session, admin_user, created.id)
    assert detail.comments == []

    receipts = announcement_service.list_read_receipts(session, admin_user, created.id)
    assert receipts == []
