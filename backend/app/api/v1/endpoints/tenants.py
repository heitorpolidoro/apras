"""Tenant administration API endpoints (APRAS-41).

The only new observable surface of the data-layer slice. Every write is
behind `deps.get_current_superuser` (APRAS-47), which reads the global
`user.is_superuser` column and returns 403 for everyone else — including a
tenant_admin of the very tenant being written, since this router is global
and resolves no acting tenant. There is deliberately no `DELETE /api/v1/tenants/{id}`: tenant-scoped
foreign keys are `RESTRICT`, so deletion of a populated tenant could not
succeed anyway. Deactivate with `PATCH {"is_active": false}` instead.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api import deps as api_deps
from app.db import get_session
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantMemberCreate,
    TenantMemberRead,
    TenantMemberUpdate,
    TenantRead,
    TenantUpdate,
)
from app.services.tenant_service import TenantService

router = APIRouter()


@router.get("", response_model=list[TenantRead])
def list_tenants(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[TenantRead]:
    """List tenants: all of them for an administrator, own memberships
    otherwise (an empty list when there are none, never an error)."""
    return TenantService.list_tenants(session=session, current_user=current_user)


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_in: TenantCreate,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> TenantRead:
    """Create a tenant. Superuser only."""
    return TenantService.create_tenant(session=session, tenant_in=tenant_in)


@router.get("/{tenant_id}", response_model=TenantRead)
def get_tenant(
    tenant_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> TenantRead:
    """Read one tenant. A non-member non-admin gets 404, never 403."""
    return TenantService.get_visible_tenant(
        session=session, tenant_id=tenant_id, current_user=current_user
    )


@router.patch("/{tenant_id}", response_model=TenantRead)
def update_tenant(
    tenant_id: UUID,
    tenant_in: TenantUpdate,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> TenantRead:
    """Rename or (de)activate a tenant. Superuser only."""
    return TenantService.update_tenant(
        session=session, tenant_id=tenant_id, tenant_in=tenant_in
    )


@router.get("/{tenant_id}/members", response_model=list[TenantMemberRead])
def list_tenant_members(
    tenant_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> list[TenantMemberRead]:
    """List a tenant's members. Administrator, or a member of that tenant."""
    return TenantService.list_members(
        session=session, tenant_id=tenant_id, current_user=current_user
    )


@router.post(
    "/{tenant_id}/members",
    response_model=TenantMemberRead,
    status_code=status.HTTP_201_CREATED,
)
def add_tenant_member(
    tenant_id: UUID,
    member_in: TenantMemberCreate,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> TenantMemberRead:
    """Link a user to a tenant. Superuser only.

    A user already linked to a *different* tenant is linked again here
    without conflict — multi-membership is supported. Only the same
    (user, tenant) pair twice is a 409.
    """
    return TenantService.add_member(
        session=session,
        tenant_id=tenant_id,
        user_id=member_in.user_id,
        is_tenant_admin=member_in.is_tenant_admin,
    )


@router.patch("/{tenant_id}/members/{user_id}", response_model=TenantMemberRead)
def set_tenant_member_admin(
    tenant_id: UUID,
    user_id: UUID,
    member_in: TenantMemberUpdate,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> TenantMemberRead:
    """Grant or revoke the tenant_admin capability. Superuser only.

    Deliberately behind the same superuser guard as its POST/DELETE
    siblings, so a tenant_admin of that very tenant gets 403 here: this is a
    global route, and the capability is only readable when an acting tenant
    has been resolved (APRAS-43 §2.1.4). An unknown tenant, an unknown user
    or a non-member are all 404.
    """
    return TenantService.set_member_admin(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        is_tenant_admin=member_in.is_tenant_admin,
    )


@router.delete(
    "/{tenant_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_tenant_member(
    tenant_id: UUID,
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> None:
    """Unlink a user from a tenant. Superuser only."""
    TenantService.remove_member(
        session=session, tenant_id=tenant_id, user_id=user_id
    )
