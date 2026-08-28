"""add_feedback_table

Revision ID: 0018_add_feedback_table
Revises: 0017_add_user_type_allowed_menus
Create Date: 2026-08-27 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0018_add_feedback_table"
down_revision: Union[str, Sequence[str], None] = "0017_add_user_type_allowed_menus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("board_response", sa.Text(), nullable=True),
        sa.Column("responded_by_id", sa.Uuid(), nullable=True),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("response_seen_by_reporter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["responded_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_reporter_user_id", "feedback", ["reporter_user_id"])
    op.create_index("ix_feedback_category", "feedback", ["category"])
    op.create_index("ix_feedback_status", "feedback", ["status"])


def downgrade() -> None:
    op.drop_index("ix_feedback_status", table_name="feedback")
    op.drop_index("ix_feedback_category", table_name="feedback")
    op.drop_index("ix_feedback_reporter_user_id", table_name="feedback")
    op.drop_table("feedback")
