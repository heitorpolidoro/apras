import uuid

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.category_service import CategoryService
from fastapi.testclient import TestClient
from sqlmodel import Session


def get_token(client, username, password):
    response = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Service-layer tests (direct calls, no HTTP)
# ---------------------------------------------------------------------------


def test_service_create_category(session: Session):
    category_in = CategoryCreate(name="Work", color="#ff0000")
    category = CategoryService.create_category(session=session, category_in=category_in)

    assert category.id is not None
    assert category.name == "Work"
    assert category.color == "#ff0000"
    assert category.is_active is True


def test_service_get_categories_only_active(session: Session):
    active = Category(name="Active", color="#00ff00", is_active=True)
    inactive = Category(name="Inactive", color="#0000ff", is_active=False)
    session.add(active)
    session.add(inactive)
    session.commit()

    result = CategoryService.get_categories(session=session, only_active=True)
    names = [c.name for c in result]

    assert "Active" in names
    assert "Inactive" not in names


def test_service_get_categories_all(session: Session):
    active = Category(name="Active", color="#00ff00", is_active=True)
    inactive = Category(name="Inactive", color="#0000ff", is_active=False)
    session.add(active)
    session.add(inactive)
    session.commit()

    result = CategoryService.get_categories(session=session, only_active=False)
    names = [c.name for c in result]

    assert "Active" in names
    assert "Inactive" in names


def test_service_update_category_name_only(session: Session, default_category: Category):
    update_in = CategoryUpdate(name="Renamed")
    updated = CategoryService.update_category(
        session=session, db_category=default_category, category_in=update_in
    )

    assert updated.name == "Renamed"
    assert updated.color == default_category.color


def test_service_update_category_color_only(session: Session, default_category: Category):
    update_in = CategoryUpdate(color="#123456")
    updated = CategoryService.update_category(
        session=session, db_category=default_category, category_in=update_in
    )

    assert updated.color == "#123456"
    assert updated.name == "General"


def test_service_update_category_is_active_only(session: Session, default_category: Category):
    update_in = CategoryUpdate(is_active=False)
    updated = CategoryService.update_category(
        session=session, db_category=default_category, category_in=update_in
    )

    assert updated.is_active is False
    assert updated.name == "General"


def test_service_update_category_multiple_fields(session: Session, default_category: Category):
    update_in = CategoryUpdate(name="Updated", color="#abcdef", is_active=False)
    updated = CategoryService.update_category(
        session=session, db_category=default_category, category_in=update_in
    )

    assert updated.name == "Updated"
    assert updated.color == "#abcdef"
    assert updated.is_active is False


def test_service_delete_category_sets_inactive(session: Session, default_category: Category):
    assert default_category.is_active is True

    CategoryService.delete_category(session=session, db_category=default_category)

    session.refresh(default_category)
    assert default_category.is_active is False

    # Row still exists in DB
    persisted = session.get(Category, default_category.id)
    assert persisted is not None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


def test_list_categories_authenticated(client: TestClient, session: Session, normal_user, default_category: Category):
    token = get_token(client, "user1", "test_user_password")
    response = client.get("/api/v1/categories/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    ids = [item["id"] for item in data]
    assert str(default_category.id) in ids


def test_list_categories_unauthenticated(client: TestClient):
    response = client.get("/api/v1/categories/")
    assert response.status_code == 401


def test_create_category_admin_success(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    response = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Finance", "color": "#ff5500"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Finance"
    assert data["color"] == "#ff5500"
    assert data["is_active"] is True
    assert "id" in data


def test_create_category_non_admin_success(client: TestClient, session: Session, normal_user):
    token = get_token(client, "user1", "test_user_password")
    response = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Finance", "color": "#ff5500"},
    )

    assert response.status_code == 201


def test_create_category_unauthenticated(client: TestClient):
    response = client.post("/api/v1/categories/", json={"name": "Finance", "color": "#ff5500"})
    assert response.status_code == 401


def test_create_category_invalid_color_format(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    response = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Bad Color", "color": "not-a-hex"},
    )

    assert response.status_code == 422


def test_update_category_admin_success(client: TestClient, session: Session, admin_user, default_category: Category):
    token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/categories/{default_category.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed Category"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Category"


def test_update_category_non_admin_success(client: TestClient, session: Session, normal_user, default_category: Category):
    token = get_token(client, "user1", "test_user_password")
    response = client.patch(
        f"/api/v1/categories/{default_category.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed"},
    )

    assert response.status_code == 200


def test_update_category_not_found(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    random_id = uuid.uuid4()
    response = client.patch(
        f"/api/v1/categories/{random_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Ghost"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_category_admin_success(client: TestClient, session: Session, admin_user, default_category: Category):
    token = get_token(client, "admin", "test_admin_password")
    response = client.delete(
        f"/api/v1/categories/{default_category.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    session.refresh(default_category)
    assert default_category.is_active is False


def test_delete_category_non_admin_success(client: TestClient, session: Session, normal_user, default_category: Category):
    token = get_token(client, "user1", "test_user_password")
    response = client.delete(
        f"/api/v1/categories/{default_category.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


def test_delete_category_not_found(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    random_id = uuid.uuid4()
    response = client.delete(
        f"/api/v1/categories/{random_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_director_can_create_category(client: TestClient, session: Session, normal_user, admin_user):
    """DIRECTOR can create categories."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user1", "password": "test_user_password"},
    )
    token = resp.json()["access_token"]
    resp = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Dir Category", "color": "#ff0000"},
    )
    assert resp.status_code == 201


def test_manager_cannot_create_category(client: TestClient, session: Session, admin_user):
    """MANAGER gets 403 when trying to create a category."""
    import uuid as _uuid
    from app.core.security import get_password_hash
    from app.models.enums import UserRole
    from app.models.user import User
    manager = User(
        id=_uuid.uuid4(),
        email="mgr_cat_test@test.com",
        full_name="Manager Cat",
        hashed_password=get_password_hash("pass"),
        role=UserRole.MANAGER,
        cpf="08050681057",
    )
    session.add(manager)
    session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "mgr_cat_test", "password": "pass"},
    )
    token = resp.json()["access_token"]
    resp = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Manager Category", "color": "#ff0000"},
    )
    assert resp.status_code == 403


def test_manager_cannot_update_category(client: TestClient, session: Session, admin_user):
    """MANAGER gets 403 when trying to update a category."""
    import uuid as _uuid
    from app.core.security import get_password_hash
    from app.models.enums import UserRole
    from app.models.user import User
    manager = User(
        id=_uuid.uuid4(),
        email="mgr_cat_upd@test.com",
        full_name="Manager Cat Upd",
        hashed_password=get_password_hash("pass"),
        role=UserRole.MANAGER,
        cpf="07491723040",
    )
    session.add(manager)
    session.commit()

    # Admin creates a category first
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "test_admin_password"},
    )
    admin_token = resp.json()["access_token"]
    cat_resp = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Protected Cat", "color": "#ff0000"},
    )
    cat_id = cat_resp.json()["id"]

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "mgr_cat_upd", "password": "pass"},
    )
    token = resp.json()["access_token"]
    resp = client.patch(
        f"/api/v1/categories/{cat_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Hacked"},
    )
    assert resp.status_code == 403


def test_list_categories_excludes_deactivated(client: TestClient, session: Session, admin_user, default_category: Category):
    token = get_token(client, "admin", "test_admin_password")

    client.delete(
        f"/api/v1/categories/{default_category.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get("/api/v1/categories/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert str(default_category.id) not in ids
