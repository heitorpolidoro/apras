"""The public condominium branding read (APRAS-74 D2, D3).

Two routes. ``GET /api/v1/public/tenants/{slug}/branding`` is what makes
``/c/<slug>`` show the condominium's own name, logo and colours to somebody
who has not signed in yet, and ``GET /api/v1/public/tenants/{slug}/logo``
(APRAS-105) serves the logo's **bytes** at a URL of ours.

The second exists because the Blob store is configured with **private**
access, by an operator decision taken deliberately: with a public store the
exposed thing would be a permanent Vercel Blob URL outside the application,
which cannot be rate-limited, measured or revoked without deleting the object.
With a public route the exposed thing is a door we own, and every other object
in the store -- assembly minutes, generated reports -- stays unreachable
without our token. The logo is public either way, since ``/c/<slug>/obras`` is
already open on the internet (APRAS-92 D1) and the logo on that page is no more
private than the page carrying it.

It was the *only* unauthenticated tenant-shaped read in the product until
APRAS-92 added ``endpoints/public_projects.py``, the obras report behind
``/c/<slug>/obras``, on this same ``/public`` mount. The two differ in one way
worth knowing before reading either: that one carries **no** rate limit and
sets no ``Cache-Control``, by an operator decision taken twice (APRAS-92 D3).
The limiter below is this route's and is not shared. The logo route has
since gained a validator (APRAS-124, see its docstring); the branding route
is deliberately unchanged.

**Mounted ``GLOBAL_SCOPED``, never ``TENANT_SCOPED``.** The caller resolves no
acting tenant -- there is no ``Authorization`` header to resolve one *for*,
and no ``X-Tenant-Id`` is sent -- so ``deps.get_current_tenant`` would refuse
every request and the fail-closed guard of ``app.core.tenant_context`` would
fire. The tenant is named in the path and is the *subject* of the read, in
exactly the sense ``{tenant_id}`` is on ``/api/v1/tenants/{tenant_id}/modules``,
so there is nothing to forge: the four fields below are public by decision.

**Existence is not a secret** (D3). The branded login is a public page, slug
enumeration is accepted, and the single mitigation is the per-IP rate limit
below. That is also why an unknown slug is an ordinary 404 rather than a
uniform answer: this route *is* the thing that publishes existence, so
uniforming it would buy nothing and cost every client a real error.

**The theme is consumed, never redefined.** ``build_theme`` is APRAS-68's and
is the only colour derivation in the repository; this module calls it once
and passes the result through verbatim, asserting nothing about its shape.
``tests/test_public_branding.py::test_the_router_derives_no_colour_of_its_own``
holds that property by AST.

Both routes map to **no catalogue permission** -- they authenticate nobody, so
there is nobody to hold one -- and therefore join ``UNGUARDED_ROUTES``
alongside ``/auth/forgot-password`` and the two public invitation routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.core.branding import build_theme
from app.core.limiter import limiter
from app.db import get_session
from app.schemas.tenant import PublicTenantBrandingRead
from app.services.tenant_service import TenantService

router = APIRouter()


def _if_none_match_matches(header: str | None, etag: str) -> bool:
    """RFC 9110 weak comparison of an ``If-None-Match`` value against ``etag``.

    Only called once a representation exists, so ``*`` matches.
    """
    if not header:
        return False
    for raw in header.split(","):
        entry = raw.strip()
        if entry == "*" or entry.removeprefix("W/") == etag:
            return True
    return False


@router.get("/tenants/{slug}/branding")
@limiter.limit("30/minute")
def get_public_tenant_branding(
    request: Request,  # noqa: ARG001  # slowapi's @limiter.limit requires this parameter by name
    slug: str,
    session: Annotated[Session, Depends(get_session)],
) -> PublicTenantBrandingRead:
    """One condominium's public identity: ``slug``, ``name``, ``logo_url``, ``theme``.

    Unauthenticated: no ``Authorization`` and no ``X-Tenant-Id``.

    **404 for an unknown slug and for an inactive condominium alike**, in one
    condition rather than two. ``is_active`` is not exposed by this body, and
    ``deps._resolve_from_header`` refuses an inactive tenant to *everyone*,
    administrators included -- so a branded login into one could never
    succeed, and answering 200 would advertise a door that is nailed shut.

    30 requests per minute per IP (``get_remote_address``): one branded login
    plus its reloads, and enough to make a slug sweep expensive.
    """
    tenant = TenantService.get_by_slug(session, slug)
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return PublicTenantBrandingRead(
        slug=tenant.slug,
        name=tenant.name,
        logo_url=tenant.logo_url,
        theme=build_theme(tenant.brand_theme),
    )


@router.get(
    "/tenants/{slug}/logo",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
@limiter.limit("30/minute")
def get_public_tenant_logo(
    request: Request,
    slug: str,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """One condominium's logo, as bytes (APRAS-105 §C).

    Unauthenticated: no ``Authorization`` and no ``X-Tenant-Id``. The object
    lives in a store configured with private access, so the read happens here,
    with the application's own credential, and only the bytes come back out --
    never the store token and never the upstream Blob URL.

    **404 for everything that is not a logo**, in one shape rather than five:
    an unknown slug, an inactive condominium, a condominium with no
    ``logo_url``, a suffix outside ``TenantService.LOGO_ALLOWED_MIME_TYPES``,
    and any read that comes back empty or refused. A storage failure is
    explicitly **not** a 5xx: the storage layer logs the reason and the caller
    is told there is no image here.

    **Revalidated on every use, never time-cached** (APRAS-124). The ``200``
    carries a strong ``ETag`` -- the quoted SHA-256 hex digest of
    ``tenant.logo_url``, which names one immutable object because every
    replacement writes a new URL -- and ``Cache-Control: no-cache``. A request
    whose ``If-None-Match`` matches (RFC 9110 weak comparison: a list, a ``W/``
    prefix and ``*`` all count) gets a bodiless ``304`` **without the outbound
    read**. No ``max-age`` of any kind: a logo replaced on the admin screen
    must show immediately at a slug-stable URL (APRAS-92 D3, APRAS-93). The tag
    is derived first, and a ``None`` tag is the ordinary ``404`` whatever
    ``If-None-Match`` holds, ``*`` included. A ``404`` carries neither header.
    The branding route beside this one is deliberately unchanged.

    30 requests per minute per IP, the same limit the branding route carries
    and the operator's decision for this one. It answers the amplification
    question ``project_report_service._logo_html`` raised: this route is
    public and performs an outbound fetch buffering up to 2 MiB on every hit
    that does not revalidate, so one cheap inbound request can buy one outbound
    request we pay for. A ``304`` counts against the limit like a ``200``
    (slowapi deducts before the handler runs). It does not reverse D3, which
    was about the obras report -- a local render with a different cost profile
    entirely.
    """
    tenant = TenantService.get_by_slug(session, slug)
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found"
        )

    etag = TenantService.logo_etag(tenant)
    if etag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found"
        )

    headers = {"ETag": etag, "Cache-Control": "no-cache"}
    if _if_none_match_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    logo = TenantService.logo_bytes(tenant)
    if logo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found"
        )

    payload, content_type = logo
    return Response(content=payload, media_type=content_type, headers=headers)
