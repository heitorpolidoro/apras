"""Add RESIDENT value to userrole enum.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-27
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "0014_add_resident_userrole"
down_revision: Union[str, Sequence[str], None] = "0013_add_construction_project"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'RESIDENT'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; skip
    pass
