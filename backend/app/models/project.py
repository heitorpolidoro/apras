"""Construction project models for APRAS (T007)."""

from datetime import date, datetime
from typing import TYPE_CHECKING
import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import MilestoneStatus, ProjectStatus

if TYPE_CHECKING:
    from app.models.user import User


class ConstructionProject(SQLModel, table=True):
    """Primary entity representing a construction or capital improvement project."""

    __tablename__ = "construction_project"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(nullable=False, index=True)
    description: str | None = Field(default=None, nullable=True)
    contractor_name: str | None = Field(default=None, nullable=True)
    total_budget: float = Field(default=0.0, nullable=False)
    executed_budget: float = Field(default=0.0, nullable=False)
    physical_progress_pct: float = Field(default=0.0, nullable=False)
    start_date: date | None = Field(default=None, nullable=True)
    estimated_completion_date: date | None = Field(default=None, nullable=True)
    actual_completion_date: date | None = Field(default=None, nullable=True)
    status: ProjectStatus = Field(
        default=ProjectStatus.PLANNED, nullable=False, index=True
    )
    cover_photo_url: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    milestones: list["ProjectMilestone"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ProjectMilestone.display_order",
        },
    )
    updates: list["ProjectUpdate"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "desc(ProjectUpdate.created_at)",
        },
    )


class ProjectMilestone(SQLModel, table=True):
    """Deliverables or stages linked to a construction project."""

    __tablename__ = "project_milestone"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="construction_project.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    title: str = Field(nullable=False)
    description: str | None = Field(default=None, nullable=True)
    status: MilestoneStatus = Field(
        default=MilestoneStatus.NEXT_STEPS, nullable=False, index=True
    )
    due_date: date | None = Field(default=None, nullable=True)
    completion_date: date | None = Field(default=None, nullable=True)
    display_order: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    project: ConstructionProject = Relationship(back_populates="milestones")


class ProjectUpdate(SQLModel, table=True):
    """Progress log entry, narrative update, or site photo posted for a project."""

    __tablename__ = "project_update"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="construction_project.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    author_id: uuid.UUID = Field(
        foreign_key="user.id",
        ondelete="RESTRICT",
        nullable=False,
        index=True,
    )
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    photos_json: str | None = Field(default=None, nullable=True)  # JSON list of urls
    cost_impact: float | None = Field(default=0.0, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    project: ConstructionProject = Relationship(back_populates="updates")
    author: "User" = Relationship()
