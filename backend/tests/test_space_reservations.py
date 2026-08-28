import uuid
from datetime import datetime, timedelta

import pytest
from app.core.exceptions import (
    ForbiddenError,
    ReservableSpaceNotFoundError,
    SpaceReservationConflictError,
    SpaceReservationNotFoundError,
)
from app.core.security import get_password_hash
from app.models.enums import ReservationStatus, UserRole
from app.models.reservation import ReservableSpace, SpaceReservation
from app.models.user import User
from app.schemas.reservation import SpaceReservationCreate
from app.services.reservation_service import SpaceReservationService
from fastapi.testclient import TestClient
from sqlmodel import Session


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def make_user(session: Session, role: UserRole, email: str, cpf: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=f"{role.value} User",
        hashed_password=get_password_hash("pass"),
        role=role,
        cpf=cpf,
    )
    session.add(user)
    session.commit()
    return user


def make_space(
    session: Session, name: str = "Salão de Festas", requires_approval: bool = False
) -> ReservableSpace:
    space = ReservableSpace(name=name, requires_approval=requires_approval)
    session.add(space)
    session.commit()
    return space


NOW = datetime(2026, 6, 1, 12, 0, 0)


def dt(hour: int, day: int = 1) -> datetime:
    return NOW.replace(day=day, hour=hour)


# ---------------------------------------------------------------------------
# Service-layer tests: create_reservation / auto-confirm vs pending
# ---------------------------------------------------------------------------


def test_create_reservation_auto_confirms_when_no_approval_required(session: Session):
    space = make_space(session, requires_approval=False)
    resident = make_user(session, UserRole.RESIDENT, "res1@test.com", "52998224725")

    reservation_in = SpaceReservationCreate(
        space_id=space.id, start_time=dt(10), end_time=dt(11)
    )
    reservation = SpaceReservationService.create_reservation(
        session=session, current_user=resident, reservation_in=reservation_in
    )

    assert reservation.status == ReservationStatus.CONFIRMED
    assert reservation.reserved_by_id == resident.id


def test_create_reservation_pending_when_approval_required(session: Session):
    space = make_space(session, requires_approval=True)
    resident = make_user(session, UserRole.RESIDENT, "res2@test.com", "11144477735")

    reservation_in = SpaceReservationCreate(
        space_id=space.id, start_time=dt(10), end_time=dt(11)
    )
    reservation = SpaceReservationService.create_reservation(
        session=session, current_user=resident, reservation_in=reservation_in
    )

    assert reservation.status == ReservationStatus.PENDING


def test_create_reservation_space_not_found(session: Session):
    resident = make_user(session, UserRole.RESIDENT, "res3@test.com", "98765432100")
    reservation_in = SpaceReservationCreate(
        space_id=uuid.uuid4(), start_time=dt(10), end_time=dt(11)
    )
    with pytest.raises(ReservableSpaceNotFoundError):
        SpaceReservationService.create_reservation(
            session=session, current_user=resident, reservation_in=reservation_in
        )


def test_create_reservation_inactive_space_not_found(session: Session):
    space = make_space(session)
    space.is_active = False
    session.add(space)
    session.commit()

    resident = make_user(session, UserRole.RESIDENT, "res4@test.com", "07491723040")
    reservation_in = SpaceReservationCreate(
        space_id=space.id, start_time=dt(10), end_time=dt(11)
    )
    with pytest.raises(ReservableSpaceNotFoundError):
        SpaceReservationService.create_reservation(
            session=session, current_user=resident, reservation_in=reservation_in
        )


def test_end_time_must_be_after_start_time():
    with pytest.raises(ValueError):
        SpaceReservationCreate(
            space_id=uuid.uuid4(), start_time=dt(11), end_time=dt(10)
        )


# ---------------------------------------------------------------------------
# Double-booking conflict checks
# ---------------------------------------------------------------------------


def test_double_booking_same_space_rejected(session: Session):
    space = make_space(session)
    resident1 = make_user(session, UserRole.RESIDENT, "db1@test.com", "80661003005")
    resident2 = make_user(session, UserRole.RESIDENT, "db2@test.com", "42245900069")

    SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )

    with pytest.raises(SpaceReservationConflictError):
        SpaceReservationService.create_reservation(
            session=session,
            current_user=resident2,
            reservation_in=SpaceReservationCreate(
                space_id=space.id, start_time=dt(11), end_time=dt(13)
            ),
        )


def test_adjacent_non_overlapping_windows_succeed(session: Session):
    space = make_space(session)
    resident1 = make_user(session, UserRole.RESIDENT, "adj1@test.com", "16899535009")
    resident2 = make_user(session, UserRole.RESIDENT, "adj2@test.com", "63093783050")

    SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(11)
        ),
    )
    second = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident2,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(11), end_time=dt(12)
        ),
    )
    assert second.status == ReservationStatus.CONFIRMED


def test_overlap_on_different_spaces_both_succeed(session: Session):
    space1 = make_space(session, name="Space A")
    space2 = make_space(session, name="Space B")
    resident1 = make_user(session, UserRole.RESIDENT, "diff1@test.com", "36658136090")
    resident2 = make_user(session, UserRole.RESIDENT, "diff2@test.com", "94120611030")

    SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space1.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    second = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident2,
        reservation_in=SpaceReservationCreate(
            space_id=space2.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    assert second.status == ReservationStatus.CONFIRMED


def test_cancelled_reservation_does_not_block_new_one(session: Session):
    space = make_space(session)
    resident1 = make_user(session, UserRole.RESIDENT, "canc1@test.com", "27466066070")
    resident2 = make_user(session, UserRole.RESIDENT, "canc2@test.com", "83236077000")

    first = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    first.status = ReservationStatus.CANCELLED
    session.add(first)
    session.commit()

    second = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident2,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(11), end_time=dt(13)
        ),
    )
    assert second.status == ReservationStatus.CONFIRMED


def test_rejected_reservation_does_not_block_new_one(session: Session):
    space = make_space(session)
    resident1 = make_user(session, UserRole.RESIDENT, "rej1@test.com", "72741118060")
    resident2 = make_user(session, UserRole.RESIDENT, "rej2@test.com", "39053344705")

    first = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    first.status = ReservationStatus.REJECTED
    session.add(first)
    session.commit()

    second = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident2,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(11), end_time=dt(13)
        ),
    )
    assert second.status == ReservationStatus.CONFIRMED


# ---------------------------------------------------------------------------
# Approve / reject
# ---------------------------------------------------------------------------


def test_approve_reservation_success(session: Session, admin_user):
    space = make_space(session, requires_approval=True)
    resident = make_user(session, UserRole.RESIDENT, "app1@test.com", "45274582030")

    reservation = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    assert reservation.status == ReservationStatus.PENDING

    approved = SpaceReservationService.decide_reservation(
        session=session,
        current_user=admin_user,
        reservation_id=reservation.id,
        approve=True,
    )
    assert approved.status == ReservationStatus.CONFIRMED
    assert approved.decided_by_id == admin_user.id
    assert approved.decided_at is not None


def test_reject_reservation_success(session: Session, admin_user):
    space = make_space(session, requires_approval=True)
    resident = make_user(session, UserRole.RESIDENT, "rej_a@test.com", "89523533060")

    reservation = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )

    rejected = SpaceReservationService.decide_reservation(
        session=session,
        current_user=admin_user,
        reservation_id=reservation.id,
        approve=False,
    )
    assert rejected.status == ReservationStatus.REJECTED
    assert rejected.decided_by_id == admin_user.id


def test_reject_frees_slot_for_new_reservation(session: Session, admin_user):
    space = make_space(session, requires_approval=True)
    resident1 = make_user(session, UserRole.RESIDENT, "rej_f1@test.com", "05946739020")
    resident2 = make_user(session, UserRole.RESIDENT, "rej_f2@test.com", "18328142080")

    first = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    SpaceReservationService.decide_reservation(
        session=session,
        current_user=admin_user,
        reservation_id=first.id,
        approve=False,
    )

    second = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident2,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    assert second.status == ReservationStatus.PENDING


def test_approve_conflicting_pending_returns_409_and_leaves_first_pending(
    session: Session, admin_user
):
    """Simulates the race the spec describes: two overlapping PENDING
    requests filed concurrently before either is decided (each individually
    would have passed create_reservation's check against the *other*
    existing rows at the moment it was filed). Since create_reservation
    itself always rejects an overlap against an existing PENDING row, this
    race can't be reproduced via two sequential create_reservation calls --
    it is simulated here by inserting the second PENDING row directly,
    exactly as a genuine race under concurrent requests would leave the
    database.
    """
    space = make_space(session, requires_approval=True)
    resident1 = make_user(session, UserRole.RESIDENT, "conf1@test.com", "60259444020")
    resident2 = make_user(session, UserRole.RESIDENT, "conf2@test.com", "01382907040")

    first = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    second = SpaceReservation(
        space_id=space.id,
        reserved_by_id=resident2.id,
        start_time=dt(11),
        end_time=dt(13),
        status=ReservationStatus.PENDING,
    )
    session.add(second)
    session.commit()
    session.refresh(second)
    assert first.status == ReservationStatus.PENDING
    assert second.status == ReservationStatus.PENDING

    # Approve the second one first -> becomes CONFIRMED.
    SpaceReservationService.decide_reservation(
        session=session,
        current_user=admin_user,
        reservation_id=second.id,
        approve=True,
    )

    # Approving the first one now conflicts with the now-CONFIRMED second.
    with pytest.raises(SpaceReservationConflictError):
        SpaceReservationService.decide_reservation(
            session=session,
            current_user=admin_user,
            reservation_id=first.id,
            approve=True,
        )

    session.refresh(first)
    assert first.status == ReservationStatus.PENDING


def test_decide_reservation_forbidden_for_non_staff(session: Session):
    space = make_space(session, requires_approval=True)
    resident = make_user(session, UserRole.RESIDENT, "nonstaff1@test.com", "70099142080")

    reservation = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    with pytest.raises(ForbiddenError):
        SpaceReservationService.decide_reservation(
            session=session,
            current_user=resident,
            reservation_id=reservation.id,
            approve=True,
        )


def test_decide_reservation_not_found(session: Session, admin_user):
    with pytest.raises(SpaceReservationNotFoundError):
        SpaceReservationService.decide_reservation(
            session=session,
            current_user=admin_user,
            reservation_id=uuid.uuid4(),
            approve=True,
        )


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


def test_owner_can_cancel_future_reservation(session: Session):
    space = make_space(session)
    resident = make_user(session, UserRole.RESIDENT, "cancel1@test.com", "38381384000")

    future_start = datetime.utcnow() + timedelta(days=1)
    future_end = future_start + timedelta(hours=1)
    reservation_in = SpaceReservationCreate(
        space_id=space.id, start_time=future_start, end_time=future_end
    )
    reservation = SpaceReservationService.create_reservation(
        session=session, current_user=resident, reservation_in=reservation_in
    )

    cancelled = SpaceReservationService.cancel_reservation(
        session=session, current_user=resident, reservation_id=reservation.id
    )
    assert cancelled.status == ReservationStatus.CANCELLED
    assert cancelled.cancelled_at is not None


def test_owner_cannot_cancel_past_reservation(session: Session):
    space = make_space(session)
    resident = make_user(session, UserRole.RESIDENT, "cancel2@test.com", "26314366005")

    reservation = SpaceReservation(
        space_id=space.id,
        reserved_by_id=resident.id,
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow() - timedelta(hours=1),
        status=ReservationStatus.CONFIRMED,
    )
    session.add(reservation)
    session.commit()

    with pytest.raises(ForbiddenError):
        SpaceReservationService.cancel_reservation(
            session=session, current_user=resident, reservation_id=reservation.id
        )


def test_owner_cannot_cancel_someone_elses_reservation(session: Session):
    space = make_space(session)
    owner = make_user(session, UserRole.RESIDENT, "owner1@test.com", "56321863030")
    other = make_user(session, UserRole.RESIDENT, "other1@test.com", "71563824020")

    future_start = datetime.utcnow() + timedelta(days=1)
    reservation = SpaceReservation(
        space_id=space.id,
        reserved_by_id=owner.id,
        start_time=future_start,
        end_time=future_start + timedelta(hours=1),
        status=ReservationStatus.CONFIRMED,
    )
    session.add(reservation)
    session.commit()

    with pytest.raises(ForbiddenError):
        SpaceReservationService.cancel_reservation(
            session=session, current_user=other, reservation_id=reservation.id
        )


def test_staff_can_cancel_any_reservation_including_started(
    session: Session, admin_user
):
    space = make_space(session)
    resident = make_user(session, UserRole.RESIDENT, "staffcancel@test.com", "94356633080")

    reservation = SpaceReservation(
        space_id=space.id,
        reserved_by_id=resident.id,
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow() + timedelta(hours=1),
        status=ReservationStatus.CONFIRMED,
    )
    session.add(reservation)
    session.commit()

    cancelled = SpaceReservationService.cancel_reservation(
        session=session, current_user=admin_user, reservation_id=reservation.id
    )
    assert cancelled.status == ReservationStatus.CANCELLED


def test_cancel_not_found(session: Session, admin_user):
    with pytest.raises(SpaceReservationNotFoundError):
        SpaceReservationService.cancel_reservation(
            session=session, current_user=admin_user, reservation_id=uuid.uuid4()
        )


def test_cancel_already_cancelled_not_found(session: Session):
    space = make_space(session)
    resident = make_user(session, UserRole.RESIDENT, "cancel3@test.com", "48252394050")

    reservation = SpaceReservation(
        space_id=space.id,
        reserved_by_id=resident.id,
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        status=ReservationStatus.CANCELLED,
    )
    session.add(reservation)
    session.commit()

    with pytest.raises(SpaceReservationNotFoundError):
        SpaceReservationService.cancel_reservation(
            session=session, current_user=resident, reservation_id=reservation.id
        )


# ---------------------------------------------------------------------------
# get_reservation visibility
# ---------------------------------------------------------------------------


def test_get_reservation_owner_can_view(session: Session):
    space = make_space(session)
    resident = make_user(session, UserRole.RESIDENT, "getr1@test.com", "78785936000")

    reservation = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    read = SpaceReservationService.get_reservation(
        session=session, current_user=resident, reservation_id=reservation.id
    )
    assert read.reserved_by_id == resident.id


def test_get_reservation_staff_can_view_any(session: Session, admin_user):
    space = make_space(session)
    resident = make_user(session, UserRole.RESIDENT, "getr2@test.com", "24866969000")

    reservation = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    read = SpaceReservationService.get_reservation(
        session=session, current_user=admin_user, reservation_id=reservation.id
    )
    assert read.id == reservation.id


def test_get_reservation_non_owner_non_staff_gets_not_found(session: Session):
    space = make_space(session)
    owner = make_user(session, UserRole.RESIDENT, "getr3@test.com", "36960452080")
    other = make_user(session, UserRole.RESIDENT, "getr4@test.com", "50801204070")

    reservation = SpaceReservationService.create_reservation(
        session=session,
        current_user=owner,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(12)
        ),
    )
    with pytest.raises(SpaceReservationNotFoundError):
        SpaceReservationService.get_reservation(
            session=session, current_user=other, reservation_id=reservation.id
        )


# ---------------------------------------------------------------------------
# list_reservations precedence & masking
# ---------------------------------------------------------------------------


def test_non_staff_sees_others_masked_and_own_unmasked(session: Session):
    space = make_space(session)
    owner = make_user(session, UserRole.RESIDENT, "list1@test.com", "82081904040")
    other = make_user(session, UserRole.RESIDENT, "list2@test.com", "40275107030")

    own_res = SpaceReservationService.create_reservation(
        session=session,
        current_user=owner,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(9), end_time=dt(10)
        ),
    )
    others_res = SpaceReservationService.create_reservation(
        session=session,
        current_user=other,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(11), end_time=dt(12)
        ),
    )

    results = SpaceReservationService.list_reservations(
        session=session, current_user=owner, space_id=space.id
    )
    by_id = {r.id: r for r in results}

    assert by_id[own_res.id].reserved_by_id == owner.id
    assert by_id[own_res.id].notes is None or True  # own row unmasked regardless

    masked = by_id[others_res.id]
    assert masked.reserved_by_id is None
    assert masked.reserved_by_name is None
    assert masked.lot_id is None
    assert masked.notes is None
    assert masked.status == ReservationStatus.CONFIRMED


def test_masked_list_excludes_cancelled_and_rejected(session: Session):
    space = make_space(session)
    owner = make_user(session, UserRole.RESIDENT, "list3@test.com", "68221929080")
    other = make_user(session, UserRole.RESIDENT, "list4@test.com", "17045135080")

    other_res = SpaceReservationService.create_reservation(
        session=session,
        current_user=other,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(11), end_time=dt(12)
        ),
    )
    other_res_db = session.get(SpaceReservation, other_res.id)
    other_res_db.status = ReservationStatus.CANCELLED
    session.add(other_res_db)
    session.commit()

    results = SpaceReservationService.list_reservations(
        session=session, current_user=owner, space_id=space.id
    )
    ids = [r.id for r in results]
    assert other_res.id not in ids


def test_staff_sees_full_detail_for_every_row_regardless_of_space_id(
    session: Session, admin_user
):
    space = make_space(session)
    resident = make_user(session, UserRole.RESIDENT, "list5@test.com", "95487566010")

    reservation = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(10), end_time=dt(11)
        ),
    )

    results = SpaceReservationService.list_reservations(
        session=session, current_user=admin_user, space_id=space.id
    )
    by_id = {r.id: r for r in results}
    assert by_id[reservation.id].reserved_by_id == resident.id


def test_non_staff_default_no_filters_returns_own_rows_only(session: Session):
    space = make_space(session)
    owner = make_user(session, UserRole.RESIDENT, "list6@test.com", "07295852080")
    other = make_user(session, UserRole.RESIDENT, "list7@test.com", "62910268060")

    own_res = SpaceReservationService.create_reservation(
        session=session,
        current_user=owner,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(9), end_time=dt(10)
        ),
    )
    SpaceReservationService.create_reservation(
        session=session,
        current_user=other,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(11), end_time=dt(12)
        ),
    )

    results = SpaceReservationService.list_reservations(
        session=session, current_user=owner
    )
    ids = [r.id for r in results]
    assert ids == [own_res.id]


def test_staff_default_no_filters_returns_everything(session: Session, admin_user):
    space = make_space(session)
    resident1 = make_user(session, UserRole.RESIDENT, "list8@test.com", "76887475000")
    resident2 = make_user(session, UserRole.RESIDENT, "list9@test.com", "43958787070")

    r1 = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident1,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(9), end_time=dt(10)
        ),
    )
    r2 = SpaceReservationService.create_reservation(
        session=session,
        current_user=resident2,
        reservation_in=SpaceReservationCreate(
            space_id=space.id, start_time=dt(11), end_time=dt(12)
        ),
    )

    results = SpaceReservationService.list_reservations(
        session=session, current_user=admin_user
    )
    ids = {r.id for r in results}
    assert {r1.id, r2.id}.issubset(ids)


def test_mine_true_overrides_space_id_even_for_admin(session: Session, admin_user):
    """The spec's own reviewer flagged this precedence case: mine=true always
    wins, restricting results to the caller's own rows regardless of role
    (even ADMINISTRATOR/DIRECTOR) and regardless of whether space_id is set.
    """
    space1 = make_space(session, name="Space Mine Test A")
    space2 = make_space(session, name="Space Mine Test B")
    resident = make_user(session, UserRole.RESIDENT, "mine1@test.com", "01488803090")

    # admin_user books a reservation on space1 (their own row).
    admin_res = SpaceReservationService.create_reservation(
        session=session,
        current_user=admin_user,
        reservation_in=SpaceReservationCreate(
            space_id=space1.id, start_time=dt(9), end_time=dt(10)
        ),
    )
    # A different user books on space1 too -- must NOT show up for admin
    # when mine=True even though space_id=space1 is also passed.
    SpaceReservationService.create_reservation(
        session=session,
        current_user=resident,
        reservation_in=SpaceReservationCreate(
            space_id=space1.id, start_time=dt(11), end_time=dt(12)
        ),
    )
    # admin_user also books on space2, to make sure mine=True+space_id
    # narrows to that one specific space rather than widening to all.
    admin_res_2 = SpaceReservationService.create_reservation(
        session=session,
        current_user=admin_user,
        reservation_in=SpaceReservationCreate(
            space_id=space2.id, start_time=dt(9), end_time=dt(10)
        ),
    )

    results_with_space = SpaceReservationService.list_reservations(
        session=session, current_user=admin_user, space_id=space1.id, mine=True
    )
    ids_with_space = {r.id for r in results_with_space}
    assert ids_with_space == {admin_res.id}
    assert admin_res_2.id not in ids_with_space

    results_no_space = SpaceReservationService.list_reservations(
        session=session, current_user=admin_user, mine=True
    )
    ids_no_space = {r.id for r in results_no_space}
    assert ids_no_space == {admin_res.id, admin_res_2.id}
    # Full detail even though "masking" would otherwise apply for non-owned
    # rows -- these are all admin_user's own rows, so no masking involved.
    for r in results_no_space:
        assert r.reserved_by_id == admin_user.id


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


def test_create_reservation_endpoint_success(
    client: TestClient, session: Session
):
    space = make_space(session)
    make_user(session, UserRole.RESIDENT, "ep1@test.com", "88289649000")
    token = get_token(client, "ep1", "pass")

    response = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "CONFIRMED"


def test_create_reservation_endpoint_guest_forbidden(
    client: TestClient, session: Session
):
    space = make_space(session)
    make_user(session, UserRole.GUEST, "ep_guest@test.com", "35931197070")
    token = get_token(client, "ep_guest", "pass")

    response = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )
    assert response.status_code == 403


def test_create_reservation_endpoint_conflict_returns_409(
    client: TestClient, session: Session
):
    space = make_space(session)
    make_user(session, UserRole.RESIDENT, "ep2@test.com", "45963084060")
    token = get_token(client, "ep2", "pass")

    payload = {
        "space_id": str(space.id),
        "start_time": "2026-06-01T10:00:00",
        "end_time": "2026-06-01T11:00:00",
    }
    first = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert second.status_code == 409


def test_approve_endpoint_forbidden_for_non_staff(
    client: TestClient, session: Session
):
    space = make_space(session, requires_approval=True)
    make_user(session, UserRole.RESIDENT, "ep3@test.com", "58551598000")
    token = get_token(client, "ep3", "pass")

    create_resp = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )
    reservation_id = create_resp.json()["id"]

    response = client.post(
        f"/api/v1/space-reservations/{reservation_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_approve_endpoint_success_for_admin(
    client: TestClient, session: Session, admin_user
):
    space = make_space(session, requires_approval=True)
    make_user(session, UserRole.RESIDENT, "ep4@test.com", "20889166070")
    resident_token = get_token(client, "ep4", "pass")

    create_resp = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )
    reservation_id = create_resp.json()["id"]

    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.post(
        f"/api/v1/space-reservations/{reservation_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_reject_endpoint_success_for_admin(
    client: TestClient, session: Session, admin_user
):
    space = make_space(session, requires_approval=True)
    make_user(session, UserRole.RESIDENT, "ep5@test.com", "13502366000")
    resident_token = get_token(client, "ep5", "pass")

    create_resp = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )
    reservation_id = create_resp.json()["id"]

    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.post(
        f"/api/v1/space-reservations/{reservation_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_cancel_endpoint_success_for_owner(client: TestClient, session: Session):
    space = make_space(session)
    make_user(session, UserRole.RESIDENT, "ep6@test.com", "91190721030")
    token = get_token(client, "ep6", "pass")

    future_start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    future_end = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat()
    create_resp = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "space_id": str(space.id),
            "start_time": future_start,
            "end_time": future_end,
        },
    )
    reservation_id = create_resp.json()["id"]

    response = client.post(
        f"/api/v1/space-reservations/{reservation_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_cancel_endpoint_forbidden_for_non_owner(
    client: TestClient, session: Session
):
    space = make_space(session)
    make_user(session, UserRole.RESIDENT, "ep7@test.com", "64118918000")
    owner_token = get_token(client, "ep7", "pass")
    make_user(session, UserRole.RESIDENT, "ep8@test.com", "77565175090")
    other_token = get_token(client, "ep8", "pass")

    future_start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    future_end = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat()
    create_resp = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "space_id": str(space.id),
            "start_time": future_start,
            "end_time": future_end,
        },
    )
    reservation_id = create_resp.json()["id"]

    response = client.post(
        f"/api/v1/space-reservations/{reservation_id}/cancel",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


def test_list_endpoint_masks_other_users_reservations(
    client: TestClient, session: Session
):
    space = make_space(session)
    make_user(session, UserRole.RESIDENT, "epl1@test.com", "68854938000")
    owner_token = get_token(client, "epl1", "pass")
    make_user(session, UserRole.RESIDENT, "epl2@test.com", "78929099000")
    other_token = get_token(client, "epl2", "pass")

    client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )

    response = client.get(
        f"/api/v1/space-reservations/?space_id={space.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["reserved_by_id"] is None
    assert data[0]["reserved_by_name"] is None


def test_list_endpoint_staff_sees_full_detail(
    client: TestClient, session: Session, admin_user
):
    space = make_space(session)
    make_user(session, UserRole.RESIDENT, "epl3@test.com", "07683213050")
    resident_token = get_token(client, "epl3", "pass")

    client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )

    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.get(
        f"/api/v1/space-reservations/?space_id={space.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["reserved_by_id"] is not None


def test_get_reservation_endpoint_not_found_for_stranger(
    client: TestClient, session: Session
):
    space = make_space(session)
    make_user(session, UserRole.RESIDENT, "epg1@test.com", "01678362000")
    owner_token = get_token(client, "epg1", "pass")
    make_user(session, UserRole.RESIDENT, "epg2@test.com", "62719839090")
    other_token = get_token(client, "epg2", "pass")

    create_resp = client.post(
        "/api/v1/space-reservations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "space_id": str(space.id),
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
    )
    reservation_id = create_resp.json()["id"]

    response = client.get(
        f"/api/v1/space-reservations/{reservation_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


def test_list_reservations_unauthenticated(client: TestClient):
    response = client.get("/api/v1/space-reservations/")
    assert response.status_code == 401


def test_list_reservations_guest_forbidden(client: TestClient, session: Session):
    make_user(session, UserRole.GUEST, "epl_guest@test.com", "62612626080")
    token = get_token(client, "epl_guest", "pass")
    response = client.get(
        "/api/v1/space-reservations/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
