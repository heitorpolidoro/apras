"""RBAC, anonymity, and notification-flag tests for Feedback."""

import itertools
import uuid

from app.models.enums import FeedbackCategory, FeedbackStatus, UserRole
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackRespond
from app.services.feedback_service import FeedbackService
from sqlmodel import Session

_cpf_counter = itertools.count(20000000001)


def _next_cpf() -> str:
    """Generates a unique 11-digit CPF-shaped string for test users."""
    return str(next(_cpf_counter))


def _make_user(session: Session, role: UserRole, email: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=f"User {role.value}",
        hashed_password="hash",
        role=role,
        cpf=_next_cpf(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_anonymous_feedback_masked_even_for_reporter(
    session: Session, admin_user: User
):
    """Masking is based on "is the viewer admin/director", not "is the viewer
    the reporter" — a reporter viewing their own anonymous submission still
    gets a masked response.
    """
    resident = _make_user(session, UserRole.GUEST, "resident_anon@example.com")

    fb = FeedbackService.create_feedback(
        session,
        resident,
        FeedbackCreate(
            category=FeedbackCategory.CRITICISM,
            message="Crítica anônima sobre a portaria",
            is_anonymous=True,
        ),
    )

    # Reporter viewing their own anonymous item: still masked
    read_by_reporter = FeedbackService.get_feedback(session, resident, fb.id)
    assert read_by_reporter.reporter_name == "Anônimo"
    assert read_by_reporter.reporter_user_id is None

    # Admin viewing: identity revealed
    read_by_admin = FeedbackService.get_feedback(session, admin_user, fb.id)
    assert read_by_admin.reporter_name == resident.full_name
    assert read_by_admin.reporter_user_id == resident.id


def test_anonymous_feedback_still_found_in_own_history(session: Session):
    """The list filter matches the raw, unmasked reporter_user_id column, so
    a resident can still find their own anonymous submission in their history.
    """
    resident = _make_user(session, UserRole.GUEST, "resident_anon_history@example.com")
    other_resident = _make_user(session, UserRole.GUEST, "resident_other_history@example.com")

    fb = FeedbackService.create_feedback(
        session,
        resident,
        FeedbackCreate(
            category=FeedbackCategory.SUGGESTION,
            message="Sugestão anônima",
            is_anonymous=True,
        ),
    )

    items, total = FeedbackService.list_feedback(session, resident)
    assert total == 1
    assert items[0].id == fb.id
    # Even in their own history listing, the response is still masked.
    assert items[0].reporter_name == "Anônimo"
    assert items[0].reporter_user_id is None

    # Other residents do not see it in their own history at all.
    other_items, other_total = FeedbackService.list_feedback(session, other_resident)
    assert other_total == 0
    assert all(item.id != fb.id for item in other_items)


def test_response_seen_by_reporter_flips_on_view_and_resets_on_new_response(
    session: Session, admin_user: User
):
    resident = _make_user(session, UserRole.GUEST, "resident_notify@example.com")

    fb = FeedbackService.create_feedback(
        session,
        resident,
        FeedbackCreate(category=FeedbackCategory.OTHER, message="Dúvida sobre taxas"),
    )
    assert fb.response_seen_by_reporter is False

    # Viewing a PENDING (unanswered) item never flips the flag.
    unanswered_view = FeedbackService.get_feedback(session, resident, fb.id)
    assert unanswered_view.response_seen_by_reporter is False

    responded = FeedbackService.respond_to_feedback(
        session,
        admin_user,
        fb.id,
        FeedbackRespond(board_response="As taxas seguem o regulamento interno."),
    )
    assert responded.status == FeedbackStatus.ANSWERED
    assert responded.response_seen_by_reporter is False

    # Staff viewing the answered item does NOT flip the reporter's seen flag.
    staff_view = FeedbackService.get_feedback(session, admin_user, fb.id)
    assert staff_view.response_seen_by_reporter is False

    # Reporter's own view of the answered item flips the flag to True.
    reporter_view = FeedbackService.get_feedback(session, resident, fb.id)
    assert reporter_view.response_seen_by_reporter is True

    # A subsequent view remains True (idempotent).
    reporter_view_again = FeedbackService.get_feedback(session, resident, fb.id)
    assert reporter_view_again.response_seen_by_reporter is True

    # A new board response resets the flag so the reporter is notified again.
    responded_again = FeedbackService.respond_to_feedback(
        session,
        admin_user,
        fb.id,
        FeedbackRespond(board_response="Atualização: revisão em andamento."),
    )
    assert responded_again.response_seen_by_reporter is False

    reporter_view_after_new_response = FeedbackService.get_feedback(
        session, resident, fb.id
    )
    assert reporter_view_after_new_response.response_seen_by_reporter is True
