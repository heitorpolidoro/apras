"""add_package_table

Revision ID: 0022_add_package_table
Revises: 0021_add_feedback_table
Create Date: 2026-08-28

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0022_add_package_table"
down_revision: Union[str, Sequence[str], None] = "0021_add_feedback_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "package",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("received_by_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("carrier", sa.String(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("picked_up_at", sa.DateTime(), nullable=True),
        sa.Column("picked_up_by_id", sa.Uuid(), nullable=True),
        sa.Column("picked_up_by_notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["received_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["picked_up_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_package_lot_id", "package", ["lot_id"])
    op.create_index("ix_package_status", "package", ["status"])


def downgrade() -> None:
    op.drop_index("ix_package_status", table_name="package")
    op.drop_index("ix_package_lot_id", table_name="package")
    op.drop_table("package")
