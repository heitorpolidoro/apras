"""The condominium profile surface (APRAS-61 D1).

Mounted ``TENANT_SCOPED`` with **no ``{tenant_id}`` in any path**, for exactly
the reason ``endpoints/subscription.py`` already records: the ``tenants``
router is mounted ``GLOBAL_SCOPED``, so it resolves no acting tenant, and with
no acting tenant ``get_effective_role_ids`` is empty and the ``is_tenant_admin``
short-circuit is structurally absent — a ``require_permission`` guard over
there would answer 403 to every tenant role *and* to every tenant admin.

Not having an id in the path is also what gives ER-4 for free: the subject is
whatever ``deps.get_current_tenant`` resolved from ``X-Tenant-Id``, and a user
naming a tenant they do not belong to is refused by
``deps._resolve_from_header`` before any handler here runs.

The read is authenticated and self-scoped and carries no permission (D6); the
three writes carry ``tenants:profile_update``, an ordinary grantable
permission (D7) that a tenant admin holds through APRAS-47's whole-catalogue
short-circuit, with no special case below.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session

from app.api import deps as api_deps
from app.db import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantProfileRead, TenantProfileUpdate
from app.services.tenant_service import TenantService

router = APIRouter()

#: Bound once at import, like `endpoints/uploads.py`'s three guards: the
#: multipart route needs a parameter default-free signature, and one object
#: read by three routes is one place the permission string is written.
_require_profile_update = api_deps.require_permission("tenants:profile_update")


@router.get("")
def get_tenant_profile(
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    _: Annotated[User, Depends(api_deps.get_current_active_user)],
) -> TenantProfileRead:
    """The acting condominium's name, id, slug, active flag and logo.

    Unguarded by design (D6): it is self-scoped to the acting tenant and
    returns data the caller already holds — ``/auth/me`` carries the tenant
    name and the logo is a public static asset — so it joins
    ``UNGUARDED_ROUTES`` under the ``/permissions/me`` precedent. The page's
    own gate is the permission, so a caller without it never loads the screen.
    """
    return TenantProfileRead.model_validate(tenant)


@router.patch("")
def update_tenant_profile(
    profile_in: TenantProfileUpdate,
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    _: Annotated[User, Depends(_require_profile_update)],
) -> TenantProfileRead:
    """Rename the acting condominium and/or move its address.

    409 when another tenant holds the name, and 409 (``SlugAlreadyTakenError``)
    when another holds the submitted ``slug`` -- never a ``-<n>`` suffix, which
    would store an address nobody typed. A malformed slug is 422
    (``InvalidSlugError``). Both errors reach their status through the ordinary
    ``DomainError`` handler; nothing here catches them.

    The slug rides the **existing** ``tenants:profile_update`` guard bound
    above (APRAS-66 D-C.1): no new route, no new permission string, no
    ``ROUTE_PERMISSIONS`` entry and therefore no parity-matrix baseline
    change. A stricter grant would restrict nobody who can reach this screen
    -- a tenant admin already holds the whole catalogue -- while the blast
    radius of a slug change (broken bookmarks) is no larger than that of the
    rename this permission already authorises.
    """
    updated = TenantService.update_profile(session, tenant, profile_in)
    return TenantProfileRead.model_validate(updated)


@router.put("/logo")
async def set_tenant_logo(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    _: Annotated[User, Depends(_require_profile_update)],
) -> TenantProfileRead:
    """Replace the condominium's logo. 422 on type, size or undecodable bytes.

    The previous file is deleted only when it was one of ours — see
    ``TenantService._delete_stored_logo``.
    """
    file_bytes = await file.read()
    updated = TenantService.set_logo(
        session,
        tenant,
        file_bytes=file_bytes,
        filename=file.filename or "logo.png",
        content_type=file.content_type or "application/octet-stream",
    )
    return TenantProfileRead.model_validate(updated)


@router.delete("/logo")
def clear_tenant_logo(
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    _: Annotated[User, Depends(_require_profile_update)],
) -> TenantProfileRead:
    """Remove the logo. Idempotent: an already-empty profile is still a 200."""
    updated = TenantService.clear_logo(session, tenant)
    return TenantProfileRead.model_validate(updated)
