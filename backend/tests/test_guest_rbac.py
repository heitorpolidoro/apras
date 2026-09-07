"""RBAC tests for the GUEST role.

Guests are newly signed-up users awaiting promotion: they can authenticate
but cannot see or interact with any task.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import get_password_hash
from app.models.category import Category
from app.models.role import Role
from tests.conftest import bundle, make_user, profile_role


def test_the_guest_profile_still_names_a_real_role(session: Session):
    """The successor of "GUEST must exist as a valid `UserRole` value".

    There is no enum to have a value in. What the module needs instead is
    that the GUEST *profile* resolves to a real role row carrying the bundle
    the enum used to grant — which is what every other case here leans on.
    """
    role = profile_role(session, "GUEST")

    assert role.name == "Convidado (papel)"
    assert set(role.permissions) == bundle("GUEST")


@pytest.fixture(name="guest_data")
def guest_data_fixture(session: Session):
    # GUEST intentionally gets zero Roles (and thus zero menu access,
    # per APRAS-8) since these tests exercise GUEST being blocked. The
    # helper director, however, needs standing "tasks" access so it can set
    # up tasks for the guest-focused assertions below.
    director_type = Role(name="Director Guest RBAC Type",)
    session.add(director_type)
    session.commit()

    guest = make_user(
        session,
        id=uuid.uuid4(),
        email="guest_rbac@test.com",
        full_name="Guest Test",
        hashed_password=get_password_hash("pass"),
        profile="GUEST",
        cpf="32464177002",
    )
    director = make_user(
        session,
        id=uuid.uuid4(),
        email="director_guest_rbac@test.com",
        full_name="Director Test",
        hashed_password=get_password_hash("pass"),
        profile="DIRECTOR",
        cpf="14555816045",
        roles=[director_type],
    )
    category = Category(id=uuid.uuid4(), name="Guest Test Category", color="#FFFFFF")
    session.add(guest)
    session.add(director)
    session.add(category)
    session.commit()
    return {"guest": guest, "director": director, "category": category}


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def _director_creates_task(client, guest_data) -> str:
    dir_token = get_token(client, "director_guest_rbac", "pass")
    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={
            "title": "Director Task",
            "category_id": str(guest_data["category"].id),
        },
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def test_guest_cannot_create_task(client: TestClient, session: Session, guest_data):
    """GUEST gets 403 when trying to create a task."""
    token = get_token(client, "guest_rbac", "pass")
    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Guest Task", "category_id": str(guest_data["category"].id)},
    )
    assert resp.status_code == 403


def test_guest_task_list_is_refused(client: TestClient, session: Session, guest_data):
    """GUEST listing tasks is a **403**.

    The history, in one place, because this case has now had four answers.
    Before APRAS-8 the GUEST role check made the list unconditionally empty
    (200 with `[]`). APRAS-8's `allowed_menus` gate then ran *first* and made
    it a 403. IAM F5 (APRAS-49 §4.2) deleted that gate, so the answer went
    back to the permission layer's 200-with-`[]`.

    APRAS-51 deletes that empty-list early return: `GET /api/v1/tasks/` is
    mapped to `tasks:read` and now enforces it with
    `Depends(require_permission("tasks:read"))`, so a non-holder is refused
    instead of served an empty page. It is the one intentional refusal-shape
    change of that task, and it is the parity cell
    `("GUEST", "GET", "/api/v1/tasks/")` moving 200 -> 403 in
    `tests/data/parity_matrix_baseline_51.json`.

    The sibling below keeps the other half of the claim: a *holder* still
    gets its list.
    """
    _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "The user doesn't have enough privileges"


def test_a_holder_of_tasks_read_still_lists_tasks(
    client: TestClient, session: Session, guest_data
):
    """The other half of APRAS-51: the guard narrows, it does not close."""
    task_id = _director_creates_task(client, guest_data)
    dir_token = get_token(client, "director_guest_rbac", "pass")
    resp = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {dir_token}"}
    )
    assert resp.status_code == 200
    assert task_id in {item["id"] for item in resp.json()}


def test_guest_cannot_edit_task(client: TestClient, session: Session, guest_data):
    """GUEST gets 404 editing a task: `assert_manager_can_see_task` refuses.

    Was a 403 while the `allowed_menus` gate ran before task visibility
    (§4.2). The baseline recorded 404 for this cell.
    """
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 404


def test_guest_cannot_see_task_history(
    client: TestClient, session: Session, guest_data
):
    """GUEST gets 404 on task history (was 403 through the menu gate, §4.2)."""
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.get(
        f"/api/v1/tasks/{task_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_guest_cannot_comment(client: TestClient, session: Session, guest_data):
    """GUEST gets **403** commenting.

    Was 403 through the menu gate (§4.2), then 404 through
    `assert_manager_can_see_task` once IAM F5 deleted that gate. APRAS-51 maps
    what was always mapped: `POST /tasks/{id}/comments` enforces
    `tasks:comment` in the dependency tree, which FastAPI solves before the
    handler runs, so the 404 never happens. Parity cell
    `("GUEST", "POST", "/api/v1/tasks/{task_id}/comments")`: 404 -> 403.
    """
    task_id = _director_creates_task(client, guest_data)
    token = get_token(client, "guest_rbac", "pass")
    resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "guest comment"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "The user doesn't have enough privileges"


def test_a_holder_of_tasks_comment_still_comments(
    client: TestClient, session: Session, guest_data
):
    """The holder half of the comment guard."""
    task_id = _director_creates_task(client, guest_data)
    dir_token = get_token(client, "director_guest_rbac", "pass")
    resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={"content": "director comment"},
    )
    assert resp.status_code == 201


def test_guest_cannot_create_category(
    client: TestClient, session: Session, guest_data
):
    """GUEST gets 403 when trying to create a category."""
    token = get_token(client, "guest_rbac", "pass")
    resp = client.post(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Guest Category", "color": "#ff0000"},
    )
    assert resp.status_code == 403


def test_assert_can_edit_task_guest_raises(session: Session, guest_data):
    """assert_can_edit_task always raises ForbiddenError for GUEST."""
    from app.api.deps import assert_can_edit_task
    from app.core.exceptions import ForbiddenError
    from app.models.task import Task

    task = Task(
        title="T",
        category_id=guest_data["category"].id,
        created_by_id=guest_data["director"].id,
        assigned_to_id=None,
    )
    session.add(task)
    session.commit()
    with pytest.raises(ForbiddenError):
        assert_can_edit_task(guest_data["guest"], task)
