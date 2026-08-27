"""add_user_type_allowed_menus

Revision ID: 0017_add_user_type_allowed_menus
Revises: 0016_add_finance_tables
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0017_add_user_type_allowed_menus"
down_revision: Union[str, Sequence[str], None] = "0016_add_finance_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add UserType.allowed_menus as a portable JSON column.

    Deliberately NOT a Postgres ARRAY: ARRAY does not compile against
    SQLite, and backend/tests/conftest.py creates the schema via
    SQLModel.metadata.create_all() against a sqlite:// in-memory engine for
    every test in the backend suite.

    No backfill beyond the column default: every existing row gets `[]`
    (empty), which is the intended disruptive rollout — every
    Director/Manager/Guest/Resident loses Tarefas/Categorias access until
    an Administrator manually grants it per UserType.
    """
    op.add_column(
        "user_type",
        sa.Column(
            "allowed_menus",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    """Drop UserType.allowed_menus."""
    op.drop_column("user_type", "allowed_menus")
