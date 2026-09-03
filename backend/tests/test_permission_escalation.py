"""Anti-escalation on both permission-grant surfaces (IAM F2, APRAS-46 §9).

Groups **become editable** in this slice — that is what makes the permission
bundle reachable at all — so the same slice has to close the escalation it
opens. The rule is one function, `role_service.assert_can_grant`, applied
to the **resulting** set: an author may only put into a group permissions they
themselves hold. It runs on all three grant surfaces:
`POST /api/v1/roles/`, `PATCH /api/v1/roles/{id}` and the
`role_ids` path of `PATCH /api/v1/users/{id}` — because an author who
cannot *create* an over-privileged group could otherwise hand an existing one
to a confederate.

Every case here is **behaviour-neutral at parity time**: nothing seeds a
bundle, so every group's `permissions` is `[]` until one of these routes
writes one, which is precisely why the check is safe to introduce in the
slice that must not diverge. The matrix cells for the three user-type routes
and `PATCH /users/{id}` prove it.
"""

import itertools
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api import deps
from app.core import tenant_context
from app.core.permissions import PERMISSIONS, SUPERUSER_ONLY_PERMISSIONS
from app.core.security import create_access_token, get_password_hash
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User
from tests.conftest import make_user

_cpf_counter = itertools.count(90_000_000_000)

#: The board's "groups:manage" is `roles:create` + `roles:update`;
#: its "finance:manage" is instantiated as `finance:category_create`. Neither
#: board string exists in the catalogue, so §12.4 pins the concrete ones.
GROUPS_MANAGE = ("roles:create", "roles:update")
FINANCE_MANAGE = "finance:category_create"


def _make_user(
    session: Session,
    role: str,
    *,
    tenant_admin: bool,
    is_superuser: bool = False,
) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@escalation.example.com",
        full_name=f"{role} escalation",
        hashed_password=get_password_hash("password"),
        profile=role,
        cpf=str(next(_cpf_counter)),
        is_superuser=is_superuser,
    )
    session.add(user)
    session.commit()
    session.add(
        UserTenantLink(
            user_id=user.id,
            tenant_id=DEFAULT_TENANT_ID,
            is_tenant_admin=tenant_admin,
        )
    )
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(DEFAULT_TENANT_ID),
    }


def _group_author(session: Session) -> User:
    """A RESIDENT carrying a group that grants exactly the author's powers.

    APRAS-47 §4.2 widened `is_tenant_admin` to *every* permission of the
    granting tenant, so the capability holder this module used at the F2
    merge base can no longer be missing one — the case would pass vacuously
    or invert. The replacement author is strictly better: it exercises the
    group mechanism the feature is about, and it is still a RESIDENT, so it
    does **not** hold `finance:category_create` — the board's named case,
    exactly.

    `users:update` rides along because `PATCH /api/v1/users/{id}`, the
    assignment surface of §9.3, is route-guarded on it: without it case 4
    would 403 before `assert_can_grant` ever ran, for the wrong reason.
    """
    user = _make_user(session, "RESIDENT", tenant_admin=False)
    group = Role(
        name=f"Autor {uuid.uuid4().hex[:8]}",
        permissions=[*GROUPS_MANAGE, "users:update"],
    )
    session.add(group)
    session.commit()
    user.roles.append(group)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _superuser(session: Session) -> User:
    """A DIRECTOR-role user carrying the global flag — never an ADMINISTRATOR.

    Explicit, so the case is about `is_superuser` and not about the enum that
    APRAS-47 §3.3 keeps in lockstep with it.
    """
    return _make_user(
        session, "DIRECTOR", tenant_admin=False, is_superuser=True
    )


def _effective(session: Session, user: User) -> frozenset[str]:
    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)
    return deps.get_effective_permissions(user, session)


# ---------------------------------------------------------------------------
# 1 + 2 -- creating a group
# ---------------------------------------------------------------------------


def test_the_author_cannot_create_a_group_carrying_a_permission_they_lack(
    client: TestClient, session: Session
):
    """The board's named case, with the concrete strings of §12.4."""
    author = _group_author(session)
    held = _effective(session, author)
    assert all(permission in held for permission in GROUPS_MANAGE)
    assert FINANCE_MANAGE not in held

    response = client.post(
        "/api/v1/roles/",
        headers=_headers(author),
        json={"name": "Escalado", "permissions": [FINANCE_MANAGE]},
    )

    assert response.status_code == 403
    assert FINANCE_MANAGE in response.json()["detail"]

    listing = client.get("/api/v1/roles/", headers=_headers(author))
    assert listing.status_code == 200
    assert not [row for row in listing.json() if row["name"] == "Escalado"]


def test_the_author_can_create_a_group_carrying_only_what_they_hold(
    client: TestClient, session: Session
):
    """The positive control: without it, the case above could pass wrongly."""
    author = _group_author(session)

    response = client.post(
        "/api/v1/roles/",
        headers=_headers(author),
        json={"name": "Legítimo", "permissions": ["roles:update"]},
    )

    assert response.status_code == 201
    assert response.json()["permissions"] == ["roles:update"]

    created_id = response.json()["id"]
    listing = client.get("/api/v1/roles/", headers=_headers(author))
    stored = next(row for row in listing.json() if row["id"] == created_id)
    assert stored["permissions"] == ["roles:update"]


# ---------------------------------------------------------------------------
# 3 + 7 -- editing a group
# ---------------------------------------------------------------------------


def test_patching_a_group_with_an_unheld_permission_is_403_and_writes_nothing(
    client: TestClient, session: Session
):
    author = _group_author(session)
    created = client.post(
        "/api/v1/roles/",
        headers=_headers(author),
        json={"name": "Editável", "permissions": []},
    )
    assert created.status_code == 201
    group_id = created.json()["id"]
    before = _effective(session, author)

    response = client.patch(
        f"/api/v1/roles/{group_id}",
        headers=_headers(author),
        json={"name": "Editável", "permissions": [FINANCE_MANAGE]},
    )

    assert response.status_code == 403
    assert FINANCE_MANAGE in response.json()["detail"]

    listing = client.get("/api/v1/roles/", headers=_headers(author))
    stored = next(row for row in listing.json() if row["id"] == group_id)
    assert stored["permissions"] == []
    # Escalation is not reachable by self-assignment either: the author's own
    # effective set is unchanged after the refusal (a partial-write guard).
    assert _effective(session, author) == before


def test_patching_a_group_without_the_permissions_field_leaves_the_bundle(
    client: TestClient, session: Session
):
    """`RoleUpdate.permissions` is `None`-sentinelled on purpose (§9.1)."""
    author = _superuser(session)
    created = client.post(
        "/api/v1/roles/",
        headers=_headers(author),
        json={"name": "Com bundle", "permissions": ["tasks:read"]},
    )
    assert created.status_code == 201
    group_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/roles/{group_id}",
        headers=_headers(author),
        json={"name": "Renomeado"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renomeado"
    assert response.json()["permissions"] == ["tasks:read"]


# ---------------------------------------------------------------------------
# 4 -- assigning a group to a user
# ---------------------------------------------------------------------------


def test_assigning_an_over_privileged_group_through_patch_users_is_403(
    client: TestClient, session: Session
):
    author = _group_author(session)
    over_privileged = Role(name="Financeiro", permissions=[FINANCE_MANAGE])
    session.add(over_privileged)
    session.commit()
    session.refresh(over_privileged)

    target = _make_user(session, "GUEST", tenant_admin=False)
    before = [role.id for role in target.roles]

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=_headers(author),
        json={"role_ids": [str(over_privileged.id)]},
    )

    assert response.status_code == 403
    assert FINANCE_MANAGE in response.json()["detail"]

    session.expire_all()
    refreshed = session.get(User, target.id)
    assert [role.id for role in refreshed.roles] == before


def test_assigning_a_group_the_author_can_grant_succeeds(
    client: TestClient, session: Session
):
    author = _group_author(session)
    allowed = Role(name="Grupo permitido", permissions=["roles:update"])
    session.add(allowed)
    session.commit()
    session.refresh(allowed)

    target = _make_user(session, "GUEST", tenant_admin=False)

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=_headers(author),
        json={"role_ids": [str(allowed.id)]},
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["roles"]] == [str(allowed.id)]


# ---------------------------------------------------------------------------
# 5 -- what a superuser may and may not grant (APRAS-47 §4.1, §6.2)
# ---------------------------------------------------------------------------


def test_a_superuser_may_grant_everything_except_the_superuser_only_four(
    client: TestClient, session: Session
):
    """APRAS-47 §4.1 + §6.2, made observable.

    A superuser now holds the whole catalogue — `packages:my_lots_read`
    included, which the ADMINISTRATOR gap used to withhold — so the only
    strings they cannot put into a group are the four whose routes are gated
    by `deps.get_current_superuser`. A group carrying one of those would
    grant nothing, which is why the refusal applies to every author.
    """
    author = _superuser(session)

    for permission in sorted(PERMISSIONS - SUPERUSER_ONLY_PERMISSIONS):
        assert permission in _effective(session, author)

    allowed = client.post(
        "/api/v1/roles/",
        headers=_headers(author),
        json={
            "name": "Quase tudo",
            "permissions": [FINANCE_MANAGE, "packages:my_lots_read"],
        },
    )
    assert allowed.status_code == 201

    for permission in sorted(SUPERUSER_ONLY_PERMISSIONS):
        refused = client.post(
            "/api/v1/roles/",
            headers=_headers(author),
            json={"name": f"Só superusuário {permission}", "permissions": [permission]},
        )
        assert refused.status_code == 403, permission
        assert permission in refused.json()["detail"]


# ---------------------------------------------------------------------------
# 6 -- unknown strings
# ---------------------------------------------------------------------------


def test_an_unknown_permission_string_is_422(client: TestClient, session: Session):
    author = _superuser(session)

    response = client.post(
        "/api/v1/roles/",
        headers=_headers(author),
        json={"name": "Inventado", "permissions": ["finance:manage"]},
    )

    assert response.status_code == 422


def test_a_stored_unknown_string_still_resolves(session: Session):
    """F1's tolerance rule: a hand-edited row stays visible, not vanishing."""
    user = _make_user(session, "GUEST", tenant_admin=False)
    hand_edited = Role(name="Editado à mão", permissions=["finance:manage"])
    session.add(hand_edited)
    session.commit()
    user.roles.append(hand_edited)
    session.add(user)
    session.commit()

    assert "finance:manage" in _effective(session, user)


def test_patching_a_group_with_an_explicit_null_bundle_leaves_it_alone(
    client: TestClient, session: Session
):
    """`"permissions": null` is the same "leave it" sentinel as omitting it."""
    author = _superuser(session)
    created = client.post(
        "/api/v1/roles/",
        headers=_headers(author),
        json={"name": "Bundle nulo", "permissions": ["tasks:read"]},
    )
    assert created.status_code == 201
    group_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/roles/{group_id}",
        headers=_headers(author),
        json={"name": "Bundle nulo", "permissions": None},
    )

    assert response.status_code == 200
    assert response.json()["permissions"] == ["tasks:read"]
