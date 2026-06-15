"""Authentication API endpoints."""

from typing import Annotated

from app.api import deps as api_deps
from app.core import security
from app.core.config import settings
from app.core.limiter import limiter
from app.db import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

router = APIRouter()


@router.post("/signup", response_model=UserRead)
def signup(
    session: Annotated[Session, Depends(get_session)],
    user_in: UserCreate,
) -> User:
    """Create new user.

    New users are created as inactive and with GUEST role; an administrator
    must activate them and assign a proper role.
    """
    # Check if username exists
    statement = select(User).where(User.username == user_in.username)
    if session.exec(statement).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username already exists",
        )

    # Check if email exists
    statement = select(User).where(User.email == user_in.email)
    if session.exec(statement).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    db_obj = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=security.get_password_hash(user_in.password),
        # Force role
        role=UserRole.GUEST,
        is_active=False,  # Wait for approval
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


@router.get("/me", response_model=UserRead)
def read_user_me(
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> User:
    """Get current user."""
    return current_user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login_access_token(
    request: Request,  # noqa: ARG001
    session: Annotated[Session, Depends(get_session)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    remember_me: Annotated[bool, Query()] = False,
) -> dict[str, str]:
    """OAuth2 compatible token login, get an access token for future requests.

    Args:
        request: The incoming request object.
        session: Database session.
        form_data: OAuth2 password request form containing username and password.
        remember_me: If True, set expiration to 7 days.

    Returns:
        Any: A dictionary containing the access token and token type.

    Raises:
        HTTPException: If credentials are incorrect or user is inactive.
    """
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

    if not user or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token_expires = security.get_token_expiration(remember_me=remember_me)

    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/dev-users", response_model=list[UserRead])
def get_dev_users(
    session: Annotated[Session, Depends(get_session)],
) -> list[User]:
    """Get all active users for development login bypass.

    Only available when ENVIRONMENT is 'development'.
    """
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    statement = select(User).where(User.is_active)
    return session.exec(statement).all()  # type: ignore


@router.post("/dev-login", response_model=Token)
def dev_login(
    session: Annotated[Session, Depends(get_session)],
    username: str,
    remember_me: Annotated[bool, Query()] = False,
) -> dict[str, str]:
    """Login without password for development purposes.

    Only available when ENVIRONMENT is 'development'.
    """
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token_expires = security.get_token_expiration(remember_me=remember_me)

    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
