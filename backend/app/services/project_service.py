"""Construction project service layer handling business logic and transactions (T007)."""

from datetime import date, datetime
import json
from uuid import UUID

from sqlmodel import Session, col, func, select

from app.core.exceptions import (
    MilestoneNotFoundError,
    ProjectNotFoundError,
    ProjectUpdateNotFoundError,
)
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.user import User
from app.schemas.project import (
    AuthorSummary,
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    ProjectCreate,
    ProjectDetailRead,
    ProjectRead,
    ProjectUpdateCreate,
    ProjectUpdateRead,
    ProjectUpdateSchema,
)


class ProjectService:
    """Service class for Construction Project domain operations."""

    @staticmethod
    def list_projects(
        session: Session,
        status: ProjectStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ConstructionProject], int]:
        """Lists projects with optional status filter and pagination."""
        query = select(ConstructionProject)
        if status:
            query = query.where(ConstructionProject.status == status)

        # Count total
        subq = query.subquery()
        total_stmt = select(func.count()).select_from(subq)
        total = session.exec(total_stmt).one()

        query = (
            query.order_by(ConstructionProject.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        projects = session.exec(query).all()
        return list(projects), total

    @staticmethod
    def create_project(
        session: Session, project_in: ProjectCreate
    ) -> ConstructionProject:
        """Creates a new construction project."""
        project = ConstructionProject(
            title=project_in.title,
            description=project_in.description,
            contractor_name=project_in.contractor_name,
            total_budget=project_in.total_budget,
            executed_budget=project_in.executed_budget,
            physical_progress_pct=project_in.physical_progress_pct,
            start_date=project_in.start_date,
            estimated_completion_date=project_in.estimated_completion_date,
            actual_completion_date=project_in.actual_completion_date,
            status=project_in.status,
            cover_photo_url=project_in.cover_photo_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        return project

    @staticmethod
    def get_project_by_id(session: Session, project_id: UUID) -> ConstructionProject:
        """Retrieves a project entity or raises ProjectNotFoundError."""
        project = session.get(ConstructionProject, project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return project

    @classmethod
    def get_project_detail(
        cls, session: Session, project_id: UUID
    ) -> ProjectDetailRead:
        """Retrieves a project with its milestones and chronological update logs."""
        project = cls.get_project_by_id(session, project_id)

        # Milestones sorted by display_order, created_at
        milestones_query = (
            select(ProjectMilestone)
            .where(ProjectMilestone.project_id == project.id)
            .order_by(
                ProjectMilestone.display_order.asc(),
                ProjectMilestone.created_at.asc(),
            )
        )
        milestones = session.exec(milestones_query).all()
        milestone_reads = [
            MilestoneRead.model_validate(m) for m in milestones
        ]

        # Updates sorted by created_at desc
        updates_query = (
            select(ProjectUpdate)
            .where(ProjectUpdate.project_id == project.id)
            .order_by(ProjectUpdate.created_at.desc())
        )
        updates = session.exec(updates_query).all()

        update_reads: list[ProjectUpdateRead] = []
        for u in updates:
            photos: list[str] = []
            if u.photos_json:
                try:
                    photos = json.loads(u.photos_json)
                except Exception:
                    photos = []

            author_summary: AuthorSummary | None = None
            if u.author:
                author_summary = AuthorSummary(
                    id=u.author.id,
                    full_name=u.author.full_name or u.author.email,
                    email=u.author.email,
                )
            else:
                author_user = session.get(User, u.author_id)
                if author_user:
                    author_summary = AuthorSummary(
                        id=author_user.id,
                        full_name=author_user.full_name or author_user.email,
                        email=author_user.email,
                    )

            update_reads.append(
                ProjectUpdateRead(
                    id=u.id,
                    project_id=u.project_id,
                    author_id=u.author_id,
                    author=author_summary,
                    title=u.title,
                    content=u.content,
                    photos=photos,
                    cost_impact=u.cost_impact,
                    created_at=u.created_at,
                )
            )

        base_read = ProjectRead.model_validate(project)
        return ProjectDetailRead(
            **base_read.model_dump(),
            milestones=milestone_reads,
            updates=update_reads,
        )

    @staticmethod
    def update_project(
        session: Session,
        project: ConstructionProject,
        project_in: ProjectUpdateSchema,
    ) -> ConstructionProject:
        """Updates project details and metrics."""
        update_data = project_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(project, key, value)

        project.updated_at = datetime.utcnow()
        session.add(project)
        session.commit()
        session.refresh(project)
        return project

    @staticmethod
    def delete_project(session: Session, project: ConstructionProject) -> None:
        """Deletes a project and cascades deletion to milestones and updates."""
        session.delete(project)
        session.commit()

    @classmethod
    def create_milestone(
        cls, session: Session, project_id: UUID, milestone_in: MilestoneCreate
    ) -> ProjectMilestone:
        """Creates a milestone for a project."""
        cls.get_project_by_id(session, project_id)

        completion_date = milestone_in.completion_date
        if (
            milestone_in.status == MilestoneStatus.DONE
            and completion_date is None
        ):
            completion_date = date.today()

        milestone = ProjectMilestone(
            project_id=project_id,
            title=milestone_in.title,
            description=milestone_in.description,
            status=milestone_in.status,
            due_date=milestone_in.due_date,
            completion_date=completion_date,
            display_order=milestone_in.display_order,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(milestone)
        session.commit()
        session.refresh(milestone)
        return milestone

    @classmethod
    def update_milestone(
        cls,
        session: Session,
        project_id: UUID,
        milestone_id: UUID,
        milestone_in: MilestoneUpdate,
    ) -> ProjectMilestone:
        """Updates milestone status, dates, or display order."""
        milestone = session.get(ProjectMilestone, milestone_id)
        if not milestone or milestone.project_id != project_id:
            raise MilestoneNotFoundError(milestone_id)

        update_data = milestone_in.model_dump(exclude_unset=True)

        if (
            milestone_in.status == MilestoneStatus.DONE
            and milestone.status != MilestoneStatus.DONE
            and milestone_in.completion_date is None
            and not milestone.completion_date
        ):
            milestone.completion_date = date.today()

        for key, value in update_data.items():
            if value is not None:
                setattr(milestone, key, value)

        milestone.updated_at = datetime.utcnow()
        session.add(milestone)
        session.commit()
        session.refresh(milestone)
        return milestone

    @classmethod
    def delete_milestone(
        cls, session: Session, project_id: UUID, milestone_id: UUID
    ) -> None:
        """Deletes a milestone."""
        milestone = session.get(ProjectMilestone, milestone_id)
        if not milestone or milestone.project_id != project_id:
            raise MilestoneNotFoundError(milestone_id)

        session.delete(milestone)
        session.commit()

    @classmethod
    def create_project_update(
        cls,
        session: Session,
        project_id: UUID,
        author_id: UUID,
        update_in: ProjectUpdateCreate,
    ) -> ProjectUpdateRead:
        """Posts a progress update / photo log and reflects financial cost impact."""
        project = cls.get_project_by_id(session, project_id)

        photos_json = (
            json.dumps(update_in.photos) if update_in.photos else None
        )

        update = ProjectUpdate(
            project_id=project_id,
            author_id=author_id,
            title=update_in.title,
            content=update_in.content,
            photos_json=photos_json,
            cost_impact=update_in.cost_impact or 0.0,
            created_at=datetime.utcnow(),
        )
        session.add(update)

        if update_in.cost_impact and update_in.cost_impact > 0:
            project.executed_budget += update_in.cost_impact
            project.updated_at = datetime.utcnow()
            session.add(project)

        session.commit()
        session.refresh(update)

        author_user = session.get(User, author_id)
        author_summary = None
        if author_user:
            author_summary = AuthorSummary(
                id=author_user.id,
                full_name=author_user.full_name or author_user.email,
                email=author_user.email,
            )

        return ProjectUpdateRead(
            id=update.id,
            project_id=update.project_id,
            author_id=update.author_id,
            author=author_summary,
            title=update.title,
            content=update.content,
            photos=update_in.photos,
            cost_impact=update.cost_impact,
            created_at=update.created_at,
        )

    @classmethod
    def delete_project_update(
        cls, session: Session, project_id: UUID, update_id: UUID
    ) -> None:
        """Deletes a project update."""
        update = session.get(ProjectUpdate, update_id)
        if not update or update.project_id != project_id:
            raise ProjectUpdateNotFoundError(update_id)

        session.delete(update)
        session.commit()
