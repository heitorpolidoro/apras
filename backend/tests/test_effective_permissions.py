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
from app.core.permissions import PERMISSIONS
from app.core.security import create_access_token
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.services.tenant_service import TenantService
from tests.conftest import PROFILE_ROLE_NAMES, bundle, make_user
from tests.matrix_world import PARITY_PROFILES

_cpf_counter = itertools.count(1)


def _next_cpf() -> str:
    """A unique 11-digit CPF-shaped string (the column is unique, not validated)."""
    return str(next(_cpf_counter)).zfill(11)


def _make_user(session: Session, role: str, **kwargs) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@perm.test",
        full_name=f"{role} user",
        hashed_password="hash",
        profile=role,
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


@pytest.mark.parametrize("role", PARITY_PROFILES)
def test_a_user_whose_only_role_is_a_profile_gets_exactly_that_bundle(
    session: Session, role
):
    """The profile row is the whole answer -- there is no fallback left.

    IAM F5 (APRAS-49 §3.2) deleted the `LEGACY_ROLE_PERMISSIONS` seed, so a
    user's set now comes from their role rows and nothing else. That the
    answer is still *exactly* the legacy set is the point: the recorded
    bundle went onto the row, so the number did not move.

    `is_superuser=False` is explicit because `conftest.make_user` defaults it
    to True for the ADMINISTRATOR profile (mirroring the `User.__init__`
    default F3 shipped), and a superuser short-circuits straight to
    `PERMISSIONS` (§4) -- the subject of `test_superuser.py`, not of the
    bundle path this case is about.
    """
    user = _make_user(session, role, is_superuser=False)

    assert deps.get_effective_permissions(user, session) == bundle(role)


def test_role_bundle_permissions_are_added_to_the_legacy_set(session: Session):
    user = _make_user(session, "RESIDENT")
    role = Role(
        name="Comissão de Obras", permissions=["assets:create", "votes:close"]
    )
    session.add(role)
    session.commit()
    user.roles.append(role)
    session.add(user)
    session.commit()

    result = deps.get_effective_permissions(user, session)

    assert {"assets:create", "votes:close"} <= result
    assert bundle("RESIDENT") <= result


def test_a_permission_already_in_the_legacy_set_appears_once(session: Session):
    """It is a set union, not a list concatenation."""
    user = _make_user(session, "RESIDENT")
    legacy = bundle("RESIDENT")
    duplicated = min(legacy)
    role = Role(name="Duplicada", permissions=[duplicated])
    session.add(role)
    session.commit()
    user.roles.append(role)
    session.add(user)
    session.commit()

    result = deps.get_effective_permissions(user, session)

    assert result == legacy
    assert isinstance(result, frozenset)


def test_a_role_of_another_tenant_contributes_nothing(
    session: Session, tenant_b: Tenant
):
    """The APRAS-43 §5.2 relationship-load trap, for permissions."""
    user = _make_user(session, "GUEST")
    foreign_type = Role(
        name="Financeiro B",
        tenant_id=tenant_b.id,
        permissions=["finance:transaction_delete"],
    )
    session.add(foreign_type)
    session.commit()
    user.roles.append(foreign_type)
    session.add(user)
    session.commit()

    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)
    result = deps.get_effective_permissions(user, session)

    assert "finance:transaction_delete" not in result
    assert result == bundle("GUEST")


def test_unknown_stored_strings_survive(session: Session):
    """A hand-edited row must stay visible: F2's UI has to be able to show it."""
    user = _make_user(session, "PORTEIRO")
    role = Role(name="Estranha", permissions=["not_a:permission"])
    session.add(role)
    session.commit()
    user.roles.append(role)
    session.add(user)
    session.commit()

    assert "not_a:permission" in deps.get_effective_permissions(user, session)


def test_only_a_real_membership_contributes(session: Session):
    """The APRAS-9 implicit membership is gone; a row alone grants nothing.

    Before migration `0033` a `Role` row whose `role` column matched the
    user's enum contributed its bundle with **no** link. It is now an
    ordinary role like any other: the same row grants nothing until the user
    is actually a member of it.
    """
    user = _make_user(session, "MANAGER")
    role_type = Role(name="Gerente", permissions=["lots:delete"])
    session.add(role_type)
    session.commit()

    assert "lots:delete" not in deps.get_effective_permissions(user, session)

    user.roles.append(role_type)
    session.add(user)
    session.commit()

    assert "lots:delete" in deps.get_effective_permissions(user, session)


def test_a_session_with_no_acting_tenant_resolves_to_the_default_tenant(
    session: Session, tenant_b: Tenant
):
    """Same fallback ladder as `get_effective_role_ids` (unit/seed path)."""
    user = _make_user(session, "DIRECTOR")
    # Two permissions DIRECTOR does not hold legacy-wise, so the assertions
    # read the tenant resolution and nothing else.
    default_type = Role(name="Padrão", permissions=["lots:delete"])
    foreign_type = Role(
        name="Outra", tenant_id=tenant_b.id, permissions=["packages:my_lots_read"]
    )
    session.add(default_type)
    session.add(foreign_type)
    session.commit()
    user.roles.extend([default_type, foreign_type])
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
    admin = _make_user(session, "ADMINISTRATOR")

    response = client.post(
        "/api/v1/tenants",
        json={"name": "Condomínio Sem Permissões"},
        headers=_headers(admin),
    )
    assert response.status_code == 201
    tenant_id = uuid.UUID(response.json()["id"])

    rows = session.exec(
        select(Role).where(Role.tenant_id == tenant_id)
    ).all()

    # APRAS-42 §7.2 still requires the six role-linked rows for the menu gate.
    assert {row.name for row in rows} == set(PROFILE_ROLE_NAMES.values())
    assert all(row.permissions == [] for row in rows)


def test_seed_creates_no_permissions(session: Session, tenant_b: Tenant):
    TenantService.ensure_legacy_roles(session, tenant_b.id)

    rows = session.exec(
        select(Role).where(Role.tenant_id == tenant_b.id)
    ).all()

    assert rows
    assert all(row.permissions == [] for row in rows)


def test_the_column_defaults_to_an_empty_list(session: Session):
    role = Role(name="Sem bundle")
    session.add(role)
    session.commit()
    session.refresh(role)

    assert role.permissions == []


# ---------------------------------------------------------------------------
# The `is_tenant_admin` capability (IAM F3, APRAS-47 §4.2)
# ---------------------------------------------------------------------------


def test_the_capability_resolves_to_the_whole_catalogue_in_the_granting_tenant(
    session: Session,
):
    """The capability means what its name says: every permission, here."""
    user = _make_user(session, "RESIDENT")
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=True
        )
    )
    session.commit()
    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)

    result = deps.get_effective_permissions(user, session)

    assert result == PERMISSIONS
    assert bundle("RESIDENT") <= result


def test_the_bridge_grants_nothing_without_an_acting_tenant(session: Session):
    """`is_acting_tenant_admin` has no DEFAULT_TENANT_ID fallback, on purpose."""
    user = _make_user(session, "RESIDENT")
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=True
        )
    )
    session.commit()

    result = deps.get_effective_permissions(user, session)

    assert result == bundle("RESIDENT")


def test_the_bridge_grants_nothing_in_a_tenant_that_did_not_grant_it(
    session: Session, tenant_b: Tenant
):
    user = _make_user(session, "RESIDENT")
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=tenant_b.id, is_tenant_admin=True
        )
    )
    session.add(
        UserTenantLink(
            user_id=user.id, tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=False
        )
    )
    session.commit()
    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)

    result = deps.get_effective_permissions(user, session)

    assert result == bundle("RESIDENT")
