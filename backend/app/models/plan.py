"""The install-wide commercial plan catalogue (APRAS-40 §3.1).

`plan` carries **no** `tenant_id`: it joins `user`, `tenant` and
`user_tenant_link` in the unscoped group of `tests/test_tenant_models.py`.
Global, not per-tenant, is the SaaS norm and it is the thing that makes "which
plan is this condominium on" a comparable answer across the install.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core import clock
from app.core.money import Money


class Plan(SQLModel, table=True):
    """One commercial plan in the install-wide catalogue (APRAS-40).

    Global, not per-tenant: the SaaS norm, and the thing that makes "which
    plan is this condominium on" a comparable answer across the install.
    ``name`` is globally unique for the same reason ``tenant.name`` is.

    **Every price field is INERT**: it is displayed and summed for display and
    never charges anything, because no payment provider exists for this
    project (§1.2). ``base_price`` is nonetheless ``Decimal`` backed by
    ``NUMERIC(12, 2)`` since APRAS-64, following
    ``finance.FinancialTransaction.amount`` and ``BudgetLine.planned_amount``
    -- money has one type in this codebase and an inert price is no reason
    for a second. ``module_prices`` stays a portable ``JSON`` dict of floats
    (JSON has no decimal type); ``subscription_service`` reads each value back
    as ``Decimal(str(value))`` so no expression mixes the two.
    """

    __tablename__ = "plan"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, nullable=False)
    description: str | None = Field(default=None, nullable=True)
    #: The toggleable modules this plan lets a tenant contract. Portable JSON,
    #: not a Postgres ARRAY: `tests/conftest.py` builds the schema with
    #: `SQLModel.metadata.create_all()` on `sqlite://` (the reason
    #: `role.permissions` and `tenant.disabled_modules` record).
    included_modules: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    #: INERT. Monthly base price of the plan.
    base_price: Money = Field(default=Decimal("0.00"), nullable=False)
    #: INERT. `{module: monthly price}` for the modules this plan lets a
    #: tenant contract. A module in `included_modules` with no entry here is
    #: bundled at no extra cost. Keys must be a subset of `included_modules`
    #: (`PlanService`, §6.2).
    module_prices: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    currency: str = Field(default="BRL", max_length=3, nullable=False)
    #: Soft deactivation. There is deliberately no DELETE route: a plan a
    #: tenant is subscribed to must not vanish, and
    #: `tenant_subscription.plan_id` is ON DELETE RESTRICT.
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=clock.db_now, nullable=False)
    updated_at: datetime = Field(default_factory=clock.db_now, nullable=False)
