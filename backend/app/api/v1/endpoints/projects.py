"""API endpoints for Construction & Capital Improvement Projects (T007)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.api import deps as api_deps
from app.core.exceptions import ProjectAccessForbiddenError
from app.db import get_session
from app.models.enums import ProjectStatus
from app.models.user import User
from app.schemas.document import AssociationDocumentRead
from app.schemas.project import (
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    PaginatedProjects,
    ProjectCreate,
    ProjectDetailRead,
    ProjectRead,
    ProjectUpdateCreate,
    ProjectUpdateRead,
    ProjectUpdateSchema,
)
from app.services import project_report_service
from app.services.project_service import ProjectService

router = APIRouter()


def _require_read_permission(
    current_user: User, session: Session, permission: str
) -> None:
    if not api_deps.has_permission(current_user, session, permission):
        raise ProjectAccessForbiddenError("Access denied to construction projects")


def _require_admin_permission(
    current_user: User, session: Session, permission: str
) -> None:
    if not api_deps.has_permission(current_user, session, permission):
        raise ProjectAccessForbiddenError(
            "Only ADMINISTRATOR and DIRECTOR can perform this action"
        )


def _require_update_permission(
    current_user: User, session: Session, permission: str
) -> None:
    if not api_deps.has_permission(current_user, session, permission):
        raise ProjectAccessForbiddenError(
            "Not enough privileges to post project updates"
        )


# -----------------------------------------------------------------------------
# Project Endpoints
# -----------------------------------------------------------------------------


@router.get("")
def list_projects(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    status: Annotated[ProjectStatus | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedProjects:
    """Lists construction projects with optional status filter and pagination."""
    _require_read_permission(current_user, session, "projects:read")
    items, total = ProjectService.list_projects(
        session=session, status=status, skip=skip, limit=limit
    )
    return PaginatedProjects(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectRead:
    """Creates a new construction project (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:create")
    project = ProjectService.create_project(session, project_in)
    return ProjectRead.model_validate(project)


# -----------------------------------------------------------------------------
# Report endpoints (APRAS-60)
#
# Both are declared **above** `GET /{id}`: FastAPI matches in declaration
# order, so a later `report` would be read as a `UUID` path parameter and
# answer 422 instead of rendering anything.
# -----------------------------------------------------------------------------


@router.get("/report", response_class=HTMLResponse)
def get_projects_report(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> HTMLResponse:
    """Render the acting tenant's construction projects as printable HTML."""
    _require_read_permission(current_user, session, "projects:read")
    return HTMLResponse(
        content=project_report_service.get_report_html(session, current_user)
    )


@router.post("/report/save", status_code=status.HTTP_201_CREATED)
def save_projects_report(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> AssociationDocumentRead:
    """Store the rendered report in the Document Center.

    The permission set is exactly `projects:read` + `documents:create`. The
    second is asserted by `save_report` itself, as its first statement, so a
    refused caller leaves no folder and no file behind.
    """
    _require_read_permission(current_user, session, "projects:read")
    return project_report_service.save_report(session, current_user)


@router.get("/{id}")
def get_project_detail(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectDetailRead:
    """Retrieves full project details including milestones and update logs."""
    _require_read_permission(current_user, session, "projects:read")
    return ProjectService.get_project_detail(session, id)


@router.put("/{id}")
def update_project(
    id: UUID,
    project_in: ProjectUpdateSchema,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectRead:
    """Updates construction project attributes (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:update")
    project = ProjectService.get_project_by_id(session, id)
    updated = ProjectService.update_project(session, project, project_in)
    return ProjectRead.model_validate(updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Deletes a project and its milestones/updates (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:delete")
    project = ProjectService.get_project_by_id(session, id)
    ProjectService.delete_project(session, project)


# -----------------------------------------------------------------------------
# Milestone Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/{id}/milestones",
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    id: UUID,
    milestone_in: MilestoneCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> MilestoneRead:
    """Creates a milestone under a project (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:milestone_create")
    milestone = ProjectService.create_milestone(session, id, milestone_in)
    return MilestoneRead.model_validate(milestone)


@router.put(
    "/{id}/milestones/{milestone_id}",
)
def update_milestone(
    id: UUID,
    milestone_id: UUID,
    milestone_in: MilestoneUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> MilestoneRead:
    """Updates milestone status, dates, or details (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:milestone_update")
    milestone = ProjectService.update_milestone(session, id, milestone_id, milestone_in)
    return MilestoneRead.model_validate(milestone)


@router.delete(
    "/{id}/milestones/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_milestone(
    id: UUID,
    milestone_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Deletes a milestone (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:milestone_delete")
    ProjectService.delete_milestone(session, id, milestone_id)


# -----------------------------------------------------------------------------
# Project Update Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/{id}/updates",
    status_code=status.HTTP_201_CREATED,
)
def create_project_update(
    id: UUID,
    update_in: ProjectUpdateCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectUpdateRead:
    """Posts a progress update log with photos and cost impact (Admin/Director/Manager)."""
    _require_update_permission(current_user, session, "projects:update_create")
    return ProjectService.create_project_update(session, id, current_user.id, update_in)


@router.delete(
    "/{id}/updates/{update_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project_update(
    id: UUID,
    update_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Deletes a progress update log (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:update_delete")
    ProjectService.delete_project_update(session, id, update_id)
