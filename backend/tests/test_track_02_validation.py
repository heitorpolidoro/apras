from fastapi.testclient import TestClient
from sqlmodel import Session


def test_inactive_user_login_fails(client: TestClient, session: Session):
    # Create an inactive user
    signup_data = {
        "email": "inactive_test@test.com",
        "full_name": "Inactive Test",
        "password": "Password123!",
        "cpf": "52998224725",
    }
    client.post("/api/v1/auth/signup", json=signup_data)

    # Try to login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "inactive_test", "password": "Password123!"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


def test_signup_creates_inactive_guest(client: TestClient, session: Session):
    signup_data = {
        "email": "guy@test.com",
        "full_name": "New Guy",
        "password": "Password123!",
        "cpf": "11144477735",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False
    # IAM F5 (APRAS-49 §8.3): signup creates the user with **zero roles**
    # and `is_active = False` -- the same practical result the forced
    # `GUEST` enum expressed, now said once instead of twice.
    assert "role" not in data
    assert data["roles"] == []
