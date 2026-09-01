"""The `tenant_admin` capability (APRAS-43).

Covers the grant/revoke API, the capability matrix over the seven swapped
tenant-scoped admin routes, the composition with the `allowed_menus` menu
gate, the `/api/v1/tenants` 403s, the route-level structural assertion, the
`ensure_role_types` re-seed path and the inactive-tenant message oracle.

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
from app.core.security import create_access_token, get_password_hash
from app.core.tenant_context import acting_tenant_scope
from app.main import app
from app.models.enums import MenuKey, UserRole
from app.models.lot import Lot
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.user_type import UserType
from app.services.tenant_service import ROLE_TYPE_NAMES, TenantService

TENANT_A = DEFAULT_TENANT_ID


def _auth(user: User, tenant_id=None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


_CPF_COUNTER = iter(range(10_000, 99_999))


def _make_user(session: Session, email: str, role: UserRole) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=email.split("@", maxsplit=1)[0],
        hashed_password=get_password_hash("password"),
        role=role,
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
    user = _make_user(session, "ta-global-admin@test.com", UserRole.ADMINISTRATOR)
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()
    return user


@pytest.fixture(name="tenant_admin")
def tenant_admin_fixture(session: Session, tenant_b: Tenant):
    """A RESIDENT holding the capability on A and a plain membership on B."""
    user = _make_user(session, "ta-syndic@test.com", UserRole.RESIDENT)
    session.add(
        UserTenantLink(user_id=user.id, tenant_id=TENANT_A, is_tenant_admin=True)
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_b.id))
    session.commit()
    return user


@pytest.fixture(name="plain_member")
def plain_member_fixture(session: Session):
    """A RESIDENT member of A holding no capability anywhere."""
    user = _make_user(session, "ta-plain@test.com", UserRole.RESIDENT)
    session.add(UserTenantLink(user_id=user.id, tenant_id=TENANT_A))
    session.commit()
    return user


@pytest.fixture(name="a_rows")
def a_rows_fixture(session: Session, global_admin: User):
    """One task, one lot and one non-role UserType in tenant A."""
    task = Task(title="Tenant A task", created_by_id=global_admin.id)
    lot = Lot(block="A", lot_number="101")
    user_type = UserType(name="Zeladoria A", allowed_menus=[])
    session.add_all([task, lot, user_type])
    session.commit()
    session.refresh(task)
    session.refresh(lot)
    session.refresh(user_type)
    return {"task": task.id, "lot": lot.id, "user_type": user_type.id}


@pytest.fixture(name="b_rows")
def b_rows_fixture(session: Session, tenant_b: Tenant, global_admin: User):
    """The same three rows, in tenant B."""
    task = Task(
        title="Tenant B task", created_by_id=global_admin.id, tenant_id=tenant_b.id
    )
    lot = Lot(block="B", lot_number="202", tenant_id=tenant_b.id)
    user_type = UserType(name="Zeladoria B", allowed_menus=[], tenant_id=tenant_b.id)
    b_user = _make_user(session, "ta-b-only@test.com", UserRole.RESIDENT)
    session.add_all([task, lot, user_type])
    session.commit()
    session.add(UserTenantLink(user_id=b_user.id, tenant_id=tenant_b.id))
    session.commit()
    session.refresh(task)
    session.refresh(lot)
    session.refresh(user_type)
    return {
        "task": task.id,
        "lot": lot.id,
        "user_type": user_type.id,
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
    outsider = _make_user(session, "ta-outsider@test.com", UserRole.RESIDENT)
    response = tenant_client.patch(
        _members_url(tenant_b.id, outsider.id),
        headers=_auth(global_admin),
        json={"is_tenant_admin": True},
    )
    assert response.status_code == 404


def test_membership_can_be_created_already_granted(
    tenant_client: TestClient, global_admin: User, tenant_b: Tenant, session: Session
):
    newcomer = _make_user(session, "ta-newcomer@test.com", UserRole.RESIDENT)
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
    newcomer = _make_user(session, "ta-newcomer2@test.com", UserRole.RESIDENT)
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
            "/api/v1/user-types/",
            headers=headers,
            json={"name": "Criado pelo síndico", "allowed_menus": []},
        ).status_code
        == 201
    )
    assert (
        tenant_client.patch(
            f"/api/v1/user-types/{a_rows['user_type']}",
            headers=headers,
            json={"name": "Zeladoria A2", "allowed_menus": []},
        ).status_code
        == 200
    )
    assert (
        tenant_client.delete(
            f"/api/v1/user-types/{a_rows['user_type']}", headers=headers
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
            "/api/v1/user-types/",
            headers=headers,
            json={"name": "Nope", "allowed_menus": []},
        ),
        tenant_client.patch(
            f"/api/v1/user-types/{b_rows['user_type']}",
            headers=headers,
            json={"name": "Nope", "allowed_menus": []},
        ),
        tenant_client.delete(
            f"/api/v1/user-types/{b_rows['user_type']}", headers=headers
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
            "/api/v1/user-types/",
            headers=headers,
            json={"name": "Nope", "allowed_menus": []},
        ),
        tenant_client.patch(
            f"/api/v1/user-types/{a_rows['user_type']}",
            headers=headers,
            json={"name": "Nope", "allowed_menus": []},
        ),
        tenant_client.delete(
            f"/api/v1/user-types/{a_rows['user_type']}", headers=headers
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
            f"/api/v1/user-types/{b_rows['user_type']}",
            headers=headers,
            json={"name": "Nope", "allowed_menus": []},
        ).status_code
        == 404
    )

    listing = tenant_client.get("/api/v1/users/", headers=headers)
    assert listing.status_code == 200
    assert str(b_rows["user"]) not in {row["id"] for row in listing.json()}


# ---------------------------------------------------------------------------
# §5.1 — composition with the allowed_menus gate
# ---------------------------------------------------------------------------


def test_tenant_admin_is_exempt_from_the_menu_gate_in_their_tenant(
    tenant_client: TestClient, tenant_admin: User
):
    response = tenant_client.get("/api/v1/tasks/", headers=_auth(tenant_admin, TENANT_A))
    assert response.status_code == 200


def test_tenant_admin_is_subject_to_the_menu_gate_elsewhere(
    tenant_client: TestClient, tenant_admin: User, tenant_b: Tenant
):
    response = tenant_client.get(
        "/api/v1/tasks/", headers=_auth(tenant_admin, tenant_b.id)
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough privileges to access tasks"


def test_menu_gate_still_admits_a_matching_user_type_without_the_capability(
    tenant_client: TestClient, session: Session, plain_member: User
):
    """The ordinary UserType path is untouched by the short-circuit."""
    user_type = UserType(name="Tarefas A", allowed_menus=[MenuKey.TASKS.value])
    session.add(user_type)
    session.commit()
    plain_member.user_types.append(user_type)
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
    assert deps.has_admin_capability(tenant_admin, session) is False


def test_is_acting_tenant_admin_reads_the_acting_tenant(
    session: Session, tenant_admin: User, tenant_b: Tenant
):
    with acting_tenant_scope(session, TENANT_A):
        assert deps.is_acting_tenant_admin(tenant_admin, session) is True
        assert deps.has_admin_capability(tenant_admin, session) is True
    with acting_tenant_scope(session, tenant_b.id):
        assert deps.is_acting_tenant_admin(tenant_admin, session) is False
        assert deps.has_admin_capability(tenant_admin, session) is False


def test_the_role_only_guards_stay_available_and_unchanged(
    session: Session, global_admin: User, plain_member: User
):
    """`get_current_active_admin` / `get_current_admin_or_manager` are not
    modified by this task: they remain correct role-only guards for the
    global tenant surface, and `get_current_admin_or_manager` keeps the
    MANAGER widening no tenant-scoped route uses any more."""
    manager = _make_user(session, "ta-manager@test.com", UserRole.MANAGER)

    assert deps.get_current_active_admin(global_admin) is global_admin
    assert deps.get_current_admin_or_manager(global_admin) is global_admin
    assert deps.get_current_admin_or_manager(manager) is manager

    for guard in (deps.get_current_active_admin, deps.get_current_admin_or_manager):
        with pytest.raises(HTTPException) as excinfo:
            guard(plain_member)
        assert excinfo.value.status_code == 403
        assert excinfo.value.detail == "The user doesn't have enough privileges"


def test_has_admin_capability_is_true_for_an_administrator_anywhere(
    session: Session, global_admin: User
):
    assert deps.has_admin_capability(global_admin, session) is True


def test_effective_user_type_ids_are_scoped_to_the_acting_tenant(
    session: Session, tenant_b: Tenant
):
    """Explicit types of another tenant no longer compose into a decision."""
    a_type = UserType(name="Explícito A", allowed_menus=[])
    b_type = UserType(name="Explícito B", allowed_menus=[], tenant_id=tenant_b.id)
    a_role_type = UserType(name="Morador A", allowed_menus=[], role=UserRole.RESIDENT)
    b_role_type = UserType(
        name="Morador B",
        allowed_menus=[],
        role=UserRole.RESIDENT,
        tenant_id=tenant_b.id,
    )
    session.add_all([a_type, b_type, a_role_type, b_role_type])
    session.commit()

    user = _make_user(session, "ta-dual-types@test.com", UserRole.RESIDENT)
    user.user_types = [a_type, b_type]
    session.add(user)
    session.commit()

    with acting_tenant_scope(session, TENANT_A):
        assert deps.get_effective_user_type_ids(user, session) == {
            a_type.id,
            a_role_type.id,
        }
    with acting_tenant_scope(session, tenant_b.id):
        assert deps.get_effective_user_type_ids(user, session) == {
            b_type.id,
            b_role_type.id,
        }


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
# §7 — TenantService.ensure_role_types
# ---------------------------------------------------------------------------


def _role_types(session: Session, tenant_id) -> list[UserType]:
    return list(
        session.exec(
            select(UserType).where(
                UserType.tenant_id == tenant_id, UserType.role.is_not(None)
            )
        ).all()
    )


def test_ensure_role_types_fills_a_tenant_that_has_none(
    session: Session, tenant_b: Tenant
):
    assert _role_types(session, tenant_b.id) == []
    TenantService.ensure_role_types(session, tenant_b.id)
    assert {ut.role for ut in _role_types(session, tenant_b.id)} == set(
        ROLE_TYPE_NAMES
    )


def test_ensure_role_types_is_idempotent(session: Session, tenant_b: Tenant):
    TenantService.ensure_role_types(session, tenant_b.id)
    before = {ut.id for ut in _role_types(session, tenant_b.id)}
    TenantService.ensure_role_types(session, tenant_b.id)
    after = {ut.id for ut in _role_types(session, tenant_b.id)}
    assert before == after
    assert len(after) == len(ROLE_TYPE_NAMES)


def test_ensure_role_types_inserts_only_the_missing_rows(
    session: Session, tenant_b: Tenant
):
    with acting_tenant_scope(session, tenant_b.id):
        session.add(
            UserType(name="Morador (papel)", allowed_menus=[], role=UserRole.RESIDENT)
        )
        session.commit()

    TenantService.ensure_role_types(session, tenant_b.id)
    rows = _role_types(session, tenant_b.id)
    assert len(rows) == len(ROLE_TYPE_NAMES)
    assert len([ut for ut in rows if ut.role == UserRole.RESIDENT]) == 1


def test_create_tenant_still_seeds_one_role_type_per_role(
    tenant_client: TestClient, global_admin: User, session: Session
):
    response = tenant_client.post(
        "/api/v1/tenants", headers=_auth(global_admin), json={"name": "Condomínio Seed"}
    )
    assert response.status_code == 201
    created = uuid.UUID(response.json()["id"])
    session.expire_all()
    assert {ut.role for ut in _role_types(session, created)} == set(ROLE_TYPE_NAMES)


# ---------------------------------------------------------------------------
# §9 — the structural route assertion
# ---------------------------------------------------------------------------

#: The whole post-task `get_current_active_admin` surface: writes on the
#: global `/api/v1/tenants` router, and nothing else.
ADMIN_ONLY_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/tenants"),
        ("PATCH", "/api/v1/tenants/{tenant_id}"),
        ("POST", "/api/v1/tenants/{tenant_id}/members"),
        ("DELETE", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
        ("PATCH", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
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


def test_no_tenant_scoped_route_keeps_a_role_only_admin_guard():
    """`get_current_active_admin` survives only on the global tenant router."""
    offenders = []
    for route in _api_routes():
        if not _depends_on(route.dependant, deps.get_current_tenant):
            continue
        if _depends_on(route.dependant, deps.get_current_active_admin) or _depends_on(
            route.dependant, deps.get_current_admin_or_manager
        ):
            offenders.extend(_route_keys(route))
    assert not offenders, sorted(offenders)


def test_get_current_active_admin_is_exactly_the_five_tenant_writes():
    found = {
        key
        for route in _api_routes()
        if _depends_on(route.dependant, deps.get_current_active_admin)
        for key in _route_keys(route)
    }
    assert found == ADMIN_ONLY_ROUTES
