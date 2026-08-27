"""User management API endpoints."""

from typing import Annotated, Any
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.user import User
from app.schemas.user import UserContactInfoUpdate, UserRead, UserUpdate
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

router = APIRouter()


@router.get("/", response_model=list[UserRead])
def read_users(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[  # noqa: ARG001
        User, Depends(api_deps.get_current_user)
    ],
    is_active: bool | None = None,
) -> list[User]:
    """Retrieve users. Available to all authenticated users."""
    statement = select(User)
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    return session.exec(statement).all()


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_active_admin)],
    user_id: UUID,
    user_in: UserUpdate,
) -> User:
    """Update a user.

    Restricted to ADMINISTRATOR.
    Safety check: ADMINISTRATOR cannot deactivate themselves or remove their own role.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Safety check
    if db_user.id == current_user.id:
        if user_in.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate themselves",
            )
        if user_in.role is not None and user_in.role != db_user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot change their own role",
            )

    update_data = user_in.model_dump(exclude_unset=True)

    if "user_type_ids" in update_data:
        user_type_ids = update_data.pop("user_type_ids")
        if user_type_ids is not None:
            db_user.user_types = []
            if user_type_ids:
                from app.models.user_type import UserType
                statement = select(UserType).where(UserType.id.in_(user_type_ids))
                db_user.user_types = session.exec(statement).all()

    for key, value in update_data.items():
        setattr(db_user, key, value)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@router.patch("/{user_id}/contact-info", response_model=UserRead)
def update_user_contact_info(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[  # noqa: ARG001
        User, Depends(api_deps.get_current_admin_or_manager)
    ],
    user_id: UUID,
    user_in: UserContactInfoUpdate,
) -> User:
    """Update a user's phone and address. Administrator or Manager only."""
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user
