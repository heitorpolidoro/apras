"""add is_tenant_admin to user_tenant_link (APRAS-43)

Revision ID: 0029_add_is_tenant_admin
Revises: 0028_add_tenant_and_membership
Create Date: 2026-08-31

Third slice of the multi-tenant chain APRAS-41 -> APRAS-42 -> APRAS-43 ->
APRAS-38: administrator-level permission restricted to a single tenant.

The capability lives on the *membership* row, not on ``user.role``: a user is
one global identity in many tenants, so a síndico who administers condominium
A and merely lives in condominium B needs a different answer per tenant. That
is exactly the shape APRAS-41 anticipated when it gave ``user_tenant_link`` a
surrogate ``id`` primary key.

Every existing membership row — including the ones ``0028`` backfilled for
every pre-existing user — becomes a plain member, which is the correct and
only safe default. The ``server_default`` also keeps the ORM/SQLite schema
(``SQLModel.metadata.create_all()``) and this Postgres schema in agreement,
and lets pre-existing writers that never heard of the column keep inserting.

Genuinely reversible: no data migration in either direction. The role-type
re-seed the same task needs (``TenantService.ensure_role_types``) is
deliberately *not* done here — it would add an irreversible ``INSERT`` step
to an otherwise perfectly reversible migration, and ``python -m app.seed`` is
the documented recovery path instead.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0029_add_is_tenant_admin"
down_revision = "0028_add_tenant_and_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_tenant_link",
        sa.Column(
            "is_tenant_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_tenant_link", "is_tenant_admin")
