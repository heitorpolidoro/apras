# Project Context & Purpose

**APRAS** — *Aplicativo de Planejamento e Resoluções para Associações e Síndicos* — is a web application for managing the administrative workload of homeowner associations (HOAs) and building managers ("síndicos" in Brazil).

## Problem Statement

Building administrators and HOA boards juggle dozens of operational tasks — maintenance requests, compliance follow-ups, vendor coordination — across spreadsheets, chat groups, and paper. APRAS centralises this into a structured, role-aware task management system with full auditability.

## Target Users

| Role            | Description                                                                                      |
|-----------------|--------------------------------------------------------------------------------------------------|
| **Administrador** (Administrator) | Full system access: manages users, categories, all tasks, and visibility settings.            |
| **Diretor** (Director)            | Can create, view, and edit any task; cannot manage users.                                      |
| **Gerente** (Manager)             | Sees tasks with no visibility targets, or at least one target matching one of the Manager's effective UserTypes; can edit only unassigned or self-assigned tasks. |
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
| `/dashboard`       | `TaskDashboard`        | `{module:"tasks"}` + the legacy `tasks` menu key |
| `/categories`      | `CategoriesPage`       | `{module:"categories"}` + the legacy `categories` menu key |
| `/admin/users`     | `AdminUserDashboard`   | `users:update`          |
| `/admin/groups`    | `GroupsAdminPage`      | any of `user_types:create/update/delete` |
| `/admin/groups/:groupId` | `GroupDetailPage`| the same rule           |

Since APRAS-48 every protected route's rule is one entry of
`ROUTE_ACCESS` (`frontend/src/features/user-administration/access/routeAccess.ts`),
passed as `ProtectedRoute`'s single `requiredAccess` prop and reused verbatim
by the matching `NAV_ITEMS` entry, so a menu and its route can never state
different rules. Authorization reads the **real** permission set
(`useCanAccess`); menus read the **simulated** one while an administrator is
"viewing as" (`useCanShowMenu`) — APRAS-35's invariant, restated over
permissions. A denied route renders `RestrictedAccessMessage` **in place** and
never redirects. Two `TRANSITIONAL (IAM F4 -> F5)` fields survive on exactly
two entries: `legacyMenu`, because `deps.assert_menu_access` still gates 12
handlers, and `landingRedirect`, the GUEST → `/welcome` / PORTEIRO → `/gate`
landing rule, which is not authorization.

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
| `/api/v1/tenants` | Tenants & membership | `backend/app/api/v1/endpoints/tenants.py` |
| `/api/v1/permissions` | Permission catalogue & effective set | `backend/app/api/v1/endpoints/permissions.py` |
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

### Tenant

One condominium/association installation, and the **tenant boundary** for
every other entity (APRAS-41). A `Tenant` has a globally unique `name` and an
`is_active` soft-deactivation flag; there is deliberately no delete endpoint,
because every tenant-scoped foreign key is `ON DELETE RESTRICT`.

**Membership.** A `User` is a *global* identity — `user.email` and `user.cpf`
stay unique across the whole install — and belongs to zero or more tenants
through the `user_tenant_link` join table. Multi-membership is first class:
only the same `(user, tenant)` pair twice is a conflict.

**Direct vs inherited scope.** A table carries its own `tenant_id` when a
tenant filter has to constrain it directly — i.e. it is reachable by a route
that lists it or fetches it by its own id without a scoped parent's id in the
path, or it has no NOT NULL FK to a scoped table. 27 tables are in that
group. The other 20 (`taskcomment`, `ballot`, `announcement_comment`, …)
**inherit** their tenant through a NOT NULL FK to a scoped parent and
deliberately carry no `tenant_id`: duplicating it would create a second,
forgeable source of truth that can disagree with the parent. The partition is
asserted mechanically in `backend/tests/test_tenant_models.py`, so a table
added by a future task cannot escape classification.

**Per-tenant uniqueness.** Constraints that would otherwise collide across
condominiums are keyed on `tenant_id`: `category.name`, `user_type.name`,
`user_type.role`, `lot.(block, lot_number)`, `occurrence.protocol_number`,
`reservable_space.name`, `asset.asset_tag` and
`finance_category.(name, type)`. `user.email`, `user.cpf`, `tenant.name` and
`access_device.device_key` stay global on purpose — the last of these
authenticates a hardware credential, so one condominium's device must not be
able to impersonate another's.

**The default tenant.** Migration `0028_add_tenant_and_membership` seeds a
single tenant with the fixed id `00000000-0000-0000-0000-000000000001` and
backfills every existing row and every existing user's membership into it.
The same literal is both the Python-side model default and each column's
`server_default`, which is what keeps pre-tenant code and tests working
unchanged.

**Tenant administrator.** `user_tenant_link.is_tenant_admin` (APRAS-43) is a
capability *layered on top of* `UserRole`, never a role of its own: it grants
**every permission in the catalogue**, inside the granting tenant only.
`deps.get_effective_permissions` returns `PERMISSIONS` for it (APRAS-47), and
returns only the user's own role/group bundles in every other tenant and with
no acting tenant. It lives on the membership row because a user is one global
identity in many tenants — a síndico who administers condominium A and merely
lives in B needs a different answer per tenant — and because a new `UserRole`
value would silently alter the 54 role comparisons spread across 22 service
modules.

* Read through `deps.is_acting_tenant_admin` / `deps.has_admin_capability`,
  which resolve the acting tenant from `session.info`. **No acting tenant
  grants nothing**: on a global route (every `/api/v1/tenants` route), in
  `app/seed.py`, in Alembic or in a unit-test `Session`, the capability is
  structurally absent.
* The seven tenant-scoped admin routes it reaches (users list/patch/contact-info,
  user-type create/patch/delete, task delete, lot delete) are gated by
  `deps.require_permission(...)` against the route's entry in
  `ROUTE_PERMISSIONS` (APRAS-46), not by a role guard. The capability exempts
  its holder from the UserType menu gate **within that tenant** exactly as a
  superuser is exempt everywhere.
* It grants the domain-service permissions (announcements, finance,
  occurrences, voting, …) inside the granting tenant. It does **not** grant
  per-lot `UserLotLink` access, or any tenant/membership management: granting
  and revoking it is
  `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}`, **superuser only**
  (`deps.get_current_superuser`).
* Privilege escalation is closed on `PATCH /api/v1/users/{id}` for every
  caller that is not a superuser: they may not grant the `ADMINISTRATOR`
  role, modify a superuser, or modify a user who holds a membership in
  another tenant. The user-visible detail strings still say "administrator" —
  deliberately, since `tests/test_user_directory_scope.py` asserts two of them
  literally and IAM F5 is the slice that retires the word. Do not "fix" the
  doc by renaming them.

**Install superuser.** `user.is_superuser` (APRAS-47, migration `0031`) is the
global counterpart of `is_tenant_admin`: every permission in **every** tenant
and with no acting tenant at all — `deps.get_effective_permissions` answers it
before any tenant is resolved. It is a column, not a role and not a group, so:

* it is **not grantable through the groups API** — the four permissions naming
  the superuser-gated routes are `SUPERUSER_ONLY_PERMISSIONS`
  (`tenants:create`, `tenants:update`, `tenants:members_manage`,
  `tenants:members_set_admin`), and `user_type_service.assert_can_grant`
  refuses them to every author, superuser included;
* it is **not settable through `UserUpdate`** — the schema has no
  `is_superuser` field, so a body carrying one is inert;
* it gates the five global `/api/v1/tenants` writes via
  `deps.get_current_superuser`, which reads the column and no role.
* **TRANSITIONAL (IAM F3 -> F5).** While `UserRole` still exists,
  `ADMINISTRATOR` and `is_superuser` are kept in lockstep: `User.__init__`
  defaults the flag for a new ADMINISTRATOR, migration `0031` set it for every
  pre-existing ADMINISTRATOR row, and `PATCH /api/v1/users/{id}` mirrors it on
  every role change. The column is nevertheless the single source of truth —
  a row stored with `role=ADMINISTRATOR, is_superuser=false` reads back as a
  non-superuser.

**The user directory is tenant-scoped.** `GET /api/v1/users/`,
`PATCH /api/v1/users/{id}` and `PATCH /api/v1/users/{id}/contact-info` target
the users visible in the acting tenant — linked to it, or link-less when it
is the default tenant (`app/services/user_service.py`). The filter is uniform
for **every** role: acting in tenant A, an `ADMINISTRATOR` gets 404 for a
B-only user exactly as a tenant_admin of A does, and reaches that user by
sending `X-Tenant-Id: B`. Global vision is a property of *sending the header*,
not of the role.

**The two permission reads.** `GET /api/v1/permissions/` returns the whole
static catalogue — one row per permission, pre-split into `module`, `action`
and `superuser_only` — and `GET /api/v1/permissions/me` returns
`{tenant_id, permissions[]}`, i.e. `deps.get_effective_permissions` for the
**acting tenant**, sorted (APRAS-48). The router is mounted `TENANT_SCOPED`,
so `/me` resolves its tenant through the same `get_current_tenant` ladder as
`/user-types/`; `/auth/me` is deliberately **not** the carrier, because it is
global (`GLOBAL_ROUTES`), so computing permissions there would answer the
*default* tenant's groups to a user acting in another one. Both routes are on
`UNGUARDED_ROUTES` — authenticated, self-scoped or data-free — which is what
keeps `ROUTE_PERMISSIONS` at 180 and
`backend/tests/data/parity_matrix_baseline.json` byte-identical. The frontend
consumes `/permissions/me` under the TanStack key `["me","permissions"]`; the
key does not start with `"tenants"`, so a tenant switch evicts and refetches
it with no reload.

**Not yet done.** `GET /api/v1/auth/me` stays global and returns the caller's
own `user_types` unfiltered, having no acting tenant to filter by.

### Task

The central entity. Represents an administrative work item (e.g., "Fix elevator in Block A", "Renew insurance policy"). A task has:

- **Title** (required) and optional **description**.
- **Status**: `PENDING` → `IN_PROGRESS` → `COMPLETED` (or `BLOCKED` / `CANCELED`).
- **Priority**: `LOW`, `MEDIUM`, `HIGH`, `URGENT`.
- **Category**: Optional colour-coded label for grouping (e.g., "Maintenance", "Legal").
- **Assignment**: A task can be assigned to a specific user (`assigned_to_id`).
- **Due Date**: Optional deadline.
- **Soft Delete**: Tasks are never physically deleted; `is_deleted` is set to `True`.
- **Visibility Targets** (`visible_to: list[UserType]`): Zero or more UserType targets a task is visible to. An empty list means the task is visible to every Manager (the same practical effect the old `null`/`manager_visible` state had); one or more targets restrict Manager visibility to Managers whose effective UserTypes intersect the list. Settable by Administrators, Directors, and self-scoped Managers (subject to the existing per-role rules for who may edit a given task).

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

This table is not exhaustive — e.g. it does not yet have a `RESIDENT` row (a pre-existing gap, unrelated to the UserType-menu-gate note below).

| Role            | Tasks                                           | Users & Categories       |
|-----------------|------------------------------------------------|--------------------------|
| `ADMINISTRATOR` | Full CRUD on all tasks; set/edit `visible_to` targets. Unconditionally exempt from the UserType menu gate below, in every tenant. Since APRAS-43 it is no longer the *only* exemption: a user holding `is_tenant_admin` on the acting tenant (see Tenant above) is exempt too, but only there — the capability is not a role and never applies outside the tenant that granted it. | Full user and category management, on the users visible in the acting tenant |
| `DIRECTOR`      | Full CRUD on all tasks; set/edit `visible_to` targets — **but only if at least one of the Director's assigned or role-linked UserTypes has `"tasks"`/`"categories"` in `allowed_menus`** (see UserType below). A Director with no qualifying UserType is blocked from Tarefas/Categorias entirely, same as any other non-Administrator role. | Can manage categories, subject to the same UserType gate |
| `MANAGER`       | Sees tasks with no `visible_to` targets, or at least one target matching one of their effective UserTypes; edit only unassigned or self-assigned tasks; may set/edit `visible_to` targets only as a subset of their own effective UserTypes. Also subject to the UserType menu gate (assigned or role-linked UserTypes). | Read-only on categories, subject to the UserType menu gate |
| `GUEST`         | No task access                                  | No access                |

### UserType

An administrator-managed label (e.g., "Board Member", "Building Staff") assigned to users for classification. Since APRAS-8, it also gates feature-level access via `allowed_menus: list[str]` (valid keys: `"tasks"`, `"categories"`): a non-Administrator user can access a gated menu only if at least one of their assigned UserTypes includes that key. This is an additional coarse gate layered in front of the existing role-based RBAC above, not a replacement for it — it does not affect fine-grained rules like `Task.visible_to` filtering or category write-role restrictions.

Since APRAS-9, one real `UserType` row is seeded per `UserRole` value (identified by a nullable, unique `role` column, e.g. "Diretor (papel)"), and a user's own role acts as an implicit UserType membership for every permission check — computed on every request via `get_effective_user_type_ids` (`backend/app/api/deps.py`), never stored as a row in the `UserUserTypeLink` join table, so a role change takes effect immediately. A user with no explicitly-assigned UserTypes falls back to the UserType implicitly linked to their own role (see APRAS-9); since that role-type starts with empty `allowed_menus`, the practical effect is the same until an Administrator configures it. Role-linked UserTypes can have their `allowed_menus` edited like any other UserType (restoring baseline-by-role access), but cannot be deleted or renamed-to-a-different-role via the API/UI — the `role` column is set once, at seed time, by the `0018_add_role_to_user_type` migration.

### Soft Delete

Tasks use logical deletion (`is_deleted = True`) rather than physical `DELETE` statements. The delete action is recorded in the audit history. Queries filter out soft-deleted records by default.

### Internationalisation (i18n)

All user-facing strings are externalised into JSON locale files (`en.json`, `pt.json`). The frontend uses `i18next` with automatic browser language detection and falls back to Portuguese (pt-BR) as the default language.

### JWT Authentication

The backend issues HS256-signed JWTs on login. Tokens encode the user's UUID as the `sub` claim and include `iat` (issued at) and `exp` (expiration) claims. The system supports **key rotation** by accepting tokens signed with any key in the `SECRET_KEYS` list (tried in order). The "remember me" option extends token life from the default 30 minutes to 7 days.










<!-- MERIDIAN_INSTRUCTIONS_START -->
# Meridian Instructions

> **AI Task Management**: If an AI agent needs to create, update, or read project tasks, it MUST go through the Meridian server first — the server owns the timestamps, so it is the only write path that keeps them consistent. Read with `GET http://localhost:3333/api/status?project=<absolute project path>`, create with `POST http://localhost:3333/api/projects/tasks`, update with `PUT http://localhost:3333/api/projects/tasks/<task id>` (both writes take `projectPath` in the JSON body). Only when the server is not running — the request fails to connect and `node cli.js start` is not an option — may an agent fall back to hand-editing `.meridian/tasks.json` directly, applying the timestamp rules below by hand.
> **File Shape**: `.meridian/tasks.json` is a bare JSON **array** of task objects. It is NOT an object with a `tasks` key. A task carries `id`, `title`, `status`, `priority`, `justification`, `expected_results`, `blockedBy`, `running`, `created_at`, `updated_at`, `moved_at` and `completed_at`. Never delete a task — move it to `nope` instead.
> **Timestamps**: ISO-8601 UTC strings. `created_at` is set once, on creation. `updated_at` is set on every write. `moved_at` is set on every status change. `completed_at` is set when the status enters `done` and set back to `null` when it leaves `done`. The server stamps all four; a hand-edit must reproduce them exactly.
> **Priority (`priority`)**: EXACTLY one of `critical`, `high`, `medium`, `low`. A task without one is read as `medium`.
> **Active Execution (`running`)**: boolean flag (`true`/`false`). Set to `true` when an agent starts actively working on a task, and set to `false` when finished or handed off.
> **Dependencies (`blockedBy`)**: optional array of task IDs that must reach `done` before this task can proceed. A task with a non-empty `blockedBy` whose dependencies aren't all `done` yet should have status `blocked` — that dependency is sufficient justification on its own (e.g. `justification: "Blocked on <task-id>"`). When every task in `blockedBy` reaches `done`, move this task back to `backlog`.
> **Allowed Statuses**: When assigning a status to a task, you MUST use EXACTLY one of the following lowercase strings. They carry no spaces and no slashes. DO NOT invent new statuses or use synonyms like 'pending', 'todo', 'completed', 'in progress' or 'qa/review'.
  - `backlog`: Task is planned but not ready to be worked on yet.
  - `spec_review`: Task needs specification or design review.
  - `ready_todo`: Task is fully specified and ready to be picked up.
  - `in_progress`: Task is currently being worked on by developer.
  - `code_review`: Task code is being reviewed for architecture, security, and test quality.
  - `qa_review`: Task is being verified independently by QA against expected results.
  - `blocked`: Task cannot proceed due to external dependencies.
  - `done`: Task is fully completed.
  - `nope`: Task was cancelled or won't be done.
> **Implementation Rule**: Before starting any implementation work, ask the user if they want to create a task for it in the Meridian system.
<!-- MERIDIAN_INSTRUCTIONS_END -->
