"""Unit and API integration tests for Feedback (Fale Conosco) management."""

import itertools
import uuid

import pytest
from app.core.exceptions import FeedbackAccessForbiddenError, FeedbackNotFoundError
from app.models.enums import FeedbackCategory, FeedbackStatus, UserRole
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackRespond
from app.services.feedback_service import FeedbackService
from fastapi.testclient import TestClient
from sqlmodel import Session

_cpf_counter = itertools.count(10000000001)


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


@pytest.mark.parametrize(
    "role",
    [
        UserRole.ADMINISTRATOR,
        UserRole.DIRECTOR,
        UserRole.MANAGER,
        UserRole.GUEST,
        UserRole.RESIDENT,
    ],
)
def test_create_feedback_succeeds_for_every_role(session: Session, role: UserRole):
    """create_feedback has no role restriction: every role, including GUEST, may submit."""
    user = _make_user(session, role, f"reporter_{role.value.lower()}@example.com")

    feedback_in = FeedbackCreate(
        category=FeedbackCategory.SUGGESTION,
        message="Poderiam instalar mais lixeiras na praça.",
        is_anonymous=False,
    )

    created = FeedbackService.create_feedback(session, user, feedback_in)

    assert created.id is not None
    assert created.category == FeedbackCategory.SUGGESTION
    assert created.message == "Poderiam instalar mais lixeiras na praça."
    assert created.status == FeedbackStatus.PENDING
    assert created.reporter_user_id == user.id
    assert created.reporter_name == user.full_name
    assert created.response_seen_by_reporter is False
    assert created.board_response is None


def test_list_feedback_staff_sees_all_others_see_own(
    session: Session, admin_user: User
):
    resident_a = _make_user(session, UserRole.GUEST, "resident_a@example.com")
    resident_b = _make_user(session, UserRole.GUEST, "resident_b@example.com")

    fb_a = FeedbackService.create_feedback(
        session,
        resident_a,
        FeedbackCreate(category=FeedbackCategory.CRITICISM, message="Crítica A"),
    )
    fb_b = FeedbackService.create_feedback(
        session,
        resident_b,
        FeedbackCreate(category=FeedbackCategory.COMPLIMENT, message="Elogio B"),
    )

    # Admin sees everything (categorized inbox)
    admin_items, admin_total = FeedbackService.list_feedback(session, admin_user)
    admin_ids = {item.id for item in admin_items}
    assert admin_total >= 2
    assert fb_a.id in admin_ids
    assert fb_b.id in admin_ids

    # Resident A sees only their own submission
    a_items, a_total = FeedbackService.list_feedback(session, resident_a)
    assert a_total == 1
    assert a_items[0].id == fb_a.id

    # Resident B sees only their own submission
    b_items, b_total = FeedbackService.list_feedback(session, resident_b)
    assert b_total == 1
    assert b_items[0].id == fb_b.id


def test_list_feedback_category_and_status_filters(
    session: Session, admin_user: User
):
    resident = _make_user(session, UserRole.GUEST, "resident_filter@example.com")

    FeedbackService.create_feedback(
        session,
        resident,
        FeedbackCreate(category=FeedbackCategory.OTHER, message="Outro assunto"),
    )
    answered = FeedbackService.create_feedback(
        session,
        resident,
        FeedbackCreate(category=FeedbackCategory.SUGGESTION, message="Sugestão"),
    )
    FeedbackService.respond_to_feedback(
        session,
        admin_user,
        answered.id,
        FeedbackRespond(board_response="Obrigado pela sugestão!"),
    )

    by_category, _ = FeedbackService.list_feedback(
        session, admin_user, category=FeedbackCategory.SUGGESTION
    )
    assert all(item.category == FeedbackCategory.SUGGESTION for item in by_category)

    by_status, _ = FeedbackService.list_feedback(
        session, admin_user, status=FeedbackStatus.ANSWERED
    )
    assert all(item.status == FeedbackStatus.ANSWERED for item in by_status)
    assert any(item.id == answered.id for item in by_status)


def test_get_feedback_not_found(session: Session, admin_user: User):
    with pytest.raises(FeedbackNotFoundError):
        FeedbackService.get_feedback(session, admin_user, uuid.uuid4())


def test_get_feedback_forbidden_for_non_reporter(session: Session):
    resident = _make_user(session, UserRole.GUEST, "resident_owner@example.com")
    other_resident = _make_user(session, UserRole.GUEST, "resident_other@example.com")

    fb = FeedbackService.create_feedback(
        session,
        resident,
        FeedbackCreate(category=FeedbackCategory.OTHER, message="Assunto privado"),
    )

    with pytest.raises(FeedbackAccessForbiddenError):
        FeedbackService.get_feedback(session, other_resident, fb.id)


def test_respond_to_feedback_staff_only(session: Session, admin_user: User):
    resident = _make_user(session, UserRole.GUEST, "resident_respond@example.com")
    other_resident = _make_user(session, UserRole.GUEST, "resident_intruder@example.com")

    fb = FeedbackService.create_feedback(
        session,
        resident,
        FeedbackCreate(category=FeedbackCategory.CRITICISM, message="Reclamação"),
    )

    # Non-staff cannot respond
    with pytest.raises(FeedbackAccessForbiddenError):
        FeedbackService.respond_to_feedback(
            session,
            other_resident,
            fb.id,
            FeedbackRespond(board_response="Tentativa indevida"),
        )

    # Admin/Director can respond
    responded = FeedbackService.respond_to_feedback(
        session,
        admin_user,
        fb.id,
        FeedbackRespond(board_response="Obrigado pelo retorno, vamos avaliar."),
    )
    assert responded.status == FeedbackStatus.ANSWERED
    assert responded.board_response == "Obrigado pelo retorno, vamos avaliar."
    assert responded.responded_by_id == admin_user.id
    assert responded.responded_by_name == admin_user.full_name
    assert responded.responded_at is not None
    assert responded.response_seen_by_reporter is False


def test_respond_to_feedback_not_found(session: Session, admin_user: User):
    with pytest.raises(FeedbackNotFoundError):
        FeedbackService.respond_to_feedback(
            session,
            admin_user,
            uuid.uuid4(),
            FeedbackRespond(board_response="Resposta"),
        )


def test_feedback_api_endpoints(client: TestClient, session: Session):
    from app.core.security import create_access_token

    resident = _make_user(session, UserRole.GUEST, "resident_api@example.com")
    token = create_access_token(subject=resident.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Create via API
    payload = {
        "category": "COMPLIMENT",
        "message": "Parabéns pela organização do evento de fim de ano!",
        "is_anonymous": False,
    }
    response = client.post("/api/v1/feedback", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["category"] == "COMPLIMENT"
    feedback_id = data["id"]

    # List via API
    list_res = client.get("/api/v1/feedback?category=COMPLIMENT", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == feedback_id for item in list_data["items"])

    # Get details via API
    detail_res = client.get(f"/api/v1/feedback/{feedback_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == feedback_id
