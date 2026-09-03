"""§3.1 sites 7 and 8: `occurrences:read_assigned`, the MANAGER tier as data.

These two need no exactness argument at all, unlike the task sites:
`occurrences:read_assigned` is the legacy `{M}` set **exactly**, so the
conversion is a literal rewrite. What the two sites did was add one disjunct —
"assigned to me" — to the reporter-or-public tier, for one role. It now adds
it for one permission.

`A/D/R/P` deliberately do **not** hold it: that fact *is* the legacy tier, now
stored as data instead of compiled into an `if` (§3.0). Staff see everything
through `occurrences:manage_all`, which still short-circuits above both sites.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.occurrence import Occurrence
from app.models.role import Role
from app.models.user import User

BASE = ["occurrences:read", "occurrences:create"]


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _user(session: Session, name: str, permissions: list[str]) -> User:
    role = Role(name=name, permissions=permissions)
    session.add(role)
    session.commit()
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@occ.example.com",
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
    reporter = _user(session, "Relator", BASE)
    assignee = _user(session, "Designado", [*BASE, "occurrences:read_assigned"])
    plain = _user(session, "Simples", BASE)
    staff = _user(session, "Diretoria", [*BASE, "occurrences:manage_all"])

    private = Occurrence(
        protocol_number="OCC-PRIVATE",
        reporter_user_id=reporter.id,
        assigned_to_id=assignee.id,
        is_public=False,
        is_anonymous=False,
        category="OTHER",
        title="Privada designada",
        description="…",
    )
    public = Occurrence(
        protocol_number="OCC-PUBLIC",
        reporter_user_id=reporter.id,
        is_public=True,
        is_anonymous=False,
        category="OTHER",
        title="Pública",
        description="…",
    )
    session.add_all([private, public])
    session.commit()
    session.refresh(private)
    session.refresh(public)
    return {
        "reporter": reporter,
        "assignee": assignee,
        "plain": plain,
        "staff": staff,
        "private": private,
        "public": public,
    }


def _titles(client: TestClient, user: User) -> set[str]:
    response = client.get("/api/v1/occurrences", headers=_auth(user))
    assert response.status_code == 200
    return {row["title"] for row in response.json()["items"]}


def test_occurrences_read_assigned_adds_assigned_occurrences_and_nothing_else(
    client: TestClient, world
):
    """The holder gains exactly the assigned-to-me disjunct."""
    assert _titles(client, world["assignee"]) == {"Privada designada", "Pública"}

    detail = client.get(
        f"/api/v1/occurrences/{world['private'].id}",
        headers=_auth(world["assignee"]),
    )
    assert detail.status_code == 200


def test_without_it_the_tier_is_reporter_or_public(client: TestClient, world):
    """A caller with neither permission sees only their own and the public ones."""
    assert _titles(client, world["plain"]) == {"Pública"}

    detail = client.get(
        f"/api/v1/occurrences/{world['private'].id}", headers=_auth(world["plain"])
    )
    assert detail.status_code == 403

    # The reporter still sees their own private occurrence, as always.
    assert _titles(client, world["reporter"]) == {"Privada designada", "Pública"}


def test_being_the_assignee_is_not_enough_without_the_permission(
    client: TestClient, session: Session, world
):
    """The half that makes the permission load-bearing rather than decorative."""
    world["private"].assigned_to_id = world["plain"].id
    session.add(world["private"])
    session.commit()

    assert _titles(client, world["plain"]) == {"Pública"}
    detail = client.get(
        f"/api/v1/occurrences/{world['private'].id}", headers=_auth(world["plain"])
    )
    assert detail.status_code == 403


def test_manage_all_still_short_circuits(client: TestClient, world):
    """Staff see everything, and they reach it above both converted sites."""
    assert _titles(client, world["staff"]) == {"Privada designada", "Pública"}

    detail = client.get(
        f"/api/v1/occurrences/{world['private'].id}", headers=_auth(world["staff"])
    )
    assert detail.status_code == 200
