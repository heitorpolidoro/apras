"""The grant surface reads the **unstripped** set (APRAS-39 §5.5).

Named for the bug it exists to catch. `assert_can_grant` validates the
*whole resulting bundle*, not the delta, and it is called with the role
editor's full resend (APRAS-48 ER-4) and with the union of the assigned
roles' bundles. Four of the six seeded roles carry `finance:read`
(ADMINISTRATOR, DIRECTOR, MANAGER, RESIDENT), so a stripped comparison would
403 a pure *rename* of any of them in a tenant with `finance` off — i.e. role
and membership administration in that tenant would freeze, contradicting
"safe, reversible in one click".

The invariant the design is checked against: **a grant can never exceed what
the author holds with every module on, which is exactly what the author will
hold if the operator re-enables the module.** So the escalation pins of IAM
F2 still hold with the module off, and they are restated here.
"""

import ast
import itertools
import pathlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api import deps
from app.core.security import create_access_token
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from tests.conftest import PROFILE_ROLE_NAMES, make_user, profile_role

TENANT_A = DEFAULT_TENANT_ID
APP_DIR = pathlib.Path(deps.__file__).resolve().parent.parent

_cpf_counter = itertools.count(1)


def _next_cpf() -> str:
    return str(next(_cpf_counter)).zfill(11)


def _make_user(session: Session, profile: str, **kwargs) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:12]}@grants.example.com",
        full_name=f"{profile} user",
        hashed_password="hash",
        profile=profile,
        cpf=_next_cpf(),
        **kwargs,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _auth(user: User, tenant_id=TENANT_A) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
        "X-Tenant-Id": str(tenant_id),
    }


def _disable(session: Session, *modules: str) -> None:
    tenant = session.get(Tenant, TENANT_A)
    tenant.disabled_modules = list(modules)
    session.add(tenant)
    session.commit()


@pytest.fixture(name="tenant_admin")
def tenant_admin_fixture(session: Session) -> User:
    """A tenant_admin of A: the whole catalogue, bounded by A's modules."""
    user = _make_user(session, "RESIDENT", is_superuser=False)
    session.add(
        UserTenantLink(user_id=user.id, tenant_id=TENANT_A, is_tenant_admin=True)
    )
    session.commit()
    return user


def _role_author(session: Session) -> User:
    """An author who administers roles but is **not** a finance manager.

    Built from an explicit bundle rather than a seeded profile: only
    ADMINISTRATOR carries `roles:create`/`users:update` among the six, and it
    also carries `finance:category_create`, so no seeded profile can express
    "may edit roles, does not hold the escalated string" on its own.
    """
    role = Role(
        name=f"Secretaria {uuid.uuid4().hex[:6]}",
        permissions=[
            "roles:create",
            "roles:read",
            "roles:update",
            "users:read",
            "users:update",
            "finance:read",
        ],
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    author = _make_user(session, "GUEST", is_superuser=False, roles=[role])
    session.add(UserTenantLink(user_id=author.id, tenant_id=TENANT_A))
    session.commit()
    return author


@pytest.fixture(name="finance_role")
def finance_role_fixture(session: Session) -> Role:
    """A seeded role that carries `finance:read` — the `Morador (papel)` row."""
    role = profile_role(session, "RESIDENT", TENANT_A)
    assert "finance:read" in role.permissions
    return role


# ---------------------------------------------------------------------------
# The frozen-administration bug
# ---------------------------------------------------------------------------


def test_renaming_a_role_that_carries_a_disabled_modules_permission_still_works(
    session: Session,
    tenant_client: TestClient,
    tenant_admin: User,
    finance_role: Role,
):
    """The editor's full resend of an unchanged bundle must still save."""
    _disable(session, "finance")
    role_id = finance_role.id
    resend = list(finance_role.permissions)

    response = tenant_client.patch(
        f"/api/v1/roles/{role_id}",
        headers=_auth(tenant_admin),
        json={"name": "Morador renomeado", "permissions": resend},
    )

    assert response.status_code == 200
    session.expire_all()
    reread = session.exec(select(Role).where(Role.id == role_id)).one()
    assert "finance:read" in reread.permissions
    assert reread.permissions == resend


def test_assigning_a_user_to_a_role_carrying_a_disabled_modules_permission_still_works(
    session: Session,
    tenant_client: TestClient,
    tenant_admin: User,
    finance_role: Role,
):
    """Granted and inert in the same case: the assignment lands, the read does not."""
    _disable(session, "finance")
    assignee = _make_user(session, "GUEST", is_superuser=False)
    session.add(UserTenantLink(user_id=assignee.id, tenant_id=TENANT_A))
    session.commit()
    assignee_id = assignee.id

    response = tenant_client.patch(
        f"/api/v1/users/{assignee_id}",
        headers=_auth(tenant_admin),
        json={"role_ids": [str(finance_role.id)]},
    )
    assert response.status_code == 200

    me = tenant_client.get(
        "/api/v1/permissions/me", headers=_auth(assignee)
    )
    assert not [p for p in me.json()["permissions"] if p.startswith("finance:")]
    assert me.json()["disabled_modules"] == ["finance"]


def test_a_disabled_modules_permission_can_still_be_added_by_an_author_who_holds_it_unstripped(
    session: Session, tenant_client: TestClient, tenant_admin: User
):
    """Adding, not only resending: the author's unstripped authority governs."""
    _disable(session, "finance")

    response = tenant_client.post(
        "/api/v1/roles/",
        headers=_auth(tenant_admin),
        json={"name": "Comissão de Finanças", "permissions": ["finance:read"]},
    )

    assert response.status_code == 201
    created = uuid.UUID(response.json()["id"])
    session.expire_all()
    reread = session.exec(select(Role).where(Role.id == created)).one()
    assert reread.permissions == ["finance:read"]

    # ...and absent from every reader's effective set while the module is off.
    holder = _make_user(session, "GUEST", is_superuser=False, roles=[reread])
    session.add(UserTenantLink(user_id=holder.id, tenant_id=TENANT_A))
    session.commit()
    deps.tenant_context.set_acting_tenant(session, TENANT_A)
    assert "finance:read" not in deps.get_effective_permissions(holder, session)


# ---------------------------------------------------------------------------
# The escalation pins, restated under a module switch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("finance_off", [True, False])
def test_an_over_privileged_grant_is_still_refused_with_the_module_off(
    session: Session, tenant_client: TestClient, finance_off: bool
):
    """IAM F2's pin, verbatim. The switch must not become a grant loophole."""
    if finance_off:
        _disable(session, "finance")
    author = _role_author(session)
    # The author lacks `finance:category_create` **even unstripped**, module
    # on or off, so no reading of the switch can make this grant legal.
    deps.tenant_context.set_acting_tenant(session, TENANT_A)
    assert "finance:category_create" not in deps.get_grantable_permissions(
        author, session
    )

    response = tenant_client.post(
        "/api/v1/roles/",
        headers=_auth(author),
        json={"name": "Escalada", "permissions": ["finance:category_create"]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You cannot grant permissions you do not hold: finance:category_create"
    )


@pytest.mark.parametrize("finance_off", [True, False])
def test_an_over_privileged_assignment_is_still_refused_with_the_module_off(
    session: Session, tenant_client: TestClient, finance_off: bool
):
    """The same for `assert_can_assign_roles` (the second grant surface)."""
    if finance_off:
        _disable(session, "finance")
    author = _role_author(session)
    over_privileged = Role(
        name="Tesouraria", permissions=["finance:category_create"]
    )
    session.add(over_privileged)
    session.commit()
    session.refresh(over_privileged)
    target = _make_user(session, "GUEST", is_superuser=False)
    session.add(UserTenantLink(user_id=target.id, tenant_id=TENANT_A))
    session.commit()

    response = tenant_client.patch(
        f"/api/v1/users/{target.id}",
        headers=_auth(author),
        json={"role_ids": [str(over_privileged.id)]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You cannot grant permissions you do not hold: finance:category_create"
    )


@pytest.mark.parametrize("kind", ["superuser", "ordinary"])
def test_superuser_only_permissions_are_still_ungrantable_with_the_module_off(
    session: Session, tenant_client: TestClient, kind: str
):
    """The `SUPERUSER_ONLY_PERMISSIONS` branch runs first and is untouched.

    Refused to **every** author, superuser included: those four strings name
    routes gated by `deps.get_current_superuser`, so a role carrying them
    would be a lie.
    """
    _disable(session, "finance")
    author = (
        _make_user(session, "ADMINISTRATOR")
        if kind == "superuser"
        else _role_author(session)
    )
    if kind == "superuser":
        session.add(UserTenantLink(user_id=author.id, tenant_id=TENANT_A))
        session.commit()

    response = tenant_client.post(
        "/api/v1/roles/",
        headers=_auth(author),
        json={"name": "Falso síndico", "permissions": ["tenants:update"]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "These permissions are granted by is_superuser only: tenants:update"
    )


# ---------------------------------------------------------------------------
# The two resolvers, and who may read the unstripped one
# ---------------------------------------------------------------------------


def test_the_grant_guard_reads_the_unstripped_set(
    session: Session, tenant_admin: User
):
    """Same user, same session: the two functions differ by exactly the strip."""
    _disable(session, "finance")
    deps.tenant_context.set_acting_tenant(session, TENANT_A)

    assert "finance:read" not in deps.get_effective_permissions(
        tenant_admin, session
    )
    assert "finance:read" in deps.get_grantable_permissions(tenant_admin, session)


def test_the_two_resolvers_agree_when_no_module_is_disabled(
    session: Session, tenant_admin: User
):
    """`[]` is the all-on state, so the swap of §5.5 is invisible there.

    This is why `test_permission_escalation.py` and
    `test_legacy_role_permissions.py` need no edit at all.
    """
    deps.tenant_context.set_acting_tenant(session, TENANT_A)

    assert deps.get_effective_permissions(
        tenant_admin, session
    ) == deps.get_grantable_permissions(tenant_admin, session)


def _references(path: pathlib.Path, name: str) -> int:
    """How many times `name` is *referenced* (loaded) in `path`.

    A `def`/`import` binding is a `Store`, so it is deliberately not counted:
    this measures adoption, not definition (APRAS-39 §12.1, suggestion S5).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == name
        and isinstance(node.ctx, ast.Load)
    )


def test_the_unstripped_resolver_is_used_only_by_the_escalation_guards():
    """A later endpoint cannot quietly adopt it as a strip bypass.

    Exactly one `def` (in `app/api/deps.py`), exactly one `import` and
    exactly one call, both in `app/services/role_service.py`. Every other
    module in `app/` must read `get_effective_permissions`.
    """
    name = "get_grantable_permissions"
    definitions: list[str] = []
    importers: list[str] = []
    referrers: dict[str, int] = {}

    for path in sorted(APP_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if name not in source:
            continue
        relative = str(path.relative_to(APP_DIR.parent))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                definitions.append(relative)
            if isinstance(node, ast.ImportFrom) and any(
                alias.name == name for alias in node.names
            ):
                importers.append(relative)
        loads = _references(path, name)
        if loads:
            referrers[relative] = loads

    assert definitions == ["app/api/deps.py"]
    assert importers == ["app/services/role_service.py"]
    assert referrers == {"app/services/role_service.py": 1}


def test_assert_can_grant_is_the_only_call_site():
    """The one call lives inside `assert_can_grant`; `assert_can_assign_roles`
    delegates to it and therefore inherits the change with no edit of its own.
    """
    source = (APP_DIR / "services" / "role_service.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }

    assert _count_calls(functions["assert_can_grant"], "get_grantable_permissions") == 1
    assert (
        _count_calls(functions["assert_can_assign_roles"], "get_grantable_permissions")
        == 0
    )
    assert (
        _count_calls(functions["assert_can_grant"], "get_effective_permissions") == 0
    )


def _count_calls(node: ast.AST, name: str) -> int:
    return sum(
        1
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == name
    )


def test_the_seeded_bundles_that_make_this_matter_still_carry_finance_read(
    session: Session,
):
    """The premise of §5.5, asserted rather than assumed.

    If a future catalogue edit removed `finance:read` from these four
    bundles, the frozen-administration hazard would change shape and this
    module's fixtures would silently stop exercising it.
    """
    carriers = {
        profile
        for profile in PROFILE_ROLE_NAMES
        if "finance:read" in profile_role(session, profile, TENANT_A).permissions
    }

    assert carriers == {"ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"}
