"""The two read-only permission routes (IAM F4, APRAS-48).

`GET /api/v1/permissions/` is the static catalogue the group editor needs in
order to render a permission the author does *not* hold as a **disabled**
checkbox rather than as an absent one; `GET /api/v1/permissions/me` is the
caller's own effective set **in the acting tenant**, which is the thing a
browser cannot compute for itself.

Both are on `UNGUARDED_ROUTES` and neither adds a row to
`ROUTE_PERMISSIONS`, so `tests/data/parity_matrix_baseline.json` stays
byte-identical and `EXPECTED_CELL_COUNT` stays 1080 (§3.3).
"""

import itertools
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api import deps
from app.core.permissions import PERMISSIONS, SUPERUSER_ONLY_PERMISSIONS, module_of
from app.core.security import create_access_token, get_password_hash
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from tests.conftest import make_user

CATALOGUE_URL = "/api/v1/permissions/"
ME_URL = "/api/v1/permissions/me"

_cpf_counter = itertools.count(80_000_000_000)


def _auth(user: User, tenant_id=DEFAULT_TENANT_ID) -> dict[str, str]:
    """Headers for a tenant-scoped route: token plus the acting tenant."""
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(tenant_id),
    }


def _user(
    session: Session,
    role: str = "RESIDENT",
    *,
    is_superuser: bool = False,
    tenants: tuple = (DEFAULT_TENANT_ID,),
    tenant_admin_in=None,
    roles: tuple = (),
) -> User:
    """A persisted user with explicit memberships and groups."""
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@permissions.example.com",
        full_name=f"{role} permissions case",
        hashed_password=get_password_hash("password"),
        profile=role,
        cpf=str(next(_cpf_counter)),
        is_superuser=is_superuser,
        roles=list(roles),
    )
    session.add(user)
    session.commit()
    for tenant_id in tenants:
        session.add(
            UserTenantLink(
                user_id=user.id,
                tenant_id=tenant_id,
                is_tenant_admin=tenant_id == tenant_admin_in,
            )
        )
    session.commit()
    session.refresh(user)
    return user


def _group(session: Session, permissions: list[str], tenant_id=DEFAULT_TENANT_ID):
    """A group (Role) in `tenant_id` carrying `permissions`."""
    group = Role(
        name=f"Grupo {uuid.uuid4().hex[:8]}",
        tenant_id=tenant_id,
        permissions=permissions,
    )
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


# ---------------------------------------------------------------------------
# 1-3 -- the catalogue
# ---------------------------------------------------------------------------


def test_catalogue_lists_every_permission_exactly_once(
    client: TestClient, session: Session
):
    """One row per catalogue entry, in ascending `permission` order."""
    response = client.get(CATALOGUE_URL, headers=_auth(_user(session)))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(PERMISSIONS)
    assert {row["permission"] for row in body} == set(PERMISSIONS)
    assert [row["permission"] for row in body] == sorted(PERMISSIONS)


def test_catalogue_marks_exactly_the_superuser_only_permissions(
    client: TestClient, session: Session
):
    """`superuser_only` mirrors F3's constant, not a re-derived guess."""
    body = client.get(CATALOGUE_URL, headers=_auth(_user(session))).json()

    marked = {row["permission"] for row in body if row["superuser_only"]}
    assert marked == set(SUPERUSER_ONLY_PERMISSIONS)


def test_catalogue_splits_module_and_action(client: TestClient, session: Session):
    """Pre-split, so the UI needs no string surgery of its own."""
    body = client.get(CATALOGUE_URL, headers=_auth(_user(session))).json()

    for row in body:
        assert f"{row['module']}:{row['action']}" == row["permission"]
        assert row["module"] == module_of(row["permission"])


# ---------------------------------------------------------------------------
# 4-7 -- /me, the acting tenant's effective set
# ---------------------------------------------------------------------------


def test_me_returns_the_effective_permissions_of_the_acting_tenant(
    client: TestClient, session: Session, tenant_b: Tenant
):
    """The same user, two tenants, two answers -- the whole point of §2.1.

    A GUEST, because the transitional `LEGACY_ROLE_PERMISSIONS` fallback is
    unioned in for **every** tenant: only a permission the caller's legacy
    role does not already carry can show the group being the difference.
    `finance:read` is `ADMR` in the legacy map, so a GUEST holds it in
    tenant A through the group and nowhere else.
    """
    group_in_a = _group(session, ["finance:read"])
    user = _user(
        session,
        "GUEST",
        tenants=(DEFAULT_TENANT_ID, tenant_b.id),
        roles=(group_in_a,),
    )

    in_a = client.get(ME_URL, headers=_auth(user, DEFAULT_TENANT_ID)).json()
    in_b = client.get(ME_URL, headers=_auth(user, tenant_b.id)).json()

    assert in_a["tenant_id"] == str(DEFAULT_TENANT_ID)
    assert in_b["tenant_id"] == str(tenant_b.id)
    assert "finance:read" in in_a["permissions"]
    assert "finance:read" not in in_b["permissions"]


def test_me_for_a_tenant_admin_is_the_whole_catalogue_in_that_tenant_only(
    client: TestClient, session: Session, tenant_b: Tenant
):
    """F3's `is_tenant_admin` semantics, through the wire."""
    user = _user(
        session,
        tenants=(DEFAULT_TENANT_ID, tenant_b.id),
        tenant_admin_in=DEFAULT_TENANT_ID,
    )

    granting = client.get(ME_URL, headers=_auth(user, DEFAULT_TENANT_ID)).json()
    other = client.get(ME_URL, headers=_auth(user, tenant_b.id)).json()

    assert set(granting["permissions"]) == set(PERMISSIONS)
    assert set(other["permissions"]) < set(PERMISSIONS)


def test_me_for_a_superuser_is_the_whole_catalogue(
    client: TestClient, session: Session
):
    """The global flag is answered before any tenant is resolved."""
    user = _user(session, "DIRECTOR", is_superuser=True)

    body = client.get(ME_URL, headers=_auth(user)).json()

    assert set(body["permissions"]) == set(PERMISSIONS)


def test_me_matches_get_effective_permissions(client: TestClient, session: Session):
    """The route adds nothing of its own: it is `deps`, sorted."""
    group = _group(session, ["occurrences:read", "documents:download"])
    user = _user(session, roles=(group,))

    body = client.get(ME_URL, headers=_auth(user)).json()

    assert body["permissions"] == sorted(deps.get_effective_permissions(user, session))


def test_me_reports_no_disabled_modules_for_an_all_on_tenant(
    client: TestClient, session: Session
):
    """`[]` is the default and the all-on state (APRAS-39 §7)."""
    user = _user(session)

    body = client.get(ME_URL, headers=_auth(user)).json()

    assert body["disabled_modules"] == []


def test_me_reports_the_disabled_modules_after_a_put(
    client: TestClient, session: Session
):
    """The field is additive: one field, one line in the handler, no new route.

    It exists because two frontend consumers cannot derive it — the
    simulation arm builds its set from the role rows rather than from this
    payload, and the "module not enabled" restricted-access variant needs the
    tenant's configuration even when the caller holds nothing.
    """
    superuser = _user(session, "DIRECTOR", is_superuser=True)
    user = _user(session)

    written = client.put(
        f"/api/v1/tenants/{DEFAULT_TENANT_ID}/modules",
        headers=_auth(superuser),
        json={"disabled_modules": ["finance"]},
    )
    assert written.status_code == 200

    body = client.get(ME_URL, headers=_auth(user)).json()

    assert body["disabled_modules"] == ["finance"]
    assert not [p for p in body["permissions"] if module_of(p) == "finance"]


# ---------------------------------------------------------------------------
# 8 -- authentication
# ---------------------------------------------------------------------------


def test_both_routes_require_authentication(client: TestClient):
    """Unguarded is not unauthenticated: no token, no answer."""
    for url in (CATALOGUE_URL, ME_URL):
        assert client.get(url).status_code == 401
