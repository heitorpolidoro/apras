"""The per-tenant subscription and its append-only history (APRAS-40 §3.2/§3.3).

**Why a table and not five more columns on `tenant`** (the shape APRAS-39
chose for modules): 39's column stores one boolean-ish fact with no history
and no foreign key. This stores a FK to `plan`, a status, a courtesy set, a
start date and notes, and it needs an append-only child table -- five columns
and a child table hung off `tenant` is a subscription entity wearing a
disguise. Recorded so the asymmetry with 39 is not read as an inconsistency.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.enums import SubscriptionChangeKind, SubscriptionStatus
from app.models.tenant import tenant_id_field


def _now() -> datetime:
    """Naive UTC now, exactly as every other model in this package writes it."""
    return datetime.utcnow()  # noqa: DTZ003


class TenantSubscription(SQLModel, table=True):
    """The commercial state of one tenant (APRAS-40). At most one per tenant."""

    __tablename__ = "tenant_subscription"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_subscription_tenant"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: Directly scoped (APRAS-41 doctrine): the tenant-side routes read and
    #: write this row through the acting tenant, so `tenant_context`'s loader
    #: criteria make a cross-tenant read structurally impossible. The
    #: superuser routes are on the GLOBAL_SCOPED tenants router, where
    #: `acting_tenant_id(session) is None`, so neither the filter nor
    #: `_stamp_tenant_on_write` applies and the explicit `tenant_id` survives.
    tenant_id: UUID = tenant_id_field()
    #: A plain FK column and deliberately **no** `Relationship`: the one place
    #: that needs the plan beside the subscription is
    #: `SubscriptionService.entitlement`, which joins them explicitly in one
    #: query (§6.3). A lazy relationship would make the plan reachable from
    #: any caller holding the row, which is exactly what §6.3's `build_read`
    #: scan exists to prevent.
    plan_id: UUID = Field(
        foreign_key="plan.id", ondelete="RESTRICT", nullable=False, index=True
    )
    status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE, nullable=False, index=True
    )
    #: Modules the global operator granted outside the plan (courtesy, trial,
    #: negotiation). Distinguishable from a contracted module by construction:
    #: it is a named column, written only by the superuser courtesy route, and
    #: it is free -- it never enters `estimated_monthly_total` (§6.4).
    courtesy_modules: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    notes: str | None = Field(default=None, nullable=True)
    started_at: datetime = Field(default_factory=_now, nullable=False)
    created_at: datetime = Field(default_factory=_now, nullable=False)
    updated_at: datetime = Field(default_factory=_now, nullable=False)


class SubscriptionChange(SQLModel, table=True):
    """An append-only record of one change to a tenant's subscription.

    The pattern is ``PurchaseQuoteDecision`` (APRAS-37): a child of a scoped
    parent, never updated, never deleted, ordered by its own timestamp. It
    carries **no** ``tenant_id`` -- it reaches its tenant through the NOT NULL
    FK to ``tenant_subscription``, and a second copy would be a forgeable
    source of truth that can disagree with the parent (APRAS-41 doctrine).

    Append-only is enforced structurally, not by convention: there is no
    ``PATCH``, no ``DELETE`` and no update route for this table, and
    ``SubscriptionService.record`` only ever ``session.add()``s one. Pinned by
    ``tests/test_subscription_history.py::test_the_history_is_never_updated_or_deleted``.
    """

    __tablename__ = "subscription_change"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    subscription_id: UUID = Field(
        foreign_key="tenant_subscription.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    kind: SubscriptionChangeKind = Field(nullable=False, index=True)
    modules_added: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    modules_removed: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    from_plan_id: UUID | None = Field(
        default=None, foreign_key="plan.id", nullable=True
    )
    to_plan_id: UUID | None = Field(
        default=None, foreign_key="plan.id", nullable=True
    )
    reason: str | None = Field(default=None, nullable=True)
    #: NOT NULL: all five write paths are authenticated requests, and a
    #: history row whose author is unknown is worse than no row.
    changed_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    changed_at: datetime = Field(default_factory=_now, nullable=False, index=True)
