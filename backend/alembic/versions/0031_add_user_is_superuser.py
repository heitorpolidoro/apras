"""add is_superuser to user (APRAS-47)

Revision ID: 0031_add_user_is_superuser
Revises: 0030_add_user_type_permissions
Create Date: 2026-09-01

Third slice of the IAM chain (F3): the ADMINISTRATOR *role* stops being the
source of global power and a real ``user.is_superuser`` column takes over.

The flag lives on ``user`` (global identity) and not on ``user_tenant_link``,
which is the whole distinction between it and ``is_tenant_admin`` (APRAS-43)
and what makes "administrator in *any* tenant" expressible at all.

The ``server_default`` keeps the ORM/SQLite schema
(``SQLModel.metadata.create_all()`` in ``backend/tests/conftest.py``) and this
Postgres schema in agreement, and lets pre-existing writers that never heard
of the column keep inserting.

Reversible in exactly the sense ``0029`` and ``0030`` are: the column and the
data it carries go together, so the downgrade leaves nothing stranded and has
nothing to restore into.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0031_add_user_is_superuser"
down_revision = "0030_add_user_type_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Every administrator that exists when this migration runs *is* the global
    # superuser today: `get_current_active_admin`, `_resolve_from_header`,
    # `TenantService.list_tenants` and `get_visible_tenant` all read
    # `role == ADMINISTRATOR` at 0030. Converting them is what makes the swap
    # in `deps` a no-op for existing installs.
    #
    # `"user"` is quoted (reserved word in Postgres) and `role` is cast with
    # `::text` (it is the native `userrole` enum, extended by 0012 / 0020).
    op.execute(
        """UPDATE "user" SET is_superuser = true """
        """WHERE role::text = 'ADMINISTRATOR'"""
    )


def downgrade() -> None:
    op.drop_column("user", "is_superuser")
