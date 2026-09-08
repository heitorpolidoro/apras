import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def test_get_task_not_found(client: TestClient, session: Session, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    random_id = uuid.uuid4()
    response = client.patch(
        f"/api/v1/tasks/{random_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "New Title"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    assert str(random_id) in response.json()["detail"]


def test_create_task_validation_error(
    client: TestClient, session: Session, admin_user, normal_user
):
    # Only directors can create tasks; empty title triggers 422
    token = get_token(client, "user1", "test_user_password")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": ""},
    )
    assert response.status_code == 422


def test_update_task_validation_error(
    client: TestClient, session: Session, admin_user, normal_user, default_category
):
    director_token = get_token(client, "user1", "test_user_password")
    admin_token = get_token(client, "admin", "test_admin_password")

    # Create a task as director
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {director_token}"},
        json={"title": "Valid Task", "category_id": str(default_category.id)},
    )
    assert response.status_code == 200
    task_id = response.json()["id"]

    # Update with invalid status (admin can update any task)
    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "INVALID_STATUS"},
    )
    assert response.status_code == 422
