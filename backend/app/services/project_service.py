"""Construction project service layer
handling business logic and transactions
(T007)."""

import io
import json
import logging
from pathlib import PurePosixPath
from uuid import UUID

from PIL import Image
from sqlmodel import Session, func, select

from app.core import clock
from app.core.exceptions import (
    InvalidPhotoFormatError,
    MilestoneNotFoundError,
    PhotoFileTooLargeError,
    ProjectNotFoundError,
    ProjectUpdateNotFoundError,
)
from app.core.money import ZERO, quantize_money
from app.core.tenant_context import acting_tenant_id
from app.core.uploads import image_content_type_for_suffix
from app.core.urls import public_project_cover_url
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
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
from app.services.media_service import ALLOWED_MIME_TYPES, MAX_FILE_SIZE
from app.services.storage_service import BaseStorageProvider, upload_storage_provider

logger = logging.getLogger(__name__)

#: The provider every cover-photo read and write goes through, bound once at
#: import as ``tenant_service`` binds its own: a module-level name is the seam
#: a test replaces with a real ``LocalStorageProvider`` rooted in ``tmp_path``.
#: Which provider it is, is decided by ``upload_storage_provider`` and by
#: nothing here (APRAS-94 §1).
_storage_provider: BaseStorageProvider = upload_storage_provider()


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
            total_budget=quantize_money(project_in.total_budget),
            executed_budget=quantize_money(project_in.executed_budget),
            physical_progress_pct=project_in.physical_progress_pct,
            start_date=project_in.start_date,
            estimated_completion_date=project_in.estimated_completion_date,
            actual_completion_date=project_in.actual_completion_date,
            status=project_in.status,
            cover_photo_url=project_in.cover_photo_url,
            created_at=clock.db_now(),
            updated_at=clock.db_now(),
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
        milestone_reads = [MilestoneRead.model_validate(m) for m in milestones]

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
                except Exception:  # noqa: BLE001  # best-effort side effect; a failure here must not fail the request
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

        # `cover_photo_display_url` is filled **here** and not left to
        # inheritance: `ProjectDetailRead` gets the field from `ProjectRead`,
        # but this payload is built in the service rather than through
        # `projects._project_read`, so an unfilled field would answer `null`
        # from the detail route forever while the list route answered a URL.
        base_read = ProjectRead.model_validate(project).model_copy(
            update={
                "cover_photo_display_url": cls.cover_display_url(
                    project, cls._acting_tenant(session)
                )
            }
        )
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
        for money_field in ("total_budget", "executed_budget"):
            if update_data.get(money_field) is not None:
                update_data[money_field] = quantize_money(update_data[money_field])
        for key, value in update_data.items():
            if value is not None:
                setattr(project, key, value)

        project.updated_at = clock.db_now()
        session.add(project)
        session.commit()
        session.refresh(project)
        return project

    # -- the cover photo (APRAS-104) ----------------------------------------
    #
    # `cover_photo_url` is **storage truth**: it holds exactly what
    # `save_file` returned, and no renderer reads it. What a renderer reads is
    # `cover_display_url`, because the Blob store is configured with private
    # access and no URL the provider mints is fetchable by a browser (§A).

    @classmethod
    def set_cover_photo(
        cls,
        session: Session,
        project: ConstructionProject,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> ConstructionProject:
        """Validate, store and record one obra's cover photo.

        Size, then declared MIME type, then Pillow-decodability, **all before**
        the write, in the order ``TenantService.set_logo`` sequences them: a
        refused upload writes no object and no column. The declared type is a
        claim the client makes; Pillow is the check.

        The limits are ``media_service``'s -- 5 MiB and the three embeddable
        image types -- and not the logo's 2 MiB. A cover photo is a project
        photo, governed by the rules that already accept the progress
        bulletins rendered in this same report; the logo's tighter cap exists
        because the logo is embedded in *every* printed document.

        **Order of operations on replace: write, set, commit, then delete.**
        If the delete fails the store keeps one unreferenced object, which is
        cheap and invisible to every reader. Delete-first would invert that
        into a project pointing at an object that no longer exists -- a broken
        image on a public page (§C).
        """
        if len(file_bytes) > MAX_FILE_SIZE:
            raise PhotoFileTooLargeError
        if content_type not in ALLOWED_MIME_TYPES:
            raise InvalidPhotoFormatError
        try:
            Image.open(io.BytesIO(file_bytes)).verify()
        except Exception as exc:
            raise InvalidPhotoFormatError from exc

        previous = project.cover_photo_url
        _, url = _storage_provider.save_file(
            file_bytes, filename, content_type, tenant_id=acting_tenant_id(session)
        )
        project.cover_photo_url = url
        project.updated_at = clock.db_now()
        session.add(project)
        session.commit()
        session.refresh(project)

        cls._delete_stored_cover(project.id, previous)
        return project

    @classmethod
    def clear_cover_photo(
        cls, session: Session, project: ConstructionProject
    ) -> ConstructionProject:
        """Drop the cover photo. Idempotent: an already-null column is a 200.

        In scope because :meth:`update_project` skips ``None`` values, so
        ``PUT /projects/{id}`` cannot clear this column at all -- without this
        the removal of the form's URL field would leave no way to drop a cover.
        """
        previous = project.cover_photo_url
        if previous is None:
            return project

        project.cover_photo_url = None
        project.updated_at = clock.db_now()
        session.add(project)
        session.commit()
        session.refresh(project)

        cls._delete_stored_cover(project.id, previous)
        return project

    @staticmethod
    def cover_photo_bytes(
        project: ConstructionProject | None,
    ) -> tuple[bytes, str] | None:
        """One obra's cover photo as ``(payload, content_type)``, or ``None``.

        The public cover route is a thin handler over this and turns every
        ``None`` into the same 404. Four refusals, none of them an error: no
        stored value; a suffix outside the three embeddable image types; a
        value this provider does not own (a pasted CDN or Drive URL, which it
        cannot read back); and a read that comes back empty -- missing,
        unreadable, or **above the ceiling**.

        **The ceiling is stated here rather than left to the provider's
        default.** ``storage_service.BLOB_MAX_READ_BYTES`` is 2 MiB, sized to
        ``TenantService.LOGO_MAX_FILE_SIZE``, and this caller accepts 5 MiB on
        upload -- so leaning on that default would ship a route that answers
        200 on upload and 404 forever after for every cover above 2 MiB.
        ``TenantService.logo_bytes`` passes its own ceiling for exactly this
        reason.
        """
        url = getattr(project, "cover_photo_url", None)
        if not url:
            return None

        content_type = image_content_type_for_suffix(PurePosixPath(url).suffix)
        if content_type is None or content_type not in ALLOWED_MIME_TYPES:
            return None

        payload = _storage_provider.read_file(url, max_bytes=MAX_FILE_SIZE)
        if not payload:
            return None

        return payload, content_type

    @staticmethod
    def cover_display_url(
        project: ConstructionProject, tenant: Tenant | None
    ) -> str | None:
        """Which URL a renderer should load for this obra's cover photo.

        One rung, in one function, so the report hero, the obra card and both
        read routes cannot disagree:

        1. no stored value, or no tenant to name in a path -> ``None``, and the
           renderer draws its placeholder. ``tenant`` is ``| None`` because
           ``project_report_service._acting_tenant`` can answer ``None`` and
           that function's policy is that a missing row degrades like a missing
           logo -- never an ``AttributeError``, and never the raw stored value;
        2. a value **this provider minted** -> our public cover route, which
           reads the object with the store's own credential and answers bytes.
           The stored value is never exposed: the store is private, so it is
           unfetchable by a browser anyway;
        3. anything else -> the stored value **verbatim**. Rows whose column is
           a CDN or Drive URL render today and keep rendering, and
           ``backend/scripts/sync_obras_from_drive.py`` writes more of them on
           every run. No open redirect is introduced: our route never forwards
           to a foreign host, it 404s for a value it cannot read.
        """
        stored = project.cover_photo_url
        if not stored:
            return None
        slug = getattr(tenant, "slug", None)
        if not slug:
            return None
        if _storage_provider.resolve_stored_path(stored) is None:
            return stored
        return public_project_cover_url(slug, project.id)

    @staticmethod
    def _acting_tenant(session: Session) -> Tenant | None:
        """The acting tenant's own row, for the display URL's slug.

        The established rung (`document_service`, `role_service`,
        `project_report_service._acting_tenant`): the acting tenant id with the
        default as the fallback, then a by-id `get`. `Tenant` carries no
        `tenant_id` and is never narrowed by the ambient criteria, so a bare
        `select(Tenant).first()` would name another condominium in the URL.
        """
        return session.get(Tenant, acting_tenant_id(session) or DEFAULT_TENANT_ID)

    @staticmethod
    def _delete_stored_cover(project_id: UUID, url: str | None) -> None:
        """Best-effort removal of the object a previous ``cover_photo_url`` named.

        The provider decides what the value maps to: only a URL it minted
        itself resolves, so a pasted third-party URL is somebody else's file
        and is left alone (APRAS-61).

        **A ``False`` from ``delete_file`` is logged here**, and that is this
        helper's reason to exist rather than a call to ``delete_file`` inline.
        The write-then-delete ordering above accepts an orphaned object as its
        chosen failure mode, and that is only acceptable while the orphan is
        recorded *somewhere* -- which the storage layer does not do uniformly:
        ``VercelBlobStorageProvider.delete_file`` logs a refusing store, but
        ``LocalStorageProvider.delete_file`` is ``except Exception: return
        False`` with no log at all, and every other caller discards the bool.
        The warning belongs in this task's own helper rather than in the shared
        provider, whose behaviour the logo and the bulletin photos also depend
        on.
        """
        stored = _storage_provider.resolve_stored_path(url)
        if stored is None:
            return
        if not _storage_provider.delete_file(stored):
            logger.warning(
                "Obra %s: a foto de capa anterior nao pudemos remover do "
                "armazenamento e ficou orfa (valor=%s)",
                project_id,
                url,
            )

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
        if milestone_in.status == MilestoneStatus.DONE and completion_date is None:
            completion_date = clock.today_utc()

        milestone = ProjectMilestone(
            project_id=project_id,
            title=milestone_in.title,
            description=milestone_in.description,
            status=milestone_in.status,
            due_date=milestone_in.due_date,
            completion_date=completion_date,
            display_order=milestone_in.display_order,
            created_at=clock.db_now(),
            updated_at=clock.db_now(),
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
        # `ProjectMilestone` inherits its tenant; loading the scoped parent
        # through the filtered session is what 404s a cross-tenant id
        # (APRAS-42 §6.1).
        cls.get_project_by_id(session, project_id)
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
            milestone.completion_date = clock.today_utc()

        for key, value in update_data.items():
            if value is not None:
                setattr(milestone, key, value)

        milestone.updated_at = clock.db_now()
        session.add(milestone)
        session.commit()
        session.refresh(milestone)
        return milestone

    @classmethod
    def delete_milestone(
        cls, session: Session, project_id: UUID, milestone_id: UUID
    ) -> None:
        """Deletes a milestone."""
        cls.get_project_by_id(session, project_id)
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

        photos_json = json.dumps(update_in.photos) if update_in.photos else None

        update = ProjectUpdate(
            project_id=project_id,
            author_id=author_id,
            title=update_in.title,
            content=update_in.content,
            photos_json=photos_json,
            cost_impact=quantize_money(update_in.cost_impact or ZERO),
            created_at=clock.db_now(),
        )
        session.add(update)

        if update_in.cost_impact and update_in.cost_impact > 0:
            project.executed_budget = quantize_money(
                project.executed_budget + update_in.cost_impact
            )
            project.updated_at = clock.db_now()
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
        cls.get_project_by_id(session, project_id)
        update = session.get(ProjectUpdate, update_id)
        if not update or update.project_id != project_id:
            raise ProjectUpdateNotFoundError(update_id)

        session.delete(update)
        session.commit()
