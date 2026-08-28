"""Task.visible_to becomes many-to-many via task_visible_to_link

Revision ID: 0021_task_visible_to_many_to_many
Revises: 0020_add_porteiro_userrole
Create Date: 2026-08-27

Replaces the single nullable `task.visible_to_id` FK with a
`task_visible_to_link` join table, so a task can be targeted at zero or
more UserTypes instead of at most one. Follows the same
INSERT-then-drop-column upgrade / lossy-LIMIT-1 downgrade pattern used by
`3f75bcd3d49f_many_to_many_user_types_and_task_.py` when it introduced the
single-FK `visible_to_id` column being replaced here.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_task_visible_to_m2m"
down_revision: Union[str, Sequence[str], None] = "0020_add_porteiro_userrole"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_visible_to_link",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("user_type_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"]),
        sa.ForeignKeyConstraint(["user_type_id"], ["user_type.id"]),
        sa.PrimaryKeyConstraint("task_id", "user_type_id"),
    )

    # Backfill: every existing task with a non-null visible_to_id becomes a
    # single-row target in the new join table.
    op.execute(
        "INSERT INTO task_visible_to_link (task_id, user_type_id) "
        "SELECT id, visible_to_id FROM task WHERE visible_to_id IS NOT NULL"
    )

    op.drop_constraint(op.f("task_visible_to_id_fkey"), "task", type_="foreignkey")
    op.drop_index(op.f("ix_task_visible_to_id"), table_name="task")
    op.drop_column("task", "visible_to_id")


def downgrade() -> None:
    op.add_column("task", sa.Column("visible_to_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_task_visible_to_id"), "task", ["visible_to_id"], unique=False
    )
    op.create_foreign_key(
        op.f("task_visible_to_id_fkey"),
        "task",
        "user_type",
        ["visible_to_id"],
        ["id"],
    )

    # Lossy: picks one arbitrary target per task if multiple exist. Any
    # target beyond the first is lost on downgrade — acceptable for a
    # downgrade path, not a normal operation.
    op.execute(
        "UPDATE task SET visible_to_id = ("
        "SELECT user_type_id FROM task_visible_to_link "
        "WHERE task_visible_to_link.task_id = task.id LIMIT 1)"
    )

    op.drop_table("task_visible_to_link")
