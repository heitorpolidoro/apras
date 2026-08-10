"""add_profile_fields_to_user

Revision ID: 0005_add_profile_fields_to_user
Revises: 0004_add_cpf_to_user
Create Date: 2026-08-10 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_add_profile_fields_to_user"
down_revision: Union[str, Sequence[str], None] = "0004_add_cpf_to_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("user", sa.Column("address", sa.String(), nullable=True))
    op.add_column("user", sa.Column("block_lot", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "block_lot")
    op.drop_column("user", "address")
    op.drop_column("user", "phone")
