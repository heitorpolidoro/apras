"""The supplier document a quote carries (APRAS-63).

Two routes on the existing purchases router, both acting on one quote of one
request and both guarded by ``purchases:quote_update`` (D4): uploading a
supplier's PDF *is* editing that quote, so no new permission string is minted
and enforcement stays exactly where the sibling quote routes put it -- inside
``PurchaseService``.

The provider under test is a **real** ``LocalStorageProvider`` pointed at a
``tmp_path``, never a stub: "the previous file no longer exists on disk" is
only worth something when a file was really written, and the production
provider is the thing being exercised.
"""

import io
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app.core.permissions import ROUTE_PERMISSIONS
from app.core.security import create_access_token
from app.core.uploads import sanitise_upload_filename
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID
from app.models.user import User
from app.services import purchase_service as purchase_service_module
from app.services.purchase_service import PurchaseService
from app.services.storage_service import LocalStorageProvider
from tests.conftest import make_user

ATTACHMENT_ROUTE = "/api/v1/purchase-requests/{request_id}/quotes/{quote_id}/attachment"
PERMISSION = "purchases:quote_update"

#: The frontend half of the two-sided pin `src/api/tenantProfile.ts`
#: established, named in every failure message so a red run points at the file
#: that has to move with it.
_FRONTEND_CLIENT = "frontend/src/api/purchases.ts"


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _make_user(session: Session, profile: str, email: str, cpf: str) -> User:
    return make_user(
        session,
        id=uuid.uuid4(),
        email=email,
        full_name=f"User {email}",
        hashed_password="hash",
        profile=profile,
        cpf=cpf,
    )


@pytest.fixture
def admin(session: Session) -> User:
    return _make_user(session, "ADMINISTRATOR", "admin_at@test.com", "11111111111")


@pytest.fixture
def manager(session: Session) -> User:
    return _make_user(session, "MANAGER", "manager_at@test.com", "33333333333")


@pytest.fixture
def other_manager(session: Session) -> User:
    return _make_user(session, "MANAGER", "manager2_at@test.com", "77777777777")


@pytest.fixture
def unprivileged(session: Session) -> User:
    """A caller holding every purchases permission **except** the mapped one.

    Not a legacy profile: the point is to move exactly one string, so the
    refusal can only be caused by ``purchases:quote_update``.
    """
    role = Role(
        name=f"Papel {uuid.uuid4().hex[:8]}",
        tenant_id=DEFAULT_TENANT_ID,
        permissions=[
            "purchases:read",
            "purchases:create",
            "purchases:quote_create",
            "purchases:quote_delete",
        ],
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return make_user(
        session,
        id=uuid.uuid4(),
        email="nogate_at@test.com",
        full_name="Sem Permissao",
        hashed_password="hash",
        profile="GUEST",
        cpf="88888888811",
        is_superuser=False,
        roles=[role],
    )


@pytest.fixture(name="storage")
def storage_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    provider = LocalStorageProvider(tmp_path / "uploads")
    monkeypatch.setattr(purchase_service_module, "_storage_provider", provider)
    return provider


def _stored_path(provider: LocalStorageProvider, url: str) -> Path:
    return provider.base_dir / url.removeprefix("/static/uploads/")


def _pdf(body: bytes = b"a quotation") -> bytes:
    return b"%PDF-1.4\n" + body + b"\n%%EOF\n"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "#0b7285").save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "#0b7285").save(buffer, format="JPEG")
    return buffer.getvalue()


def _create_request(client: TestClient, user: User, title: str = "Pedido") -> dict:
    res = client.post(
        "/api/v1/purchase-requests", json={"title": title}, headers=_headers(user)
    )
    assert res.status_code == 201, res.text
    return res.json()


def _add_quote(client: TestClient, user: User, request_id: str, **overrides) -> dict:
    # Since APRAS-73 the price lives on the quote's lines; `unit_price`
    # and `quantity` here shape the single default line this module needs.
    unit_price = overrides.pop("unit_price", 10.0)
    quantity = overrides.pop("quantity", 1)
    payload = {
        "supplier_name": "Fornecedor A",
        "items": [
            {
                "description": "Item do orçamento",
                "quantity": quantity,
                "unit_price": unit_price,
            }
        ],
    }
    payload.update(overrides)
    res = client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json=payload,
        headers=_headers(user),
    )
    assert res.status_code == 201, res.text
    return res.json()


def _url(request_id: str, quote_id: str) -> str:
    return ATTACHMENT_ROUTE.format(request_id=request_id, quote_id=quote_id)


def _upload(
    client: TestClient,
    user: User,
    request_id: str,
    quote_id: str,
    *,
    content: bytes,
    filename: str = "orcamento-acme.pdf",
    content_type: str = "application/pdf",
):
    return client.put(
        _url(request_id, quote_id),
        files={"file": (filename, content, content_type)},
        headers=_headers(user),
    )


@pytest.fixture
def quote(client: TestClient, admin: User) -> dict:
    request = _create_request(client, admin, "Troca das luminárias")
    created = _add_quote(client, admin, request["id"], supplier_name="Luz & Cia")
    return {"request": request, "quote": created}


# ---------------------------------------------------------------------------
# The happy paths
# ---------------------------------------------------------------------------


def test_put_stores_a_pdf_and_returns_the_public_url_and_original_name(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=_pdf(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["attachment_url"].startswith("/static/uploads/")
    assert body["attachment_filename"] == "orcamento-acme.pdf"
    assert _stored_path(storage, body["attachment_url"]).exists()


@pytest.mark.parametrize(
    ("filename", "content_type", "factory"),
    [
        ("proposta.png", "image/png", _png),
        ("proposta.jpg", "image/jpeg", _jpeg),
    ],
)
def test_png_and_jpeg_are_accepted_the_same_way(
    client: TestClient,
    admin: User,
    quote: dict,
    storage: LocalStorageProvider,
    filename: str,
    content_type: str,
    factory,
) -> None:
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=factory(),
        filename=filename,
        content_type=content_type,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["attachment_filename"] == filename
    assert _stored_path(storage, body["attachment_url"]).exists()


def test_get_request_exposes_the_two_columns_on_every_quote(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id = quote["request"]["id"]
    _add_quote(client, admin, request_id, supplier_name="Sem anexo", unit_price=99.0)
    uploaded = _upload(
        client, admin, request_id, quote["quote"]["id"], content=_pdf()
    ).json()

    detail = client.get(
        f"/api/v1/purchase-requests/{request_id}", headers=_headers(admin)
    ).json()

    by_supplier = {q["supplier_name"]: q for q in detail["quotes"]}
    assert by_supplier["Luz & Cia"]["attachment_url"] == uploaded["attachment_url"]
    assert by_supplier["Luz & Cia"]["attachment_filename"] == "orcamento-acme.pdf"
    assert by_supplier["Sem anexo"]["attachment_url"] is None
    assert by_supplier["Sem anexo"]["attachment_filename"] is None


# ---------------------------------------------------------------------------
# The refusals -- D2 and D3: 422, no file, no column
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("notas.txt", "text/plain", b"nao e um documento"),
        ("logo.svg", "image/svg+xml", b"<svg xmlns='http://www.w3.org/2000/svg'/>"),
        ("grande.pdf", "application/pdf", b"%PDF-1.4" + b"x" * (5 * 1024 * 1024)),
        ("mentiroso.pdf", "application/pdf", b"nao comeca com o marcador"),
        ("quebrado.png", "image/png", b"nao decodifica"),
    ],
    ids=["wrong-type", "svg", "too-large", "not-a-pdf", "undecodable-png"],
)
def test_a_refused_file_is_422_and_writes_neither_file_nor_column(
    client: TestClient,
    admin: User,
    quote: dict,
    storage: LocalStorageProvider,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=content,
        filename=filename,
        content_type=content_type,
    )

    assert response.status_code == 422, response.text
    detail = client.get(
        f"/api/v1/purchase-requests/{quote['request']['id']}", headers=_headers(admin)
    ).json()
    assert detail["quotes"][0]["attachment_url"] is None
    assert detail["quotes"][0]["attachment_filename"] is None
    assert not list(storage.base_dir.rglob("*.*"))


# ---------------------------------------------------------------------------
# Replacement and removal -- D6
# ---------------------------------------------------------------------------


def test_a_second_upload_replaces_and_deletes_the_previous_file(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id, quote_id = quote["request"]["id"], quote["quote"]["id"]
    first = _upload(client, admin, request_id, quote_id, content=_pdf(b"um")).json()
    second = _upload(
        client,
        admin,
        request_id,
        quote_id,
        content=_png(),
        filename="proposta.png",
        content_type="image/png",
    ).json()

    assert second["attachment_url"] != first["attachment_url"]
    assert second["attachment_filename"] == "proposta.png"
    assert not _stored_path(storage, first["attachment_url"]).exists()
    assert _stored_path(storage, second["attachment_url"]).exists()


def test_delete_clears_both_columns_removes_the_file_and_is_idempotent(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id, quote_id = quote["request"]["id"], quote["quote"]["id"]
    stored = _upload(client, admin, request_id, quote_id, content=_pdf()).json()

    first = client.delete(_url(request_id, quote_id), headers=_headers(admin))
    assert first.status_code == 200, first.text
    assert first.json()["attachment_url"] is None
    assert first.json()["attachment_filename"] is None
    assert not _stored_path(storage, stored["attachment_url"]).exists()

    second = client.delete(_url(request_id, quote_id), headers=_headers(admin))
    assert second.status_code == 200, second.text
    assert second.json()["attachment_url"] is None


def test_deleting_the_quote_deletes_its_file(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id, quote_id = quote["request"]["id"], quote["quote"]["id"]
    stored = _upload(client, admin, request_id, quote_id, content=_pdf()).json()

    removed = client.delete(
        f"/api/v1/purchase-requests/{request_id}/quotes/{quote_id}",
        headers=_headers(admin),
    )

    assert removed.status_code == 204, removed.text
    assert not _stored_path(storage, stored["attachment_url"]).exists()


def test_deleting_the_request_deletes_every_quotes_file(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id = quote["request"]["id"]
    second_quote = _add_quote(
        client, admin, request_id, supplier_name="Eletro Norte", unit_price=20.0
    )
    first = _upload(
        client, admin, request_id, quote["quote"]["id"], content=_pdf(b"um")
    ).json()
    second = _upload(
        client, admin, request_id, second_quote["id"], content=_pdf(b"dois")
    ).json()

    removed = client.delete(
        f"/api/v1/purchase-requests/{request_id}", headers=_headers(admin)
    )

    assert removed.status_code == 204, removed.text
    assert not _stored_path(storage, first["attachment_url"]).exists()
    assert not _stored_path(storage, second["attachment_url"]).exists()


# ---------------------------------------------------------------------------
# Frozen means frozen -- D5
# ---------------------------------------------------------------------------


def test_a_decided_request_answers_409_on_both_routes_and_keeps_the_file(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id, quote_id = quote["request"]["id"], quote["quote"]["id"]
    stored = _upload(client, admin, request_id, quote_id, content=_pdf()).json()
    decided = client.post(
        f"/api/v1/purchase-requests/{request_id}/decision",
        json={"quote_id": quote_id, "justification": "melhor prazo de entrega"},
        headers=_headers(admin),
    )
    assert decided.status_code == 201, decided.text

    upload = _upload(client, admin, request_id, quote_id, content=_pdf(b"outro"))
    removal = client.delete(_url(request_id, quote_id), headers=_headers(admin))

    assert upload.status_code == 409, upload.text
    assert removal.status_code == 409, removal.text
    assert _stored_path(storage, stored["attachment_url"]).exists()
    detail = client.get(
        f"/api/v1/purchase-requests/{request_id}", headers=_headers(admin)
    ).json()
    assert detail["quotes"][0]["attachment_url"] == stored["attachment_url"]


# ---------------------------------------------------------------------------
# Permissions -- D4
# ---------------------------------------------------------------------------


def test_a_caller_without_the_permission_is_403(
    client: TestClient, unprivileged: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id, quote_id = quote["request"]["id"], quote["quote"]["id"]

    upload = _upload(client, unprivileged, request_id, quote_id, content=_pdf())
    removal = client.delete(_url(request_id, quote_id), headers=_headers(unprivileged))

    assert upload.status_code == 403, upload.text
    assert removal.status_code == 403, removal.text


def test_a_manager_may_attach_to_their_own_quote_only(
    client: TestClient,
    admin: User,
    manager: User,
    other_manager: User,
    storage: LocalStorageProvider,
) -> None:
    request = _create_request(client, admin, "Pedido do gerente")
    own = _add_quote(client, manager, request["id"], supplier_name="Do gerente")

    mine = _upload(client, manager, request["id"], own["id"], content=_pdf())
    theirs = _upload(client, other_manager, request["id"], own["id"], content=_pdf())

    assert mine.status_code == 200, mine.text
    assert theirs.status_code == 403, theirs.text


def test_an_unknown_request_or_quote_is_404(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    request_id, quote_id = quote["request"]["id"], quote["quote"]["id"]

    unknown_request = _upload(
        client, admin, str(uuid.uuid4()), quote_id, content=_pdf()
    )
    unknown_quote = _upload(
        client, admin, request_id, str(uuid.uuid4()), content=_pdf()
    )

    assert unknown_request.status_code == 404, unknown_request.text
    assert unknown_quote.status_code == 404, unknown_quote.text


# ---------------------------------------------------------------------------
# The two-sided pin with the frontend client
# ---------------------------------------------------------------------------


def test_the_attachment_contract_matches_the_frontend_client() -> None:
    """Neither side can import the other, so each states it and names the other."""
    assert PurchaseService.ATTACHMENT_MAX_FILE_SIZE == 5 * 1024 * 1024, (
        "PurchaseService.ATTACHMENT_MAX_FILE_SIZE changed. "
        f"`QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES` in {_FRONTEND_CLIENT} "
        "pre-checks the file against this number; update both."
    )
    assert {
        "application/pdf",
        "image/png",
        "image/jpeg",
    } == PurchaseService.ATTACHMENT_ALLOWED_MIME_TYPES, (
        "PurchaseService.ATTACHMENT_ALLOWED_MIME_TYPES changed. "
        f"`QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES` in {_FRONTEND_CLIENT} feeds "
        "the `accept=` of the file input and its client-side pre-check."
    )
    assert ROUTE_PERMISSIONS[("PUT", ATTACHMENT_ROUTE)] == PERMISSION
    assert ROUTE_PERMISSIONS[("DELETE", ATTACHMENT_ROUTE)] == PERMISSION


def test_the_cap_is_imported_from_media_service_rather_than_re_typed() -> None:
    """D2: 5 MiB is `media_service.MAX_FILE_SIZE`, reused, not restated."""
    from app.services import media_service

    assert PurchaseService.ATTACHMENT_MAX_FILE_SIZE == media_service.MAX_FILE_SIZE


def test_webp_and_svg_are_deliberately_outside_the_accepted_set() -> None:
    """D2, stated so a future author has to delete a case to accept either."""
    assert "image/webp" not in PurchaseService.ATTACHMENT_ALLOWED_MIME_TYPES
    assert "image/svg+xml" not in PurchaseService.ATTACHMENT_ALLOWED_MIME_TYPES


# ---------------------------------------------------------------------------
# The name the client sends is a claim, not a path (APRAS-63 D1)
# ---------------------------------------------------------------------------


def test_a_png_named_svg_still_lands_on_disk_with_a_png_extension(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    """The on-disk extension comes from the validated type, never from the name.

    `/static/uploads/` is served unauthenticated by a `StaticFiles` mount that
    guesses the content type from the extension, so an attacker-chosen `.svg`
    (or `.html`) suffix on otherwise valid image bytes would be an
    active-content surface -- the very one D2 excludes SVG to avoid.
    """
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=_png(),
        filename="payload.svg",
        content_type="image/png",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    stored = _stored_path(storage, body["attachment_url"])
    assert stored.suffix == ".png"
    assert stored.exists()
    assert body["attachment_url"].endswith(".png")
    assert body["attachment_filename"] == "payload.png"


def test_a_jpeg_keeps_the_canonical_jpg_extension_whatever_the_name_says(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=_jpeg(),
        filename="orcamento.html",
        content_type="image/jpeg",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert _stored_path(storage, body["attachment_url"]).suffix == ".jpg"
    assert body["attachment_filename"] == "orcamento.jpg"


def test_directory_components_are_stripped_from_the_stored_name(
    client: TestClient, admin: User, quote: dict
) -> None:
    """Basename first: a traversal prefix never reaches the column."""
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=_pdf(),
        filename="../../etc/orcamento acme.pdf",
    )

    assert response.status_code == 200, response.text
    name = response.json()["attachment_filename"]
    assert name == "orcamento acme.pdf"
    assert "/" not in name


def test_control_characters_are_dropped_from_the_stored_name() -> None:
    """Unit level: the multipart encoder escapes these before the wire.

    APRAS-65 moved the body to `app.core.uploads`; the purchase call site
    passes its own two constants, so what this asserts is unchanged.
    """
    assert (
        sanitise_upload_filename(
            "or\ncamento\x00\tacme.pdf",
            "application/pdf",
            max_length=PurchaseService.ATTACHMENT_FILENAME_MAX_LENGTH,
            fallback_stem=PurchaseService.ATTACHMENT_FALLBACK_STEM,
        )
        == "orcamentoacme.pdf"
    )


def test_the_private_sanitiser_is_gone() -> None:
    """APRAS-65: one sanitiser, in `app.core.uploads`, not a copy per service."""
    assert not hasattr(PurchaseService, "_sanitise_attachment_filename")


def test_a_windows_style_path_is_reduced_to_its_basename(
    client: TestClient, admin: User, quote: dict
) -> None:
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=_pdf(),
        filename=r"C:\Users\acme\Desktop\orcamento.pdf",
    )

    assert response.status_code == 200, response.text
    assert response.json()["attachment_filename"] == "orcamento.pdf"


def test_a_nameless_upload_falls_back_to_a_typed_default(
    client: TestClient, admin: User, quote: dict, storage: LocalStorageProvider
) -> None:
    """An empty or all-dots name still has to produce one usable name."""
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=_png(),
        filename="...",
        content_type="image/png",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["attachment_filename"] == "documento.png"
    assert _stored_path(storage, body["attachment_url"]).suffix == ".png"


def test_an_absurdly_long_name_is_truncated_but_keeps_its_extension(
    client: TestClient, admin: User, quote: dict
) -> None:
    response = _upload(
        client,
        admin,
        quote["request"]["id"],
        quote["quote"]["id"],
        content=_pdf(),
        filename="a" * 400 + ".pdf",
    )

    assert response.status_code == 200, response.text
    name = response.json()["attachment_filename"]
    assert name.endswith(".pdf")
    assert len(name) <= 128
