"""Add PORTEIRO value to userrole enum.

Revision ID: 0020_add_porteiro_userrole
Revises: 0019_drop_block_lot_from_user
Create Date: 2026-08-27
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "0020_add_porteiro_userrole"
down_revision: Union[str, Sequence[str], None] = "0019_drop_block_lot_from_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'PORTEIRO'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; skip
    pass
