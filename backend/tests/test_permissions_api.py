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
from app.models.enums import UserRole
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.user_type import UserType

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
    role: UserRole = UserRole.RESIDENT,
    *,
    is_superuser: bool = False,
    tenants: tuple = (DEFAULT_TENANT_ID,),
    tenant_admin_in=None,
    user_types: tuple = (),
) -> User:
    """A persisted user with explicit memberships and groups."""
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@permissions.example.com",
        full_name=f"{role.value} permissions case",
        hashed_password=get_password_hash("password"),
        role=role,
        cpf=str(next(_cpf_counter)),
        is_superuser=is_superuser,
        user_types=list(user_types),
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
    """A group (UserType) in `tenant_id` carrying `permissions`."""
    group = UserType(
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
        UserRole.GUEST,
        tenants=(DEFAULT_TENANT_ID, tenant_b.id),
        user_types=(group_in_a,),
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
    user = _user(session, UserRole.DIRECTOR, is_superuser=True)

    body = client.get(ME_URL, headers=_auth(user)).json()

    assert set(body["permissions"]) == set(PERMISSIONS)


def test_me_matches_get_effective_permissions(client: TestClient, session: Session):
    """The route adds nothing of its own: it is `deps`, sorted."""
    group = _group(session, ["occurrences:read", "documents:download"])
    user = _user(session, user_types=(group,))

    body = client.get(ME_URL, headers=_auth(user)).json()

    assert body["permissions"] == sorted(deps.get_effective_permissions(user, session))


# ---------------------------------------------------------------------------
# 8 -- authentication
# ---------------------------------------------------------------------------


def test_both_routes_require_authentication(client: TestClient):
    """Unguarded is not unauthenticated: no token, no answer."""
    for url in (CATALOGUE_URL, ME_URL):
        assert client.get(url).status_code == 401
