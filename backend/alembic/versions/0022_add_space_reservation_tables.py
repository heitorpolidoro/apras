"""add_space_reservation_tables

Revision ID: 0022_add_space_reservation_tables
Revises: 0021_add_feedback_table
Create Date: 2026-08-28 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0022_add_space_reservation_tables"
down_revision: Union[str, Sequence[str], None] = "0021_add_feedback_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reservable_space",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_reservable_space_name", "reservable_space", ["name"])

    op.create_table(
        "space_reservation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("reserved_by_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["space_id"], ["reservable_space.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reserved_by_id"], ["user.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["decided_by_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_space_reservation_space_id", "space_reservation", ["space_id"]
    )
    op.create_index(
        "ix_space_reservation_reserved_by_id",
        "space_reservation",
        ["reserved_by_id"],
    )
    op.create_index(
        "ix_space_reservation_lot_id", "space_reservation", ["lot_id"]
    )
    op.create_index(
        "ix_space_reservation_start_time", "space_reservation", ["start_time"]
    )
    op.create_index(
        "ix_space_reservation_status", "space_reservation", ["status"]
    )
    # Composite index supporting the double-booking overlap query
    # (WHERE space_id = ? AND status IN (...) AND ...).
    op.create_index(
        "ix_space_reservation_space_status_time",
        "space_reservation",
        ["space_id", "status", "start_time", "end_time"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_space_reservation_space_status_time", table_name="space_reservation"
    )
    op.drop_index("ix_space_reservation_status", table_name="space_reservation")
    op.drop_index(
        "ix_space_reservation_start_time", table_name="space_reservation"
    )
    op.drop_index("ix_space_reservation_lot_id", table_name="space_reservation")
    op.drop_index(
        "ix_space_reservation_reserved_by_id", table_name="space_reservation"
    )
    op.drop_index("ix_space_reservation_space_id", table_name="space_reservation")
    op.drop_table("space_reservation")

    op.drop_index("ix_reservable_space_name", table_name="reservable_space")
    op.drop_table("reservable_space")
