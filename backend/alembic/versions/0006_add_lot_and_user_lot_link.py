"""add_lot_and_user_lot_link

Revision ID: 0006_add_lot_and_user_lot_link
Revises: 0005_add_profile_fields_to_user
Create Date: 2026-08-24 04:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_add_lot_and_user_lot_link"
down_revision: Union[str, Sequence[str], None] = "0005_add_profile_fields_to_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lot",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("block", sa.String(), nullable=False),
        sa.Column("lot_number", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("postal_code", sa.String(), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("fraction_ideal", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="VACANT"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("block", "lot_number", name="uq_lot_block_lot_number"),
    )
    op.create_index(op.f("ix_lot_block"), "lot", ["block"], unique=False)
    op.create_index(op.f("ix_lot_lot_number"), "lot", ["lot_number"], unique=False)

    op.create_table(
        "user_lot_link",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("association_type", sa.String(), nullable=False, server_default="PROPRIETARIO"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lot_id", name="uq_user_lot_link_user_lot"),
    )
    op.create_index(op.f("ix_user_lot_link_user_id"), "user_lot_link", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_lot_link_lot_id"), "user_lot_link", ["lot_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_lot_link_lot_id"), table_name="user_lot_link")
    op.drop_index(op.f("ix_user_lot_link_user_id"), table_name="user_lot_link")
    op.drop_table("user_lot_link")
    op.drop_index(op.f("ix_lot_lot_number"), table_name="lot")
    op.drop_index(op.f("ix_lot_block"), table_name="lot")
    op.drop_table("lot")
