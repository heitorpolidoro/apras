"""Task management API endpoints."""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.core.exceptions import ForbiddenError, TaskNotFoundError
from app.db import get_session
from app.models.enums import TaskPriority, TaskStatus, UserRole
from app.models.task import Task, TaskComment, TaskHistory
from app.models.user import User
from app.schemas.task import (TaskCommentCreate, TaskCommentRead,
                              TaskCommentUpdate, TaskCreate, TaskHistoryRead,
                              TaskRead, TaskUpdate)
from app.services.task_service import TaskService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

router = APIRouter()


@router.post("/", response_model=TaskRead)
def create_task(
    task_in: TaskCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> TaskRead:
    """Create a new task. Any authenticated user except GUEST can create tasks."""
    if current_user.role == UserRole.GUEST:
        raise ForbiddenError("Guests cannot create tasks")
    db_task = TaskService.create_task(
        session=session,
        task_in=task_in,
        created_by_id=current_user.id,
        manager_visible=(current_user.role == UserRole.MANAGER),
    )
    return TaskService.get_task_with_names(session=session, db_task=db_task)


@router.get("/", response_model=list[TaskRead])
def list_tasks(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    status: Annotated[TaskStatus | None, Query()] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    assigned_to_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
) -> list[TaskRead]:
    """List tasks with optional filters. GUEST sees no tasks."""
    if current_user.role == UserRole.GUEST:
        return []

    from app.models.category import Category
    from sqlalchemy.orm import aliased

    creator_alias = aliased(User)
    assignee_alias = aliased(User)

    statement = (
        select(
            Task,
            creator_alias.full_name,
            assignee_alias.full_name,
            Category.name,
            Category.color,
        )
        .where(Task.is_deleted.is_(False))
        .join(creator_alias, Task.created_by_id == creator_alias.id, isouter=True)
        .join(assignee_alias, Task.assigned_to_id == assignee_alias.id, isouter=True)
        .join(Category, Task.category_id == Category.id, isouter=True)
    )

    if assigned_to_id:
        statement = statement.where(Task.assigned_to_id == assigned_to_id)
    if status:
        statement = statement.where(Task.status == status)
    if priority:
        statement = statement.where(Task.priority == priority)
    if category_id:
        statement = statement.where(Task.category_id == category_id)
    if current_user.role == UserRole.MANAGER:
        statement = statement.where(Task.manager_visible.is_(True))

    results = session.exec(statement).all()
    tasks = []
    for db_task, creator_name, assignee_name, category_name, category_color in results:
        task_data = db_task.model_dump()
        task_data["created_by_name"] = creator_name
        task_data["assigned_to_name"] = assignee_name
        task_data["category_name"] = category_name
        task_data["category_color"] = category_color
        tasks.append(TaskRead.model_validate(task_data))
    return tasks


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> TaskRead:
    """Update an existing task."""
    db_task = session.get(Task, task_id)
    if not db_task or db_task.is_deleted:
        raise TaskNotFoundError(task_id)

    api_deps.assert_manager_can_see_task(current_user, db_task)
    api_deps.assert_can_edit_task(current_user, db_task)

    updated_task = TaskService.update_task(
        session=session, db_task=db_task, task_in=task_in, current_user=current_user
    )
    return TaskService.get_task_with_names(session=session, db_task=updated_task)


@router.get("/{task_id}/history", response_model=list[TaskHistoryRead])
def get_task_history(
    task_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[TaskHistory]:
    """Get the audit history for a specific task."""
    db_task = session.get(Task, task_id)
    if not db_task or db_task.is_deleted:
        raise TaskNotFoundError(task_id)

    api_deps.assert_manager_can_see_task(current_user, db_task)
    return TaskService.get_history(session=session, task_id=task_id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_active_admin)],
) -> None:
    """Delete a task (Soft Delete). Only ADMINISTRATOR can delete tasks."""
    db_task = session.get(Task, task_id)
    if not db_task or db_task.is_deleted:
        raise TaskNotFoundError(task_id)

    TaskService.delete_task(
        session=session, db_task=db_task, changed_by_id=current_user.id
    )


# ── Comments ──────────────────────────────────────────────────────────────────


@router.get("/{task_id}/comments", response_model=list[TaskCommentRead])
def list_comments(
    task_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[TaskCommentRead]:
    """List all comments for a task."""
    db_task = session.get(Task, task_id)
    if not db_task or db_task.is_deleted:
        raise TaskNotFoundError(task_id)

    api_deps.assert_manager_can_see_task(current_user, db_task)
    return TaskService.get_comments(session=session, task_id=task_id)


@router.post(
    "/{task_id}/comments",
    response_model=TaskCommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    task_id: UUID,
    comment_in: TaskCommentCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> TaskCommentRead:
    """Add a comment to a task. Any authenticated user can comment."""
    db_task = session.get(Task, task_id)
    if not db_task or db_task.is_deleted:
        raise TaskNotFoundError(task_id)

    api_deps.assert_manager_can_see_task(current_user, db_task)
    return TaskService.create_comment(
        session=session,
        task_id=task_id,
        content=comment_in.content,
        created_by_id=current_user.id,
    )


@router.patch("/{task_id}/comments/{comment_id}", response_model=TaskCommentRead)
def update_comment(
    task_id: UUID,
    comment_id: UUID,
    comment_in: TaskCommentUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> TaskCommentRead:
    """Edit a comment. Only the comment author can edit it."""
    db_task = session.get(Task, task_id)
    if not db_task or db_task.is_deleted:
        raise TaskNotFoundError(task_id)

    api_deps.assert_manager_can_see_task(current_user, db_task)
    comment = session.get(TaskComment, comment_id)
    if not comment or comment.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    if comment.created_by_id != current_user.id:
        raise ForbiddenError("Only the comment author can edit it")

    return TaskService.update_comment(
        session=session, comment=comment, content=comment_in.content
    )
