"""Feedback service layer handling business logic and authorization checks."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.exceptions import FeedbackAccessForbiddenError, FeedbackNotFoundError
from app.models.enums import FeedbackCategory, FeedbackStatus, UserRole
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackRead, FeedbackRespond


class FeedbackService:
    """Service class for Feedback domain operations."""

    @staticmethod
    def _build_feedback_read(
        session: Session, current_user: User, feedback: Feedback
    ) -> FeedbackRead:
        """Helper to convert Feedback model into sanitized FeedbackRead schema."""
        is_admin_or_director = current_user.role in [
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
        ]

        reporter_user_id = feedback.reporter_user_id
        reporter_name = None

        if feedback.is_anonymous and not is_admin_or_director:
            reporter_user_id = None
            reporter_name = "Anônimo"
        elif feedback.reporter:
            reporter_name = feedback.reporter.full_name or feedback.reporter.email

        responded_by_name = None
        if feedback.responded_by_id:
            responder = session.get(User, feedback.responded_by_id)
            if responder:
                responded_by_name = responder.full_name or responder.email

        return FeedbackRead(
            id=feedback.id,
            reporter_user_id=reporter_user_id,
            reporter_name=reporter_name,
            is_anonymous=feedback.is_anonymous,
            category=feedback.category,
            message=feedback.message,
            status=feedback.status,
            board_response=feedback.board_response,
            responded_by_id=feedback.responded_by_id,
            responded_by_name=responded_by_name,
            responded_at=feedback.responded_at,
            response_seen_by_reporter=feedback.response_seen_by_reporter,
            created_at=feedback.created_at,
        )

    @classmethod
    def create_feedback(
        cls, session: Session, current_user: User, feedback_in: FeedbackCreate
    ) -> FeedbackRead:
        """Creates a feedback submission. Any authenticated user may submit."""
        feedback = Feedback(
            reporter_user_id=current_user.id,
            is_anonymous=feedback_in.is_anonymous,
            category=feedback_in.category,
            message=feedback_in.message,
            status=FeedbackStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        session.add(feedback)
        session.commit()
        session.refresh(feedback)

        return cls._build_feedback_read(session, current_user, feedback)

    @classmethod
    def list_feedback(
        cls,
        session: Session,
        current_user: User,
        category: FeedbackCategory | None = None,
        status: FeedbackStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[FeedbackRead], int]:
        """Lists feedback visible to current_user with optional filters.

        Administrators/Directors see everything (the categorized inbox);
        everyone else sees only their own submissions, matched by the raw
        `reporter_user_id` column regardless of `is_anonymous`.
        """
        query = select(Feedback)

        if current_user.role not in [UserRole.ADMINISTRATOR, UserRole.DIRECTOR]:
            query = query.where(Feedback.reporter_user_id == current_user.id)

        if category:
            query = query.where(Feedback.category == category)
        if status:
            query = query.where(Feedback.status == status)

        subq = query.subquery()
        total_stmt = select(func.count()).select_from(subq)
        total = session.exec(total_stmt).one()

        query = query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit)
        items = session.exec(query).all()

        results = [cls._build_feedback_read(session, current_user, f) for f in items]
        return results, total

    @classmethod
    def get_feedback(
        cls, session: Session, current_user: User, feedback_id: UUID
    ) -> FeedbackRead:
        """Retrieves a feedback submission by ID if the caller has access.

        Marks `response_seen_by_reporter = True` when the reporter (not
        staff) views an already-`ANSWERED` item — this is the in-app
        "notification" mechanism.
        """
        feedback = session.get(Feedback, feedback_id)
        if not feedback:
            raise FeedbackNotFoundError(feedback_id)

        is_admin_or_director = current_user.role in [
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
        ]

        if not is_admin_or_director and feedback.reporter_user_id != current_user.id:
            raise FeedbackAccessForbiddenError

        if (
            not is_admin_or_director
            and feedback.status == FeedbackStatus.ANSWERED
            and not feedback.response_seen_by_reporter
        ):
            feedback.response_seen_by_reporter = True
            session.add(feedback)
            session.commit()
            session.refresh(feedback)

        return cls._build_feedback_read(session, current_user, feedback)

    @classmethod
    def respond_to_feedback(
        cls,
        session: Session,
        current_user: User,
        feedback_id: UUID,
        response_in: FeedbackRespond,
    ) -> FeedbackRead:
        """Records the board's response. Administrator/Director only."""
        feedback = session.get(Feedback, feedback_id)
        if not feedback:
            raise FeedbackNotFoundError(feedback_id)

        if current_user.role not in [UserRole.ADMINISTRATOR, UserRole.DIRECTOR]:
            raise FeedbackAccessForbiddenError(
                "Only administrators or directors can respond to feedback"
            )

        feedback.board_response = response_in.board_response
        feedback.responded_by_id = current_user.id
        feedback.responded_at = datetime.utcnow()
        feedback.status = FeedbackStatus.ANSWERED
        feedback.response_seen_by_reporter = False

        session.add(feedback)
        session.commit()
        session.refresh(feedback)

        return cls._build_feedback_read(session, current_user, feedback)
