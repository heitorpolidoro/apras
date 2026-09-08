"""API endpoints for Visitor master profile management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api import deps
from app.models.user import User
from app.schemas.visitor import (
    PaginatedVisitorRead,
    VisitorCreate,
    VisitorRead,
    VisitorUpdate,
)
from app.services.visitor_service import VisitorService

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
def list_visitors(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.require_permission("visitors:read"))],  # noqa: ARG001  # FastAPI dependency guard: its only job is the 403
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> PaginatedVisitorRead:
    """Search and list visitors by name, CPF, company, or vehicle plate."""
    visitors, total = VisitorService.search_visitors(
        session, q=q, skip=skip, limit=limit
    )
    items = [VisitorRead.model_validate(v) for v in visitors]
    return PaginatedVisitorRead(items=items, total=total, skip=skip, limit=limit)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_visitor(
    visitor_in: VisitorCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.require_permission("visitors:create"))],  # noqa: ARG001  # FastAPI dependency guard: its only job is the 403
) -> VisitorRead:
    """Create a new visitor master profile."""
    visitor = VisitorService.create_visitor(session, visitor_in)
    return VisitorRead.model_validate(visitor)


@router.get(
    "/{visitor_id}",
    status_code=status.HTTP_200_OK,
)
def get_visitor(
    visitor_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.require_permission("visitors:read"))],  # noqa: ARG001  # FastAPI dependency guard: its only job is the 403
) -> VisitorRead:
    """Get visitor profile by ID."""
    visitor = VisitorService.get_visitor_by_id(session, visitor_id)
    return VisitorRead.model_validate(visitor)


@router.put(
    "/{visitor_id}",
    status_code=status.HTTP_200_OK,
)
def update_visitor(
    visitor_id: UUID,
    visitor_in: VisitorUpdate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.require_permission("visitors:update"))],  # noqa: ARG001  # FastAPI dependency guard: its only job is the 403
) -> VisitorRead:
    """Update visitor profile details."""
    visitor = VisitorService.update_visitor(session, visitor_id, visitor_in)
    return VisitorRead.model_validate(visitor)
