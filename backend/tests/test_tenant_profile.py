"""The condominium profile surface (APRAS-61).

One tenant-side router, `/api/v1/tenant-profile`, with **no `{tenant_id}` in
any path**: the subject is always the acting tenant, resolved from
`X-Tenant-Id` by `deps.get_current_tenant`. A path parameter would be a
second, forgeable source of truth and would hand a tenant_admin of A a way to
name B -- the same argument `endpoints/subscription.py` already carries, and
the reason this router exists beside the superuser `/tenants/{id}` block
instead of inside it.

The three writes are guarded by `tenants:profile_update`, an ordinary,
grantable permission. An `is_tenant_admin` member reaches them with **no
special case in any handler**: APRAS-47's whole-catalogue short-circuit plus
`tenants` being a core module, so APRAS-39's strip can never remove it.
"""

import io
import itertools
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session

from app.core.permissions import ROUTE_PERMISSIONS, UNGUARDED_ROUTES
from app.core.security import create_access_token, get_password_hash
from app.models.project import ConstructionProject
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.services import tenant_service as tenant_service_module
from app.services.storage_service import LocalStorageProvider
from app.services.tenant_service import TenantService
from tests.conftest import make_user

PROFILE_URL = "/api/v1/tenant-profile"
LOGO_URL = "/api/v1/tenant-profile/logo"
REPORT_URL = "/api/v1/projects/report"
PERMISSION = "tenants:profile_update"

#: The frontend half of the two-sided pin, named in every failure message so a
#: red run points at the file that has to move with it.
_FRONTEND_CLIENT = "frontend/src/api/tenantProfile.ts"

_SERIAL = itertools.count(1)


def _cpf(serial: int) -> str:
    """A check-digit-valid CPF, derived: `user.cpf` is globally unique and a
    hand-written list runs out the moment a case adds one more caller."""
    base = f"{serial:09d}"
    digits = [int(c) for c in base]
    for weights in (range(10, 1, -1), range(11, 1, -1)):
        total = sum(d * w for d, w in zip(digits, weights, strict=True))
        check = (total * 10) % 11
        digits.append(0 if check == 10 else check)
    return "".join(str(d) for d in digits)


def _auth(user: User, tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


def _member(
    session: Session,
    *,
    permissions: list[str],
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    is_tenant_admin: bool = False,
) -> User:
    """A plain member whose whole authority is `permissions`.

    Never one of the six legacy profile rows: this task mints a **new**
    catalogue string, and nothing seeds it into any bundle, so the caller's
    authority has to be exactly what the case grants.
    """
    role = Role(
        name=f"Papel {uuid.uuid4().hex[:8]}",
        tenant_id=tenant_id,
        permissions=list(permissions),
    )
    session.add(role)
    session.commit()
    session.refresh(role)

    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@profile.example.com",
        full_name="Perfil Caller",
        hashed_password=get_password_hash("password123"),
        profile="GUEST",
        tenant_id=tenant_id,
        cpf=_cpf(next(_SERIAL)),
        is_superuser=False,
        roles=[role],
    )
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=tenant_id, is_tenant_admin=is_tenant_admin
        )
    )
    session.commit()
    return user


def _png(size: tuple[int, int] = (4, 4), colour: str = "#082f2a") -> bytes:
    """A real, Pillow-decodable PNG — the bytes the route is meant to accept."""
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(
    client: TestClient,
    user: User,
    *,
    content: bytes,
    filename: str = "logo.png",
    content_type: str = "image/png",
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
):
    return client.put(
        LOGO_URL,
        files={"file": (filename, content, content_type)},
        headers=_auth(user, tenant_id),
    )


def _logo_of(session: Session, tenant_id: uuid.UUID) -> str | None:
    session.expire_all()
    tenant = session.get(Tenant, tenant_id)
    return tenant.logo_url


@pytest.fixture(name="storage")
def storage_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point the service's module-level provider at a temporary directory.

    A real `LocalStorageProvider`, not a stub: the "the previous file no
    longer exists on disk" claim is only worth something when a file was
    really written, and the production provider is the thing under test.
    """
    provider = LocalStorageProvider(tmp_path / "uploads")
    monkeypatch.setattr(tenant_service_module, "_storage_provider", provider)
    return provider


def _stored_path(provider: LocalStorageProvider, url: str) -> Path:
    return provider.base_dir / url.removeprefix("/static/uploads/")


# ---------------------------------------------------------------------------
# The read (D6): authenticated, self-scoped, unguarded
# ---------------------------------------------------------------------------


def test_get_answers_the_acting_tenants_profile(
    tenant_client: TestClient, session: Session
):
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant.logo_url = "/static/uploads/2026/09/seed.png"
    session.add(tenant)
    session.commit()
    caller = _member(session, permissions=[])

    response = tenant_client.get(PROFILE_URL, headers=_auth(caller, DEFAULT_TENANT_ID))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(DEFAULT_TENANT_ID)
    assert body["name"] == tenant.name
    assert body["is_active"] is True
    assert body["logo_url"] == "/static/uploads/2026/09/seed.png"


def test_the_read_is_on_the_unguarded_allowlist_and_the_writes_are_not():
    """D6, stated against the registry rather than against a docstring."""
    assert ("GET", PROFILE_URL) in UNGUARDED_ROUTES
    assert ("GET", PROFILE_URL) not in ROUTE_PERMISSIONS
    for key in (
        ("PATCH", PROFILE_URL),
        ("PUT", LOGO_URL),
        ("DELETE", LOGO_URL),
    ):
        assert ROUTE_PERMISSIONS[key] == PERMISSION
        assert key not in UNGUARDED_ROUTES


# ---------------------------------------------------------------------------
# The rename (PATCH)
# ---------------------------------------------------------------------------


def test_a_holder_renames_the_acting_tenant(
    tenant_client: TestClient, session: Session
):
    caller = _member(session, permissions=[PERMISSION])

    response = tenant_client.patch(
        PROFILE_URL,
        json={"name": "Residencial Altos da Serra VI"},
        headers=_auth(caller, DEFAULT_TENANT_ID),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Residencial Altos da Serra VI"
    session.expire_all()
    assert (
        session.get(Tenant, DEFAULT_TENANT_ID).name == "Residencial Altos da Serra VI"
    )


def test_a_name_another_tenant_already_holds_is_409(
    tenant_client: TestClient, session: Session, tenant_b: Tenant
):
    caller = _member(session, permissions=[PERMISSION])
    before = session.get(Tenant, DEFAULT_TENANT_ID).name

    response = tenant_client.patch(
        PROFILE_URL,
        json={"name": tenant_b.name},
        headers=_auth(caller, DEFAULT_TENANT_ID),
    )

    assert response.status_code == 409
    session.expire_all()
    assert session.get(Tenant, DEFAULT_TENANT_ID).name == before


@pytest.mark.parametrize("name", ["", "x" * 121])
def test_an_empty_or_over_long_name_is_422(
    tenant_client: TestClient, session: Session, name: str
):
    caller = _member(session, permissions=[PERMISSION])

    response = tenant_client.patch(
        PROFILE_URL, json={"name": name}, headers=_auth(caller, DEFAULT_TENANT_ID)
    )

    assert response.status_code == 422


def test_is_active_is_not_writable_here(tenant_client: TestClient, session: Session):
    """Deactivating a condominium stays a superuser act on `/tenants/{id}`."""
    caller = _member(session, permissions=[PERMISSION])

    response = tenant_client.patch(
        PROFILE_URL,
        json={"name": "Ainda Ativo", "is_active": False},
        headers=_auth(caller, DEFAULT_TENANT_ID),
    )

    assert response.status_code == 200
    session.expire_all()
    assert session.get(Tenant, DEFAULT_TENANT_ID).is_active is True


# ---------------------------------------------------------------------------
# The logo upload (PUT)
# ---------------------------------------------------------------------------


def test_uploading_a_png_stores_the_bytes_and_sets_the_column(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    caller = _member(session, permissions=[PERMISSION])
    content = _png()

    response = _upload(tenant_client, caller, content=content)

    assert response.status_code == 200
    url = response.json()["logo_url"]
    assert url.startswith("/static/uploads/")
    assert _logo_of(session, DEFAULT_TENANT_ID) == url
    stored = _stored_path(storage, url)
    assert stored.exists()
    assert stored.read_bytes() == content


@pytest.mark.parametrize(
    ("filename", "mime", "image_format"),
    [
        ("logo.jpg", "image/jpeg", "JPEG"),
        ("logo.webp", "image/webp", "WEBP"),
    ],
)
def test_the_other_two_accepted_types_are_also_stored(
    tenant_client: TestClient,
    session: Session,
    storage: LocalStorageProvider,
    filename: str,
    mime: str,
    image_format: str,
):
    caller = _member(session, permissions=[PERMISSION])
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "#c6a04a").save(buffer, format=image_format)

    response = _upload(
        tenant_client,
        caller,
        content=buffer.getvalue(),
        filename=filename,
        content_type=mime,
    )

    assert response.status_code == 200
    assert _stored_path(storage, response.json()["logo_url"]).exists()


def test_a_second_upload_replaces_the_file_and_the_column(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    caller = _member(session, permissions=[PERMISSION])
    first = _upload(tenant_client, caller, content=_png()).json()["logo_url"]
    first_path = _stored_path(storage, first)
    assert first_path.exists()

    second = _upload(
        tenant_client, caller, content=_png(size=(8, 8), colour="#9b7327")
    ).json()["logo_url"]

    assert second != first
    assert _logo_of(session, DEFAULT_TENANT_ID) == second
    assert _stored_path(storage, second).exists()
    assert not first_path.exists()


def test_an_externally_hosted_previous_url_is_left_alone(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    """Only a `/static/uploads/` value maps back to a file we own."""
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant.logo_url = "https://cdn.example/logo-alheio.png"
    session.add(tenant)
    session.commit()
    caller = _member(session, permissions=[PERMISSION])

    response = _upload(tenant_client, caller, content=_png())

    assert response.status_code == 200
    assert response.json()["logo_url"].startswith("/static/uploads/")


@pytest.mark.parametrize(
    ("filename", "mime"),
    [
        ("brasao.svg", "image/svg+xml"),
        ("notas.txt", "text/plain"),
        ("logo.gif", "image/gif"),
    ],
)
def test_an_unsupported_type_is_422_and_writes_nothing(
    tenant_client: TestClient,
    session: Session,
    storage: LocalStorageProvider,
    filename: str,
    mime: str,
):
    caller = _member(session, permissions=[PERMISSION])

    response = _upload(
        tenant_client, caller, content=_png(), filename=filename, content_type=mime
    )

    assert response.status_code == 422
    assert _logo_of(session, DEFAULT_TENANT_ID) is None
    assert not list(storage.base_dir.rglob("*")) or not any(
        path.is_file() for path in storage.base_dir.rglob("*")
    )


def test_a_file_over_the_cap_is_422_and_writes_nothing(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    caller = _member(session, permissions=[PERMISSION])
    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (3 * 1024 * 1024)

    response = _upload(tenant_client, caller, content=oversized)

    assert response.status_code == 422
    assert _logo_of(session, DEFAULT_TENANT_ID) is None
    assert not any(path.is_file() for path in storage.base_dir.rglob("*"))


def test_an_undecodable_body_with_an_accepted_type_is_422(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    """D3: the declared MIME type is a claim, Pillow is the check."""
    caller = _member(session, permissions=[PERMISSION])

    response = _upload(tenant_client, caller, content=b"not-an-image-at-all")

    assert response.status_code == 422
    assert _logo_of(session, DEFAULT_TENANT_ID) is None
    assert not any(path.is_file() for path in storage.base_dir.rglob("*"))


def test_a_refused_upload_leaves_an_existing_logo_untouched(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    caller = _member(session, permissions=[PERMISSION])
    good = _upload(tenant_client, caller, content=_png()).json()["logo_url"]

    refused = _upload(
        tenant_client,
        caller,
        content=b"broken",
        filename="x.svg",
        content_type="image/svg+xml",
    )

    assert refused.status_code == 422
    assert _logo_of(session, DEFAULT_TENANT_ID) == good
    assert _stored_path(storage, good).exists()


def test_a_provider_without_a_base_dir_skips_the_delete_instead_of_raising(
    tenant_client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """The non-local branch of ``_delete_stored_logo``, exercised rather than
    assumed.

    A `/static/uploads/` value can only have come from a
    ``LocalStorageProvider``, but the provider bound *now* may be a different
    one (the parity harness swaps in a stub; a future task may swap in S3).
    With no ``base_dir`` there is no path to map back to, and the replacement
    must still succeed: the previous file is the old provider's problem, not a
    reason to refuse the upload.
    """

    class _NoBaseDirStorage:
        def save_file(self, file_bytes, filename, content_type):
            return f"/dev/null/{filename}", f"http://null/{filename}"

        def delete_file(self, file_path):  # pragma: no cover - never reached
            raise AssertionError("a provider with no base_dir must not be asked")

    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant.logo_url = "/static/uploads/2026/09/antigo.png"
    session.add(tenant)
    session.commit()
    caller = _member(session, permissions=[PERMISSION])
    monkeypatch.setattr(tenant_service_module, "_storage_provider", _NoBaseDirStorage())

    response = _upload(tenant_client, caller, content=_png())

    assert response.status_code == 200
    assert _logo_of(session, DEFAULT_TENANT_ID) == "http://null/logo.png"


# ---------------------------------------------------------------------------
# The logo removal (DELETE)
# ---------------------------------------------------------------------------


def test_delete_clears_the_column_removes_the_file_and_is_idempotent(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    caller = _member(session, permissions=[PERMISSION])
    url = _upload(tenant_client, caller, content=_png()).json()["logo_url"]
    stored = _stored_path(storage, url)

    first = tenant_client.delete(LOGO_URL, headers=_auth(caller, DEFAULT_TENANT_ID))

    assert first.status_code == 200
    assert first.json()["logo_url"] is None
    assert _logo_of(session, DEFAULT_TENANT_ID) is None
    assert not stored.exists()

    second = tenant_client.delete(LOGO_URL, headers=_auth(caller, DEFAULT_TENANT_ID))

    assert second.status_code == 200
    assert second.json()["logo_url"] is None


# ---------------------------------------------------------------------------
# The guard (D6, D7)
# ---------------------------------------------------------------------------


def test_a_non_holder_is_403_on_all_three_writes(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    caller = _member(session, permissions=["tenants:read", "tenants:update"])
    headers = _auth(caller, DEFAULT_TENANT_ID)

    assert (
        tenant_client.patch(PROFILE_URL, json={"name": "Novo"}, headers=headers)
    ).status_code == 403
    assert _upload(tenant_client, caller, content=_png()).status_code == 403
    assert tenant_client.delete(LOGO_URL, headers=headers).status_code == 403
    assert _logo_of(session, DEFAULT_TENANT_ID) is None


def test_a_tenant_admin_with_no_role_permissions_reaches_all_three_writes(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    """D7: the whole-catalogue short-circuit, with no special case in any
    handler. `tenants` is core, so APRAS-39's strip can never remove it."""
    caller = _member(session, permissions=[], is_tenant_admin=True)
    headers = _auth(caller, DEFAULT_TENANT_ID)

    assert (
        tenant_client.patch(
            PROFILE_URL, json={"name": "Condomínio do Síndico"}, headers=headers
        )
    ).status_code == 200
    assert _upload(tenant_client, caller, content=_png()).status_code == 200
    assert tenant_client.delete(LOGO_URL, headers=headers).status_code == 200


def test_a_member_of_b_acting_as_a_is_403_and_as_logo_is_unchanged(
    tenant_client: TestClient,
    session: Session,
    tenant_b: Tenant,
    storage: LocalStorageProvider,
):
    """ER-4 comes for free: `deps._resolve_from_header` refuses the header
    before any handler runs, so there is nothing in a body or a path to
    forge."""
    tenant_a = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant_a.logo_url = "/static/uploads/2026/09/de-a.png"
    session.add(tenant_a)
    session.commit()
    outsider = _member(
        session, permissions=[PERMISSION], tenant_id=tenant_b.id, is_tenant_admin=True
    )

    response = _upload(tenant_client, outsider, content=_png())

    assert response.status_code == 403
    assert response.json()["detail"] == "Not a member of the requested tenant"
    assert _logo_of(session, DEFAULT_TENANT_ID) == "/static/uploads/2026/09/de-a.png"


def test_the_write_lands_only_on_the_acting_tenant(
    tenant_client: TestClient,
    session: Session,
    tenant_b: Tenant,
    storage: LocalStorageProvider,
):
    caller = _member(
        session, permissions=[PERMISSION], tenant_id=tenant_b.id, is_tenant_admin=True
    )

    response = _upload(tenant_client, caller, content=_png(), tenant_id=tenant_b.id)

    assert response.status_code == 200
    assert _logo_of(session, tenant_b.id) == response.json()["logo_url"]
    assert _logo_of(session, DEFAULT_TENANT_ID) is None


# ---------------------------------------------------------------------------
# The consequence: the works report, with no diff in its service
# ---------------------------------------------------------------------------


def test_the_report_masthead_renders_the_uploaded_logo(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    """ER-8. `project_report_service` already reads `tenant.logo_url`; this
    task only gives an operator a way to write it."""
    session.add(ConstructionProject(title="Obra com logo"))
    session.commit()
    caller = _member(session, permissions=[PERMISSION, "projects:read"])

    url = _upload(tenant_client, caller, content=_png()).json()["logo_url"]
    body = tenant_client.get(REPORT_URL, headers=_auth(caller, DEFAULT_TENANT_ID)).text

    assert f'<img src="{url}"' in body


# ---------------------------------------------------------------------------
# The two-sided pin with the frontend client
# ---------------------------------------------------------------------------


def test_the_profile_contract_matches_the_frontend_client():
    """The backend half of the pin `src/api/uploads.ts` established.

    Neither side can import the other, so each states the constant and names
    the other: changing the server without changing the client fails here, and
    changing the client without changing the server fails over there.
    """
    assert TenantService.LOGO_MAX_FILE_SIZE == 2 * 1024 * 1024, (
        "TenantService.LOGO_MAX_FILE_SIZE changed. "
        f"`TENANT_LOGO_MAX_FILE_SIZE_BYTES` in {_FRONTEND_CLIENT} pre-checks "
        "the file against this number and `tenantProfile.hint` interpolates "
        "it; update both."
    )
    assert {
        "image/jpeg",
        "image/png",
        "image/webp",
    } == TenantService.LOGO_ALLOWED_MIME_TYPES, (
        "TenantService.LOGO_ALLOWED_MIME_TYPES changed. "
        f"`TENANT_LOGO_ALLOWED_MIME_TYPES` in {_FRONTEND_CLIENT} feeds the "
        "`accept=` of the logo input and its client-side pre-check; update it."
    )
    assert ROUTE_PERMISSIONS[("PUT", LOGO_URL)] == PERMISSION, (
        f"the logo route's permission changed. `TENANT_PROFILE_PERMISSION` in "
        f"{_FRONTEND_CLIENT} is what `ROUTE_ACCESS['/admin/tenant-profile']` "
        "and the page's controls are gated on; update it."
    )
    assert LOGO_URL == "/api/v1/tenant-profile/logo", (
        f"the route path changed; {_FRONTEND_CLIENT} calls it as "
        "`/tenant-profile/logo` on the shared client."
    )


def test_svg_is_deliberately_outside_the_accepted_set():
    """D2, stated so a future author has to delete a case to accept SVG.

    An SVG is active content served same-origin from `/static/uploads/` and
    embedded in a printable report a browser renders: accepting it without a
    sanitiser is a stored-XSS surface, and a sanitiser is a task of its own.
    """
    assert "image/svg+xml" not in TenantService.LOGO_ALLOWED_MIME_TYPES


def test_a_hostile_logo_name_cannot_choose_the_stored_extension(
    tenant_client: TestClient, session: Session, storage: LocalStorageProvider
):
    """APRAS-65: valid PNG bytes offered as `payload.svg` are stored `.png`.

    `/static/uploads` is unauthenticated and its content type used to be
    guessed from this extension, so an `.svg` here was script execution in
    this origin.
    """
    response = _upload(
        tenant_client,
        _member(session, permissions=[PERMISSION]),
        content=_png(),
        filename="payload.svg",
        content_type="image/png",
    )

    assert response.status_code == 200
    url = response.json()["logo_url"]
    assert url.endswith(".png")
    stored = _stored_path(storage, url)
    assert stored.suffix == ".png"
    assert stored.exists()
    assert not list(storage.base_dir.rglob("*.svg"))
