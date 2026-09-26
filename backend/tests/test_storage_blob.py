"""Uploads that survive a serverless deploy (APRAS-94).

The production filesystem is read-only outside `/tmp`, so
`LocalStorageProvider.save_file`'s `mkdir` raises `OSError` on Vercel and the
exception escapes to Starlette's `ServerErrorMiddleware` -- which sits
*outside* `CORSMiddleware` and answers with a bodiless 500 carrying no
`access-control-allow-origin`. That header's absence is the signature of an
unhandled route exception, and it is what the browser mislabels as CORS.

So this module proves two things, and one is as important as the other: the
Blob provider speaks the REST contract `@vercel/blob` 2.6.1 speaks, and **no
storage failure of any shape escapes unhandled** -- not a non-2xx, not a
transport error, and not a 2xx whose body is not the JSON we expect.

Every case here patches `httpx.Client.request` the way `tests/test_mail.py`
patches `httpx.AsyncClient.post`. Nothing in this file reaches the network,
and the token-absent case asserts that no request is attempted at all.
"""

import io
import itertools
import re
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions import (
    StorageUnavailableError,
    UnsupportedStorageContentTypeError,
)
from app.core.security import create_access_token, get_password_hash
from app.core.tenant_context import set_acting_tenant
from app.models.enums import EntityType, StorageProvider
from app.models.media_asset import MediaAsset
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User
from app.services import (
    project_report_service,
    storage_service,
    tenant_service,
    voting_service,
)
from app.services.media_service import MediaService
from app.services.storage_service import (
    BLOB_API_BASE_URL,
    BLOB_API_VERSION,
    CloudinaryStorageProvider,
    LocalStorageProvider,
    S3StorageProvider,
    VercelBlobStorageProvider,
    generated_storage_provider,
    upload_storage_provider,
)
from tests.voting_helpers import make_assembly, make_user, make_vote

#: A token of the shape Vercel injects: the store id is the fourth
#: `_`-separated field, exactly as `parseStoreIdFromReadWriteToken` reads it.
TOKEN = "vercel_blob_rw_Str01dAbCdEf_s3cr3trandom"
STORE_ID = "Str01dAbCdEf"

UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
PATHNAME_PATTERN = re.compile(
    rf"^(uploads|generated)/[^/]+/\d{{4}}/\d{{2}}/{UUID_PATTERN}"
    r"\.(jpg|png|webp|pdf|html)$"
)

BLOB_URL = f"https://{STORE_ID.lower()}.public.blob.vercel-storage.com/x.png"

#: The tenant-logo route, and one of the origins `settings.BACKEND_CORS_ORIGINS`
#: allows -- the pair the production symptom was reported on.
LOGO_URL = "/api/v1/tenant-profile/logo"
ALLOWED_ORIGIN = "https://apras.vercel.app"

_SERIAL = itertools.count(1)


def _cpf(serial: int) -> str:
    """A check-digit-valid CPF, derived: `user.cpf` is globally unique."""
    digits = [int(character) for character in f"{serial:09d}"]
    for weights in (range(10, 1, -1), range(11, 1, -1)):
        total = sum(d * w for d, w in zip(digits, weights, strict=True))
        check = (total * 10) % 11
        digits.append(0 if check == 10 else check)
    return "".join(str(d) for d in digits)


def _ok(url: str = BLOB_URL) -> httpx.Response:
    """The success body the API answers a `PUT` with."""
    return httpx.Response(
        200,
        json={
            "url": url,
            "downloadUrl": f"{url}?download=1",
            "pathname": "uploads/x.png",
            "contentType": "image/png",
        },
    )


@pytest.fixture(name="http")
def http_fixture(monkeypatch: pytest.MonkeyPatch):
    """Capture every `httpx.Client.request`, answering with a canned response.

    Returns an installer: `http(response)` (or `http(error=...)`) hands back
    the list every captured call is appended to, so a case asserts on the
    request it produced *and* on how many it made.
    """

    def _install(
        response: httpx.Response | None = None, *, error: Exception | None = None
    ):
        calls: list[SimpleNamespace] = []
        original = httpx.Client.request

        def _request(_self, method, url, **kwargs):
            if not str(url).startswith(BLOB_API_BASE_URL):
                # FastAPI's `TestClient` is itself an `httpx.Client`, so only
                # the Blob API's own calls may be canned here: a route under
                # test has to keep reaching the ASGI app.
                return original(_self, method, url, **kwargs)
            calls.append(
                SimpleNamespace(
                    method=method,
                    url=str(url),
                    headers=dict(kwargs.get("headers") or {}),
                    content=kwargs.get("content"),
                    json=kwargs.get("json"),
                )
            )
            if error is not None:
                raise error
            return response if response is not None else _ok()

        monkeypatch.setattr(httpx.Client, "request", _request)
        return calls

    return _install


@pytest.fixture(name="forbid_http")
def forbid_http_fixture(monkeypatch: pytest.MonkeyPatch):
    """Any HTTP request at all fails the test that installed this."""

    original = httpx.Client.request

    def _boom(_self, method, url, **kwargs):
        if not str(url).startswith(BLOB_API_BASE_URL):
            return original(_self, method, url, **kwargs)
        raise AssertionError("the storage provider made an HTTP request")

    monkeypatch.setattr(httpx.Client, "request", _boom)


def _uploads(token: str | None = TOKEN) -> VercelBlobStorageProvider:
    return VercelBlobStorageProvider(
        namespace=storage_service.UPLOAD_NAMESPACE, token=token
    )


def _generated(token: str | None = TOKEN) -> VercelBlobStorageProvider:
    return VercelBlobStorageProvider(
        namespace=storage_service.GENERATED_NAMESPACE, token=token, allow_html=True
    )


def _pathname_of(call: SimpleNamespace) -> str:
    return parse_qs(urlparse(call.url).query)["pathname"][0]


# ---------------------------------------------------------------------------
# The seam: which provider a service gets, and who may build one
# ---------------------------------------------------------------------------


def test_without_a_token_both_factories_return_todays_local_provider(
    monkeypatch: pytest.MonkeyPatch, forbid_http
):
    monkeypatch.setattr(settings, "BLOB_READ_WRITE_TOKEN", None)

    uploads = upload_storage_provider()
    generated = generated_storage_provider()

    assert isinstance(uploads, LocalStorageProvider)
    assert uploads.base_dir.as_posix() == "static/uploads"
    assert uploads.url_prefix == "/static/uploads"
    assert uploads.provider_kind is StorageProvider.LOCAL_DISK
    assert isinstance(generated, LocalStorageProvider)
    assert generated.base_dir.as_posix() == "static/generated"
    assert generated.url_prefix == "/static/generated"


def test_with_a_token_both_factories_return_the_blob_provider(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "BLOB_READ_WRITE_TOKEN", TOKEN)

    uploads = upload_storage_provider()
    generated = generated_storage_provider()

    assert isinstance(uploads, VercelBlobStorageProvider)
    assert isinstance(generated, VercelBlobStorageProvider)
    assert uploads.namespace == storage_service.UPLOAD_NAMESPACE
    assert generated.namespace == storage_service.GENERATED_NAMESPACE
    assert uploads.provider_kind is StorageProvider.VERCEL_BLOB
    assert uploads.allow_html is False
    assert generated.allow_html is True


def test_no_module_outside_storage_service_instantiates_a_provider():
    """ER 2, as a text scan: the five hard-coded bindings are gone."""
    offenders = [
        path.as_posix()
        for path in Path("app").rglob("*.py")
        if path.name != "storage_service.py"
        and "LocalStorageProvider(" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


# ---------------------------------------------------------------------------
# The REST contract
# ---------------------------------------------------------------------------


def test_save_file_puts_the_bytes_with_every_documented_header(http):
    calls = http()

    internal, url = _uploads().save_file(
        b"\x89PNG-bytes", "logo.png", "image/png", tenant_id=None
    )

    assert len(calls) == 1
    call = calls[0]
    assert call.method == "PUT"
    assert call.url.startswith(f"{BLOB_API_BASE_URL}/?pathname=")
    assert call.content == b"\x89PNG-bytes"
    assert call.headers["authorization"] == f"Bearer {TOKEN}"
    assert call.headers["x-api-version"] == BLOB_API_VERSION
    assert call.headers["x-vercel-blob-store-id"] == STORE_ID
    assert call.headers["x-vercel-blob-access"] == "public"
    assert call.headers["x-add-random-suffix"] == "0"
    assert call.headers["x-content-type"] == "image/png"
    assert "x-allow-overwrite" not in {key.lower() for key in call.headers}
    assert url == BLOB_URL
    assert internal == BLOB_URL


def test_the_canonical_content_type_is_sent_not_the_clients_string(http):
    calls = http()

    _uploads().save_file(b"%PDF-1.7", "nota.pdf", "Application/PDF; version=1.7")

    assert calls[0].headers["x-content-type"] == "application/pdf"
    assert _pathname_of(calls[0]).endswith(".pdf")


def test_the_pathname_is_namespaced_by_the_acting_tenant(http):
    calls = http()
    tenant_id = uuid.uuid4()

    _uploads().save_file(b"x", "logo.png", "image/png", tenant_id=tenant_id)
    _generated().save_file(b"<html>", "ata.html", "text/html", tenant_id=tenant_id)

    upload_pathname, generated_pathname = (_pathname_of(call) for call in calls)
    assert PATHNAME_PATTERN.match(upload_pathname)
    assert PATHNAME_PATTERN.match(generated_pathname)
    assert upload_pathname.startswith(f"uploads/{tenant_id}/")
    assert generated_pathname.startswith(f"generated/{tenant_id}/")
    assert upload_pathname.endswith(".png")
    assert generated_pathname.endswith(".html")


def test_without_an_acting_tenant_the_segment_is_shared(http):
    calls = http()

    _uploads().save_file(b"x", "logo.png", "image/png", tenant_id=None)

    assert _pathname_of(calls[0]).startswith("uploads/shared/")


def test_the_client_filename_never_reaches_the_pathname(http):
    """APRAS-65: the name is display metadata, the suffix comes from the type."""
    calls = http()

    _uploads().save_file(b"x", "../../evil.svg", "image/png")

    pathname = _pathname_of(calls[0])
    assert "evil" not in pathname
    assert ".svg" not in pathname
    assert ".." not in pathname
    assert pathname.endswith(".png")


# ---------------------------------------------------------------------------
# What may be stored at all (the `HardenedStaticFiles` protection, per type)
# ---------------------------------------------------------------------------


def test_the_upload_namespace_refuses_html_and_an_unmapped_type(forbid_http):
    provider = _uploads()

    for content_type in ("text/html", "image/svg+xml"):
        with pytest.raises(UnsupportedStorageContentTypeError):
            provider.save_file(b"<script>", "x", content_type)


def test_the_generated_namespace_accepts_html_but_still_refuses_an_unmapped_type(
    http, forbid_http
):
    with pytest.raises(UnsupportedStorageContentTypeError):
        _generated().save_file(b"x", "x", "image/svg+xml")

    calls = http()
    _, url = _generated().save_file(b"<html>", "ata.html", "text/html")

    assert calls[0].headers["x-content-type"] == "text/html"
    assert url == BLOB_URL


# ---------------------------------------------------------------------------
# Failure: six inputs, one mapped error, never a crash
# ---------------------------------------------------------------------------


def test_a_non_2xx_raises_with_the_apis_own_code_and_message(http):
    http(
        httpx.Response(
            400,
            json={"error": {"code": "bad_request", "message": "pathname is required"}},
        )
    )

    with pytest.raises(StorageUnavailableError) as raised:
        _uploads().save_file(b"x", "logo.png", "image/png")

    assert "400" in raised.value.message
    assert "bad_request" in raised.value.message
    assert "pathname is required" in raised.value.message


def test_a_non_2xx_whose_body_is_not_json_still_raises_the_mapped_error(http):
    http(httpx.Response(502, text="<html>An error occurred</html>"))

    with pytest.raises(StorageUnavailableError) as raised:
        _uploads().save_file(b"x", "logo.png", "image/png")

    assert "502" in raised.value.message


def test_a_transport_error_raises_the_mapped_error(http):
    http(error=httpx.ConnectTimeout("timed out"))

    with pytest.raises(StorageUnavailableError):
        _uploads().save_file(b"x", "logo.png", "image/png")


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.Response(200, json={}), id="200-without-a-url"),
        pytest.param(httpx.Response(200, text="not json at all"), id="200-not-json"),
        pytest.param(httpx.Response(200, json={"url": ""}), id="200-empty-url"),
        pytest.param(httpx.Response(200, json={"url": 7}), id="200-url-not-a-string"),
        pytest.param(httpx.Response(200, json=["url"]), id="200-not-an-object"),
    ],
)
def test_a_2xx_with_an_unexpected_body_raises_the_mapped_error(http, response):
    """The one drift signature the version pin cannot make loud.

    A `KeyError` or a `JSONDecodeError` here would escape to
    `ServerErrorMiddleware` and reproduce byte-for-byte the bodiless,
    header-less 500 this task exists to eliminate.
    """
    http(response)

    with pytest.raises(StorageUnavailableError):
        _uploads().save_file(b"x", "logo.png", "image/png")


def test_an_absent_token_raises_before_any_request_and_names_the_variable(forbid_http):
    with pytest.raises(StorageUnavailableError) as raised:
        _uploads(token=None).save_file(b"x", "logo.png", "image/png")

    assert "BLOB_READ_WRITE_TOKEN" in raised.value.message


def test_a_malformed_token_raises_before_any_request(forbid_http):
    with pytest.raises(StorageUnavailableError) as raised:
        _uploads(token="not-a-blob-token").save_file(b"x", "logo.png", "image/png")

    assert "BLOB_READ_WRITE_TOKEN" in raised.value.message


def test_the_unimplemented_stubs_raise_the_mapped_error_not_notimplementederror():
    for provider in (S3StorageProvider(), CloudinaryStorageProvider()):
        with pytest.raises(StorageUnavailableError):
            provider.save_file(b"x", "logo.png", "image/png")
        with pytest.raises(StorageUnavailableError):
            provider.delete_file("whatever")


def test_storage_service_names_no_notimplementederror():
    source = Path("app/services/storage_service.py").read_text(encoding="utf-8")

    assert "NotImplementedError" not in source


def test_the_local_provider_maps_a_read_only_filesystem_to_the_domain_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    """The belt to the braces: even with no token, Vercel gets a JSON body."""

    def _read_only(*_args, **_kwargs):
        raise OSError(30, "Read-only file system")

    monkeypatch.setattr(Path, "mkdir", _read_only)

    with pytest.raises(StorageUnavailableError) as raised:
        LocalStorageProvider(tmp_path / "uploads").save_file(
            b"x", "logo.png", "image/png"
        )

    assert "read-only" in raised.value.message.lower()


# ---------------------------------------------------------------------------
# Deletion, and APRAS-61's leave-it-alone rule
# ---------------------------------------------------------------------------


def test_delete_file_posts_the_url_and_reports_success(http):
    calls = http(httpx.Response(200, json={}))

    deleted = _uploads().delete_file(BLOB_URL)

    assert deleted is True
    assert len(calls) == 1
    assert calls[0].method == "POST"
    assert calls[0].url == f"{BLOB_API_BASE_URL}/delete"
    assert calls[0].json == {"urls": [BLOB_URL]}
    assert calls[0].headers["content-type"] == "application/json"
    assert calls[0].headers["authorization"] == f"Bearer {TOKEN}"


def test_delete_file_never_raises_and_reports_failure(http):
    http(httpx.Response(500, text="boom"))

    assert _uploads().delete_file(BLOB_URL) is False


def test_delete_file_reports_failure_on_a_transport_error(http):
    http(error=httpx.ConnectError("no route"))

    assert _uploads().delete_file(BLOB_URL) is False


def test_delete_file_makes_no_request_for_a_value_it_did_not_mint(forbid_http):
    provider = _uploads()

    assert provider.delete_file("static/uploads/2026/09/x.png") is False
    assert provider.delete_file("/static/uploads/2026/09/x.png") is False
    assert provider.delete_file("https://cdn.example.com/logo.png") is False


def test_resolve_stored_path_claims_blob_urls_and_leaves_everything_else_alone():
    provider = _uploads()

    assert provider.resolve_stored_path(BLOB_URL) == BLOB_URL
    assert provider.resolve_stored_path("https://cdn.example.com/logo.png") is None
    assert provider.resolve_stored_path(None) is None


def test_the_local_provider_resolves_its_own_prefix_and_no_other(tmp_path):
    uploads = LocalStorageProvider(tmp_path / "uploads")
    generated = LocalStorageProvider(
        base_dir=tmp_path / "generated", url_prefix="/static/generated"
    )

    assert uploads.resolve_stored_path("/static/uploads/2026/09/x.png") == str(
        tmp_path / "uploads" / "2026/09/x.png"
    )
    assert generated.resolve_stored_path("/static/generated/2026/09/a.html") == str(
        tmp_path / "generated" / "2026/09/a.html"
    )
    assert generated.resolve_stored_path("/static/uploads/2026/09/x.png") is None
    assert uploads.resolve_stored_path("https://cdn.example.com/logo.png") is None
    assert uploads.resolve_stored_path(None) is None


# ---------------------------------------------------------------------------
# Through the services and the route: the symptom this task exists to remove
# ---------------------------------------------------------------------------


def _member(session: Session, permissions: list[str]) -> User:
    """A caller whose whole authority is ``permissions``."""
    role = Role(
        name=f"Papel {uuid.uuid4().hex[:8]}",
        tenant_id=DEFAULT_TENANT_ID,
        permissions=list(permissions),
    )
    session.add(role)
    session.commit()
    session.refresh(role)

    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@blob.example.com",
        full_name="Blob Caller",
        hashed_password=get_password_hash("password123"),
        cpf=_cpf(next(_SERIAL)),
        is_superuser=False,
        roles=[role],
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    return user


def _png() -> bytes:
    """Bytes Pillow can decode -- `media_service` really opens them."""
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "#082f2a").save(buffer, format="PNG")
    return buffer.getvalue()


def _put_logo(client: TestClient, user: User, *, origin: str | None = None):
    headers = {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(DEFAULT_TENANT_ID),
    }
    if origin is not None:
        headers["Origin"] = origin
    return client.put(
        LOGO_URL, files={"file": ("logo.png", _png(), "image/png")}, headers=headers
    )


def test_a_storage_failure_answers_503_with_a_body_and_the_cors_header(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """The regression test for the misleading CORS symptom.

    An *unhandled* exception here would be answered by Starlette's
    `ServerErrorMiddleware`, which sits outside `CORSMiddleware`: a bodiless
    500 with no `access-control-allow-origin`, which the browser reports as a
    CORS failure. Leaving the route as a mapped `DomainError` is what puts
    both the body and the header back.
    """

    class _Failing(LocalStorageProvider):
        def save_file(self, *_args, **_kwargs):
            raise StorageUnavailableError("o sistema de arquivos é somente leitura")

    monkeypatch.setattr(tenant_service, "_storage_provider", _Failing())
    caller = _member(session, ["tenants:profile_update"])

    response = _put_logo(client, caller, origin=ALLOWED_ORIGIN)

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"]
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_a_configured_blob_token_makes_the_logo_url_absolute(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch, http
):
    """Not a relative `/static/uploads/...`, which resolves against the
    *frontend* origin and so has never rendered in production."""
    calls = http()
    monkeypatch.setattr(settings, "BLOB_READ_WRITE_TOKEN", TOKEN)
    monkeypatch.setattr(tenant_service, "_storage_provider", upload_storage_provider())
    caller = _member(session, ["tenants:profile_update"])

    response = _put_logo(client, caller)

    assert response.status_code == 200, response.text
    logo_url = response.json()["logo_url"]
    assert logo_url == BLOB_URL
    assert logo_url.startswith("https://")
    assert urlparse(logo_url).hostname.endswith(".blob.vercel-storage.com")
    assert _pathname_of(calls[0]).startswith(f"uploads/{DEFAULT_TENANT_ID}/")


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        pytest.param(TOKEN, StorageProvider.VERCEL_BLOB, id="blob"),
        pytest.param(None, StorageProvider.LOCAL_DISK, id="local-disk"),
    ],
)
def test_a_media_asset_records_the_provider_that_stored_the_bytes(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
    http,
    tmp_path,
    token: str | None,
    expected: StorageProvider,
):
    http()
    monkeypatch.setattr(settings, "BLOB_READ_WRITE_TOKEN", token)
    monkeypatch.setattr(storage_service, "DEFAULT_UPLOAD_BASE_DIR", tmp_path / "up")
    uploader = make_user(session, "ADMINISTRATOR")

    asset = MediaService().upload_photo(
        session,
        uploader,
        _png(),
        "foto.png",
        "image/png",
        EntityType.LOT,
        uuid.uuid4(),
    )

    stored = session.get(MediaAsset, asset.id)
    assert stored.storage_provider is expected


def test_both_generated_writers_store_through_the_configured_provider(
    session: Session, monkeypatch: pytest.MonkeyPatch, http
):
    """ER 21: the obras report and the assembly minutes were broken in
    production for the same reason, and are fixed by the same seam."""
    calls = http()
    monkeypatch.setattr(settings, "BLOB_READ_WRITE_TOKEN", TOKEN)
    set_acting_tenant(session, DEFAULT_TENANT_ID)
    admin = make_user(session, "ADMINISTRATOR")
    assembly = make_assembly(session, admin)
    make_vote(session, admin, assembly=assembly)
    voting_service.close_assembly(session, admin, assembly)

    minutes = voting_service.save_minutes(session, admin, assembly)
    obras = project_report_service.save_report(session, admin)

    assert minutes.file_url == BLOB_URL
    assert obras.file_url == BLOB_URL
    for call in calls:
        pathname = _pathname_of(call)
        assert PATHNAME_PATTERN.match(pathname)
        assert pathname.startswith(f"generated/{DEFAULT_TENANT_ID}/")
        assert pathname.endswith(".html")


def test_the_local_provider_maps_a_failed_write_to_the_domain_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    """The directory can be created and the write still fails -- a full disk, a
    permission, a `/tmp` quota. Same mapped answer, never a bare `OSError`."""
    real_open = open

    def _refuse(path, mode="r", *args, **kwargs):
        if "w" in mode:
            raise OSError(28, "No space left on device")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _refuse)

    with pytest.raises(StorageUnavailableError) as raised:
        LocalStorageProvider(tmp_path / "uploads").save_file(
            b"x", "logo.png", "image/png"
        )

    assert "No space left on device" in raised.value.message


def test_the_local_delete_reports_failure_instead_of_raising(tmp_path):
    """`delete_file`'s best-effort contract: a directory where a file was
    expected cannot be unlinked, and a failed cleanup must not fail the
    request that replaced the document."""
    target = tmp_path / "not-a-file"
    target.mkdir()

    assert LocalStorageProvider(tmp_path).delete_file(str(target)) is False


def test_a_non_ascii_token_is_refused_before_the_header_is_encoded(
    forbid_http: None,
) -> None:
    """A token httpx cannot encode must not escape as a bare UnicodeEncodeError.

    `UnicodeEncodeError` is not an `httpx.HTTPError`, so without this guard it
    would pass `_request` untouched, reach `ServerErrorMiddleware` and answer a
    bodiless 500 with no CORS header -- the exact symptom this provider exists
    to remove. A smart quote pasted into the Vercel dashboard is enough to do it.
    """
    provider = VercelBlobStorageProvider(
        namespace="uploads", token="vercel_blob_rw_store”_secret"
    )
    with pytest.raises(StorageUnavailableError) as raised:
        provider.save_file(b"bytes", "logo.png", "image/png")
    assert "BLOB_READ_WRITE_TOKEN" in str(raised.value)
