"""Tests for multiple Role visibility targets per task (APRAS-11).

`Task.visible_to_id` (single nullable FK) became `Task.visible_to` (a
many-to-many relationship via `TaskVisibleToLink`), so a task can be
targeted at zero or more Roles. These tests cover the scenarios called
out explicitly in the spec's Testing section that aren't already covered by
the translated single-target tests in `test_tasks_rbac.py`: partial overlap
across multiple targets, no overlap at all, the auto-default fallback to
the role-type id when a Manager has zero explicit Roles, and the
`list_tasks` SQL filter under multiple targets.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import assert_manager_can_see_task
from app.core.exceptions import TaskNotFoundError
from app.core.security import get_password_hash
from app.models.category import Category
from app.models.role import Role
from app.models.task import Task
from tests.conftest import make_user


def _token(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


@pytest.fixture(name="two_types")
def two_types_fixture(session: Session):
    """Two distinct Roles with `tasks` menu access."""
    type_a = Role(name="Financeiro",)
    type_b = Role(name="Juridico",)
    session.add(type_a)
    session.add(type_b)
    session.commit()
    return type_a, type_b


@pytest.fixture(name="category")
def category_fixture(session: Session):
    category = Category(name="Multi Target Category", color="#123456")
    session.add(category)
    session.commit()
    return category


@pytest.fixture(name="admin")
def admin_fixture(session: Session):
    admin = make_user(
        session,
        id=uuid.uuid4(),
        email="multi_admin@test.com",
        full_name="Multi Admin",
        hashed_password=get_password_hash("pass"),
        profile="ADMINISTRATOR",
        cpf="52998224725",
    )
    session.add(admin)
    session.commit()
    return admin


# ---------------------------------------------------------------------------
# assert_manager_can_see_task with multiple targets
# ---------------------------------------------------------------------------


def test_manager_sees_task_with_partial_overlap_across_multiple_targets(
    session: Session, two_types, admin
):
    """A Manager whose effective ids overlap with only ONE of several
    targets can still see the task."""
    type_a, type_b = two_types
    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="partial_overlap_mgr@test.com",
        full_name="Partial Overlap Manager",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="11144477735",
        roles=[type_a],
    )
    session.add(manager)
    session.commit()

    task = Task(
        title="Multi target task",
        created_by_id=admin.id,
        visible_to=[type_a, type_b],
    )
    session.add(task)
    session.commit()

    assert_manager_can_see_task(manager, task, session)  # should not raise


def test_manager_cannot_see_task_with_no_overlap_across_multiple_targets(
    session: Session, two_types, admin
):
    """A Manager with zero overlap across all of a task's multiple targets
    cannot see it."""
    type_a, type_b = two_types
    other_type = Role(name="RH",)
    session.add(other_type)
    session.commit()

    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="no_overlap_mgr@test.com",
        full_name="No Overlap Manager",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="07491723040",
        roles=[other_type],
    )
    session.add(manager)
    session.commit()

    task = Task(
        title="Multi target task 2",
        created_by_id=admin.id,
        visible_to=[type_a, type_b],
    )
    session.add(task)
    session.commit()

    with pytest.raises(TaskNotFoundError):
        assert_manager_can_see_task(manager, task, session)


def test_manager_sees_task_with_zero_targets(session: Session, admin):
    """A task with zero targets remains visible to every Manager
    (unchanged from the old `None` behavior)."""
    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="zero_targets_mgr@test.com",
        full_name="Zero Targets Manager",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="70323955008",
    )
    session.add(manager)
    session.commit()

    task = Task(title="No targets task", created_by_id=admin.id)
    session.add(task)
    session.commit()

    assert task.visible_to == []
    assert_manager_can_see_task(manager, task, session)  # should not raise


def test_manager_sees_task_with_single_target_they_hold(session: Session, admin):
    """A task with exactly one target the Manager holds is visible (basic
    single-target sanity check under the new list-backed relationship)."""
    ut = Role(name="Single Target Type",)
    session.add(ut)
    session.commit()

    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="single_target_mgr@test.com",
        full_name="Single Target Manager",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="94465542073",
        roles=[ut],
    )
    session.add(manager)
    session.commit()

    task = Task(title="Single target task", created_by_id=admin.id, visible_to=[ut])
    session.add(task)
    session.commit()

    assert_manager_can_see_task(manager, task, session)  # should not raise


# ---------------------------------------------------------------------------
# list_tasks SQL filter with multiple targets
# ---------------------------------------------------------------------------


def test_list_tasks_filter_with_multiple_targets(
    client: TestClient, session: Session, two_types, admin, category
):
    """The list_tasks EXISTS/NOT-EXISTS filter correctly surfaces a task
    with multiple targets to a Manager overlapping just one of them, and
    hides a multi-target task with no overlap at all."""
    type_a, type_b = two_types
    other_type = Role(name="No Overlap Type",)
    session.add(other_type)
    session.commit()

    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="list_filter_mgr@test.com",
        full_name="List Filter Manager",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="98765432100",
        roles=[type_b],
    )
    session.add(manager)
    session.commit()

    overlapping = Task(
        title="Overlapping multi-target task",
        created_by_id=admin.id,
        category_id=category.id,
        visible_to=[type_a, type_b],
    )
    non_overlapping = Task(
        title="Non-overlapping multi-target task",
        created_by_id=admin.id,
        category_id=category.id,
        visible_to=[type_a, other_type],
    )
    session.add(overlapping)
    session.add(non_overlapping)
    session.commit()

    token = _token(client, "list_filter_mgr", "pass")
    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Overlapping multi-target task" in titles
    assert "Non-overlapping multi-target task" not in titles

    # The visible task's `visible_to` in the response includes both targets
    # (batch-fetch result assembly, not lost to the WHERE-clause filter).
    overlapping_data = next(
        t for t in response.json() if t["title"] == "Overlapping multi-target task"
    )
    returned_type_ids = {vt["id"] for vt in overlapping_data["visible_to"]}
    assert returned_type_ids == {str(type_a.id), str(type_b.id)}


# ---------------------------------------------------------------------------
# create_task auto-default: explicit ids vs role-type-only fallback
# ---------------------------------------------------------------------------


def test_create_task_defaults_to_all_explicit_ids_not_effective_set(
    client: TestClient, session: Session, category
):
    """A scoped author defaults to exactly the roles they belong to.

    The APRAS-9 distinction this case was written to police — "explicit ids,
    not the *effective* set, or every task becomes visible to every Manager
    org-wide" — collapsed with IAM F5: the role-implicit membership became a
    real `user_role_link` row (migration `0033`), so explicit **is**
    effective. `Gerente (papel)` is one of this author's roles now, and
    including it is correct rather than the leak it used to be.
    """
    type_a = Role(name="Explicit A")
    type_b = Role(name="Explicit B")
    session.add(type_a)
    session.add(type_b)
    session.commit()

    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="explicit_default_mgr@test.com",
        full_name="Explicit Default Manager",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="27943501062",
        roles=[type_a, type_b],
    )
    session.add(manager)
    session.commit()

    token = _token(client, "explicit_default_mgr", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Auto default task", "category_id": str(category.id)},
    )
    assert response.status_code == 200
    profile_row = next(
        role for role in manager.roles if role.name == "Gerente (papel)"
    )
    visible_to_ids = {vt["id"] for vt in response.json()["visible_to"]}
    assert visible_to_ids == {
        str(type_a.id),
        str(type_b.id),
        str(profile_row.id),
    }


def test_create_task_falls_back_to_role_type_when_zero_explicit_types(
    client: TestClient, session: Session, category
):
    """An author whose only role is the profile row defaults to that row.

    The old fallback branch (`effective set` when there are zero explicit
    types) is unreachable since IAM F5 — there is no membership the author
    does not hold explicitly — but the *answer* is the one it produced.
    """
    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="role_fallback_mgr@test.com",
        full_name="Role Fallback Manager",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="53412530006",
    )
    session.add(manager)
    session.commit()

    token = _token(client, "role_fallback_mgr", "pass")
    response = client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Role fallback task", "category_id": str(category.id)},
    )
    assert response.status_code == 200
    profile_row = next(
        role for role in manager.roles if role.name == "Gerente (papel)"
    )
    visible_to_ids = {vt["id"] for vt in response.json()["visible_to"]}
    assert visible_to_ids == {str(profile_row.id)}
