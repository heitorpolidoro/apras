"""ER-7: `PATCH /api/v1/users/{user_id}/superuser` (IAM F5, APRAS-49 §8.4).

F3 shipped one *transitional* writer of the global flag — `update_user`'s
role-change mirror — so that demoting an administrator would not strand
`is_superuser` set. F5 drops the enum, and with it that mirror. Deleting both
would have left a demoted administrator holding the entire catalogue in every
tenant with SQL as the only cure: a privilege-retention hole created by the
slice whose headline is that it creates none.

So the mirror is **replaced**, not merely deleted. This module is the whole
proof of the replacement: the grant, the revoke, the four refusals, the
idempotence, and the two registry facts that keep the parity baseline
byte-identical while the route exists.
"""

import itertools
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api import deps
from app.core.permissions import ROUTE_PERMISSIONS, UNGUARDED_ROUTES
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User
from tests.conftest import make_user
from tests.test_tenant_route_scope import GLOBAL_ROUTES

SUPERUSER_ROUTE = ("PATCH", "/api/v1/users/{user_id}/superuser")

_cpf = itertools.count(88_000_000_000)


def _url(user: User) -> str:
    return f"/api/v1/users/{user.id}/superuser"


def _auth(user: User) -> dict[str, str]:
    """The route is tenant-scoped, so the header is mandatory (§8.4)."""
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(DEFAULT_TENANT_ID),
    }


def _user(
    session: Session,
    profile: str,
    *,
    is_superuser: bool = False,
    tenant_admin: bool = False,
    is_active: bool = True,
) -> User:
    user = make_user(
        session,
        profile=profile,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@grant.example.com",
        full_name=f"{profile} grant case",
        hashed_password=get_password_hash("password"),
        cpf=str(next(_cpf)),
        is_superuser=is_superuser,
        is_active=is_active,
    )
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


# ---------------------------------------------------------------------------
# The grant and the revoke
# ---------------------------------------------------------------------------


def test_a_superuser_can_grant_is_superuser(
    client: TestClient, session: Session
):
    root = _user(session, "DIRECTOR", is_superuser=True)
    target = _user(session, "GUEST")

    response = client.patch(
        _url(target), headers=_auth(root), json={"is_superuser": True}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(target.id),
        "email": target.email,
        "is_superuser": True,
    }
    session.expire_all()
    assert session.get(User, target.id).is_superuser is True

    # And the flag really means the whole catalogue, in this tenant.
    me = client.get("/api/v1/permissions/me", headers=_auth(target))
    assert me.status_code == 200
    assert len(me.json()["permissions"]) == 161


def test_a_superuser_can_revoke_is_superuser(
    client: TestClient, session: Session
):
    root = _user(session, "DIRECTOR", is_superuser=True)
    target = _user(session, "MANAGER", is_superuser=True)

    response = client.patch(
        _url(target), headers=_auth(root), json={"is_superuser": False}
    )

    assert response.status_code == 200
    assert response.json()["is_superuser"] is False
    session.expire_all()
    assert session.get(User, target.id).is_superuser is False

    # The target falls back to their roles' union, not to nothing and not to
    # the catalogue.
    me = client.get("/api/v1/permissions/me", headers=_auth(target))
    assert me.status_code == 200
    assert 0 < len(me.json()["permissions"]) < 159


# ---------------------------------------------------------------------------
# The three refusals of the guard
# ---------------------------------------------------------------------------


def test_a_tenant_admin_cannot_call_the_route(
    client: TestClient, session: Session
):
    """The capability is per-tenant; the flag is global. F3's detail, verbatim."""
    syndic = _user(session, "RESIDENT", tenant_admin=True)
    target = _user(session, "GUEST")

    response = client.patch(
        _url(target), headers=_auth(syndic), json={"is_superuser": True}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"
    session.expire_all()
    assert session.get(User, target.id).is_superuser is False


def test_an_ordinary_user_cannot_call_the_route(
    client: TestClient, session: Session
):
    ordinary = _user(session, "DIRECTOR")
    target = _user(session, "GUEST")

    response = client.patch(
        _url(target), headers=_auth(ordinary), json={"is_superuser": True}
    )

    assert response.status_code == 403


def test_an_unauthenticated_caller_cannot_call_the_route(
    client: TestClient, session: Session
):
    target = _user(session, "GUEST")

    response = client.patch(_url(target), json={"is_superuser": True})

    assert response.status_code == 401


def test_an_unknown_user_id_is_a_404(client: TestClient, session: Session):
    root = _user(session, "DIRECTOR", is_superuser=True)

    response = client.patch(
        f"/api/v1/users/{uuid.uuid4()}/superuser",
        headers=_auth(root),
        json={"is_superuser": True},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# The one refusal of the handler: never leave the install with no way in
# ---------------------------------------------------------------------------


def test_the_last_active_superuser_cannot_demote_themselves(
    client: TestClient, session: Session
):
    root = _user(session, "DIRECTOR", is_superuser=True)

    response = client.patch(
        _url(root), headers=_auth(root), json={"is_superuser": False}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The last superuser cannot be demoted"
    session.expire_all()
    assert session.get(User, root.id).is_superuser is True


def test_the_last_active_superuser_cannot_be_demoted_by_anyone(
    client: TestClient, session: Session
):
    """The rule is stated over the whole table, not over `user_id == me`.

    A second superuser exists but is **inactive**, so demoting the only
    *active* one would still leave the install with no way in — which is why
    the count filters on `is_active` and why this case is distinct from the
    self-demotion one above.
    """
    active_root = _user(session, "DIRECTOR", is_superuser=True)
    inactive_root = _user(session, "MANAGER", is_superuser=True, is_active=False)

    response = client.patch(
        _url(active_root),
        headers=_auth(active_root),
        json={"is_superuser": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The last superuser cannot be demoted"
    session.expire_all()
    assert session.get(User, active_root.id).is_superuser is True
    assert session.get(User, inactive_root.id).is_superuser is True


def test_a_superuser_may_demote_themselves_while_another_active_one_exists(
    client: TestClient, session: Session
):
    first = _user(session, "DIRECTOR", is_superuser=True)
    _second = _user(session, "MANAGER", is_superuser=True)

    response = client.patch(
        _url(first), headers=_auth(first), json={"is_superuser": False}
    )
    assert response.status_code == 200

    # And the demotion takes effect immediately: the caller's next call 403s.
    again = client.patch(
        _url(first), headers=_auth(first), json={"is_superuser": True}
    )
    assert again.status_code == 403


def test_setting_the_flag_to_its_current_value_is_a_no_op(
    client: TestClient, session: Session
):
    """Idempotent, and it never trips the refusal: the count does not change."""
    root = _user(session, "DIRECTOR", is_superuser=True)

    response = client.patch(
        _url(root), headers=_auth(root), json={"is_superuser": True}
    )

    assert response.status_code == 200
    assert response.json()["is_superuser"] is True
    session.expire_all()
    assert session.get(User, root.id).is_superuser is True


# ---------------------------------------------------------------------------
# The two registry facts (§8.4)
# ---------------------------------------------------------------------------


def test_the_route_is_unguarded_by_permission_and_superuser_guarded():
    """It maps to no catalogue permission, so **this route** costs no cell.

    `is_superuser` is a column, not a bundle. Minting a catalogue string whose
    only purpose is to be refused by `assert_can_grant` — and paying six
    baseline cells for it — would be the wrong trade, so the route goes on the
    unguarded allowlist instead. That property is what this case is about, and
    it has not moved.
    """
    assert SUPERUSER_ROUTE in UNGUARDED_ROUTES
    assert SUPERUSER_ROUTE not in ROUTE_PERMISSIONS
    # The F4 merge base is 192 routes / 180 mapped / 12 unguarded; this slice
    # added exactly one route and exactly one allowlist entry. APRAS-39 then
    # added two more by the same convention (the per-tenant module switch) and
    # APRAS-40 seven more (four `/api/v1/plans` and three
    # `/api/v1/tenants/{id}/subscription*`), which is why the count reads 22.
    # `ROUTE_PERMISSIONS` moved 180 -> 183 in APRAS-40, from its three
    # *permission-guarded* billing routes and nothing else; the F2 golden file
    # stays byte-identical because those 18 cells live in the additive
    # `tests/data/parity_matrix_baseline_40.json`.
    assert len(UNGUARDED_ROUTES) == 22
    assert len(ROUTE_PERMISSIONS) == 183

    route = next(
        r
        for r in app.routes
        if getattr(r, "path", None) == SUPERUSER_ROUTE[1]
        and SUPERUSER_ROUTE[0] in getattr(r, "methods", set())
    )

    def _depends_on(dependant, target) -> bool:
        if dependant.call is target:
            return True
        return any(_depends_on(sub, target) for sub in dependant.dependencies)

    assert _depends_on(route.dependant, deps.get_current_superuser)


def test_the_superuser_route_is_tenant_scoped_like_the_rest_of_the_users_router():
    """Deliberately the opposite call from APRAS-43's members route (§8.4).

    That one is global because `is_tenant_admin` is a *per-tenant* capability
    and hiding the acting tenant is what stops a tenant admin granting it to
    themselves. Here the capability is `is_superuser`, a **global** flag only
    a superuser can write, so there is no self-grant to prevent by hiding the
    acting tenant — and moving the route out of the `users` router purely to
    reach `GLOBAL_SCOPED` would cost a new router and a new mount for one
    handler.
    """
    assert SUPERUSER_ROUTE not in GLOBAL_ROUTES
    # 18 at the IAM F5 merge base; APRAS-39's two module-switch routes are
    # mounted on the global tenants router and therefore join this set.
    assert len(GLOBAL_ROUTES) == 27

    route = next(
        r
        for r in app.routes
        if getattr(r, "path", None) == SUPERUSER_ROUTE[1]
        and SUPERUSER_ROUTE[0] in getattr(r, "methods", set())
    )

    def _depends_on(dependant, target) -> bool:
        if dependant.call is target:
            return True
        return any(_depends_on(sub, target) for sub in dependant.dependencies)

    assert _depends_on(route.dependant, deps.get_current_tenant)


def test_a_call_without_the_tenant_header_behaves_like_the_sibling_route(
    client: TestClient, session: Session
):
    """The practical consequence of being scoped, stated so it is not a 400 surprise."""
    root = _user(session, "DIRECTOR", is_superuser=True)
    target = _user(session, "GUEST")
    headers = {"Authorization": f"Bearer {create_access_token(root.id)}"}

    grant = client.patch(_url(target), headers=headers, json={"is_superuser": True})
    sibling = client.patch(
        f"/api/v1/users/{target.id}", headers=headers, json={"full_name": "X"}
    )

    assert grant.status_code == sibling.status_code


def test_user_read_still_does_not_expose_is_superuser(
    client: TestClient, session: Session
):
    """§8.3: who the superusers are is not a fact `GET /users/` may leak."""
    root = _user(session, "DIRECTOR", is_superuser=True)
    _user(session, "GUEST")

    listing = client.get("/api/v1/users/", headers=_auth(root))

    assert listing.status_code == 200
    assert listing.json()
    for payload in listing.json():
        assert "is_superuser" not in payload
        assert "role" not in payload


@pytest.mark.parametrize("field", ["role", "is_superuser"])
def test_user_update_has_no_role_and_no_is_superuser_field(field: str):
    from app.schemas.user import UserUpdate  # noqa: PLC0415

    assert field not in UserUpdate.model_fields
