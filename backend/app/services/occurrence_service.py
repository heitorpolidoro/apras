"""Occurrence service layer handling business logic and authorization checks."""

from datetime import datetime
import json
from uuid import UUID

from sqlmodel import Session, col, func, or_, select

from app.core.exceptions import (
    OccurrenceAccessForbiddenError,
    OccurrenceNotFoundError,
)
from app.models.enums import (
    OccurrenceCategory,
    OccurrencePriority,
    OccurrenceStatus,
    UserRole,
)
from app.models.lot import Lot
from app.models.occurrence import Occurrence, OccurrenceTimeline
from app.models.user import User
from app.schemas.occurrence import (
    OccurrenceCreate,
    OccurrenceDetailRead,
    OccurrenceRead,
    OccurrenceStatusUpdate,
    OccurrenceTimelineRead,
    TimelineNoteCreate,
)
from app.services.protocol_generator import generate_occurrence_protocol


class OccurrenceService:
    """Service class for Occurrence domain operations."""

    @staticmethod
    def _build_occurrence_read(
        session: Session, current_user: User, occurrence: Occurrence
    ) -> OccurrenceRead:
        """Helper to convert Occurrence model into sanitized OccurrenceRead schema."""
        is_admin_or_director = current_user.role in [
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
        ]

        reporter_user_id = occurrence.reporter_user_id
        reporter_name = None

        if occurrence.is_anonymous and not is_admin_or_director:
            reporter_user_id = None
            reporter_name = "Anônimo"
        elif occurrence.reporter:
            reporter_name = occurrence.reporter.full_name or occurrence.reporter.email

        lot_summary = None
        if occurrence.lot_id:
            lot = session.get(Lot, occurrence.lot_id)
            if lot:
                lot_summary = f"Quadra {lot.block}, Lote {lot.lot_number}"

        assigned_to_name = None
        if occurrence.assigned_to_id:
            assignee = session.get(User, occurrence.assigned_to_id)
            if assignee:
                assigned_to_name = assignee.full_name or assignee.email

        photo_urls = []
        if occurrence.photo_urls_json:
            try:
                photo_urls = json.loads(occurrence.photo_urls_json)
            except Exception:
                photo_urls = []

        return OccurrenceRead(
            id=occurrence.id,
            protocol_number=occurrence.protocol_number,
            lot_id=occurrence.lot_id,
            lot_summary=lot_summary,
            reporter_user_id=reporter_user_id,
            reporter_name=reporter_name,
            is_anonymous=occurrence.is_anonymous,
            is_public=occurrence.is_public,
            category=occurrence.category,
            title=occurrence.title,
            description=occurrence.description,
            photo_urls=photo_urls,
            status=occurrence.status,
            priority=occurrence.priority,
            assigned_to_id=occurrence.assigned_to_id,
            assigned_to_name=assigned_to_name,
            resolution_notes=occurrence.resolution_notes,
            created_at=occurrence.created_at,
            updated_at=occurrence.updated_at,
            resolved_at=occurrence.resolved_at,
        )

    @staticmethod
    def _check_user_access(current_user: User, occurrence: Occurrence) -> bool:
        """Determines if user has read access to the specified occurrence."""
        if current_user.role in [UserRole.ADMINISTRATOR, UserRole.DIRECTOR]:
            return True
        if current_user.role == UserRole.MANAGER:
            return (
                occurrence.assigned_to_id == current_user.id
                or occurrence.reporter_user_id == current_user.id
                or occurrence.is_public
            )
        return occurrence.reporter_user_id == current_user.id or occurrence.is_public

    @classmethod
    def create_occurrence(
        cls, session: Session, current_user: User, occurrence_in: OccurrenceCreate
    ) -> OccurrenceRead:
        """Creates a ticket with auto-generated protocol and initial timeline entry."""
        protocol_number = generate_occurrence_protocol(session)
        photo_urls_json = (
            json.dumps(occurrence_in.photo_urls) if occurrence_in.photo_urls else None
        )

        occurrence = Occurrence(
            protocol_number=protocol_number,
            lot_id=occurrence_in.lot_id,
            reporter_user_id=current_user.id,
            is_anonymous=occurrence_in.is_anonymous,
            is_public=occurrence_in.is_public,
            category=occurrence_in.category,
            title=occurrence_in.title,
            description=occurrence_in.description,
            photo_urls_json=photo_urls_json,
            status=OccurrenceStatus.OPEN,
            priority=OccurrencePriority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(occurrence)
        session.flush()

        # Initial timeline entry
        timeline_entry = OccurrenceTimeline(
            occurrence_id=occurrence.id,
            actor_id=current_user.id,
            status_from=None,
            status_to=OccurrenceStatus.OPEN,
            note="Ocorrência registrada no sistema",
            is_internal_only=False,
            created_at=datetime.utcnow(),
        )
        session.add(timeline_entry)
        session.commit()
        session.refresh(occurrence)

        return cls._build_occurrence_read(session, current_user, occurrence)

    @classmethod
    def get_occurrences(
        cls,
        session: Session,
        current_user: User,
        category: OccurrenceCategory | None = None,
        status: OccurrenceStatus | None = None,
        is_public: bool | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[OccurrenceRead], int]:
        """Lists occurrences visible to current_user with optional filters."""
        query = select(Occurrence)

        # RBAC Filtering
        if current_user.role not in [UserRole.ADMINISTRATOR, UserRole.DIRECTOR]:
            if current_user.role == UserRole.MANAGER:
                query = query.where(
                    or_(
                        Occurrence.assigned_to_id == current_user.id,
                        Occurrence.reporter_user_id == current_user.id,
                        Occurrence.is_public == True,  # noqa: E712
                    )
                )
            else:
                query = query.where(
                    or_(
                        Occurrence.reporter_user_id == current_user.id,
                        Occurrence.is_public == True,  # noqa: E712
                    )
                )

        # Optional filters
        if category:
            query = query.where(Occurrence.category == category)
        if status:
            query = query.where(Occurrence.status == status)
        if is_public is not None:
            query = query.where(Occurrence.is_public == is_public)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Occurrence.protocol_number.ilike(search_pattern),
                    Occurrence.title.ilike(search_pattern),
                    Occurrence.description.ilike(search_pattern),
                )
            )

        # Count total
        subq = query.subquery()
        total_stmt = select(func.count()).select_from(subq)
        total = session.exec(total_stmt).one()

        query = query.order_by(Occurrence.created_at.desc()).offset(skip).limit(limit)
        occurrences = session.exec(query).all()

        items = [
            cls._build_occurrence_read(session, current_user, occ)
            for occ in occurrences
        ]
        return items, total

    @classmethod
    def get_occurrence_by_id(
        cls, session: Session, current_user: User, occurrence_id: UUID
    ) -> OccurrenceDetailRead:
        """Retrieves an occurrence by ID with timeline history if caller has access."""
        occurrence = session.get(Occurrence, occurrence_id)
        if not occurrence:
            raise OccurrenceNotFoundError(occurrence_id)

        if not cls._check_user_access(current_user, occurrence):
            raise OccurrenceAccessForbiddenError

        base_read = cls._build_occurrence_read(session, current_user, occurrence)

        is_admin_or_director = current_user.role in [
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
        ]

        timeline_entries = []
        for entry in occurrence.timeline_entries:
            if entry.is_internal_only and not is_admin_or_director:
                continue

            actor_name = None
            if entry.actor:
                if (
                    occurrence.is_anonymous
                    and entry.actor_id == occurrence.reporter_user_id
                    and not is_admin_or_director
                ):
                    actor_name = "Anônimo"
                else:
                    actor_name = entry.actor.full_name or entry.actor.email

            timeline_entries.append(
                OccurrenceTimelineRead(
                    id=entry.id,
                    occurrence_id=entry.occurrence_id,
                    actor_id=entry.actor_id,
                    actor_name=actor_name,
                    status_from=entry.status_from,
                    status_to=entry.status_to,
                    note=entry.note,
                    is_internal_only=entry.is_internal_only,
                    created_at=entry.created_at,
                )
            )

        timeline_entries.sort(key=lambda x: x.created_at)

        return OccurrenceDetailRead(
            **base_read.model_dump(),
            timeline=timeline_entries,
        )

    @classmethod
    def update_occurrence_status(
        cls,
        session: Session,
        current_user: User,
        occurrence_id: UUID,
        update_in: OccurrenceStatusUpdate,
    ) -> OccurrenceRead:
        """Updates status, priority, assignment, or resolution notes of a ticket."""
        occurrence = session.get(Occurrence, occurrence_id)
        if not occurrence:
            raise OccurrenceNotFoundError(occurrence_id)

        is_admin_or_director = current_user.role in [
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
        ]
        is_assigned = occurrence.assigned_to_id == current_user.id

        if not (is_admin_or_director or is_assigned):
            raise OccurrenceAccessForbiddenError(
                "Only administrators, directors, or assigned staff can update status"
            )

        old_status = occurrence.status
        status_changed = False

        if update_in.status and update_in.status != old_status:
            occurrence.status = update_in.status
            status_changed = True
            if update_in.status in [
                OccurrenceStatus.RESOLVED,
                OccurrenceStatus.REJECTED,
            ]:
                occurrence.resolved_at = datetime.utcnow()

        if update_in.priority is not None:
            occurrence.priority = update_in.priority

        if update_in.assigned_to_id is not None:
            occurrence.assigned_to_id = update_in.assigned_to_id

        if update_in.resolution_notes is not None:
            occurrence.resolution_notes = update_in.resolution_notes

        occurrence.updated_at = datetime.utcnow()

        # Add timeline entry for update
        note_text = update_in.resolution_notes or (
            f"Status alterado para {occurrence.status.value}"
            if status_changed
            else "Ocorrência atualizada"
        )

        timeline_entry = OccurrenceTimeline(
            occurrence_id=occurrence.id,
            actor_id=current_user.id,
            status_from=old_status if status_changed else None,
            status_to=occurrence.status if status_changed else None,
            note=note_text,
            is_internal_only=False,
            created_at=datetime.utcnow(),
        )
        session.add(timeline_entry)
        session.commit()
        session.refresh(occurrence)

        return cls._build_occurrence_read(session, current_user, occurrence)

    @classmethod
    def add_timeline_note(
        cls,
        session: Session,
        current_user: User,
        occurrence_id: UUID,
        note_in: TimelineNoteCreate,
    ) -> OccurrenceTimelineRead:
        """Appends a timeline note or status transition log to an occurrence."""
        occurrence = session.get(Occurrence, occurrence_id)
        if not occurrence:
            raise OccurrenceNotFoundError(occurrence_id)

        if not cls._check_user_access(current_user, occurrence):
            raise OccurrenceAccessForbiddenError

        is_admin_or_director = current_user.role in [
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
        ]
        is_internal = note_in.is_internal_only if is_admin_or_director else False

        status_from = None
        status_to = None

        if note_in.status_to and note_in.status_to != occurrence.status:
            status_from = occurrence.status
            status_to = note_in.status_to
            occurrence.status = note_in.status_to
            if note_in.status_to in [
                OccurrenceStatus.RESOLVED,
                OccurrenceStatus.REJECTED,
            ]:
                occurrence.resolved_at = datetime.utcnow()

        occurrence.updated_at = datetime.utcnow()

        timeline_entry = OccurrenceTimeline(
            occurrence_id=occurrence.id,
            actor_id=current_user.id,
            status_from=status_from,
            status_to=status_to,
            note=note_in.note,
            is_internal_only=is_internal,
            created_at=datetime.utcnow(),
        )

        session.add(timeline_entry)
        session.commit()
        session.refresh(timeline_entry)

        actor_name = current_user.full_name or current_user.email
        if (
            occurrence.is_anonymous
            and current_user.id == occurrence.reporter_user_id
            and not is_admin_or_director
        ):
            actor_name = "Anônimo"

        return OccurrenceTimelineRead(
            id=timeline_entry.id,
            occurrence_id=timeline_entry.occurrence_id,
            actor_id=timeline_entry.actor_id,
            actor_name=actor_name,
            status_from=timeline_entry.status_from,
            status_to=timeline_entry.status_to,
            note=timeline_entry.note,
            is_internal_only=timeline_entry.is_internal_only,
            created_at=timeline_entry.created_at,
        )
