"""
Authentication and authorization dependencies for the API.
"""

import uuid
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.db import get_session
from app.models.enums import MenuKey, UserRole
from app.models.task import Task
from app.models.user import User
from app.models.user_type import UserType

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str, Depends(reusable_oauth2)],
) -> User:
    """
    Retrieve the current authenticated user from the JWT token.

    Args:
        session: Database session.
        token: JWT access token.

    Returns:
        User: The authenticated user object.

    Raises:
        HTTPException: If token is invalid, expired, or user not found.
    """
    all_keys = [settings.SECRET_KEY, *settings.SECRET_KEYS]
    payload = None

    for key in all_keys:
        try:
            payload = jwt.decode(token, key, algorithms=[settings.ALGORITHM])
            break
        except (jwt.PyJWTError, ValidationError):
            continue

    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )

    if payload is None:
        raise credentials_exception

    try:
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = uuid.UUID(user_id)
    except ValueError as err:
        raise credentials_exception from err
    user = session.get(User, token_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user


get_current_active_user = get_current_user
get_db = get_session


def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Verify the current user has the ADMINISTRATOR role.

    Args:
        current_user: The authenticated user.

    Returns:
        User: The user if they have the administrator role.

    Raises:
        HTTPException: If the user role is not ADMINISTRATOR.
    """
    if current_user.role != UserRole.ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def get_current_admin_or_manager(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Verify the current user has the ADMINISTRATOR or MANAGER role.

    Args:
        current_user: The authenticated user.

    Returns:
        User: The user if they have the administrator or manager role.

    Raises:
        HTTPException: If the user role is neither ADMINISTRATOR nor MANAGER.
    """
    if current_user.role not in (UserRole.ADMINISTRATOR, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def get_effective_user_type_ids(user: User, session: Session) -> set[UUID]:
    """Return the user's effective UserType ids for permission evaluation.

    This is the explicitly-assigned UserType ids (`user.user_types`) plus
    the id of the UserType matching the user's own role, if one exists
    (APRAS-9). The role-matching membership is computed on every call, not
    stored in the `UserUserTypeLink` join table, so a role change takes
    effect immediately with no sync step.

    Args:
        user: The user whose effective UserType ids are being computed.
        session: Database session used to look up the role-matching UserType.

    Returns:
        set[UUID]: The union of explicit and role-implicit UserType ids.
    """
    explicit_ids = {ut.id for ut in user.user_types}
    role_type = session.exec(select(UserType).where(UserType.role == user.role)).first()
    if role_type:
        explicit_ids.add(role_type.id)
    return explicit_ids


def assert_menu_access(current_user: User, menu_key: MenuKey, session: Session) -> None:
    """Raise ForbiddenError unless the user can access the given menu/feature.

    ADMINISTRATOR always passes. Every other role needs at least one
    effective UserType (explicitly-assigned or role-implicit, see
    `get_effective_user_type_ids`) with `menu_key` in its `allowed_menus`.

    Args:
        current_user: The authenticated user making the request.
        menu_key: The menu/feature being accessed (e.g. tasks, categories).
        session: Database session used to resolve effective UserType ids.

    Raises:
        ForbiddenError: If the user does not have access to the menu.
    """
    if current_user.role == UserRole.ADMINISTRATOR:
        return
    effective_ids = get_effective_user_type_ids(current_user, session)
    if effective_ids:
        effective_types = session.exec(
            select(UserType).where(UserType.id.in_(effective_ids))
        ).all()
        if any(menu_key.value in ut.allowed_menus for ut in effective_types):
            return
    raise ForbiddenError(f"Not enough privileges to access {menu_key.value}")


def assert_manager_can_see_task(current_user: User, task: Task, session: Session) -> None:
    """Raise TaskNotFoundError for tasks the user is not allowed to see.

    MANAGER may only access tasks with visible_to_id = None OR visible_to_id
    in their effective UserType ids (explicitly-assigned or role-implicit,
    see `get_effective_user_type_ids`). GUEST may not access any task.

    Args:
        current_user: The authenticated user making the request.
        task: The task being accessed.
        session: Database session used to resolve effective UserType ids.

    Raises:
        TaskNotFoundError: If the task is not visible to the user's role.
    """
    from app.core.exceptions import TaskNotFoundError

    if current_user.role == UserRole.GUEST:
        raise TaskNotFoundError(task.id)
    if current_user.role == UserRole.MANAGER:
        if task.visible_to_id is not None:
            user_type_ids = get_effective_user_type_ids(current_user, session)
            if task.visible_to_id not in user_type_ids:
                raise TaskNotFoundError(task.id)


def assert_can_edit_task(current_user: User, task: Task) -> None:
    """Raise ForbiddenError if the user is not allowed to edit the task.

    ADMINISTRATOR and DIRECTOR may edit any task.
    MANAGER may only edit tasks that are unassigned or assigned to themselves.
    GUEST may not edit any task.

    Args:
        current_user: The authenticated user making the request.
        task: The task being edited.

    Raises:
        ForbiddenError: If the user's role does not allow editing this task.
    """
    if current_user.role == UserRole.GUEST:
        raise ForbiddenError("Guests cannot edit tasks")
    if current_user.role == UserRole.MANAGER:
        if task.assigned_to_id is not None and task.assigned_to_id != current_user.id:
            raise ForbiddenError(
                "Managers can only edit unassigned or self-assigned tasks"
            )
