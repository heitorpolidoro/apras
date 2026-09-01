"""User management API endpoints.

The directory is **tenant-scoped** since APRAS-43: `GET /`,
`PATCH /{user_id}` and `PATCH /{user_id}/contact-info` all target the users
visible in the acting tenant (`UserService`, §6.2), for every caller and
every role — a superuser reaches another tenant's users by sending that
tenant's `X-Tenant-Id`, not by being exempt from the filter.

The escalation guards of `update_user` are the complement of that rule: they
are checked **only** for a caller that is not a superuser (APRAS-47 §7), and
they exist because `role`, `is_active` and `cpf` are global fields — handing
this endpoint to a tenant-local administrator without them would let the
tenant_admin of one condominium mint a superuser.
"""

from typing import Annotated
from uuid import UUID

from app.api import deps as api_deps
from app.db import get_session
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_type import UserType
from app.schemas.user import UserContactInfoUpdate, UserRead, UserUpdate
from app.schemas.user_type import UserTypeRead
from app.services import user_type_service
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

router = APIRouter()


def _to_read(user: User, tenant_id: UUID) -> UserRead:
    """Serialise a user, keeping only the acting tenant's UserType rows.

    `UserRead.user_types` is a relationship load, which the ambient filter
    deliberately exempts (APRAS-42 §4.2), so the narrowing is explicit here
    rather than implied.
    """
    read = UserRead.model_validate(user)
    read.user_types = [
        UserTypeRead.model_validate(user_type)
        for user_type in user.user_types
        if user_type.tenant_id == tenant_id
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

    Checks, in order (APRAS-43 §6.3, re-expressed by APRAS-47 §7):

    0. every caller — the target must be visible in the acting tenant, else
       404. This is the lookup itself, not an added check;
    1-3. only a caller that is **not** a superuser — may not grant the
       ADMINISTRATOR role, may not touch a superuser, and may not touch a
       user who also belongs to another tenant (every writable field here is
       global, so editing a shared user reaches across the boundary).

    The detail strings are kept verbatim on purpose: two of them are asserted
    literally by `tests/test_user_directory_scope.py`, and IAM F5 — which
    retires the word "administrator" from the vocabulary — is the slice that
    rewords them.

    The pre-existing self-protection checks (an administrator cannot
    deactivate themselves or change their own role) are untouched and still
    apply to every caller.
    """
    db_user = UserService.get_visible_user(session, user_id, tenant.id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not current_user.is_superuser:
        # A payload read, not an actor read — and with the role-change mirror
        # below it *is* the superuser grant, so it must stay closed.
        if user_in.role == UserRole.ADMINISTRATOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant administrators cannot grant the ADMINISTRATOR role",
            )
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
    if db_user.id == current_user.id:
        if user_in.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate themselves",
            )
        if user_in.role is not None and user_in.role != db_user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot change their own role",
            )

    update_data = user_in.model_dump(exclude_unset=True)

    if "user_type_ids" in update_data:
        user_type_ids = update_data.pop("user_type_ids")
        if user_type_ids is not None:
            _assign_user_types(
                session, db_user, user_type_ids, tenant.id, current_user
            )

    for key, value in update_data.items():
        setattr(db_user, key, value)

    # TRANSITIONAL (IAM F3 -> F5). While the enum still exists, ADMINISTRATOR
    # and is_superuser must move together: promoting through this route is
    # already superuser-only (rule 1), and *demoting* an administrator has
    # always removed their global power immediately. Writing the column here
    # is what keeps that true and what lets F5 drop the enum without losing or
    # stranding a grant.
    #
    # `.get(...) is not None` and not `"role" in update_data` so that an
    # explicit `{"role": null}` — which `exclude_unset` keeps, and which the
    # loop above would refuse against a NOT NULL column anyway — cannot be
    # read as "demote to non-superuser". Only a body naming a real role moves
    # the column. `update_data["role"]` is a payload read, outside both AST
    # rules.
    if update_data.get("role") is not None:
        db_user.is_superuser = update_data["role"] == UserRole.ADMINISTRATOR

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return _to_read(db_user, tenant.id)


def _assign_user_types(
    session: Session,
    db_user: User,
    user_type_ids: list[UUID],
    tenant_id: UUID,
    author: User,
) -> None:
    """Replace the target's acting-tenant UserType links, keeping the rest.

    Two deliberate differences from the pre-APRAS-43 behaviour, both §7:

    * an id that does not resolve to a UserType **of the acting tenant** is a
      422, never a silent drop — a 200 that discards half the payload is
      exactly the shape that hides a cross-tenant mistake;
    * the target's UserType rows in *other* tenants are preserved, because
      replacing the whole collection while acting in one tenant was itself a
      cross-tenant write.
    """
    found = session.exec(
        select(UserType).where(
            UserType.id.in_(user_type_ids), UserType.tenant_id == tenant_id
        )
    ).all()
    missing = set(user_type_ids) - {user_type.id for user_type in found}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Unknown user_type_ids: "
                + ", ".join(sorted(str(item) for item in missing))
            ),
        )
    # The second grant surface (APRAS-46 §9.3): handing an existing
    # over-privileged group to a confederate is the same escalation as
    # creating one.
    user_type_service.assert_can_assign_user_types(session, author, found)
    keep = [
        user_type
        for user_type in db_user.user_types
        if user_type.tenant_id != tenant_id
    ]
    db_user.user_types = [*keep, *found]


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

    ADMINISTRATOR, a tenant_admin of the acting tenant, or a MANAGER. Only
    rule 0 of §6.3 applies here — the schema exposes no `role`, no
    `is_active` and no `user_type_ids`, so there is nothing to escalate.
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
