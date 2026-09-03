from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.main import get_origins


def test_get_origins_empty():
    with patch.object(settings, "BACKEND_CORS_ORIGINS", []):
        assert get_origins() == []


def test_list_tasks_filter_by_category(
    client: TestClient, session: Session, admin_user, normal_user, default_category
):
    """Test that tasks can be filtered by category_id."""
    director_token = client.post(
        "/api/v1/auth/login",
        data={"username": "user1", "password": "test_user_password"},
    ).json()["access_token"]
    admin_token = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "test_admin_password"},
    ).json()["access_token"]

    # Create a task as director
    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {director_token}"},
        json={
            "title": "Category Task",
            "category_id": str(default_category.id),
            "priority": "MEDIUM",
        },
    )
    assert resp.status_code == 200

    # Filter by category as admin
    response = client.get(
        f"/api/v1/tasks/?category_id={default_category.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(t["category_id"] == str(default_category.id) for t in data)
