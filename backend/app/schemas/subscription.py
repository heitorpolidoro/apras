"""Schemas for the subscription area (APRAS-40 §5.4).

``PUT`` everywhere and never ``PATCH`` for the module and courtesy sets: the
body is the **complete desired state**, so the operation is idempotent and the
response is the same body the ``GET`` returns (APRAS-39 §6.2's reasoning).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import SubscriptionChangeKind, SubscriptionStatus
from app.schemas.plan import PlanRead


class ModuleEntitlementRead(BaseModel):
    """One catalogue module, seen from the subscription area (§4.7)."""

    module: str
    is_core: bool
    #: From `tenant.disabled_modules` -- APRAS-39's truth, and the only input
    #: to permission resolution. This task changes no line of the resolver.
    is_active: bool
    in_plan: bool
    courtesy: bool
    #: `ent.managed and module in ent.all and module not in CORE_MODULES`.
    #: The `ent.managed` conjunct is load-bearing, not defensive: without it
    #: every toggleable module of an **unmanaged** tenant would read
    #: `can_contract: true` while `PUT /api/v1/subscription/modules` answers
    #: 404 (§4.6). This field means exactly "the PUT would accept this
    #: module" and nothing looser.
    can_contract: bool
    #: INERT. `ent.plan.module_prices.get(module)`; None when the tenant is
    #: unmanaged or the module is bundled at no extra cost.
    monthly_price: float | None
    #: One of CORE / UNMANAGED / PLAN / COURTESY / OVERRIDE, or None when the
    #: module is not active (§4.7's priority order).
    source: str | None


class SubscriptionRead(BaseModel):
    """The tenant's whole commercial state, in one body (§4.7, §6.4)."""

    tenant_id: UUID
    plan: PlanRead | None
    status: SubscriptionStatus | None
    started_at: datetime | None
    notes: str | None
    #: One row per `MODULES` entry, sorted by `module`.
    modules: list[ModuleEntitlementRead]
    #: INERT (§6.4). None when the tenant has no subscription.
    estimated_monthly_total: float | None
    currency: str | None


class SubscriptionModulesUpdate(BaseModel):
    """The **contracted set**, not the whole active set (§4.4 a step 5).

    A module the tenant is not offered a checkbox for -- a courtesy grant or
    an APRAS-39 raw override -- must not be switched off by being omitted, so
    the server's merge preserves exactly what the tenant does not govern.
    """

    active_modules: list[str]


class SubscriptionAdminUpdate(BaseModel):
    """Assign or change the plan, from the superuser side (§4.4 b)."""

    plan_id: UUID
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    notes: str | None = None


class CourtesyUpdate(BaseModel):
    """The complete desired courtesy set, from the superuser side (§4.4 c)."""

    courtesy_modules: list[str]
    reason: str | None = None


class SubscriptionChangeRead(BaseModel):
    """One append-only history row, with both plan names resolved."""

    id: UUID
    kind: SubscriptionChangeKind
    modules_added: list[str]
    modules_removed: list[str]
    from_plan_name: str | None
    to_plan_name: str | None
    reason: str | None
    changed_by_id: UUID
    changed_by_name: str | None
    changed_at: datetime
