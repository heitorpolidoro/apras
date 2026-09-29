"""API endpoints for Construction & Capital Improvement Projects (T007)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.api import deps as api_deps
from app.core.exceptions import ProjectAccessForbiddenError
from app.db import get_session
from app.models.enums import ProjectStatus
from app.models.project import ConstructionProject
from app.models.tenant import Tenant
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


def _project_read(project: ConstructionProject, tenant: Tenant | None) -> ProjectRead:
    """The one body every `ProjectRead` route in this module answers.

    `cover_photo_display_url` is **derived on read** and never stored
    (APRAS-104 §B), the shape `tenant_profile._profile_of` already uses for
    `theme`: `ProjectService.cover_display_url` is the single rung choosing
    between our public cover route and a third-party URL kept verbatim, so no
    route here can disagree with another about which URL a client should load.

    `ProjectService.get_project_detail` fills the same field itself, because it
    builds `ProjectDetailRead` in the service and does not pass through here.
    """
    return ProjectRead.model_validate(project).model_copy(
        update={
            "cover_photo_display_url": ProjectService.cover_display_url(project, tenant)
        }
    )


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
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
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
        items=[_project_read(p, tenant) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
) -> ProjectRead:
    """Creates a new construction project (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:create")
    project = ProjectService.create_project(session, project_in)
    return _project_read(project, tenant)


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
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
) -> ProjectRead:
    """Updates construction project attributes (Admin/Director only)."""
    _require_admin_permission(current_user, session, "projects:update")
    project = ProjectService.get_project_by_id(session, id)
    updated = ProjectService.update_project(session, project, project_in)
    return _project_read(updated, tenant)


# -----------------------------------------------------------------------------
# The cover photo (APRAS-104)
#
# Declared **after** `GET /{id}` and `PUT /{id}`, which is safe in both
# directions: `/{id}/cover-photo` is two segments and `/{id}` is one, so
# neither can shadow the other whatever the order. The two report routes above
# are the ones with a real ordering constraint -- a literal `report` competing
# with a `{id}` parameter at the same depth.
#
# Both carry `projects:update`, the permission that already authorises editing
# an obra's fields: a caller who may not edit an obra may not give it a photo,
# and a caller who may, could already set this column through `PUT /{id}`. No
# new catalogue string, so no permission-catalogue change.
# -----------------------------------------------------------------------------


@router.put("/{id}/cover-photo")
async def set_project_cover_photo(
    id: UUID,
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
) -> ProjectRead:
    """Replace one obra's cover photo. 400 on type, size or undecodable bytes.

    The stored column records exactly what the provider returned; what a
    client should *load* is the derived `cover_photo_display_url` in the body.
    The previously stored object is deleted only when it was one of ours -- see
    `ProjectService._delete_stored_cover`.
    """
    _require_admin_permission(current_user, session, "projects:update")
    project = ProjectService.get_project_by_id(session, id)
    file_bytes = await file.read()
    updated = ProjectService.set_cover_photo(
        session,
        project,
        file_bytes=file_bytes,
        filename=file.filename or "capa.png",
        content_type=file.content_type or "application/octet-stream",
    )
    return _project_read(updated, tenant)


@router.delete("/{id}/cover-photo")
def clear_project_cover_photo(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
) -> ProjectRead:
    """Remove one obra's cover photo. Idempotent: a second call is still a 200.

    200 with the read schema rather than 204, because that is what
    `DELETE /api/v1/tenant-profile/logo` already declares and there is no
    reason for the sibling resource to answer differently.
    """
    _require_admin_permission(current_user, session, "projects:update")
    project = ProjectService.get_project_by_id(session, id)
    updated = ProjectService.clear_cover_photo(session, project)
    return _project_read(updated, tenant)


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
