"""Role management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api import deps as api_deps
from app.db import get_session
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.services import role_service

router = APIRouter()


@router.get("/", response_model=list[RoleRead])
def read_roles(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],  # noqa: ARG001
) -> list[Role]:
    """Retrieve all roles."""
    return session.exec(select(Role)).all()


@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[
        User, Depends(api_deps.require_permission("roles:create"))
    ],
    role_in: RoleCreate,
) -> Role:
    """Create a new role in the acting tenant.

    ADMINISTRATOR, or a tenant_admin of the acting tenant (APRAS-43).
    """
    role_service.assert_can_grant(session, current_user, role_in.permissions)
    existing = session.exec(
        select(Role).where(Role.name == role_in.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists",
        )
    role = Role(
        name=role_in.name,
        permissions=role_in.permissions,
        landing_path=role_in.landing_path,
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


@router.patch("/{role_id}", response_model=RoleRead)
def update_role(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[
        User, Depends(api_deps.require_permission("roles:update"))
    ],
    role_id: UUID,
    role_in: RoleUpdate,
) -> Role:
    """Update a role. ADMINISTRATOR or a tenant_admin of its tenant.

    A role of another tenant is a 404 through the ambient filter, not a
    403.
    """
    db_type = session.get(Role, role_id)
    if not db_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    if role_in.permissions is not None:
        role_service.assert_can_grant(
            session, current_user, role_in.permissions
        )
        db_type.permissions = role_in.permissions
    db_type.name = role_in.name
    # `landing_path` is **only** written when the client actually sent it.
    #
    # Its sibling `permissions` guards the same hazard with a `None`
    # sentinel, which does not work here: `None` is a *meaningful* value —
    # it is how an operator clears a landing preference — so "field absent"
    # and "field explicitly null" have to stay distinguishable, and
    # `model_fields_set` is what distinguishes them.
    #
    # Without this, a save from any client that omits the field (F4's role
    # editor sent exactly `{name, permissions}`) would write NULL over the
    # `/gate` and `/welcome` values migration `0033` backfills onto
    # `Porteiro (papel)` and `Convidado (papel)`, silently regressing the two
    # landing redirects §10.4 exists to preserve.
    if "landing_path" in role_in.model_fields_set:
        db_type.landing_path = role_in.landing_path
    session.add(db_type)
    session.commit()
    session.refresh(db_type)
    return db_type


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[  # noqa: ARG001
        User, Depends(api_deps.require_permission("roles:delete"))
    ],
    role_id: UUID,
) -> None:
    """Delete a role. Requires `roles:delete` in the acting tenant.

    **Every** row is deletable since IAM F5 (APRAS-49 §13): the `role` column
    that made six of them undeletable is gone, and with it the doctrine of
    "role-linked types that cannot be deleted or renamed". Deleting
    `Diretor (papel)` strips every director, and that is the operator's
    prerogative.
    """
    db_type = session.get(Role, role_id)
    if not db_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    session.delete(db_type)
    session.commit()
