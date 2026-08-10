# Project Context & Purpose

**APRAS** — *Aplicativo de Planejamento e Resoluções para Associações e Síndicos* — is a web application for managing the administrative workload of homeowner associations (HOAs) and building managers ("síndicos" in Brazil).

## Problem Statement

Building administrators and HOA boards juggle dozens of operational tasks — maintenance requests, compliance follow-ups, vendor coordination — across spreadsheets, chat groups, and paper. APRAS centralises this into a structured, role-aware task management system with full auditability.

## Target Users

| Role            | Description                                                                                      |
|-----------------|--------------------------------------------------------------------------------------------------|
| **Administrador** (Administrator) | Full system access: manages users, categories, all tasks, and visibility settings.            |
| **Diretor** (Director)            | Can create, view, and edit any task; cannot manage users.                                      |
| **Gerente** (Manager)             | Sees only tasks explicitly marked as `manager_visible`; can edit only unassigned or self-assigned tasks. |
| **Convidado** (Guest)             | Read-only role (effectively blocked from task interaction).                                    |

## Key Capabilities

- Task CRUD with status, priority, category, assignment, and due-date tracking.
- Role-Based Access Control (RBAC) with four tiers of permissions.
- Full audit trail — every field-level change on a task is recorded in a `TaskHistory` timeline.
- Per-task comment threads.
- Soft-delete for tasks (logical deletion with `is_deleted` flag).
- Internationalisation (pt-BR and en) via i18next.
- Category management with colour-coded labels.
- User-type labels (admin-managed classification of users).

## Production URLs

| Surface  | URL                                  |
|----------|--------------------------------------|
| Frontend | https://apras-front.vercel.app       |
| Backend  | https://apras-back.vercel.app        |

---

# High-level Architecture

```
┌──────────────────┐        HTTPS/JSON        ┌─────────────────────┐
│                  │  ──────────────────────▶  │                     │
│   React SPA      │  VITE_API_URL             │   FastAPI Backend   │
│   (Vite + TS)    │  /api/v1/*                │   (Python 3.13)     │
│                  │  ◀──────────────────────  │                     │
└──────────────────┘                           └────────┬────────────┘
                                                        │
                                                        │ SQLModel / SQLAlchemy
                                                        │ (psycopg2-binary)
                                                        ▼
                                               ┌─────────────────────┐
                                               │   PostgreSQL 16     │
                                               └─────────────────────┘
```

## Frontend (React SPA)

- Single-page application served by Vite; deployed as a static site on **Vercel** (`apras-front`).
- Client-side routing with `react-router-dom`. Root `/` redirects to `/dashboard`.
- Authentication state managed via React Context (`AuthContext`), JWT stored in `sessionStorage` or `localStorage` (depending on "remember me").
- All API calls go through a centralised Axios client (`src/api/client.ts`) that auto-attaches the `Bearer` token and an optional Vercel protection bypass header.
- Server-state caching and mutations handled by **TanStack Query** (`useQuery` / `useMutation`).

### Route Map

| Route              | Component              | Access                  |
|--------------------|------------------------|-------------------------|
| `/login`           | `LoginPage`            | Public                  |
| `/signup`          | `SignupPage`           | Public                  |
| `/dashboard`       | `TaskDashboard`        | Authenticated           |
| `/categories`      | `CategoriesPage`       | Authenticated           |
| `/admin/users`     | `AdminUserDashboard`   | Administrator only      |

## Backend (FastAPI)

- RESTful API under the `/api/v1` prefix, deployed as a serverless function on **Vercel** (`apras-back`).
- Authentication via JWT (HS256) with bcrypt password hashing. Supports key rotation through `SECRET_KEYS` list.
- Rate limiting via `slowapi`.
- Database migrations managed by **Alembic**.
- Business logic encapsulated in service classes (`TaskService`, `CategoryService`), separate from route handlers.
- Domain errors are raised as typed exceptions (`DomainError`, `TaskNotFoundError`, `ForbiddenError`) and caught by global exception handlers.

### API Endpoints (v1)

| Prefix           | Resource        | File                                     |
|------------------|-----------------|------------------------------------------|
| `/api/v1/auth`   | Authentication  | `backend/app/api/v1/endpoints/auth.py`   |
| `/api/v1/tasks`  | Tasks           | `backend/app/api/v1/endpoints/tasks.py`  |
| `/api/v1/users`  | Users           | `backend/app/api/v1/endpoints/users.py`  |
| `/api/v1/categories` | Categories  | `backend/app/api/v1/endpoints/categories.py` |
| `/api/v1/user-types` | User Types  | `backend/app/api/v1/endpoints/user_types.py` |
| `/api/v1/health` | Health check    | `backend/app/api/v1/api.py`              |

## Data Layer

- **ORM**: SQLModel (Pydantic + SQLAlchemy hybrid). Models define both the database table and the Pydantic schema in one class.
- **Database**: PostgreSQL 16 (Vercel Postgres in production; local via Docker at port `5436`).
- **Migrations**: Alembic with `env.py` wired to a non-pooling connection URL for safe DDL.

## CI/CD

- **GitHub Actions** — `ci.yml` runs backend tests (pytest, 90% coverage gate) and frontend tests (Vitest, 75% coverage gate) on every push/PR.
- **Migrate** — `migrate.yml` runs Alembic migrations on push to `master`.
- **Release** — `release.yml` handles semantic versioning and releases.
- **Static Analysis** — SonarCloud and DeepSource are integrated for code quality and security scanning.
- **Deploy** — Automatic production deploy on merge to `master` via Vercel Git integration for both projects.

---

# Key Technologies & Stack

## Backend

| Category              | Technology                                         |
|-----------------------|----------------------------------------------------|
| Language              | Python 3.13                                        |
| Framework             | FastAPI ≥ 0.136                                    |
| ORM                   | SQLModel ≥ 0.0.38 (SQLAlchemy under the hood)      |
| Database              | PostgreSQL 16                                      |
| DB Driver             | psycopg2-binary                                    |
| Migrations            | Alembic ≥ 1.18                                     |
| Authentication        | PyJWT (HS256), passlib + bcrypt                    |
| Settings              | pydantic-settings (`.env` driven)                  |
| Validation            | email-validator, python-multipart                  |
| Rate Limiting         | slowapi                                            |
| ASGI Server           | Uvicorn                                            |
| Package Manager       | uv                                                 |
| Linting               | Ruff (all rules selected; line-length 88)          |
| Testing               | pytest + pytest-cov, httpx (async test client)     |

## Frontend

| Category              | Technology                                         |
|-----------------------|----------------------------------------------------|
| Language              | TypeScript ~6.0                                    |
| UI Framework          | React 19                                           |
| Build Tool            | Vite 8                                             |
| Styling               | Tailwind CSS 4 + `@tailwindcss/vite` plugin        |
| Component Primitives  | Radix UI (label, select, slot)                     |
| Variant Utility       | class-variance-authority, clsx, tailwind-merge     |
| Icons                 | Lucide React                                       |
| HTTP Client           | Axios                                              |
| Server-state          | TanStack Query 5                                   |
| Routing               | react-router-dom 7                                 |
| i18n                  | i18next + react-i18next + browser language detector |
| Testing               | Vitest 4 + @testing-library/react + jsdom          |
| Linting               | ESLint 9 + typescript-eslint                       |

## Infrastructure & DevOps

| Category              | Technology                                         |
|-----------------------|----------------------------------------------------|
| Hosting               | Vercel (both frontend and backend)                 |
| Containerisation      | Docker + Docker Compose                            |
| CI/CD                 | GitHub Actions                                     |
| Code Quality          | SonarCloud, DeepSource                             |
| Source Control         | Git (GitHub)                                       |

---

# Directory Structure

```
apras/
├── backend/                        # Python backend application
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory, middleware, CORS
│   │   ├── db.py                   # SQLModel engine & session dependency
│   │   ├── seed.py                 # Database seeding script
│   │   ├── api/
│   │   │   ├── deps.py             # Auth dependencies (get_current_user, RBAC guards)
│   │   │   └── v1/
│   │   │       ├── api.py          # APIRouter aggregator + /health endpoint
│   │   │       └── endpoints/
│   │   │           ├── auth.py     # Login, signup, token refresh
│   │   │           ├── tasks.py    # Task CRUD, comments, history
│   │   │           ├── users.py    # User listing and admin management
│   │   │           ├── categories.py # Category CRUD
│   │   │           └── user_types.py # User-type label CRUD
│   │   ├── core/
│   │   │   ├── config.py           # Settings class (env vars, DB URL, JWT config)
│   │   │   ├── security.py         # JWT creation/validation, password hashing
│   │   │   ├── limiter.py          # Slowapi rate limiter instance
│   │   │   ├── exceptions.py       # Custom domain exception classes
│   │   │   └── exception_handlers.py # Global FastAPI exception handlers
│   │   ├── models/
│   │   │   ├── enums.py            # TaskStatus, TaskPriority, UserRole
│   │   │   ├── task.py             # Task, TaskComment, TaskHistory (SQLModel)
│   │   │   ├── user.py             # User model
│   │   │   ├── category.py         # Category model
│   │   │   └── user_type.py        # UserType model
│   │   ├── schemas/
│   │   │   ├── task.py             # TaskCreate, TaskUpdate, TaskRead, etc.
│   │   │   ├── user.py             # UserCreate, UserRead, UserUpdate
│   │   │   ├── category.py         # CategoryCreate, CategoryRead
│   │   │   ├── user_type.py        # UserTypeCreate, UserTypeRead
│   │   │   └── token.py            # Token response schema
│   │   └── services/
│   │       ├── task_service.py     # Task business logic (CRUD, history, comments)
│   │       └── category_service.py # Category business logic
│   ├── alembic/                    # Database migration scripts
│   │   ├── env.py
│   │   └── versions/               # Individual migration files
│   ├── tests/                      # Pytest test suite (24 test modules)
│   │   ├── conftest.py             # Shared fixtures (in-memory DB, test client)
│   │   ├── test_tasks_rbac.py      # RBAC permission tests for tasks
│   │   ├── test_categories.py      # Category endpoint tests
│   │   └── ...
│   ├── pyproject.toml              # Python project config (deps, ruff, coverage)
│   ├── alembic.ini                 # Alembic configuration
│   ├── Dockerfile                  # Backend container image
│   └── vercel.json                 # Vercel serverless function config
│
├── frontend/                       # React SPA
│   ├── src/
│   │   ├── App.tsx                 # Root component with routing
│   │   ├── main.tsx                # React entry point (QueryClient, i18n init)
│   │   ├── index.css               # Global styles and Tailwind directives
│   │   ├── api/
│   │   │   ├── client.ts           # Axios instance with auth interceptor
│   │   │   └── errors.ts           # Standardised error handling
│   │   ├── types/
│   │   │   └── auth.ts             # User, UserRole, UserType interfaces
│   │   ├── hooks/
│   │   │   └── useUsers.ts         # User data fetching hook
│   │   ├── components/
│   │   │   └── ui/                 # Shared UI primitives (button, input, badge, etc.)
│   │   ├── features/
│   │   │   ├── task-management/
│   │   │   │   ├── components/     # TaskDashboard, TaskBoard, TaskCard, TaskForm,
│   │   │   │   │                   # TaskList, TaskDetailsView, AuditTimeline,
│   │   │   │   │                   # TaskComments, CategoriesPage
│   │   │   │   ├── hooks/          # useTasks, useCategories, useTaskFiltering
│   │   │   │   ├── types/          # Task, Category, TaskHistory TS interfaces
│   │   │   │   └── utils/          # taskUtils.ts (status/priority helpers)
│   │   │   └── user-administration/
│   │   │       ├── components/     # Navbar, ProtectedRoute
│   │   │       ├── context/        # AuthContext (login state, token management)
│   │   │       └── pages/          # LoginPage, SignupPage, AdminUserDashboard
│   │   ├── i18n/
│   │   │   ├── index.ts            # i18next initialisation
│   │   │   └── locales/
│   │   │       ├── en.json         # English translations
│   │   │       └── pt.json         # Portuguese (Brazil) translations
│   │   ├── lib/
│   │   │   └── utils.ts            # Generic utility functions (cn helper)
│   │   └── test/                   # Test setup and helpers
│   ├── package.json                # Node dependencies and scripts
│   ├── vite.config.ts              # Vite build configuration
│   ├── vitest.config.ts            # Vitest test configuration
│   ├── tsconfig.json               # TypeScript configuration
│   ├── eslint.config.js            # ESLint configuration
│   ├── components.json             # shadcn/ui component config
│   ├── Dockerfile                  # Frontend container image
│   └── vercel.json                 # Vercel SPA rewrite rules
│
├── docker-compose.yml              # Full local dev environment (db + backend + frontend)
├── sonar-project.properties        # SonarCloud analysis configuration
├── package.json                    # Root scripts (Vercel preview deploys)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # Main CI pipeline (tests + coverage gates)
│   │   ├── migrate.yml             # Alembic migration runner on merge to master
│   │   ├── release.yml             # Automated release workflow
│   │   └── gemini-*.yml            # AI-assisted triage, review, and dispatch workflows
│   └── CODEOWNERS
└── docs/                           # Project documentation
```

---

# Domain Concepts

### Task

The central entity. Represents an administrative work item (e.g., "Fix elevator in Block A", "Renew insurance policy"). A task has:

- **Title** (required) and optional **description**.
- **Status**: `PENDING` → `IN_PROGRESS` → `COMPLETED` (or `BLOCKED` / `CANCELED`).
- **Priority**: `LOW`, `MEDIUM`, `HIGH`, `URGENT`.
- **Category**: Optional colour-coded label for grouping (e.g., "Maintenance", "Legal").
- **Assignment**: A task can be assigned to a specific user (`assigned_to_id`).
- **Due Date**: Optional deadline.
- **Soft Delete**: Tasks are never physically deleted; `is_deleted` is set to `True`.
- **Manager Visibility** (`manager_visible`): Controls whether users with the Manager role can see this task. Only Administrators and Directors can toggle this flag.

### TaskHistory (Audit Trail)

Every field-level change on a `Task` creates a `TaskHistory` record capturing the field name, old value, new value, who made the change, and when. This powers the **AuditTimeline** component on the frontend. When the changed field is `assigned_to_id`, the service resolves the raw UUID to a `{name, role}` object for display.

### TaskComment

Free-text comments attached to a task, threaded chronologically. Each comment records its author and timestamps.

### Category

An administrator-defined label with a display **name** and **hex colour**. Tasks can optionally belong to one category. Categories have an `is_active` flag for soft deactivation.

### User

An authenticated actor in the system. Fields include email (used as login), full name, hashed password, active flag, and **role**. Users can optionally be classified under a **UserType**.

### UserRole (RBAC)

The permission model is a four-tier enum:

| Role            | Tasks                                           | Users & Categories       |
|-----------------|------------------------------------------------|--------------------------|
| `ADMINISTRATOR` | Full CRUD on all tasks; toggle `manager_visible` | Full user and category management |
| `DIRECTOR`      | Full CRUD on all tasks; toggle `manager_visible` | Can manage categories    |
| `MANAGER`       | View only `manager_visible` tasks; edit only unassigned or self-assigned tasks; cannot toggle visibility | Read-only on categories  |
| `GUEST`         | No task access                                  | No access                |

### UserType

An administrator-managed label (e.g., "Board Member", "Building Staff") that can be assigned to users for classification purposes. Not tied to permissions — purely informational.

### Soft Delete

Tasks use logical deletion (`is_deleted = True`) rather than physical `DELETE` statements. The delete action is recorded in the audit history. Queries filter out soft-deleted records by default.

### Internationalisation (i18n)

All user-facing strings are externalised into JSON locale files (`en.json`, `pt.json`). The frontend uses `i18next` with automatic browser language detection and falls back to Portuguese (pt-BR) as the default language.

### JWT Authentication

The backend issues HS256-signed JWTs on login. Tokens encode the user's UUID as the `sub` claim and include `iat` (issued at) and `exp` (expiration) claims. The system supports **key rotation** by accepting tokens signed with any key in the `SECRET_KEYS` list (tried in order). The "remember me" option extends token life from the default 30 minutes to 7 days.




<!-- MERIDIAN_INSTRUCTIONS_START -->
# Meridian Instructions

> **AI Task Management**: If an AI agent needs to create, update, or read project tasks, they MUST directly parse and modify the `.meridian/tasks.json` file (A JSON object with a `tasks` array containing tasks with id, title, status, justification).
> **Allowed Statuses**: When assigning a status to a task, you MUST use EXACTLY one of the following lowercase strings. DO NOT invent new statuses or use synonyms like 'pending', 'todo', or 'completed'.
  - `backlog`: Task is planned but not ready to be worked on yet.
  - `specreview`: Task needs specification or design review.
  - `readytodo`: Task is fully specified and ready to be picked up.
  - `inprogress`: Task is currently being worked on.
  - `qareview`: Task is done and waiting for QA or code review.
  - `blocked`: Task cannot proceed due to external dependencies.
  - `done`: Task is fully completed.
  - `nope`: Task was cancelled or won't be done.
> **Implementation Rule**: Before starting any implementation work, ask the user if they want to create a task for it in the Meridian system.
<!-- MERIDIAN_INSTRUCTIONS_END -->
