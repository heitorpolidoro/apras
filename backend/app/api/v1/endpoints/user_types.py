"""User type management API endpoints."""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.user import User
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate, UserTypeRead, UserTypeUpdate
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

router = APIRouter()


@router.get("/", response_model=list[UserTypeRead])
def read_user_types(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],  # noqa: ARG001
) -> list[UserType]:
    """Retrieve all user types."""
    return session.exec(select(UserType)).all()


@router.post("/", response_model=UserTypeRead, status_code=status.HTTP_201_CREATED)
def create_user_type(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_active_admin)],  # noqa: ARG001
    user_type_in: UserTypeCreate,
) -> UserType:
    """Create a new user type. Restricted to ADMINISTRATOR."""
    existing = session.exec(
        select(UserType).where(UserType.name == user_type_in.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user type with this name already exists",
        )
    user_type = UserType(
        name=user_type_in.name, allowed_menus=user_type_in.allowed_menus
    )
    session.add(user_type)
    session.commit()
    session.refresh(user_type)
    return user_type


@router.patch("/{user_type_id}", response_model=UserTypeRead)
def update_user_type(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_active_admin)],  # noqa: ARG001
    user_type_id: UUID,
    user_type_in: UserTypeUpdate,
) -> UserType:
    """Update a user type. Restricted to ADMINISTRATOR."""
    db_type = session.get(UserType, user_type_id)
    if not db_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User type not found"
        )
    db_type.name = user_type_in.name
    db_type.allowed_menus = user_type_in.allowed_menus
    session.add(db_type)
    session.commit()
    session.refresh(db_type)
    return db_type


@router.delete("/{user_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_type(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_active_admin)],  # noqa: ARG001
    user_type_id: UUID,
) -> None:
    """Delete a user type. Restricted to ADMINISTRATOR."""
    db_type = session.get(UserType, user_type_id)
    if not db_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User type not found"
        )
    session.delete(db_type)
    session.commit()
