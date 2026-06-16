"""Remove username column from user table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_user_username", table_name="user")
    op.drop_column("user", "username")


def downgrade() -> None:
    op.add_column(
        "user",
        sa.Column("username", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)
