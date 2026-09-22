"""The public condominium branding read (APRAS-74).

``GET /api/v1/public/tenants/{slug}/branding`` is the only unauthenticated,
tenant-shaped read in the product. Three properties carry it, and each one is
asserted here rather than assumed:

* **Four keys, asserted as an equality.** A future field added to
  ``Tenant`` or to a sibling schema must not be able to leak onto a route
  nobody authenticates.
* **The theme is APRAS-68's, not a second derivation.** The handler calls
  ``app.core.branding.build_theme`` and passes the result through verbatim;
  ``test_the_router_derives_no_colour_of_its_own`` proves by AST that the
  module contains no colour arithmetic of its own.
* **Existence is public, but not free.** Slug enumeration is accepted (D3)
  and the single mitigation is the per-IP rate limit, so the 31st request
  inside a minute is asserted to be a 429.
"""

import ast
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.branding import build_theme
from app.core.permissions import UNGUARDED_ROUTES
from app.main import app
from app.models.tenant import Tenant
from app.services.tenant_service import TenantService

#: The route, spelled exactly as FastAPI mounts it.
ROUTE = ("GET", "/api/v1/public/tenants/{slug}/branding")

#: The whole body, asserted as a set so a new field cannot slip in.
EXPECTED_KEYS = {"slug", "name", "logo_url", "theme"}

#: A valid simple-mode branding object, in the shape
#: ``PATCH /api/v1/tenant-profile`` stores.
BRAND_THEME = {"mode": "simple", "primary": "#ffe680", "accent": "#0ea5e9"}

ROUTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "api"
    / "v1"
    / "endpoints"
    / "public_branding.py"
)


def _url(slug: str) -> str:
    return f"/api/v1/public/tenants/{slug}/branding"


def _tenant(session: Session, **kwargs) -> Tenant:
    """A tenant carrying a distinct name, so its slug is derived and unique."""
    kwargs.setdefault("id", uuid.uuid4())
    kwargs.setdefault("name", f"Condomínio {uuid.uuid4().hex[:8]}")
    tenant = Tenant(**kwargs)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


# ---------------------------------------------------------------------------
# The 200
# ---------------------------------------------------------------------------


def test_an_existing_slug_answers_200_with_no_credential_of_any_kind(
    client: TestClient, session: Session
):
    """ER-1: no ``Authorization`` header and no ``X-Tenant-Id`` header."""
    tenant = _tenant(session, name="Condomínio Altos da Serra")

    response = client.get(_url(tenant.slug))

    assert response.status_code == 200
    assert response.json()["slug"] == "condominio-altos-da-serra"
    # Stated as an assertion on the request the client just made, so the
    # "unauthenticated" claim is not merely an absence in the source above.
    assert "Authorization" not in response.request.headers
    assert "X-Tenant-Id" not in response.request.headers


def test_the_body_carries_exactly_four_keys(client: TestClient, session: Session):
    """ER-2: an equality, so no further field can leak in later."""
    tenant = _tenant(
        session,
        name="Residencial Vila das Flores",
        logo_url="/static/uploads/vila.png",
        brand_theme=dict(BRAND_THEME),
    )

    body = client.get(_url(tenant.slug)).json()

    assert set(body) == EXPECTED_KEYS
    assert body["name"] == "Residencial Vila das Flores"
    assert body["logo_url"] == "/static/uploads/vila.png"


@pytest.mark.parametrize(
    "leaked",
    ["id", "tenant_id", "is_active", "disabled_modules", "plan", "brand_theme"],
)
def test_no_operator_field_reaches_the_public_body(
    client: TestClient, session: Session, leaked: str
):
    tenant = _tenant(session, brand_theme=dict(BRAND_THEME))

    assert leaked not in client.get(_url(tenant.slug)).json()


# ---------------------------------------------------------------------------
# The theme is APRAS-68's, consumed and not redefined
# ---------------------------------------------------------------------------


def test_theme_is_null_for_a_condominium_with_no_colours(
    client: TestClient, session: Session
):
    """ER-3: the other three fields are still populated."""
    tenant = _tenant(session, name="Condomínio Sem Cores", logo_url=None)

    body = client.get(_url(tenant.slug)).json()

    assert body == {
        "slug": "condominio-sem-cores",
        "name": "Condomínio Sem Cores",
        "logo_url": None,
        "theme": None,
    }


def test_theme_is_the_branding_modules_own_derivation(
    client: TestClient, session: Session
):
    """Passed through verbatim: asserted against ``build_theme`` itself.

    The *shape* of the value is deliberately not asserted here -- APRAS-68
    owns it and may change it (simple vs. advanced modes) without touching
    this module.
    """
    tenant = _tenant(session, brand_theme=dict(BRAND_THEME))

    theme = client.get(_url(tenant.slug)).json()["theme"]

    assert theme is not None
    assert theme == build_theme(dict(BRAND_THEME))


def test_the_router_derives_no_colour_of_its_own():
    """ER-3: one derivation in the repository, and it is not in this file.

    An AST walk rather than a text scan, so the module docstring may name
    the concepts freely while the *code* is held to a single call.
    """
    tree = ast.parse(ROUTER_PATH.read_text(encoding="utf-8"))
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } | {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden = {
        "hex_to_oklch",
        "oklch_to_linear_srgb",
        "audit_contrast",
        "relative_luminance",
        "contrast_ratio",
        "normalize_hex_color",
    }
    assert not (called & forbidden), sorted(called & forbidden)
    assert "build_theme" in called, "the router must consume APRAS-68's builder"


# ---------------------------------------------------------------------------
# The 404s
# ---------------------------------------------------------------------------


def test_an_unknown_slug_is_404_with_the_ordinary_error_body(client: TestClient):
    """ER-4: no special casing and no uniform response."""
    response = client.get(_url("condominio-inexistente"))

    assert response.status_code == 404
    assert set(response.json()) == {"detail"}
    assert isinstance(response.json()["detail"], str)


def test_an_inactive_condominium_is_404_as_well(client: TestClient, session: Session):
    """``deps._resolve_from_header`` refuses an inactive tenant to everyone,
    so a branded login into it could never succeed; answering 200 would
    advertise a door that is nailed shut."""
    tenant = _tenant(session, name="Condomínio Desativado", is_active=False)

    assert client.get(_url(tenant.slug)).status_code == 404


def test_the_slug_match_is_exact(client: TestClient, session: Session):
    tenant = _tenant(session, name="Condomínio Altos")

    assert client.get(_url(tenant.slug.upper())).status_code == 404
    assert client.get(_url(f"{tenant.slug}-2")).status_code == 404


# ---------------------------------------------------------------------------
# The rate limit (D3's single mitigation)
# ---------------------------------------------------------------------------


def test_the_thirty_first_request_inside_a_minute_is_429(
    client: TestClient, session: Session
):
    """ER-5: `@limiter.limit("30/minute")`, through the existing handler.

    `tests/conftest.py` disables the limiter for the whole suite, so the
    case re-enables it around itself and restores the flag in a `finally`,
    exactly as `tests/test_rate_limit.py` does. The storage is reset on both
    sides so the case is order-independent.
    """
    tenant = _tenant(session, name="Condomínio Enumerável")
    app.state.limiter.reset()
    app.state.limiter.enabled = True
    try:
        for _ in range(30):
            assert client.get(_url(tenant.slug)).status_code == 200

        response = client.get(_url(tenant.slug))
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
    finally:
        app.state.limiter.enabled = False
        app.state.limiter.reset()


# ---------------------------------------------------------------------------
# The registries
# ---------------------------------------------------------------------------


def test_the_route_is_unguarded_and_carries_the_public_tag():
    """ER-6: mapped to no catalogue permission, and visible as public."""
    assert ROUTE in UNGUARDED_ROUTES

    route = next(
        r
        for r in app.routes
        if getattr(r, "path", None) == ROUTE[1]
        and "GET" in getattr(r, "methods", set())
    )
    assert route.tags == ["public"]


# ---------------------------------------------------------------------------
# The service lookup
# ---------------------------------------------------------------------------


def test_get_by_slug_returns_the_row_or_none(session: Session):
    tenant = _tenant(session, name="Condomínio Buscável")

    assert TenantService.get_by_slug(session, tenant.slug) is not None
    assert TenantService.get_by_slug(session, tenant.slug).id == tenant.id
    assert TenantService.get_by_slug(session, "nao-existe") is None
