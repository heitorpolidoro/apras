# Project Context & Purpose

**APRAS** — *Aplicativo de Planejamento e Resoluções para Associações e Síndicos* — is a web application for managing the administrative workload of homeowner associations (HOAs) and building managers ("síndicos" in Brazil).

## Problem Statement

Building administrators and HOA boards juggle dozens of operational tasks — maintenance requests, compliance follow-ups, vendor coordination — across spreadsheets, chat groups, and paper. APRAS centralises this into a structured, role-aware task management system with full auditability.

## Target Users

| Role            | Description                                                                                      |
|-----------------|--------------------------------------------------------------------------------------------------|
| **Administrador** (Administrator) | Full system access: manages users, categories, all tasks, and visibility settings.            |
| **Diretor** (Director)            | Can create, view, and edit any task; cannot manage users.                                      |
| **Gerente** (Manager)             | Sees tasks with no visibility targets, or at least one target matching one of the Manager's roles; can edit only unassigned or self-assigned tasks. |
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
- Client-side routing with `react-router-dom`. Root `/` resolves through
  `RootRedirect`'s fallback chain (APRAS-39 §10.4): the caller's
  `landing_path` if its route is accessible → `/dashboard` if accessible →
  the first `NAV_ITEMS` entry they may see, in declaration order → `/welcome`.
  The chain exists because a tenant with `tasks` turned off would otherwise
  strand everyone on a restricted `/dashboard`.
- Authentication state managed via React Context (`AuthContext`), JWT stored in `sessionStorage` or `localStorage` (depending on "remember me").
- All API calls go through a centralised Axios client (`src/api/client.ts`) that auto-attaches the `Bearer` token and an optional Vercel protection bypass header.
- Server-state caching and mutations handled by **TanStack Query** (`useQuery` / `useMutation`).

### Route Map

| Route              | Component              | Access                  |
|--------------------|------------------------|-------------------------|
| `/login`           | `LoginPage`            | Public                  |
| `/signup`          | `SignupPage`           | Public                  |
| `/dashboard`       | `TaskDashboard`        | `{module:"tasks"}`      |
| `/categories`      | `CategoriesPage`       | `{module:"categories"}` |
| `/admin/users`     | `AdminUserDashboard`   | `users:update`          |
| `/admin/roles`     | `RolesAdminPage`       | any of `roles:create/update/delete` |
| `/admin/roles/:roleId` | `RoleDetailPage`   | the same rule           |
| `/admin/modules`   | `TenantModulesPage`    | `{superuser:true}`      |
| `/infractions`     | `InfractionsPage`      | any of `infractions:read` |
| `/infraction-rules`| `InfractionRulesPage`  | any of `infractions:rule_create/rule_update/rule_deactivate` |
| `/my-infractions`  | `MyInfractionsPage`    | any of `infractions:my_lots_read` |

Since APRAS-48 every protected route's rule is one entry of
`ROUTE_ACCESS` (`frontend/src/features/user-administration/access/routeAccess.ts`),
passed as `ProtectedRoute`'s single `requiredAccess` prop and reused verbatim
by the matching `NAV_ITEMS` entry, so a menu and its route can never state
different rules. APRAS-39 added a third rule shape, `{superuser:true}`, for
`/admin/modules`: it is the first frontend surface for a superuser-only
*backend* route, and such routes carry no catalogue permission, so no
`{anyOf}` rule could express it. The flag is read from the **real** auth user
and is never simulated, so "view-as" cannot open an operator screen.

Authorization reads the **real** permission set (`useCanAccess`); menus read
the **simulated** one while an administrator is "viewing as"
(`useCanShowMenu`) — APRAS-35's invariant, restated over permissions. A denied
route renders `RestrictedAccessMessage` **in place** and never redirects; since
APRAS-39 that component has a second, purely presentational variant for a
route whose module the tenant has turned off (`common.moduleUnavailable`).
One field survives, on exactly two entries — `/dashboard` and `/categories`:
`landingRedirect`, which sends a caller carrying a `landing_path` preference
(GUEST → `/welcome`, PORTEIRO → `/gate`) to it instead. It is a preference,
not authorization, which is why it lives on the role row. Since APRAS-39 it
fires **only when the landing target is itself accessible**: a PORTEIRO whose
tenant has `gate` turned off stays where `RootRedirect`'s chain put them
rather than being bounced onto a screen that would refuse them. Its sibling
`legacyMenu` died together with `deps.assert_menu_access`, which IAM F5
deleted.

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
| `/api/v1/roles`  | Roles           | `backend/app/api/v1/endpoints/roles.py`  |
| `/api/v1/tenants` | Tenants & membership | `backend/app/api/v1/endpoints/tenants.py` |
| `/api/v1/permissions` | Permission catalogue & effective set | `backend/app/api/v1/endpoints/permissions.py` |
| `/api/v1/tenants/{id}/modules` | Per-tenant module switch (`GET`/`PUT`, superuser only) | `backend/app/api/v1/endpoints/tenants.py` |
| `/api/v1/subscription` | Tenant-side subscription area (`GET`, `PUT /modules`, `GET /history`) | `backend/app/api/v1/endpoints/subscription.py` |
| `/api/v1/plans` | Install-wide plan catalogue (`GET`/`POST`/`GET {id}`/`PATCH {id}`, superuser only) | `backend/app/api/v1/endpoints/plans.py` |
| `/api/v1/tenants/{id}/subscription` | Per-tenant subscription read and plan assignment (`GET`/`PUT`, superuser only) | `backend/app/api/v1/endpoints/tenants.py` |
| `/api/v1/tenants/{id}/subscription/courtesy` | Courtesy grants outside the plan (`PUT`, superuser only) | `backend/app/api/v1/endpoints/tenants.py` |
| `/api/v1/infraction-rules` | Infraction rule catalogue and its escalation policy (`GET`/`POST`/`GET {id}`/`PUT {id}`/`DELETE {id}` soft-deactivates/`PUT {id}/policy`), plus `/api/v1/infraction-settings` (`GET`/`PUT`) | `backend/app/api/v1/endpoints/infractions.py` |
| `/api/v1/infractions` | The infraction process: list, detail, next-step suggestion, promotion from an occurrence, stage append, contestation and recidivism-cycle closes | `backend/app/api/v1/endpoints/infractions.py` |
| `/api/v1/health` | Health check    | `backend/app/api/v1/api.py`              |

## Data Layer

- **ORM**: SQLModel (Pydantic + SQLAlchemy hybrid). Models define both the database table and the Pydantic schema in one class.
- **Database**: PostgreSQL 16 (Vercel Postgres in production; local via Docker at port `5436`).
- **Migrations**: Alembic with `env.py` wired to a non-pooling connection URL for safe DDL.

### Running the Postgres migration tests locally

`backend/tests/test_migrations_postgres.py` needs a real Postgres it is
allowed to destroy: every fixture runs `DROP SCHEMA public CASCADE` and
re-runs the Alembic chain. **Never point `TEST_POSTGRES_URL` at the dev
database on 5436** — it will be emptied. The database must be **UTF-8**:
migration `0028` seeds `Condomínio Padrão`.

**initdb (no Docker needed — the dev machine's Docker disk is often full):**

```bash
export PGDATA=/tmp/apras-pgtest PGPORT=55432
initdb -U postgres -E UTF8 --locale=C "$PGDATA"
pg_ctl -D "$PGDATA" -o "-p $PGPORT" -l /tmp/apras-pgtest.log start
createdb -h localhost -p "$PGPORT" -U postgres apras_test

cd backend && TEST_POSTGRES_URL=postgresql://postgres@localhost:55432/apras_test \
  SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v

pg_ctl -D "$PGDATA" stop && rm -rf "$PGDATA"
```

**Docker, when it has disk:**

```bash
docker run -d --rm -p 55432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=apras_test \
  -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C" postgres:16-alpine

cd backend && TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:55432/apras_test \
  SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v
```

Check what you got with `psql "$TEST_POSTGRES_URL" -tAc "SHOW server_encoding"`
— it must print `UTF8`. Two known divergences, both deliberate: Homebrew's
`initdb` on this machine is **PostgreSQL 14** while CI and `docker-compose.yml`
are **16**; and the CI job and both recipes above use `--locale=C`, while
`docker-compose.yml`'s `db` sets no `POSTGRES_INITDB_ARGS` and so gets
`en_US.utf8` collation. Nothing in the module asserts a collation-dependent
ordering today, but a test that starts to must account for the difference.
For anything that turns on version- or collation-specific catalog behaviour,
use the Docker recipe (or `brew install postgresql@16`) and treat the CI job
as the source of truth.

## CI/CD

- **GitHub Actions** — `ci.yml` runs backend tests (pytest, 90% coverage gate) and frontend tests (Vitest, 75% coverage gate) on every push/PR.
- **Migration tests** — `ci.yml`'s `backend-migrations` job runs
  `backend/tests/test_migrations_postgres.py` against a throwaway
  **Postgres 16 (UTF-8)** service container. The module self-skips wherever
  `TEST_POSTGRES_URL` is unset, so **CI is the source of truth** for it; a
  guard step fails the job if the module reports any skip or fewer than 53
  cases, because a fully-skipped run exits 0. `ci.yml` also accepts
  `workflow_dispatch`, so any branch can be run manually with
  `gh workflow run ci.yml --ref <branch>`.
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
│   │   │           └── roles.py     # Role CRUD
│   │   ├── core/
│   │   │   ├── config.py           # Settings class (env vars, DB URL, JWT config)
│   │   │   ├── security.py         # JWT creation/validation, password hashing
│   │   │   ├── limiter.py          # Slowapi rate limiter instance
│   │   │   ├── exceptions.py       # Custom domain exception classes
│   │   │   └── exception_handlers.py # Global FastAPI exception handlers
│   │   ├── models/
│   │   │   ├── enums.py            # TaskStatus, TaskPriority, …
│   │   │   ├── task.py             # Task, TaskComment, TaskHistory (SQLModel)
│   │   │   ├── user.py             # User model
│   │   │   ├── category.py         # Category model
│   │   │   └── role.py             # Role model
│   │   ├── schemas/
│   │   │   ├── task.py             # TaskCreate, TaskUpdate, TaskRead, etc.
│   │   │   ├── user.py             # UserCreate, UserRead, UserUpdate
│   │   │   ├── category.py         # CategoryCreate, CategoryRead
│   │   │   ├── role.py             # RoleCreate, RoleRead
│   │   │   └── token.py            # Token response schema
│   │   └── services/
│   │       ├── task_service.py     # Task business logic (CRUD, history, comments)
│   │       └── category_service.py # Category business logic
│   ├── alembic/                    # Database migration scripts
│   │   ├── env.py
│   │   └── versions/               # Individual migration files
│   ├── scripts/                    # CI helpers (not product code, not collected)
│   │   └── assert_no_skips.py      # Fails the migration job if its cases skipped
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
│   │   │   └── auth.ts             # User, Role interfaces
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
│   │   ├── ci.yml                  # Main CI pipeline (tests, coverage gates, Postgres migration job)
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
path, or it has no NOT NULL FK to a scoped table. **28** tables are in that
group — APRAS-41's 27 plus `tenant_subscription` (APRAS-40), the first one
added after migration `0028`. The other **21** (`taskcomment`, `ballot`,
`announcement_comment`, `subscription_change`, …) **inherit** their tenant
through a NOT NULL FK to a scoped parent and deliberately carry no
`tenant_id`: duplicating it would create a second, forgeable source of truth
that can disagree with the parent. Four tables are **unscoped** — `user`,
`tenant`, `user_tenant_link` and `plan` (the install-wide commercial
catalogue) — for 53 in all. The partition is asserted mechanically in
`backend/tests/test_tenant_models.py`, so a table added by a future task
cannot escape classification.

Migration `0028`'s own `_TENANT_SCOPED_TABLES` literal is **frozen history**
and records only what that migration scoped; a directly-scoped table added
later registers in `POST_0028_SCOPED_TABLES`
(`backend/tests/test_tenant_models.py`) and in `TENANT_SCOPED_TABLES`
(`backend/tests/test_migrations_postgres.py`, an exact-set assertion against
the live schema), and must name its tenant FK `fk_<table>_tenant_id` to satisfy
`test_every_scoped_table_has_the_four_properties`.

**Per-tenant uniqueness.** Constraints that would otherwise collide across
condominiums are keyed on `tenant_id`: `category.name`, `role.name`,
`lot.(block, lot_number)`, `occurrence.protocol_number`,
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
capability, never a role: it grants **every permission in the catalogue**,
inside the granting tenant only. `deps.get_effective_permissions` returns
`PERMISSIONS` for it (APRAS-47), and returns only the user's own role bundles
in every other tenant and with no acting tenant. It lives on the membership
row because a user is one global identity in many tenants — a síndico who
administers condominium A and merely lives in B needs a different answer per
tenant.

* Read through `deps.is_acting_tenant_admin`, which resolves the acting
  tenant from `session.info`. **No acting tenant grants nothing**: on a
  global route (every `/api/v1/tenants` route), in `app/seed.py`, in Alembic
  or in a unit-test `Session`, the capability is structurally absent.
* The seven tenant-scoped admin routes it reaches (users list/patch/contact-info,
  role create/patch/delete, task delete, lot delete) are gated by
  `deps.require_permission(...)` against the route's entry in
  `ROUTE_PERMISSIONS` (APRAS-46), not by a role guard.
* It grants the domain-service permissions (announcements, finance,
  occurrences, voting, …) inside the granting tenant. It does **not** grant
  per-lot `UserLotLink` access, or any tenant/membership management: granting
  and revoking it is
  `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}`, **superuser only**
  (`deps.get_current_superuser`).
* Privilege escalation is closed on `PATCH /api/v1/users/{id}` for every
  caller that is not a superuser: they may not modify a superuser, or modify
  a user who holds a membership in another tenant. Since APRAS-49 there is no
  third rule to state — `UserUpdate` carries neither `role` nor
  `is_superuser`, so `role_ids` is the only field that can widen anyone and
  `role_service.assert_can_assign_roles` already guards it. The user-visible
  detail strings still say "administrator"; they are legacy wording,
  asserted literally by `tests/test_user_directory_scope.py`. Do not "fix"
  the doc by renaming them.

### Módulos por tenant

A per-tenant **feature switch** (APRAS-39) that composes with the permission
model by *stripping*, never by replacing. The 28 modules are exactly the
`<module>` segments of the catalogue (`permissions.MODULES`, derived and never
hand-listed, so a module a future task adds is toggleable the day its first
permission exists — `infractions` in `APRAS-44` is the first to arrive that
way, with no edit to this switch at all). **Four** of them are `CORE_MODULES`
and can never be turned off — `tenants`, `users`, `roles`, `billing` — because
a condominium without identity, membership, the authorization vocabulary or
the surface it contracts modules from could not administer itself back into
existence. The other **24** are the billable features.

**Storage is negative.** `tenant.disabled_modules` (portable `JSON`,
`NOT NULL DEFAULT '[]'`, migration `0034`) lists what is *off*, so `[]` means
"everything on": the column's `server_default` is the all-on backfill for
every existing tenant, a new tenant is all-on with no seeding, and a module a
future task adds is active everywhere with no data step. What it gives up,
stated so it is not rediscovered: no efficient "which tenants have `finance`
on" query. (The missing audit row is no longer missing: `APRAS-40` records
every write to this column, including the raw superuser one, as a
`subscription_change` — see *Assinatura e planos*.)

**Three writers, one column, one reader.** The superuser `PUT` below is now
one of **three** routes that write `disabled_modules`: it is the *raw lever*,
deliberately unbounded by the subscription so it stays the operator's repair
tool, beside `APRAS-40`'s ceiling-constrained tenant-side contracting `PUT`
and its entitlement-expanding courtesy `PUT`. The **reader** is still exactly
`deps.get_effective_permissions`, and `APRAS-40` adds no line to it. See
*Assinatura e planos*.

**One enforcement point.** `deps.get_effective_permissions` returns the user's
authority **minus** every string whose module the acting tenant turned off.
Route guards, the in-handler `has_permission` checks, the object-level
`SCOPE_PERMISSIONS` predicates, every service-level check and
`GET /api/v1/permissions/me` — hence the frontend menu and the frontend routes
— all follow from that one function. There is no registry mapping routes to
modules that a new endpoint could forget to join, and no second mechanism.

* **The single exception is the grant surface.** `role_service.assert_can_grant`
  (and `assert_can_assign_roles`, which delegates to it) compares against
  `deps.get_grantable_permissions` — the same authority, **unstripped**. The
  guard validates the *whole resulting bundle*, and four of the six seeded
  roles carry `finance:read`, so a stripped comparison would 403 a pure
  *rename* of any of them in a tenant with `finance` off: role and membership
  administration in that tenant would freeze. Nothing escalates, because a
  grant can never exceed what the author holds with every module on — which is
  exactly what they will hold when the operator re-enables it — and the
  grantee's copy is inert meanwhile. `get_grantable_permissions` has exactly
  one definition and is referenced only in that guard module, pinned by
  `tests/test_module_gating_grants.py`.
* **A superuser is deliberately not filtered.** The global operator *sets* the
  switch and must be able to inspect and repair a tenant whose module they
  just turned off. The flag is answered before any tenant is resolved, and the
  switch is commercial packaging over a tenant's users, not a data boundary.
* **The refusal is byte-identical to any other 403.** No error-path code is
  touched. A client that needs to distinguish reads `disabled_modules` from
  `/permissions/me`; an operator reads `GET /api/v1/tenants/{id}/modules`.
* **Toggling is non-destructive.** No `role.permissions` row is ever edited, so
  re-enabling a module restores exactly the previous access with no data
  migration and no re-authoring. "Inert, not deleted" is what the strip
  produces.
* `GET /api/v1/permissions/` is **not** stripped, by construction: it is the
  static catalogue, identical for every caller, and the role editor needs it
  to render a permission the author does not hold as a disabled checkbox.

**Companion modules** (operator documentation, not code — the 28 toggle
independently and the incoherent configurations they allow are safe and
reversible in one click): `assets` ↔ `inventory`; `reservations` ↔ `spaces`;
`visitors` ↔ `authorizations` ↔ `gate` ↔ `access_control`; `tasks` →
`categories`; `assemblies` ↔ `votes`; `lots` → `residents`, `packages`,
`infractions`; `occurrences` → `infractions` (`APRAS-44`: the promotion source
and the lot an infraction is always against — both couplings are one checkbox
to fix). The `/admin/modules` checklist is grouped by these clusters, which is
presentation, not machinery.

**The two routes**, both superuser-only (`deps.get_current_superuser`) on the
global tenants router, so a tenant_admin acting in their own tenant gets 403.
They map to no catalogue permission, by the convention
`PATCH /users/{id}/superuser` established — `UNGUARDED_ROUTES` grew by two and
`ROUTE_PERMISSIONS` did not move, which is what kept
`tests/data/parity_matrix_baseline.json` byte-identical at 1080 cells.
(`APRAS-40` then took the registry to **183/22**; the F2 file is still
byte-identical, because its 18 new cells live in the additive
`tests/data/parity_matrix_baseline_40.json`.)

```bash
# read every module's state in one tenant
curl "$API/api/v1/tenants/$TENANT/modules" -H "Authorization: Bearer $TOKEN"

# turn finance off (declarative: the body is the complete desired state)
curl -X PUT "$API/api/v1/tenants/$TENANT/modules" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"disabled_modules": ["finance"]}'

# turn everything back on
curl -X PUT "$API/api/v1/tenants/$TENANT/modules" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"disabled_modules": []}'
```

An unknown tenant is **404** (resolved first, so it outranks a bad payload);
an unknown module string or any core module is **400**, raised before the
column assignment so a rejected `PUT` leaves the row untouched.

### Assinatura e planos

The commercial layer over the module switch (`APRAS-40`). **Prices are inert
and nothing is charged — no payment provider exists for this project.** Every
amount below is stored, returned and summed for display only; a follow-up task
wires a provider once an account exists (same blocker class as `APRAS-13`).
No SDK, no API key, no webhook receiver, no outbound HTTP call, and no
dependency was added to `backend/pyproject.toml` or `frontend/package.json`.

**Three tables** (migration `0035`, exactly reversible, seeding nothing):

* `plan` — the install-wide, superuser-managed catalogue. **Global**: it
  carries no `tenant_id`, because a per-tenant catalogue would make "which
  plan is this condominium on" incomparable across the install. `name` is
  globally unique for the same reason `tenant.name` is. There is deliberately
  **no `DELETE`**: `tenant_subscription.plan_id` is `ON DELETE RESTRICT` and a
  plan a tenant is on must not vanish, so `PATCH {"is_active": false}` is the
  removal operation, exactly as for `Tenant`.
* `tenant_subscription` — at most one per tenant
  (`uq_tenant_subscription_tenant`), directly scoped, carrying the plan, the
  status, the courtesy set, a start date and notes.
* `subscription_change` — append-only history, inheriting its tenant through
  the NOT NULL FK to its parent. No `PATCH`, no `DELETE`, no update route:
  `SubscriptionService.record` only ever `session.add()`s one.

**THE RULE, quoted verbatim, because everything else follows from it:**

> `tenant.disabled_modules` remains the only input to permission resolution.
> `APRAS-40` changes no line of `deps.get_effective_permissions`,
> `deps.disabled_modules` or `permissions.filter_by_modules`. What `APRAS-40`
> adds is a constraint on *who may write that column and to what value*.

The ceiling is `SubscriptionService.entitlement(session, tenant)`, which has
**exactly one definition** and is the only place that loads a subscription and
its plan — one query, one join, no `Relationship`. It returns a frozen
`Entitlement(subscription, plan, included, courtesy)` whose `.all` is
`included | courtesy` for a managed tenant and the whole of
`TOGGLEABLE_MODULES` for an unmanaged one. `build_read` derives every field it
returns from that result and touches the session not at all.

**The four levers on one column:**

| Lever | Actor | Bounded by the ceiling? | History row |
|---|---|---|---|
| `PUT /api/v1/subscription/modules` | `billing:manage` (⊇ tenant_admin, superuser), acting in own tenant | **yes** — 400 outside the entitlement | `CONTRACTED` |
| `PUT /api/v1/tenants/{id}/subscription` | superuser | **applies** it, shrink-only | `PLAN_CHANGE` |
| `PUT /api/v1/tenants/{id}/subscription/courtesy` | superuser | **expands** it, and activates | `COURTESY_GRANT` / `COURTESY_REVOKE` |
| `PUT /api/v1/tenants/{id}/modules` (`APRAS-39`, unchanged) | superuser | **no** — the raw lever | `OVERRIDE` |

The raw lever stays unconstrained on purpose: it is the operator's repair
tool, and a tenant whose subscription data is wrong must still be fixable.
When it puts a module outside the entitlement, the subscription area reports
that module as `source: "OVERRIDE"` — visible, named and distinguishable from
both a contracted and a courtesy activation.

*Why courtesy activates while a plan change does not:* courtesy names one or
more specific modules as a deliberate per-module operator act — "turn this on
for them" — whereas a plan names a bundle and says nothing about what the
condominium wants switched on. Contracting a newly covered module is the
tenant's explicit act, and that is what makes the contracting screen mean
something.

**`source`, six values in priority order** (per module, top to bottom, first
match wins, so a module in both the plan and the courtesy set reads `"PLAN"`):

1. `"CORE"` — in `CORE_MODULES`;
2. `null` — not active;
3. `"UNMANAGED"` — active, and the tenant has no subscription row;
4. `"PLAN"` — active, and in the plan;
5. `"COURTESY"` — active, and in the courtesy set;
6. `"OVERRIDE"` — active, subscription exists, in neither.

**No subscription — the semantics.** A fresh install has **no plans and no
subscriptions** (`0035` inserts no rows), so adopting billing is opt-in. For a
tenant with no subscription row: `GET /api/v1/subscription` is **200** with
`plan: null`, every toggleable module `source: "UNMANAGED"` when active and
**`can_contract: false`** for every module — because the contracting `PUT` is
a **404** there, and a `true` would promise a button that cannot work.
`GET /api/v1/subscription/history` is **200** `[]`. Module availability is
unchanged from `APRAS-39`: `disabled_modules` is `[]` and everything is on.

**`subscription.status` gates nothing.** `ACTIVE` / `SUSPENDED` / `CANCELED`
are recorded, displayed and returned, and change no entitlement and no access:
enforcing suspension is a consequence of a failed charge, and there is no
charging.

**Who holds the two permissions.** `billing:read` is the area, `billing:manage`
is the act of contracting; neither implies the other. An `is_tenant_admin`
holder reaches both for free (`APRAS-47`'s whole-catalogue short-circuit, plus
`billing` being core so the strip never removes it) with **no special case
anywhere in the code** — that is the whole reason the gate is a permission and
not a flag check. A superuser reaches them for free too. **No role row
anywhere holds either string on a fresh install**, deliberately: a "Diretor"
gets the area when a tenant_admin ticks the two boxes in the role editor, the
same way they get every other capability. Seeding them would hand commercial
authority to every director of every existing condominium without the síndico
asking.

`billing` **must be core**, and it is load-bearing: if it were toggleable, a
plan (or an operator) could turn it off and the condominium would lose the
only surface from which it can contract anything back on. Consequently
`PUT /api/v1/tenants/{id}/modules {"disabled_modules": ["billing"]}` answers
**400**, through `APRAS-39`'s existing guard and with no new code.

```bash
# a tenant contracts finance (the body is the CONTRACTED set only: a courtesy
# or an operator-override activation is never sent and is never dropped)
curl -X PUT "$API/api/v1/subscription/modules" \
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: $TENANT" \
  -H 'Content-Type: application/json' \
  -d '{"active_modules": ["documents", "finance"]}'

# a superuser assigns a plan (creates the subscription, then applies the
# ceiling shrink-only)
curl -X PUT "$API/api/v1/tenants/$TENANT/subscription" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"plan_id": "'"$PLAN"'", "status": "ACTIVE", "notes": "renegociado"}'

# a superuser grants finance as a courtesy: activated in one call, and free
curl -X PUT "$API/api/v1/tenants/$TENANT/subscription/courtesy" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"courtesy_modules": ["finance"], "reason": "negociação"}'
```

**Out of scope, named so it is not rediscovered in review:** charging of any
kind and every provider-shaped artefact (SDK, API key, webhook receiver,
invoices, receipts, proration, dunning, trials, coupons, tax); tenant-initiated
plan changes (a plan change is a commercial negotiation and without a provider
it cannot be paid for, so plan assignment stays superuser-only); per-tenant or
custom plans; deleting a plan; and a module dependency graph.

**Install superuser.** `user.is_superuser` (APRAS-47, migration `0031`) is the
global counterpart of `is_tenant_admin`: every permission in **every** tenant
and with no acting tenant at all — `deps.get_effective_permissions` answers it
before any tenant is resolved. It is a column, not a role and not a group, so:

* it is **not grantable through the roles API** — the four permissions naming
  the superuser-gated routes are `SUPERUSER_ONLY_PERMISSIONS`
  (`tenants:create`, `tenants:update`, `tenants:members_manage`,
  `tenants:members_set_admin`), and `role_service.assert_can_grant` refuses
  them to every author, superuser included;
* it is **not settable through `UserUpdate`** — the schema has no
  `is_superuser` field, so a body carrying one is inert;
* it gates the five global `/api/v1/tenants` writes via
  `deps.get_current_superuser`, which reads the column and no role;
* it has exactly **one** API surface of its own,
  `PATCH /api/v1/users/{user_id}/superuser` (APRAS-49). See
  *is_superuser* below.

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
`{tenant_id, permissions[], landing_path, disabled_modules[]}`, i.e.
`deps.get_effective_permissions` for the **acting tenant**, sorted (APRAS-48),
already stripped of the tenant's disabled modules (APRAS-39). The router is mounted `TENANT_SCOPED`,
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
own `roles` unfiltered, having no acting tenant to filter by.

### Task

The central entity. Represents an administrative work item (e.g., "Fix elevator in Block A", "Renew insurance policy"). A task has:

- **Title** (required) and optional **description**.
- **Status**: `PENDING` → `IN_PROGRESS` → `COMPLETED` (or `BLOCKED` / `CANCELED`).
- **Priority**: `LOW`, `MEDIUM`, `HIGH`, `URGENT`.
- **Category**: Optional colour-coded label for grouping (e.g., "Maintenance", "Legal").
- **Assignment**: A task can be assigned to a specific user (`assigned_to_id`).
- **Due Date**: Optional deadline.
- **Soft Delete**: Tasks are never physically deleted; `is_deleted` is set to `True`.
- **Visibility Targets** (`visible_to: list[Role]`): Zero or more roles a task is visible to. An empty list means the task is visible to everyone who can see tasks at all; one or more targets restrict it to callers whose roles intersect the list — but **only** for a caller without `tasks:read_all`, which is what makes the targets a narrowing rather than a gate. A caller without `tasks:read_all` may set targets only as a subset of their own roles.

### TaskHistory (Audit Trail)

Every field-level change on a `Task` creates a `TaskHistory` record capturing the field name, old value, new value, who made the change, and when. This powers the **AuditTimeline** component on the frontend. When the changed field is `assigned_to_id`, the service resolves the raw UUID to a `{name, role}` object for display.

### TaskComment

Free-text comments attached to a task, threaded chronologically. Each comment records its author and timestamps.

### Category

An administrator-defined label with a display **name** and **hex colour**. Tasks can optionally belong to one category. Categories have an `is_active` flag for soft deactivation.

### User

An authenticated actor in the system. Fields include email (used as login),
full name, hashed password, active flag, and `is_superuser`. A user's power is
**entirely** their `Role` memberships (`user_role_link`) plus the two
capability columns; there is no role column and no per-user permission.

### Permissions are in code

`backend/app/core/permissions.py` is the vocabulary: **174 strings** in **28
modules**, spelled `<module>:<action>` (`tasks:read`, `purchases:decide`,
`gate:checkin`). `ROUTE_PERMISSIONS` maps **201** routes to one permission
each; `UNGUARDED_ROUTES` names the rest. A route in neither fails
`tests/test_permission_registry.py`, in CI, before it can ship with a hole in
it.

That module deliberately imports nothing — no FastAPI, no SQLModel, not even a
model — so it stays importable from Alembic, from a script and from a test
with no database.

**Every mapped route is now proven enforced** (APRAS-51).
`backend/tests/test_permission_alignment.py` places all 201 in exactly one
declared enforcement form — 53 route-level `Depends(require_permission(P))`,
5 `get_current_superuser`, 3 membership-gated, 5 service-enforced, 135
in-handler — with the exception allowlist `UNENFORCED` **empty**, and sweeps
the other 193 with a real request from a caller holding the whole catalogue
except the route's own permission, pinning the *shape* of the refusal. Two
forms are deliberate and are proven per route rather than excused: **five
routes are enforced in a service** — the two ballot routes, whose
`voting_service._assert_can_cast` writes a `BallotRejection(ROLE_FORBIDDEN)`
row and answers `"Este perfil não vota"` before the 403, and the three
`packages` routes, whose `PackageService._assert_lot_access` lets a
`packages:queue_read` gatehouse holder through without the mapped permission —
and **the three global tenant reads** (`GET /tenants`,
`GET /tenants/{id}`, `GET /tenants/{id}/members`) are gated by **membership**,
not by `tenants:read`/`tenants:members_read`, because they are global-scoped
and a permission gate there would refuse a user their own tenant list.

*Production impact of that alignment, stated once:* since IAM F5 nothing is
seeded, so **every role that does not hold the mapped permission lost access to
those routes** on deploy — including roles that reached those screens before,
because the map claimed a gate the code did not have. That removal is the
point of the change, not a side effect. It surfaces as a **403** carrying
`PermissionRequired`'s existing detail `"The user doesn't have enough
privileges"` and the frontend's existing `RestrictedAccessMessage` in place;
there is no backfill and no migration, and the operator's lever is to grant
the permission in the role editor.

Five of the 25 previously served a caller because of **who they were**, and
now also require the mapped permission: `GET /api/v1/feedback/{id}` and
`POST /api/v1/feedback` (the reporter), `POST
/api/v1/space-reservations/{id}/cancel` (the reservation's owner), and `GET` /
`DELETE /api/v1/uploads/photos/{photo_id}` (the photo's uploader). "The owner
can always cancel their own reservation" is now conditional on
`reservations:cancel`. No parity cell moves — all six legacy bundles hold
these five strings — which is exactly why it is written down here rather than
left to the matrix to notice.

### Roles are data

One `role` row per tenant: a name, a flat `permissions` list, an optional
`landing_path`. There is **no role nesting** and there are **no per-user
permissions** — both are standing board decisions, and both are what keep a
user's effective set answerable by one union with no traversal.

Six rows per tenant carry the pre-F5 bundles because migration `0033` put them
there. They are **ordinary, editable, deletable roles**: there are no system
roles, and nothing is seeded with permissions by any migration or by
`TenantService.ensure_legacy_roles`, which inserts the six historically-named
rows with `permissions = []` and grants nobody anything. Deleting
`Diretor (papel)` strips every director, and that is the operator's
prerogative.

A user's effective set is `deps.get_effective_permissions`: the superuser
short-circuit, then the union of the `permissions` of their roles **in the
acting tenant**, then the tenant_admin short-circuit. Strings stored in a row
that are not in the catalogue are kept as-is — silently dropping them would
hide a data bug the role editor must be able to show.

### `is_superuser`

A global flag on `user`: the whole catalogue, in every tenant, and with no
acting tenant at all. It has exactly **one** API surface,
`PATCH /api/v1/users/{user_id}/superuser` with body `{"is_superuser": bool}`,
callable only by a superuser and refusing any revoke that would leave **zero
active** superusers. There is deliberately **no UI** for it, because
`UserRead` does not expose who the superusers are:

```bash
# grant
curl -X PATCH "$API/api/v1/users/$USER_ID/superuser" \
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: $TENANT" \
  -H 'Content-Type: application/json' -d '{"is_superuser": true}'

# what it replaces
psql -c "UPDATE \"user\" SET is_superuser = true WHERE email = '...';"
```

The route is **tenant-scoped** (it is mounted in the `users` router), so the
header is required even though the acting tenant plays no part in the
decision. That is the opposite call from APRAS-43's
`PATCH /tenants/{id}/members/{user_id}`, and deliberately: `is_tenant_admin`
is a per-tenant capability, so hiding the acting tenant is what stops a tenant
admin granting it to themselves; `is_superuser` is global and only a superuser
can write it, so there is no self-grant to prevent.

`is_tenant_admin` is the same power inside one tenant (APRAS-43), granted by
`PATCH /api/v1/tenants/{id}/members/{user_id}`.

### Object and visibility rules are permissions too

Not every authorization question is "may this actor call this route". These
are the in-code, object-dimension predicates, and they are catalogue
permissions like any other — grantable, revocable, visible in the role editor:

| Permission | What it decides |
|---|---|
| `tasks:read_all` | see every task regardless of its `visible_to` targets, and author a task without the targets defaulting |
| `tasks:update_any` | edit a task assigned to someone else |
| `occurrences:read_assigned` | see occurrences assigned to me even without `occurrences:manage_all` |
| `occurrences:manage_all` | see every occurrence, see internal-only timeline entries, unmask anonymous reporters, update status without being assigned |
| `gate:checkin` | operate the gatehouse |
| `visitors:manage_any_lot` | act on visitors of any lot, not only linked ones |
| `residents:read_any_lot` | read residents of any lot |
| `packages:my_lots_read` | the resident-side package view; refused to every holder of `packages:queue_read` |

Plus the two things that were never roles: **`UserLotLink` per-lot narrowing**
and **per-object ownership** (a comment's author, a photo's uploader, a
transaction's creator).

One message is legacy wording and is kept verbatim on purpose:
`assert_can_edit_task` still raises *"Managers can only edit unassigned or
self-assigned tasks"*. It is now keyed on `tasks:update_any`, not on a role.

### What is gone

Retired by APRAS-49 (IAM F5), listed here so a reader of old code knows what
they are looking at:

* **`UserRole`** — the four-tier enum and the `user.role` column. A user's
  power is their role memberships.
* **`allowed_menus`** and the **menu gate** — `deps.assert_menu_access` and
  its 12 call sites. Removing it widened access for one population: a user
  who holds `tasks:read` or `categories:read` but belongs to no role carrying
  the corresponding menu key. That is deliberate — the gate's job is now done,
  and done finer, by `tasks:read` in a role, and keeping both would be two
  sources of truth for one question. **The operator's replacement lever is to
  remove `tasks:*` from the role.**
* **`LEGACY_ROLE_PERMISSIONS`** — the F1 bridge that let `get_effective_permissions`
  answer for users who held no role rows. Its last recording survives as
  `backend/tests/data/legacy_role_bundles.json`.
* **the doctrine of "role-linked types that cannot be deleted or renamed"** —
  the `role` column that identified them is gone.

The words "user type" and "group" no longer name anything: the entity is a
**role**, in the API, in the UI and in the database.

### Migrating an existing install

```bash
# 1. back up first -- 0033 is not byte-reversible
pg_dump -h localhost -p 5436 -U postgres nexdom > /tmp/nexdom-pre-f5.sql

# 2. migrate
cd backend && POSTGRES_URL=postgresql://postgres:postgres@localhost:5436/nexdom \
  .venv/bin/alembic upgrade head

# 3. if a guard refuses, it prints the affected users; fix and re-run:
#    UPDATE "user" SET is_superuser = true WHERE email = '...';
#    or INSERT INTO user_tenant_link (user_id, tenant_id) VALUES (...);

# 4. full reset instead (destroys demo data):
cd backend && .venv/bin/python -m app.seed
```

`0033` **refuses to run** in two places, and both print exactly who is
affected:

1. **Before writing anything**, if any user is explicitly linked to a
   historically-named role row that is not their own enum role. The backfill
   would silently widen them, so it stops instead and prints two remediations
   that both preserve today's effective set exactly. There is no override
   flag: an env var would let the widening ship silently, which is the one
   thing the guard exists to prevent.
2. **After the backfill and before the drops**, if any active,
   non-superuser, non-tenant-admin user would be left with no way in.

**Reversibility.** `alembic downgrade -1` restores the schema exactly,
restores everything `0033` *wrote* exactly, and restores what it *dropped*
best-effort. `role.allowed_menus` comes back `[]` for every row — those values
are deliberately not journalled, and that is the whole of the loss.

**`f5_backfill_journal`.** The table `0033` leaves at head so its downgrade can
restore role bundles, backfill-created links and folder ACLs exactly. It is
**required** by that downgrade, not merely helpful: with the table missing,
`alembic downgrade -1` refuses by name and changes nothing. `DROP TABLE
f5_backfill_journal` is therefore a **one-way door** — safe only once you are
certain you will never downgrade past `0033`. The table has no SQLModel model
and is invisible to `Base.metadata`, so `alembic revision --autogenerate` at
head would propose dropping it; no workflow here runs autogenerate (every
migration in `alembic/versions/` is hand-written), and this line exists so
that stays a known fact rather than a lost rollback.

### Infrações

The per-condominium **rule catalogue**, its per-rule escalation ladder, and the
infraction process (`APRAS-44`). One toggleable module, `infractions`, 13
permissions, 18 routes, seven tables, migration `0036`.

**Five decisions carry the design, and none of them is an implementation
detail.**

1. **The fine is isolated from Financeiro.** Applying a `MULTA` records a
   value, a date and the person it was applied against. It creates **no**
   `FinancialTransaction`, touches no finance table and imports no finance
   module. `backend/tests/test_infraction_isolation.py` proves it by AST over
   the module's five files and by row count over the whole flow, so connecting
   the two later has to be a *decision* rather than a drift.
2. **An occurrence can be promoted, and an infraction can be born direct.**
   `POST /api/v1/infractions/from-occurrence/{id}` sets `source_occurrence_id`
   and writes an `OccurrenceTimeline` note; `OccurrenceDetailRead.infraction_ids`
   is the return leg. The same occurrence may be promoted more than once — one
   incident can breach two articles. Because `occurrence.lot_id` is nullable
   and `infraction.lot_id` is not, the **effective lot** is the body's when
   sent and the occurrence's when not, with a 422 if both are absent and a 422
   if both are present and different.
3. **Defense is registration only.** A `NOTIFICACAO` step freezes
   `defense_due_on` on the stage row; the notified unit attaches a written
   contestation inside it. There is no accept/reject, no adjudicator and no
   state a contestation moves the process into. Holding
   `infractions:contest` gets a caller to the route; being linked to the
   infraction's lot (`UserLotLink` **or** an active `Resident` row) gets them
   past it — **including a superuser and a tenant admin**, because a
   contestation is the unit's own act. Staff filing one on a unit's behalf is
   deliberately out of scope: it needs its own route and an on-behalf-of
   field, or the timeline would claim the resident filed something they did
   not.
4. **Recidivism is personal, not `propter rem`.** The count is per
   **(rule, responsible person)**, never per lot — CC art. 1337's
   *reiteradamente* is a property of a person, unlike the quotas of art. 1345.
   A sale or a tenant change therefore resets the ladder **by construction**,
   with no reset button and no reset code path, while
   `GET /api/v1/infractions?lot_id=…` still returns the lot's whole history.
   `POST /api/v1/infractions/cycles/close` covers only the case the legal
   addendum names — a change of resident not reflected in the cadastre in time
   — and it is an auditable, justified **cutoff going forward**: an infraction
   registered before it keeps its count, its stages and its ladder index, and
   nothing is ever deleted. Its `lot_id` is optional audit context and is
   deliberately absent from the recidivism predicate.
5. **The current stage is derived, never stored.** `infraction` carries no
   `status` and no `current_stage` column; the current stage is the last row of
   the append-only `infraction_stage`, ordered by `(applied_on, created_at,
   id)`. Even `GET /api/v1/infractions?stage=` reads it as a correlated
   subquery rather than a column, and `?stage=NONE` is "no stage applied yet".
   A column-set assertion pins the absence, because a convenience column added
   later is exactly how an append-only history stops being the truth.

**The suggestion algorithm**, `GET /api/v1/infractions/{id}/next-step`, is one
1-based ordinal collapsing the two escalations — across infractions and within
one process:

```
ladder_index   = recidivism_count + stages_applied + 1
suggested_step = steps_by_order[min(ladder_index, n)]      # n = len(steps)
is_saturated   = n > 0 and ladder_index >= n
```

It reads and computes and **never writes**: staff confirm or override, and the
system never advances a process by itself. `POST /stages` with `action = null`
applies the suggestion; an explicit `action` is always accepted and records
`suggestion_followed = false`, so a deviation from policy is itself auditable.
A rule with **zero** steps is a normal state, not an error: `next-step`
answers 200 with `reason = "NO_POLICY"`, `action = null` is a 409
(`"Rule has no escalation policy"`), and an explicit action still works.
`reason == "CLAMPED"` and `is_saturated` disagree at exactly the last rung,
where the step *is* the suggestion but nothing was truncated.

**The condominium fee is an explicit parameter**, because there is none to
read: this codebase has no per-lot billing anywhere. A `MULTIPLE` fine
multiplies `infraction_settings.condo_fee_amount`, a tenant-scoped singleton
owned by this module, materialised lazily on the first `PUT` (so migration
`0036` seeds nothing) and read as all-nulls when absent. With it unset, the
suggestion answers `fine_amount_unavailable_reason = "CONDO_FEE_NOT_SET"` and
`POST /stages` is a 409 unless an explicit `fine_amount` is passed. Applied
amounts are **frozen** on the stage row, so a later change to the fee never
rewrites history.

**Recommended permission bundle.** Nothing is seeded (the post-F5 doctrine), so
these are the grants an operator makes, not rows any migration writes:

| Permission | ADMINISTRATOR | DIRECTOR | MANAGER | RESIDENT | PORTEIRO | GUEST |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `infractions:read` | ✓ | ✓ | ✓ | | | |
| `infractions:create` | ✓ | ✓ | ✓ | | | |
| `infractions:advance` | ✓ | ✓ | ✓ | | | |
| `infractions:promote` | ✓ | ✓ | ✓ | | | |
| `infractions:cycle_close` | ✓ | ✓ | ✓ | | | |
| `infractions:contest` | ✓ | ✓ | ✓ | ✓ | | |
| `infractions:my_lots_read` | ✓ | ✓ | ✓ | ✓ | | |
| `infractions:rule_read` | ✓ | ✓ | ✓ | | | |
| `infractions:rule_create` | ✓ | ✓ | | | | |
| `infractions:rule_update` | ✓ | ✓ | | | | |
| `infractions:rule_deactivate` | ✓ | ✓ | | | | |
| `infractions:policy_update` | ✓ | ✓ | | | | |
| `infractions:settings_update` | ✓ | ✓ | | | | |

`cycle_close` is MANAGER-level because the board's own definition of staff is
ADMINISTRATOR/DIRECTOR/MANAGER and the act is auditable and additive, never a
deletion. `infractions:my_lots_read` is a **filter, not an inverted gate**:
`GET /api/v1/infractions/my-lots` narrows to the caller's linked lots and
refuses nobody, so a staff member with no linked lot gets `[]` — which is why
`ADMIN_GAP_PERMISSIONS` stays a one-element set and `packages:my_lots_read` is
still the only member. `rule_deactivate`, not `rule_delete`: `DELETE
/api/v1/infraction-rules/{id}` soft-deactivates, because infractions reference
rules and the lot's history has to stay whole and navigable. A deactivated
rule refuses to start a *new* infraction (422) while every existing process
still advances along its very same ladder.

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
