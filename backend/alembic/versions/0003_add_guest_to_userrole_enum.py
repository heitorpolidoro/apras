"""Add GUEST value to userrole enum.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'GUEST'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; skip
    pass
