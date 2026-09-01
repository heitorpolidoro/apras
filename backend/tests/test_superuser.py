"""The global `is_superuser` column (IAM F3, APRAS-47).

The flag is the subject, so every case constructs it **explicitly** — a
`DIRECTOR` with `is_superuser=True`, an `ADMINISTRATOR` with
`is_superuser=False` — and never leans on §3.3's creation-time default.
That is what makes these assertions about `is_superuser` rather than about
`role`.
"""

import io
import itertools
import uuid

from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session, select

from app.api import deps
from app.core import tenant_context
from app.core.permissions import (
    LEGACY_ROLE_PERMISSIONS,
    PERMISSIONS,
    ROUTE_PERMISSIONS,
    SUPERUSER_ONLY_PERMISSIONS,
)
from app.core.security import create_access_token, get_password_hash
from app.models.enums import UserRole
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.user_type import UserType

_cpf_counter = itertools.count(70_000_000_000)


def _make_user(
    session: Session | None,
    role: UserRole,
    *,
    is_superuser: bool | None = None,
) -> User:
    """Build (and optionally persist) a user with an explicit flag."""
    data = {
        "id": uuid.uuid4(),
        "email": f"{uuid.uuid4().hex[:12]}@superuser.example.com",
        "full_name": f"{role.value} superuser case",
        "hashed_password": get_password_hash("password"),
        "role": role,
        "cpf": str(next(_cpf_counter)),
    }
    if is_superuser is not None:
        data["is_superuser"] = is_superuser
    user = User(**data)
    if session is not None:
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# 19 -- the creation-time default (§3.3)
# ---------------------------------------------------------------------------


def test_an_administrator_defaults_to_superuser():
    assert _make_user(None, UserRole.ADMINISTRATOR).is_superuser is True


def test_an_explicit_false_beats_the_administrator_default():
    assert (
        _make_user(None, UserRole.ADMINISTRATOR, is_superuser=False).is_superuser
        is False
    )


def test_a_non_administrator_is_not_a_superuser_by_default():
    assert _make_user(None, UserRole.DIRECTOR).is_superuser is False


def test_an_explicit_true_on_a_non_administrator_is_kept():
    assert _make_user(None, UserRole.DIRECTOR, is_superuser=True).is_superuser is True


def test_a_stored_administrator_with_the_flag_off_reads_back_off(session: Session):
    """`__init__` is not reached on DB load, so the column is the source of truth."""
    user = _make_user(session, UserRole.ADMINISTRATOR, is_superuser=False)
    session.expire_all()

    reloaded = session.get(User, user.id)
    session.refresh(reloaded)

    assert reloaded.role is UserRole.ADMINISTRATOR
    assert reloaded.is_superuser is False


# ---------------------------------------------------------------------------
# 1-7 -- resolution (ER-2): the two short-circuits of §4
# ---------------------------------------------------------------------------


def _superuser(session: Session) -> User:
    """A DIRECTOR-role user carrying the flag — never an ADMINISTRATOR.

    The point of the module: these assertions are about `is_superuser`, and a
    DIRECTOR is what makes them unable to pass for the wrong reason.
    """
    user = _make_user(session, UserRole.DIRECTOR, is_superuser=True)
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    return user


def _tenant_admin_of_a(session: Session, tenant_b: Tenant) -> User:
    """A RESIDENT holding the capability on A and a plain membership on B."""
    user = _make_user(session, UserRole.RESIDENT, is_superuser=False)
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=True
        )
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_b.id))
    session.commit()
    return user


def test_a_superuser_holds_the_whole_catalogue_in_the_granting_tenant(
    session: Session,
):
    user = _superuser(session)
    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)

    assert deps.get_effective_permissions(user, session) == PERMISSIONS


def test_a_superuser_holds_the_whole_catalogue_in_a_tenant_they_do_not_belong_to(
    session: Session, tenant_b: Tenant
):
    user = _superuser(session)
    tenant_context.set_acting_tenant(session, tenant_b.id)

    assert deps.get_effective_permissions(user, session) == PERMISSIONS


def test_a_superuser_holds_the_whole_catalogue_with_no_acting_tenant(
    session: Session,
):
    """The flag is global, so it is answered before any tenant is resolved."""
    user = _superuser(session)

    assert tenant_context.acting_tenant_id(session) is None
    assert deps.get_effective_permissions(user, session) == PERMISSIONS


def test_a_tenant_admin_holds_the_whole_catalogue_in_the_granting_tenant(
    session: Session, tenant_b: Tenant
):
    user = _tenant_admin_of_a(session, tenant_b)
    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)

    assert deps.get_effective_permissions(user, session) == PERMISSIONS


def test_a_tenant_admin_of_a_holds_only_their_role_bundle_in_b(
    session: Session, tenant_b: Tenant
):
    """The non-leakage case. Set equality, so the precondition is asserted."""
    user = _tenant_admin_of_a(session, tenant_b)
    tenant_context.set_acting_tenant(session, tenant_b.id)

    # Only meaningful if nothing else contributes: no UserType resolves for
    # this user in B, and no UserType reachable in B carries a bundle.
    assert deps.get_effective_user_type_ids(user, session) == set()
    reachable = session.exec(
        select(UserType).where(UserType.tenant_id == tenant_b.id)
    ).all()
    assert all(user_type.permissions == [] for user_type in reachable)

    assert (
        deps.get_effective_permissions(user, session)
        == LEGACY_ROLE_PERMISSIONS[UserRole.RESIDENT]
    )


def test_a_tenant_admin_holds_only_their_role_bundle_with_no_acting_tenant(
    session: Session, tenant_b: Tenant
):
    """`is_acting_tenant_admin` has no DEFAULT_TENANT_ID fallback, on purpose."""
    user = _tenant_admin_of_a(session, tenant_b)

    assert tenant_context.acting_tenant_id(session) is None
    assert (
        deps.get_effective_permissions(user, session)
        == LEGACY_ROLE_PERMISSIONS[UserRole.RESIDENT]
    )


def test_a_superuser_holds_the_documented_administrator_gap(session: Session):
    """§4.1's decision, made observable: the catalogue is whole, gap included."""
    user = _superuser(session)
    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)

    assert "packages:my_lots_read" in deps.get_effective_permissions(user, session)
    assert (
        "packages:my_lots_read"
        not in LEGACY_ROLE_PERMISSIONS[UserRole.ADMINISTRATOR]
    )


# ---------------------------------------------------------------------------
# 8-11 -- the five global /api/v1/tenants writes (ER-3)
# ---------------------------------------------------------------------------

#: The whole `get_current_superuser` surface, duplicated from
#: `test_tenant_admin.py` on purpose: this module states its own boundary and
#: the original test keeps passing unmodified.
SUPERUSER_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/tenants"),
        ("PATCH", "/api/v1/tenants/{tenant_id}"),
        ("POST", "/api/v1/tenants/{tenant_id}/members"),
        ("DELETE", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
        ("PATCH", "/api/v1/tenants/{tenant_id}/members/{user_id}"),
    }
)


def _auth(user: User) -> dict[str, str]:
    """No `X-Tenant-Id`: these five routes are global and resolve no tenant."""
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _five_writes(client: TestClient, actor: User, tenant: Tenant, target: User):
    """Call each of the five writes once; yield `(label, response)`."""
    yield "create", client.post(
        "/api/v1/tenants", headers=_auth(actor), json={"name": f"C {uuid.uuid4().hex[:8]}"}
    )
    yield "update", client.patch(
        f"/api/v1/tenants/{tenant.id}",
        headers=_auth(actor),
        json={"name": f"R {uuid.uuid4().hex[:8]}"},
    )
    yield "add_member", client.post(
        f"/api/v1/tenants/{tenant.id}/members",
        headers=_auth(actor),
        json={"user_id": str(target.id)},
    )
    yield "set_admin", client.patch(
        f"/api/v1/tenants/{tenant.id}/members/{target.id}",
        headers=_auth(actor),
        json={"is_tenant_admin": True},
    )
    yield "remove_member", client.delete(
        f"/api/v1/tenants/{tenant.id}/members/{target.id}", headers=_auth(actor)
    )


def test_every_global_write_succeeds_for_a_superuser(
    client: TestClient, session: Session, tenant_b: Tenant
):
    """A DIRECTOR-role user carrying the flag passes all five."""
    actor = _superuser(session)
    target = _make_user(session, UserRole.GUEST, is_superuser=False)

    statuses = {
        label: response.status_code
        for label, response in _five_writes(client, actor, tenant_b, target)
    }

    assert statuses == {
        "create": 201,
        "update": 200,
        "add_member": 201,
        "set_admin": 200,
        "remove_member": 204,
    }


def test_every_global_write_is_403_for_an_administrator_without_the_flag(
    client: TestClient, session: Session, tenant_b: Tenant
):
    """The proof that the column, and not the enum, is what is read."""
    actor = _make_user(session, UserRole.ADMINISTRATOR, is_superuser=False)
    session.add(UserTenantLink(user_id=actor.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    target = _make_user(session, UserRole.GUEST, is_superuser=False)

    for label, response in _five_writes(client, actor, tenant_b, target):
        assert response.status_code == 403, label
        assert response.json()["detail"] == "The user doesn't have enough privileges"


def test_every_global_write_is_403_for_a_tenant_admin_of_the_target_tenant(
    client: TestClient, session: Session, tenant_b: Tenant
):
    """Parity with `test_tenant_admin.py`, restated here as this module's boundary."""
    actor = _make_user(session, UserRole.RESIDENT, is_superuser=False)
    session.add(
        UserTenantLink(user_id=actor.id, tenant_id=tenant_b.id, is_tenant_admin=True)
    )
    session.commit()
    target = _make_user(session, UserRole.GUEST, is_superuser=False)

    for label, response in _five_writes(client, actor, tenant_b, target):
        assert response.status_code == 403, label


def test_setting_the_capability_is_403_for_a_tenant_admin_and_200_for_a_superuser(
    client: TestClient, session: Session, tenant_b: Tenant
):
    """Granting *and* revoking `is_tenant_admin` is superuser-only."""
    syndic = _make_user(session, UserRole.RESIDENT, is_superuser=False)
    session.add(
        UserTenantLink(user_id=syndic.id, tenant_id=tenant_b.id, is_tenant_admin=True)
    )
    session.commit()
    root = _superuser(session)

    refused = client.patch(
        f"/api/v1/tenants/{tenant_b.id}/members/{syndic.id}",
        headers=_auth(syndic),
        json={"is_tenant_admin": False},
    )
    assert refused.status_code == 403

    revoked = client.patch(
        f"/api/v1/tenants/{tenant_b.id}/members/{syndic.id}",
        headers=_auth(root),
        json={"is_tenant_admin": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["is_tenant_admin"] is False

    granted = client.patch(
        f"/api/v1/tenants/{tenant_b.id}/members/{syndic.id}",
        headers=_auth(root),
        json={"is_tenant_admin": True},
    )
    assert granted.status_code == 200
    assert granted.json()["is_tenant_admin"] is True


# ---------------------------------------------------------------------------
# 12-16, 20 -- not grantable, and out of a tenant_admin's reach (ER-4)
# ---------------------------------------------------------------------------


def _scoped_auth(user: User, tenant_id=DEFAULT_TENANT_ID) -> dict[str, str]:
    """Headers for a tenant-scoped route."""
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(tenant_id),
    }


def _member(session: Session, role: UserRole, *, tenant_admin: bool = False) -> User:
    user = _make_user(session, role, is_superuser=False)
    session.add(
        UserTenantLink(
            user_id=user.id,
            tenant_id=DEFAULT_TENANT_ID,
            is_tenant_admin=tenant_admin,
        )
    )
    session.commit()
    return user


def test_the_superuser_flag_is_not_settable_through_patch_users(
    client: TestClient, session: Session
):
    """`UserUpdate` has no `is_superuser` field, so the body is inert."""
    author = _superuser(session)
    target = _member(session, UserRole.GUEST)

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=_scoped_auth(author),
        json={"is_superuser": True},
    )

    assert response.status_code == 200
    assert "is_superuser" not in response.json()
    session.expire_all()
    assert session.get(User, target.id).is_superuser is False


def test_a_group_carrying_a_superuser_only_permission_is_403_even_for_a_superuser(
    client: TestClient, session: Session
):
    """The point is that the group would be a lie, not that the author is untrusted."""
    for author in (_superuser(session), _member(session, UserRole.RESIDENT, tenant_admin=True)):
        response = client.post(
            "/api/v1/user-types/",
            headers=_scoped_auth(author),
            json={"name": f"Falso {uuid.uuid4().hex[:6]}", "permissions": ["tenants:create"]},
        )

        assert response.status_code == 403
        assert "tenants:create" in response.json()["detail"]

    assert not session.exec(
        select(UserType).where(UserType.name.like("Falso %"))
    ).all()


def test_patching_a_group_to_add_a_superuser_only_permission_is_403(
    client: TestClient, session: Session
):
    author = _superuser(session)
    created = client.post(
        "/api/v1/user-types/",
        headers=_scoped_auth(author),
        json={"name": "Editável su", "permissions": ["tasks:read"]},
    )
    assert created.status_code == 201
    group_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/user-types/{group_id}",
        headers=_scoped_auth(author),
        json={
            "name": "Editável su",
            "permissions": ["tasks:read", "tenants:members_set_admin"],
        },
    )

    assert response.status_code == 403
    assert "tenants:members_set_admin" in response.json()["detail"]

    listing = client.get("/api/v1/user-types/", headers=_scoped_auth(author))
    stored = next(row for row in listing.json() if row["id"] == group_id)
    assert stored["permissions"] == ["tasks:read"]


def test_a_tenant_admin_cannot_grant_the_administrator_role(
    client: TestClient, session: Session
):
    syndic = _member(session, UserRole.RESIDENT, tenant_admin=True)
    target = _member(session, UserRole.GUEST)

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=_scoped_auth(syndic),
        json={"role": "ADMINISTRATOR"},
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Tenant administrators cannot grant the ADMINISTRATOR role"
    )


def test_a_tenant_admin_cannot_modify_a_superuser_of_any_role(
    client: TestClient, session: Session
):
    """Rule 2 now protects a DIRECTOR-role superuser, which the merge base did not."""
    syndic = _member(session, UserRole.RESIDENT, tenant_admin=True)
    root = _superuser(session)

    response = client.patch(
        f"/api/v1/users/{root.id}",
        headers=_scoped_auth(syndic),
        json={"full_name": "Rebatizado"},
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Tenant administrators cannot modify an administrator"
    )


def test_promoting_and_demoting_moves_the_column_with_the_role(
    client: TestClient, session: Session
):
    """§7.3's mirror: the enum and the column never drift while both exist."""
    author = _superuser(session)
    target = _member(session, UserRole.GUEST)

    promoted = client.patch(
        f"/api/v1/users/{target.id}",
        headers=_scoped_auth(author),
        json={"role": "ADMINISTRATOR"},
    )
    assert promoted.status_code == 200
    session.expire_all()
    assert session.get(User, target.id).is_superuser is True

    demoted = client.patch(
        f"/api/v1/users/{target.id}",
        headers=_scoped_auth(author),
        json={"role": "DIRECTOR"},
    )
    assert demoted.status_code == 200
    session.expire_all()
    assert session.get(User, target.id).is_superuser is False


def test_superuser_only_permissions_are_exactly_the_four_tenant_permissions():
    """§6.1's pin: the constant cannot drift from the routes it describes."""
    from_routes = {ROUTE_PERMISSIONS[key] for key in SUPERUSER_ROUTES}
    # Five routes, four strings: POST /members and DELETE /members/{user_id}
    # share `tenants:members_manage`.
    expected = {
        "tenants:create",
        "tenants:update",
        "tenants:members_manage",
        "tenants:members_set_admin",
    }

    assert from_routes == SUPERUSER_ONLY_PERMISSIONS
    assert expected == SUPERUSER_ONLY_PERMISSIONS
    assert SUPERUSER_ONLY_PERMISSIONS <= PERMISSIONS


# ---------------------------------------------------------------------------
# 17-18 -- the widening's two deliberate consequences (§4.3, ER-7)
# ---------------------------------------------------------------------------


def _test_image_bytes() -> bytes:
    image = Image.new("RGB", (200, 200), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_a_resident_tenant_admin_is_routed_to_the_queue(
    client: TestClient, session: Session
):
    """`packages:queue_read` is tested first, so `/my-lots` refuses and
    `/queue` — a strict superset, every lot including their own — answers.

    Exactly what an ADMINISTRATOR living in the condominium already
    experiences: no information is lost, only the route changes.
    """
    syndic = _member(session, UserRole.RESIDENT, tenant_admin=True)

    refused = client.get("/api/v1/packages/my-lots", headers=_scoped_auth(syndic))
    assert refused.status_code == 403
    assert (
        refused.json()["detail"]
        == "Use /packages/queue para ver encomendas de todos os lotes."
    )

    queue = client.get("/api/v1/packages/queue", headers=_scoped_auth(syndic))
    assert queue.status_code == 200


def test_a_tenant_admin_upload_is_auto_approved(client: TestClient, session: Session):
    """They hold `uploads:auto_approve`, which is what "administrator-level in
    this tenant" means; an ADMINISTRATOR behaves the same way today."""
    syndic = _member(session, UserRole.RESIDENT, tenant_admin=True)

    response = client.post(
        "/api/v1/uploads/photo",
        headers=_scoped_auth(syndic),
        files={"file": ("su.jpg", _test_image_bytes(), "image/jpeg")},
        data={"entity_type": "VISITOR"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "APPROVED"
    assert response.json()["approved_by_id"] == str(syndic.id)
