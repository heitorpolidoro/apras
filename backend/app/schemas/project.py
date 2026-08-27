"""Pydantic schemas for Construction & Capital Improvement Project Tracking (T007)."""

from datetime import date, datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MilestoneStatus, ProjectStatus


class ProjectBase(BaseModel):
    """Base schema for construction project fields."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    contractor_name: str | None = None
    total_budget: float = Field(default=0.0, ge=0.0)
    executed_budget: float = Field(default=0.0, ge=0.0)
    physical_progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    start_date: date | None = None
    estimated_completion_date: date | None = None
    actual_completion_date: date | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    cover_photo_url: str | None = None


class ProjectCreate(ProjectBase):
    """Schema for creating a new construction project."""

    pass


class ProjectUpdateSchema(BaseModel):
    """Schema for updating an existing construction project."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    contractor_name: str | None = None
    total_budget: float | None = Field(None, ge=0.0)
    executed_budget: float | None = Field(None, ge=0.0)
    physical_progress_pct: float | None = Field(None, ge=0.0, le=100.0)
    start_date: date | None = None
    estimated_completion_date: date | None = None
    actual_completion_date: date | None = None
    status: ProjectStatus | None = None
    cover_photo_url: str | None = None


class MilestoneBase(BaseModel):
    """Base schema for milestone properties."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: MilestoneStatus = MilestoneStatus.NEXT_STEPS
    due_date: date | None = None
    completion_date: date | None = None
    display_order: int = 0


class MilestoneCreate(MilestoneBase):
    """Schema for creating a project milestone."""

    pass


class MilestoneUpdate(BaseModel):
    """Schema for updating a project milestone."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: MilestoneStatus | None = None
    due_date: date | None = None
    completion_date: date | None = None
    display_order: int | None = None


class MilestoneRead(MilestoneBase):
    """Schema for reading a project milestone."""

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdateCreate(BaseModel):
    """Schema for creating a progress update / photo log."""

    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    photos: list[str] = Field(default_factory=list)
    cost_impact: float | None = 0.0


class AuthorSummary(BaseModel):
    """Summary of author information."""

    id: uuid.UUID
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdateRead(BaseModel):
    """Schema for reading a progress update."""

    id: uuid.UUID
    project_id: uuid.UUID
    author_id: uuid.UUID
    author: AuthorSummary | None = None
    title: str
    content: str
    photos: list[str] = Field(default_factory=list)
    cost_impact: float | None = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectRead(ProjectBase):
    """Schema for reading basic project info in lists."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailRead(ProjectRead):
    """Schema for reading detailed project view with milestones and updates."""

    milestones: list[MilestoneRead] = Field(default_factory=list)
    updates: list[ProjectUpdateRead] = Field(default_factory=list)


class PaginatedProjects(BaseModel):
    """Paginated list of construction projects."""

    items: list[ProjectRead]
    total: int
    skip: int
    limit: int
