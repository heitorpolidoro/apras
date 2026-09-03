"""Regression guard: APRAS-41 changes the schema, never the behaviour.

The tenancy slice is only safe to ship ahead of request-scoped resolution
(APRAS-42) if adding a second tenant is observationally inert. Two things
have to hold, and both are asserted here rather than left to review:

1. `get_effective_role_ids` resolves a role's Role deterministically.
   APRAS-41 achieved that by being tenant-blind and by refusing to seed
   role-linked `Role` rows for a new tenant. **APRAS-42 is the slice that
   flips both halves**, exactly as this module's tripwire anticipated: the
   lookup is now filtered by the session's acting tenant (falling back to the
   default tenant), and `POST /api/v1/tenants` seeds one role-linked row per
   `UserRole` into the new tenant. The direct-call assertions below are
   unchanged and still pass, because a plain `Session` resolves the default
   tenant's row.
2. Existing list endpoints keep returning exactly what they returned before
   a second tenant existed.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import get_effective_role_ids
from app.core.security import create_access_token
from app.models.category import Category
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
from app.models.user import User
from app.services.tenant_service import LEGACY_ROLE_NAMES
from tests.conftest import make_user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def admin(session: Session) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="inert_admin@test.com",
        full_name="Inert Admin",
        hashed_password="hash",
        profile="ADMINISTRATOR",
        cpf="11111111111",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_creating_a_second_tenant_leaves_effective_roles_unchanged(
    session: Session, client: TestClient, admin: User
):
    explicit_type = Role(name="Equipe")
    session.add(explicit_type)
    session.commit()

    director = make_user(
        session,
        id=uuid.uuid4(),
        email="inert_director@test.com",
        full_name="Inert Director",
        hashed_password="hash",
        profile="DIRECTOR",
        cpf="22222222222",
        roles=[explicit_type],
    )
    session.add(director)
    session.commit()

    role_type = next(
        role for role in director.roles if role.name == "Diretor (papel)"
    )
    before = get_effective_role_ids(director, session)

    response = client.post(
        "/api/v1/tenants", json={"name": "Segundo Condomínio"}, headers=_headers(admin)
    )
    assert response.status_code == 201

    after = get_effective_role_ids(director, session)

    assert after == before
    assert after == {role_type.id, explicit_type.id}


def test_creating_a_second_tenant_seeds_its_own_role_types(
    session: Session, client: TestClient, admin: User
):
    """APRAS-42 §7.2: a new tenant gets the six historically-named rows.

    This inverts the APRAS-41 tripwire above by design — that assertion
    existed to catch seeding landing *before* tenant-aware resolution, and
    tenant-aware resolution is this slice. The rows all belong to the new
    tenant, so the default tenant's set is untouched and the direct-call
    assertions above still resolve exactly one row.
    """
    session.add(Role(name="Gerente (papel)"))
    session.commit()
    before_default_tenant = len(
        session.query(Role).filter(Role.tenant_id == DEFAULT_TENANT_ID).all()
    )

    response = client.post(
        "/api/v1/tenants", json={"name": "Terceiro Condomínio"}, headers=_headers(admin)
    )
    assert response.status_code == 201
    new_tenant_id = uuid.UUID(response.json()["id"])

    session.expire_all()
    seeded = session.query(Role).filter(Role.tenant_id == new_tenant_id).all()
    assert {ut.name for ut in seeded} == set(LEGACY_ROLE_NAMES)
    assert (
        len(session.query(Role).filter(Role.tenant_id == DEFAULT_TENANT_ID).all())
        == before_default_tenant
    )


def test_existing_list_endpoints_are_unchanged_by_a_second_tenant(
    client: TestClient, admin: User
):
    """`GET /tasks/` and `GET /categories/` return the same payload before
    and after another tenant exists."""
    client.post(
        "/api/v1/categories/",
        json={"name": "Manutenção", "color": "#123456"},
        headers=_headers(admin),
    )
    client.post(
        "/api/v1/tasks/",
        json={"title": "Trocar lâmpada", "status": "PENDING", "priority": "MEDIUM"},
        headers=_headers(admin),
    )

    categories_before = client.get("/api/v1/categories/", headers=_headers(admin)).json()
    tasks_before = client.get("/api/v1/tasks/", headers=_headers(admin)).json()

    client.post(
        "/api/v1/tenants", json={"name": "Quarto Condomínio"}, headers=_headers(admin)
    )

    assert client.get("/api/v1/categories/", headers=_headers(admin)).json() == categories_before
    assert client.get("/api/v1/tasks/", headers=_headers(admin)).json() == tasks_before
    assert len(categories_before) == 1
    assert len(tasks_before) == 1


def test_a_second_tenant_does_not_leak_into_scoped_defaults(
    session: Session, client: TestClient, admin: User
):
    """New rows still land in the default tenant until APRAS-42 resolves an
    acting tenant per request."""
    session.add(Tenant(name="Quinto Condomínio"))
    session.commit()

    client.post(
        "/api/v1/categories/",
        json={"name": "Jardinagem", "color": "#abcdef"},
        headers=_headers(admin),
    )

    created = session.query(Category).filter(Category.name == "Jardinagem").one()
    assert created.tenant_id == DEFAULT_TENANT_ID
