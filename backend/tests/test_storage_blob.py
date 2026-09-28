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

import inspect
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
    BLOB_HOST_SUFFIX,
    CloudinaryStorageProvider,
    LocalStorageProvider,
    S3StorageProvider,
    VercelBlobStorageProvider,
    generated_storage_provider,
    upload_storage_provider,
)
from app.services.tenant_service import TenantService
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


# ---------------------------------------------------------------------------
# Reading an object back (APRAS-96)
# ---------------------------------------------------------------------------
#
# The store was write-only, so APRAS-92's logo ladder took its linked-`<img>`
# rung for every Blob-stored logo. These cases pin the read side: a single
# reachable host, a bound enforced twice, and `None` -- never an exception --
# for every failure shape, because the one caller is an unauthenticated,
# uncached render.
#
# `httpx.Client.stream` is patched, not `.request`, and the gate is **not** the
# one the write fixtures use. A read is a `GET` on the CDN object URL, which
# never starts with `BLOB_API_BASE_URL`, so a fixture copied from `http` above
# would hand every read straight to the live CDN. This one keys off
# `BLOB_HOST_SUFFIX` and fails the test outright for any other URL instead of
# passing it through.

READ_URL = f"https://{STORE_ID.lower()}.public.blob.vercel-storage.com/uploads/x.png"

#: Every value that is not one of *this* store's public objects. The four host
#: clauses of `resolve_own_url` are each represented: a foreign store, a
#: non-Blob host, a store id that only *prefixes* ours, a wrong access label
#: and an extra label -- plus the non-TLS scheme and the relative paths.
NOT_OURS = [
    pytest.param(None, id="none"),
    pytest.param("", id="empty"),
    pytest.param("static/uploads/2026/09/x.png", id="relative-path"),
    pytest.param("/static/uploads/2026/09/x.png", id="absolute-path"),
    pytest.param(
        f"http://{STORE_ID.lower()}.public.blob.vercel-storage.com/x.png",
        id="not-tls",
    ),
    pytest.param("https://cdn.example.com/x.png", id="foreign-host"),
    pytest.param(
        "https://other.public.blob.vercel-storage.com/x.png", id="other-store"
    ),
    pytest.param(
        f"https://{STORE_ID.lower()}x.public.blob.vercel-storage.com/x.png",
        id="store-id-merely-a-prefix",
    ),
    pytest.param(
        f"https://{STORE_ID.lower()}.evil.blob.vercel-storage.com/x.png",
        id="wrong-access-label",
    ),
    pytest.param(
        f"https://{STORE_ID.lower()}.public.a.blob.vercel-storage.com/x.png",
        id="an-extra-label",
    ),
    # `urlparse` itself raises `ValueError` on this one, before any field is
    # read: `resolve_own_url` still answers `None` and `read_file` still logs a
    # line, with `-` where the host would be.
    pytest.param("https://[::1/x.png", id="malformed-ipv6"),
]

#: The tokens that yield no store id at all, the non-ASCII one included: it is
#: the shape that would otherwise surface as a `UnicodeEncodeError` from inside
#: the transport rather than as `None`.
UNUSABLE_TOKENS = [
    pytest.param(None, id="absent"),
    pytest.param("", id="empty"),
    pytest.param("vercel_blob_rw", id="malformed"),
    pytest.param("vercel_blob_rw_Str01dAbCdÉf_s3cr3t", id="non-ascii"),
]


class _Streamed:
    """A stand-in for `httpx`'s streaming response context manager.

    It counts both `iter_bytes()` invocations and chunks actually consumed, so
    a case can assert the body was never read at all *and* that a read which
    overran was abandoned rather than buffered whole.
    """

    def __init__(self, status_code=200, *, chunks=(), headers=None):
        self.status_code = status_code
        self._chunks = list(chunks)
        self.headers = httpx.Headers(headers or {})
        self.iter_calls = 0
        self.chunks_consumed = 0
        self.closed = False

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def iter_bytes(self):
        self.iter_calls += 1

        def _chunks():
            for chunk in self._chunks:
                self.chunks_consumed += 1
                yield chunk

        return _chunks()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.closed = True
        return False


def _served(
    body: bytes = b"PNGBYTES",
    *,
    status: int = 200,
    chunks: list[bytes] | None = None,
    headers: dict[str, str] | None = None,
    declare_length: bool = True,
) -> _Streamed:
    """A response serving `body` (or `chunks`), with a truthful
    `content-length` unless the case is about its absence."""
    served = list(chunks) if chunks is not None else [body]
    head = dict(headers or {})
    if declare_length and "content-length" not in {key.lower() for key in head}:
        head["content-length"] = str(sum(len(chunk) for chunk in served))
    return _Streamed(status, chunks=served, headers=head)


@pytest.fixture(name="blob_read")
def blob_read_fixture(monkeypatch: pytest.MonkeyPatch):
    """Capture every `httpx.Client.stream`, answering with a canned response.

    The gate is `BLOB_HOST_SUFFIX` and there is **no pass-through**: a read URL
    is a CDN object URL, so the write fixtures' `startswith(BLOB_API_BASE_URL)`
    test would let it reach the real network. Any other URL fails the test.
    """

    def _install(
        response: _Streamed | None = None, *, error: Exception | None = None
    ) -> list[SimpleNamespace]:
        calls: list[SimpleNamespace] = []

        def _stream(_self, method, url, **kwargs):
            host = urlparse(str(url)).hostname or ""
            if not host.endswith(BLOB_HOST_SUFFIX):
                raise AssertionError(
                    f"a read escaped the fake and would have hit the network: {url}"
                )
            calls.append(
                SimpleNamespace(
                    method=method,
                    url=str(url),
                    headers={
                        key.lower(): value
                        for key, value in (kwargs.get("headers") or {}).items()
                    },
                )
            )
            if error is not None:
                raise error
            return response if response is not None else _served()

        monkeypatch.setattr(httpx.Client, "stream", _stream)
        return calls

    return _install


def test_read_file_gets_the_object_url_itself_with_no_credential(blob_read):
    """ER 2: a `GET` on the CDN object URL, not on `vercel.com/api/blob`, and
    no `authorization` header -- a public object needs none, and not sending
    one means a bug in the host check could not leak the write token."""
    calls = blob_read(_served(b"PNGBYTES"))

    assert _uploads().read_file(READ_URL) == b"PNGBYTES"

    assert len(calls) == 1
    assert calls[0].method == "GET"
    assert calls[0].url == READ_URL
    assert BLOB_API_BASE_URL not in calls[0].url
    assert "authorization" not in calls[0].headers


def test_read_file_takes_one_positional_argument(blob_read):
    """APRAS-92 §B's ladder calls `read_file(url)` and nothing else."""
    blob_read(_served(b"PNGBYTES"))

    assert _uploads().read_file(READ_URL) == b"PNGBYTES"
    assert storage_service.BaseStorageProvider.read_file(_uploads(), READ_URL) is None


@pytest.mark.parametrize("url", NOT_OURS)
def test_read_file_attempts_no_request_for_a_url_this_store_does_not_own(
    blob_read, url
):
    calls = blob_read(_served(b"SECRET"))

    assert _uploads().read_file(url) is None
    assert calls == []


@pytest.mark.parametrize("url", NOT_OURS)
def test_resolve_own_url_claims_only_this_stores_public_objects(url):
    provider = _uploads()

    assert provider.resolve_own_url(READ_URL) == READ_URL
    assert provider.resolve_own_url(url) is None


def test_resolve_own_url_refuses_userinfo_and_a_port():
    provider = _uploads()
    host = f"{STORE_ID.lower()}.public.blob.vercel-storage.com"

    assert provider.resolve_own_url(f"https://evil@{host}/x.png") is None
    assert provider.resolve_own_url(f"https://u:p@{host}/x.png") is None
    assert provider.resolve_own_url(f"https://{host}:8443/x.png") is None
    assert provider.resolve_own_url(f"https://{host}:notaport/x.png") is None


@pytest.mark.parametrize("token", UNUSABLE_TOKENS)
def test_read_file_with_no_usable_token_owns_nothing_and_asks_nothing(blob_read, token):
    calls = blob_read(_served(b"SECRET"))
    provider = _uploads(token=token)

    assert provider.resolve_own_url(READ_URL) is None
    assert provider.read_file(READ_URL) is None
    assert calls == []


@pytest.mark.parametrize("status", [301, 302, 400, 403, 404, 429, 500, 503])
def test_read_file_returns_none_for_any_non_2xx(blob_read, status):
    blob_read(_served(b"body", status=status))

    assert _uploads().read_file(READ_URL) is None


def test_a_redirect_is_not_followed(blob_read):
    """A `3xx` is a non-success status, so the second request never happens --
    including the one an SSRF would want, at the metadata address."""
    calls = blob_read(
        _served(
            b"",
            status=302,
            headers={"location": "http://169.254.169.254/latest/meta-data/"},
        )
    )

    assert _uploads().read_file(READ_URL) is None
    assert len(calls) == 1
    assert calls[0].url == READ_URL
    assert all("169.254.169.254" not in call.url for call in calls)


def test_read_file_returns_none_for_an_empty_body(blob_read):
    blob_read(_served(b""))

    assert _uploads().read_file(READ_URL) is None


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(httpx.ConnectError("no route"), id="connect-error"),
        pytest.param(httpx.ReadTimeout("timed out"), id="read-timeout"),
        pytest.param(httpx.HTTPError("generic"), id="httpx-error"),
        pytest.param(StorageUnavailableError("unavailable"), id="storage-unavailable"),
        pytest.param(ValueError("surprise"), id="value-error"),
        pytest.param(KeyError("surprise"), id="key-error"),
        pytest.param(UnicodeEncodeError("utf-8", "x", 0, 1, "bad"), id="unicode"),
    ],
)
def test_no_exception_of_any_type_escapes_read_file(blob_read, error):
    """`read_file` is reached from a public, unauthenticated render: an escaping
    exception would answer the bodiless 500 APRAS-94 §6 exists to prevent."""
    blob_read(error=error)

    assert _uploads().read_file(READ_URL) is None


def test_the_default_ceiling_is_the_logo_ceiling():
    """No logo the product ever accepted is refused by the default."""
    assert storage_service.BLOB_MAX_READ_BYTES == 2 * 1024 * 1024
    assert storage_service.BLOB_MAX_READ_BYTES == TenantService.LOGO_MAX_FILE_SIZE


def test_a_content_length_over_the_ceiling_is_refused_before_a_byte_is_read(
    blob_read,
):
    oversize = storage_service.BLOB_MAX_READ_BYTES + 1
    response = _Streamed(
        200,
        chunks=[b"\x00" * oversize],
        headers={"content-length": str(oversize)},
    )
    blob_read(response)

    assert _uploads().read_file(READ_URL) is None
    assert response.iter_calls == 0
    assert response.chunks_consumed == 0


def test_a_body_overrunning_the_ceiling_without_a_content_length_is_abandoned(
    blob_read,
):
    """`content-length` is absent on a chunked response and is a remote claim
    either way, so the streamed check is the one that actually holds."""
    chunk = b"\x00" * (64 * 1024)
    total = storage_service.BLOB_MAX_READ_BYTES // len(chunk) + 4
    response = _served(chunks=[chunk] * total, declare_length=False)
    blob_read(response)

    assert _uploads().read_file(READ_URL) is None
    assert response.iter_calls == 1
    assert response.chunks_consumed < total


def test_a_body_at_the_ceiling_is_returned_whole_and_one_byte_over_is_not(
    blob_read,
):
    body = b"\x5a" * storage_service.BLOB_MAX_READ_BYTES

    blob_read(_served(body))
    assert _uploads().read_file(READ_URL) == body

    blob_read(_served(body + b"\x5a"))
    assert _uploads().read_file(READ_URL) is None


def test_a_caller_may_supply_a_tighter_ceiling_than_the_default(blob_read):
    body = b"\x5a" * 2048

    blob_read(_served(body))
    assert _uploads().read_file(READ_URL) == body

    blob_read(_served(body))
    assert _uploads().read_file(READ_URL, max_bytes=1024) is None


def test_every_failure_is_logged_once_and_a_success_is_silent(blob_read, caplog):
    blob_read(_served(b"PNGBYTES"))
    with caplog.at_level("WARNING", logger=storage_service.__name__):
        assert _uploads().read_file(READ_URL) == b"PNGBYTES"
    assert caplog.records == []

    blob_read(_served(b"", status=404))
    with caplog.at_level("WARNING", logger=storage_service.__name__):
        assert _uploads().read_file(READ_URL) is None
    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "404" in message
    assert TOKEN not in message


def test_the_base_provider_reads_nothing_and_owns_nothing():
    """Both defaults are concrete and return `None`, so no stub and no test
    double can raise an unimplemented-method exception at a client."""

    class _Minimal(storage_service.BaseStorageProvider):
        def save_file(self, file_bytes, filename, content_type, *, tenant_id=None):
            return "", ""

        def delete_file(self, file_path):
            return True

    provider = _Minimal()

    assert provider.read_file(READ_URL) is None
    assert provider.read_file(READ_URL, max_bytes=10) is None
    assert provider.resolve_own_url(READ_URL) is None

    signature = inspect.signature(storage_service.BaseStorageProvider.read_file)
    max_bytes = signature.parameters["max_bytes"]
    assert max_bytes.kind is inspect.Parameter.KEYWORD_ONLY
    assert max_bytes.default is None


# ---------------------------------------------------------------------------
# The local provider's `max_bytes`, which exists so the override is not
# narrower than the base it implements (APRAS-96).
# ---------------------------------------------------------------------------


def test_the_local_provider_accepts_and_honours_a_read_ceiling(tmp_path) -> None:
    """`max_bytes` must work on local disk, not only on Blob.

    The base declares `read_file(url, *, max_bytes=None)`. An override that
    took only `url` would raise `TypeError` the first time a caller stated a
    limit -- on whichever deployment happens to be configured for local disk,
    and with nothing in CI to catch it, since this project runs no type
    checker. So the keyword is exercised here rather than assumed.
    """
    target = tmp_path / "2026" / "09"
    target.mkdir(parents=True)
    (target / "logo.png").write_bytes(b"x" * 1024)
    provider = LocalStorageProvider(base_dir=tmp_path, url_prefix="/static/uploads")
    url = "/static/uploads/2026/09/logo.png"

    # No ceiling asked for: the whole file, exactly as before the keyword.
    assert provider.read_file(url) == b"x" * 1024
    # A ceiling that fits: still the whole file, and no TypeError.
    assert provider.read_file(url, max_bytes=1024) == b"x" * 1024
    # A ceiling below the file: refused, and nothing partial is handed back.
    assert provider.read_file(url, max_bytes=1023) is None


# ---------------------------------------------------------------------------
# Why a Blob refusal happened, not merely that one did (APRAS-101)
#
# `_describe` reads the response body only when it is JSON shaped exactly
# `{"error": {"code", "message"}}`, and nothing logged anything at all, so the
# production `400` on the logo upload arrived as a bare status: undiagnosable.
# These cases pin the record -- and, above everything else, pin that the
# credential scrub runs over the *whole* body before the 512-byte bound is
# applied to it.
# ---------------------------------------------------------------------------

#: The provider's token for the credential cases. Token-shaped, so
#: `_store_id` still reads `Str01dAbCdEf` out of it, with a tail segment that
#: could only be a secret -- an assertion on its absence cannot pass by luck.
SECRET_TOKEN = "vercel_blob_rw_Str01dAbCdEf_s3cr3tv4lu3"
SECRET_SEGMENT = "s3cr3tv4lu3"

#: Where the echoed token starts inside the straddle case's body. Numerically
#: pinned rather than described as "a few bytes before the bound": the token
#: runs from byte 498 to byte 536, so `BLOB_LOG_BODY_MAX_BYTES` (512) falls
#: *inside* it and a truncate-then-scrub implementation leaks the prefix that
#: fits. At this offset the leaked prefix is `vercel_blob_rw`, which is why the
#: case asserts the absence of **every** prefix from that length up rather than
#: only of `vercel_blob_rw_Str`: an assertion on the longer fragment alone
#: would pass under both orderings here and discriminate nothing.
STRADDLE_OFFSET = 498


def _sole_record(caplog) -> object:
    """The one WARNING the refusal produced, from this module's own logger."""
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert record.name == storage_service.__name__
    return record


def _refused_save(caplog, *, token: str = TOKEN) -> object:
    """Drive one refused upload and hand back its single log record.

    The canned response is whatever the `http` fixture the case installed
    answers with.
    """
    with (
        caplog.at_level("WARNING", logger=storage_service.__name__),
        pytest.raises(StorageUnavailableError),
    ):
        _uploads(token=token).save_file(b"x", "logo.png", "image/png")
    return _sole_record(caplog)


def test_a_refused_upload_logs_the_status_the_method_and_the_apis_body(http, caplog):
    http(
        httpx.Response(
            400,
            json={"error": {"code": "bad_request", "message": "pathname is required"}},
        )
    )

    message = _refused_save(caplog).getMessage()

    assert "400" in message
    assert "PUT" in message
    assert "bad_request" in message
    assert "pathname is required" in message


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(
            httpx.Response(400, text="Bad Request: missing pathname"),
            "missing pathname",
            id="plain-text",
        ),
        pytest.param(
            httpx.Response(400, json={"message": "store suspended"}),
            "store suspended",
            id="bare-message-dict",
        ),
        pytest.param(
            httpx.Response(400, text="<html><body>Gateway refused</body></html>"),
            "Gateway refused",
            id="an-intermediarys-html",
        ),
    ],
)
def test_a_body_the_error_shape_drops_still_reaches_the_record(
    http, caplog, body, expected
):
    """The shape `_describe` reduces to a bare status -- the task's whole point.

    The caller-visible message stays exactly what it was: only the record
    carries the body.
    """
    http(body)

    record = _refused_save(caplog)

    assert expected in record.getMessage()


def test_the_allowlisted_response_headers_reach_the_record(http, caplog):
    http(
        httpx.Response(
            400,
            text="refused",
            headers={
                "x-vercel-error": "BLOB_STORE_SUSPENDED",
                "x-vercel-error-code": "store_suspended",
                "x-vercel-id": "gru1::abc123",
                "retry-after": "30",
            },
        )
    )

    message = _refused_save(caplog).getMessage()

    for value in ("BLOB_STORE_SUSPENDED", "store_suspended", "gru1::abc123", "30"):
        assert value in message


def test_a_refusal_without_those_headers_still_logs_and_names_none_of_them(
    http, caplog
):
    http(httpx.Response(400, text="refused"))

    message = _refused_save(caplog).getMessage()

    assert "refused" in message
    for absent in (
        "x-vercel-error",
        "x-vercel-error-code",
        "x-vercel-id",
        "retry-after",
    ):
        assert absent not in message


def test_a_2xx_without_a_usable_url_is_logged_with_its_body(http, caplog):
    """The second refusal point: a 2xx whose body carries no usable `url`."""
    http(httpx.Response(200, json={"pathname": "uploads/x.png"}))

    message = _refused_save(caplog).getMessage()

    assert "200" in message
    assert "uploads/x.png" in message


def test_no_record_can_carry_the_store_credential(http, caplog):
    http(
        httpx.Response(
            400, json={"error": {"message": f"token {SECRET_TOKEN} rejeitado"}}
        )
    )

    message = _refused_save(caplog, token=SECRET_TOKEN).getMessage()

    assert SECRET_TOKEN not in message
    assert SECRET_SEGMENT not in message
    assert "Bearer" not in message
    assert "authorization" not in message.lower()
    assert "***" in message


def test_the_credential_cannot_survive_the_truncation_boundary(http, caplog):
    """The ordering of the two operations, proven rather than asserted.

    Scrub-then-truncate replaces the whole token before a single byte is cut,
    so no fragment of it survives. Truncate-then-scrub cuts the token at byte
    512, and the surviving prefix no longer matches the full-token pattern --
    it passes the scrub untouched and reaches a durable log stream.
    """
    body = "." * STRADDLE_OFFSET + SECRET_TOKEN + " (fim do corpo)"
    assert len(body.encode("utf-8")) > storage_service.BLOB_LOG_BODY_MAX_BYTES
    assert STRADDLE_OFFSET < storage_service.BLOB_LOG_BODY_MAX_BYTES
    http(httpx.Response(400, text=body))

    message = _refused_save(caplog, token=SECRET_TOKEN).getMessage()

    assert SECRET_TOKEN not in message
    assert SECRET_SEGMENT not in message
    assert "vercel_blob_rw_Str" not in message
    # Every prefix from the generic marker up, so the case discriminates at
    # this offset instead of merely conforming to the description.
    for cut in range(len("vercel_blob_rw"), len(SECRET_TOKEN) + 1):
        assert SECRET_TOKEN[:cut] not in message


@pytest.mark.parametrize(
    "filler",
    [
        pytest.param("E", id="ascii"),
        # Multibyte, so the bound has to be measured in **bytes**: 512 of these
        # are 1024 bytes, which a character-count bound would wave through.
        pytest.param("é", id="multibyte"),
    ],
)
def test_a_long_refusal_body_is_bounded_in_bytes_and_marked(http, caplog, filler):
    body = filler * (10 * 1024)
    http(httpx.Response(400, text=body))

    record = _refused_save(caplog)

    logged_body = record.args[-1]
    assert logged_body.endswith(storage_service.BLOB_LOG_TRUNCATION_MARKER)
    kept = logged_body.removesuffix(storage_service.BLOB_LOG_TRUNCATION_MARKER)
    assert len(kept.encode("utf-8")) <= storage_service.BLOB_LOG_BODY_MAX_BYTES
    assert storage_service.BLOB_LOG_BODY_MAX_BYTES == 512
    assert len(record.getMessage()) < len(body)


def test_a_successful_upload_emits_no_record(http, caplog):
    http()

    with caplog.at_level("WARNING", logger=storage_service.__name__):
        _, url = _uploads().save_file(b"x", "logo.png", "image/png")

    assert url == BLOB_URL
    assert caplog.records == []


def test_a_failed_delete_is_no_longer_silent(http, caplog):
    http(
        httpx.Response(
            404, json={"error": {"code": "not_found", "message": "blob not found"}}
        )
    )

    with caplog.at_level("WARNING", logger=storage_service.__name__):
        assert _uploads().delete_file(BLOB_URL) is False

    message = _sole_record(caplog).getMessage()
    assert "404" in message
    assert "POST" in message
    assert "blob not found" in message


def test_the_scrub_is_a_no_op_with_no_token_configured_and_corrupts_nothing():
    """The empty-token guard, which is not decoration.

    `bytes.replace(b"", b"***")` inserts the replacement between *every* byte,
    so a provider built without a token would log a body no one could read.
    Unreachable through `save_file` -- `_store_id` refuses a token-less
    provider before any request -- so it is exercised here directly.
    """
    provider = _uploads(token=None)
    response = httpx.Response(400, text="pathname is required", headers={"e": "1"})

    assert provider._refusal_body(response) == "pathname is required"
    assert provider._refusal_headers(response) == {
        "content-type": "text/plain; charset=utf-8"
    }
