"""add_occurrence_tables

Revision ID: 0009_add_occurrence_tables
Revises: 0008_add_visitor_tables
Create Date: 2026-08-25 15:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_add_occurrence_tables"
down_revision: Union[str, Sequence[str], None] = "0008_add_visitor_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "occurrence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("protocol_number", sa.String(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("photo_urls_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("protocol_number"),
    )
    op.create_index("ix_occurrence_protocol_number", "occurrence", ["protocol_number"])
    op.create_index("ix_occurrence_lot_id", "occurrence", ["lot_id"])
    op.create_index("ix_occurrence_reporter_user_id", "occurrence", ["reporter_user_id"])
    op.create_index("ix_occurrence_category", "occurrence", ["category"])
    op.create_index("ix_occurrence_status", "occurrence", ["status"])
    op.create_index("ix_occurrence_priority", "occurrence", ["priority"])
    op.create_index("ix_occurrence_assigned_to_id", "occurrence", ["assigned_to_id"])
    op.create_index("ix_occurrence_status_category_public", "occurrence", ["status", "category", "is_public"])

    op.create_table(
        "occurrence_timeline",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("status_from", sa.String(), nullable=True),
        sa.Column("status_to", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("is_internal_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_occurrence_timeline_occurrence_id", "occurrence_timeline", ["occurrence_id"])
    op.create_index("ix_occurrence_timeline_actor_id", "occurrence_timeline", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_occurrence_timeline_actor_id", table_name="occurrence_timeline")
    op.drop_index("ix_occurrence_timeline_occurrence_id", table_name="occurrence_timeline")
    op.drop_table("occurrence_timeline")

    op.drop_index("ix_occurrence_status_category_public", table_name="occurrence")
    op.drop_index("ix_occurrence_assigned_to_id", table_name="occurrence")
    op.drop_index("ix_occurrence_priority", table_name="occurrence")
    op.drop_index("ix_occurrence_status", table_name="occurrence")
    op.drop_index("ix_occurrence_category", table_name="occurrence")
    op.drop_index("ix_occurrence_reporter_user_id", table_name="occurrence")
    op.drop_index("ix_occurrence_lot_id", table_name="occurrence")
    op.drop_index("ix_occurrence_protocol_number", table_name="occurrence")
    op.drop_table("occurrence")
