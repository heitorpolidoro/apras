"""Initial schema (squashed from 0001-0006).

Revision ID: 0001
Revises:
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_type",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_user_type_name", "user_type", ["name"], unique=True)

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMINISTRATOR", "DIRECTOR", "MANAGER", "GUEST", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["type_id"], ["user_type.id"], name="fk_user_type_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)
    op.create_index("ix_user_type_id", "user", ["type_id"], unique=False)

    op.create_table(
        "category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("color", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_category_name"), "category", ["name"], unique=True)

    op.create_table(
        "task",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IN_PROGRESS", "COMPLETED", "CANCELED", "BLOCKED", name="taskstatus"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="taskpriority"),
            nullable=False,
        ),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("manager_visible", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], name="fk_task_category_id_category"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_title"), "task", ["title"], unique=False)
    op.create_index(op.f("ix_task_assigned_to_id"), "task", ["assigned_to_id"], unique=False)
    op.create_index(op.f("ix_task_created_by_id"), "task", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_task_is_deleted"), "task", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_task_priority"), "task", ["priority"], unique=False)
    op.create_index(op.f("ix_task_status"), "task", ["status"], unique=False)
    op.create_index(op.f("ix_task_category_id"), "task", ["category_id"], unique=False)

    op.create_table(
        "taskhistory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("old_value", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("new_value", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "taskcomment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("content", sqlmodel.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_taskcomment_task_id", "taskcomment", ["task_id"])
    op.create_index("ix_taskcomment_created_by_id", "taskcomment", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_taskcomment_created_by_id", table_name="taskcomment")
    op.drop_index("ix_taskcomment_task_id", table_name="taskcomment")
    op.drop_table("taskcomment")
    op.drop_table("taskhistory")
    op.drop_index(op.f("ix_task_category_id"), table_name="task")
    op.drop_index(op.f("ix_task_status"), table_name="task")
    op.drop_index(op.f("ix_task_priority"), table_name="task")
    op.drop_index(op.f("ix_task_is_deleted"), table_name="task")
    op.drop_index(op.f("ix_task_created_by_id"), table_name="task")
    op.drop_index(op.f("ix_task_assigned_to_id"), table_name="task")
    op.drop_index(op.f("ix_task_title"), table_name="task")
    op.drop_table("task")
    op.drop_index(op.f("ix_category_name"), table_name="category")
    op.drop_table("category")
    op.drop_index("ix_user_type_id", table_name="user")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
    op.drop_index("ix_user_type_name", table_name="user_type")
    op.drop_table("user_type")
    sa.Enum(name="taskstatus").drop(op.get_bind())
    sa.Enum(name="taskpriority").drop(op.get_bind())
    sa.Enum(name="userrole").drop(op.get_bind())
