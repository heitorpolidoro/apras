"""API Endpoints for Occurrence management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import get_current_user, has_permission
from app.db import get_session
from app.models.enums import OccurrenceCategory, OccurrenceStatus
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


def _assert_not_porteiro(current_user: User, session: Session, permission: str) -> None:
    """Raise 403 unless the caller holds this route's own permission.

    Named for the rule it used to spell (PORTEIRO is a gate-only role and
    never reaches this module); each call site now passes the permission of
    *its* route, so a helper shared by a dozen routes does not collapse a
    dozen permissions into one.
    """
    if not has_permission(current_user, session, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )


@router.get("")
def list_occurrences(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    category: Annotated[OccurrenceCategory | None, Query()] = None,
    status_filter: Annotated[OccurrenceStatus | None, Query(alias="status")] = None,
    is_public: Annotated[bool | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedOccurrenceRead:
    """Lists occurrences visible to current user."""
    _assert_not_porteiro(current_user, db, "occurrences:read")
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_occurrence(
    occurrence_in: OccurrenceCreate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OccurrenceRead:
    """Creates a new occurrence ticket."""
    _assert_not_porteiro(current_user, db, "occurrences:create")
    return OccurrenceService.create_occurrence(
        session=db, current_user=current_user, occurrence_in=occurrence_in
    )


@router.get("/{id}")
def get_occurrence(
    id: UUID,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OccurrenceDetailRead:
    """Retrieves full details and timeline history of an occurrence ticket."""
    _assert_not_porteiro(current_user, db, "occurrences:read")
    return OccurrenceService.get_occurrence_by_id(
        session=db, current_user=current_user, occurrence_id=id
    )


@router.put("/{id}/status")
def update_occurrence_status(
    id: UUID,
    update_in: OccurrenceStatusUpdate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OccurrenceRead:
    """Updates status, priority, assignment, or resolution notes of a ticket."""
    _assert_not_porteiro(current_user, db, "occurrences:update_status")
    return OccurrenceService.update_occurrence_status(
        session=db, current_user=current_user, occurrence_id=id, update_in=update_in
    )


@router.post(
    "/{id}/timeline",
    status_code=status.HTTP_201_CREATED,
)
def add_timeline_note(
    id: UUID,
    note_in: TimelineNoteCreate,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OccurrenceTimelineRead:
    """Appends a timeline note or status transition entry to an occurrence."""
    _assert_not_porteiro(current_user, db, "occurrences:add_note")
    return OccurrenceService.add_timeline_note(
        session=db, current_user=current_user, occurrence_id=id, note_in=note_in
    )
