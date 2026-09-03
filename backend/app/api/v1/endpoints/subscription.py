"""The tenant-side subscription area (APRAS-40 §5.1).

Mounted ``TENANT_SCOPED``, because a permission-guarded route **must** resolve
an acting tenant: post-F5 ``get_effective_role_ids`` returns the empty set with
no acting tenant, so a ``billing:read`` holder on a global route would be
403'd.

There is **no ``{tenant_id}`` in these paths, on purpose.** The subject is the
acting tenant, resolved from ``X-Tenant-Id`` by ``get_current_tenant``. A path
parameter would be a second, forgeable source of truth and would hand a
tenant_admin of A a way to name B.

An ``is_tenant_admin`` holder reaches all three with **no special case here**:
APRAS-47 makes an acting tenant_admin hold every permission in the catalogue in
the granting tenant, and ``billing`` is core so APRAS-39's strip never removes
it. That is the whole reason the gate is a permission and not a flag check.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api import deps as api_deps
from app.db import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionChangeRead,
    SubscriptionModulesUpdate,
    SubscriptionRead,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("")
def get_my_subscription(
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    _: Annotated[User, Depends(api_deps.require_permission("billing:read"))],
) -> SubscriptionRead:
    """The acting tenant's plan, module entitlements and inert estimate.

    **200 even with no subscription** (§4.6): `plan: null`, every toggleable
    module `source: "UNMANAGED"` when active and `can_contract: false`,
    because the contracting `PUT` is a 404 there. Adopting billing is opt-in.
    """
    return SubscriptionService.build_read(session, tenant)


@router.put("/modules")
def set_my_modules(
    modules_in: SubscriptionModulesUpdate,
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    current_user: Annotated[
        User, Depends(api_deps.require_permission("billing:manage"))
    ],
) -> SubscriptionRead:
    """Contract or cancel modules within the plan (§4.4 a).

    The body is the **contracted set** -- the plan-covered checkboxes and
    nothing else. Courtesy and override activations are display-only rows on
    the page, are never sent, and are never dropped: the merge preserves what
    the tenant does not govern. A no-op `PUT` is a 200 that writes no history
    row, which is what lets the UI re-save safely.
    """
    return SubscriptionService.set_modules(
        session=session,
        tenant=tenant,
        active_modules=modules_in.active_modules,
        actor=current_user,
    )


@router.get("/history")
def get_my_history(
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    _: Annotated[User, Depends(api_deps.require_permission("billing:read"))],
) -> list[SubscriptionChangeRead]:
    """The acting tenant's change history, newest first, and only its own."""
    return SubscriptionService.list_history(session=session, tenant=tenant)
