"""The public logo route (APRAS-105 §C).

``GET /api/v1/public/tenants/{slug}/logo`` is the third unauthenticated
tenant-shaped read in the product, and the first that answers with bytes the
application fetched from somewhere else. It exists because the Blob store is
configured with **private** access by operator decision: the object is not
readable without our credential, so the backend reads it and serves the bytes.
The store stays private; the *route* is public.

Three properties carry it and each is asserted here:

* **It authenticates nobody**, so it is on ``UNGUARDED_ROUTES`` and maps to no
  catalogue permission.
* **Every refusal is a 404**, indistinguishably: an unknown slug, an inactive
  condominium, no logo, a suffix outside the three embeddable image types, an
  unreadable object and an oversized one all answer the same thing. A storage
  failure is never a 5xx.
* **The credential never leaves the backend.** It goes out on the read and
  appears in neither the response body nor the response headers.

The rate limit is asserted **structurally**. ``tests/conftest.py`` sets
``app.state.limiter.enabled = False`` for the whole suite, so a case that fires
31 requests and expects a 429 would pass while asserting nothing at all unless
it re-enabled the limiter around itself -- which the behavioural case below
does, exactly as ``test_public_branding.py`` does.
"""

import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import urls
from app.core.limiter import limiter
from app.core.permissions import UNGUARDED_ROUTES
from app.main import app
from app.models.tenant import Tenant
from app.services import tenant_service as tenant_service_module
from app.services.storage_service import (
    BLOB_HOST_SUFFIX,
    LocalStorageProvider,
    VercelBlobStorageProvider,
)
from app.services.tenant_service import TenantService
from tests.route_introspection import route_paths

#: The route, spelled exactly as FastAPI mounts it.
ROUTE = ("GET", "/api/v1/public/tenants/{slug}/logo")

#: A one-pixel PNG, small enough to compare byte for byte.
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

#: A token of the shape Vercel injects, with a tail that could only be a
#: secret: an assertion on its absence cannot pass by luck.
TOKEN = "vercel_blob_rw_Str01dAbCdEf_s3cr3tv4lu3"
STORE_ID = "Str01dAbCdEf"
BLOB_LOGO_URL = (
    f"https://{STORE_ID.lower()}.private.blob.vercel-storage.com/uploads/logo.png"
)


def _url(slug: str) -> str:
    return f"/api/v1/public/tenants/{slug}/logo"


def _tenant(session: Session, **kwargs) -> Tenant:
    kwargs.setdefault("id", uuid.uuid4())
    kwargs.setdefault("name", f"Condomínio {uuid.uuid4().hex[:8]}")
    tenant = Tenant(**kwargs)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@pytest.fixture(name="uploads")
def uploads_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real ``LocalStorageProvider`` rooted in ``tmp_path``.

    Real, not a double: the containment check and the prefix rule under test
    are the production ones.
    """
    monkeypatch.setattr(
        tenant_service_module, "_storage_provider", LocalStorageProvider(tmp_path)
    )
    return tmp_path


def _store(uploads: Path, name: str, payload: bytes) -> str:
    target = uploads / "2026" / "09" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return f"/static/uploads/2026/09/{name}"


# ---------------------------------------------------------------------------
# The 200
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("logo.png", "image/png"),
        ("logo.jpg", "image/jpeg"),
        ("logo.webp", "image/webp"),
    ],
)
def test_the_logo_is_served_with_no_credential_of_any_kind(
    client: TestClient, session: Session, uploads: Path, name: str, content_type: str
):
    tenant = _tenant(session, logo_url=_store(uploads, name, PNG_BYTES))

    response = client.get(_url(tenant.slug))

    assert response.status_code == 200
    assert response.content == PNG_BYTES
    assert response.headers["content-type"] == content_type
    # Asserted on the request the client just made, so "unauthenticated" is
    # not merely an absence in the source.
    assert "Authorization" not in response.request.headers
    assert "X-Tenant-Id" not in response.request.headers


def test_the_route_sets_no_cache_control_and_no_etag(
    client: TestClient, session: Session, uploads: Path
):
    """APRAS-92 D3, for the same reason it was taken there: a browser-held copy
    cannot be invalidated, and a logo replaced on the admin screen must not
    stay stale at a slug-stable URL."""
    tenant = _tenant(session, logo_url=_store(uploads, "logo.png", PNG_BYTES))

    headers = client.get(_url(tenant.slug)).headers

    assert "cache-control" not in headers
    assert "etag" not in headers


# ---------------------------------------------------------------------------
# Every refusal is the same 404
# ---------------------------------------------------------------------------


def test_an_unknown_slug_is_404(client: TestClient, session: Session, uploads: Path):
    assert client.get(_url("nao-existe")).status_code == 404


def test_an_inactive_condominium_is_404(
    client: TestClient, session: Session, uploads: Path
):
    """Matching the report route: an inactive condominium is not published."""
    tenant = _tenant(
        session, is_active=False, logo_url=_store(uploads, "logo.png", PNG_BYTES)
    )

    assert client.get(_url(tenant.slug)).status_code == 404


def test_a_condominium_with_no_logo_is_404(
    client: TestClient, session: Session, uploads: Path
):
    tenant = _tenant(session, logo_url=None)

    assert client.get(_url(tenant.slug)).status_code == 404


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("logo.svg", id="active-content"),
        pytest.param("logo.bin", id="untyped-suffix"),
        pytest.param("logo.pdf", id="not-an-image"),
    ],
)
def test_a_suffix_outside_the_logo_allowlist_is_404(
    client: TestClient, session: Session, uploads: Path, name: str
):
    """``image/svg+xml`` is active content and is deliberately out of
    ``LOGO_ALLOWED_MIME_TYPES``; the route must not publish one."""
    tenant = _tenant(session, logo_url=_store(uploads, name, PNG_BYTES))

    assert client.get(_url(tenant.slug)).status_code == 404


def test_an_unreadable_object_is_404_and_never_a_5xx(
    client: TestClient, session: Session, uploads: Path
):
    """The storage layer logs the reason; the route answers 404."""
    tenant = _tenant(session, logo_url="/static/uploads/2026/09/gone.png")

    response = client.get(_url(tenant.slug))

    assert response.status_code == 404


def test_a_value_escaping_the_uploads_directory_reads_nothing(
    client: TestClient, session: Session, uploads: Path
):
    tenant = _tenant(session, logo_url="/static/uploads/../../../etc/passwd")

    response = client.get(_url(tenant.slug))

    assert response.status_code == 404
    assert b"root:" not in response.content


def test_an_object_over_the_two_mib_ceiling_is_refused_rather_than_streamed(
    client: TestClient, session: Session, uploads: Path
):
    """The read states ``max_bytes=LOGO_MAX_FILE_SIZE`` explicitly rather than
    relying on ``BLOB_MAX_READ_BYTES``'s default."""
    oversized = b"\x89PNG" + b"\x00" * TenantService.LOGO_MAX_FILE_SIZE
    tenant = _tenant(session, logo_url=_store(uploads, "logo.png", oversized))

    response = client.get(_url(tenant.slug))

    assert response.status_code == 404
    assert len(response.content) < len(oversized)


def test_a_file_exactly_at_the_ceiling_is_still_served(
    client: TestClient, session: Session, uploads: Path
):
    """No logo the product ever accepted is refused by the bound."""
    at_the_ceiling = b"\x5a" * TenantService.LOGO_MAX_FILE_SIZE
    tenant = _tenant(session, logo_url=_store(uploads, "logo.png", at_the_ceiling))

    response = client.get(_url(tenant.slug))

    assert response.status_code == 200
    assert len(response.content) == TenantService.LOGO_MAX_FILE_SIZE


# ---------------------------------------------------------------------------
# The private store, read with our own credential
# ---------------------------------------------------------------------------


@pytest.fixture(name="private_store")
def private_store_fixture(monkeypatch: pytest.MonkeyPatch) -> list[SimpleNamespace]:
    """A Blob provider whose store refuses anonymous reads.

    The double is the *store*: it decides from the request's headers, so an
    implementation that dropped the credential would be refused exactly as
    production was. ``httpx.Client.stream`` is patched and not ``.request``,
    because the ``TestClient`` driving the route under test is itself an
    ``httpx.Client`` and has to keep reaching the ASGI app.
    """
    calls: list[SimpleNamespace] = []

    def _stream(_self, method, url, **kwargs):
        host = urlparse(str(url)).hostname or ""
        if not host.endswith(BLOB_HOST_SUFFIX):
            raise AssertionError(f"a read escaped the fake: {url}")
        headers = {
            key.lower(): value for key, value in (kwargs.get("headers") or {}).items()
        }
        calls.append(SimpleNamespace(method=method, url=str(url), headers=headers))
        authorized = headers.get("authorization") == f"Bearer {TOKEN}"
        body = PNG_BYTES if authorized else b"forbidden"
        return _Streamed(200 if authorized else 403, body)

    monkeypatch.setattr(httpx.Client, "stream", _stream)
    monkeypatch.setattr(
        tenant_service_module,
        "_storage_provider",
        VercelBlobStorageProvider(namespace="uploads", token=TOKEN),
    )
    return calls


class _Streamed:
    """The slice of `httpx`'s streaming response the provider actually uses."""

    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = httpx.Headers({"content-length": str(len(body))})

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def iter_bytes(self):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_the_route_reads_a_private_object_with_the_applications_own_credential(
    client: TestClient, session: Session, private_store: list[SimpleNamespace]
):
    tenant = _tenant(session, logo_url=BLOB_LOGO_URL)

    response = client.get(_url(tenant.slug))

    assert response.status_code == 200
    assert response.content == PNG_BYTES
    assert len(private_store) == 1
    assert private_store[0].headers["authorization"] == f"Bearer {TOKEN}"


def test_the_credential_reaches_neither_the_body_nor_the_headers(
    client: TestClient, session: Session, private_store: list[SimpleNamespace]
):
    tenant = _tenant(session, logo_url=BLOB_LOGO_URL)

    response = client.get(_url(tenant.slug))

    assert response.status_code == 200
    rendered = " ".join(f"{key}: {value}" for key, value in response.headers.items())
    for secret in (TOKEN, "s3cr3tv4lu3", STORE_ID, BLOB_LOGO_URL):
        assert secret.encode() not in response.content
        assert secret not in rendered


# ---------------------------------------------------------------------------
# The rate limit (the operator's decision, §C)
# ---------------------------------------------------------------------------


def test_the_route_is_decorated_with_a_thirty_per_minute_limit():
    """Structural, deliberately.

    ``tests/conftest.py`` disables the limiter for the whole suite, so a case
    that fires 31 requests and expects a 429 passes while asserting nothing --
    this project has shipped exactly that vacuous test once. This one reads
    slowapi's own registry, which is keyed by the handler's qualified name.
    """
    from app.api.v1.endpoints import public_branding

    key = (
        f"{public_branding.__name__}.{public_branding.get_public_tenant_logo.__name__}"
    )

    assert key in limiter._route_limits
    limits = [str(item.limit) for item in limiter._route_limits[key]]
    assert limits == ["30 per 1 minute"]
    # The sibling's limit, unchanged: the two are separate registrations.
    sibling = (
        f"{public_branding.__name__}."
        f"{public_branding.get_public_tenant_branding.__name__}"
    )
    assert [str(item.limit) for item in limiter._route_limits[sibling]] == [
        "30 per 1 minute"
    ]


def test_the_thirty_first_request_inside_a_minute_is_429(
    client: TestClient, session: Session, uploads: Path
):
    """The limit, exercised end to end with the limiter re-enabled around this
    case and restored in a ``finally`` -- the pattern
    ``test_public_branding.py`` and ``test_rate_limit.py`` already use."""
    tenant = _tenant(session, logo_url=_store(uploads, "logo.png", PNG_BYTES))
    app.state.limiter.reset()
    app.state.limiter.enabled = True
    try:
        for _ in range(30):
            assert client.get(_url(tenant.slug)).status_code == 200

        assert client.get(_url(tenant.slug)).status_code == 429
    finally:
        app.state.limiter.enabled = False
        app.state.limiter.reset()


# ---------------------------------------------------------------------------
# The registries
# ---------------------------------------------------------------------------


def test_the_route_is_unguarded_and_maps_to_no_permission():
    from app.core.permissions import ROUTE_PERMISSIONS

    assert ROUTE in UNGUARDED_ROUTES
    assert ROUTE not in ROUTE_PERMISSIONS


def test_the_builders_prefix_is_the_one_the_application_mounts():
    """``app/core/urls.py`` restates ``/api/v1`` rather than importing
    ``app.main``; the two are pinned against each other here."""
    live = route_paths()

    assert f"{urls.API_V1_PREFIX}{urls.PUBLIC_PREFIX}/tenants/{{slug}}/logo" in live
