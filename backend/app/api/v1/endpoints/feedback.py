"""API Endpoints for Feedback (Fale Conosco) management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api.deps import get_current_user, require_permission
from app.db import get_session
from app.models.enums import FeedbackCategory, FeedbackStatus
from app.models.user import User
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackRead,
    FeedbackRespond,
    PaginatedFeedbackRead,
)
from app.services.feedback_service import FeedbackService

router = APIRouter()

#: The three APRAS-51 guards, bound once at import.
#:
#: These handlers keep the older `current_user: User = Depends(...)` spelling
#: -- their `db` parameter is defaulted, so an `Annotated` parameter with no
#: default could not follow it -- and a *call* in an argument default is
#: `B008`. Binding the guard to a module-level singleton is exactly the
#: remedy that rule names, and `PermissionRequired` is stateless, so one
#: instance per route is correct.
_require_feedback_read = require_permission("feedback:read")
_require_feedback_create = require_permission("feedback:create")


@router.get("", response_model=PaginatedFeedbackRead)
def list_feedback(
    db: Session = Depends(get_session),
    current_user: User = Depends(_require_feedback_read),
    category: FeedbackCategory | None = Query(default=None),
    status_filter: FeedbackStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedFeedbackRead:
    """Lists feedback submissions visible to current user."""
    items, total = FeedbackService.list_feedback(
        session=db,
        current_user=current_user,
        category=category,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return PaginatedFeedbackRead(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(_require_feedback_create),
) -> FeedbackRead:
    """Creates a new feedback submission. Any authenticated user may submit."""
    return FeedbackService.create_feedback(
        session=db, current_user=current_user, feedback_in=feedback_in
    )


@router.get("/{id}", response_model=FeedbackRead)
def get_feedback(
    id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(_require_feedback_read),
) -> FeedbackRead:
    """Retrieves a feedback submission by ID; flips the seen flag for the reporter."""
    return FeedbackService.get_feedback(
        session=db, current_user=current_user, feedback_id=id
    )


@router.put("/{id}/respond", response_model=FeedbackRead)
def respond_to_feedback(
    id: UUID,
    response_in: FeedbackRespond,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FeedbackRead:
    """Records the board's response to a feedback submission."""
    return FeedbackService.respond_to_feedback(
        session=db, current_user=current_user, feedback_id=id, response_in=response_in
    )
