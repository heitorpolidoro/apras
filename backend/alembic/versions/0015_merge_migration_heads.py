"""merge_0013_branches

Revision ID: 0015_merge_heads
Revises: 0013_add_announcement_tables, 0014_add_resident_userrole
Create Date: 2026-08-27 14:11:10.379153

Merges two migrations that were both authored (concurrently, in separate
branches) as "0013" against the same parent (0012_add_access_control_tables):
0013_add_announcement_tables and 0013_add_construction_project. This is a
no-op merge point with no schema changes of its own.

Note: `alembic downgrade -1` fails here with "Ambiguous walk" -- this is
expected Alembic behavior at merge points (it can't infer which parent
branch to walk into) and is not a bug. Downgrade past this point using an
explicit target, e.g. `alembic downgrade 0014_add_resident_userrole`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0015_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('0013_add_announcement_tables', '0014_add_resident_userrole')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
