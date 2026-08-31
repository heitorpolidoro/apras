"""Regression guard: APRAS-41 changes the schema, never the behaviour.

The tenancy slice is only safe to ship ahead of request-scoped resolution
(APRAS-42) if adding a second tenant is observationally inert. Two things
have to hold, and both are asserted here rather than left to review:

1. `get_effective_user_type_ids` is deliberately tenant-blind — it resolves a
   role's UserType with `select(UserType).where(UserType.role == role).first()`.
   That is only deterministic while there is exactly one role-linked row per
   role, which is why `POST /api/v1/tenants` does **not** seed role-linked
   `UserType` rows for a new tenant. If someone later adds that seeding here
   instead of in APRAS-42, this test fails.
2. Existing list endpoints keep returning exactly what they returned before
   a second tenant existed.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import get_effective_user_type_ids
from app.core.security import create_access_token
from app.models.category import Category
from app.models.enums import UserRole
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
from app.models.user import User
from app.models.user_type import UserType


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def admin(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="inert_admin@test.com",
        full_name="Inert Admin",
        hashed_password="hash",
        role=UserRole.ADMINISTRATOR,
        cpf="11111111111",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_creating_a_second_tenant_leaves_effective_user_types_unchanged(
    session: Session, client: TestClient, admin: User
):
    role_type = UserType(name="Diretor (papel)", allowed_menus=[], role=UserRole.DIRECTOR)
    explicit_type = UserType(name="Equipe", allowed_menus=["tasks"])
    session.add_all([role_type, explicit_type])
    session.commit()

    director = User(
        id=uuid.uuid4(),
        email="inert_director@test.com",
        full_name="Inert Director",
        hashed_password="hash",
        role=UserRole.DIRECTOR,
        cpf="22222222222",
        user_types=[explicit_type],
    )
    session.add(director)
    session.commit()

    before = get_effective_user_type_ids(director, session)

    response = client.post(
        "/api/v1/tenants", json={"name": "Segundo Condomínio"}, headers=_headers(admin)
    )
    assert response.status_code == 201

    after = get_effective_user_type_ids(director, session)

    assert after == before
    assert after == {role_type.id, explicit_type.id}


def test_creating_a_second_tenant_seeds_no_user_types(
    session: Session, client: TestClient, admin: User
):
    """Per-tenant role-type seeding is APRAS-42's job, not this slice's."""
    session.add(UserType(name="Gerente (papel)", allowed_menus=[], role=UserRole.MANAGER))
    session.commit()
    before = len(session.query(UserType).all())

    client.post(
        "/api/v1/tenants", json={"name": "Terceiro Condomínio"}, headers=_headers(admin)
    )

    assert len(session.query(UserType).all()) == before


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
