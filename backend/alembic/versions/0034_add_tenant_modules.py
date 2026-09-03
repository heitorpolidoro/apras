"""add tenant.disabled_modules, the per-tenant module switch (APRAS-39)

Revision ID: 0034_add_tenant_modules
Revises: 0033_drop_user_role_and_menus
Create Date: 2026-09-02

One portable JSON column and nothing else.

**Negative storage on purpose.** ``[]`` means "every module active", so the
``server_default`` *is* the all-on backfill for every existing tenant --
including ``00000000-0000-0000-0000-000000000001`` -- a new tenant is all-on
with no seeding, and a module a future task adds is active everywhere with no
data step. A ``tenant_module(tenant_id, module, is_enabled)`` table would
instead need 23 inserts per tenant at creation time and a backfill for every
future module, and would have to be taught to the tenancy machinery
(``tenant_context._discover_scoped_models`` picks up every mapped class with a
``tenant_id`` column, which would be fatal here: the superuser writes this
from a **global** route for an arbitrary tenant).

``sa.JSON``, not a Postgres ``ARRAY``, for the reason ``0030`` records: the
test harness builds this schema on ``sqlite://`` with
``SQLModel.metadata.create_all()``.

**No data statement in either direction**, which is what makes it exactly
reversible.
"""

import sqlalchemy as sa

from alembic import op

revision = "0034_add_tenant_modules"
down_revision = "0033_drop_user_role_and_menus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column(
            "disabled_modules", sa.JSON(), nullable=False, server_default="[]"
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant", "disabled_modules")
