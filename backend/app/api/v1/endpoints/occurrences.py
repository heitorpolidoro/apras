"""API Endpoints for Occurrence management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models.enums import OccurrenceCategory, OccurrenceStatus, UserRole
from app.models.user import User
from app.schemas.occurrence import (
    OccurrenceCreate,
    OccurrenceDetailRead,
    OccurrenceRead,
    OccurrenceStatusUpdate,
    OccurrenceTimelineRead,
    PaginatedOccurrenceRead,
    TimelineNoteCreate,
)
from app.services.occurrence_service import OccurrenceService

router = APIRouter()


def _assert_not_porteiro(current_user: User) -> None:
    """Raise 403 if the caller is PORTEIRO (gate-only role, no access here)."""
    if current_user.role == UserRole.PORTEIRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )


@router.get("", response_model=PaginatedOccurrenceRead)
def list_occurrences(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    category: OccurrenceCategory | None = Query(default=None),
    status_filter: OccurrenceStatus | None = Query(default=None, alias="status"),
    is_public: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedOccurrenceRead:
    """Lists occurrences visible to current user."""
    _assert_not_porteiro(current_user)
    items, total = OccurrenceService.get_occurrences(
        session=db,
        current_user=current_user,
        category=category,
        status=status_filter,
        is_public=is_public,
        search=search,
        skip=skip,
        limit=limit,
    )
    return PaginatedOccurrenceRead(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=OccurrenceRead, status_code=status.HTTP_201_CREATED)
def create_occurrence(
    occurrence_in: OccurrenceCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OccurrenceRead:
    """Creates a new occurrence ticket."""
    _assert_not_porteiro(current_user)
    return OccurrenceService.create_occurrence(
        session=db, current_user=current_user, occurrence_in=occurrence_in
    )


@router.get("/{id}", response_model=OccurrenceDetailRead)
def get_occurrence(
    id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OccurrenceDetailRead:
    """Retrieves full details and timeline history of an occurrence ticket."""
    _assert_not_porteiro(current_user)
    return OccurrenceService.get_occurrence_by_id(
        session=db, current_user=current_user, occurrence_id=id
    )


@router.put("/{id}/status", response_model=OccurrenceRead)
def update_occurrence_status(
    id: UUID,
    update_in: OccurrenceStatusUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OccurrenceRead:
    """Updates status, priority, assignment, or resolution notes of a ticket."""
    _assert_not_porteiro(current_user)
    return OccurrenceService.update_occurrence_status(
        session=db, current_user=current_user, occurrence_id=id, update_in=update_in
    )


@router.post(
    "/{id}/timeline",
    response_model=OccurrenceTimelineRead,
    status_code=status.HTTP_201_CREATED,
)
def add_timeline_note(
    id: UUID,
    note_in: TimelineNoteCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OccurrenceTimelineRead:
    """Appends a timeline note or status transition entry to an occurrence."""
    _assert_not_porteiro(current_user)
    return OccurrenceService.add_timeline_note(
        session=db, current_user=current_user, occurrence_id=id, note_in=note_in
    )
