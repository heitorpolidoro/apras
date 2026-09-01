"""`deps.get_effective_permissions` and the "nothing is seeded" rule (APRAS-45).

Two subjects, one file, because they are two halves of the same claim: the
resolver is meaningful *only* because no role carries any permission yet, and
the legacy fallback is what keeps F1..F4 from resolving to the empty set.

`get_effective_permissions` has zero production call sites in this slice, by
design (§11.6). Enforcement is F4.
"""

import itertools
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api import deps
from app.core import tenant_context
from app.core.permissions import LEGACY_ROLE_PERMISSIONS
from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
from app.models.user import User
from app.models.user_type import UserType
from app.services.tenant_service import TenantService

_cpf_counter = itertools.count(1)


def _next_cpf() -> str:
    """A unique 11-digit CPF-shaped string (the column is unique, not validated)."""
    return str(next(_cpf_counter)).zfill(11)


def _make_user(session: Session, role: UserRole, **kwargs) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@perm.test",
        full_name=f"{role.value} user",
        hashed_password="hash",
        role=role,
        cpf=_next_cpf(),
        **kwargs,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


# ---------------------------------------------------------------------------
# §8 -- the resolver
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", list(UserRole))
def test_a_user_with_no_roles_gets_exactly_the_legacy_set(session: Session, role):
    """The transitional fallback is the whole answer while nothing is seeded."""
    user = _make_user(session, role)

    assert deps.get_effective_permissions(user, session) == LEGACY_ROLE_PERMISSIONS[
        role
    ]


def test_role_bundle_permissions_are_added_to_the_legacy_set(session: Session):
    user = _make_user(session, UserRole.RESIDENT)
    user_type = UserType(
        name="Comissão de Obras", permissions=["assets:create", "votes:close"]
    )
    session.add(user_type)
    session.commit()
    user.user_types.append(user_type)
    session.add(user)
    session.commit()

    result = deps.get_effective_permissions(user, session)

    assert {"assets:create", "votes:close"} <= result
    assert LEGACY_ROLE_PERMISSIONS[UserRole.RESIDENT] <= result


def test_a_permission_already_in_the_legacy_set_appears_once(session: Session):
    """It is a set union, not a list concatenation."""
    user = _make_user(session, UserRole.RESIDENT)
    legacy = LEGACY_ROLE_PERMISSIONS[UserRole.RESIDENT]
    duplicated = min(legacy)
    user_type = UserType(name="Duplicada", permissions=[duplicated])
    session.add(user_type)
    session.commit()
    user.user_types.append(user_type)
    session.add(user)
    session.commit()

    result = deps.get_effective_permissions(user, session)

    assert result == legacy
    assert isinstance(result, frozenset)


def test_a_role_of_another_tenant_contributes_nothing(
    session: Session, tenant_b: Tenant
):
    """The APRAS-43 §5.2 relationship-load trap, for permissions."""
    user = _make_user(session, UserRole.GUEST)
    foreign_type = UserType(
        name="Financeiro B",
        tenant_id=tenant_b.id,
        permissions=["finance:transaction_delete"],
    )
    session.add(foreign_type)
    session.commit()
    user.user_types.append(foreign_type)
    session.add(user)
    session.commit()

    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)
    result = deps.get_effective_permissions(user, session)

    assert "finance:transaction_delete" not in result
    assert result == LEGACY_ROLE_PERMISSIONS[UserRole.GUEST]


def test_unknown_stored_strings_survive(session: Session):
    """A hand-edited row must stay visible: F2's UI has to be able to show it."""
    user = _make_user(session, UserRole.PORTEIRO)
    user_type = UserType(name="Estranha", permissions=["not_a:permission"])
    session.add(user_type)
    session.commit()
    user.user_types.append(user_type)
    session.add(user)
    session.commit()

    assert "not_a:permission" in deps.get_effective_permissions(user, session)


def test_the_role_linked_user_type_contributes_its_permissions(session: Session):
    """The implicit APRAS-9 role-linked row counts, with no explicit link."""
    user = _make_user(session, UserRole.MANAGER)
    role_type = UserType(name="Gerente", role=UserRole.MANAGER, permissions=["lots:delete"])
    session.add(role_type)
    session.commit()

    assert "lots:delete" in deps.get_effective_permissions(user, session)


def test_a_session_with_no_acting_tenant_resolves_to_the_default_tenant(
    session: Session, tenant_b: Tenant
):
    """Same fallback ladder as `get_effective_user_type_ids` (unit/seed path)."""
    user = _make_user(session, UserRole.DIRECTOR)
    # Two permissions DIRECTOR does not hold legacy-wise, so the assertions
    # read the tenant resolution and nothing else.
    default_type = UserType(name="Padrão", permissions=["lots:delete"])
    foreign_type = UserType(
        name="Outra", tenant_id=tenant_b.id, permissions=["packages:my_lots_read"]
    )
    session.add(default_type)
    session.add(foreign_type)
    session.commit()
    user.user_types.extend([default_type, foreign_type])
    session.add(user)
    session.commit()

    assert tenant_context.acting_tenant_id(session) is None
    result = deps.get_effective_permissions(user, session)

    assert "lots:delete" in result
    assert "packages:my_lots_read" not in result


# ---------------------------------------------------------------------------
# §7.4 -- nothing is seeded
# ---------------------------------------------------------------------------


def test_a_fresh_tenant_has_no_role_with_permissions(
    client: TestClient, session: Session
):
    """"A fresh tenant's role list comes back empty" == empty of permissions."""
    admin = _make_user(session, UserRole.ADMINISTRATOR)

    response = client.post(
        "/api/v1/tenants",
        json={"name": "Condomínio Sem Permissões"},
        headers=_headers(admin),
    )
    assert response.status_code == 201
    tenant_id = uuid.UUID(response.json()["id"])

    rows = session.exec(
        select(UserType).where(UserType.tenant_id == tenant_id)
    ).all()

    # APRAS-42 §7.2 still requires the six role-linked rows for the menu gate.
    assert {row.role for row in rows} == set(UserRole)
    assert all(row.permissions == [] for row in rows)


def test_seed_creates_no_permissions(session: Session, tenant_b: Tenant):
    TenantService.ensure_role_types(session, tenant_b.id)

    rows = session.exec(
        select(UserType).where(UserType.tenant_id == tenant_b.id)
    ).all()

    assert rows
    assert all(row.permissions == [] for row in rows)


def test_the_column_defaults_to_an_empty_list(session: Session):
    user_type = UserType(name="Sem bundle")
    session.add(user_type)
    session.commit()
    session.refresh(user_type)

    assert user_type.permissions == []
