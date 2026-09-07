"""§3.1 sites 1, 2, 4, 5, 6: the `visible_to` tier, as two permissions.

Four of the eight Rule-C survivors keyed on **one** fact — "MANAGER is scoped
by `visible_to`" — and that is the point of the conversion: four places that
spelled the same sentence become four reads of `tasks:read_all`. The fifth,
`assert_can_edit_task`, keys on `tasks:update_any`.

**Why the conversion is exact, GUEST included.** `tasks:read_all` is the
legacy `{A, D, R, P}` set, i.e. `holders(tasks:read) - {M}`, so for every
actor that can *reach* these sites `not has_permission(..., "tasks:read_all")`
is equivalent to `role == MANAGER`. The single actor for which the two
predicates differ is GUEST — not a MANAGER, and no `tasks:read_all` — and a
GUEST holds none of `tasks:read` / `tasks:create` / `tasks:update`, so the
guard above refuses before any of these lines runs: **the divergent state is
unreachable**. These cases construct both sides of that argument.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.category import Category
from app.models.role import Role
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User

SCOPED = ["tasks:read", "tasks:create", "tasks:update", "tasks:comment"]
UNSCOPED = [*SCOPED, "tasks:read_all", "tasks:update_any"]


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _user(session: Session, name: str, permissions: list[str]) -> User:
    role = Role(name=name, permissions=permissions)
    session.add(role)
    session.commit()
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@tasks.example.com",
        full_name=name,
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
        roles=[role],
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="world")
def world_fixture(session: Session):
    """One category, a scoped author, an unscoped author, and three tasks."""
    category = Category(id=uuid.uuid4(), name="Geral", color="#808080")
    session.add(category)
    session.commit()

    scoped = _user(session, "Escopado", SCOPED)
    unscoped = _user(session, "Irrestrito", UNSCOPED)
    other = Role(name="Conselho")
    session.add(other)
    session.commit()

    untargeted = Task(
        title="Sem alvo", category_id=category.id, created_by_id=unscoped.id
    )
    mine = Task(
        title="Meu alvo",
        category_id=category.id,
        created_by_id=unscoped.id,
        visible_to=[scoped.roles[0]],
    )
    theirs = Task(
        title="Alvo alheio",
        category_id=category.id,
        created_by_id=unscoped.id,
        visible_to=[other],
    )
    session.add_all([untargeted, mine, theirs])
    session.commit()
    for task in (untargeted, mine, theirs):
        session.refresh(task)
    return {
        "category": category,
        "scoped": scoped,
        "unscoped": unscoped,
        "untargeted": untargeted,
        "mine": mine,
        "theirs": theirs,
    }


# ---------------------------------------------------------------------------
# site 4 -- endpoints/tasks.py::list_tasks
# ---------------------------------------------------------------------------


def test_a_user_without_tasks_read_all_is_scoped_by_visible_to_on_list(
    client: TestClient, world
):
    response = client.get("/api/v1/tasks/", headers=_auth(world["scoped"]))

    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert titles == {"Sem alvo", "Meu alvo"}


def test_a_user_with_tasks_read_all_sees_every_task(client: TestClient, world):
    response = client.get("/api/v1/tasks/", headers=_auth(world["unscoped"]))

    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert titles == {"Sem alvo", "Meu alvo", "Alvo alheio"}


# ---------------------------------------------------------------------------
# site 1 -- deps.assert_manager_can_see_task
# ---------------------------------------------------------------------------


def test_a_user_without_tasks_read_all_is_scoped_by_visible_to_on_get(
    client: TestClient, world
):
    """A task targeted elsewhere is a `TaskNotFoundError`, not a 403.

    The exception class and the message are the ones the role comparison
    raised: only the condition changed (§3.1 site 1).
    """
    headers = _auth(world["scoped"])

    assert (
        client.get(
            f"/api/v1/tasks/{world['mine'].id}/history", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/tasks/{world['theirs'].id}/history", headers=headers
        ).status_code
        == 404
    )


def test_a_user_with_tasks_read_all_reaches_a_task_targeted_elsewhere(
    client: TestClient, world
):
    response = client.get(
        f"/api/v1/tasks/{world['theirs'].id}/history",
        headers=_auth(world["unscoped"]),
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# site 2 -- deps.assert_can_edit_task
# ---------------------------------------------------------------------------


def test_a_user_without_tasks_update_any_cannot_edit_an_other_assigned_task(
    client: TestClient, session: Session, world
):
    """The `ForbiddenError` message is kept verbatim as legacy wording (§13)."""
    world["untargeted"].assigned_to_id = world["unscoped"].id
    session.add(world["untargeted"])
    session.commit()

    response = client.patch(
        f"/api/v1/tasks/{world['untargeted'].id}",
        headers=_auth(world["scoped"]),
        json={"status": "IN_PROGRESS"},
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Managers can only edit unassigned or self-assigned tasks"
    )


def test_a_user_without_tasks_update_any_can_edit_their_own_and_unassigned(
    client: TestClient, session: Session, world
):
    unassigned = client.patch(
        f"/api/v1/tasks/{world['untargeted'].id}",
        headers=_auth(world["scoped"]),
        json={"status": "IN_PROGRESS"},
    )
    assert unassigned.status_code == 200

    world["mine"].assigned_to_id = world["scoped"].id
    session.add(world["mine"])
    session.commit()
    own = client.patch(
        f"/api/v1/tasks/{world['mine'].id}",
        headers=_auth(world["scoped"]),
        json={"status": "IN_PROGRESS"},
    )
    assert own.status_code == 200


def test_a_user_with_tasks_update_any_can_edit_an_other_assigned_task(
    client: TestClient, session: Session, world
):
    world["untargeted"].assigned_to_id = world["scoped"].id
    session.add(world["untargeted"])
    session.commit()

    response = client.patch(
        f"/api/v1/tasks/{world['untargeted'].id}",
        headers=_auth(world["unscoped"]),
        json={"status": "IN_PROGRESS"},
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# sites 5 and 6 -- task_service.create_task / update_task
# ---------------------------------------------------------------------------


def test_create_defaults_visible_to_for_a_scoped_author_only(
    client: TestClient, world
):
    """A scoped author's untargeted task would be invisible to them."""
    scoped = client.post(
        "/api/v1/tasks/",
        headers=_auth(world["scoped"]),
        json={"title": "Padrão escopado", "category_id": str(world["category"].id)},
    )
    assert scoped.status_code == 200
    assert {row["id"] for row in scoped.json()["visible_to"]} == {
        str(role.id) for role in world["scoped"].roles
    }

    unscoped = client.post(
        "/api/v1/tasks/",
        headers=_auth(world["unscoped"]),
        json={"title": "Sem padrão", "category_id": str(world["category"].id)},
    )
    assert unscoped.status_code == 200
    assert unscoped.json()["visible_to"] == []


def test_update_rejects_targets_outside_a_scoped_authors_roles(
    client: TestClient, session: Session, world
):
    other = session.exec(
        Role.__table__.select().where(Role.__table__.c.name == "Conselho")
    ).first()

    refused = client.patch(
        f"/api/v1/tasks/{world['mine'].id}",
        headers=_auth(world["scoped"]),
        json={"visible_to_ids": [str(other.id)]},
    )
    assert refused.status_code == 403
    assert (
        refused.json()["detail"]
        == "Managers can only set visibility targets they belong to"
    )

    allowed = client.patch(
        f"/api/v1/tasks/{world['mine'].id}",
        headers=_auth(world["unscoped"]),
        json={"visible_to_ids": [str(other.id)]},
    )
    assert allowed.status_code == 200


def test_the_divergent_guest_state_is_unreachable(
    client: TestClient, session: Session, world
):
    """The load-bearing half of §3.1's exactness argument.

    A GUEST is the one actor for which `not has("tasks:read_all")` and
    `role == MANAGER` disagreed. It holds none of `tasks:read`,
    `tasks:create` or `tasks:update`, so `require_permission` and the
    `tasks:read` line refuse before the converted comparison is ever
    evaluated — which is why the conversion moves no outcome.
    """
    guest = _user(session, "Convidado", [])

    # Since APRAS-51 the listing route enforces its mapped `tasks:read` in the
    # dependency tree, so the refusal is a 403 rather than the empty list this
    # line used to read. The claim is unchanged: the converted comparison is
    # never reached, and now it is not reached one dependency earlier.
    listing = client.get("/api/v1/tasks/", headers=_auth(guest))
    assert listing.status_code == 403
    assert listing.json()["detail"] == "The user doesn't have enough privileges"
    assert (
        client.get(
            f"/api/v1/tasks/{world['untargeted'].id}/history", headers=_auth(guest)
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/tasks/",
            headers=_auth(guest),
            json={"title": "Nope", "category_id": str(world["category"].id)},
        ).status_code
        == 403
    )


def test_a_caller_with_no_roles_who_can_create_always_holds_tasks_read_all(
    client: TestClient, session: Session, world
):
    """Why `create_task`'s APRAS-9 fallback branch is now *unreachable*.

    The two-tier defaulting — explicit roles first, the effective set as a
    fallback — collapsed with the enum: the effective set **is** the explicit
    set since migration `0033`, and a caller with zero roles cannot hold
    `tasks:create` without also holding `tasks:read_all`, because the only
    sources of a permission without a membership are the superuser and
    tenant_admin short-circuits, both of which grant the whole catalogue.
    This case is that argument, executed: a tenant_admin with no roles
    creates a task and nothing is defaulted, because it is not scoped at all.
    """
    syndic = User(
        id=uuid.uuid4(),
        email="syndic@tasks.example.com",
        full_name="Síndico",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
    )
    session.add(syndic)
    session.commit()
    session.add(
        UserTenantLink(
            user_id=syndic.id, tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=True
        )
    )
    session.commit()
    session.refresh(syndic)
    assert syndic.roles == []

    response = client.post(
        "/api/v1/tasks/",
        headers={
            "Authorization": f"Bearer {create_access_token(syndic.id)}",
            "X-Tenant-Id": str(DEFAULT_TENANT_ID),
        },
        json={"title": "Sem papéis", "category_id": str(world["category"].id)},
    )

    assert response.status_code == 200
    # A tenant_admin holds `tasks:read_all`, so nothing is defaulted at all.
    assert response.json()["visible_to"] == []
