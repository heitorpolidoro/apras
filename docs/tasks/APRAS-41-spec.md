# APRAS-41 — Add Tenant model, multi-tenant user membership, and default-tenant backfill migration

First slice of the multi-tenant SaaS chain `APRAS-41 → APRAS-42 → APRAS-43 → APRAS-38`.
This slice is **the data layer only**. When it lands, the API must behave *exactly* as it
does today for every existing endpoint — the only new observable surface is
`/api/v1/tenants`.

## Scope

**In scope**

1. `Tenant` and `UserTenantLink` SQLModel models + Pydantic schemas.
2. A `tenant_id` FK column on every **directly tenant-scoped** table (27 tables, enumerated
   in §2.1), and an explicit, justified decision that the remaining 20 tables derive their
   tenant through their parent (§2.2).
3. Relaxation of the 7 global unique constraints/indexes that multi-tenancy makes wrong
   (§2.3).
4. One Alembic migration `0028_add_tenant_and_membership` that creates the two tables,
   adds the FKs, rewrites the uniques, seeds exactly one default tenant, backfills every
   existing row and every existing user's membership, and downgrades cleanly.
5. Admin-only tenant CRUD and membership link/unlink endpoints under `/api/v1/tenants`.
6. Tests: unit/endpoint tests on the sqlite suite, migration assertions in the
   Postgres-gated module.

**Explicitly NOT in scope** (see §7 for the full non-goals list)

- No request-scoped tenant resolution, no `X-Tenant-Id` header, no `get_current_tenant`
  dependency, no query filtering — that is APRAS-42.
- No `tenant_admin` flag or RBAC composition — that is APRAS-43.
- No frontend work of any kind — that is APRAS-38.
- No change to the behaviour of any existing endpoint.

---

## 1. Tenant identity model

### 1.1 The well-known default tenant

The single hardest constraint on this slice is that ~68 existing test modules construct
models directly (`Category(name="General")`, `UserType(name=...)`, …) against an in-memory
sqlite database built by `SQLModel.metadata.create_all()` (`backend/tests/conftest.py`),
and every existing endpoint inserts rows without knowing anything about tenants. A bare
`NOT NULL tenant_id` with no default would break both.

Resolve this with a **well-known, fixed default tenant id** declared once as a constant:

```python
# backend/app/models/tenant.py
DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_TENANT_NAME = "Condomínio Padrão"
```

Consequences, all deliberate:

- Every scoped model declares
  `tenant_id: UUID = Field(default=DEFAULT_TENANT_ID, foreign_key="tenant.id", index=True, nullable=False)`.
  ORM inserts that omit `tenant_id` (i.e. all of today's code and all of today's tests)
  keep working and land in the default tenant.
- The migration inserts the `tenant` row with **exactly** `DEFAULT_TENANT_ID`, and sets the
  column's `server_default` to the same literal, so raw-SQL/`bulk_insert` paths and any
  not-yet-updated writer also land in the default tenant instead of violating `NOT NULL`.
- APRAS-42 replaces the Python-side default with a server-resolved acting tenant and may
  then drop the `server_default`. Say so in the model docstring so the follow-up is not
  lost.

`backend/tests/conftest.py` gains an **autouse** `default_tenant` fixture that inserts the
`Tenant(id=DEFAULT_TENANT_ID, name=DEFAULT_TENANT_NAME)` row into the sqlite session before
any other fixture, so the FK target exists and joins are meaningful. No other existing test
module may be edited to add `tenant_id` — if a test needs editing, the default is wrong.

### 1.2 `backend/app/models/tenant.py`

```python
class Tenant(SQLModel, table=True):
    __tablename__ = "tenant"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class UserTenantLink(SQLModel, table=True):
    __tablename__ = "user_tenant_link"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_link_user_tenant"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", ondelete="CASCADE", nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
```

Notes on deliberate choices:

- **Table name is `user_tenant_link`, not `usertenantlink`.** The task's captured wording
  said `usertenantlink` (SQLModel's implicit default), but every other explicit join table
  in this codebase is snake_case with an explicit `__tablename__`: `user_lot_link`,
  `user_user_type_link`, `task_visible_to_link`. Consistency wins; this is a naming
  refinement, not a scope change.
- **Surrogate `id` PK + unique `(user_id, tenant_id)`**, mirroring `UserLotLink`
  (`backend/app/models/lot.py`), rather than a composite PK. APRAS-43 will add an
  `is_tenant_admin` column to this row, and a surrogate key makes that row addressable.
- `Tenant.is_active` is a soft-deactivation flag. There is **no** `DELETE /tenants/{id}`;
  deactivation is `PATCH … {"is_active": false}`. This slice does not define what
  `is_active=false` *does* — nothing consumes it until APRAS-42.
- Both classes are exported from `backend/app/models/__init__.py` alongside
  `DEFAULT_TENANT_ID`.
- `User` gets **no** `tenant_id`. A user is a global identity that belongs to zero or more
  tenants through `UserTenantLink`; `user.email` and `user.cpf` stay globally unique.

### 1.3 `backend/app/schemas/tenant.py`

Follow the `backend/app/schemas/category.py` shape:

- `TenantBase` — `name: str = Field(..., min_length=1, max_length=120)`
- `TenantCreate(TenantBase)` — plus `is_active: bool = True`
- `TenantUpdate` — `name: str | None`, `is_active: bool | None` (all optional)
- `TenantRead(TenantBase)` — `id: UUID`, `is_active: bool`, `created_at`, `updated_at`,
  `model_config = ConfigDict(from_attributes=True)`
- `TenantMemberCreate` — `user_id: UUID`
- `TenantMemberRead` — `user_id: UUID`, `email: str`, `full_name: str`, `role: UserRole`,
  `linked_at: datetime`

---

## 2. Which tables get `tenant_id`

### 2.0 The rule

There are **48** tables in `SQLModel.metadata` today. The rule applied, stated once so the
migration is reviewable:

> A table carries a **direct `tenant_id`** if APRAS-42 will have to filter it *itself* —
> i.e. it is reachable by at least one route that lists it or fetches it by its own id
> **without a tenant-scoped parent's id already in the path**, or it has no NOT NULL FK to
> a directly-scoped table.
>
> A table **inherits** its tenant if it is only ever reached through a scoped parent's id
> and holds a NOT NULL FK to a directly-scoped parent. Adding `tenant_id` to those tables
> would be a denormalisation with a second source of truth (a child row whose `tenant_id`
> disagrees with its parent's) and no query it makes cheaper.

**27 direct + 20 inherited + 1 global (`user`, §1.2) = 48.** Both lists are exhaustive and
disjoint; the implementer must assert the arithmetic in a test (see §5.1), so that a table
added by a future task cannot silently escape classification.

### 2.1 Direct `tenant_id` — 27 tables

Each gets `sa.Column("tenant_id", sa.Uuid(), nullable=False, server_default=<DEFAULT_TENANT_ID literal>)`,
an FK to `tenant.id` with `ondelete="RESTRICT"`, and index `ix_<table>_tenant_id`.

| # | Table | Why direct |
|---|-------|-----------|
| 1 | `task` | Root aggregate; `GET /tasks/` |
| 2 | `category` | Root; no parent FK |
| 3 | `user_type` | Root; `GET /user-types/` — see §2.4 |
| 4 | `lot` | Root; `GET /lots/` |
| 5 | `resident` | `GET/PUT /residents/{resident_id}` reaches it without `lot_id`; also spares APRAS-42 a two-hop join from `facial_template` |
| 6 | `visitor` | Root; no parent FK; `GET /visitors/` |
| 7 | `visitor_authorization` | `GET /authorizations/{authorization_id}` and `/authorizations/{id}/qr-code` reach it without `lot_id` |
| 8 | `access_log` | `GET /access-logs` lists across lots/visitors |
| 9 | `announcement` | Root; `GET /announcements` |
| 10 | `document_folder` | Root; `GET /documents/folders` |
| 11 | `association_document` | `GET /documents` lists across folders; `folder_id` is its own parent but the list route is folder-free |
| 12 | `occurrence` | Root; `GET /occurrences` |
| 13 | `package` | `GET /packages`, `/packages/queue` list across lots |
| 14 | `reservable_space` | Root; `GET /reservable-spaces/` |
| 15 | `space_reservation` | `GET /space-reservations/` lists across spaces |
| 16 | `construction_project` | Root; `GET /projects` |
| 17 | `purchase_request` | Root; `GET /purchase-requests` |
| 18 | `asset` | Root; `GET /assets` |
| 19 | `inventory_movement` | `GET /inventory-movements` lists across assets |
| 20 | `access_device` | Root; `GET /access-control/devices` |
| 21 | `finance_category` | Root; `GET /finance/categories` |
| 22 | `budget_line` | `GET /finance/budget-lines` lists across categories; parent FK is `RESTRICT`, not `CASCADE` |
| 23 | `financial_transaction` | `GET /finance/transactions` lists across categories; parent FK is `RESTRICT` |
| 24 | `assembly` | Root; `GET /assemblies/` |
| 25 | `vote` | `GET /votes/` is top-level **and** `vote.assembly_id` is nullable (ENQUETE votes have no assembly), so there is no parent to inherit from |
| 26 | `feedback` | Root; `reporter_user_id` is nullable (anonymous feedback) |
| 27 | `media_asset` | Polymorphic `entity_type`/`entity_id` with nullable `entity_id` and no real FK — nothing to inherit from |

### 2.2 Inherited scope — 20 tables, no `tenant_id`

Every one of these holds a **NOT NULL** FK to a directly-scoped parent (verified against
`SQLModel.metadata`, not from the models by eye) and is only reached through that parent's
id.

| Table | Scoped through | Parent FK | ondelete |
|---|---|---|---|
| `taskcomment` | `task` | `task_id` NOT NULL | CASCADE |
| `taskhistory` | `task` | `task_id` NOT NULL | CASCADE |
| `task_visible_to_link` | `task` | `task_id` NOT NULL (composite PK) | — |
| `user_user_type_link` | `user_type` | `user_type_id` NOT NULL (composite PK) | — |
| `user_lot_link` | `lot` | `lot_id` NOT NULL | CASCADE |
| `announcement_media` | `announcement` | `announcement_id` NOT NULL | CASCADE |
| `announcement_comment` | `announcement` | `announcement_id` NOT NULL | CASCADE |
| `announcement_read_receipt` | `announcement` | `announcement_id` NOT NULL | CASCADE |
| `occurrence_timeline` | `occurrence` | `occurrence_id` NOT NULL | CASCADE |
| `document_download_log` | `association_document` | `document_id` NOT NULL | CASCADE |
| `project_milestone` | `construction_project` | `project_id` NOT NULL | CASCADE |
| `project_update` | `construction_project` | `project_id` NOT NULL | CASCADE |
| `purchase_quote` | `purchase_request` | `purchase_request_id` NOT NULL | CASCADE |
| `purchase_quote_decision` | `purchase_request` | `purchase_request_id` NOT NULL | CASCADE |
| `vote_option` | `vote` | `vote_id` NOT NULL | CASCADE |
| `ballot` | `vote` | `vote_id` NOT NULL | CASCADE |
| `ballot_rejection` | `vote` | `vote_id` NOT NULL | CASCADE |
| `lot_voter_eligibility` | `lot` | `lot_id` NOT NULL | CASCADE |
| `facial_template` | `resident` | `resident_id` NOT NULL (unique) | CASCADE |
| `facial_access_event` | `access_device` | `device_id` NOT NULL | CASCADE |

Two footnotes the implementer must carry into the migration docstring, because APRAS-42
will trip on them otherwise:

- **`ballot` / `ballot_rejection` deliberately have no `tenant_id`** even though they also
  carry a nullable `lot_id`. A ballot only exists inside a vote; the vote is the tenant
  boundary. Duplicating `tenant_id` onto a ballot would create a second, forgeable source
  of truth on the most audit-sensitive table in the system.
- **`announcement_comment` is the one exception to the rule as written**: it has a
  parent-free route, `DELETE /api/v1/announcements/comments/{comment_id}`. It stays
  inherited anyway — a comment has no meaning outside its announcement — and APRAS-42 must
  join to `announcement` on that single route. State this in the migration docstring.
- `task_visible_to_link` and `user_user_type_link` have composite PKs and no `ondelete`;
  they are pure join tables and inherit from `task`/`user_type` respectively. Note that
  `user_user_type_link` spans a global entity (`user`) and a scoped one (`user_type`) —
  the scoped side is the tenant boundary.

### 2.3 Unique constraints that must be relaxed

A global unique is a cross-tenant collision waiting to happen: two condos cannot both have
a category "Manutenção", a lot "A/12", or a "Salão de Festas". These 8 rewrites are part of
this slice because they are schema, not behaviour, and with a single tenant they are
behaviour-identical.

| Table | Today | Becomes |
|---|---|---|
| `category` | unique idx `ix_category_name` | unique idx `ix_category_tenant_name` on `(tenant_id, name)`; plain idx on `name` |
| `user_type` | unique idx `ix_user_type_name` | unique idx `ix_user_type_tenant_name` on `(tenant_id, name)` |
| `user_type` | unique idx `ix_user_type_role` (created by `0018`) | unique idx `ix_user_type_tenant_role` on `(tenant_id, role)` |
| `lot` | `UniqueConstraint("block", "lot_number")` | `uq_lot_tenant_block_lot_number` on `(tenant_id, block, lot_number)` |
| `occurrence` | unique idx `ix_occurrence_protocol_number` | unique idx `ix_occurrence_tenant_protocol` on `(tenant_id, protocol_number)` |
| `reservable_space` | unique idx `ix_reservable_space_name` | unique idx `ix_reservable_space_tenant_name` on `(tenant_id, name)` |
| `asset` | unique idx `ix_asset_asset_tag` | unique idx `ix_asset_tenant_asset_tag` on `(tenant_id, asset_tag)` |
| `finance_category` | `UniqueConstraint("name", "type")` | `uq_finance_category_tenant_name_type` on `(tenant_id, name, type)` |

Left **global on purpose**, with the reason recorded in the migration docstring:

- `user.email`, `user.cpf` — a user is one identity across tenants.
- `access_device.device_key` — a hardware credential that authenticates
  `POST /access-control/webhook/verification`; it must be unique across the whole install
  or one condo's device could impersonate another's.
- `Tenant.name` — globally unique so the admin tenant list is unambiguous.
- `budget_line.uq_budget_line_category_year`, `user_lot_link.uq_user_lot_link_user_lot`,
  `lot_voter_eligibility.uq_lot_voter_eligibility`,
  `announcement_read_receipt.uq_announcement_read_receipt_user` — already keyed on an
  already-scoped column; nothing to change.

Both the SQLModel `__table_args__` **and** the migration must be updated in lockstep, so
the sqlite schema built by `create_all()` matches Postgres. `user_type.role` currently
carries an *anonymous* column-level `UniqueConstraint` in the model but a *named unique
index* in Postgres (from `0018`) — replace the model's `unique=True` on `role` with an
explicit named `UniqueConstraint` in `__table_args__` so the two agree.

The composite `(tenant_id, role)` unique still allows many NULL `role` values (NULLs never
collide in a unique index on either Postgres or SQLite) and still rejects a duplicate role
*within* a tenant, so the existing
`test_user_type_role_unique_constraint_rejects_duplicate_role` and
`…_allows_multiple_null_roles` tests must keep passing unmodified.

### 2.4 `user_type` is scoped, but resolution is not changed

`user_type` gets a `tenant_id` because APRAS-43's expected results require a `tenant_admin`
to manage user-types "only over rows belonging to that tenant".

However, `get_effective_user_type_ids` (`backend/app/api/deps.py`) does
`select(UserType).where(UserType.role == user.role)).first()` — tenant-blind. **Do not
touch it in this slice.** With the migration's backfill, every `user_type` row is in the
default tenant and there is exactly one row per role, so `.first()` returns what it returns
today.

Correspondingly, `POST /api/v1/tenants` **does not seed role-linked `UserType` rows for the
new tenant**. Seeding them here would immediately create N rows per role and make
`.first()` non-deterministic. Making `get_effective_user_type_ids` tenant-aware *and*
seeding per-tenant role types is APRAS-42's job (request-scoped resolution). Record this as
an explicit hand-off in the model docstring and in the APRAS-42 spec's inputs. This slice
must ship a regression test proving that creating a second tenant does not change
`get_effective_user_type_ids`' output for an existing user.

---

## 3. Migration `0028_add_tenant_and_membership`

File: `backend/alembic/versions/0028_add_tenant_and_membership.py`

- `revision = "0028_add_tenant_and_membership"` — **30 characters**, under the 32-char limit.
- `down_revision = "0027_add_purchase_quotation"` (verified: `alembic heads` reports
  `0027_add_purchase_quotation (head)`, a single head).
- After this migration `alembic heads` must still report exactly one head.
- Follow the `0026`/`0027` precedent: **StrEnum-backed columns use `sa.String()`, never
  `sa.Enum()`**. `tenant_id` is `sa.Uuid()`, matching every other id column.

### `upgrade()` — ordered steps

1. `op.create_table("tenant", …)` — `id` Uuid PK, `name` String NOT NULL, `is_active`
   Boolean NOT NULL `server_default=sa.true()`, `created_at`/`updated_at` DateTime NOT
   NULL. Unique index `ix_tenant_name`.
2. `op.create_table("user_tenant_link", …)` — `id` Uuid PK, `user_id` Uuid NOT NULL FK
   `user.id` CASCADE, `tenant_id` Uuid NOT NULL FK `tenant.id` CASCADE, `created_at`.
   Indexes on both FKs; unique constraint `uq_user_tenant_link_user_tenant`.
3. `op.bulk_insert` the single default tenant with `id = DEFAULT_TENANT_ID`
   (`00000000-0000-0000-0000-000000000001`), `name = "Condomínio Padrão"`,
   `is_active = True`. This is the *only* insert into `tenant`; the migration must never
   create more than one.
4. For each of the 27 tables in §2.1, in a loop over a module-level
   `_TENANT_SCOPED_TABLES: tuple[str, ...]` constant so the list is readable and testable:
   a. `op.add_column(table, sa.Column("tenant_id", sa.Uuid(), nullable=True))`
   b. `op.execute(f"UPDATE {table} SET tenant_id = '<uuid>'")` — backfill
   c. `op.alter_column(table, "tenant_id", nullable=False, server_default=sa.text("'<uuid>'"))`
   d. `op.create_foreign_key(f"fk_{table}_tenant_id", table, "tenant", ["tenant_id"], ["id"], ondelete="RESTRICT")`
   e. `op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])`
5. Backfill membership: insert one `user_tenant_link` row per existing `user.id` pointing at
   the default tenant, via `op.execute` with a `INSERT INTO user_tenant_link (id, user_id, tenant_id, created_at) SELECT … FROM "user"`.
   Generate ids with `gen_random_uuid()`; if that is not guaranteed available, read the
   user ids in a `op.get_bind()` result set and `bulk_insert` Python-side UUIDs. Quote the
   `user` table name — it is a reserved word in Postgres.
6. Apply the 8 unique rewrites of §2.3: `op.drop_index` / `op.drop_constraint` then
   `op.create_index(..., unique=True)` / `op.create_unique_constraint`.

The whole `upgrade()` must be safe on an **empty** database as well as a populated one
(fresh-install CI runs `base → head`), so every `UPDATE`/`INSERT … SELECT` must tolerate
zero rows.

### `downgrade()` — exact inverse

Restore the 8 original uniques first, then for each of the 27 tables drop the index, drop
the FK constraint and drop the `tenant_id` column, then drop `user_tenant_link`, then drop
`tenant`. `alembic downgrade -1` from head must leave a schema that `alembic upgrade head`
can re-apply.

---

## 4. API — `/api/v1/tenants`

New `backend/app/api/v1/endpoints/tenants.py`, registered in
`backend/app/api/v1/api.py` as
`api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])`.
Business logic in `backend/app/services/tenant_service.py` (`TenantService`, classmethod
style, mirroring `CategoryService`).

Write operations use the existing `deps.get_current_active_admin` dependency, which already
returns **403** for every non-`ADMINISTRATOR` role (`DIRECTOR`, `MANAGER`, `RESIDENT`,
`PORTEIRO`, `GUEST`). Do not invent a new guard.

| Method & path | Guard | Success | Errors |
|---|---|---|---|
| `GET /api/v1/tenants` | any authenticated user | 200 `list[TenantRead]` | — |
| `POST /api/v1/tenants` | `get_current_active_admin` | 201 `TenantRead` | 403 non-admin; 409 duplicate name; 422 empty name |
| `GET /api/v1/tenants/{tenant_id}` | any authenticated user | 200 `TenantRead` | 404 unknown id, **and 404 for a non-admin who is not a member** (never 403 — do not leak existence) |
| `PATCH /api/v1/tenants/{tenant_id}` | `get_current_active_admin` | 200 `TenantRead` | 403 non-admin; 404 unknown; 409 name collision |
| `GET /api/v1/tenants/{tenant_id}/members` | admin, or a member of that tenant | 200 `list[TenantMemberRead]` | 404 unknown / non-member non-admin |
| `POST /api/v1/tenants/{tenant_id}/members` | `get_current_active_admin` | 201 `TenantMemberRead` | 403 non-admin; 404 unknown tenant or user; **409 already linked** |
| `DELETE /api/v1/tenants/{tenant_id}/members/{user_id}` | `get_current_active_admin` | 204 | 403 non-admin; 404 link does not exist |

`GET /api/v1/tenants` listing rule (the one asymmetric read):

- `ADMINISTRATOR` → **all** tenants, ordered by `name`.
- every other role → only tenants the caller is linked to via `user_tenant_link`, ordered
  by `name`; a user with no memberships gets `[]`, not an error.

Multi-membership is a first-class requirement: linking user *U* to tenant *B* while *U* is
already linked to tenant *A* must succeed (201). Only the *same* `(user, tenant)` pair a
second time is a 409.

There is intentionally **no** `DELETE /api/v1/tenants/{id}` — the FKs added in §2.1 use
`ondelete="RESTRICT"`, so deleting a populated tenant would fail anyway. Deactivate with
`PATCH`.

### Exceptions

Add to `backend/app/core/exceptions.py` and wire into the mapping in
`backend/app/core/exception_handlers.py`:

| Exception | Status |
|---|---|
| `TenantNotFoundError` | 404 |
| `TenantAlreadyExistsError` | 409 |
| `TenantMembershipAlreadyExistsError` | 409 |
| `TenantMembershipNotFoundError` | 404 |

---

## 5. Tests

### 5.1 sqlite suite (`backend/tests/`)

- `conftest.py`: autouse `default_tenant` fixture seeding `Tenant(id=DEFAULT_TENANT_ID)`.
  **Exactly two existing test files may be touched, and no others:**
  `backend/tests/conftest.py` (this fixture and nothing else) and
  `backend/tests/test_migrations_postgres.py` (**purely additive** — the two fixtures and
  six cases of §5.2 appended at the end; every case already in that file must keep passing
  **unmodified**, byte-for-byte). If any *other* pre-existing test needs a `tenant_id`
  argument added, the default in §1.1 is wrong — fix the default, not the test.
- `test_tenants.py` — happy paths for all 7 routes, the 409s, the 404s, the ordering, the
  empty-membership `[]`, and multi-membership (one user in two tenants).
- `test_tenants_rbac.py` — the 403 matrix: `POST /tenants`, `PATCH /tenants/{id}`,
  `POST /tenants/{id}/members`, `DELETE /tenants/{id}/members/{user_id}` each parametrised
  over `DIRECTOR`, `MANAGER`, `RESIDENT`, `PORTEIRO`, `GUEST` → 403; `ADMINISTRATOR` →
  200/201/204. Plus `GET /tenants` global-vs-own-tenants.
- `test_tenant_models.py` — `DEFAULT_TENANT_ID` is applied as the default on a
  representative sample of scoped models; `UserTenantLink` duplicate pair raises
  `IntegrityError`; `_TENANT_SCOPED_TABLES` has 27 entries and every entry names a real
  table in `SQLModel.metadata`; the 20 inherited tables have **no** `tenant_id` column and
  each has a NOT NULL FK to its listed parent; and the partition is exhaustive —
  `set(direct) | set(inherited) | {"user", "tenant", "user_tenant_link"}` equals
  `set(SQLModel.metadata.tables)`, so a table added later cannot escape classification.
- `test_tenant_no_behaviour_change.py` — regression guard: creating a second tenant leaves
  `get_effective_user_type_ids(user, session)` unchanged, and a representative existing
  endpoint (`GET /api/v1/tasks/`, `GET /api/v1/categories/`) returns the same payload as
  before the change.

### 5.2 Postgres-gated migration assertions

Appended to `backend/tests/test_migrations_postgres.py` — **additive only**, reusing its
existing `_run_alembic` helper and `TEST_POSTGRES_URL` skip marker. Every case already in
that module keeps its current body and keeps using `migrated_pg_engine`. Run locally
against the real database on port 5436:

```
TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5436/nexdom \
  SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v
```

#### 5.2.1 Isolation — mandatory, and the reason for it

`migrated_pg_engine` is **module-scoped** and its consumers **commit**. Every test in the
module therefore shares one database and inherits whatever earlier tests left behind. Three
of the six new cases below are impossible on that fixture, and one of them would make
another new case fail:

- `test_tenant_table_has_exactly_one_default_row` asserts `SELECT count(*) FROM tenant = 1`
  — order-dependent the moment any sibling commits a second tenant.
- `test_existing_rows_are_backfilled` must seed rows *at revision 0027* and then upgrade,
  but the shared database is already at `head` when the module's first test runs.
- `test_scoped_uniques_are_per_tenant` commits two `category` rows with the same `name`;
  `test_downgrade_removes_tenant_schema` then has to restore the **global** unique index
  `ix_category_name` over exactly those committed duplicates. Verified against the real
  Postgres on 5436: this fails with
  `ERROR: could not create unique index "ix_category_name" / DETAIL: Key (name)=(...) is
  duplicated.` — i.e. `alembic downgrade -1` would *not* run cleanly, contradicting
  expected result 4.

**The isolation mechanism is therefore part of the deliverable, not an implementation
detail left open.** Add these two function-scoped fixtures to the module and use them; do
not invent a third mechanism, and do not resolve this by ordering the tests or by having
each case delete its own rows.

```python
def _reset_to(engine, target: str) -> None:
    """Hard-reset `public` and re-run the migration chain up to `target`."""
    engine.dispose()  # drop pooled connections before the DDL
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    _run_alembic("upgrade", target)


@pytest.fixture
def isolated_pg_engine(migrated_pg_engine):
    """A database at `head` containing nothing but what the migrations seed.

    Resets on setup *and* on teardown, so a case using it neither inherits
    another case's committed rows nor leaks its own — in either direction,
    and regardless of execution order.
    """
    _reset_to(migrated_pg_engine, "head")
    yield migrated_pg_engine
    _reset_to(migrated_pg_engine, "head")


@pytest.fixture
def pg_engine_at_0027(migrated_pg_engine):
    """Same reset, stopped one revision *before* 0028 so the test can seed
    pre-migration rows and drive `upgrade head` itself."""
    _reset_to(migrated_pg_engine, "0027_add_purchase_quotation")
    yield migrated_pg_engine
    _reset_to(migrated_pg_engine, "head")
```

Rules that make this sound, each of which the implementer can check:

1. **Every one of the six new cases takes `isolated_pg_engine` or `pg_engine_at_0027`.**
   None of them takes `migrated_pg_engine` directly.
2. **Because both fixtures reset on setup as well as teardown, no execution order is
   assumed anywhere** — not between the new cases, not between new and pre-existing ones.
   `test_downgrade_removes_tenant_schema` starts from a freshly migrated database, so the
   duplicate categories committed by `test_scoped_uniques_are_per_tenant` cannot exist when
   `ix_category_name` is restored. Verified on 5436: after the reset-and-re-migrate,
   `SELECT count(*) FROM category` is `0` and `ix_category_name` is back as
   `CREATE UNIQUE INDEX ... USING btree (name)`.
3. **Teardown always leaves the database at `head`**, which is exactly the state
   `migrated_pg_engine`'s own setup produces — so a pre-existing case running after a new
   one sees what it sees today. Each pre-existing case seeds, inside its own body, every row
   it later asserts on (checked: none of them depends on a row committed by an earlier
   case), so a reset landing between two of them cannot break either.
4. **`_reset_to` disposes the pool before the DDL.** `DROP SCHEMA public CASCADE` does not
   block on idle pooled connections (measured: 0.14 s with a live pool), but disposing
   removes any question of a connection outliving the objects it referenced.
5. **Do not optimise the resets away.** A full `base → head` run costs ~1.6 s on the 5436
   instance; twelve of them is ~20 s in a module that is skipped entirely unless
   `TEST_POSTGRES_URL` is set.

#### 5.2.2 The six cases

| Case | Fixture | Asserts |
|---|---|---|
| `test_tenant_table_has_exactly_one_default_row` | `isolated_pg_engine` | `SELECT count(*) FROM tenant` is exactly 1 and its `id` equals `DEFAULT_TENANT_ID` |
| `test_every_scoped_table_has_not_null_tenant_id` | `isolated_pg_engine` | for all 27 tables of §2.1, `information_schema.columns` has `column_name='tenant_id'`, `is_nullable='NO'`, and a `column_default` containing the default uuid |
| `test_inherited_tables_have_no_tenant_id` | `isolated_pg_engine` | for all 20 tables of §2.2, **absence** of a `tenant_id` column (this is what stops a later drive-by from denormalising `ballot`) |
| `test_existing_rows_are_backfilled` | `pg_engine_at_0027` | inserts a `user`, a `category` and a `task` **while the database sits at 0027**, then calls `_run_alembic("upgrade", "head")` itself; afterwards each seeded row's `tenant_id` equals `DEFAULT_TENANT_ID` and the seeded user has exactly one `user_tenant_link` row pointing at the default tenant |
| `test_scoped_uniques_are_per_tenant` | `isolated_pg_engine` | inserts a second tenant; two `category` rows with the same `name` in *different* tenants both insert; the same `name` twice in *one* tenant raises a unique violation. The rows it commits are wiped by the fixture teardown |
| `test_downgrade_removes_tenant_schema` | `isolated_pg_engine` | `alembic downgrade -1` succeeds; `tenant` and `user_tenant_link` are gone, no `tenant_id` column survives on any of the 27 tables, and the 8 original global uniques (including `ix_category_name`) are back; then `alembic upgrade head` succeeds again |

`test_downgrade_removes_tenant_schema` must additionally assert that `alembic current`
reports `0027_add_purchase_quotation` immediately after the `downgrade -1`. Expected
result 4 names `-1` explicitly and `0028` is head when this task lands, so `-1` is
unambiguous today; the assertion is what makes it *stay* unambiguous — the module's own
comments record that a relative offset silently drifts onto the wrong revision once a
later migration is chained on top, and this turns that drift into a failure instead of a
false pass.

The existing `test_user_type_role_seeds_*` / `_unique_constraint_*` / `test_userrole_*` /
`test_task_visible_to_*` / `test_downgrade_*` cases must all pass **unmodified**.

### 5.3 Gates

`uv run pytest` with the existing 90% coverage gate must pass. `ruff` clean.

---

## 6. Docs

Add a **Tenant** entry to the *Domain Concepts* section of `AGENTS.md` describing the
tenant boundary, the direct-vs-inherited rule, the default tenant, and the explicit
statement that request-scoped resolution is APRAS-42. Add `/api/v1/tenants` to the API
endpoints table.

---

## 7. Out of Scope / Non-goals

- **Frontend: nothing at all.** No component, hook, type, i18n key or route changes. The
  only frontend requirement is negative: `npm run build`, `npm run lint` and Vitest with
  its 75% gate must keep passing **untouched**, because nothing under `frontend/` is
  modified by this task. The tenant switcher is APRAS-38.
- No `X-Tenant-Id` header, no `get_current_tenant` dependency, no service/query changes, no
  cross-tenant isolation tests — APRAS-42. Every existing endpoint keeps returning exactly
  what it returns today.
- No `is_tenant_admin` column, no RBAC composition, no change to `assert_menu_access` or
  `get_effective_user_type_ids` — APRAS-43.
- No per-tenant seeding of role-linked `UserType` rows on tenant creation (§2.4) — APRAS-42.
- No tenant deletion endpoint; no data migration between tenants; no tenant-level settings,
  branding, billing or subdomain routing.
- No change to `backend/app/seed.py` beyond whatever is required for it to keep running
  (it inherits the model default, so ideally zero changes).
