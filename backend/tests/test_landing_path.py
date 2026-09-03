"""§10.4: `role.landing_path` — why the landings had to become data.

`/dashboard` and `/categories` redirected a GUEST to `/welcome` and a PORTEIRO
to `/gate`, on the **effective** role. F4 recorded these as role-shaped and
un-expressible in permissions, and it was right: a PORTEIRO holds `tasks:read`
and `gate:checkin`, and so do A/D/M, so no predicate over the catalogue
separates "pin the gatekeeper to the gate" from "the board can also open the
gate". Landing is a **preference**, not authorization.

So it becomes data on the role row, read back through
`GET /api/v1/permissions/me`. Two properties follow, and both are pinned here:
the value is validated against an allowlist (an open string would be an open
redirect the moment `RootRedirect` consumes it — a security property, not a
nicety), and it follows the *effective* identity, which is safe precisely
because route access stays on the real set.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User
from app.schemas.role import LANDING_PATHS, RoleCreate, RoleUpdate
from tests.conftest import make_user, profile_role


def _auth(user: User) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(DEFAULT_TENANT_ID),
    }


def _user(session: Session, roles: list[Role]) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@landing.example.com",
        full_name="Landing case",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
        roles=roles,
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    session.refresh(user)
    return user


def _landing(client: TestClient, user: User) -> str | None:
    response = client.get("/api/v1/permissions/me", headers=_auth(user))
    assert response.status_code == 200
    return response.json()["landing_path"]


def test_permissions_me_returns_the_first_non_null_landing_path(
    client: TestClient, session: Session
):
    gate = Role(name="Porteiro (papel)", landing_path="/gate")
    session.add(gate)
    session.commit()

    assert _landing(client, _user(session, [gate])) == "/gate"


def test_it_is_null_when_no_role_carries_one(client: TestClient, session: Session):
    plain = Role(name="Sem preferência")
    session.add(plain)
    session.commit()

    assert _landing(client, _user(session, [plain])) is None


def test_a_user_with_two_landing_carrying_roles_gets_the_first_by_name(
    client: TestClient, session: Session
):
    """"First non-null, ordered by role name" is total and deterministic.

    It is only *identical* to the retired enum switch for users with one
    landing-carrying role. A user holding both `Administrador (papel)` and
    `Porteiro (papel)` lands on `/gate`, where the switch — keyed on a single
    global value — sent them to `/dashboard`. That is a deliberate,
    defensible answer: the gatekeeper role is the one that carries an opinion
    about where to land.
    """
    admin = Role(name="Administrador (papel)", landing_path="/dashboard")
    gate = Role(name="Porteiro (papel)", landing_path="/gate")
    session.add_all([admin, gate])
    session.commit()

    # "Administrador (papel)" sorts before "Porteiro (papel)".
    assert _landing(client, _user(session, [gate, admin])) == "/dashboard"

    welcome = Role(name="Convidado (papel)", landing_path="/welcome")
    session.add(welcome)
    session.commit()
    assert _landing(client, _user(session, [gate, welcome])) == "/welcome"


def test_a_role_of_another_tenant_never_supplies_the_landing(
    client: TestClient, session: Session, tenant_b
):
    """Same narrowing as the permission set: the answer is per tenant."""
    elsewhere = Role(name="Porteiro B", landing_path="/gate", tenant_id=tenant_b.id)
    session.add(elsewhere)
    session.commit()

    assert _landing(client, _user(session, [elsewhere])) is None


def test_permissions_me_landing_path_follows_the_simulated_roles(
    client: TestClient, session: Session
):
    """It follows the **effective** identity, and that is safe by design.

    `/permissions/me` is the effective-set endpoint, so simulating a porteiro
    shows the porteiro's landing — which is what an operator previewing a
    role wants. Route *access* stays on the real set
    (`ProtectedRoute.permissions.test.tsx`), so a simulated landing can never
    lock the real administrator out.

    The backend half of that is simply that the endpoint answers for whoever
    the caller is: a user who *is* the porteiro and a superuser previewing
    the porteiro's roles read the same body.
    """
    gate = Role(name="Porteiro (papel)", landing_path="/gate")
    session.add(gate)
    session.commit()
    porteiro = _user(session, [gate])

    previewing = make_user(
        session,
        profile="ADMINISTRATOR",
        id=uuid.uuid4(),
        email="preview@landing.example.com",
        full_name="Preview",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
        roles=[gate],
    )
    session.add(UserTenantLink(user_id=previewing.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    assert _landing(client, porteiro) == "/gate"
    assert _landing(client, previewing) == "/gate"


# ---------------------------------------------------------------------------
# The allowlist is a security property (§8.1)
# ---------------------------------------------------------------------------


def test_the_allowlist_is_the_five_in_app_paths():
    assert frozenset(
        {"/dashboard", "/gate", "/welcome", "/announcements", "/occurrences"}
    ) == LANDING_PATHS


@pytest.mark.parametrize(
    "value",
    ["https://evil.example.com", "//evil.example.com", "/admin/roles", "javascript:x"],
)
def test_role_create_rejects_a_landing_path_outside_the_allowlist(value: str):
    """An open string would be an open redirect the moment `RootRedirect` uses it."""
    with pytest.raises(ValueError, match="Unknown landing_path"):
        RoleCreate(name="Aberta", landing_path=value)
    with pytest.raises(ValueError, match="Unknown landing_path"):
        RoleUpdate(name="Aberta", landing_path=value)


def test_role_create_accepts_an_allowlisted_path_and_none():
    assert RoleCreate(name="Portaria", landing_path="/gate").landing_path == "/gate"
    assert RoleCreate(name="Sem").landing_path is None


def test_the_api_refuses_an_open_landing_path(client: TestClient, session: Session):
    author = make_user(
        session,
        profile="ADMINISTRATOR",
        id=uuid.uuid4(),
        email="author@landing.example.com",
        full_name="Author",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
    )
    session.add(UserTenantLink(user_id=author.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    refused = client.post(
        "/api/v1/roles/",
        headers=_auth(author),
        json={"name": "Aberta", "landing_path": "https://evil.example.com"},
    )
    assert refused.status_code == 422

    accepted = client.post(
        "/api/v1/roles/",
        headers=_auth(author),
        json={"name": "Portaria", "landing_path": "/gate"},
    )
    assert accepted.status_code == 201
    assert accepted.json()["landing_path"] == "/gate"


def test_the_role_editor_writes_and_clears_landing_path(
    client: TestClient, session: Session
):
    """`PATCH /roles/{id}` is the operator-editable half of §10.4.

    The hard-coded enum switch never had this: an operator can now decide
    where a role's members land, and un-decide it.
    """
    author = make_user(
        session,
        profile="ADMINISTRATOR",
        id=uuid.uuid4(),
        email="editor@landing.example.com",
        full_name="Editor",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
    )
    session.add(UserTenantLink(user_id=author.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    role = Role(name="Portaria")
    session.add(role)
    session.commit()
    session.refresh(role)

    set_it = client.patch(
        f"/api/v1/roles/{role.id}",
        headers=_auth(author),
        json={"name": "Portaria", "landing_path": "/gate"},
    )
    assert set_it.status_code == 200
    assert set_it.json()["landing_path"] == "/gate"

    clear_it = client.patch(
        f"/api/v1/roles/{role.id}",
        headers=_auth(author),
        json={"name": "Portaria", "landing_path": None},
    )
    assert clear_it.status_code == 200
    assert clear_it.json()["landing_path"] is None


def test_an_explicit_null_landing_path_is_accepted_by_the_validator():
    """`None` is the "no opinion" value and must survive the allowlist."""
    assert RoleCreate(name="Sem", landing_path=None).landing_path is None
    assert RoleUpdate(name="Sem", landing_path=None).landing_path is None


def test_patching_a_role_without_landing_path_leaves_it(
    client: TestClient, session: Session
):
    """CR1: an omitted `landing_path` is a **no-op**, not a wipe.

    Mirrors `test_permission_escalation.py::
    test_patching_a_group_without_the_permissions_field_leaves_the_bundle`,
    and it has to exist for the same reason: `update_role` overwrites, so a
    field the client did not send must not reach the row.

    The hazard was live, not theoretical. Migration `0033` backfills `/gate`
    onto `Porteiro (papel)` and `/welcome` onto `Convidado (papel)`, and F4's
    role editor saved `{name, permissions}` — so renaming either row, or
    ticking one permission on it, destroyed the landing redirect §10.4 exists
    to preserve.

    `permissions`' `None` sentinel does not transfer: `None` is a meaningful
    value here (it *is* "clear the preference"), so `update_role` reads
    `model_fields_set` to tell an absent field from an explicit null.
    """
    author = make_user(
        session,
        profile="ADMINISTRATOR",
        id=uuid.uuid4(),
        email="omit@landing.example.com",
        full_name="Omit",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
    )
    session.add(UserTenantLink(user_id=author.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    created = client.post(
        "/api/v1/roles/",
        headers=_auth(author),
        json={"name": "Porteiro (papel)", "landing_path": "/gate"},
    )
    assert created.status_code == 201
    role_id = created.json()["id"]

    # The exact payload the role editor sends: no `landing_path` key at all.
    renamed = client.patch(
        f"/api/v1/roles/{role_id}",
        headers=_auth(author),
        json={"name": "Portaria", "permissions": []},
    )

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Portaria"
    assert renamed.json()["landing_path"] == "/gate"

    # And it survives a save that carries neither optional field.
    again = client.patch(
        f"/api/v1/roles/{role_id}",
        headers=_auth(author),
        json={"name": "Portaria Principal"},
    )
    assert again.status_code == 200
    assert again.json()["landing_path"] == "/gate"

    # An **explicit** null still clears it: absent and null stay distinct.
    cleared = client.patch(
        f"/api/v1/roles/{role_id}",
        headers=_auth(author),
        json={"name": "Portaria Principal", "landing_path": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["landing_path"] is None


def test_the_two_backfilled_rows_survive_an_ordinary_save(
    client: TestClient, session: Session
):
    """The regression CR1 names, at the two rows that actually carry a value."""
    author = make_user(
        session,
        profile="ADMINISTRATOR",
        id=uuid.uuid4(),
        email="editor2@landing.example.com",
        full_name="Editor",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
    )
    session.add(UserTenantLink(user_id=author.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    for profile, expected in (("PORTEIRO", "/gate"), ("GUEST", "/welcome")):
        row = profile_role(session, profile)
        assert row.landing_path == expected

        response = client.patch(
            f"/api/v1/roles/{row.id}",
            headers=_auth(author),
            json={"name": row.name, "permissions": sorted(row.permissions)},
        )

        assert response.status_code == 200, response.text
        assert response.json()["landing_path"] == expected, profile
