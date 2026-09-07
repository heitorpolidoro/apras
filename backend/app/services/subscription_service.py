"""The subscription service: the ceiling, the three levers and the history.

APRAS-40 §4/§6.3. **The rule, once:**

    `tenant.disabled_modules` remains the only input to permission
    resolution. APRAS-40 changes no line of `deps.get_effective_permissions`,
    `deps.disabled_modules` or `permissions.filter_by_modules`. What APRAS-40
    adds is a constraint on *who may write that column and to what value*.

So this module never resolves a permission. It writes `tenant.disabled_modules`
through three levers -- the tenant-side contracting `PUT`, the superuser plan
assignment and the superuser courtesy grant -- and APRAS-39's raw superuser
switch remains a fourth, deliberately unconstrained writer of the same column
(the operator's repair tool), which this module only *records*.

**Import direction, stated so it is not discovered in review:**
`tenant_service.py` imports :class:`SubscriptionService` from here, so this
module must **not** import ``TenantService`` at module level. It does not need
to: it loads :class:`~app.models.tenant.Tenant` from the session directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.core.exceptions import (
    CoreModuleNotContractableError,
    InactivePlanError,
    ModuleNotEntitledError,
    SubscriptionNotFoundError,
    TenantNotFoundError,
    UnknownModuleError,
)
from app.core.permissions import CORE_MODULES, MODULES, TOGGLEABLE_MODULES
from app.models.enums import SubscriptionChangeKind
from app.models.plan import Plan
from app.models.subscription import SubscriptionChange, TenantSubscription
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.plan import PlanRead
from app.schemas.subscription import (
    CourtesyUpdate,
    ModuleEntitlementRead,
    SubscriptionAdminUpdate,
    SubscriptionChangeRead,
    SubscriptionRead,
)
from app.services.plan_service import PlanService

if TYPE_CHECKING:  # pragma: no cover
    from uuid import UUID


def _now() -> datetime:
    return datetime.utcnow()  # noqa: DTZ003


@dataclass(frozen=True)
class Entitlement:
    """The structured ceiling of one tenant, **and the whole input of
    :meth:`SubscriptionService.build_read`** (APRAS-40 §4.1/§6.3).

    Structured, not a flat set, because ``build_read`` has to tell *why* a
    module is entitled -- ``in_plan`` and ``courtesy`` are two different
    columns of the read model and two different ``source`` values -- while the
    ceiling itself must stay one definition. :attr:`all` is the ceiling; the
    two frozensets are the provenance.

    It carries the two **loaded rows** as well, because the read model needs
    ``status`` / ``started_at`` / ``notes`` from the subscription and
    ``base_price`` / ``module_prices`` / ``currency`` and the embedded
    ``PlanRead`` from the plan. :meth:`SubscriptionService.entitlement` is the
    single place that loads either of them, in one query, so ``build_read``
    touches the session not at all.
    """

    subscription: TenantSubscription | None
    plan: Plan | None
    included: frozenset[str]
    courtesy: frozenset[str]

    def __post_init__(self) -> None:
        # `plan_id` is NOT NULL (§3.2), so the two are absent together or
        # present together. Anything else is a loader bug, not a state.
        if (self.subscription is None) != (self.plan is None):
            raise AssertionError(
                "Entitlement: subscription and plan must be absent or present "
                "together"
            )

    @property
    def managed(self) -> bool:
        """False iff the tenant has no subscription row (§4.6)."""
        return self.subscription is not None

    @property
    def all(self) -> frozenset[str]:
        """§4.1's `entitlement(tenant)`. The ONLY ceiling in the codebase."""
        if not self.managed:
            return TOGGLEABLE_MODULES
        return self.included | self.courtesy


class SubscriptionService:
    """Reads and writes one tenant's commercial state."""

    # -- loaders ------------------------------------------------------------

    @staticmethod
    def entitlement(session: Session, tenant: Tenant) -> Entitlement:
        """The one loader, and the one definition of the ceiling (§6.3).

        A single statement -- a join, not two round trips and not a lazy
        relationship. The ``tenant_id`` predicate is explicit because the
        superuser routes are GLOBAL_SCOPED, where ``tenant_context`` adds no
        criteria of its own.
        """
        row = session.exec(
            select(TenantSubscription, Plan)
            .join(Plan, Plan.id == TenantSubscription.plan_id)
            .where(TenantSubscription.tenant_id == tenant.id)
        ).first()
        if row is None:
            return Entitlement(
                subscription=None,
                plan=None,
                included=frozenset(),
                courtesy=frozenset(),
            )
        subscription, plan = row
        return Entitlement(
            subscription=subscription,
            plan=plan,
            included=frozenset(plan.included_modules) & TOGGLEABLE_MODULES,
            courtesy=frozenset(subscription.courtesy_modules) & TOGGLEABLE_MODULES,
        )

    @staticmethod
    def get_subscription(
        *, session: Session, tenant_id: UUID
    ) -> TenantSubscription | None:
        """The tenant's subscription row, or ``None``. **Never raises.**

        Returning ``None`` rather than raising is what lets
        ``TenantService.set_modules``' appended history block stay a guard
        rather than a try/except, so APRAS-39's status codes cannot move.
        """
        return session.exec(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id == tenant_id
            )
        ).first()

    @staticmethod
    def _get_tenant(session: Session, tenant_id: UUID) -> Tenant:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)
        return tenant

    # -- the read model -----------------------------------------------------

    @classmethod
    def build_read(cls, session: Session, tenant: Tenant) -> SubscriptionRead:
        """The whole subscription area, derived from one `Entitlement` (§4.7).

        This body **touches the session not at all**: it calls
        :meth:`entitlement` exactly once and reads everything it returns off
        that result. ``session`` is forwarded, never queried, which is what
        makes `test_build_read_derives_everything_from_the_entitlement_result`
        satisfiable and ER-6's "from that result alone" literally true.
        """
        ent = cls.entitlement(session, tenant)
        active = MODULES - set(tenant.disabled_modules)

        rows: list[ModuleEntitlementRead] = []
        for module in sorted(MODULES):
            is_core = module in CORE_MODULES
            is_active = is_core or module in active
            in_plan = module in ent.included
            courtesy = module in ent.courtesy
            rows.append(
                ModuleEntitlementRead(
                    module=module,
                    is_core=is_core,
                    is_active=is_active,
                    in_plan=in_plan,
                    courtesy=courtesy,
                    can_contract=(
                        ent.managed and module in ent.all and not is_core
                    ),
                    monthly_price=(
                        None
                        if ent.plan is None
                        else ent.plan.module_prices.get(module)
                    ),
                    source=cls._source(
                        is_core=is_core,
                        is_active=is_active,
                        managed=ent.managed,
                        in_plan=in_plan,
                        courtesy=courtesy,
                    ),
                )
            )

        total = None
        if ent.plan is not None:
            total = ent.plan.base_price + sum(
                ent.plan.module_prices.get(module, 0.0)
                for module in active & TOGGLEABLE_MODULES
                if module not in ent.courtesy
            )

        return SubscriptionRead(
            tenant_id=tenant.id,
            plan=None if ent.plan is None else PlanRead.model_validate(ent.plan),
            status=None if ent.subscription is None else ent.subscription.status,
            started_at=(
                None if ent.subscription is None else ent.subscription.started_at
            ),
            notes=None if ent.subscription is None else ent.subscription.notes,
            modules=rows,
            estimated_monthly_total=total,
            currency=None if ent.plan is None else ent.plan.currency,
        )

    @staticmethod
    def _source(
        *,
        is_core: bool,
        is_active: bool,
        managed: bool,
        in_plan: bool,
        courtesy: bool,
    ) -> str | None:
        """§4.7's six values, evaluated top to bottom, first match wins.

        A module that is both in the plan and in the courtesy set therefore
        reads ``"PLAN"`` -- deterministic, and pinned by
        `test_source_priority_is_plan_over_courtesy`.
        """
        if is_core:
            return "CORE"
        if not is_active:
            return None
        if not managed:
            return "UNMANAGED"
        if in_plan:
            return "PLAN"
        if courtesy:
            return "COURTESY"
        return "OVERRIDE"

    # -- the history --------------------------------------------------------

    @staticmethod
    def record(
        *,
        session: Session,
        subscription: TenantSubscription,
        kind: SubscriptionChangeKind,
        added: list[str],
        removed: list[str],
        actor: User,
        reason: str | None = None,
        from_plan_id: UUID | None = None,
        to_plan_id: UUID | None = None,
    ) -> None:
        """The **only** writer of `subscription_change`. It only ever adds."""
        session.add(
            SubscriptionChange(
                subscription_id=subscription.id,
                kind=kind,
                modules_added=sorted(added),
                modules_removed=sorted(removed),
                from_plan_id=from_plan_id,
                to_plan_id=to_plan_id,
                reason=reason,
                changed_by_id=actor.id,
            )
        )

    @classmethod
    def list_history(
        cls,
        *,
        session: Session,
        tenant: Tenant,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[SubscriptionChangeRead]:
        """One tenant's history, newest first. Empty when it has no
        subscription (§4.6) -- a 200 with `[]`, never a 404.

        `limit=None` means *no* `LIMIT`, so the tenant-side route
        (`GET /api/v1/subscription/history`) keeps APRAS-40's behaviour byte
        for byte. `skip`/`limit` are applied in **SQL**, not by slicing a
        fully materialised list, so the two name-resolution loops below stay
        O(page).

        The order carries a deterministic tiebreak on `id`: two rows written
        in one call (a courtesy grant plus its revoke) can share a
        `changed_at`, and without it they would page unstably.
        """
        subscription = cls.get_subscription(session=session, tenant_id=tenant.id)
        if subscription is None:
            return []
        statement = (
            select(SubscriptionChange)
            .where(SubscriptionChange.subscription_id == subscription.id)
            .order_by(
                SubscriptionChange.changed_at.desc(), SubscriptionChange.id.desc()
            )
            .offset(skip)
        )
        if limit is not None:
            statement = statement.limit(limit)
        rows = session.exec(statement).all()

        plan_names: dict[UUID, str] = {}
        for row in rows:
            for plan_id in (row.from_plan_id, row.to_plan_id):
                if plan_id is not None and plan_id not in plan_names:
                    plan = session.get(Plan, plan_id)
                    if plan is not None:
                        plan_names[plan_id] = plan.name
        author_names: dict[UUID, str] = {}
        for row in rows:
            if row.changed_by_id not in author_names:
                author = session.get(User, row.changed_by_id)
                if author is not None:
                    author_names[row.changed_by_id] = author.full_name

        return [
            SubscriptionChangeRead(
                id=row.id,
                kind=row.kind,
                modules_added=list(row.modules_added),
                modules_removed=list(row.modules_removed),
                from_plan_name=(
                    None
                    if row.from_plan_id is None
                    else plan_names.get(row.from_plan_id)
                ),
                to_plan_name=(
                    None if row.to_plan_id is None else plan_names.get(row.to_plan_id)
                ),
                reason=row.reason,
                changed_by_id=row.changed_by_id,
                changed_by_name=author_names.get(row.changed_by_id),
                changed_at=row.changed_at,
            )
            for row in rows
        ]

    # -- the three levers ---------------------------------------------------

    @classmethod
    def set_modules(
        cls,
        *,
        session: Session,
        tenant: Tenant,
        active_modules: list[str],
        actor: User,
    ) -> SubscriptionRead:
        """§4.4 (a): the tenant contracts, within the ceiling.

        The body is the **contracted set**, not the whole active set: a module
        the tenant is not offered a checkbox for must not be switched off by
        being omitted. ``preserved`` below is exactly the courtesy-active and
        override-active modules, so omission deactivates only plan-covered
        modules and a courtesy grant or an APRAS-39 raw override survives
        every tenant-side write.
        """
        ent = cls.entitlement(session, tenant)
        if not ent.managed:
            raise SubscriptionNotFoundError

        requested_raw = set(active_modules)
        for module in sorted(requested_raw):
            if module not in MODULES:
                raise UnknownModuleError(module)
        # Core modules in the body are accepted and ignored -- they are always
        # active, so naming one in the *active* list is simply true.
        requested = requested_raw & TOGGLEABLE_MODULES
        not_entitled = requested - ent.all
        if not_entitled:
            raise ModuleNotEntitledError(sorted(not_entitled))

        active_before = TOGGLEABLE_MODULES - set(tenant.disabled_modules)
        preserved = active_before - ent.included
        new_active = requested | preserved

        added = sorted(new_active - active_before)
        removed = sorted(active_before - new_active)
        if added or removed:
            tenant.disabled_modules = sorted(TOGGLEABLE_MODULES - new_active)
            tenant.updated_at = _now()
            session.add(tenant)
            cls.record(
                session=session,
                subscription=ent.subscription,
                kind=SubscriptionChangeKind.CONTRACTED,
                added=added,
                removed=removed,
                actor=actor,
            )
            session.commit()
            session.refresh(tenant)
        return cls.build_read(session, tenant)

    @classmethod
    def set_plan(
        cls,
        *,
        session: Session,
        tenant_id: UUID,
        payload: SubscriptionAdminUpdate,
        actor: User,
    ) -> SubscriptionRead:
        """§4.4 (b): the superuser assigns or changes the plan, then applies
        the ceiling **shrink-only**.

        Modules that leave the entitlement are deactivated; modules that newly
        enter it are **not** auto-activated -- contracting them is the
        tenant's explicit act, and that is what makes the contracting screen
        meaningful.

        **A genuine no-op appends nothing**, exactly like the other two levers:
        re-sending the plan, status and notes a tenant already carries, with
        nothing left to deactivate, is a 200 that writes no row. The three
        levers are idempotent in the same way, so a UI that re-saves cannot
        manufacture history. First adoption is never a no-op -- it is a real
        commercial event and §4.4 (b) requires it to be visible.

        `reason` is deliberately **not** set from `payload.notes`: `notes` is
        *subscription* metadata (the current state of the arrangement) and
        `reason` is *per-change* metadata (why this row exists). Conflating
        them would re-stamp the same sentence on every future plan change.
        """
        tenant = cls._get_tenant(session, tenant_id)
        plan = PlanService.get_plan(session=session, plan_id=payload.plan_id)
        subscription = cls.get_subscription(session=session, tenant_id=tenant_id)

        already_on_it = (
            subscription is not None and subscription.plan_id == plan.id
        )
        if not plan.is_active and not already_on_it:
            raise InactivePlanError(plan.name)

        adopting = subscription is None
        from_plan_id = None if adopting else subscription.plan_id
        commercial_change = adopting or (
            subscription.plan_id != plan.id
            or subscription.status != payload.status
            or subscription.notes != payload.notes
        )

        if adopting:
            subscription = TenantSubscription(
                tenant_id=tenant_id,
                plan_id=plan.id,
                status=payload.status,
                notes=payload.notes,
            )
            session.add(subscription)
        elif commercial_change:
            subscription.plan_id = plan.id
            subscription.status = payload.status
            subscription.notes = payload.notes
            subscription.updated_at = _now()
            session.add(subscription)
        if commercial_change:
            # `flush`, not `commit` (round-2 review N-2): the row has to be
            # visible to `entitlement`'s join below, but the plan write, the
            # ceiling shrink and the history row must land together. A commit
            # here could leave the plan changed with no shrink and no history
            # -- the same shape S-5 closed on the raw lever.
            session.flush()

        ent = cls.entitlement(session, tenant)
        active_before = TOGGLEABLE_MODULES - set(tenant.disabled_modules)
        new_active = active_before & ent.all
        removed = sorted(active_before - new_active)
        new_disabled = sorted(TOGGLEABLE_MODULES - new_active)

        # `removed` can be non-empty with no commercial change: APRAS-39's raw
        # lever may have activated something outside the entitlement, and
        # re-assigning the same plan is how an operator repairs that (§4.5's
        # I2). That is a real event and it is recorded.
        if commercial_change or removed:
            if tenant.disabled_modules != new_disabled:
                tenant.disabled_modules = new_disabled
                tenant.updated_at = _now()
                session.add(tenant)
            cls.record(
                session=session,
                subscription=subscription,
                kind=SubscriptionChangeKind.PLAN_CHANGE,
                added=[],
                removed=removed,
                actor=actor,
                from_plan_id=from_plan_id,
                to_plan_id=plan.id,
            )
            # One commit for the plan write, the ceiling shrink and the
            # history row together.
            session.commit()
            session.refresh(tenant)
            session.refresh(subscription)
        return cls.build_read(session, tenant)

    @classmethod
    def set_courtesy(
        cls,
        *,
        session: Session,
        tenant_id: UUID,
        payload: CourtesyUpdate,
        actor: User,
    ) -> SubscriptionRead:
        """§4.4 (c): the superuser grants or revokes courtesy, and activates.

        Courtesy names one or more **specific** modules as a deliberate
        per-module operator act -- "turn this on for them" -- whereas a plan
        names a bundle and says nothing about what the condominium wants
        switched on. That asymmetry with §4.4 (b) is deliberate.
        """
        tenant = cls._get_tenant(session, tenant_id)
        ent = cls.entitlement(session, tenant)
        if not ent.managed:
            raise SubscriptionNotFoundError
        subscription = ent.subscription

        requested = set(payload.courtesy_modules)
        for module in sorted(requested):
            if module not in MODULES:
                raise UnknownModuleError(module)
        core = requested & CORE_MODULES
        if core:
            raise CoreModuleNotContractableError(sorted(core))

        toggleable_requested = requested & TOGGLEABLE_MODULES
        granted = sorted(toggleable_requested - ent.courtesy)
        revoked = sorted(ent.courtesy - toggleable_requested)

        subscription.courtesy_modules = sorted(requested)
        subscription.updated_at = _now()
        session.add(subscription)

        active_before = TOGGLEABLE_MODULES - set(tenant.disabled_modules)
        # Newly granted modules are activated; revoked ones are deactivated
        # unless the plan also covers them, in which case the revoke changes
        # nothing but the label.
        new_active = (active_before | set(granted)) - (
            set(revoked) - ent.included
        )
        tenant.disabled_modules = sorted(TOGGLEABLE_MODULES - new_active)
        tenant.updated_at = _now()
        session.add(tenant)

        if granted:
            cls.record(
                session=session,
                subscription=subscription,
                kind=SubscriptionChangeKind.COURTESY_GRANT,
                added=granted,
                removed=[],
                actor=actor,
                reason=payload.reason,
            )
        if revoked:
            cls.record(
                session=session,
                subscription=subscription,
                kind=SubscriptionChangeKind.COURTESY_REVOKE,
                added=[],
                removed=revoked,
                actor=actor,
                reason=payload.reason,
            )
        session.commit()
        session.refresh(tenant)
        return cls.build_read(session, tenant)

    # -- the superuser read -------------------------------------------------

    @classmethod
    def read_for_tenant(cls, *, session: Session, tenant_id: UUID) -> SubscriptionRead:
        """The same body `GET /api/v1/subscription` returns, named by path."""
        return cls.build_read(session, cls._get_tenant(session, tenant_id))

    @classmethod
    def list_history_for_tenant(
        cls, *, session: Session, tenant_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[SubscriptionChangeRead]:
        """The same rows `GET /api/v1/subscription/history` returns, named by
        path (APRAS-52 §3.1).

        `_get_tenant` raises `TenantNotFoundError` for an unknown id, so this
        is a 404 through the existing global handler -- the same status the
        sibling `GET /{tenant_id}/subscription` gives, with no new error class
        and no new handler.
        """
        return cls.list_history(
            session=session,
            tenant=cls._get_tenant(session, tenant_id),
            skip=skip,
            limit=limit,
        )
