"""add_construction_project_tables

Revision ID: 0013_add_construction_project
Revises: 0012_add_access_control_tables
Create Date: 2026-08-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0013_add_construction_project"
down_revision: Union[str, Sequence[str], None] = "0012_add_access_control_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "construction_project",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contractor_name", sa.String(), nullable=True),
        sa.Column("total_budget", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("executed_budget", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("physical_progress_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("estimated_completion_date", sa.Date(), nullable=True),
        sa.Column("actual_completion_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PLANNED"),
        sa.Column("cover_photo_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_construction_project_title", "construction_project", ["title"])
    op.create_index("ix_construction_project_status", "construction_project", ["status"])

    op.create_table(
        "project_milestone",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("construction_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="NEXT_STEPS"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_milestone_project_id", "project_milestone", ["project_id"])
    op.create_index("ix_project_milestone_status", "project_milestone", ["status"])

    op.create_table(
        "project_update",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("construction_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("photos_json", sa.Text(), nullable=True),
        sa.Column("cost_impact", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_update_project_id", "project_update", ["project_id"])
    op.create_index("ix_project_update_author_id", "project_update", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_project_update_author_id", table_name="project_update")
    op.drop_index("ix_project_update_project_id", table_name="project_update")
    op.drop_table("project_update")

    op.drop_index("ix_project_milestone_status", table_name="project_milestone")
    op.drop_index("ix_project_milestone_project_id", table_name="project_milestone")
    op.drop_table("project_milestone")

    op.drop_index("ix_construction_project_status", table_name="construction_project")
    op.drop_index("ix_construction_project_title", table_name="construction_project")
    op.drop_table("construction_project")
