"""The user directory becomes tenant-scoped (APRAS-43 §6).

`GET /api/v1/users/`, `PATCH /api/v1/users/{id}` and
`PATCH /api/v1/users/{id}/contact-info` target the users *visible in the
acting tenant* — for every role, `ADMINISTRATOR` included. The escalation
guards of §6.3 are the complement: they fire only for a caller that is not a
global `ADMINISTRATOR`.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import create_access_token, get_password_hash
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.services.user_service import UserService
from tests.conftest import make_user

TENANT_A = DEFAULT_TENANT_ID


def _auth(user: User, tenant_id=None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


_CPF_COUNTER = iter(range(20_000, 99_999))


def _make_user(
    session: Session,
    email: str,
    role: str = "RESIDENT",
    tenants: tuple = (),
    is_tenant_admin_in=None,
) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=email,
        full_name=email.split("@", maxsplit=1)[0],
        hashed_password=get_password_hash("password"),
        profile=role,
        cpf=f"8{next(_CPF_COUNTER):010d}"[:11],
    )
    session.add(user)
    session.commit()
    for tenant_id in tenants:
        session.add(
            UserTenantLink(
                user_id=user.id,
                tenant_id=tenant_id,
                is_tenant_admin=tenant_id == is_tenant_admin_in,
            )
        )
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="directory_admin")
def directory_admin_fixture(session: Session):
    """An ADMINISTRATOR whose only membership is tenant A."""
    return _make_user(
        session, "dir-admin@test.com", "ADMINISTRATOR", (TENANT_A,)
    )


@pytest.fixture(name="syndic")
def syndic_fixture(session: Session):
    """A RESIDENT holding the capability on tenant A."""
    return _make_user(
        session,
        "dir-syndic@test.com",
        "RESIDENT",
        (TENANT_A,),
        is_tenant_admin_in=TENANT_A,
    )


@pytest.fixture(name="a_user")
def a_user_fixture(session: Session):
    return _make_user(session, "dir-a-only@test.com", tenants=(TENANT_A,))


@pytest.fixture(name="b_user")
def b_user_fixture(session: Session, tenant_b: Tenant):
    return _make_user(session, "dir-b-only@test.com", tenants=(tenant_b.id,))


@pytest.fixture(name="orphan_user")
def orphan_user_fixture(session: Session):
    """A user with no membership at all — visible in the default tenant."""
    return _make_user(session, "dir-orphan@test.com")


@pytest.fixture(name="dual_user")
def dual_user_fixture(session: Session, tenant_b: Tenant):
    return _make_user(session, "dir-dual@test.com", tenants=(TENANT_A, tenant_b.id))


@pytest.fixture(name="second_admin")
def second_admin_fixture(session: Session):
    return _make_user(
        session, "dir-second-admin@test.com", "ADMINISTRATOR", (TENANT_A,)
    )


def _emails(payload) -> set[str]:
    return {row["email"] for row in payload}


# ---------------------------------------------------------------------------
# §6.2 — the visibility rule on the listing
# ---------------------------------------------------------------------------


def test_listing_is_scoped_to_the_acting_tenant_for_a_tenant_admin(
    tenant_client: TestClient,
    syndic: User,
    a_user: User,
    b_user: User,
    orphan_user: User,
):
    response = tenant_client.get("/api/v1/users/", headers=_auth(syndic, TENANT_A))
    assert response.status_code == 200
    emails = _emails(response.json())
    assert a_user.email in emails
    assert orphan_user.email in emails
    assert b_user.email not in emails


def test_listing_applies_the_same_filter_to_an_administrator(
    tenant_client: TestClient, directory_admin: User, b_user: User, a_user: User
):
    """The filter is uniform: an ADMINISTRATOR is not exempt."""
    response = tenant_client.get("/api/v1/users/", headers=_auth(directory_admin))
    assert response.status_code == 200
    assert b_user.email not in _emails(response.json())
    assert a_user.email in _emails(response.json())


def test_administrator_reaches_tenant_b_by_sending_the_header(
    tenant_client: TestClient, directory_admin: User, b_user: User, tenant_b: Tenant
):
    response = tenant_client.get(
        "/api/v1/users/", headers=_auth(directory_admin, tenant_b.id)
    )
    assert response.status_code == 200
    emails = _emails(response.json())
    assert b_user.email in emails
    assert directory_admin.email not in emails


def test_listing_still_composes_with_the_is_active_filter(
    tenant_client: TestClient, directory_admin: User, session: Session
):
    inactive = _make_user(session, "dir-inactive@test.com", tenants=(TENANT_A,))
    inactive.is_active = False
    session.add(inactive)
    session.commit()

    active_only = tenant_client.get(
        "/api/v1/users/?is_active=true", headers=_auth(directory_admin)
    )
    assert active_only.status_code == 200
    assert inactive.email not in _emails(active_only.json())

    inactive_only = tenant_client.get(
        "/api/v1/users/?is_active=false", headers=_auth(directory_admin)
    )
    assert _emails(inactive_only.json()) == {inactive.email}


# ---------------------------------------------------------------------------
# §6.2 — the by-id visibility 404, ADMINISTRATOR included
# ---------------------------------------------------------------------------


def test_administrator_gets_404_for_a_foreign_user_and_200_with_the_header(
    tenant_client: TestClient, directory_admin: User, b_user: User, tenant_b: Tenant
):
    in_a = tenant_client.patch(
        f"/api/v1/users/{b_user.id}",
        headers=_auth(directory_admin, TENANT_A),
        json={"full_name": "Nope"},
    )
    assert in_a.status_code == 404

    in_a_contact = tenant_client.patch(
        f"/api/v1/users/{b_user.id}/contact-info",
        headers=_auth(directory_admin, TENANT_A),
        json={"phone": "11999999999"},
    )
    assert in_a_contact.status_code == 404

    in_b = tenant_client.patch(
        f"/api/v1/users/{b_user.id}",
        headers=_auth(directory_admin, tenant_b.id),
        json={"full_name": "Renamed in B"},
    )
    assert in_b.status_code == 200
    assert in_b.json()["full_name"] == "Renamed in B"

    in_b_contact = tenant_client.patch(
        f"/api/v1/users/{b_user.id}/contact-info",
        headers=_auth(directory_admin, tenant_b.id),
        json={"phone": "11999999999"},
    )
    assert in_b_contact.status_code == 200
    assert in_b_contact.json()["phone"] == "11999999999"


def test_tenant_admin_gets_404_for_a_foreign_user(
    tenant_client: TestClient, syndic: User, b_user: User
):
    response = tenant_client.patch(
        f"/api/v1/users/{b_user.id}",
        headers=_auth(syndic, TENANT_A),
        json={"full_name": "Nope"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# §6.3 — the escalation guards, only for a non-ADMINISTRATOR caller
# ---------------------------------------------------------------------------


def test_a_tenant_admin_cannot_mint_a_superuser_through_this_route(
    tenant_client: TestClient, syndic: User, a_user: User
):
    """The rule that replaced rule 1 (IAM F5, APRAS-49 §3.3 #2, §8.3).

    F3 answered 403 to `{"role": "ADMINISTRATOR"}`. With the enum gone
    `UserUpdate` carries neither `role` nor `is_superuser`, so those keys are
    not fields at all: the request is accepted and writes nothing. The flag's
    only API surface is the superuser-only route of §8.4.
    """
    response = tenant_client.patch(
        f"/api/v1/users/{a_user.id}",
        headers=_auth(syndic, TENANT_A),
        json={"role": "ADMINISTRATOR", "is_superuser": True},
    )
    assert response.status_code == 200
    assert "is_superuser" not in response.json()
    assert "role" not in response.json()


def test_tenant_admin_cannot_modify_an_administrator(
    tenant_client: TestClient, syndic: User, second_admin: User
):
    response = tenant_client.patch(
        f"/api/v1/users/{second_admin.id}",
        headers=_auth(syndic, TENANT_A),
        json={"full_name": "Nope"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "Tenant administrators cannot modify an administrator"
    )


def test_tenant_admin_cannot_modify_a_multi_tenant_user(
    tenant_client: TestClient, syndic: User, dual_user: User
):
    response = tenant_client.patch(
        f"/api/v1/users/{dual_user.id}",
        headers=_auth(syndic, TENANT_A),
        json={"full_name": "Nope"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "This user belongs to another tenant"


def test_the_escalation_rules_never_fire_for_a_global_administrator(
    tenant_client: TestClient,
    directory_admin: User,
    a_user: User,
    second_admin: User,
    dual_user: User,
):
    headers = _auth(directory_admin, TENANT_A)

    grant = tenant_client.patch(
        f"/api/v1/users/{a_user.id}",
        headers=headers,
        json={"full_name": "Renamed By Superuser"},
    )
    assert grant.status_code == 200
    assert grant.json()["full_name"] == "Renamed By Superuser"

    touch_admin = tenant_client.patch(
        f"/api/v1/users/{second_admin.id}",
        headers=headers,
        json={"full_name": "Renamed Admin"},
    )
    assert touch_admin.status_code == 200

    touch_dual = tenant_client.patch(
        f"/api/v1/users/{dual_user.id}",
        headers=headers,
        json={"full_name": "Renamed Dual"},
    )
    assert touch_dual.status_code == 200


def test_contact_info_gains_no_escalation_rule(
    tenant_client: TestClient, syndic: User, dual_user: User
):
    """Its schema exposes no role/is_active/role_ids, so only rule 0
    applies — a target visible in the acting tenant is editable."""
    response = tenant_client.patch(
        f"/api/v1/users/{dual_user.id}/contact-info",
        headers=_auth(syndic, TENANT_A),
        json={"phone": "11777777777"},
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "11777777777"


# ---------------------------------------------------------------------------
# §7 — foreign role_ids are a 422, and foreign links are preserved
# ---------------------------------------------------------------------------


@pytest.fixture(name="typed_target")
def typed_target_fixture(session: Session, tenant_b: Tenant):
    """A user carrying one Role in A and one in B."""
    a_type = Role(name="Tipo A",)
    b_type = Role(name="Tipo B",tenant_id=tenant_b.id)
    session.add_all([a_type, b_type])
    session.commit()
    session.refresh(a_type)
    session.refresh(b_type)

    user = _make_user(session, "dir-typed@test.com", tenants=(TENANT_A,))
    user.roles = [a_type, b_type]
    session.add(user)
    session.commit()
    return {"user": user, "a_type": a_type, "b_type": b_type}


def test_unknown_role_id_is_422(
    tenant_client: TestClient, directory_admin: User, typed_target: dict
):
    response = tenant_client.patch(
        f"/api/v1/users/{typed_target['user'].id}",
        headers=_auth(directory_admin, TENANT_A),
        json={"role_ids": [str(uuid.uuid4())]},
    )
    assert response.status_code == 422
    assert "Unknown role_ids" in str(response.json()["detail"])


def test_a_role_of_another_tenant_is_422(
    tenant_client: TestClient, directory_admin: User, typed_target: dict
):
    response = tenant_client.patch(
        f"/api/v1/users/{typed_target['user'].id}",
        headers=_auth(directory_admin, TENANT_A),
        json={"role_ids": [str(typed_target["b_type"].id)]},
    )
    assert response.status_code == 422


def test_valid_ids_return_200_and_preserve_the_foreign_link(
    tenant_client: TestClient,
    directory_admin: User,
    typed_target: dict,
    session: Session,
    raw_session: Session,
):
    new_type = Role(name="Tipo A2",)
    session.add(new_type)
    session.commit()
    session.refresh(new_type)

    response = tenant_client.patch(
        f"/api/v1/users/{typed_target['user'].id}",
        headers=_auth(directory_admin, TENANT_A),
        json={"role_ids": [str(new_type.id)]},
    )
    assert response.status_code == 200
    # The response body only shows the acting tenant's types.
    assert [ut["id"] for ut in response.json()["roles"]] == [str(new_type.id)]

    raw_session.expire_all()
    stored = raw_session.get(User, typed_target["user"].id)
    assert {ut.id for ut in stored.roles} == {
        new_type.id,
        typed_target["b_type"].id,
    }


def test_clearing_roles_keeps_the_foreign_link(
    tenant_client: TestClient,
    directory_admin: User,
    typed_target: dict,
    raw_session: Session,
):
    response = tenant_client.patch(
        f"/api/v1/users/{typed_target['user'].id}",
        headers=_auth(directory_admin, TENANT_A),
        json={"role_ids": []},
    )
    assert response.status_code == 200
    assert response.json()["roles"] == []

    raw_session.expire_all()
    stored = raw_session.get(User, typed_target["user"].id)
    assert {ut.id for ut in stored.roles} == {typed_target["b_type"].id}


# ---------------------------------------------------------------------------
# §6.2 — every response body's `roles` is acting-tenant only
# ---------------------------------------------------------------------------


def test_every_user_route_filters_roles_in_the_response(
    tenant_client: TestClient, directory_admin: User, typed_target: dict
):
    headers = _auth(directory_admin, TENANT_A)
    target_id = str(typed_target["user"].id)
    a_type_id = str(typed_target["a_type"].id)
    b_type_id = str(typed_target["b_type"].id)

    listing = tenant_client.get("/api/v1/users/", headers=headers)
    assert listing.status_code == 200
    row = next(row for row in listing.json() if row["id"] == target_id)
    assert [ut["id"] for ut in row["roles"]] == [a_type_id]

    patched = tenant_client.patch(
        f"/api/v1/users/{target_id}", headers=headers, json={"full_name": "Typed"}
    )
    assert [ut["id"] for ut in patched.json()["roles"]] == [a_type_id]

    contact = tenant_client.patch(
        f"/api/v1/users/{target_id}/contact-info",
        headers=headers,
        json={"phone": "11666666666"},
    )
    assert [ut["id"] for ut in contact.json()["roles"]] == [a_type_id]
    assert b_type_id not in {ut["id"] for ut in contact.json()["roles"]}


# ---------------------------------------------------------------------------
# The service helpers, in isolation
# ---------------------------------------------------------------------------


def test_visible_users_statement_partitions_the_directory(
    session: Session, tenant_b: Tenant, a_user: User, b_user: User, orphan_user: User
):
    in_a = session.exec(UserService.visible_users_statement(TENANT_A)).all()
    in_b = session.exec(UserService.visible_users_statement(tenant_b.id)).all()

    assert {u.email for u in in_a} == {a_user.email, orphan_user.email}
    assert {u.email for u in in_b} == {b_user.email}


def test_membership_tenant_ids_returns_every_membership(
    session: Session, tenant_b: Tenant, dual_user: User
):
    assert UserService.membership_tenant_ids(session, dual_user.id) == {
        TENANT_A,
        tenant_b.id,
    }


def test_get_visible_user_returns_none_outside_the_tenant(
    session: Session, tenant_b: Tenant, b_user: User
):
    assert UserService.get_visible_user(session, b_user.id, TENANT_A) is None
    assert UserService.get_visible_user(session, b_user.id, tenant_b.id) is not None


def test_orphan_users_are_invisible_outside_the_default_tenant(
    session: Session, tenant_b: Tenant, orphan_user: User
):
    assert UserService.get_visible_user(session, orphan_user.id, tenant_b.id) is None
    assert (
        UserService.get_visible_user(session, orphan_user.id, TENANT_A) is not None
    )


def test_no_role_link_survives_a_missing_target(session: Session):
    """Sanity: the statement is a plain SELECT with no join fan-out."""
    rows = session.exec(select(User)).all()
    visible = session.exec(UserService.visible_users_statement(TENANT_A)).all()
    assert len(visible) <= len(rows)
