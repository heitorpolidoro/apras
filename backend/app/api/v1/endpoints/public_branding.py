"""The public condominium branding read (APRAS-74 D2, D3).

One route, and it is the only unauthenticated tenant-shaped read in the
product: ``GET /api/v1/public/tenants/{slug}/branding`` is what makes
``/c/<slug>`` show the condominium's own name, logo and colours to somebody
who has not signed in yet.

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

The route maps to **no catalogue permission** -- it authenticates nobody, so
there is nobody to hold one -- and therefore joins ``UNGUARDED_ROUTES``
alongside ``/auth/forgot-password`` and the two public invitation routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.branding import build_theme
from app.core.limiter import limiter
from app.db import get_session
from app.schemas.tenant import PublicTenantBrandingRead
from app.services.tenant_service import TenantService

router = APIRouter()


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
