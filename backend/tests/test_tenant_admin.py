"""The `tenant_admin` capability (APRAS-43).

Covers the grant/revoke API, the capability matrix over the seven swapped
tenant-scoped admin routes, the composition with the `allowed_menus` menu
gate, the `/api/v1/tenants` 403s, the route-level structural assertion, the
`ensure_legacy_roles` re-seed path and the inactive-tenant message oracle.

Every request goes through `tenant_client`, whose override gives each request
its own `Session` — exactly what `app.db.get_session` does in production. That
is what makes the cross-tenant 404s real rather than an artefact of a shared
identity map.
"""

import uuid

import pytest
from fastapi import HTTPException
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api import deps
from app.core.permissions import PERMISSIONS
from app.core.security import create_access_token, get_password_hash
from app.core.tenant_context import acting_tenant_scope
from app.main import app
from app.models.lot import Lot
from app.models.role import Role
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.services.tenant_service import LEGACY_ROLE_NAMES, TenantService
from tests.conftest import make_user

TENANT_A = DEFAULT_TENANT_ID


def _auth(user: User, tenant_id=None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


_CPF_COUNTER = iter(range(10_000, 99_999))


def _make_user(session: Session, email: str, role: str) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=email,
        full_name=email.split("@", maxsplit=1)[0],
        hashed_password=get_password_hash("password"),
        profile=role,
        cpf=f"9{next(_CPF_COUNTER):010d}"[:11],
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="global_admin")
def global_admin_fixture(session: Session):
    """An ADMINISTRATOR whose only membership is tenant A."""
    user = _make_user(session, "ta-global-admin@test.com", "ADMINISTRATOR")
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()
    return user


@pytest.fixture(name="tenant_admin")
def tenant_admin_fixture(session: Session, tenant_b: Tenant):
    """A RESIDENT holding the capability on A and a plain membership on B."""
    user = _make_user(session, "ta-syndic@test.com", "RESIDENT")
    session.add(
        UserTenantLink(user_id=user.id, tenant_id=TENANT_A, is_tenant_admin=True)
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_b.id))
    session.commit()
    return user


@pytest.fixture(name="plain_member")
def plain_member_fixture(session: Session):
    """A RESIDENT member of A holding no capability anywhere."""
    user = _make_user(session, "ta-plain@test.com", "RESIDENT")
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()
    return user


@pytest.fixture(name="a_rows")
def a_rows_fixture(session: Session, global_admin: User):
    """One task, one lot and one non-role Role in tenant A."""
    task = Task(title="Tenant A task", created_by_id=global_admin.id)
    lot = Lot(block="A", lot_number="101")
    role = Role(name="Zeladoria A")
    session.add_all([task, lot, role])
    session.commit()
    session.refresh(task)
    session.refresh(lot)
    session.refresh(role)
    return {"task": task.id, "lot": lot.id, "role": role.id}


@pytest.fixture(name="b_rows")
def b_rows_fixture(session: Session, tenant_b: Tenant, global_admin: User):
    """The same three rows, in tenant B."""
    task = Task(
        title="Tenant B task", created_by_id=global_admin.id, tenant_id=tenant_b.id
    )
    lot = Lot(block="B", lot_number="202", tenant_id=tenant_b.id)
    role = Role(name="Zeladoria B", tenant_id=tenant_b.id)
    b_user = _make_user(session, "ta-b-only@test.com", "RESIDENT")
    session.add_all([task, lot, role])
    session.commit()
    session.add(UserTenantLink(user_id=b_user.id, tenant_id=tenant_b.id))
    session.commit()
    session.refresh(task)
    session.refresh(lot)
    session.refresh(role)
    return {
        "task": task.id,
        "lot": lot.id,
        "role": role.id,
        "user": b_user.id,
    }


# ---------------------------------------------------------------------------
# §3 — grant and revoke through the membership API
# ---------------------------------------------------------------------------


def _members_url(tenant_id, user_id) -> str:
    return f"/api/v1/tenants/{tenant_id}/members/{user_id}"


def test_administrator_grants_the_capability(
    tenant_client: TestClient, global_admin: User, plain_member: User
):
    response = tenant_client.patch(
        _members_url(TENANT_A, plain_member.id),
        headers=_auth(global_admin),
        json={"is_tenant_admin": True},
    )
    assert response.status_code == 200
    assert response.json()["is_tenant_admin"] is True
    assert response.json()["user_id"] == str(plain_member.id)

    listing = tenant_client.get(
        f"/api/v1/tenants/{TENANT_A}/members", headers=_auth(global_admin)
    )
    assert listing.status_code == 200
    rows = {row["user_id"]: row for row in listing.json()}
    assert rows[str(plain_member.id)]["is_tenant_admin"] is True


def test_administrator_revokes_the_capability(
    tenant_client: TestClient, global_admin: User, tenant_admin: User
):
    response = tenant_client.patch(
        _members_url(TENANT_A, tenant_admin.id),
        headers=_auth(global_admin),
        json={"is_tenant_admin": False},
    )
    assert response.status_code == 200
    assert response.json()["is_tenant_admin"] is False

    listing = tenant_client.get(
        f"/api/v1/tenants/{TENANT_A}/members", headers=_auth(global_admin)
    )
    rows = {row["user_id"]: row for row in listing.json()}
    assert rows[str(tenant_admin.id)]["is_tenant_admin"] is False


def test_grant_on_an_unknown_tenant_is_404(
    tenant_client: TestClient, global_admin: User, plain_member: User
):
    response = tenant_client.patch(
        _members_url(uuid.uuid4(), plain_member.id),
        headers=_auth(global_admin),
        json={"is_tenant_admin": True},
    )
    assert response.status_code == 404


def test_grant_for_an_unknown_user_is_404(
    tenant_client: TestClient, global_admin: User
):
    response = tenant_client.patch(
        _members_url(TENANT_A, uuid.uuid4()),
        headers=_auth(global_admin),
        json={"is_tenant_admin": True},
    )
    assert response.status_code == 404


def test_grant_for_a_non_member_is_404(
    tenant_client: TestClient, global_admin: User, tenant_b: Tenant, session: Session
):
    outsider = _make_user(session, "ta-outsider@test.com", "RESIDENT")
    response = tenant_client.patch(
        _members_url(tenant_b.id, outsider.id),
        headers=_auth(global_admin),
        json={"is_tenant_admin": True},
    )
    assert response.status_code == 404


def test_membership_can_be_created_already_granted(
    tenant_client: TestClient, global_admin: User, tenant_b: Tenant, session: Session
):
    newcomer = _make_user(session, "ta-newcomer@test.com", "RESIDENT")
    response = tenant_client.post(
        f"/api/v1/tenants/{tenant_b.id}/members",
        headers=_auth(global_admin),
        json={"user_id": str(newcomer.id), "is_tenant_admin": True},
    )
    assert response.status_code == 201
    assert response.json()["is_tenant_admin"] is True


def test_membership_create_defaults_to_plain_member(
    tenant_client: TestClient, global_admin: User, tenant_b: Tenant, session: Session
):
    newcomer = _make_user(session, "ta-newcomer2@test.com", "RESIDENT")
    response = tenant_client.post(
        f"/api/v1/tenants/{tenant_b.id}/members",
        headers=_auth(global_admin),
        json={"user_id": str(newcomer.id)},
    )
    assert response.status_code == 201
    assert response.json()["is_tenant_admin"] is False


def test_grant_is_403_for_a_plain_member(
    tenant_client: TestClient, plain_member: User
):
    response = tenant_client.patch(
        _members_url(TENANT_A, plain_member.id),
        headers=_auth(plain_member),
        json={"is_tenant_admin": True},
    )
    assert response.status_code == 403


def test_grant_is_403_for_a_tenant_admin_of_that_very_tenant(
    tenant_client: TestClient, tenant_admin: User, plain_member: User
):
    """On a global route the capability is not even readable (§2.1.4)."""
    response = tenant_client.patch(
        _members_url(TENANT_A, plain_member.id),
        headers=_auth(tenant_admin),
        json={"is_tenant_admin": True},
    )
    assert response.status_code == 403


def test_every_tenant_write_is_403_for_a_tenant_admin(
    tenant_client: TestClient, tenant_admin: User, plain_member: User
):
    headers = _auth(tenant_admin)
    assert (
        tenant_client.post(
            "/api/v1/tenants", headers=headers, json={"name": "Condomínio C"}
        ).status_code
        == 403
    )
    assert (
        tenant_client.patch(
            f"/api/v1/tenants/{TENANT_A}", headers=headers, json={"name": "Renamed"}
        ).status_code
        == 403
    )
    assert (
        tenant_client.post(
            f"/api/v1/tenants/{TENANT_A}/members",
            headers=headers,
            json={"user_id": str(plain_member.id)},
        ).status_code
        == 403
    )
    assert (
        tenant_client.delete(
            _members_url(TENANT_A, plain_member.id), headers=headers
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# §4.3 — the capability matrix over the seven swapped routes
# ---------------------------------------------------------------------------


def test_tenant_admin_passes_every_admin_gated_route_in_their_tenant(
    tenant_client: TestClient,
    tenant_admin: User,
    plain_member: User,
    a_rows: dict,
):
    headers = _auth(tenant_admin, TENANT_A)

    assert tenant_client.get("/api/v1/users/", headers=headers).status_code == 200
    assert (
        tenant_client.patch(
            f"/api/v1/users/{plain_member.id}",
            headers=headers,
            json={"full_name": "Renamed Member"},
        ).status_code
        == 200
    )
    assert (
        tenant_client.patch(
            f"/api/v1/users/{plain_member.id}/contact-info",
            headers=headers,
            json={"phone": "11999999999"},
        ).status_code
        == 200
    )
    assert (
        tenant_client.post(
            "/api/v1/roles/",
            headers=headers,
            json={"name": "Criado pelo síndico" },
        ).status_code
        == 201
    )
    assert (
        tenant_client.patch(
            f"/api/v1/roles/{a_rows['role']}",
            headers=headers,
            json={"name": "Zeladoria A2" },
        ).status_code
        == 200
    )
    assert (
        tenant_client.delete(
            f"/api/v1/roles/{a_rows['role']}", headers=headers
        ).status_code
        == 204
    )
    assert (
        tenant_client.delete(
            f"/api/v1/tasks/{a_rows['task']}", headers=headers
        ).status_code
        == 204
    )
    assert (
        tenant_client.delete(
            f"/api/v1/lots/{a_rows['lot']}", headers=headers
        ).status_code
        == 204
    )


def test_tenant_admin_is_403_acting_where_they_hold_no_grant(
    tenant_client: TestClient,
    tenant_admin: User,
    tenant_b: Tenant,
    b_rows: dict,
):
    headers = _auth(tenant_admin, tenant_b.id)
    forbidden = [
        tenant_client.patch(
            f"/api/v1/users/{b_rows['user']}",
            headers=headers,
            json={"full_name": "Nope"},
        ),
        tenant_client.patch(
            f"/api/v1/users/{b_rows['user']}/contact-info",
            headers=headers,
            json={"phone": "11888888888"},
        ),
        tenant_client.post(
            "/api/v1/roles/",
            headers=headers,
            json={"name": "Nope" },
        ),
        tenant_client.patch(
            f"/api/v1/roles/{b_rows['role']}",
            headers=headers,
            json={"name": "Nope" },
        ),
        tenant_client.delete(
            f"/api/v1/roles/{b_rows['role']}", headers=headers
        ),
        tenant_client.delete(f"/api/v1/tasks/{b_rows['task']}", headers=headers),
        tenant_client.delete(f"/api/v1/lots/{b_rows['lot']}", headers=headers),
    ]
    assert [response.status_code for response in forbidden] == [403] * 7


def test_plain_member_of_a_is_403_on_the_same_routes(
    tenant_client: TestClient, plain_member: User, a_rows: dict, global_admin: User
):
    headers = _auth(plain_member, TENANT_A)
    forbidden = [
        tenant_client.patch(
            f"/api/v1/users/{global_admin.id}",
            headers=headers,
            json={"full_name": "Nope"},
        ),
        tenant_client.patch(
            f"/api/v1/users/{global_admin.id}/contact-info",
            headers=headers,
            json={"phone": "11888888888"},
        ),
        tenant_client.post(
            "/api/v1/roles/",
            headers=headers,
            json={"name": "Nope" },
        ),
        tenant_client.patch(
            f"/api/v1/roles/{a_rows['role']}",
            headers=headers,
            json={"name": "Nope" },
        ),
        tenant_client.delete(
            f"/api/v1/roles/{a_rows['role']}", headers=headers
        ),
        tenant_client.delete(f"/api/v1/tasks/{a_rows['task']}", headers=headers),
        tenant_client.delete(f"/api/v1/lots/{a_rows['lot']}", headers=headers),
    ]
    assert [response.status_code for response in forbidden] == [403] * 7


def test_tenant_admin_never_reaches_tenant_b_data_while_acting_in_a(
    tenant_client: TestClient, tenant_admin: User, b_rows: dict
):
    headers = _auth(tenant_admin, TENANT_A)

    assert (
        tenant_client.patch(
            f"/api/v1/users/{b_rows['user']}",
            headers=headers,
            json={"full_name": "Nope"},
        ).status_code
        == 404
    )
    assert (
        tenant_client.patch(
            f"/api/v1/roles/{b_rows['role']}",
            headers=headers,
            json={"name": "Nope" },
        ).status_code
        == 404
    )

    listing = tenant_client.get("/api/v1/users/", headers=headers)
    assert listing.status_code == 200
    assert str(b_rows["user"]) not in {row["id"] for row in listing.json()}


# ---------------------------------------------------------------------------
# §5.1 — the capability composes with the permission layer
# ---------------------------------------------------------------------------
#
# IAM F5 (APRAS-49 §4.1) deleted the `allowed_menus` gate these three cases
# were written against. What they measured — "the capability short-circuits
# in its own tenant and grants nothing anywhere else" — survives verbatim on
# `tasks:read`, which is what gates `/api/v1/tasks/` now. The *shape* of the
# refusal moves: it is `require_permission`'s 403 rather than the gate's, so
# the detail string changes with the guard that emits it.


def test_tenant_admin_is_exempt_from_the_permission_check_in_their_tenant(
    tenant_client: TestClient, tenant_admin: User
):
    response = tenant_client.get("/api/v1/tasks/", headers=_auth(tenant_admin, TENANT_A))
    assert response.status_code == 200


def test_tenant_admin_holds_nothing_elsewhere(
    tenant_client: TestClient, tenant_admin: User, tenant_b: Tenant
):
    """In tenant B the capability is not readable, so the bundle is all.

    The list is **refused**, not empty: since APRAS-51 `tasks:read` *is* a
    route-level guard on `GET /api/v1/tasks/`, so a caller who resolves no
    `tasks:read` in the acting tenant gets `require_permission`'s 403 instead
    of the empty page it used to be served. The claim of this case is
    unchanged and is if anything sharper -- the capability grants nothing
    outside the tenant that granted it.
    """
    response = tenant_client.get(
        "/api/v1/tasks/", headers=_auth(tenant_admin, tenant_b.id)
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


def test_an_ordinary_role_still_admits_a_member_without_the_capability(
    tenant_client: TestClient, session: Session, plain_member: User
):
    """The ordinary Role path is untouched by the short-circuit."""
    role = Role(name="Tarefas A", permissions=["tasks:read"])
    session.add(role)
    session.commit()
    plain_member.roles.append(role)
    session.add(plain_member)
    session.commit()

    response = tenant_client.get("/api/v1/tasks/", headers=_auth(plain_member, TENANT_A))
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# §4.1 — the helpers, in isolation
# ---------------------------------------------------------------------------


def test_is_acting_tenant_admin_is_false_without_an_acting_tenant(
    session: Session, tenant_admin: User
):
    """A `Session` with no acting tenant grants nothing — fail closed."""
    assert deps.is_acting_tenant_admin(tenant_admin, session) is False


def test_is_acting_tenant_admin_reads_the_acting_tenant(
    session: Session, tenant_admin: User, tenant_b: Tenant
):
    with acting_tenant_scope(session, TENANT_A):
        assert deps.is_acting_tenant_admin(tenant_admin, session) is True
    with acting_tenant_scope(session, tenant_b.id):
        assert deps.is_acting_tenant_admin(tenant_admin, session) is False


def test_the_superuser_guard_stays_available_and_unchanged(
    session: Session, global_admin: User, plain_member: User
):
    """The global tenant surface keeps exactly one guard, with the same 403.

    APRAS-47 §5.1 converted `get_current_active_admin` into
    `get_current_superuser` — it now reads `User.is_superuser`, and the
    detail string is byte-identical — and deleted
    `get_current_admin_or_manager`, whose last caller APRAS-46 removed.
    `global_admin` is an ADMINISTRATOR, so §3.3's transitional default
    carries the flag and this guard answers for them exactly as before.
    """
    assert global_admin.is_superuser is True
    assert deps.get_current_superuser(global_admin) is global_admin

    with pytest.raises(HTTPException) as excinfo:
        deps.get_current_superuser(plain_member)
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "The user doesn't have enough privileges"


def test_a_superuser_needs_no_capability_anywhere(
    session: Session, global_admin: User
):
    """`has_admin_capability` died with its only caller (§4.1).

    It existed to let `assert_menu_access` short-circuit for "administrator
    here", and F3 §5.1 already recorded that the gate was its sole consumer.
    The property it expressed survives on the flag itself, which
    `get_effective_permissions` short-circuits on before any tenant is
    resolved.
    """
    assert not hasattr(deps, "has_admin_capability")
    assert global_admin.is_superuser is True
    assert deps.get_effective_permissions(global_admin, session) == PERMISSIONS


def test_effective_role_ids_are_scoped_to_the_acting_tenant(
    session: Session, tenant_b: Tenant
):
    """Explicit types of another tenant no longer compose into a decision."""
    a_type = Role(name="Explícito A")
    b_type = Role(name="Explícito B", tenant_id=tenant_b.id)
    session.add_all([a_type, b_type])
    session.commit()

    user = _make_user(session, "ta-dual-types@test.com", "RESIDENT")
    profile_row = user.roles[0]
    user.roles = [profile_row, a_type, b_type]
    session.add(user)
    session.commit()

    with acting_tenant_scope(session, TENANT_A):
        assert deps.get_effective_role_ids(user, session) == {
            a_type.id,
            profile_row.id,
        }
    with acting_tenant_scope(session, tenant_b.id):
        assert deps.get_effective_role_ids(user, session) == {b_type.id}


# ---------------------------------------------------------------------------
# §7 — the inactive-tenant existence oracle
# ---------------------------------------------------------------------------


def test_non_member_of_an_inactive_tenant_gets_the_membership_message(
    tenant_client: TestClient, session: Session, tenant_b: Tenant, plain_member: User
):
    """Byte-identical to the answer for an *active* tenant they are not a
    member of, so the pair of messages stops being an existence oracle."""
    active_answer = tenant_client.get(
        "/api/v1/categories/", headers=_auth(plain_member, tenant_b.id)
    )
    tenant_b.is_active = False
    session.add(tenant_b)
    session.commit()

    inactive_answer = tenant_client.get(
        "/api/v1/categories/", headers=_auth(plain_member, tenant_b.id)
    )

    assert active_answer.status_code == inactive_answer.status_code == 403
    assert (
        active_answer.json()["detail"]
        == inactive_answer.json()["detail"]
        == "Not a member of the requested tenant"
    )


def test_member_of_an_inactive_tenant_still_gets_the_inactive_message(
    tenant_client: TestClient, session: Session, tenant_b: Tenant, tenant_admin: User
):
    tenant_b.is_active = False
    session.add(tenant_b)
    session.commit()

    response = tenant_client.get(
        "/api/v1/categories/", headers=_auth(tenant_admin, tenant_b.id)
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is inactive"


# ---------------------------------------------------------------------------
# §7 — TenantService.ensure_legacy_roles
# ---------------------------------------------------------------------------


def _role_types(session: Session, tenant_id) -> list[Role]:
    """The historically-named rows of `tenant_id`.

    Keyed on **name** since IAM F5 (APRAS-49 §9.2): the `role` column that
    identified them was dropped by migration `0033`.
    """
    return list(
        session.exec(
            select(Role).where(
                Role.tenant_id == tenant_id, Role.name.in_(LEGACY_ROLE_NAMES)
            )
        ).all()
    )


def test_ensure_legacy_roles_fills_a_tenant_that_has_none(
    session: Session, tenant_b: Tenant
):
    assert _role_types(session, tenant_b.id) == []
    TenantService.ensure_legacy_roles(session, tenant_b.id)
    assert {ut.name for ut in _role_types(session, tenant_b.id)} == set(
        LEGACY_ROLE_NAMES
    )


def test_ensure_legacy_roles_is_idempotent(session: Session, tenant_b: Tenant):
    TenantService.ensure_legacy_roles(session, tenant_b.id)
    before = {ut.id for ut in _role_types(session, tenant_b.id)}
    TenantService.ensure_legacy_roles(session, tenant_b.id)
    after = {ut.id for ut in _role_types(session, tenant_b.id)}
    assert before == after
    assert len(after) == len(LEGACY_ROLE_NAMES)


def test_ensure_legacy_roles_inserts_only_the_missing_rows(
    session: Session, tenant_b: Tenant
):
    with acting_tenant_scope(session, tenant_b.id):
        session.add(
            Role(name="Morador (papel)")
        )
        session.commit()

    TenantService.ensure_legacy_roles(session, tenant_b.id)
    rows = _role_types(session, tenant_b.id)
    assert len(rows) == len(LEGACY_ROLE_NAMES)
    assert len([ut for ut in rows if ut.name == "Morador (papel)"]) == 1


def test_create_tenant_still_seeds_the_six_historically_named_roles(
    tenant_client: TestClient, global_admin: User, session: Session
):
    response = tenant_client.post(
        "/api/v1/tenants", headers=_auth(global_admin), json={"name": "Condomínio Seed"}
    )
    assert response.status_code == 201
    created = uuid.UUID(response.json()["id"])
    session.expire_all()
    assert {ut.name for ut in _role_types(session, created)} == set(LEGACY_ROLE_NAMES)


# ---------------------------------------------------------------------------
# §9 — the structural route assertion
# ---------------------------------------------------------------------------

#: The whole post-task `get_current_superuser` surface: writes on the
#: global `/api/v1/tenants` router, and nothing else.
ADMIN_ONLY_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/tenants"),
        ("PATCH", "/api/v1/tenants/{tenant_id}"),
        ("POST", "/api/v1/tenants/{tenant_id}/members"),
        ("DELETE", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
        ("PATCH", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
        # IAM F5 (APRAS-49 §8.4): the one route outside `/api/v1/tenants`
        # that `get_current_superuser` guards -- the grant and the revoke of
        # the global flag itself.
        ("PATCH", "/api/v1/users/{user_id}/superuser"),
        # APRAS-39 §6.4: the per-tenant module switch, read and write. The
        # module switch is a property of the tenant, written from *outside*
        # it -- a tenant_admin must not be able to reach it by acting in
        # their own tenant, which is exactly what the global mount plus this
        # guard produce. Declared as a real `Depends`, never inlined: this
        # assertion is an exact set over the dependency tree.
        ("GET", "/api/v1/tenants/{tenant_id}/modules"),
        ("PUT", "/api/v1/tenants/{tenant_id}/modules"),
        # APRAS-40 §5.3: the commercial surfaces. Three per-tenant
        # subscription routes on this same global tenants router, and the
        # four routes of the wholly superuser-only `plans` router. Like the
        # lines above they declare a real
        # `Depends(api_deps.get_current_superuser)` and never an in-handler
        # `if not user.is_superuser`: this assertion is an exact set over
        # `_depends_on(route.dependant, deps.get_current_superuser)`, so an
        # inlined check would be invisible to it and to the two other
        # structural walkers in this repository.
        ("GET", "/api/v1/tenants/{tenant_id}/subscription"),
        ("PUT", "/api/v1/tenants/{tenant_id}/subscription"),
        ("PUT", "/api/v1/tenants/{tenant_id}/subscription/courtesy"),
        # APRAS-52 §2.2: the fourth per-tenant subscription route, the
        # operator's change-history read. A tenant_admin of that very tenant
        # is refused here too -- the router is global, so the capability is
        # not even readable.
        ("GET", "/api/v1/tenants/{tenant_id}/subscription/history"),
        ("GET", "/api/v1/plans/"),
        ("POST", "/api/v1/plans/"),
        ("GET", "/api/v1/plans/{plan_id}"),
        ("PATCH", "/api/v1/plans/{plan_id}"),
    }
)


def _depends_on(dependant: Dependant, target) -> bool:
    if dependant.call is target:
        return True
    return any(_depends_on(sub, target) for sub in dependant.dependencies)


def _route_keys(route: APIRoute) -> list[tuple[str, str]]:
    return [(method, route.path) for method in sorted(route.methods)]


def _api_routes() -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


#: The one tenant-scoped route that is nevertheless superuser-guarded (IAM
#: F5, APRAS-49 §8.4). The classification is deliberate and is the *opposite*
#: call from APRAS-43's `PATCH /tenants/{id}/members/{user_id}`: that one is
#: global because `is_tenant_admin` is a per-tenant capability and hiding the
#: acting tenant is what stops a tenant admin granting it to themselves. Here
#: the capability is `is_superuser`, a **global** flag only a superuser can
#: write, so there is no self-grant to prevent by hiding the acting tenant --
#: and moving the route out of the `users` router purely to reach
#: `GLOBAL_SCOPED` would cost a new router and a new mount for one handler.
#: The practical consequence: the caller must send the tenant header, and the
#: acting tenant plays no part in the decision or in what is written.
SUPERUSER_GUARDED_SCOPED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {("PATCH", "/api/v1/users/{user_id}/superuser")}
)


def test_only_the_superuser_grant_is_both_scoped_and_superuser_guarded():
    """`get_current_superuser` survives on the global tenant router and §8.4."""
    offenders = []
    for route in _api_routes():
        if not _depends_on(route.dependant, deps.get_current_tenant):
            continue
        if _depends_on(route.dependant, deps.get_current_superuser):
            offenders.extend(_route_keys(route))
    assert set(offenders) == SUPERUSER_GUARDED_SCOPED_ROUTES, sorted(offenders)


def test_get_current_superuser_is_exactly_the_sixteen_operator_routes():
    """The name states the count, so the count is asserted beside it.

    8 at the APRAS-39 merge base; APRAS-40 adds **7** (four `/api/v1/plans`
    and three `/api/v1/tenants/{tenant_id}/subscription*`), all seven
    declaring a real `Depends(api_deps.get_current_superuser)`; APRAS-52 adds
    the **sixteenth**, the per-tenant change-history read, declared the same
    way. The `len` assertion is what keeps this module's whole premise true
    -- that its case names state its counts -- after round 1 shipped a name
    saying fourteen over a set of fifteen.
    """
    found = {
        key
        for route in _api_routes()
        if _depends_on(route.dependant, deps.get_current_superuser)
        for key in _route_keys(route)
    }
    assert found == ADMIN_ONLY_ROUTES
    assert len(ADMIN_ONLY_ROUTES) == 16
