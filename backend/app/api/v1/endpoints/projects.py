"""API endpoints for Construction & Capital Improvement Projects (T007)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api import deps as api_deps
from app.core.exceptions import ProjectAccessForbiddenError
from app.db import get_session
from app.models.enums import ProjectStatus, UserRole
from app.models.user import User
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
from app.services.project_service import ProjectService

router = APIRouter()

_PROJECT_READ_ROLES = {
    UserRole.ADMINISTRATOR,
    UserRole.DIRECTOR,
    UserRole.MANAGER,
    UserRole.RESIDENT,
}
_PROJECT_ADMIN_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}
_PROJECT_UPDATE_ROLES = {
    UserRole.ADMINISTRATOR,
    UserRole.DIRECTOR,
    UserRole.MANAGER,
}


def _require_read_permission(current_user: User) -> None:
    if current_user.role not in _PROJECT_READ_ROLES:
        raise ProjectAccessForbiddenError(
            "Access denied to construction projects"
        )


def _require_admin_permission(current_user: User) -> None:
    if current_user.role not in _PROJECT_ADMIN_ROLES:
        raise ProjectAccessForbiddenError(
            "Only ADMINISTRATOR and DIRECTOR can perform this action"
        )


def _require_update_permission(current_user: User) -> None:
    if current_user.role not in _PROJECT_UPDATE_ROLES:
        raise ProjectAccessForbiddenError(
            "Not enough privileges to post project updates"
        )


# -----------------------------------------------------------------------------
# Project Endpoints
# -----------------------------------------------------------------------------


@router.get("", response_model=PaginatedProjects)
def list_projects(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    status: ProjectStatus | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedProjects:
    """Lists construction projects with optional status filter and pagination."""
    _require_read_permission(current_user)
    items, total = ProjectService.list_projects(
        session=session, status=status, skip=skip, limit=limit
    )
    return PaginatedProjects(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectRead:
    """Creates a new construction project (Admin/Director only)."""
    _require_admin_permission(current_user)
    project = ProjectService.create_project(session, project_in)
    return ProjectRead.model_validate(project)


@router.get("/{id}", response_model=ProjectDetailRead)
def get_project_detail(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectDetailRead:
    """Retrieves full project details including milestones and update logs."""
    _require_read_permission(current_user)
    return ProjectService.get_project_detail(session, id)


@router.put("/{id}", response_model=ProjectRead)
def update_project(
    id: UUID,
    project_in: ProjectUpdateSchema,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectRead:
    """Updates construction project attributes (Admin/Director only)."""
    _require_admin_permission(current_user)
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
    _require_admin_permission(current_user)
    project = ProjectService.get_project_by_id(session, id)
    ProjectService.delete_project(session, project)


# -----------------------------------------------------------------------------
# Milestone Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/{id}/milestones",
    response_model=MilestoneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    id: UUID,
    milestone_in: MilestoneCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> MilestoneRead:
    """Creates a milestone under a project (Admin/Director only)."""
    _require_admin_permission(current_user)
    milestone = ProjectService.create_milestone(session, id, milestone_in)
    return MilestoneRead.model_validate(milestone)


@router.put(
    "/{id}/milestones/{milestone_id}",
    response_model=MilestoneRead,
)
def update_milestone(
    id: UUID,
    milestone_id: UUID,
    milestone_in: MilestoneUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> MilestoneRead:
    """Updates milestone status, dates, or details (Admin/Director only)."""
    _require_admin_permission(current_user)
    milestone = ProjectService.update_milestone(
        session, id, milestone_id, milestone_in
    )
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
    _require_admin_permission(current_user)
    ProjectService.delete_milestone(session, id, milestone_id)


# -----------------------------------------------------------------------------
# Project Update Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/{id}/updates",
    response_model=ProjectUpdateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_update(
    id: UUID,
    update_in: ProjectUpdateCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> ProjectUpdateRead:
    """Posts a progress update log with photos and cost impact (Admin/Director/Manager)."""
    _require_update_permission(current_user)
    return ProjectService.create_project_update(
        session, id, current_user.id, update_in
    )


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
    _require_admin_permission(current_user)
    ProjectService.delete_project_update(session, id, update_id)
