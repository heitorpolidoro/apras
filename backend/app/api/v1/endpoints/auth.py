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
    # Check if email exists
    statement = select(User).where(User.email == user_in.email)
    if session.exec(statement).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    db_obj = User(
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
    username = form_data.username
    if "@" not in username:
        statement = select(User).where(User.email.like(f"{username}@%"))
    else:
        statement = select(User).where(User.email == username)
    user = session.exec(statement).first()

    if not user or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
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
    email: str | None = None,
    username: str | None = None,
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

    identifier = email or username
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email or username is required",
        )

    if "@" not in identifier:
        statement = select(User).where(User.email.like(f"{identifier}@%"))
    else:
        statement = select(User).where(User.email == identifier)
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


from app.schemas.token import ForgotPasswordRequest, ResetPasswordRequest
import httpx
import os

@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    """Request password reset link.

    Generates a JWT token for password reset and sends it via Resend API
    (if RESEND_API_KEY is present) or logs it to stdout.
    """
    statement = select(User).where(User.email == body.email.strip())
    user = session.exec(statement).first()

    # Always return success response to prevent user enumeration
    if not user:
        return {"message": "If the email is registered, a password reset link has been sent."}

    # Generate password reset token
    token = security.create_password_reset_token(user.email)
    
    # We use the request origin or construct it from headers
    origin = request.headers.get("origin") or "http://localhost:5173"
    reset_url = f"{origin}/reset-password?token={token}"

    resend_api_key = os.getenv("RESEND_API_KEY")
    if resend_api_key:
        try:
            async with httpx.AsyncClient() as client:
                email_payload = {
                    "from": os.getenv("EMAIL_FROM", "onboarding@resend.dev"),
                    "to": user.email,
                    "subject": "Recuperação de Senha - APRAS",
                    "html": f"""
                    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
                      <h2 style="color: #059669; margin-top: 0;">APRAS</h2>
                      <p>Olá, {user.full_name or 'usuário'}!</p>
                      <p>Recebemos uma solicitação para redefinir sua senha. Clique no botão abaixo para escolher uma nova:</p>
                      <div style="margin: 24px 0;">
                        <a href="{reset_url}" style="background-color: #059669; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Redefinir Senha</a>
                      </div>
                      <p style="color: #6b7280; font-size: 14px;">Se você não solicitou isso, pode ignorar este e-mail com segurança.</p>
                      <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 20px 0;" />
                      <p style="color: #9ca3af; font-size: 12px;">Este link irá expirar em 15 minutos.</p>
                    </div>
                    """
                }
                headers = {
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                }
                response = await client.post("https://api.resend.com/emails", json=email_payload, headers=headers)
                response.raise_for_status()
        except Exception as e:
            print(f"Failed to send email via Resend: {e}")
            print(f"[AUTH] Password reset requested for user: {user.email}")
            print(f"[AUTH] Reset URL: {reset_url}")
    else:
        print(f"[AUTH] Password reset requested for user: {user.email}")
        print(f"[AUTH] Reset URL: {reset_url}")

    return {"message": "If the email is registered, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    """Reset password using a JWT reset token."""
    email = security.verify_password_reset_token(body.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de redefinição de senha inválido ou expirado.",
        )

    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # Update password and hash it
    user.hashed_password = security.get_password_hash(body.new_password)
    session.add(user)
    session.commit()

    return {"message": "Senha redefinida com sucesso."}
