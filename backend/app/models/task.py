"""Database models for Task, TaskComment and TaskHistory."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from .enums import TaskPriority, TaskStatus

if TYPE_CHECKING:
    from .category import Category
    from .user import User
    from .user_type import UserType


class TaskVisibleToLink(SQLModel, table=True):
    """Join table for the many-to-many `Task.visible_to` relationship.

    Matches `UserUserTypeLink`'s shape exactly: composite primary key
    (`task_id`, `user_type_id`), no surrogate `id` column, no
    `ondelete`/`index` annotations (see APRAS-11 spec).
    """

    __tablename__ = "task_visible_to_link"

    task_id: UUID = Field(foreign_key="task.id", primary_key=True)
    user_type_id: UUID = Field(foreign_key="user_type.id", primary_key=True)


def get_utc_now() -> datetime:
    """
    Get the current UTC time.

    Returns:
        datetime: Current datetime in UTC.
    """
    return datetime.now(UTC)


class Task(SQLModel, table=True):
    """
    SQLModel for the Task entity.

    Attributes:
        id: Unique identifier for the task.
        title: Title of the task.
        description: Detailed description.
        status: Current status (PENDING, etc.).
        priority: Task priority (LOW, etc.).
        due_date: Deadline for the task.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        is_deleted: Soft delete flag.
        created_by_id: ID of the user who created the task.
        assigned_to_id: ID of the user assigned to the task.
        category_id: ID of the category for the task.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(index=True)
    description: str | None = None
    status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, index=True)
    due_date: datetime | None = None
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    is_deleted: bool = Field(default=False, index=True)

    USER_ID_FK: ClassVar[str] = "user.id"
    CATEGORY_ID_FK: ClassVar[str] = "category.id"

    # Foreign Keys
    created_by_id: UUID = Field(foreign_key=USER_ID_FK, index=True)
    assigned_to_id: UUID | None = Field(
        default=None, foreign_key=USER_ID_FK, index=True
    )
    category_id: UUID | None = Field(
        default=None, foreign_key=CATEGORY_ID_FK, index=True
    )

    # Relationships
    creator: "User" = Relationship(
        back_populates="created_tasks",
        sa_relationship_kwargs={"foreign_keys": "Task.created_by_id"},
    )
    assignee: Optional["User"] = Relationship(
        back_populates="assigned_tasks",
        sa_relationship_kwargs={"foreign_keys": "Task.assigned_to_id"},
    )
    category: "Category" = Relationship(back_populates="tasks")
    visible_to: list["UserType"] = Relationship(link_model=TaskVisibleToLink)
    history: list["TaskHistory"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    comments: list["TaskComment"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class TaskComment(SQLModel, table=True):
    """
    SQLModel for task comments.

    Attributes:
        id: Unique identifier for the comment.
        task_id: ID of the associated task.
        created_by_id: ID of the user who wrote the comment.
        content: Comment text.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(
        sa_column=Column(
            "task_id",
            ForeignKey("task.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    created_by_id: UUID = Field(foreign_key=Task.USER_ID_FK, index=True)
    content: str
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    # Relationships
    task: "Task" = Relationship(back_populates="comments")
    created_by: "User" = Relationship()


class TaskHistory(SQLModel, table=True):
    """
    SQLModel for tracking changes to Task fields.

    Attributes:
        id: Unique identifier for the history record.
        task_id: ID of the associated task.
        changed_by_id: ID of the user who made the change.
        field_name: Name of the field that was changed.
        old_value: Value before the change.
        new_value: Value after the change.
        timestamp: When the change occurred.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(
        sa_column=Column(
            "task_id", ForeignKey("task.id", ondelete="CASCADE"), nullable=False
        )
    )
    changed_by_id: UUID = Field(foreign_key=Task.USER_ID_FK)
    field_name: str
    old_value: str | None = None
    new_value: str | None = None
    timestamp: datetime = Field(default_factory=get_utc_now)

    # Relationships
    task: "Task" = Relationship(back_populates="history")
    changed_by: "User" = Relationship()
