import uuid

from app.core.security import get_password_hash
from app.models.enums import UserRole
from app.models.reservation import ReservableSpace
from app.models.user import User
from app.schemas.reservation import ReservableSpaceCreate, ReservableSpaceUpdate
from app.services.reservation_service import ReservableSpaceService
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


# ---------------------------------------------------------------------------
# Service-layer tests (direct calls, no HTTP)
# ---------------------------------------------------------------------------


def test_service_create_space(session: Session):
    space_in = ReservableSpaceCreate(name="Party Room", capacity=30)
    space = ReservableSpaceService.create_space(session=session, space_in=space_in)

    assert space.id is not None
    assert space.name == "Party Room"
    assert space.capacity == 30
    assert space.requires_approval is False
    assert space.is_active is True


def test_service_get_spaces_only_active(session: Session):
    active = ReservableSpace(name="Active Space", is_active=True)
    inactive = ReservableSpace(name="Inactive Space", is_active=False)
    session.add(active)
    session.add(inactive)
    session.commit()

    result = ReservableSpaceService.get_spaces(session=session, only_active=True)
    names = [s.name for s in result]

    assert "Active Space" in names
    assert "Inactive Space" not in names


def test_service_get_spaces_all(session: Session):
    active = ReservableSpace(name="Active Space", is_active=True)
    inactive = ReservableSpace(name="Inactive Space", is_active=False)
    session.add(active)
    session.add(inactive)
    session.commit()

    result = ReservableSpaceService.get_spaces(session=session, only_active=False)
    names = [s.name for s in result]

    assert "Active Space" in names
    assert "Inactive Space" in names


def test_service_update_space_name_only(session: Session):
    space = ReservableSpace(name="Gym")
    session.add(space)
    session.commit()

    update_in = ReservableSpaceUpdate(name="Fitness Center")
    updated = ReservableSpaceService.update_space(
        session=session, db_space=space, space_in=update_in
    )

    assert updated.name == "Fitness Center"


def test_service_update_space_multiple_fields(session: Session):
    space = ReservableSpace(name="Pool")
    session.add(space)
    session.commit()

    update_in = ReservableSpaceUpdate(
        description="Outdoor pool", capacity=20, requires_approval=True
    )
    updated = ReservableSpaceService.update_space(
        session=session, db_space=space, space_in=update_in
    )

    assert updated.description == "Outdoor pool"
    assert updated.capacity == 20
    assert updated.requires_approval is True


def test_service_deactivate_space_sets_inactive(session: Session):
    space = ReservableSpace(name="BBQ Area")
    session.add(space)
    session.commit()

    assert space.is_active is True

    ReservableSpaceService.deactivate_space(session=session, db_space=space)

    session.refresh(space)
    assert space.is_active is False

    # Row still exists in DB (soft delete)
    persisted = session.get(ReservableSpace, space.id)
    assert persisted is not None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


def test_list_spaces_authenticated(client: TestClient, session: Session, admin_user):
    space = ReservableSpace(name="Salão de Festas")
    session.add(space)
    session.commit()

    token = get_token(client, "admin", "test_admin_password")
    response = client.get(
        "/api/v1/reservable-spaces/", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert str(space.id) in ids


def test_list_spaces_guest_can_see(session: Session, client: TestClient):
    guest = make_user(session, UserRole.GUEST, "guest_spaces@test.com", "80661003005")
    token = get_token(client, "guest_spaces", "pass")
    response = client.get(
        "/api/v1/reservable-spaces/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    _ = guest


def test_list_spaces_unauthenticated(client: TestClient):
    response = client.get("/api/v1/reservable-spaces/")
    assert response.status_code == 401


def test_create_space_admin_success(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    response = client.post(
        "/api/v1/reservable-spaces/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Quadra Poliesportiva", "capacity": 10},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Quadra Poliesportiva"
    assert data["capacity"] == 10
    assert data["is_active"] is True
    assert data["requires_approval"] is False


def test_director_can_create_space(client: TestClient, session: Session, normal_user):
    token = get_token(client, "user1", "test_user_password")
    response = client.post(
        "/api/v1/reservable-spaces/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Sala de Jogos"},
    )
    assert response.status_code == 201


def test_resident_cannot_create_space(session: Session, client: TestClient):
    make_user(session, UserRole.RESIDENT, "resident_spaces@test.com", "98765432100")
    token = get_token(client, "resident_spaces", "pass")
    response = client.post(
        "/api/v1/reservable-spaces/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Should Fail"},
    )
    assert response.status_code == 403


def test_manager_cannot_create_space(session: Session, client: TestClient):
    make_user(session, UserRole.MANAGER, "mgr_spaces@test.com", "08050681057")
    token = get_token(client, "mgr_spaces", "pass")
    response = client.post(
        "/api/v1/reservable-spaces/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Should Fail Too"},
    )
    assert response.status_code == 403


def test_create_space_unauthenticated(client: TestClient):
    response = client.post("/api/v1/reservable-spaces/", json={"name": "Nope"})
    assert response.status_code == 401


def test_update_space_admin_success(client: TestClient, session: Session, admin_user):
    space = ReservableSpace(name="Churrasqueira")
    session.add(space)
    session.commit()

    token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/reservable-spaces/{space.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Churrasqueira Renovada"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Churrasqueira Renovada"


def test_update_space_non_admin_forbidden(
    session: Session, client: TestClient, admin_user
):
    space = ReservableSpace(name="Sauna")
    session.add(space)
    session.commit()

    make_user(session, UserRole.RESIDENT, "resident_upd@test.com", "11144477735")
    token = get_token(client, "resident_upd", "pass")
    response = client.patch(
        f"/api/v1/reservable-spaces/{space.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Hacked"},
    )
    assert response.status_code == 403


def test_update_space_not_found(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    random_id = uuid.uuid4()
    response = client.patch(
        f"/api/v1/reservable-spaces/{random_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Ghost"},
    )
    assert response.status_code == 404


def test_deactivate_space_admin_success(
    client: TestClient, session: Session, admin_user
):
    space = ReservableSpace(name="Espaço Gourmet")
    session.add(space)
    session.commit()

    token = get_token(client, "admin", "test_admin_password")
    response = client.delete(
        f"/api/v1/reservable-spaces/{space.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    session.refresh(space)
    assert space.is_active is False


def test_deactivate_space_non_admin_forbidden(
    session: Session, client: TestClient, admin_user
):
    space = ReservableSpace(name="Brinquedoteca")
    session.add(space)
    session.commit()

    make_user(session, UserRole.RESIDENT, "resident_del@test.com", "07491723040")
    token = get_token(client, "resident_del", "pass")
    response = client.delete(
        f"/api/v1/reservable-spaces/{space.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_deactivate_space_not_found(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    random_id = uuid.uuid4()
    response = client.delete(
        f"/api/v1/reservable-spaces/{random_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_list_spaces_excludes_deactivated(
    client: TestClient, session: Session, admin_user
):
    space = ReservableSpace(name="Vestiário")
    session.add(space)
    session.commit()

    token = get_token(client, "admin", "test_admin_password")
    client.delete(
        f"/api/v1/reservable-spaces/{space.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        "/api/v1/reservable-spaces/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert str(space.id) not in ids
