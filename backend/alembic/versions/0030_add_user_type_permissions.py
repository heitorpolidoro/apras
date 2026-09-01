"""add permissions bundle to user_type (APRAS-45)

Revision ID: 0030_add_user_type_permissions
Revises: 0029_add_is_tenant_admin
Create Date: 2026-09-01

First slice of the IAM chain (F1): fine permissions live in code
(``app/core/permissions.py``), roles become permission *bundles* stored as
data, and users hold roles N:N. This migration adds the bundle column and
nothing else.

**Nothing is seeded, ever** — not the six role-linked rows, not a default
bundle. That is the user's explicit decision, and it is what makes this
migration exactly reversible: no ``INSERT``, no ``UPDATE``, no data step in
either direction. Transitional compatibility for the roles that exist today
lives in the ``LEGACY_ROLE_PERMISSIONS`` map in code, which slice F5 deletes.

Portable ``sa.JSON`` and not a Postgres ``ARRAY``, copied field for field
from ``0017_add_user_type_allowed_menus``: ``ARRAY`` does not compile against
SQLite, and ``backend/tests/conftest.py`` builds the schema with
``SQLModel.metadata.create_all()`` on a ``sqlite://`` in-memory engine for
every test in the backend suite. The ``server_default`` also back-fills every
pre-existing ``user_type`` row with ``[]`` and keeps writers that never heard
of the column working.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0030_add_user_type_permissions"
down_revision = "0029_add_is_tenant_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_type",
        sa.Column(
            "permissions",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_type", "permissions")
