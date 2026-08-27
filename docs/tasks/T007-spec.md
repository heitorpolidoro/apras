</Meridian Spec Generator — Task Spec Author>
<T007 — Acompanhamento Físico e Financeiro de Obras>

## Scope

This task implements the Construction & Capital Improvement Project Tracking module ("Acompanhamento Físico e Financeiro de Obras") for APRAS. It provides HOA administrators, board directors, managers, and residents with physical progress tracking, milestone workflow management, budget vs. actual execution monitoring, and real-time site photo logs.

### In Scope
1. **Database Schema & SQLModels**:
   - `ConstructionProject`: Primary project entity tracking general details, contractor information, budget limits, executed expenses, physical completion percentage (0.0 to 100.0), timeline dates, project lifecycle status, and cover photo URL.
   - `ProjectMilestone`: Discrete deliverables or stages linked to a construction project with status (`DONE`, `IN_PROGRESS`, `NEXT_STEPS`), target due dates, actual completion dates, and display ordering.
   - `ProjectUpdate`: Progress reports and photo logs posted by authorized users containing narrative descriptions, an array of photo URLs (`photos_json`), and an optional financial cost impact (`cost_impact`).
   - Domain enumerations:
     - `ProjectStatus`: `PLANNED`, `IN_PROGRESS`, `PAUSED`, `COMPLETED`
     - `MilestoneStatus`: `DONE`, `IN_PROGRESS`, `NEXT_STEPS`
   - Foreign key relationships with cascade deletes: `ProjectMilestone.project_id -> ConstructionProject.id` (ON DELETE CASCADE) and `ProjectUpdate.project_id -> ConstructionProject.id` (ON DELETE CASCADE).
   - Alembic database migration script creating all tables, foreign keys, and indexes.

2. **RBAC & Security Matrix**:
   - `ADMINISTRATOR` & `DIRECTOR`: Full CRUD permissions across projects, milestones, and progress updates.
   - `MANAGER`: Read projects and milestones; create progress updates (`POST /api/v1/projects/{id}/updates`).
   - `RESIDENT`: Read-only access to list and view projects, milestones, financial execution progress, and progress updates feed.
   - `GUEST`: Access denied (`403 Forbidden`).

3. **Backend REST API Endpoints under `/api/v1/projects`**:
   - `GET /api/v1/projects`: List construction projects with optional status filter and pagination (`skip`, `limit`).
   - `POST /api/v1/projects`: Create a new construction project (Admin/Director).
   - `GET /api/v1/projects/{id}`: Retrieve detailed project view including milestones and chronological updates.
   - `PUT /api/v1/projects/{id}`: Update project details, budget, or physical progress percentage (Admin/Director).
   - `DELETE /api/v1/projects/{id}`: Physically delete project and cascade delete milestones and updates (Admin/Director).
   - `POST /api/v1/projects/{id}/milestones`: Add milestone to project (Admin/Director).
   - `PUT /api/v1/projects/{id}/milestones/{milestone_id}`: Update milestone details/status/dates (Admin/Director).
   - `DELETE /api/v1/projects/{id}/milestones/{milestone_id}`: Remove milestone (Admin/Director).
   - `POST /api/v1/projects/{id}/updates`: Post progress update with photos and optional cost impact (Admin/Director/Manager).
   - `DELETE /api/v1/projects/{id}/updates/{update_id}`: Delete progress update (Admin/Director).
   - Domain exception classes (`ProjectNotFoundError`, `MilestoneNotFoundError`, `ProjectUpdateNotFoundError`, `ProjectInvalidProgressError`) registered in FastAPI global exception handlers.

4. **Frontend UI & State Management**:
   - Route `/projects` (`ConstructionTrackerPage.tsx`) protected by `ProtectedRoute`.
   - Navigation link in `Navbar.tsx` ("Obras").
   - UI Components:
     - `ProjectSummaryCard`: Visual card with cover photo, status badge, physical progress circle/bar, budget progress bar, contractor name, and dates.
     - `MilestoneTimeline`: Chronological milestone board categorized into *Feito* (Done), *Em Andamento* (In Progress), and *Próximos Passos* (Next Steps).
     - `BudgetVsActualProgressBar`: Side-by-side financial comparison bar displaying total budget, executed amount, variance, and warning indicator for overruns (> 100%).
     - `ProjectUpdateFeed`: Chronological feed of photo and text updates with author metadata and cost impact badges.
     - `ProjectFormModal`: Modal dialog to create and edit construction projects.
     - `MilestoneFormModal`: Modal dialog to create and edit milestones.
     - `ProjectUpdateModal`: Modal dialog to submit progress updates with photo URLs.
   - API client module (`src/api/projects.ts`) and custom TanStack Query hooks (`src/hooks/useProjects.ts`).
   - Internationalization keys in `pt.json` and `en.json` under the `projects.*` namespace.

5. **Testing & Quality Assurance**:
   - Backend unit and API integration tests in `backend/tests/test_projects.py` and `backend/tests/test_projects_rbac.py` achieving ≥ 90% code coverage.
   - Frontend component and hook tests in `frontend/src/features/construction-tracking/__tests__/` achieving ≥ 75% code coverage.

---

## Approach

### Data Layer (`backend/app/models/` & `backend/app/schemas/`)

1. **Domain Enums (`backend/app/models/enums.py`)**:
   ```python
   class ProjectStatus(StrEnum):
       PLANNED = "PLANNED"
       IN_PROGRESS = "IN_PROGRESS"
       PAUSED = "PAUSED"
       COMPLETED = "COMPLETED"

   class MilestoneStatus(StrEnum):
       DONE = "DONE"
       IN_PROGRESS = "IN_PROGRESS"
       NEXT_STEPS = "NEXT_STEPS"
   ```

2. **SQLModel Entities (`backend/app/models/project.py`)**:
   ```python
   import uuid
   from datetime import date, datetime
   from sqlmodel import Field, Relationship, SQLModel
   from app.models.enums import ProjectStatus, MilestoneStatus

   class ConstructionProject(SQLModel, table=True):
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
       status: ProjectStatus = Field(default=ProjectStatus.PLANNED, nullable=False, index=True)
       cover_photo_url: str | None = Field(default=None, nullable=True)
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       # Relationships
       milestones: list["ProjectMilestone"] = Relationship(
           back_populates="project",
           sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ProjectMilestone.display_order"}
       )
       updates: list["ProjectUpdate"] = Relationship(
           back_populates="project",
           sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "desc(ProjectUpdate.created_at)"}
       )

   class ProjectMilestone(SQLModel, table=True):
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
       status: MilestoneStatus = Field(default=MilestoneStatus.NEXT_STEPS, nullable=False, index=True)
       due_date: date | None = Field(default=None, nullable=True)
       completion_date: date | None = Field(default=None, nullable=True)
       display_order: int = Field(default=0, nullable=False)
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       project: ConstructionProject = Relationship(back_populates="milestones")

   class ProjectUpdate(SQLModel, table=True):
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
       photos_json: str | None = Field(default=None, nullable=True)  # JSON array: ["url1", "url2"]
       cost_impact: float | None = Field(default=0.0, nullable=True)
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       project: ConstructionProject = Relationship(back_populates="updates")
   ```

3. **Pydantic Schemas (`backend/app/schemas/project.py`)**:
   ```python
   import uuid
   from datetime import date, datetime
   from pydantic import BaseModel, Field, field_validator
   from app.models.enums import ProjectStatus, MilestoneStatus

   class ProjectBase(BaseModel):
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
       pass

   class ProjectUpdateSchema(BaseModel):
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
       title: str = Field(..., min_length=1, max_length=255)
       description: str | None = None
       status: MilestoneStatus = MilestoneStatus.NEXT_STEPS
       due_date: date | None = None
       completion_date: date | None = None
       display_order: int = 0

   class MilestoneCreate(MilestoneBase):
       pass

   class MilestoneUpdate(BaseModel):
       title: str | None = Field(None, min_length=1, max_length=255)
       description: str | None = None
       status: MilestoneStatus | None = None
       due_date: date | None = None
       completion_date: date | None = None
       display_order: int | None = None

   class MilestoneRead(MilestoneBase):
       id: uuid.UUID
       project_id: uuid.UUID
       created_at: datetime
       updated_at: datetime

   class ProjectUpdateCreate(BaseModel):
       title: str = Field(..., min_length=1, max_length=255)
       content: str = Field(..., min_length=1)
       photos: list[str] = Field(default_factory=list)
       cost_impact: float | None = 0.0

   class AuthorSummary(BaseModel):
       id: uuid.UUID
       full_name: str
       email: str

   class ProjectUpdateRead(BaseModel):
       id: uuid.UUID
       project_id: uuid.UUID
       author_id: uuid.UUID
       author: AuthorSummary | None = None
       title: str
       content: str
       photos: list[str] = Field(default_factory=list)
       cost_impact: float | None = 0.0
       created_at: datetime

   class ProjectRead(ProjectBase):
       id: uuid.UUID
       created_at: datetime
       updated_at: datetime

   class ProjectDetailRead(ProjectRead):
       milestones: list[MilestoneRead] = Field(default_factory=list)
       updates: list[ProjectUpdateRead] = Field(default_factory=list)

   class PaginatedProjects(BaseModel):
       items: list[ProjectRead]
       total: int
       skip: int
       limit: int
   ```

### Service Layer (`backend/app/services/project_service.py`)

- `list_projects(session, status: ProjectStatus | None, skip: int = 0, limit: int = 50) -> tuple[list[ConstructionProject], int]`:
  Queries `ConstructionProject` with optional status filter and pagination, ordered by `created_at DESC`.
- `create_project(session, project_in: ProjectCreate) -> ConstructionProject`:
  Instantiates and saves a new `ConstructionProject`.
- `get_project_by_id(session, project_id: UUID) -> ConstructionProject`:
  Fetches project or raises `ProjectNotFoundError`.
- `get_project_detail(session, project_id: UUID) -> ProjectDetailRead`:
  Fetches project with loaded `milestones` (sorted by `display_order`) and `updates` (sorted by `created_at DESC`). Populates `author` details on updates.
- `update_project(session, project: ConstructionProject, project_in: ProjectUpdateSchema) -> ConstructionProject`:
  Applies non-None fields, updates `updated_at`, and saves.
- `delete_project(session, project: ConstructionProject) -> None`:
  Deletes project entity (cascade deletes milestones and updates in DB).
- `create_milestone(session, project_id: UUID, milestone_in: MilestoneCreate) -> ProjectMilestone`:
  Verifies project exists, sets completion_date automatically if `status == MilestoneStatus.DONE` and completion_date was not provided, saves milestone.
- `update_milestone(session, milestone_id: UUID, milestone_in: MilestoneUpdate) -> ProjectMilestone`:
  Fetches milestone or raises `MilestoneNotFoundError`. Automatically updates `completion_date` to current date if transitioning to `DONE` without explicit date.
- `delete_milestone(session, milestone_id: UUID) -> None`:
  Deletes milestone or raises `MilestoneNotFoundError`.
- `create_project_update(session, project_id: UUID, author_id: UUID, update_in: ProjectUpdateCreate) -> ProjectUpdate`:
  Verifies project exists. Serializes `photos` list to `photos_json`. Optionally adds `cost_impact` to `project.executed_budget` if cost_impact > 0.
- `delete_project_update(session, update_id: UUID) -> None`:
  Deletes update or raises `ProjectUpdateNotFoundError`.

### Endpoint & Security Layer (`backend/app/api/v1/endpoints/projects.py`)

- **Permissions Enforcement**:
  - `GET /api/v1/projects` & `GET /api/v1/projects/{id}`:
    Allowed for authenticated users with role `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, or `RESIDENT`. `GUEST` gets 403 Forbidden.
  - `POST /api/v1/projects`, `PUT /api/v1/projects/{id}`, `DELETE /api/v1/projects/{id}`:
    Restricted to `ADMINISTRATOR` and `DIRECTOR`.
  - `POST /api/v1/projects/{id}/milestones`, `PUT /api/v1/projects/{id}/milestones/{milestone_id}`, `DELETE /api/v1/projects/{id}/milestones/{milestone_id}`:
    Restricted to `ADMINISTRATOR` and `DIRECTOR`.
  - `POST /api/v1/projects/{id}/updates`:
    Restricted to `ADMINISTRATOR`, `DIRECTOR`, and `MANAGER`.
  - `DELETE /api/v1/projects/{id}/updates/{update_id}`:
    Restricted to `ADMINISTRATOR` and `DIRECTOR`.

### Database Migration

- Alembic revision script creating `construction_project`, `project_milestone`, and `project_update` tables with appropriate indexes and cascade delete foreign keys.

### Frontend Layer (`frontend/src/features/construction-tracking/`)

1. **Types (`frontend/src/types/project.ts`)**:
   - `ProjectStatus`, `MilestoneStatus`
   - `ConstructionProject`, `ProjectMilestone`, `ProjectUpdate`, `ProjectDetail`
   - `ProjectCreatePayload`, `ProjectUpdatePayload`, `MilestoneCreatePayload`, `MilestoneUpdatePayload`, `ProjectUpdateCreatePayload`

2. **API Client (`frontend/src/api/projects.ts`)**:
   - `getProjects(params: { status?: ProjectStatus; skip?: number; limit?: number })`
   - `getProjectDetail(id: string)`
   - `createProject(payload: ProjectCreatePayload)`
   - `updateProject(id: string, payload: ProjectUpdatePayload)`
   - `deleteProject(id: string)`
   - `createMilestone(projectId: string, payload: MilestoneCreatePayload)`
   - `updateMilestone(projectId: string, milestoneId: string, payload: MilestoneUpdatePayload)`
   - `deleteMilestone(projectId: string, milestoneId: string)`
   - `createProjectUpdate(projectId: string, payload: ProjectUpdateCreatePayload)`
   - `deleteProjectUpdate(projectId: string, updateId: string)`

3. **React Hooks (`frontend/src/hooks/useProjects.ts`)**:
   - `useProjects(statusFilter, page, limit)`: TanStack Query hook with key `["projects", statusFilter, page]`.
   - `useProjectDetail(projectId)`: Query hook with key `["project", projectId]`.
   - `useCreateProject()`, `useUpdateProject()`, `useDeleteProject()`
   - `useCreateMilestone()`, `useUpdateMilestone()`, `useDeleteMilestone()`
   - `useCreateProjectUpdate()`, `useDeleteProjectUpdate()`

4. **UI Components (`frontend/src/features/construction-tracking/components/`)**:
   - `ConstructionTrackerPage.tsx`: Main page with header, status filter pills, "New Project" button (for Admin/Director), grid of `ProjectSummaryCard`, and drawer/view for project details.
   - `ProjectSummaryCard.tsx`: Card featuring cover image with fallback, title, contractor tag, status badge, physical progress circular gauge, and budget progress bar.
   - `BudgetVsActualProgressBar.tsx`: Financial component showing total budget vs executed budget, percentage executed, remaining amount, and amber/red badge when budget is exceeded.
   - `MilestoneTimeline.tsx`: Three-column or accordion workflow board for milestones organized into:
     - `DONE` (Feito — green badge, check icon, completed date)
     - `IN_PROGRESS` (Em Andamento — blue badge, clock icon, due date)
     - `NEXT_STEPS` (Próximos Passos — gray badge, calendar icon)
     Includes "Add Milestone" and edit/delete actions for Admin/Director.
   - `ProjectUpdateFeed.tsx`: Chronological log with author name, timestamp, rich text content, attached photo thumbnail carousel/grid with lightbox view, cost impact badge, and delete action for Admin/Director.
   - `ProjectFormModal.tsx`: Form modal with inputs for title, description, contractor name, total budget, executed budget, physical progress percentage slider (0-100), start/completion dates, status, and cover photo URL.
   - `MilestoneFormModal.tsx`: Form modal for milestone title, description, status, due date, completion date, and display order.
   - `ProjectUpdateModal.tsx`: Modal for adding progress log with title, content description, photo URL inputs, and optional cost impact.

5. **Navigation & Routing**:
   - Add `/projects` route to `App.tsx` wrapped with `ProtectedRoute` (allowed: `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `RESIDENT`).
   - Add "Obras" navigation item in `Navbar.tsx` visible to all authorized roles.

6. **i18n Localization**:
   - Add comprehensive keys to `frontend/src/i18n/locales/pt.json` and `en.json` under `projects.*`.

---

## Expected Results

- [ ] Database tables `construction_project`, `project_milestone`, and `project_update` are created via an Alembic migration with appropriate PKs, FKs (`ON DELETE CASCADE`), indexes, and check constraints.
- [ ] Enums `ProjectStatus` (`PLANNED`, `IN_PROGRESS`, `PAUSED`, `COMPLETED`) and `MilestoneStatus` (`DONE`, `IN_PROGRESS`, `NEXT_STEPS`) are defined and enforced.
- [ ] `POST /api/v1/projects` allows `ADMINISTRATOR` and `DIRECTOR` to create projects with valid budget, progress, contractor, and date attributes; returns `201 Created`.
- [ ] `GET /api/v1/projects` returns paginated list of projects, filterable by `status`, accessible to `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, and `RESIDENT`.
- [ ] `GET /api/v1/projects/{id}` returns complete project details with nested `milestones` and `updates` (including author metadata).
- [ ] `PUT /api/v1/projects/{id}` allows `ADMINISTRATOR` and `DIRECTOR` to update project details; returns `200 OK`.
- [ ] `DELETE /api/v1/projects/{id}` cascades deletion of related milestones and updates for `ADMINISTRATOR` and `DIRECTOR`; returns `204 No Content`.
- [ ] `POST /api/v1/projects/{id}/milestones`, `PUT /api/v1/projects/{id}/milestones/{milestone_id}`, and `DELETE /api/v1/projects/{id}/milestones/{milestone_id}` manage milestone states correctly with Admin/Director permission guards.
- [ ] `POST /api/v1/projects/{id}/updates` allows `ADMINISTRATOR`, `DIRECTOR`, and `MANAGER` to post progress updates with photo URLs and cost impact.
- [ ] `DELETE /api/v1/projects/{id}/updates/{update_id}` allows `ADMINISTRATOR` and `DIRECTOR` to remove updates.
- [ ] Unauthenticated requests or requests from `GUEST` users to `/api/v1/projects/*` are rejected with `401 Unauthorized` or `403 Forbidden`.
- [ ] Non-existent project, milestone, or update IDs return structured `404 Not Found` domain error responses.
- [ ] Frontend route `/projects` renders `ConstructionTrackerPage` displaying active construction projects, progress indicators, and budget metrics.
- [ ] `BudgetVsActualProgressBar` correctly calculates executed percentage and warns when executed budget exceeds total budget.
- [ ] `MilestoneTimeline` groups milestones by `DONE`, `IN_PROGRESS`, and `NEXT_STEPS` with action buttons displayed only for Admin/Director.
- [ ] `ProjectUpdateFeed` renders photo galleries and cost impacts for project updates.
- [ ] Project, Milestone, and Update creation/edit modals submit properly and invalidate TanStack Query caches.
- [ ] All user-facing UI text uses i18n keys in `pt.json` and `en.json`.
- [ ] Backend pytest suite passes with ≥ 90% test coverage for all new models, services, and endpoints.
- [ ] Frontend vitest suite passes with ≥ 75% test coverage for all new components and hooks.

---

## Out of Scope

- Direct integration with third-party accounting software or automated bank OFX reconciliation (handled separately in Domain 8 / T008).
- Direct automated bidding or quotation management with external contractors.
- Multi-currency conversion (all budgets and costs are modeled in BRL / standard float).
- Resident commenting/forum discussions on project updates (governed through the general Feedback / Contact channel in T011).
