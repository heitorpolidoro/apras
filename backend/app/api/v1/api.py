"""API v1 router."""

from app.api.v1.endpoints import (
    access_control,
    access_logs,
    announcements,
    assets,
    auth,
    authorizations,
    categories,
    documents,
    feedback,
    finance,
    inventory_movements,
    lots,
    occurrences,
    packages,
    permissions,
    plans,
    projects,
    purchases,
    reservations,
    residents,
    subscription,
    tasks,
    tenants,
    uploads,
    roles,
    users,
    visitors,
    voting,
)
from fastapi import APIRouter, Depends

from app.api import deps

api_router = APIRouter()

#: Attached to every router whose tables are tenant-scoped. Resolving the
#: acting tenant at *mount* time rather than in ~170 handler signatures is
#: what makes "is this route scoped?" reviewable in one diff (APRAS-42 §5.1).
TENANT_SCOPED = [Depends(deps.get_current_tenant)]

#: Attached to the routers whose whole surface is unscoped (`user`,
#: `tenant`, `user_tenant_link`) or device-authenticated, so the fail-closed
#: guard of `app.core.tenant_context` does not fire on them.
GLOBAL_SCOPED = [Depends(deps.use_global_tenant_scope)]


@api_router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


api_router.include_router(auth.router, prefix="/auth", tags=["auth"], dependencies=GLOBAL_SCOPED)
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"], dependencies=TENANT_SCOPED)
api_router.include_router(users.router, prefix="/users", tags=["users"], dependencies=TENANT_SCOPED)
api_router.include_router(categories.router, prefix="/categories", tags=["categories"], dependencies=TENANT_SCOPED)
api_router.include_router(roles.router, prefix="/roles", tags=["roles"], dependencies=TENANT_SCOPED)
# Tenant-scoped, and it must be: `/permissions/me` answers "what do I hold in
# the tenant I am acting in", which is exactly what `get_current_tenant`
# resolves (APRAS-48 §2.1). `/auth/me` stays global and gains nothing.
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"], dependencies=TENANT_SCOPED)
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"], dependencies=GLOBAL_SCOPED)
api_router.include_router(lots.router, prefix="/lots", tags=["lots"], dependencies=TENANT_SCOPED)
api_router.include_router(residents.router, tags=["residents"], dependencies=TENANT_SCOPED)
api_router.include_router(visitors.router, prefix="/visitors", tags=["visitors"], dependencies=TENANT_SCOPED)
api_router.include_router(authorizations.router, tags=["authorizations"], dependencies=TENANT_SCOPED)
api_router.include_router(access_logs.router, prefix="/access-logs", tags=["access-logs"], dependencies=TENANT_SCOPED)
api_router.include_router(occurrences.router, prefix="/occurrences", tags=["occurrences"], dependencies=TENANT_SCOPED)
api_router.include_router(documents.router, prefix="/documents", tags=["documents"], dependencies=TENANT_SCOPED)
api_router.include_router(uploads.router, dependencies=TENANT_SCOPED)
api_router.include_router(
    access_control.router,
    prefix="/access-control",
    tags=["access-control"],
    dependencies=TENANT_SCOPED,
)
# The device webhook authenticates an `X-Device-Key`, not a JWT, so it cannot
# inherit `get_current_tenant` (which depends on `get_current_user`). It is
# mounted separately in global scope and resolves its own acting tenant from
# the device it authenticates (APRAS-42 §6.4).
api_router.include_router(
    access_control.webhook_router,
    prefix="/access-control",
    tags=["access-control"],
    dependencies=GLOBAL_SCOPED,
)
api_router.include_router(projects.router, prefix="/projects", tags=["projects"], dependencies=TENANT_SCOPED)
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"], dependencies=TENANT_SCOPED)
api_router.include_router(finance.router, prefix="/finance", tags=["finance"], dependencies=TENANT_SCOPED)
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"], dependencies=TENANT_SCOPED)
api_router.include_router(
    reservations.spaces_router,
    prefix="/reservable-spaces",
    tags=["reservable-spaces"],
    dependencies=TENANT_SCOPED,
)
api_router.include_router(
    reservations.reservations_router,
    prefix="/space-reservations",
    tags=["space-reservations"],
    dependencies=TENANT_SCOPED,
)
api_router.include_router(packages.router, prefix="/packages", tags=["packages"], dependencies=TENANT_SCOPED)
api_router.include_router(
    voting.assemblies_router,
    prefix="/assemblies",
    tags=["assemblies"],
    dependencies=TENANT_SCOPED,
)
api_router.include_router(voting.votes_router, prefix="/votes", tags=["votes"], dependencies=TENANT_SCOPED)
api_router.include_router(assets.router, prefix="/assets", tags=["assets"], dependencies=TENANT_SCOPED)
api_router.include_router(
    inventory_movements.router,
    prefix="/inventory-movements",
    tags=["inventory-movements"],
    dependencies=TENANT_SCOPED,
)
api_router.include_router(
    purchases.router,
    prefix="/purchase-requests",
    tags=["purchase-requests"],
    dependencies=TENANT_SCOPED,
)
# APRAS-40 §5.1: tenant-scoped, and it must be. The three routes are
# permission-guarded, and post-F5 `get_effective_role_ids` returns the empty
# set with no acting tenant -- so a `billing:read` holder on a global router
# would be 403'd. The subject is the acting tenant, never a path parameter.
api_router.include_router(
    subscription.router,
    prefix="/subscription",
    tags=["subscription"],
    dependencies=TENANT_SCOPED,
)
# APRAS-40 §5.2: the install-wide plan catalogue. Every route is
# superuser-only, so no acting tenant is needed and the router joins
# `tenants` in the global set. `plan` carries no `tenant_id`.
api_router.include_router(
    plans.router, prefix="/plans", tags=["plans"], dependencies=GLOBAL_SCOPED
)






