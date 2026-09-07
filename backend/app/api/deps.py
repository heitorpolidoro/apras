"""
Authentication and authorization dependencies for the API.
"""

import uuid
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.orm import object_session
from sqlmodel import Session, select

from app.core import tenant_context
from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.core.permissions import CORE_MODULES, PERMISSIONS, filter_by_modules
from app.db import get_session
from app.models.role import Role
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

#: Name of the header carrying the acting tenant id.
TENANT_HEADER = "X-Tenant-Id"


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str, Depends(reusable_oauth2)],
) -> User:
    """
    Retrieve the current authenticated user from the JWT token.

    Args:
        session: Database session.
        token: JWT access token.

    Returns:
        User: The authenticated user object.

    Raises:
        HTTPException: If token is invalid, expired, or user not found.
    """
    all_keys = [settings.SECRET_KEY, *settings.SECRET_KEYS]
    payload = None

    for key in all_keys:
        try:
            payload = jwt.decode(token, key, algorithms=[settings.ALGORITHM])
            break
        except (jwt.PyJWTError, ValidationError):
            continue

    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )

    if payload is None:
        raise credentials_exception

    try:
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = uuid.UUID(user_id)
    except ValueError as err:
        raise credentials_exception from err
    user = session.get(User, token_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user


get_current_active_user = get_current_user
get_db = get_session


def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Verify the current user is a global superuser (APRAS-47 §5.1).

    Reads `User.is_superuser`, the install-wide column, and not the
    ADMINISTRATOR role it replaced. Deliberately role-free *and* tenant-free,
    so the five global `/api/v1/tenants` writes it guards keep resolving with
    no acting tenant — which is exactly why a tenant_admin, whose capability
    is only readable once a tenant is resolved, gets 403 there.

    Args:
        current_user: The authenticated user.

    Returns:
        User: The user if they carry the superuser flag.

    Raises:
        HTTPException: If the user is not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


# ---------------------------------------------------------------------------
# The tenant_admin capability (APRAS-43 §4.1)
# ---------------------------------------------------------------------------


def is_acting_tenant_admin(user: User, session: Session) -> bool:
    """Return whether the session's acting tenant grants `user` the capability.

    Deliberately **without** the `DEFAULT_TENANT_ID` fallback that
    `get_effective_role_ids` uses: that function falls back so a unit
    test session resolves deterministically, this one *grants power*, so an
    unresolved session must grant nothing. A `Session(engine)` in
    `app/seed.py`, in Alembic or in a unit test therefore never carries the
    capability, and neither does a global route — which is what makes the
    `/api/v1/tenants` 403s fall out of the design instead of out of a check
    somebody has to remember.

    The acting tenant is read from `session.info`, exactly as APRAS-42
    established, so no call site grows a parameter. `UserTenantLink` is
    excluded from `TENANT_SCOPED_MODELS`, so this query is not itself
    filtered.

    Args:
        user: The user whose capability is being read.
        session: Database session carrying (or not) an acting tenant.

    Returns:
        bool: True only when an acting tenant is resolved and grants it.
    """
    tenant_id = tenant_context.acting_tenant_id(session)
    if tenant_id is None:
        return False
    link = session.exec(
        select(UserTenantLink).where(
            UserTenantLink.user_id == user.id,
            UserTenantLink.tenant_id == tenant_id,
        )
    ).first()
    return bool(link and link.is_tenant_admin)


def get_effective_role_ids(user: User, session: Session) -> set[UUID]:
    """Return the user's role ids in the session's acting tenant.

    Since IAM F5 (APRAS-49 §3.1 #3) this is **only** the explicit
    memberships: the role-implicit membership the enum used to compute on
    every call became a real `user_role_link` row at migration time
    (`0033`, §7.2 step 2), so the resolved set is unchanged for every user
    that existed before it and is now reproducible from data alone.

    `session` stays in the signature -- it is what resolves the acting
    tenant -- even though no query is issued any more.

    Args:
        user: The user whose role ids are being computed.
        session: Database session carrying (or not) an acting tenant.

    Returns:
        set[UUID]: The ids of the user's roles in the acting tenant.
    """
    # The acting tenant of the request session, or the default tenant when
    # the caller is not a request (unit tests, `app/seed.py`).
    tenant_id = tenant_context.acting_tenant_id(session) or DEFAULT_TENANT_ID
    # Relationship loads are exempt from the ambient filter, so the roles are
    # narrowed here (APRAS-43 §5.2): without this, a dual-tenant user's
    # tenant-B rows compose into a tenant-A decision.
    return {role.id for role in user.roles if role.tenant_id == tenant_id}


def disabled_modules(session: Session) -> frozenset[str]:
    """The modules the session's acting tenant has turned off (APRAS-39 §5.1).

    Empty when no acting tenant is resolved (a global route, `app/seed.py`,
    Alembic, a bare unit-test `Session`) and empty when the acting tenant row
    is absent, because a module switch must never be the reason a session
    that resolves no tenant grants *less*: the permissions that matter on
    those paths are the caller's own, and `get_current_tenant` guarantees the
    row exists on every request that has an acting tenant.

    `CORE_MODULES` is subtracted here rather than trusted from the row: the
    API refuses to write them (§6.3), and a hand-edited row must not be able
    to lock a condominium out of its own user and role administration.

    Args:
        session: Database session carrying (or not) an acting tenant.

    Returns:
        frozenset[str]: The disabled, non-core modules of the acting tenant.
    """
    tenant_id = tenant_context.acting_tenant_id(session)
    if tenant_id is None:
        return frozenset()
    # An identity-map hit on every scoped request: `get_current_tenant`
    # already did `session.get(Tenant, tenant_id)`, so this costs no SQL.
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        return frozenset()
    return frozenset(tenant.disabled_modules) - CORE_MODULES


def _resolve_permissions(user: User, session: Session) -> frozenset[str]:
    """The user's authority in the acting tenant, **before** the module strip.

    Exactly what `get_effective_permissions` was before APRAS-39, moved
    verbatim: the superuser short-circuit, the roles' bundles, the
    acting-tenant_admin whole-catalogue branch. Nothing here knows that
    modules exist, which is what lets the two public readers above differ by
    the strip and by nothing else.

    Two short-circuits and a union (APRAS-47 §4):

      0. `user.is_superuser` -> the **whole catalogue**, in every tenant and
         with no acting tenant at all. The flag is global, so it is answered
         before any tenant is resolved;
      1. the `permissions` of the user's roles in the acting tenant
         (`get_effective_role_ids`, so a membership change is immediate and a
         role of another tenant never composes into this answer);
      2. `is_acting_tenant_admin` -> the whole catalogue as well, but only
         while acting **in the tenant that granted the capability**.

    IAM F5 (APRAS-49 §3.2) deleted the third contributor, F1's
    `LEGACY_ROLE_PERMISSIONS[user.role]` seed. `granted` now starts empty:
    every permission a non-superuser, non-tenant-admin holds comes from a
    role row, which is the whole point of the chain.

    Both short-circuits return rather than union, because
    `PERMISSIONS | anything == PERMISSIONS` and an early return says "this is
    a short-circuit" instead of "this is one more contributor".

    Scoping is what stops leakage: `is_acting_tenant_admin` reads the acting
    tenant from `session.info` and looks up *that* tenant's `UserTenantLink`,
    with no DEFAULT_TENANT_ID fallback. A síndico of A acting in B, a global
    route, `app/seed.py`, Alembic and a bare unit-test `Session` therefore
    resolve through the role/group bundles and nothing else.

    No nesting (a role's permissions are a flat list) and no per-user loose
    permission.

    Strings stored in a role's `permissions` that are not in the catalogue (a
    hand-edited row, or a permission a later slice deleted) are kept as is.
    Silently dropping them would hide a data bug that F2's UI must be able to
    show.

    Args:
        user: The user whose permissions are being resolved.
        session: Database session carrying (or not) an acting tenant.

    Returns:
        frozenset[str]: The catalogue for a superuser or an acting
        tenant_admin; otherwise the union of the user's role bundles.
    """
    # A superuser holds every permission there is, in every tenant, and with
    # no acting tenant at all.
    if user.is_superuser:
        return PERMISSIONS
    effective_ids = get_effective_role_ids(user, session)
    granted: set[str] = set()
    if effective_ids:
        roles = session.exec(
            select(Role).where(Role.id.in_(effective_ids))
        ).all()
        for role in roles:
            granted.update(role.permissions)
    # Administrator-level power inside one tenant (APRAS-43): every
    # permission, but only while acting in the tenant that granted it. It
    # reads the *capability*, never a role.
    if is_acting_tenant_admin(user, session):
        return PERMISSIONS
    return frozenset(granted)


def get_effective_permissions(user: User, session: Session) -> frozenset[str]:
    """What `user` may **do** here: authority ∩ the tenant's active modules.

    Every caller that existed before APRAS-39 keeps this signature and this
    meaning, which is what makes the module switch a single enforcement
    point: route-level `require_permission`, the in-handler `has_permission`
    checks, the object-level `SCOPE_PERMISSIONS` predicates, every
    service-level check and `GET /api/v1/permissions/me` — hence the frontend
    menu and the frontend routes — all read this one function. There is no
    registry mapping routes to modules that a future endpoint could forget to
    join.

    The composition is an intersection, never a replacement: *access*
    requires `permission ∈ role bundles` **and**
    `module_of(permission) ∉ disabled`, so the switch can only ever narrow.
    Nothing is deleted either — `role.permissions` rows are untouched, so
    re-enabling a module restores exactly the previous access.

    A superuser is deliberately **not** filtered (§5.3): the global operator
    is the one who *sets* the switch and must be able to inspect and repair a
    tenant whose module they just turned off. `_resolve_permissions` returns
    `PERMISSIONS` for them, and the exemption is re-stated here explicitly
    because the short-circuit inside `_resolve_permissions` cannot express it
    on its own.

    A disabled module produces exactly the 403 a missing permission produces
    (§5.4) — no error-path code is touched at all.

    Args:
        user: The user whose permissions are being resolved.
        session: Database session carrying (or not) an acting tenant.

    Returns:
        frozenset[str]: The authority of `_resolve_permissions`, minus every
        string whose module the acting tenant has turned off.
    """
    resolved = _resolve_permissions(user, session)
    if user.is_superuser:
        return resolved
    return filter_by_modules(resolved, disabled_modules(session))


def get_grantable_permissions(user: User, session: Session) -> frozenset[str]:
    """What `user` may **hand to somebody else**: authority, unstripped.

    The module switch is commercial packaging, not an authority boundary
    (APRAS-39 §5.5). It must not freeze a tenant's role and membership
    administration, so the two anti-escalation guards in
    `app/services/role_service.py` — and nothing else in the codebase — read
    this function instead of `get_effective_permissions`.

    Why it has to exist: `assert_can_grant` validates the **whole resulting
    bundle**, not the delta, and it is called with the editor's full resend
    (APRAS-48 ER-4) and with the union of the assigned roles' bundles. Four
    of the six seeded roles carry `finance:read`, so a stripped comparison
    would 403 a pure *rename* of any of them in a tenant with `finance` off.

    Why it escalates nothing: a grant can never exceed what the author holds
    with every module on, which is exactly what the author will hold if the
    operator re-enables the module — and the grantee's copy is inert
    meanwhile, because the strip applies to the *grantee's* reads exactly as
    to everybody's. `SUPERUSER_ONLY_PERMISSIONS` is refused by a branch that
    runs first and is untouched.

    Args:
        user: The user performing a grant.
        session: Database session carrying (or not) an acting tenant.

    Returns:
        frozenset[str]: `_resolve_permissions`, with no module filter.
    """
    return _resolve_permissions(user, session)


def has_permission(user: User, session: Session, permission: str) -> bool:
    """True when `user` holds `permission` in the session's acting tenant.

    The in-code predicate every non-route-level authorization check uses
    after IAM F2's swap: same function, same line, same exception class, same
    detail string as the role comparison it replaces -- only the condition
    changes.

    Args:
        user: The user whose permissions are being read.
        session: Database session carrying (or not) an acting tenant.
        permission: A `<module>:<action>` string from the catalogue.

    Returns:
        bool: Whether the permission is held.
    """
    return permission in get_effective_permissions(user, session)


def assert_manager_can_see_task(current_user: User, task: Task, session: Session) -> None:
    """Raise TaskNotFoundError for tasks the user is not allowed to see.

    A caller **without** `tasks:read_all` is scoped by `Task.visible_to`:
    they may only access tasks with an empty target list (visible to
    everyone so scoped) or with at least one target among their own roles.
    A caller without `tasks:read` may not access any task.

    IAM F5 (APRAS-49 §3.1 site 1) replaced the retired `MANAGER` comparison with
    `not has_permission(..., "tasks:read_all")`. The conversion is exact:
    `tasks:read_all` is the legacy `{A, D, R, P}` set, i.e. everyone but
    MANAGER, and the one actor for which the two predicates differ -- GUEST,
    who is neither a MANAGER nor a holder -- holds no `tasks:read` either and
    is refused by the line above before this one runs.

    Args:
        current_user: The authenticated user making the request.
        task: The task being accessed.
        session: Database session used to resolve permissions and role ids.

    Raises:
        TaskNotFoundError: If the task is not visible to the user.
    """
    from app.core.exceptions import TaskNotFoundError

    if not has_permission(current_user, session, "tasks:read"):
        raise TaskNotFoundError(task.id)
    if not has_permission(current_user, session, "tasks:read_all"):
        if task.visible_to and not (
            {vt.id for vt in task.visible_to}
            & get_effective_role_ids(current_user, session)
        ):
            raise TaskNotFoundError(task.id)


def assert_can_edit_task(
    current_user: User, task: Task, session: Session | None = None
) -> None:
    """Raise ForbiddenError if the user is not allowed to edit the task.

    A caller holding `tasks:update_any` may edit any task. A caller without
    it may only edit tasks that are unassigned or assigned to themselves. A
    caller without `tasks:update` may not edit any task.

    IAM F5 (APRAS-49 §3.1 site 2) replaced the retired `MANAGER` comparison with
    `not has_permission(..., "tasks:update_any")`, by the §3.1 argument: the
    permission is the legacy `{A, D, R, P}` set and the one divergent actor
    (GUEST) is already refused by `tasks:update`. The `ForbiddenError`
    message is kept verbatim and is recorded in `AGENTS.md` as legacy
    wording.

    `session` is optional and falls back to the ORM session `task` is already
    attached to. Production always passes it explicitly
    (`endpoints/tasks.py::update_task`); the fallback exists so the four
    pre-existing unit tests that call this helper with two arguments
    (`test_tasks_rbac.py`, `test_guest_rbac.py`) stay byte-identical, which
    APRAS-46 §11 requires. `object_session` is SQLAlchemy's own accessor, so
    nothing is guessed: a detached task has no session and the caller must
    supply one.

    Args:
        current_user: The authenticated user making the request.
        task: The task being edited.
        session: Database session used to resolve effective permissions.

    Raises:
        ForbiddenError: If the user's permissions do not allow editing this task.
    """
    session = session if session is not None else object_session(task)
    if not has_permission(current_user, session, "tasks:update"):
        raise ForbiddenError("Guests cannot edit tasks")
    if not has_permission(current_user, session, "tasks:update_any"):
        if task.assigned_to_id is not None and task.assigned_to_id != current_user.id:
            raise ForbiddenError(
                "Managers can only edit unassigned or self-assigned tasks"
            )


# ---------------------------------------------------------------------------
# Tenant resolution (APRAS-42 §3)
# ---------------------------------------------------------------------------


def _tenant_memberships(session: Session, user: User) -> list[UUID]:
    """Tenant ids the user is explicitly linked to, in insertion order."""
    links = session.exec(
        select(UserTenantLink).where(UserTenantLink.user_id == user.id)
    ).all()
    return [link.tenant_id for link in links]


def _resolve_from_header(
    session: Session, current_user: User, raw_header: str
) -> Tenant:
    """Resolve the acting tenant from an explicit `X-Tenant-Id` value."""
    try:
        tenant_id = uuid.UUID(raw_header)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-Id header",
        ) from err

    tenant = session.get(Tenant, tenant_id)
    is_superuser = current_user.is_superuser
    if tenant is None:
        # Never confirm the existence of a tenant to a non-superuser.
        if is_superuser:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the requested tenant",
        )
    # Membership *before* activity (APRAS-43 §7): answering "Tenant is
    # inactive" to a non-member would confirm that the tenant exists, which
    # is exactly the existence oracle the 404/403 split above exists to
    # close. A member — and any superuser — still gets the accurate
    # "Tenant is inactive".
    if not (is_superuser or tenant_id in _tenant_memberships(session, current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the requested tenant",
        )
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive"
        )
    return tenant


def _resolve_without_header(session: Session, current_user: User) -> Tenant:
    """Resolve the acting tenant of a caller that sent no header.

    400 is reserved for genuine ambiguity: the frontend does not send the
    header until APRAS-38, and migration 0028 gave every pre-existing user
    exactly one membership.
    """
    memberships = _tenant_memberships(session, current_user)
    if len(memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header is required: user belongs to multiple tenants",
        )

    tenant_id = memberships[0] if memberships else DEFAULT_TENANT_ID
    tenant = session.get(Tenant, tenant_id)
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header is required",
        )
    return tenant


def get_current_tenant(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    x_tenant_id: Annotated[str | None, Header(alias=TENANT_HEADER)] = None,
) -> Tenant:
    """Resolve the acting tenant of the request and arm the session filter.

    Attached at `include_router` level to every tenant-scoped router
    (`app/api/v1/api.py`), so "is this route scoped?" is a property of the
    mount rather than of the handler author's memory. Its only side effect
    is `tenant_context.set_acting_tenant`.
    """
    if x_tenant_id is not None:
        tenant = _resolve_from_header(session, current_user, x_tenant_id)
    else:
        tenant = _resolve_without_header(session, current_user)
    tenant_context.set_acting_tenant(session, tenant.id)
    return tenant


class PermissionRequired:
    """FastAPI dependency: 403 unless the caller holds `permission`.

    A class rather than a closure so `tests/test_permission_enforcement.py`
    can read `.permission` off a route's dependant tree and compare it to
    `ROUTE_PERMISSIONS`.

    Depends on `get_current_tenant` for the same reason
    `get_current_tenant_admin` did (APRAS-43 §4.2): the acting tenant must be
    resolved before permissions are, router-level dependencies resolve first,
    and a shared sub-dependency is solved once per request, so this is
    self-sufficient and free.

    **Which routes carry it.** Any route in `ROUTE_PERMISSIONS` whose
    enforcement form is **D**, the route-level dependency form. That is not a
    fixed list and it is deliberately not enumerated here: the set is walked
    off `route.dependant` and asserted by
    `tests/test_permission_enforcement.py::PERMISSION_GUARDED_ROUTES`, which
    also pins its size, and every mapped route is placed in exactly one of the
    five declared forms by `tests/test_permission_alignment.py`. Adding a
    route to this form is an ordinary, reviewable change: update that literal.

    IAM F2 (APRAS-46) shipped this class on seven routes and said so here.
    That sentence is retired, not merely stale: APRAS-40 added three, APRAS-44
    eighteen and APRAS-51 twenty-five, and a docstring naming a count is the
    exact defect class APRAS-51 exists to close — a normative statement about
    enforcement that the code contradicts.

    **The rule that still binds** is about *moving* a gate, not about adding
    one. A gate that runs inside the handler today must stay inside the
    handler: FastAPI solves sub-dependencies *before* it raises
    body-validation errors, so hoisting one into the dependency tree would
    flip a denied caller's `422` (invalid body) or `404` (missing object) into
    a `403`. It is what keeps the five `SERVICE_ENFORCED` routes
    (`tests/test_permission_alignment.py`) out of this form — converting them
    would delete a `BallotRejection` audit row, a Portuguese user-facing
    message and the `packages:queue_read` gatehouse short-circuit. What
    APRAS-51 added instead is a gate where there was **none**, on 25 routes
    the map already claimed, which moves three parity cells and no others.
    """

    def __init__(self, permission: str) -> None:
        self.permission = permission

    def __call__(
        self,
        session: Annotated[Session, Depends(get_session)],
        current_user: Annotated[User, Depends(get_current_user)],
        _tenant: Annotated[Tenant, Depends(get_current_tenant)],
    ) -> User:
        if not has_permission(current_user, session, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user


def require_permission(permission: str) -> PermissionRequired:
    """The route-level guard: `Depends(require_permission("lots:delete"))`.

    Returns the `User`, so a handler signature that read
    `Depends(get_current_tenant_admin)` needs no other edit, and the 403
    detail is byte-identical to the one it replaces.
    """
    return PermissionRequired(permission)


def use_global_tenant_scope(
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Mark the request session resolved with no acting tenant.

    Attached to the routes of the global allowlist (§5.3) so the fail-closed
    guard does not fire on them.
    """
    tenant_context.use_global_scope(session)


def use_default_tenant_scope(
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Act in the default tenant without consulting a user.

    Used by `POST /api/v1/auth/signup` only: an unauthenticated caller must
    not be able to place itself in an arbitrary tenant by guessing a UUID,
    so any `X-Tenant-Id` header is ignored there.
    """
    tenant_context.set_acting_tenant(session, DEFAULT_TENANT_ID)
