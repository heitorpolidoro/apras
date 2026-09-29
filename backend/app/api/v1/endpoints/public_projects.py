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

**The cover route's limiter is its own (APRAS-104 ER11).** The second route
below, ``GET /tenants/{slug}/projects/{project_id}/cover``, carries
``@limiter.limit("300/minute")``. That does **not** reverse D3 and it does not
claim the report route's policy, which is "no limiter": ``public_branding.py``
already settles the principle a bytes route is judged by -- "The limiter below
is this route's and is not shared" -- and the cover GET has the logo GET's shape
exactly, public and uncached with one outbound Blob fetch we are billed for on
every hit. It is a *worse* amplifier than the logo, because one report view
costs one logo fetch but *N* cover fetches, and a route strictly more
amplifying than one that is limited cannot be unlimited on the limited one's
reasoning.

**The number, by arithmetic.** The honest unit is the page view and the
limiter's unit is the request, so the two differ by the fan-out: the largest
report to plan for carries **12 obras**, and since nothing on this surface sets
``Cache-Control`` a reload repeats all twelve; the worst legitimate load to
survive is one NAT'd condominium office, ~10 distinct readers behind one
address loading or reloading twice a minute, i.e. **20 views/minute**; 20 x 12
= **240**, and 300 is the next round number above it, admitting 25
views/minute at twelve obras. So the two bytes routes carry the *same* policy
measured in page views -- the logo's 30/minute is 30 views/minute at one fetch
per view -- and differ tenfold in requests only because the fan-out differs
tenfold. Copying 30 here would exhaust on the **third** page view of a
twelve-obra report.

**The accepted risk, recorded where the code is**, as this module's convention
requires. At 300/minute with twelve covers at the 5 MiB cap the worst case is
~1.5 GiB/min of paid Blob egress from one address, and that is accepted
knowingly: a bandwidth-parity limit would be ~12/minute, one page view a
minute, which is not a limit but an outage indistinguishable to a resident from
the product being broken. **This limiter is a fan-out guard, not an egress
budget.** The worst case is also not reachable by accident -- it needs twelve
covers all at the cap and a caller choosing to pull them 300 times a minute.
The real answer is ``Cache-Control`` plus server-side resizing, both out of
scope here and both belonging with **APRAS-93**, where a cache changes the
arithmetic. A 429 lands on an ``<img src>`` and the browser draws its
broken-image glyph in that obra's hero; the report HTML itself still renders,
because it comes from the unmetered route above.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.core import tenant_context
from app.core.limiter import limiter
from app.db import get_session
from app.models.project import ConstructionProject
from app.services import project_report_service
from app.services.project_service import ProjectService
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


@router.get(
    "/tenants/{slug}/projects/{project_id}/cover",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
@limiter.limit("300/minute")
def get_public_project_cover(
    request: Request,  # noqa: ARG001  # slowapi's @limiter.limit requires this parameter by name
    slug: str,
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """One obra's cover photo, as bytes (APRAS-104 §A).

    Unauthenticated: no ``Authorization`` and no ``X-Tenant-Id``. The object
    lives in a store configured with private access, so the read happens here,
    with the application's own credential, and only the bytes come back out --
    never the store token and never the upstream Blob URL.

    **404 for everything that is not a readable cover photo**, in one shape
    rather than seven: an unknown slug, an inactive condominium, a project that
    is not this condominium's, a project with no ``cover_photo_url``, a suffix
    outside the three accepted image types, a value the provider does not own
    (a pasted CDN or Drive URL -- this route never forwards to a foreign host),
    and any read that comes back empty or refused. A storage failure is
    explicitly **not** a 5xx: the storage layer logs the reason and the caller
    is told there is no image here.

    **Keyed by slug, not by project id alone.** Keying on the id would need a
    cross-tenant lookup from an unauthenticated, ``GLOBAL_SCOPED`` handler;
    keying on the slug lets the lookup run inside ``acting_tenant_scope``, which
    enforces "this project belongs to this condominium" as a side effect of the
    scope rather than as a hand-written check. It is also the shape of the
    report route the image is embedded in.

    The path cannot shadow the report route above even though both live under
    ``/tenants/{slug}/projects/…``: ``…/projects/report`` is two segments after
    the slug and this is three, so no literal/parameter ambiguity arises and no
    declaration-order constraint applies between them.

    **No ``Cache-Control`` and no ``ETag``**, the one thing this route takes
    from the report route; the limit it carries is its own (see the module
    docstring).
    """
    tenant = TenantService.get_by_slug(session, slug)
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cover photo not found"
        )

    # The third production caller of `acting_tenant_scope`, and the review
    # comment its docstring requires: the lookup below must be narrowed to the
    # condominium the slug names, and an anonymous request resolves no acting
    # tenant of its own. Entering the scope is what makes "this project belongs
    # to this condominium" a property of the ambient `with_loader_criteria`
    # rather than a hand-written `where` a future reader could drop. It is
    # entered around the lookup only and restored after it, so nothing
    # downstream of this request acts in that condominium.
    with tenant_context.acting_tenant_scope(session, tenant.id):
        project = session.get(ConstructionProject, project_id)
        cover = ProjectService.cover_photo_bytes(project)

    if cover is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cover photo not found"
        )

    payload, content_type = cover
    return Response(content=payload, media_type=content_type)
