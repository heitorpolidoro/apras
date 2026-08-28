import uuid

import pytest
from app.core.security import get_password_hash
from app.models.category import Category
from app.models.enums import UserRole
from app.models.user import User
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_manager_role_value_exists():
    """MANAGER must exist as a valid UserRole value."""
    from app.models.enums import UserRole

    assert UserRole.MANAGER == "MANAGER"


@pytest.fixture(name="test_data")
def test_data_fixture(session: Session):
    from app.models.user_type import UserType

    # DIRECTOR is now subject to the tasks/categories menu gate
    # (assert_menu_access, APRAS-8); grant standing access so this fixture's
    # director keeps the "full CRUD on all tasks" behavior these RBAC tests
    # exercise, unrelated to the menu gate itself.
    director_type = UserType(
        name="Director RBAC Type", allowed_menus=["tasks", "categories"]
    )
    session.add(director_type)
    session.commit()

    admin = User(
        id=uuid.uuid4(),
        email="admin_rbac@test.com",
        full_name="Admin Test",
        hashed_password=get_password_hash("pass"),
        role=UserRole.ADMINISTRATOR,
        cpf="52998224725",
    )
    director = User(
        id=uuid.uuid4(),
        email="director_rbac@test.com",
        full_name="Director Test",
        hashed_password=get_password_hash("pass"),
        role=UserRole.DIRECTOR,
        cpf="11144477735",
        user_types=[director_type],
    )
    category = Category(id=uuid.uuid4(), name="Test Category", color="#FFFFFF")
    session.add(admin)
    session.add(director)
    session.add(category)
    session.commit()
    return {"admin": admin, "director": director, "category": category}


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def test_rbac_task_workflow(client: TestClient, session: Session, test_data):
    admin_token = get_token(client, "admin_rbac", "pass")
    dir_token = get_token(client, "director_rbac", "pass")
    category_id = str(test_data["category"].id)

    # 1. Diretor PODE criar tarefas (novo privilégio na hierarquia Admin/Diretor)
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={"title": "Director Task", "category_id": category_id},
    )
    assert response.status_code == 200

    # 2. Diretor cria outra tarefa (apenas diretores criam tarefas)
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={
            "title": "Second Task",
            "assigned_to_id": str(test_data["director"].id),
            "category_id": category_id,
        },
    )
    assert response.status_code == 200
    admin_task_id = response.json()["id"]

    # 3. Diretor muda o STATUS da sua tarefa (Permitido)
    response = client.patch(
        f"/api/v1/tasks/{admin_task_id}",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"

    # 4. Apenas Administrador pode EXCLUIR tarefas
    response = client.delete(
        f"/api/v1/tasks/{admin_task_id}",
        headers={"Authorization": f"Bearer {dir_token}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/api/v1/tasks/{admin_task_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_assert_can_edit_task_allows_admin(session: Session, test_data):
    """ADMINISTRATOR can always edit any task, even one assigned to someone else."""
    from app.api.deps import assert_can_edit_task
    from app.models.task import Task

    admin = test_data["admin"]
    task = Task(
        title="T",
        category_id=test_data["category"].id,
        created_by_id=admin.id,
        assigned_to_id=test_data["director"].id,
    )
    session.add(task)
    session.commit()
    # Should not raise
    assert_can_edit_task(admin, task)


def test_assert_can_edit_task_manager_unassigned(session: Session, test_data):
    """MANAGER can edit tasks with no assignee."""
    import uuid as _uuid

    from app.api.deps import assert_can_edit_task
    from app.core.security import get_password_hash
    from app.models.enums import UserRole
    from app.models.task import Task
    from app.models.user import User

    manager = User(
        id=_uuid.uuid4(),
        email="mgr_tmp@test.com",
        full_name="Manager Tmp",
        hashed_password=get_password_hash("pass"),
        role=UserRole.MANAGER,
        cpf="08050681057",
    )
    session.add(manager)
    session.commit()
    task = Task(
        title="T",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        assigned_to_id=None,
    )
    session.add(task)
    session.commit()
    assert_can_edit_task(manager, task)  # should not raise


def test_assert_can_edit_task_manager_other_user_raises(session: Session, test_data):
    """MANAGER cannot edit tasks assigned to someone else."""
    import uuid as _uuid

    import pytest
    from app.api.deps import assert_can_edit_task
    from app.core.exceptions import ForbiddenError
    from app.core.security import get_password_hash
    from app.models.enums import UserRole
    from app.models.task import Task
    from app.models.user import User

    manager = User(
        id=_uuid.uuid4(),
        email="mgr_tmp2@test.com",
        full_name="Manager Tmp2",
        hashed_password=get_password_hash("pass"),
        role=UserRole.MANAGER,
        cpf="07491723040",
    )
    session.add(manager)
    session.commit()
    task = Task(
        title="T",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        assigned_to_id=test_data["director"].id,  # assigned to director, not manager
    )
    session.add(task)
    session.commit()
    with pytest.raises(ForbiddenError):
        assert_can_edit_task(manager, task)


@pytest.fixture(name="manager_type")
def manager_type_fixture(session: Session):
    """Create and persist a user type for manager.

    Also grants "tasks" menu access: manager_type is the only UserType
    assigned to `manager_user` in these tests, so it must carry standing
    tasks access for the pre-existing visibility/RBAC assertions below to
    keep exercising what they were designed to test, independent of the
    new menu gate (APRAS-8).
    """
    from app.models.user_type import UserType
    ut = UserType(name="Test Manager Type", allowed_menus=["tasks"])
    session.add(ut)
    session.commit()
    return ut


@pytest.fixture(name="other_type")
def other_type_fixture(session: Session):
    """A second UserType, distinct from `manager_type` and held by nobody
    in these tests — used to build tasks targeted away from the Manager
    (replacing the old single-FK tests' use of an arbitrary random uuid,
    which can no longer represent "a real target the Manager lacks" once
    `visible_to` only ever contains ids resolved to real UserType rows)."""
    from app.models.user_type import UserType

    ut = UserType(name="Other RBAC Type", allowed_menus=[])
    session.add(ut)
    session.commit()
    return ut


@pytest.fixture(name="manager_user")
def manager_user_fixture(session: Session, manager_type):
    """Create and persist a MANAGER user for RBAC tests."""
    import uuid as _uuid

    from app.core.security import get_password_hash

    manager = User(
        id=_uuid.uuid4(),
        email="manager_rbac@test.com",
        full_name="Manager Test",
        hashed_password=get_password_hash("pass"),
        role=UserRole.MANAGER,
        user_types=[manager_type],
        cpf="70323955008",
    )
    session.add(manager)
    session.commit()
    return manager


def test_manager_can_create_task(
    client: TestClient, session: Session, test_data, manager_user
):
    """MANAGER can create tasks."""
    token = get_token(client, "manager_rbac", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Manager Task", "category_id": str(test_data["category"].id)},
    )
    assert response.status_code == 200


def test_admin_can_create_task(client: TestClient, session: Session, test_data):
    """ADMINISTRATOR can create tasks."""
    token = get_token(client, "admin_rbac", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Admin Task", "category_id": str(test_data["category"].id)},
    )
    assert response.status_code == 200


def test_manager_cannot_edit_other_assigned_task(
    client: TestClient, session: Session, test_data, manager_user, manager_type
):
    """MANAGER gets 403 when editing a task visible to them (visible_to_ids=[manager_type.id]) but assigned to someone else."""
    dir_token = get_token(client, "director_rbac", "pass")
    mgr_token = get_token(client, "manager_rbac", "pass")
    category_id = str(test_data["category"].id)

    # Task is visible to manager_type, but assigned to Director
    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={
            "title": "Director Task",
            "category_id": category_id,
            "assigned_to_id": str(test_data["director"].id),
            "visible_to_ids": [str(manager_type.id)],
        },
    )
    assert resp.status_code == 200
    task_id = resp.json()["id"]

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 403


def test_manager_gets_404_for_invisible_task(
    client: TestClient, session: Session, test_data, manager_user, other_type
):
    """MANAGER gets 404 when accessing/editing a task not visible to them."""
    dir_token = get_token(client, "director_rbac", "pass")
    mgr_token = get_token(client, "manager_rbac", "pass")
    category_id = str(test_data["category"].id)

    # Task is targeted at a UserType the Manager doesn't belong to.
    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={
            "title": "Director Task",
            "category_id": category_id,
            "assigned_to_id": str(test_data["director"].id),
            "visible_to_ids": [str(other_type.id)],
        },
    )
    assert resp.status_code == 200
    task_id = resp.json()["id"]

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 404


def test_manager_can_edit_self_assigned_task(
    client: TestClient, session: Session, test_data, manager_user, manager_type
):
    """MANAGER can edit a task assigned to themselves (when visible_to=[manager_type])."""
    from app.models.task import Task

    mgr_token = get_token(client, "manager_rbac", "pass")
    task = Task(
        title="Manager Own Task",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        assigned_to_id=manager_user.id,
        visible_to=[manager_type],
    )
    session.add(task)
    session.commit()
    task_id = str(task.id)

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"


def test_manager_can_edit_unassigned_task(
    client: TestClient, session: Session, test_data, manager_user, manager_type
):
    """MANAGER can edit a task with no assignee (when visible_to=[manager_type])."""
    from app.models.task import Task

    mgr_token = get_token(client, "manager_rbac", "pass")
    task = Task(
        title="Unassigned Task",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        assigned_to_id=None,
        visible_to=[manager_type],
    )
    session.add(task)
    session.commit()
    task_id = str(task.id)

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 200


def test_manager_cannot_delete_task(
    client: TestClient, session: Session, test_data, manager_user, manager_type
):
    """MANAGER gets 403 when trying to delete a task."""
    dir_token = get_token(client, "director_rbac", "pass")
    mgr_token = get_token(client, "manager_rbac", "pass")

    resp = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {dir_token}"},
        json={
            "title": "Task To Delete",
            "category_id": str(test_data["category"].id),
            "visible_to_ids": [str(manager_type.id)],
        },
    )
    task_id = resp.json()["id"]

    resp = client.delete(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 403


def test_task_model_has_no_visible_to_id_field():
    """Task model no longer has a `visible_to_id` column: it's replaced by
    the many-to-many `visible_to` relationship (APRAS-11), defaulting to an
    empty list."""
    from app.models.task import Task

    task = Task(title="t", created_by_id=__import__("uuid").uuid4())
    assert not hasattr(task, "visible_to_id")
    assert task.visible_to == []


def test_task_read_schema_includes_visible_to():
    """TaskRead schema must expose `visible_to` (list of UserTypeRead), not
    the old `visible_to_id`/`visible_to_name` single-value fields."""
    from app.schemas.task import TaskRead

    assert "visible_to" in TaskRead.model_fields
    assert "visible_to_id" not in TaskRead.model_fields
    assert "visible_to_name" not in TaskRead.model_fields


def test_task_update_schema_includes_visible_to_ids():
    """TaskUpdate schema must accept `visible_to_ids` (a list)."""
    from app.schemas.task import TaskUpdate

    target_id = uuid.uuid4()
    update = TaskUpdate(visible_to_ids=[target_id])
    assert update.visible_to_ids == [target_id]


def test_manager_create_task_defaults_visible_to_explicit_user_type(
    client: TestClient, test_data, manager_user, manager_type
):
    """Tasks created by MANAGER with no explicit targets default to the
    Manager's explicit UserType ids (APRAS-11)."""
    token = get_token(client, "manager_rbac", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Manager Visible Task",
            "category_id": str(test_data["category"].id),
        },
    )
    assert response.status_code == 200
    visible_to_ids = {vt["id"] for vt in response.json()["visible_to"]}
    assert visible_to_ids == {str(manager_type.id)}


def test_admin_create_task_defaults_to_empty_visible_to(
    client: TestClient, test_data
):
    """Tasks created by ADMIN must have an empty `visible_to` by default."""
    token = get_token(client, "admin_rbac", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Admin Hidden Task",
            "category_id": str(test_data["category"].id),
        },
    )
    assert response.status_code == 200
    assert response.json()["visible_to"] == []


def test_director_create_task_defaults_to_empty_visible_to(
    client: TestClient, test_data
):
    """Tasks created by DIRECTOR must have an empty `visible_to` by default."""
    token = get_token(client, "director_rbac", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Director Hidden Task",
            "category_id": str(test_data["category"].id),
        },
    )
    assert response.status_code == 200
    assert response.json()["visible_to"] == []


def test_manager_list_only_sees_targeted_tasks(
    client: TestClient,
    session: Session,
    test_data,
    manager_user,
    manager_type,
    other_type,
):
    """MANAGER only sees tasks targeted to their UserType."""
    from app.models.task import Task

    hidden = Task(
        title="Hidden from Manager",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        visible_to=[other_type],
    )
    visible = Task(
        title="Visible to Manager",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        visible_to=[manager_type],
    )
    session.add(hidden)
    session.add(visible)
    session.commit()

    token = get_token(client, "manager_rbac", "pass")
    response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Visible to Manager" in titles
    assert "Hidden from Manager" not in titles


def test_admin_list_sees_all_tasks(
    client: TestClient, session: Session, test_data, manager_user, other_type
):
    """ADMIN sees all tasks regardless of visible_to targeting."""
    from app.models.task import Task

    hidden = Task(
        title="Admin Sees Hidden",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        visible_to=[other_type],
    )
    session.add(hidden)
    session.commit()

    token = get_token(client, "admin_rbac", "pass")
    response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Admin Sees Hidden" in titles


def test_manager_gets_404_for_invisible_task_history(
    client: TestClient, session: Session, test_data, manager_user, other_type
):
    """MANAGER gets 404 when accessing history of an invisible task."""
    from app.models.task import Task

    hidden = Task(
        title="Hidden History Task",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        visible_to=[other_type],
    )
    session.add(hidden)
    session.commit()

    token = get_token(client, "manager_rbac", "pass")
    response = client.get(
        f"/api/v1/tasks/{hidden.id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_manager_gets_404_for_invisible_task_comments(
    client: TestClient, session: Session, test_data, manager_user, other_type
):
    """MANAGER gets 404 when listing comments of an invisible task."""
    from app.models.task import Task

    hidden = Task(
        title="Hidden Comments Task",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        visible_to=[other_type],
    )
    session.add(hidden)
    session.commit()

    token = get_token(client, "manager_rbac", "pass")
    response = client.get(
        f"/api/v1/tasks/{hidden.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_admin_can_set_visible_to_ids(
    client: TestClient, session: Session, test_data, manager_user, manager_type, other_type
):
    """ADMIN can set visible_to_ids on a task, making it visible to MANAGER."""
    from app.models.task import Task

    hidden = Task(
        title="Will Become Visible",
        category_id=test_data["category"].id,
        created_by_id=test_data["admin"].id,
        visible_to=[other_type],
    )
    session.add(hidden)
    session.commit()

    admin_token = get_token(client, "admin_rbac", "pass")
    response = client.patch(
        f"/api/v1/tasks/{hidden.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"visible_to_ids": [str(manager_type.id)]},
    )
    assert response.status_code == 200
    assert {vt["id"] for vt in response.json()["visible_to"]} == {str(manager_type.id)}

    # MANAGER can now see it in the list
    mgr_token = get_token(client, "manager_rbac", "pass")
    list_response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    titles = [t["title"] for t in list_response.json()]
    assert "Will Become Visible" in titles


def test_manager_cannot_change_visible_to_ids_outside_effective_set(
    client: TestClient, session: Session, test_data, manager_user, manager_type
):
    """MANAGER gets 403 when setting visible_to_ids to a type they don't
    possess (APRAS-11 generalizes the old single-value check to a list, and
    now rejects the request outright instead of silently ignoring it)."""
    from app.models.task import Task

    visible = Task(
        title="Manager Own Task",
        category_id=test_data["category"].id,
        created_by_id=manager_user.id,
        visible_to=[manager_type],
    )
    session.add(visible)
    session.commit()

    mgr_token = get_token(client, "manager_rbac", "pass")
    other_type_id = str(uuid.uuid4())
    response = client.patch(
        f"/api/v1/tasks/{visible.id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"visible_to_ids": [other_type_id]},
    )
    assert response.status_code == 403


def test_manager_can_change_visible_to_ids_within_effective_set(
    client: TestClient, session: Session, test_data, manager_user, manager_type
):
    """MANAGER can set visible_to_ids as long as every id is within their
    effective UserType ids."""
    from app.models.task import Task

    visible = Task(
        title="Manager Own Task 2",
        category_id=test_data["category"].id,
        created_by_id=manager_user.id,
        visible_to=[manager_type],
    )
    session.add(visible)
    session.commit()

    mgr_token = get_token(client, "manager_rbac", "pass")
    response = client.patch(
        f"/api/v1/tasks/{visible.id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"visible_to_ids": [str(manager_type.id)]},
    )
    assert response.status_code == 200
    assert {vt["id"] for vt in response.json()["visible_to"]} == {str(manager_type.id)}
