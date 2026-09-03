"""The install-wide plan catalogue API (APRAS-40 §5.2).

Mounted **GLOBAL_SCOPED**: every route is superuser-only
(``Depends(api_deps.get_current_superuser)``), so no acting tenant is needed
and the router joins ``tenants`` in the global set.

**No DELETE.** ``tenant_subscription.plan_id`` is ``ON DELETE RESTRICT`` and a
plan a tenant is on must not vanish; deactivation (``PATCH {"is_active":
false}``) is the operation, exactly as for ``Tenant``.

**Why the catalogue is not readable by tenant-side actors.** A
permission-guarded ``GET /api/v1/plans/`` would need the router to be
tenant-scoped, which would put a ``get_current_superuser`` guard on a
tenant-scoped route and trip
``test_tenant_admin.py::test_no_tenant_scoped_route_keeps_a_global_admin_guard``.
The tenant sees its own plan -- name, description, included modules, prices --
**embedded** in ``GET /api/v1/subscription``.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api import deps as api_deps
from app.db import get_session
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanRead, PlanUpdate
from app.services.plan_service import PlanService

router = APIRouter()


@router.get("/")
def list_plans(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> list[PlanRead]:
    """Every plan, **including inactive ones**. Superuser only."""
    return [
        PlanRead.model_validate(plan)
        for plan in PlanService.list_plans(session=session)
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_plan(
    plan_in: PlanCreate,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> PlanRead:
    """Create a plan. Superuser only. Prices are inert display metadata."""
    return PlanRead.model_validate(
        PlanService.create_plan(session=session, plan_in=plan_in)
    )


@router.get("/{plan_id}")
def get_plan(
    plan_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> PlanRead:
    """Read one plan. Superuser only."""
    return PlanRead.model_validate(
        PlanService.get_plan(session=session, plan_id=plan_id)
    )


@router.patch("/{plan_id}")
def update_plan(
    plan_id: UUID,
    plan_in: PlanUpdate,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> PlanRead:
    """Update a plan, including `is_active`. Superuser only.

    Deactivation is the operation that replaces a delete: a tenant already on
    the plan keeps it (re-assigning the current plan is still allowed), and no
    new tenant can be moved onto it.
    """
    return PlanRead.model_validate(
        PlanService.update_plan(session=session, plan_id=plan_id, plan_in=plan_in)
    )
