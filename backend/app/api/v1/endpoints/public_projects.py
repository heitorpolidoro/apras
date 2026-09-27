"""The public obras report (APRAS-92, D1/D2/D3).

One route: ``GET /api/v1/public/tenants/{slug}/projects/report`` renders the
construction-projects report of the condominium the slug names, for a visitor
who is not signed in. It is what `/c/<slug>/obras` puts in front of a resident
who was handed a link, and it answers the same document
``project_report_service.render_report_html`` produces for the internal route.

**Mounted ``GLOBAL_SCOPED``, never ``TENANT_SCOPED``**, exactly like
``public_branding``: the caller sends no ``Authorization`` and no
``X-Tenant-Id``, so ``deps.get_current_tenant`` would refuse every request and
the fail-closed guard of ``app.core.tenant_context`` would fire. The tenant is
named in the path and is the *subject* of the read, in the same sense
``{tenant_id}`` is on ``/api/v1/tenants/{tenant_id}/modules``. It maps to **no
catalogue permission** -- it authenticates nobody, so there is nobody to hold
one -- and therefore joins ``UNGUARDED_ROUTES``.

**404 for an unknown slug and for an inactive condominium alike**, in one
condition and with one detail. ``deps._resolve_from_header`` refuses an
inactive tenant to *everyone*, administrators included, so answering 200 here
would publish a condominium that cannot be signed into.

**The tenant seam.** The renderer resolves its tenant from the session rather
than from an argument (``_acting_tenant`` reads ``acting_tenant_id``, and
milestones and bulletins ride the already-narrowed ``project.milestones`` /
``project.updates`` relationships). An anonymous request resolves no acting
tenant, so this handler establishes one for the duration of the render with
``tenant_context.acting_tenant_scope``. That is the smallest seam available: no
change to either tenant-resolution helper, and the renderer still contains no
``select()`` over an inherited table.

**The accepted risk, stated where the route is (D3).** The operator chose a
guessable slug over an unguessable per-link token (D1) and full budget parity
with the internal report (D2), and declined both a per-IP rate limit and
``Cache-Control`` (D3) -- the latter because a browser-held copy cannot be
invalidated, so a freshly published bulletin would stay invisible for the whole
TTL. So a caller can walk the slug space and pull every condominium's full
report, budget figures included, at whatever rate they like, and each hit costs
a full render. This route therefore carries **no** ``@limiter.limit`` and sets
**no** ``Cache-Control`` or ``ETag``, deliberately and not by omission.
**APRAS-93** owns any revisit; do not add one here without it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.core import tenant_context
from app.db import get_session
from app.services import project_report_service
from app.services.tenant_service import TenantService

router = APIRouter()


@router.get("/tenants/{slug}/projects/report", response_class=HTMLResponse)
def get_public_projects_report(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    """The condominium's obras report, as printable HTML, to anyone.

    Unauthenticated: no ``Authorization`` and no ``X-Tenant-Id``. Rendered
    fresh on every request -- no limit, no cache, no ``ETag`` (D3).

    ``user=None`` is the whole difference from the internal route's document:
    the footer renders its ``Gerado em ...`` timestamp with no author clause,
    because there is no caller to name.
    """
    tenant = TenantService.get_by_slug(session, slug)
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    # The second production caller of `acting_tenant_scope`, and the review
    # comment its docstring requires: the renderer reads its tenant off the
    # session (and reaches milestones and bulletins through the ambient
    # `with_loader_criteria`), so an anonymous request has to establish the
    # scope rather than pass a tenant in. It is entered around the render only
    # and restored after it, so nothing downstream of this request acts in the
    # condominium the slug named.
    with tenant_context.acting_tenant_scope(session, tenant.id):
        document = project_report_service.get_report_html(session, None)

    return HTMLResponse(content=document)
