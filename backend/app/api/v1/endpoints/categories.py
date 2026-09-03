"""Category management API endpoints."""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.category_service import CategoryService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

router = APIRouter()


def _require_category_write_permission(
    current_user: User, session: Session, permission: str
) -> None:
    """Raise 403 unless the caller holds this route's category permission."""
    if not api_deps.has_permission(current_user, session, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMINISTRATOR and DIRECTOR can manage categories",
        )


@router.get("/", response_model=list[CategoryRead])
def list_categories(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[  # noqa: ARG001
        User, Depends(api_deps.get_current_user)
    ],
) -> list[CategoryRead]:
    """List every active category. Any authenticated caller.

    The dependency stays even though the handler no longer reads it: it is
    what makes the route authenticated. IAM F5 (APRAS-49 §4.1) removed the
    the `assert_menu_access(...)` line that used to consume it.
    """
    return CategoryService.get_categories(session=session)


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> CategoryRead:
    """Create a new category. ADMINISTRATOR and DIRECTOR only."""
    _require_category_write_permission(current_user, session, "categories:create")
    return CategoryService.create_category(session=session, category_in=category_in)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: UUID,
    category_in: CategoryUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> CategoryRead:
    """Update a category. ADMINISTRATOR and DIRECTOR only."""
    _require_category_write_permission(current_user, session, "categories:update")
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryService.update_category(
        session=session, db_category=db_category, category_in=category_in
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Deactivate a category. ADMINISTRATOR and DIRECTOR only."""
    _require_category_write_permission(current_user, session, "categories:delete")
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    CategoryService.delete_category(session=session, db_category=db_category)
