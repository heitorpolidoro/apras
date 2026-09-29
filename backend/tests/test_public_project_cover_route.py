"""The public cover-photo route (APRAS-104 §A, §C).

``GET /api/v1/public/tenants/{slug}/projects/{project_id}/cover`` is the fourth
unauthenticated tenant-shaped read in the product and the second that answers
with bytes the application fetched from somewhere else. It exists for the same
reason the logo route does: the Blob store is configured with **private**
access by operator decision, so the object is not readable without our
credential -- not by an anonymous reader of ``/c/<slug>/obras`` and not by a
signed-in administrator either, because an ``<img src>`` carries no credential
of ours in either case. The backend reads the object and serves the bytes. The
store stays private; the *route* is public.

Four properties carry it and each is asserted here:

* **It authenticates nobody**, so it is on ``UNGUARDED_ROUTES`` and maps to no
  catalogue permission (asserted in ``tests/test_projects.py``, beside the two
  write routes it partners).
* **Every refusal is a 404**, indistinguishably and with the literal equality
  rather than a ``!= 500``: an unknown slug, an inactive condominium, a project
  belonging to another condominium, a project with no cover, a value the
  provider owns but cannot read. One test per condition.
* **The read ceiling is this caller's, stated explicitly.**
  ``storage_service.BLOB_MAX_READ_BYTES`` defaults to 2 MiB -- sized to the
  logo's 2 MiB upload limit -- while a cover accepts 5 MiB, so an
  implementation that omitted ``max_bytes`` would answer 200 on upload and 404
  forever after for every cover above 2 MiB, for every resident. Two size cases
  bracket the ceiling and one spy pins its *reference*.
* **It carries a rate limit of its own**, ``300/minute``, asserted
  **structurally**: ``tests/conftest.py`` sets ``app.state.limiter.enabled =
  False`` suite-wide, so a case firing 301 requests and expecting a 429 would
  assert nothing at all.
"""

import base64
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.limiter import limiter
from app.models.project import ConstructionProject
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
from app.services import media_service
from app.services import project_service as project_service_module
from app.services.storage_service import BaseStorageProvider, LocalStorageProvider

#: A real, Pillow-decodable 1x1 PNG, small enough to compare byte for byte.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
    "IQAAAABJRU5ErkJggg=="
)

#: A second payload, distinguishable from the first **by value**: the
#: cross-tenant case asserts these bytes are absent from the response body, and
#: an assertion on bytes that also appear elsewhere could pass by luck.
OTHER_TENANT_BYTES = b"\x89PNG\r\n\x1a\nSEGREDO-DO-OUTRO-CONDOMINIO" + b"\x00" * 64


def _url(slug: str, project_id) -> str:
    return f"/api/v1/public/tenants/{slug}/projects/{project_id}/cover"


@pytest.fixture(name="uploads")
def uploads_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A **real** ``LocalStorageProvider`` rooted in ``tmp_path``.

    Real and not a double: the prefix rule and the containment check under test
    are the production ones, and the over-ceiling case below is load-bearing
    *because* this provider applies no implicit ceiling of its own.
    """
    monkeypatch.setattr(
        project_service_module, "_storage_provider", LocalStorageProvider(tmp_path)
    )
    return tmp_path


def _store(uploads: Path, name: str, payload: bytes) -> str:
    """Write an object under the provider's own prefix and return its URL."""
    target = uploads / "2026" / "09" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return f"/static/uploads/2026/09/{name}"


def _tenant(session: Session, **kwargs) -> Tenant:
    kwargs.setdefault("id", uuid.uuid4())
    kwargs.setdefault("name", f"Condomínio {uuid.uuid4().hex[:8]}")
    tenant = Tenant(**kwargs)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def _project(session: Session, **kwargs) -> ConstructionProject:
    kwargs.setdefault("title", "Modernização das Portarias")
    kwargs.setdefault("tenant_id", DEFAULT_TENANT_ID)
    project = ConstructionProject(**kwargs)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _default_tenant(session: Session) -> Tenant:
    return session.get(Tenant, DEFAULT_TENANT_ID)


# ---------------------------------------------------------------------------
# The 200
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("capa.png", "image/png"),
        ("capa.jpg", "image/jpeg"),
        ("capa.webp", "image/webp"),
    ],
)
def test_the_cover_is_served_to_an_unauthenticated_caller_as_bytes(
    client: TestClient,
    session: Session,
    uploads: Path,
    name: str,
    content_type: str,
):
    """ER3's 200: the bytes that were stored, and the image type those bytes
    are -- never the upstream Blob URL and never the store token."""
    tenant = _default_tenant(session)
    stored = _store(uploads, name, PNG_BYTES)
    project = _project(session, cover_photo_url=stored)

    response = client.get(_url(tenant.slug, project.id))

    assert response.status_code == 200
    assert response.content == PNG_BYTES
    assert response.headers["content-type"] == content_type
    # Asserted on the request the client just made, so "unauthenticated" is not
    # merely an absence in the source.
    assert "Authorization" not in response.request.headers
    assert "X-Tenant-Id" not in response.request.headers
    # The route answers bytes, never the stored value.
    assert stored.encode() not in response.content


def test_the_route_sets_no_cache_control_and_no_etag(
    client: TestClient, session: Session, uploads: Path
):
    """The one thing this route does take from the report route (§B). Out of
    scope here and owned by **APRAS-93**, like the report's own policy."""
    tenant = _default_tenant(session)
    project = _project(session, cover_photo_url=_store(uploads, "capa.png", PNG_BYTES))

    headers = client.get(_url(tenant.slug, project.id)).headers

    assert "cache-control" not in headers
    assert "etag" not in headers


# ---------------------------------------------------------------------------
# ER3 -- five conditions, five tests, `status_code == 404` every time
# ---------------------------------------------------------------------------


def test_an_unknown_slug_is_404(client: TestClient, session: Session, uploads: Path):
    project = _project(session, cover_photo_url=_store(uploads, "capa.png", PNG_BYTES))

    assert client.get(_url("nao-existe", project.id)).status_code == 404


def test_an_inactive_condominium_is_404(
    client: TestClient, session: Session, uploads: Path
):
    """Matching the report and logo routes: ``deps._resolve_from_header``
    refuses an inactive tenant to *everyone*, so publishing one here would
    advertise a door that is nailed shut."""
    tenant = _default_tenant(session)
    tenant.is_active = False
    session.add(tenant)
    session.commit()
    project = _project(session, cover_photo_url=_store(uploads, "capa.png", PNG_BYTES))

    assert client.get(_url(tenant.slug, project.id)).status_code == 404


def test_a_project_belonging_to_another_condominium_is_404_with_no_bytes(
    tenant_client: TestClient,
    session: Session,
    raw_session: Session,
    uploads: Path,
    tenant_b: Tenant,
):
    """ER3's cross-tenant case, and the only one that also asserts a body.

    A 404 over a leaked payload is still a leak, so the other condominium's
    bytes are asserted **absent** from the response rather than only the status
    being asserted present.

    It runs on ``tenant_client``, which gives every request its own
    ``Session``: ``Session.get()`` can answer from the identity map without
    emitting a query at all, and a project seeded into the *request* session
    would then never exercise ``tenant_context``'s loader criteria -- the very
    thing that makes this a 404.
    """
    stored = _store(uploads, "capa-do-outro.png", OTHER_TENANT_BYTES)
    project = ConstructionProject(
        title="Obra do outro condomínio",
        tenant_id=tenant_b.id,
        cover_photo_url=stored,
    )
    raw_session.add(project)
    raw_session.commit()
    raw_session.refresh(project)
    tenant_a = session.get(Tenant, DEFAULT_TENANT_ID)
    session.expunge_all()

    response = tenant_client.get(_url(tenant_a.slug, project.id))

    assert response.status_code == 404
    assert OTHER_TENANT_BYTES not in response.content


def test_a_project_with_no_cover_photo_is_404(
    client: TestClient, session: Session, uploads: Path
):
    tenant = _default_tenant(session)
    project = _project(session, cover_photo_url=None)

    assert client.get(_url(tenant.slug, project.id)).status_code == 404


def test_a_value_the_provider_owns_but_cannot_read_is_404(
    client: TestClient, session: Session, uploads: Path
):
    """No fake and no patch: the column names a file under the provider's
    **own** ``url_prefix`` that was never written, so ``resolve_stored_path``
    resolves it and the read then fails. A storage failure is deliberately not
    a 5xx."""
    tenant = _default_tenant(session)
    project = _project(
        session, cover_photo_url="/static/uploads/2026/09/nunca-gravada.png"
    )

    assert client.get(_url(tenant.slug, project.id)).status_code == 404


def test_a_third_party_stored_value_is_404_and_is_never_forwarded(
    client: TestClient, session: Session, uploads: Path
):
    """A value the provider does not own. No open redirect is introduced: this
    route never forwards to a foreign host, it 404s (§A.2)."""
    tenant = _default_tenant(session)
    project = _project(session, cover_photo_url="https://cdn.example/capa.jpg")

    response = client.get(_url(tenant.slug, project.id))

    assert response.status_code == 404
    assert "location" not in response.headers


# ---------------------------------------------------------------------------
# ER4 -- the read ceiling, bracketed against `media_service.MAX_FILE_SIZE`
# ---------------------------------------------------------------------------


def test_a_cover_of_exactly_the_upload_ceiling_is_served_in_full(
    client: TestClient, session: Session, uploads: Path
):
    """The lower bracket. It fails if the ceiling is **too small** -- a retyped
    ``2 * 1024 * 1024`` makes ``read_file`` answer ``None`` for this object and
    the route answers 404 instead of these bytes.

    Pinned against ``media_service.MAX_FILE_SIZE`` itself and never a retyped
    literal.
    """
    payload = b"\x00" * media_service.MAX_FILE_SIZE
    tenant = _default_tenant(session)
    project = _project(session, cover_photo_url=_store(uploads, "capa.png", payload))

    response = client.get(_url(tenant.slug, project.id))

    assert response.status_code == 200
    assert len(response.content) == media_service.MAX_FILE_SIZE
    assert response.content == payload


def test_a_cover_one_byte_over_the_upload_ceiling_is_404(
    client: TestClient, session: Session, uploads: Path
):
    """The load-bearing case, and load-bearing **on the local provider**.

    ``LocalStorageProvider.read_file`` returns ``path.read_bytes()`` -- the
    whole file, no bound at all -- when ``max_bytes is None``
    (``storage_service.py:334-335``, under a docstring paragraph headed "No
    implicit ceiling"). So an implementation that omits the keyword reads this
    object in full and serves it **200**, and this assertion goes red in CI
    with no Blob store involved. That is the omission the whole decision exists
    to prevent.
    """
    payload = b"\x00" * (media_service.MAX_FILE_SIZE + 1)
    tenant = _default_tenant(session)
    project = _project(session, cover_photo_url=_store(uploads, "capa.png", payload))

    assert client.get(_url(tenant.slug, project.id)).status_code == 404


def test_the_read_states_the_upload_ceiling_by_reference(
    client: TestClient,
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
    uploads: Path,
):
    """The spy, whose value is **narrow** and worth stating as such.

    The two size cases above already catch every wrong *number*, in both
    directions, so this catches neither an omitted argument nor a wrong
    ceiling.

    It does **not** catch a retyped-but-equal literal either, and an earlier
    version of this docstring claimed it did. ``==`` between two equal ints is
    true whichever way each was spelled, so writing ``5 * 1024 * 1024`` in place
    of the constant leaves every test here green. That claim was false and is
    the shape this repository has already paid for eleven times: a test whose
    comment names coverage it does not have stops the next reader looking.

    What it actually buys is **deferred** drift protection. The literal and the
    constant agree today, so nothing fires today; the assertion fires on the day
    ``media_service.MAX_FILE_SIZE`` moves and the stranded literal stops matching
    it. That is worth one line -- the route's ceiling follows the upload limit
    instead of silently parting from it -- and it is worth exactly that, no more.

    The comparison is ``==``. Never ``is``: on an ``int`` above 256 that relies
    on CPython interning a folded constant, which is not a property to build an
    assertion on.
    """
    calls: list[dict[str, Any]] = []

    class SpyProvider(BaseStorageProvider):
        def save_file(self, file_bytes, filename, content_type, *, tenant_id=None):
            raise AssertionError("the public read route must not write")

        def delete_file(self, file_path):
            raise AssertionError("the public read route must not delete")

        def resolve_stored_path(self, url):
            return url

        def read_file(self, url, *, max_bytes=None):
            calls.append({"url": url, "max_bytes": max_bytes})
            return PNG_BYTES

    monkeypatch.setattr(project_service_module, "_storage_provider", SpyProvider())
    tenant = _default_tenant(session)
    project = _project(session, cover_photo_url="/static/uploads/2026/09/capa.png")

    assert client.get(_url(tenant.slug, project.id)).status_code == 200

    assert len(calls) == 1
    assert calls[0]["max_bytes"] == media_service.MAX_FILE_SIZE


# ---------------------------------------------------------------------------
# ER11 -- the rate limit, read out of slowapi's own registry
# ---------------------------------------------------------------------------


def test_the_route_is_decorated_with_a_three_hundred_per_minute_limit():
    """Structural, deliberately, and for a mechanism this file names.

    ``tests/conftest.py:24`` sets ``app.state.limiter.enabled = False`` for the
    whole suite, so a case that fires 301 requests and expects a 429 passes
    while asserting nothing -- this project has shipped exactly that vacuous
    test once. This reads slowapi's registry, which is keyed by the handler's
    qualified name, exactly as
    ``test_public_logo_route.py::test_the_route_is_decorated_with_a_thirty_per_minute_limit``
    does.

    The number is **page-view parity** with the logo route's 30/minute rather
    than request parity: 30/min is 30 views/min at one fetch per view, and
    300/min is 25 views/min at twelve covers per view. The arithmetic is 12
    obras x 20 views/min (one NAT'd condominium office, ~10 readers, two loads
    each) = 240, rounded up to the next round number. Copying the logo's 30
    would exhaust on the **third** page view of a twelve-obra report.
    """
    from app.api.v1.endpoints import public_projects

    key = (
        f"{public_projects.__name__}."
        f"{public_projects.get_public_project_cover.__name__}"
    )

    assert key in limiter._route_limits
    limits = [str(item.limit) for item in limiter._route_limits[key]]
    assert limits == ["300 per 1 minute"]

    # APRAS-92 D3, provably untouched rather than promised: the report handler
    # acquires no limit as a side effect of this registration. **APRAS-93**
    # owns any revisit there.
    report_key = (
        f"{public_projects.__name__}."
        f"{public_projects.get_public_projects_report.__name__}"
    )
    assert report_key not in limiter._route_limits


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("capa.svg", id="active-content"),
        pytest.param("capa.bin", id="untyped-suffix"),
        pytest.param("capa.pdf", id="not-an-image"),
    ],
)
def test_a_suffix_outside_the_accepted_image_types_is_404(
    client: TestClient, session: Session, uploads: Path, name: str
):
    """``image/svg+xml`` is active content -- script, ``foreignObject``,
    external references -- and is deliberately out of
    ``media_service.ALLOWED_MIME_TYPES`` for APRAS-61 D2's reason: the report a
    browser renders embeds this image. The route must not publish one, even
    though the object is really there under the provider's own prefix."""
    tenant = _default_tenant(session)
    project = _project(session, cover_photo_url=_store(uploads, name, PNG_BYTES))

    assert client.get(_url(tenant.slug, project.id)).status_code == 404
