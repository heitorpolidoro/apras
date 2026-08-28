"""API-level RBAC tests for Package (encomendas) endpoints, focused on the GUEST bypass
scenario flagged during spec review: a GUEST-role account linked to a lot via
UserLotLink/Resident must still be rejected on every package route.
"""

import uuid

import pytest
from app.core.security import create_access_token
from app.models.enums import LotAssociationType, UserRole
from app.models.resident import Resident
from app.models.user import User
from app.schemas.lot import LotCreate, UserLotLinkCreate
from app.services.lot_service import LotService
from app.services.package_service import PackageService
from app.schemas.package import PackageCreate
from fastapi.testclient import TestClient
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
def guest_user(session: Session) -> User:
    return _make_user(session, UserRole.GUEST, "55566677789", "guest_rbac_pkg@test.com")


@pytest.fixture
def resident_user(session: Session) -> User:
    return _make_user(session, UserRole.RESIDENT, "66677788890", "resident_rbac_pkg@test.com")


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_guest_forbidden_on_create(session: Session, client: TestClient, guest_user: User):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="1"))
    res = client.post(
        "/api/v1/packages", json={"lot_id": str(lot.id)}, headers=_headers(guest_user)
    )
    assert res.status_code == 403


def test_guest_forbidden_on_get_packages_for_lot_even_when_linked_via_user_lot_link(
    session: Session, client: TestClient, guest_user: User, admin_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="2"))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )
    res = client.get(f"/api/v1/packages?lot_id={lot.id}", headers=_headers(guest_user))
    assert res.status_code == 403


def test_guest_forbidden_on_get_packages_for_lot_even_when_linked_via_resident_row(
    session: Session, client: TestClient, guest_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="3"))
    resident_row = Resident(
        lot_id=lot.id,
        user_id=guest_user.id,
        full_name="Guest as household member",
        cpf="11122233396",
        is_active=True,
    )
    session.add(resident_row)
    session.commit()

    res = client.get(f"/api/v1/packages?lot_id={lot.id}", headers=_headers(guest_user))
    assert res.status_code == 403


def test_guest_forbidden_on_queue(session: Session, client: TestClient, guest_user: User):
    res = client.get("/api/v1/packages/queue", headers=_headers(guest_user))
    assert res.status_code == 403


def test_guest_forbidden_on_my_lots_even_when_linked(
    session: Session, client: TestClient, guest_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="4"))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )
    res = client.get("/api/v1/packages/my-lots", headers=_headers(guest_user))
    assert res.status_code == 403


def test_guest_forbidden_on_get_package_by_id_even_when_linked(
    session: Session, client: TestClient, guest_user: User, normal_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="5"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    res = client.get(f"/api/v1/packages/{created.id}", headers=_headers(guest_user))
    assert res.status_code == 403


def test_guest_forbidden_on_pickup_even_when_linked(
    session: Session, client: TestClient, guest_user: User, normal_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="6"))
    created = PackageService.create_package(session, normal_user, PackageCreate(lot_id=lot.id))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=guest_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    res = client.post(
        f"/api/v1/packages/{created.id}/pickup", json={}, headers=_headers(guest_user)
    )
    assert res.status_code == 403


def test_resident_full_flow_via_api(
    session: Session, client: TestClient, resident_user: User, normal_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="7"))
    LotService.link_user(
        session,
        lot.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )

    created_res = client.post(
        "/api/v1/packages",
        json={"lot_id": str(lot.id), "description": "Encomenda"},
        headers=_headers(normal_user),
    )
    assert created_res.status_code == 201
    package_id = created_res.json()["id"]

    list_res = client.get(f"/api/v1/packages?lot_id={lot.id}", headers=_headers(resident_user))
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    my_lots_res = client.get("/api/v1/packages/my-lots", headers=_headers(resident_user))
    assert my_lots_res.status_code == 200
    assert len(my_lots_res.json()) == 1
    assert my_lots_res.json()[0]["id"] == str(lot.id)

    pickup_res = client.post(
        f"/api/v1/packages/{package_id}/pickup",
        json={"picked_up_by_notes": "retirado por mim"},
        headers=_headers(resident_user),
    )
    assert pickup_res.status_code == 200
    assert pickup_res.json()["status"] == "PICKED_UP"
    assert pickup_res.json()["picked_up_by_id"] == str(resident_user.id)

    # Double pickup rejected
    conflict_res = client.post(
        f"/api/v1/packages/{package_id}/pickup", json={}, headers=_headers(resident_user)
    )
    assert conflict_res.status_code == 409


def test_resident_cannot_access_other_lot_via_api(
    session: Session, client: TestClient, resident_user: User, normal_user: User
):
    lot_own = LotService.create_lot(session, LotCreate(block="G", lot_number="8"))
    lot_other = LotService.create_lot(session, LotCreate(block="G", lot_number="9"))
    LotService.link_user(
        session,
        lot_own.id,
        UserLotLinkCreate(user_id=resident_user.id, association_type=LotAssociationType.PROPRIETARIO),
    )
    created_res = client.post(
        "/api/v1/packages",
        json={"lot_id": str(lot_other.id)},
        headers=_headers(normal_user),
    )
    package_id = created_res.json()["id"]

    res = client.get(f"/api/v1/packages?lot_id={lot_other.id}", headers=_headers(resident_user))
    assert res.status_code == 403

    res2 = client.get(f"/api/v1/packages/{package_id}", headers=_headers(resident_user))
    assert res2.status_code == 403

    res3 = client.post(
        f"/api/v1/packages/{package_id}/pickup", json={}, headers=_headers(resident_user)
    )
    assert res3.status_code == 403


def test_gatekeeper_roles_can_create_and_pickup(
    session: Session, client: TestClient, admin_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="10"))
    created_res = client.post(
        "/api/v1/packages", json={"lot_id": str(lot.id)}, headers=_headers(admin_user)
    )
    assert created_res.status_code == 201
    package_id = created_res.json()["id"]

    queue_res = client.get("/api/v1/packages/queue", headers=_headers(admin_user))
    assert queue_res.status_code == 200
    assert queue_res.json()["total"] == 1

    pickup_res = client.post(
        f"/api/v1/packages/{package_id}/pickup", json={}, headers=_headers(admin_user)
    )
    assert pickup_res.status_code == 200

    queue_after_res = client.get("/api/v1/packages/queue", headers=_headers(admin_user))
    assert queue_after_res.json()["total"] == 0


def test_resident_forbidden_on_create_and_queue(
    session: Session, client: TestClient, resident_user: User
):
    lot = LotService.create_lot(session, LotCreate(block="G", lot_number="11"))
    res = client.post(
        "/api/v1/packages", json={"lot_id": str(lot.id)}, headers=_headers(resident_user)
    )
    assert res.status_code == 403

    res2 = client.get("/api/v1/packages/queue", headers=_headers(resident_user))
    assert res2.status_code == 403


def test_nonexistent_lot_returns_404_on_create(
    session: Session, client: TestClient, admin_user: User
):
    res = client.post(
        "/api/v1/packages", json={"lot_id": str(uuid.uuid4())}, headers=_headers(admin_user)
    )
    assert res.status_code == 404


def test_nonexistent_package_returns_404(session: Session, client: TestClient, admin_user: User):
    res = client.get(f"/api/v1/packages/{uuid.uuid4()}", headers=_headers(admin_user))
    assert res.status_code == 404
