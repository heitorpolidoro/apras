from app.core import security
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.user import User


def test_forgot_password_flow(client: TestClient, normal_user: User):
    # Test requesting password reset for registered email
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": normal_user.email},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "sent" in response.json()["message"]

    # Test requesting password reset for unregistered email (should return same success message)
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unregistered@test.com"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "sent" in response.json()["message"]


def test_reset_password_flow(client: TestClient, session: Session, normal_user: User):
    # Generate valid reset token
    token = security.create_password_reset_token(normal_user.email)

    # Reset password using the valid token
    new_password = "new_secret_password!"
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "sucesso" in response.json()["message"].lower()

    # Verify that the hashed password changed and we can login
    session.refresh(normal_user)
    assert security.verify_password(new_password, normal_user.hashed_password)

    # Test resetting with an invalid/expired token
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalid_or_expired_token", "new_password": "some_password"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "inválido" in response.json()["detail"].lower()
