"""RBAC tests for the PORTEIRO (gatekeeper) role (APRAS-12).

PORTEIRO is scoped to exactly the gate check-in/check-out flow:
- Allowed: check-in/check-out (access_logs.py), GET /lots/ and GET
  /lots/{id} (required for the GatekeeperDashboard lot selector),
  visitors.py (unrestricted for any authenticated user).
- Forbidden: lot write endpoints, and every handler in occurrences.py,
  documents.py, announcements.py, and authorizations.py (the four modules
  that had zero role-based authorization before this task).

Every test also includes a regression check proving the same endpoint still
works for a role that could call it before this task.
"""

import io
import uuid

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.enums import AuthorizationType, DayOfWeek, ShiftType, UserRole
from app.models.user import User
from app.schemas.lot import LotCreate
from app.schemas.visitor import VisitorAuthorizationCreate, VisitorCreate
from app.services.lot_service import LotService
from app.services.visitor_service import VisitorService


@pytest.fixture
def porteiro_user(session: Session) -> User:
    """Create and persist a PORTEIRO user."""
    user = User(
        id=uuid.uuid4(),
        email="porteiro@test.com",
        full_name="Porteiro User",
        hashed_password=get_password_hash("password"),
        role=UserRole.PORTEIRO,
        cpf="98765432100",
    )
    session.add(user)
    session.commit()
    return user


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _make_image_bytes(color: str = "red") -> bytes:
    img = Image.new("RGB", (50, 50), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# lots.py — PORTEIRO gains read access, write access unchanged
# ---------------------------------------------------------------------------


def test_porteiro_can_read_lots_but_not_write(
    client: TestClient, session: Session, porteiro_user: User, admin_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="P1", lot_number="01"))

    # PORTEIRO can list and read lot detail (required for GatekeeperDashboard).
    assert client.get("/api/v1/lots/", headers=_auth_header(porteiro_user)).status_code == 200
    assert (
        client.get(f"/api/v1/lots/{lot.id}", headers=_auth_header(porteiro_user)).status_code
        == 200
    )

    # PORTEIRO still cannot write lots.
    assert (
        client.post(
            "/api/v1/lots/",
            json={"block": "P1", "lot_number": "02"},
            headers=_auth_header(porteiro_user),
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/v1/lots/{lot.id}",
            json={"notes": "hacked"},
            headers=_auth_header(porteiro_user),
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/lots/{lot.id}", headers=_auth_header(porteiro_user)).status_code
        == 403
    )

    # Regression: ADMINISTRATOR keeps full read+write access.
    assert client.get("/api/v1/lots/", headers=_auth_header(admin_user)).status_code == 200
    assert (
        client.post(
            "/api/v1/lots/",
            json={"block": "P1", "lot_number": "03"},
            headers=_auth_header(admin_user),
        ).status_code
        == 201
    )


# ---------------------------------------------------------------------------
# access_logs.py — PORTEIRO can check visitors in and out
# ---------------------------------------------------------------------------


def test_porteiro_can_check_in_and_check_out(
    client: TestClient, session: Session, porteiro_user: User, admin_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="P2", lot_number="01"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Visitante Porteiro"))
    auth = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor.id,
            auth_type=AuthorizationType.PERMANENT,
            allowed_days=list(DayOfWeek),
            allowed_shifts=[ShiftType.FULL_DAY],
        ),
        admin_user,
    )

    res_in = client.post(
        "/api/v1/access-logs/check-in",
        json={"visitor_id": str(visitor.id), "lot_id": str(lot.id), "authorization_id": str(auth.id)},
        headers=_auth_header(porteiro_user),
    )
    assert res_in.status_code == 201
    log_id = res_in.json()["id"]

    res_out = client.post(
        "/api/v1/access-logs/check-out",
        json={"access_log_id": log_id},
        headers=_auth_header(porteiro_user),
    )
    assert res_out.status_code == 200

    # Regression: ADMINISTRATOR/DIRECTOR/MANAGER retain unchanged access.
    visitor2 = VisitorService.create_visitor(session, VisitorCreate(full_name="Visitante Admin"))
    auth2 = VisitorService.create_authorization(
        session,
        lot.id,
        VisitorAuthorizationCreate(
            visitor_id=visitor2.id,
            auth_type=AuthorizationType.PERMANENT,
            allowed_days=list(DayOfWeek),
            allowed_shifts=[ShiftType.FULL_DAY],
        ),
        admin_user,
    )
    res_in_admin = client.post(
        "/api/v1/access-logs/check-in",
        json={
            "visitor_id": str(visitor2.id),
            "lot_id": str(lot.id),
            "authorization_id": str(auth2.id),
        },
        headers=_auth_header(admin_user),
    )
    assert res_in_admin.status_code == 201


# ---------------------------------------------------------------------------
# visitors.py — left unrestricted, PORTEIRO must still be able to search
# ---------------------------------------------------------------------------


def test_porteiro_can_search_visitors(client: TestClient, porteiro_user: User):
    res = client.get("/api/v1/visitors", headers=_auth_header(porteiro_user))
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# occurrences.py — zero role checks before this task; PORTEIRO now excluded
# ---------------------------------------------------------------------------


def test_porteiro_forbidden_on_all_occurrence_handlers(
    client: TestClient, porteiro_user: User, normal_user: User
):
    headers_porteiro = _auth_header(porteiro_user)
    headers_normal = _auth_header(normal_user)

    payload = {
        "category": "OTHER",
        "title": "Teste",
        "description": "Descrição de teste",
        "is_public": True,
        "is_anonymous": False,
    }

    # Regression: normal_user (DIRECTOR) can still create/list/get/update/note.
    create_res = client.post("/api/v1/occurrences", json=payload, headers=headers_normal)
    assert create_res.status_code == 201
    occ_id = create_res.json()["id"]

    assert client.get("/api/v1/occurrences", headers=headers_normal).status_code == 200
    assert client.get(f"/api/v1/occurrences/{occ_id}", headers=headers_normal).status_code == 200
    assert (
        client.put(
            f"/api/v1/occurrences/{occ_id}/status",
            json={"status": "UNDER_REVIEW"},
            headers=headers_normal,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/occurrences/{occ_id}/timeline",
            json={"note": "Nota", "is_internal_only": False},
            headers=headers_normal,
        ).status_code
        == 201
    )

    # PORTEIRO forbidden on every handler.
    assert client.get("/api/v1/occurrences", headers=headers_porteiro).status_code == 403
    assert client.post("/api/v1/occurrences", json=payload, headers=headers_porteiro).status_code == 403
    assert client.get(f"/api/v1/occurrences/{occ_id}", headers=headers_porteiro).status_code == 403
    assert (
        client.put(
            f"/api/v1/occurrences/{occ_id}/status",
            json={"status": "RESOLVED"},
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/occurrences/{occ_id}/timeline",
            json={"note": "Nota", "is_internal_only": False},
            headers=headers_porteiro,
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# documents.py — zero role checks before this task; PORTEIRO now excluded
# ---------------------------------------------------------------------------


def test_porteiro_forbidden_on_all_document_handlers(
    client: TestClient, porteiro_user: User, admin_user: User
):
    headers_porteiro = _auth_header(porteiro_user)
    headers_admin = _auth_header(admin_user)

    # Regression: admin_user (ADMINISTRATOR) can still do everything.
    folder_res = client.post(
        "/api/v1/documents/folders", json={"name": "Pasta Regressao"}, headers=headers_admin
    )
    assert folder_res.status_code == 201
    folder_id = folder_res.json()["id"]

    assert client.get("/api/v1/documents/folders", headers=headers_admin).status_code == 200
    assert (
        client.put(
            f"/api/v1/documents/folders/{folder_id}",
            json={"name": "Pasta Atualizada"},
            headers=headers_admin,
        ).status_code
        == 200
    )

    doc_res = client.post(
        "/api/v1/documents",
        json={
            "folder_id": folder_id,
            "title": "Doc Regressao",
            "file_url": "https://storage.example.com/docs/reg.pdf",
            "file_size_bytes": 100,
        },
        headers=headers_admin,
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    assert client.get("/api/v1/documents", headers=headers_admin).status_code == 200
    version_res = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        json={"file_url": "https://storage.example.com/docs/reg_v2.pdf", "file_size_bytes": 120},
        headers=headers_admin,
    )
    assert version_res.status_code == 201
    assert (
        client.post(f"/api/v1/documents/{doc_id}/download", headers=headers_admin).status_code
        == 200
    )
    assert client.delete(f"/api/v1/documents/{doc_id}", headers=headers_admin).status_code == 204
    assert (
        client.delete(f"/api/v1/documents/folders/{folder_id}", headers=headers_admin).status_code
        == 204
    )

    # PORTEIRO forbidden on every handler. Build a fresh folder/document
    # (as admin) so each PORTEIRO call exercises the real guard, not a 404.
    folder2 = client.post(
        "/api/v1/documents/folders", json={"name": "Pasta Porteiro"}, headers=headers_admin
    ).json()
    doc2 = client.post(
        "/api/v1/documents",
        json={
            "folder_id": folder2["id"],
            "title": "Doc Porteiro",
            "file_url": "https://storage.example.com/docs/porteiro.pdf",
            "file_size_bytes": 100,
        },
        headers=headers_admin,
    ).json()

    assert client.get("/api/v1/documents/folders", headers=headers_porteiro).status_code == 403
    assert (
        client.post(
            "/api/v1/documents/folders", json={"name": "X"}, headers=headers_porteiro
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/v1/documents/folders/{folder2['id']}",
            json={"name": "Y"},
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert client.get("/api/v1/documents", headers=headers_porteiro).status_code == 403
    assert (
        client.post(
            "/api/v1/documents",
            json={
                "folder_id": folder2["id"],
                "title": "Deveria falhar",
                "file_url": "https://storage.example.com/docs/x.pdf",
                "file_size_bytes": 10,
            },
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/documents/{doc2['id']}/versions",
            json={"file_url": "https://storage.example.com/docs/x2.pdf", "file_size_bytes": 10},
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert (
        client.post(f"/api/v1/documents/{doc2['id']}/download", headers=headers_porteiro).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/documents/{doc2['id']}", headers=headers_porteiro).status_code == 403
    )
    assert (
        client.delete(
            f"/api/v1/documents/folders/{folder2['id']}", headers=headers_porteiro
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# announcements.py — zero role checks before this task; PORTEIRO now excluded
# ---------------------------------------------------------------------------


def test_porteiro_forbidden_on_all_announcement_handlers(
    client: TestClient, porteiro_user: User, admin_user: User
):
    headers_porteiro = _auth_header(porteiro_user)
    headers_admin = _auth_header(admin_user)

    # Regression: admin_user (ADMINISTRATOR, a publisher) can still do
    # everything it could before this task.
    created = client.post(
        "/api/v1/announcements",
        json={"title": "Regressao", "content": "Conteudo"},
        headers=headers_admin,
    )
    assert created.status_code == 201
    ann_id = created.json()["id"]

    assert client.get("/api/v1/announcements", headers=headers_admin).status_code == 200
    assert client.get(f"/api/v1/announcements/{ann_id}", headers=headers_admin).status_code == 200
    assert (
        client.put(
            f"/api/v1/announcements/{ann_id}",
            json={"title": "Atualizado"},
            headers=headers_admin,
        ).status_code
        == 200
    )
    media = client.post(
        f"/api/v1/announcements/{ann_id}/media",
        headers=headers_admin,
        files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert media.status_code == 201
    media_id = media.json()["id"]
    assert (
        client.delete(
            f"/api/v1/announcements/{ann_id}/media/{media_id}", headers=headers_admin
        ).status_code
        == 204
    )
    assert client.get(f"/api/v1/announcements/{ann_id}/comments", headers=headers_admin).status_code == 200
    comment = client.post(
        f"/api/v1/announcements/{ann_id}/comments",
        json={"content": "Comentario"},
        headers=headers_admin,
    )
    assert comment.status_code == 201
    comment_id = comment.json()["id"]
    assert (
        client.delete(
            f"/api/v1/announcements/comments/{comment_id}", headers=headers_admin
        ).status_code
        == 204
    )
    assert client.post(f"/api/v1/announcements/{ann_id}/read", headers=headers_admin).status_code == 200
    assert (
        client.get(f"/api/v1/announcements/{ann_id}/read-receipts", headers=headers_admin).status_code
        == 200
    )
    assert client.delete(f"/api/v1/announcements/{ann_id}", headers=headers_admin).status_code == 204

    # PORTEIRO forbidden on every handler. Use a fresh announcement/comment
    # (as admin) so each PORTEIRO call exercises the guard, not a 404.
    ann2 = client.post(
        "/api/v1/announcements",
        json={"title": "Porteiro", "content": "Conteudo"},
        headers=headers_admin,
    ).json()
    comment2 = client.post(
        f"/api/v1/announcements/{ann2['id']}/comments",
        json={"content": "Comentario admin"},
        headers=headers_admin,
    ).json()

    assert client.get("/api/v1/announcements", headers=headers_porteiro).status_code == 403
    assert (
        client.post(
            "/api/v1/announcements",
            json={"title": "X", "content": "Y"},
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert client.get(f"/api/v1/announcements/{ann2['id']}", headers=headers_porteiro).status_code == 403
    assert (
        client.put(
            f"/api/v1/announcements/{ann2['id']}",
            json={"title": "Hack"},
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/announcements/{ann2['id']}", headers=headers_porteiro).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/announcements/{ann2['id']}/media",
            headers=headers_porteiro,
            files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/announcements/{ann2['id']}/media/{uuid.uuid4()}", headers=headers_porteiro
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/announcements/{ann2['id']}/comments", headers=headers_porteiro).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/announcements/{ann2['id']}/comments",
            json={"content": "Nao deveria"},
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/announcements/comments/{comment2['id']}", headers=headers_porteiro
        ).status_code
        == 403
    )
    assert (
        client.post(f"/api/v1/announcements/{ann2['id']}/read", headers=headers_porteiro).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/announcements/{ann2['id']}/read-receipts", headers=headers_porteiro
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# authorizations.py — zero role checks before this task; PORTEIRO now excluded
# ---------------------------------------------------------------------------


def test_porteiro_forbidden_on_all_authorization_handlers(
    client: TestClient, session: Session, porteiro_user: User, admin_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="P3", lot_number="01"))
    visitor = VisitorService.create_visitor(session, VisitorCreate(full_name="Visitante Auth"))

    headers_porteiro = _auth_header(porteiro_user)
    headers_admin = _auth_header(admin_user)

    # Regression: admin_user can still list/create/revoke.
    assert (
        client.get(f"/api/v1/lots/{lot.id}/authorizations", headers=headers_admin).status_code
        == 200
    )
    created = client.post(
        f"/api/v1/lots/{lot.id}/authorizations",
        json={"visitor_id": str(visitor.id), "auth_type": "SINGLE"},
        headers=headers_admin,
    )
    assert created.status_code == 201
    auth_id = created.json()["id"]
    assert (
        client.put(
            f"/api/v1/authorizations/{auth_id}/revoke", headers=headers_admin
        ).status_code
        == 200
    )

    # PORTEIRO forbidden on every handler.
    assert (
        client.get(f"/api/v1/lots/{lot.id}/authorizations", headers=headers_porteiro).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/lots/{lot.id}/authorizations",
            json={"visitor_id": str(visitor.id), "auth_type": "SINGLE"},
            headers=headers_porteiro,
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/v1/authorizations/{auth_id}/revoke", headers=headers_porteiro
        ).status_code
        == 403
    )
