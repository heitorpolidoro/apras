"""Tenant administration API endpoints (APRAS-41).

The only new observable surface of the data-layer slice. Every write is
behind the existing `deps.get_current_active_admin` guard, which already
returns 403 for every non-ADMINISTRATOR role — no new guard is invented
here. There is deliberately no `DELETE /api/v1/tenants/{id}`: tenant-scoped
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
    _: Annotated[User, Depends(api_deps.get_current_active_admin)],
) -> TenantRead:
    """Create a tenant. ADMINISTRATOR only."""
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
    _: Annotated[User, Depends(api_deps.get_current_active_admin)],
) -> TenantRead:
    """Rename or (de)activate a tenant. ADMINISTRATOR only."""
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
    _: Annotated[User, Depends(api_deps.get_current_active_admin)],
) -> TenantMemberRead:
    """Link a user to a tenant. ADMINISTRATOR only.

    A user already linked to a *different* tenant is linked again here
    without conflict — multi-membership is supported. Only the same
    (user, tenant) pair twice is a 409.
    """
    return TenantService.add_member(
        session=session, tenant_id=tenant_id, user_id=member_in.user_id
    )


@router.delete(
    "/{tenant_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_tenant_member(
    tenant_id: UUID,
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_active_admin)],
) -> None:
    """Unlink a user from a tenant. ADMINISTRATOR only."""
    TenantService.remove_member(
        session=session, tenant_id=tenant_id, user_id=user_id
    )
