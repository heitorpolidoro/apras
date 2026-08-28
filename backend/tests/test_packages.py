"""Unit tests for the Package (encomendas) service layer."""

import uuid

import pytest
from app.core.exceptions import (
    LotNotFoundError,
    PackageAccessForbiddenError,
    PackageAlreadyPickedUpError,
    PackageNotFoundError,
)
from app.models.enums import LotAssociationType, PackageStatus, UserRole
from app.models.resident import Resident
from app.models.user import User
from app.schemas.lot import LotCreate, UserLotLinkCreate
from app.schemas.package import PackageCreate, PackagePickup
from app.services.lot_service import LotService
from app.services.package_service import PackageService
from sqlmodel import Session


def _make_user(session: Session, role: UserRole, cpf: str, email: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=f"User {email}",
        hashed_password="hash",
        role=role,
        cpf=cpf,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def resident_user(session: Session) -> User:
    return _make_user(session, UserRole.RESIDENT, "22233344456", "resident_pkg@test.com")


@pytest.fixture
def guest_user(session: Session) -> User:
    return _make_user(session, UserRole.GUEST, "33344455567", "guest_pkg@test.com")


@pytest.fixture
def porteiro_user(session: Session) -> User:
    return _make_user(session, UserRole.PORTEIRO, "44455566678", "porteiro_pkg@test.com")


def test_create_package_success(session: Session, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="P", lot_number="1"))

    result = PackageService.create_package(
        session,
        normal_user,
        PackageCreate(lot_id=lot.id, description="Caixa Amazon", carrier="Correios"),
    )

    assert result.id is not None
    assert result.lot_id == lot.id
    assert result.lot_summary is not None
    assert result.lot_summary.id == lot.id
    assert result.lot_summary.block == "P"
    assert result.lot_summary.lot_number == "1"
    assert result.received_by_id == normal_user.id
    assert result.received_by_name == normal_user.full_name
    assert result.description == "Caixa Amazon"
    assert result.carrier == "Correios"
    assert result.status == PackageStatus.AWAITING_PICKUP
    assert result.picked_up_at is None


def test_create_package_lot_not_found(session: Session, normal_user: User):
    with pytest.raises(LotNotFoundError):
        PackageService.create_package(
            session, normal_user, PackageCreate(lot_id=uuid.uuid4())
        )


def test_create_package_forbidden_for_resident(session: Session, resident_user: User):
    lot = LotService.create_lot(session, LotCreate(block="P", lot_number="2"))
    with pytest.raises(PackageAccessForbiddenError):
        PackageService.create_package(
            session, resident_user, PackageCreate(lot_id=lot.id)
        )


def test_create_package_forbidden_for_guest(session: Session, guest_user: User):
    lot = LotService.create_lot(session, LotCreate(block="P", lot_number="3"))
    with pytest.raises(PackageAccessForbiddenError):
        PackageService.create_package(session, guest_user, PackageCreate(lot_id=lot.id))


def test_get_packages_for_lot_gatekeeper_any_lot(session: Session, admin_user: User, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="Q", lot_number="1"))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))

    items, total = PackageService.get_packages_for_lot(session, admin_user, lot.id)
    assert total == 1
    assert items[0].lot_id == lot.id


def test_get_packages_for_lot_resident_linked_via_user_lot_link(
    session: Session, normal_user: User, resident_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="Q", lot_number="2"))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    items, total = PackageService.get_packages_for_lot(session, resident_user, lot.id)
    assert total == 1


def test_get_packages_for_lot_resident_linked_via_active_resident_row(
    session: Session, normal_user: User, resident_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="Q", lot_number="3"))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    resident_row = Resident(
        lot_id=lot.id,
        user_id=resident_user.id,
        full_name="Household Member",
        cpf="98765432100",
        is_active=True,
    )
    session.add(resident_row)
    session.commit()

    items, total = PackageService.get_packages_for_lot(session, resident_user, lot.id)
    assert total == 1


def test_get_packages_for_lot_resident_different_lot_forbidden(
    session: Session, normal_user: User, resident_user: User
):
    lot_own = LotService.create_lot(session, LotCreate(block="Q", lot_number="4"))
    lot_other = LotService.create_lot(session, LotCreate(block="Q", lot_number="5"))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot_other.id))
    LotService.link_user(
        session,
        lot_own.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_packages_for_lot(session, resident_user, lot_other.id)


def test_get_packages_for_lot_guest_forbidden_even_when_linked_via_user_lot_link(
    session: Session, normal_user: User, guest_user: User
):
    """The specific bypass scenario flagged by RBAC review: GUEST + real lot linkage."""
    lot = LotService.create_lot(session, LotCreate(block="Q", lot_number="6"))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_packages_for_lot(session, guest_user, lot.id)


def test_get_packages_for_lot_guest_forbidden_even_when_linked_via_resident_row(
    session: Session, normal_user: User, guest_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="Q", lot_number="7"))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    resident_row = Resident(
        lot_id=lot.id,
        user_id=guest_user.id,
        full_name="Guest Household Member",
        cpf="11122233396",
        is_active=True,
    )
    session.add(resident_row)
    session.commit()

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_packages_for_lot(session, guest_user, lot.id)


def test_get_packages_for_lot_filters_by_status(session: Session, admin_user: User, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="Q", lot_number="8"))
    pkg1 = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    PackageService.mark_picked_up(session, admin_user, pkg1.id, PackagePickup())

    items, total = PackageService.get_packages_for_lot(
        session, admin_user, lot.id, status=PackageStatus.PICKED_UP
    )
    assert total == 1
    assert items[0].id == pkg1.id

    items_awaiting, total_awaiting = PackageService.get_packages_for_lot(
        session, admin_user, lot.id, status=PackageStatus.AWAITING_PICKUP
    )
    assert total_awaiting == 1
    assert items_awaiting[0].id != pkg1.id


def test_get_awaiting_pickup_queue_gatekeeper_cross_lot(
    session: Session, admin_user: User, normal_user: User, porteiro_user: User
):
    lot1 = LotService.create_lot(session, LotCreate(block="R", lot_number="1"))
    lot2 = LotService.create_lot(session, LotCreate(block="R", lot_number="2"))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot1.id))
    PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot2.id))

    items, total = PackageService.get_awaiting_pickup_queue(session, porteiro_user)
    assert total == 2
    lot_ids = {i.lot_id for i in items}
    assert lot_ids == {lot1.id, lot2.id}


def test_get_awaiting_pickup_queue_forbidden_for_resident(session: Session, resident_user: User):
    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_awaiting_pickup_queue(session, resident_user)


def test_get_awaiting_pickup_queue_forbidden_for_guest(session: Session, guest_user: User):
    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_awaiting_pickup_queue(session, guest_user)


def test_get_package_by_id_gatekeeper_any(session: Session, admin_user: User, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="S", lot_number="1"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))

    fetched = PackageService.get_package_by_id(session, admin_user, created.id)
    assert fetched.id == created.id


def test_get_package_by_id_linked_resident(
    session: Session, normal_user: User, resident_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="S", lot_number="2"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    fetched = PackageService.get_package_by_id(session, resident_user, created.id)
    assert fetched.id == created.id


def test_get_package_by_id_different_lot_forbidden(
    session: Session, normal_user: User, resident_user: User
):
    lot_own = LotService.create_lot(session, LotCreate(block="S", lot_number="3"))
    lot_other = LotService.create_lot(session, LotCreate(block="S", lot_number="4"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot_other.id))
    LotService.link_user(
        session,
        lot_own.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_package_by_id(session, resident_user, created.id)


def test_get_package_by_id_guest_forbidden_even_when_linked(
    session: Session, normal_user: User, guest_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="S", lot_number="5"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_package_by_id(session, guest_user, created.id)


def test_get_package_by_id_not_found(session: Session, admin_user: User):
    with pytest.raises(PackageNotFoundError):
        PackageService.get_package_by_id(session, admin_user, uuid.uuid4())


def test_get_my_lots_resident(session: Session, resident_user: User):
    lot = LotService.create_lot(session, LotCreate(block="T", lot_number="1"))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    lots = PackageService.get_my_lots(session, resident_user)
    assert len(lots) == 1
    assert lots[0].id == lot.id
    assert lots[0].block == "T"


def test_get_my_lots_empty_for_unlinked_resident(session: Session, resident_user: User):
    lots = PackageService.get_my_lots(session, resident_user)
    assert lots == []


def test_get_my_lots_forbidden_for_gatekeeper_roles(
    session: Session, admin_user: User, normal_user: User, porteiro_user: User
):
    for user in (admin_user, normal_user, porteiro_user):
        with pytest.raises(PackageAccessForbiddenError):
            PackageService.get_my_lots(session, user)


def test_get_my_lots_forbidden_for_guest_even_when_linked(session: Session, guest_user: User):
    lot = LotService.create_lot(session, LotCreate(block="T", lot_number="2"))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.get_my_lots(session, guest_user)


def test_mark_picked_up_gatekeeper_any_lot(session: Session, admin_user: User, normal_user: User):
    lot = LotService.create_lot(session, LotCreate(block="U", lot_number="1"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))

    updated = PackageService.mark_picked_up(
        session, admin_user, created.id, PackagePickup(picked_up_by_notes="Retirado pelo síndico")
    )
    assert updated.status == PackageStatus.PICKED_UP
    assert updated.picked_up_at is not None
    assert updated.picked_up_by_id == admin_user.id
    assert updated.picked_up_by_notes == "Retirado pelo síndico"


def test_mark_picked_up_linked_resident_sets_own_id(
    session: Session, normal_user: User, resident_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="U", lot_number="2"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    updated = PackageService.mark_picked_up(
        session, resident_user, created.id, PackagePickup()
    )
    assert updated.status == PackageStatus.PICKED_UP
    assert updated.picked_up_by_id == resident_user.id
    assert updated.picked_up_by_notes is None


def test_mark_picked_up_different_lot_forbidden(
    session: Session, normal_user: User, resident_user: User
):
    lot_own = LotService.create_lot(session, LotCreate(block="U", lot_number="3"))
    lot_other = LotService.create_lot(session, LotCreate(block="U", lot_number="4"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot_other.id))
    LotService.link_user(
        session,
        lot_own.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.mark_picked_up(session, resident_user, created.id, PackagePickup())


def test_mark_picked_up_guest_forbidden_even_when_linked(
    session: Session, normal_user: User, guest_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="U", lot_number="5"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    with pytest.raises(PackageAccessForbiddenError):
        PackageService.mark_picked_up(session, guest_user, created.id, PackagePickup())


def test_mark_picked_up_already_picked_up_conflict(
    session: Session, admin_user: User, normal_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="U", lot_number="6"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    PackageService.mark_picked_up(session, admin_user, created.id, PackagePickup())

    with pytest.raises(PackageAlreadyPickedUpError):
        PackageService.mark_picked_up(session, admin_user, created.id, PackagePickup())


def test_mark_picked_up_not_found(session: Session, admin_user: User):
    with pytest.raises(PackageNotFoundError):
        PackageService.mark_picked_up(session, admin_user, uuid.uuid4(), PackagePickup())


def test_package_read_names_null_when_referencing_user_deleted(
    session: Session, admin_user: User, normal_user: User
):
    """received_by_name/picked_up_by_name resolve to None if the FK'd user is gone."""
    lot = LotService.create_lot(session, LotCreate(block="V", lot_number="1"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    picked = PackageService.mark_picked_up(session, admin_user, created.id, PackagePickup())
    assert picked.received_by_name == normal_user.full_name
    assert picked.picked_up_by_name == admin_user.full_name

    # Simulate the referencing users having been removed (as if ondelete=SET NULL
    # had fired), leaving orphan ids that no longer resolve to a User row.
    from app.models.package import Package

    pkg_row = session.get(Package, created.id)
    session.delete(session.get(User, normal_user.id))
    session.delete(session.get(User, admin_user.id))
    session.commit()
    session.refresh(pkg_row)

    read_again = PackageService._build_package_read(session, pkg_row)
    assert read_again.received_by_name is None
    assert read_again.picked_up_by_name is None
