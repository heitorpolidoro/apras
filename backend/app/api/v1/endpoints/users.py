"""User management API endpoints.

The directory is **tenant-scoped** since APRAS-43: `GET /`,
`PATCH /{user_id}` and `PATCH /{user_id}/contact-info` all target the users
visible in the acting tenant (`UserService`, §6.2), for every caller and
every role — a superuser reaches another tenant's users by sending that
tenant's `X-Tenant-Id`, not by being exempt from the filter.

The escalation guards of `update_user` are the complement of that rule: they
are checked **only** for a caller that is not a superuser (APRAS-47 §7), and
they exist because `is_active` and `cpf` are global fields — handing this
endpoint to a tenant-local administrator without them would let the
tenant_admin of one condominium reach across the tenant boundary.

Since IAM F5 (APRAS-49 §8.3) it can no longer mint a superuser at all:
`UserUpdate` carries neither `role` nor `is_superuser`, so `role_ids` — which
`role_service.assert_can_assign_roles` guards — is the only field here that
can widen anyone. The global flag has its own superuser-only route below.
"""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role
from app.schemas.user import (
    SuperuserRead,
    SuperuserUpdate,
    UserContactInfoUpdate,
    UserRead,
    UserUpdate,
)
from app.schemas.role import RoleRead
from app.services import role_service
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

router = APIRouter()


def _to_read(user: User, tenant_id: UUID) -> UserRead:
    """Serialise a user, keeping only the acting tenant's Role rows.

    `UserRead.roles` is a relationship load, which the ambient filter
    deliberately exempts (APRAS-42 §4.2), so the narrowing is explicit here
    rather than implied.
    """
    read = UserRead.model_validate(user)
    read.roles = [
        RoleRead.model_validate(role)
        for role in user.roles
        if role.tenant_id == tenant_id
    ]
    return read


@router.get("/", response_model=list[UserRead])
def read_users(
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    current_user: Annotated[  # noqa: ARG001
        User, Depends(api_deps.get_current_user)
    ],
    is_active: bool | None = None,
) -> list[UserRead]:
    """Retrieve the users visible in the acting tenant.

    Available to all authenticated users, as before; what changed is the
    target set, which is now membership-filtered for everyone (§6.2).
    """
    statement = UserService.visible_users_statement(tenant.id)
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    return [_to_read(user, tenant.id) for user in session.exec(statement).all()]


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    *,
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    current_user: Annotated[User, Depends(api_deps.require_permission("users:update"))],
    user_id: UUID,
    user_in: UserUpdate,
) -> UserRead:
    """Update a user. Anyone holding `users:update` in the acting tenant.

    Checks, in order (APRAS-43 §6.3, re-expressed by APRAS-47 §7 and
    APRAS-49 §8.3):

    0. every caller — the target must be visible in the acting tenant, else
       404. This is the lookup itself, not an added check;
    1-2. only a caller that is **not** a superuser — may not touch a
       superuser, and may not touch a user who also belongs to another
       tenant (`is_active` and `cpf` are global, so editing a shared user
       reaches across the boundary).

    IAM F5 deleted the former rule 1 ("may not grant the ADMINISTRATOR
    role"): there is no role to grant.

    The self-protection checks apply to **every** caller: nobody may
    deactivate themselves, and since §8.5 nobody may change their own
    `role_ids` either — which is where all authority now lives.
    """
    db_user = UserService.get_visible_user(session, user_id, tenant.id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not current_user.is_superuser:
        # IAM F5 (APRAS-49 §3.3 #2, §8.3) deleted the third rule -- "tenant
        # admins cannot grant the ADMINISTRATOR role". There is no role to
        # grant, and `is_superuser` is not a field of `UserUpdate` at all any
        # more: it moved to its own superuser-only route, which no tenant
        # admin can call. That closes the escalation hole APRAS-46 §12.5
        # recorded as inherited by this slice.
        if db_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant administrators cannot modify an administrator",
            )
        if UserService.membership_tenant_ids(session, db_user.id) - {tenant.id}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user belongs to another tenant",
            )

    # Safety check
    if db_user.id == current_user.id and user_in.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate themselves",
        )

    update_data = user_in.model_dump(exclude_unset=True)

    # The self-guard, re-expressed on `role_ids` (IAM F5, APRAS-49 §8.5).
    # It is a deliberate **narrowing**: today an administrator may freely
    # change their own memberships and is blocked only from changing their
    # own enum value. After F5 `role_ids` is the only thing that edits one's
    # own authority, which is exactly what the guard exists to forbid.
    # Compared **within the acting tenant**, because that is the only scope
    # `_assign_roles` writes: it replaces the acting tenant's links and
    # preserves the target's rows in every other tenant. `db_user.roles` is a
    # relationship load and is exempt from the ambient filter (APRAS-42
    # §4.2), so without the narrowing a dual-tenant administrator who submits
    # exactly their own acting-tenant ids -- a no-op -- would get a spurious
    # 400. The same explicit narrowing `_to_read` and `role_names_in` do.
    if db_user.id == current_user.id and "role_ids" in update_data:
        role_ids = update_data["role_ids"]
        if role_ids is not None and set(role_ids) != {
            role.id for role in db_user.roles if role.tenant_id == tenant.id
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot change their own roles",
            )

    if "role_ids" in update_data:
        role_ids = update_data.pop("role_ids")
        if role_ids is not None:
            _assign_roles(
                session, db_user, role_ids, tenant.id, current_user
            )

    for key, value in update_data.items():
        setattr(db_user, key, value)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return _to_read(db_user, tenant.id)


def _assign_roles(
    session: Session,
    db_user: User,
    role_ids: list[UUID],
    tenant_id: UUID,
    author: User,
) -> None:
    """Replace the target's acting-tenant Role links, keeping the rest.

    Two deliberate differences from the pre-APRAS-43 behaviour, both §7:

    * an id that does not resolve to a Role **of the acting tenant** is a
      422, never a silent drop — a 200 that discards half the payload is
      exactly the shape that hides a cross-tenant mistake;
    * the target's Role rows in *other* tenants are preserved, because
      replacing the whole collection while acting in one tenant was itself a
      cross-tenant write.
    """
    found = session.exec(
        select(Role).where(
            Role.id.in_(role_ids), Role.tenant_id == tenant_id
        )
    ).all()
    missing = set(role_ids) - {role.id for role in found}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Unknown role_ids: "
                + ", ".join(sorted(str(item) for item in missing))
            ),
        )
    # The second grant surface (APRAS-46 §9.3): handing an existing
    # over-privileged group to a confederate is the same escalation as
    # creating one.
    role_service.assert_can_assign_roles(session, author, found)
    keep = [
        role
        for role in db_user.roles
        if role.tenant_id != tenant_id
    ]
    db_user.roles = [*keep, *found]


@router.patch("/{user_id}/contact-info", response_model=UserRead)
def update_user_contact_info(
    *,
    session: Annotated[Session, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
    current_user: Annotated[  # noqa: ARG001
        User, Depends(api_deps.require_permission("users:update_contact"))
    ],
    user_id: UUID,
    user_in: UserContactInfoUpdate,
) -> UserRead:
    """Update a user's phone and address.

    Anyone holding `users:update_contact` in the acting tenant. Only rule 0
    of §6.3 applies here — the schema exposes no `is_active` and no
    `role_ids`, so there is nothing to escalate.
    """
    db_user = UserService.get_visible_user(session, user_id, tenant.id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return _to_read(db_user, tenant.id)


@router.patch("/{user_id}/superuser", response_model=SuperuserRead)
def set_superuser(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_superuser)],  # noqa: ARG001
    user_id: UUID,
    user_in: SuperuserUpdate,
) -> User:
    """Grant or revoke the global `is_superuser` flag (IAM F5, APRAS-49 §8.4).

    F3 shipped a *transitional* writer -- `update_user`'s role-change mirror
    -- so that demoting an administrator would not strand the flag. F5 drops
    the enum, and with it that mirror. Deleting both would leave a demoted
    administrator holding the entire catalogue in every tenant with SQL as
    the only cure, so the mirror is **replaced** here rather than merely
    deleted: the grant *and* the revoke keep a home.

    **Guard.** `get_current_superuser`, F3's dependency, unchanged. Not a
    catalogue permission, not grantable to a role, not reachable by a tenant
    admin -- which is why this route sits in `UNGUARDED_ROUTES` and maps to
    no permission, and why the parity baseline does not move.

    **The one refusal.** A revoke that would leave the install with **zero**
    active superusers answers 400. The rule is stated over the whole table
    rather than over `user_id == me`, so it subsumes self-demotion *and* one
    superuser demoting the only other one. It is the online mirror of
    `0033`'s post-condition guard: never leave the install with no way in.

    **Idempotence.** Setting the flag to the value it already holds is a 200
    no-op and never trips the refusal -- the count does not change.

    **Tenant scope.** The route is mounted inside the `users` router, which
    carries `Depends(get_current_tenant)`, so it is classified *scoped* and
    the caller must send the tenant header like every other `/users/*` route.
    The acting tenant plays no part in the decision or in what is written:
    `is_superuser` is a global flag only a superuser can write, so there is
    no self-grant to prevent by hiding the acting tenant -- the opposite call
    from APRAS-43's `PATCH /tenants/{id}/members/{user_id}`, and recorded as
    such in §8.4.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if db_user.is_superuser and not user_in.is_superuser:
        remaining = session.exec(
            select(User).where(
                User.is_superuser == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
                User.id != db_user.id,
            )
        ).first()
        if remaining is None and db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The last superuser cannot be demoted",
            )
    db_user.is_superuser = user_in.is_superuser
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user
