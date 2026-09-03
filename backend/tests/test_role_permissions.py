"""Role membership after the enum (IAM F5, APRAS-49 §12.2 category 3).

Was `test_role_type_permissions.py`, whose subject was "treating `UserRole` as
an implicit Role" (APRAS-9). That mechanism is gone: migration `0033` turned
the role-implicit membership into a real `user_role_link` row, so
`get_effective_role_ids` is now the user's explicit memberships narrowed to
the acting tenant, and nothing else.

**The effective-set assertions themselves are unchanged** -- what moved is how
the membership gets there. The three cases the enum made possible and F5
inverts are called out where they appear: the menu-gate fallback (deleted with
the gate, §4.1), "role-linked rows cannot be deleted" (now *every* row is
deletable, §13) and `RoleRead.role` (the field is gone, §8.1).
"""

import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import get_effective_role_ids
from app.core.security import create_access_token, get_password_hash
from app.core.tenant_context import acting_tenant_scope
from app.models.category import Category
from app.models.role import Role
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import PROFILE_ROLE_NAMES, make_user


def _token(user: User) -> str:
    return create_access_token(user.id)


# ---------------------------------------------------------------------------
# get_effective_role_ids - unit tests
# ---------------------------------------------------------------------------


def test_effective_ids_are_the_explicit_memberships(session: Session):
    """A user's effective ids are exactly the roles they are linked to."""
    board = Role(name="Board")
    session.add(board)
    session.commit()

    user = make_user(
        session,
        id=uuid.uuid4(),
        email="explicit_only@test.com",
        full_name="Explicit Only",
        hashed_password="x",
        profile="DIRECTOR",
        cpf="52998224725",
        roles=[board],
    )

    profile_row = next(
        role for role in user.roles if role.name == PROFILE_ROLE_NAMES["DIRECTOR"]
    )
    assert get_effective_role_ids(user, session) == {board.id, profile_row.id}


def test_effective_ids_of_a_profile_only_user_are_the_profile_row(session: Session):
    """The membership the enum used to compute is now a real row.

    Before `0033` this user had **no** `user_role_link` row at all and
    `get_effective_role_ids` resolved `Diretor (papel)` from the enum on every
    call. The resolved set is unchanged; the mechanism is data.
    """
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="profile_only@test.com",
        full_name="Profile Only",
        hashed_password="x",
        profile="DIRECTOR",
        cpf="11144477735",
    )

    assert get_effective_role_ids(user, session) == {user.roles[0].id}
    assert user.roles[0].name == PROFILE_ROLE_NAMES["DIRECTOR"]


def test_effective_ids_deduplicate(session: Session):
    """Assigning the profile row a second time yields a set, not a multiset."""
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="dedup@test.com",
        full_name="Dedup",
        hashed_password="x",
        profile="GUEST",
        cpf="07491723040",
    )
    profile_row = user.roles[0]
    user.roles = [profile_row, profile_row]
    session.add(user)
    session.commit()

    ids = get_effective_role_ids(user, session)
    assert ids == {profile_row.id}
    assert len(ids) == 1


def test_effective_ids_are_empty_for_a_user_with_no_roles(session: Session):
    """A user with zero memberships holds zero roles -- and zero permissions.

    This is the shape `POST /auth/signup` now creates (§8.3) and the shape
    migration `0033`'s post-condition guard refuses to leave behind for an
    *active* user (§7.3).
    """
    user = User(
        id=uuid.uuid4(),
        email="none@test.com",
        full_name="None",
        hashed_password="x",
        cpf="70323955008",
    )
    session.add(user)
    session.commit()

    assert get_effective_role_ids(user, session) == set()


def test_effective_ids_are_narrowed_to_the_acting_tenant(session: Session):
    """A role of another tenant never composes into this tenant's answer."""
    tenant_b = Tenant(name="Condomínio B")
    session.add(tenant_b)
    session.commit()
    session.refresh(tenant_b)

    b_role = Role(name="Board B", tenant_id=tenant_b.id)
    session.add(b_role)
    session.commit()

    user = make_user(
        session,
        id=uuid.uuid4(),
        email="dual@test.com",
        full_name="Dual",
        hashed_password="x",
        profile="MANAGER",
        cpf="08050681057",
        roles=[b_role],
    )
    profile_row = next(
        role for role in user.roles if role.name == PROFILE_ROLE_NAMES["MANAGER"]
    )

    assert get_effective_role_ids(user, session) == {profile_row.id}
    with acting_tenant_scope(session, tenant_b.id):
        assert get_effective_role_ids(user, session) == {b_role.id}


# ---------------------------------------------------------------------------
# Task.visible_to targeting a profile row
# ---------------------------------------------------------------------------


def test_a_task_targeted_at_a_profile_row_is_visible_to_its_members(
    client: TestClient, session: Session
):
    """The APRAS-9 case, unchanged in outcome and reachable through data.

    A task whose `visible_to` names `Gerente (papel)` is visible to a manager
    whose only membership is that row -- which is now an explicit link rather
    than an enum match.
    """
    admin = make_user(
        session,
        id=uuid.uuid4(),
        email="admin_vis@test.com",
        full_name="Admin Vis",
        hashed_password=get_password_hash("pass"),
        profile="ADMINISTRATOR",
        cpf="94465542073",
    )
    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="manager_vis@test.com",
        full_name="Manager Vis",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="98765432100",
    )
    category = Category(id=uuid.uuid4(), name="Vis Category", color="#445566")
    session.add(category)
    session.commit()

    task = Task(
        title="Visible via profile row",
        category_id=category.id,
        created_by_id=admin.id,
        visible_to=[manager.roles[0]],
    )
    session.add(task)
    session.commit()

    response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {_token(manager)}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Visible via profile row" in [t["title"] for t in response.json()]


def test_a_task_targeted_elsewhere_is_hidden_from_a_scoped_member(
    client: TestClient, session: Session
):
    """The other half of the same rule: `tasks:read_all` is what lifts it."""
    admin = make_user(
        session,
        id=uuid.uuid4(),
        email="admin_hidden@test.com",
        full_name="Admin Hidden",
        hashed_password=get_password_hash("pass"),
        profile="ADMINISTRATOR",
        cpf="41940480038",
    )
    manager = make_user(
        session,
        id=uuid.uuid4(),
        email="manager_hidden@test.com",
        full_name="Manager Hidden",
        hashed_password=get_password_hash("pass"),
        profile="MANAGER",
        cpf="96476331030",
    )
    other = Role(name="Conselho")
    category = Category(id=uuid.uuid4(), name="Hidden Category", color="#123456")
    session.add(other)
    session.add(category)
    session.commit()

    session.add(
        Task(
            title="Targeted elsewhere",
            category_id=category.id,
            created_by_id=admin.id,
            visible_to=[other],
        )
    )
    session.commit()

    response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {_token(manager)}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Targeted elsewhere" not in [t["title"] for t in response.json()]

    # The administrator holds `tasks:read_all` and is not scoped at all.
    response = client.get(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )
    assert "Targeted elsewhere" in [t["title"] for t in response.json()]


# ---------------------------------------------------------------------------
# There are no undeletable rows any more (§13)
# ---------------------------------------------------------------------------


def test_a_historically_named_role_can_be_deleted(
    client: TestClient, session: Session
):
    """The inversion: `DELETE /roles/{id}` on `Morador (papel)` is 204.

    It was a 403 while `role` identified a "role-linked type that cannot be
    deleted or renamed". `0033` dropped that column, and with it the doctrine:
    the six historically-named rows are ordinary, editable, deletable roles,
    and deleting one strips every member -- the operator's prerogative.
    """
    admin = make_user(
        session,
        id=uuid.uuid4(),
        email="admin_delete@test.com",
        full_name="Admin Delete",
        hashed_password=get_password_hash("pass"),
        profile="ADMINISTRATOR",
        cpf="16899216085",
    )
    resident = make_user(
        session,
        id=uuid.uuid4(),
        email="resident_delete@test.com",
        full_name="Resident Delete",
        hashed_password=get_password_hash("pass"),
        profile="RESIDENT",
        cpf="65970687003",
    )
    row = resident.roles[0]
    assert row.name == PROFILE_ROLE_NAMES["RESIDENT"]

    response = client.delete(
        f"/api/v1/roles/{row.id}",
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(Role, row.id) is None


def test_an_ordinary_role_can_still_be_deleted(client: TestClient, session: Session):
    admin = make_user(
        session,
        id=uuid.uuid4(),
        email="admin_delete2@test.com",
        full_name="Admin Delete 2",
        hashed_password=get_password_hash("pass"),
        profile="ADMINISTRATOR",
        cpf="53412530006",
    )
    regular = Role(name="Board")
    session.add(regular)
    session.commit()

    response = client.delete(
        f"/api/v1/roles/{regular.id}",
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# RoleRead after the drop (§8.1)
# ---------------------------------------------------------------------------


def test_role_read_carries_no_role_and_no_allowed_menus(
    client: TestClient, session: Session
):
    """`{id, name, permissions, landing_path}` -- and nothing else."""
    admin = make_user(
        session,
        id=uuid.uuid4(),
        email="admin_read@test.com",
        full_name="Admin Read",
        hashed_password=get_password_hash("pass"),
        profile="ADMINISTRATOR",
        cpf="27943501062",
    )

    response = client.get(
        "/api/v1/roles/",
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )
    assert response.status_code == status.HTTP_200_OK
    for payload in response.json():
        assert set(payload) == {"id", "name", "permissions", "landing_path"}


def test_create_role_ignores_a_role_field(client: TestClient, session: Session):
    """`RoleCreate` has no `role` field, so a stray one is simply dropped."""
    admin = make_user(
        session,
        id=uuid.uuid4(),
        email="admin_create_role@test.com",
        full_name="Admin Create Role",
        hashed_password=get_password_hash("pass"),
        profile="ADMINISTRATOR",
        cpf="15350946056",
    )

    response = client.post(
        "/api/v1/roles/",
        json={"name": "Sneaky Type", "role": "DIRECTOR"},
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert "role" not in response.json()
