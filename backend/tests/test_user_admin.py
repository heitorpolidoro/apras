from app.models.enums import UserRole
from app.models.user import User
from fastapi.testclient import TestClient
from sqlmodel import Session, select


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def test_signup(client: TestClient, session: Session):
    signup_data = {
        "email": "newuser@test.com",
        "full_name": "New User",
        "password": "Password123!",
        "cpf": "22233344405",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["is_active"] is False
    assert data["role"] == UserRole.GUEST

    # Verify in DB
    user = session.exec(select(User).where(User.email == "newuser@test.com")).first()
    assert user is not None
    assert user.is_active is False


def test_signup_duplicate_email(client: TestClient, normal_user):
    signup_data = {
        "email": normal_user.email,
        "full_name": "Duplicate User",
        "password": "Password123!",
        "cpf": "99988877714",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"]


def test_me_endpoint(client: TestClient, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_list_users_accessible_to_all_authenticated(
    client: TestClient, admin_user, normal_user
):
    """Test that the user list endpoint is accessible to all authenticated users."""
    admin_token = get_token(client, "admin", "test_admin_password")
    user_token = get_token(client, "user1", "test_user_password")

    # Admin can list
    response = client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2

    # Director can also list (needed to populate assignee dropdowns)
    response = client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_update_user_status_and_role(client: TestClient, admin_user, session: Session):
    # Create an inactive user
    new_user = User(
        email="pending@test.com",
        full_name="Pending User",
        hashed_password="...",
        is_active=False,
        role=UserRole.DIRECTOR,
        cpf="12345678909",
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    admin_token = get_token(client, "admin", "test_admin_password")

    # Activate user
    response = client.patch(
        f"/api/v1/users/{new_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": True},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    # Change role to Administrator
    response = client.patch(
        f"/api/v1/users/{new_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": UserRole.ADMINISTRATOR},
    )
    assert response.status_code == 200
    assert response.json()["role"] == UserRole.ADMINISTRATOR


def test_admin_cannot_deactivate_self(client: TestClient, admin_user):
    admin_token = get_token(client, "admin", "test_admin_password")

    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert response.status_code == 400
    assert "Administrators cannot deactivate themselves" in response.json()["detail"]


def test_admin_cannot_change_own_role(client: TestClient, admin_user):
    admin_token = get_token(client, "admin", "test_admin_password")

    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": UserRole.DIRECTOR},
    )
    assert response.status_code == 400
    assert "Administrators cannot change their own role" in response.json()["detail"]
