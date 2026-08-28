"""Task service layer for business logic."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.models.task import Task, TaskComment, TaskHistory, get_utc_now
from app.schemas.task import TaskCommentRead, TaskCreate, TaskUpdate
from sqlmodel import Session, select

if TYPE_CHECKING:
    from app.models.user import User


class TaskService:
    """Service class for task-related operations."""

    @staticmethod
    def create_task(
        session: Session,
        task_in: TaskCreate,
        created_by_id: UUID,
        current_user: "User",
    ) -> Task:
        """Create a new task in the database."""
        from app.api.deps import get_effective_user_type_ids
        from app.models.enums import UserRole
        from app.models.user_type import UserType

        visible_to_ids = list(task_in.visible_to_ids)
        # If MANAGER is creating a task and hasn't specified any targets,
        # default to their *explicit* UserType ids (current_user.user_types)
        # only — not the full APRAS-9 effective set, which always includes
        # the shared role-type id and would make every auto-defaulted task
        # visible to every Manager org-wide. Fall back to the role-type id
        # alone only when the Manager has zero explicit UserTypes.
        if current_user.role == UserRole.MANAGER and not visible_to_ids:
            explicit_ids = {ut.id for ut in current_user.user_types}
            if explicit_ids:
                visible_to_ids = list(explicit_ids)
            else:
                visible_to_ids = list(
                    get_effective_user_type_ids(current_user, session)
                )

        db_task = Task.model_validate(
            task_in,
            update={"created_by_id": created_by_id, "visible_to": []},
        )
        if visible_to_ids:
            db_task.visible_to = session.exec(
                select(UserType).where(UserType.id.in_(visible_to_ids))
            ).all()

        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        return db_task

    @staticmethod
    def update_task(
        session: Session, db_task: Task, task_in: TaskUpdate, current_user: "User"
    ) -> Task:
        """Update a task with audit logging."""
        from app.api.deps import get_effective_user_type_ids
        from app.core.exceptions import ForbiddenError
        from app.models.enums import UserRole
        from app.models.user_type import UserType

        update_data = task_in.model_dump(exclude_unset=True)
        visible_to_ids = update_data.pop("visible_to_ids", None)

        # MANAGER may only set targets that are a subset of their own
        # effective UserType ids (explicitly-assigned or role-implicit, see
        # APRAS-9) — cannot grant visibility to a type they don't belong to.
        if visible_to_ids is not None and current_user.role == UserRole.MANAGER:
            effective_ids = get_effective_user_type_ids(current_user, session)
            if not set(visible_to_ids) <= effective_ids:
                raise ForbiddenError(
                    "Managers can only set visibility targets they belong to"
                )

        for key, value in update_data.items():
            old_value = getattr(db_task, key)
            if old_value != value:
                history = TaskHistory(
                    task_id=db_task.id,
                    changed_by_id=current_user.id,
                    field_name=key,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(value) if value is not None else None,
                    timestamp=get_utc_now(),
                )
                session.add(history)
                setattr(db_task, key, value)

        if visible_to_ids is not None:
            old_ids = sorted(str(ut.id) for ut in db_task.visible_to)
            new_ids = sorted(str(uid) for uid in visible_to_ids)
            if old_ids != new_ids:
                history = TaskHistory(
                    task_id=db_task.id,
                    changed_by_id=current_user.id,
                    field_name="visible_to",
                    old_value=",".join(old_ids) or None,
                    new_value=",".join(new_ids) or None,
                    timestamp=get_utc_now(),
                )
                session.add(history)
            db_task.visible_to = (
                session.exec(
                    select(UserType).where(UserType.id.in_(visible_to_ids))
                ).all()
                if visible_to_ids
                else []
            )

        db_task.updated_at = get_utc_now()
        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        return db_task

    @staticmethod
    def get_history(session: Session, task_id: UUID) -> list[dict[str, Any]]:
        """Retrieve the audit history for a task.

        For entries where field_name == 'assigned_to_id', the old_value and
        new_value (UUID strings) are resolved to {name, role} dicts in
        resolved_old_value and resolved_new_value respectively.
        """
        from app.models.user import User

        statement = (
            select(TaskHistory, User)
            .join(User, TaskHistory.changed_by_id == User.id)
            .where(TaskHistory.task_id == task_id)
            .order_by(TaskHistory.timestamp.desc())
        )
        results = session.exec(statement).all()
        history_list = []
        for history, user in results:
            item = history.model_dump()
            item["user_name"] = user.full_name or user.username
            if history.field_name == "assigned_to_id":
                item["resolved_old_value"] = TaskService._resolve_user(
                    session, history.old_value
                )
                item["resolved_new_value"] = TaskService._resolve_user(
                    session, history.new_value
                )
            history_list.append(item)
        return history_list

    @staticmethod
    def _resolve_user(session: Session, user_id_str: str | None) -> dict | None:
        """Look up a user by UUID string and return {name, role}, or None."""
        if user_id_str is None or user_id_str == "null":
            return None
        import uuid as _uuid

        from app.models.user import User

        try:
            uid = _uuid.UUID(user_id_str)
        except ValueError:
            return None
        u = session.get(User, uid)
        if u is None:
            return None
        return {"name": u.full_name or u.username, "role": str(u.role)}

    @staticmethod
    def delete_task(session: Session, db_task: Task, changed_by_id: UUID) -> None:
        """Perform soft delete on a task and log it in history."""
        db_task.is_deleted = True
        db_task.updated_at = get_utc_now()

        history = TaskHistory(
            task_id=db_task.id,
            changed_by_id=changed_by_id,
            field_name="is_deleted",
            old_value="False",
            new_value="True",
            timestamp=get_utc_now(),
        )
        session.add(history)
        session.add(db_task)
        session.commit()

    @staticmethod
    def get_task_with_names(session: Session, db_task: Task) -> Any:
        """Enrich a task with creator, assignee and category details for response."""
        from app.models.category import Category
        from app.models.user import User
        from app.schemas.task import TaskRead
        from app.schemas.user_type import UserTypeRead

        # `create_task`/`update_task` commit the `visible_to` link rows via
        # the session, but `db_task.visible_to` may still reflect a stale
        # (pre-commit) state on the Python object; refresh it explicitly so
        # the response reflects the just-persisted targets.
        session.refresh(db_task, attribute_names=["visible_to"])

        creator = session.get(User, db_task.created_by_id)
        assignee = (
            session.get(User, db_task.assigned_to_id)
            if db_task.assigned_to_id
            else None
        )
        category = session.get(Category, db_task.category_id)

        task_data = db_task.model_dump()
        task_data["created_by_name"] = creator.full_name if creator else None
        task_data["assigned_to_name"] = assignee.full_name if assignee else None
        task_data["category_name"] = category.name if category else None
        task_data["category_color"] = category.color if category else None
        task_data["visible_to"] = [
            UserTypeRead.model_validate(ut) for ut in db_task.visible_to
        ]

        return TaskRead.model_validate(task_data)

    # ── Comments ──────────────────────────────────────────────────────────

    @staticmethod
    def get_comments(session: Session, task_id: UUID) -> list[TaskCommentRead]:
        """List all comments for a task, ordered oldest first."""
        from app.models.user import User

        statement = (
            select(TaskComment, User)
            .join(User, TaskComment.created_by_id == User.id)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at.asc())
        )
        results = session.exec(statement).all()
        comments = []
        for comment, user in results:
            data = comment.model_dump()
            data["created_by_name"] = user.full_name or user.username
            comments.append(TaskCommentRead.model_validate(data))
        return comments

    @staticmethod
    def create_comment(
        session: Session, task_id: UUID, content: str, created_by_id: UUID
    ) -> TaskCommentRead:
        """Create a new comment on a task."""
        from app.models.user import User

        comment = TaskComment(
            task_id=task_id,
            created_by_id=created_by_id,
            content=content,
        )
        session.add(comment)
        session.commit()
        session.refresh(comment)

        user = session.get(User, created_by_id)
        data = comment.model_dump()
        data["created_by_name"] = user.full_name or user.username if user else ""
        return TaskCommentRead.model_validate(data)

    @staticmethod
    def update_comment(
        session: Session, comment: TaskComment, content: str
    ) -> TaskCommentRead:
        """Update the content of an existing comment."""
        from app.models.user import User

        comment.content = content
        comment.updated_at = get_utc_now()
        session.add(comment)
        session.commit()
        session.refresh(comment)

        user = session.get(User, comment.created_by_id)
        data = comment.model_dump()
        data["created_by_name"] = user.full_name or user.username if user else ""
        return TaskCommentRead.model_validate(data)
