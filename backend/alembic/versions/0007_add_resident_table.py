"""add_resident_table

Revision ID: 0007_add_resident_table
Revises: 0006_add_lot_and_user_lot_link
Create Date: 2026-08-25 14:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_add_resident_table"
down_revision: Union[str, Sequence[str], None] = "0006_add_lot_and_user_lot_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resident",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("cpf", sa.String(), nullable=False),
        sa.Column("rg", sa.String(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("relationship_type", sa.String(), nullable=False, server_default="TITULAR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resident_lot_id"), "resident", ["lot_id"], unique=False)
    op.create_index(op.f("ix_resident_user_id"), "resident", ["user_id"], unique=False)
    op.create_index(op.f("ix_resident_cpf"), "resident", ["cpf"], unique=False)
    op.create_index(op.f("ix_resident_email"), "resident", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_resident_email"), table_name="resident")
    op.drop_index(op.f("ix_resident_cpf"), table_name="resident")
    op.drop_index(op.f("ix_resident_user_id"), table_name="resident")
    op.drop_index(op.f("ix_resident_lot_id"), table_name="resident")
    op.drop_table("resident")
