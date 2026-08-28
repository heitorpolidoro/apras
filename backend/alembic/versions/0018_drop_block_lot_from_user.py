"""drop_block_lot_from_user

Revision ID: 0018_drop_block_lot_from_user
Revises: 0017_add_user_type_allowed_menus
Create Date: 2026-08-27 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0018_drop_block_lot_from_user"
down_revision: Union[str, Sequence[str], None] = "0017_add_user_type_allowed_menus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the orphaned User.block_lot column.

    Fully superseded by Lot/UserLotLink for anyone who actually lives in a
    unit. Never populated by any UI path.
    """
    op.drop_column("user", "block_lot")


def downgrade() -> None:
    """Re-add User.block_lot as nullable.

    Data is not recoverable on downgrade - acceptable, since the column has
    never been populated by any UI path.
    """
    op.add_column("user", sa.Column("block_lot", sa.String(), nullable=True))
