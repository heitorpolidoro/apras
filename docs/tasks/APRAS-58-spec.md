# APRAS-58 — Collapse the 40 Alembic revisions into a single `0001_initial_schema`

## Scope

Replace the whole Alembic history (39 revision modules in
`backend/alembic/versions/`, plus `__init__.py`; head
`0037_logo_and_planned_progress`) with **one** revision generated from the
**final model state**, and repair everything in the repository that pointed at
a revision that no longer exists. Production is reset separately (APRAS-59, a
human operation): this task ships the code, **never the push** (see
*§ Publication order*).

The 19 uncommitted working-tree files that drop the `" (papel)"` suffix from
the six legacy role names (`app/seed.py`, `app/seed_demo.py`,
`app/services/tenant_service.py`, `tests/conftest.py` and ~15
`tests/test_*.py`) are **part of this task** and are committed with it. They
are already written; do not redo them, and do not extend them.

Not in scope: any schema change of its own (the consolidated migration must
produce exactly the schema `SQLModel.metadata` already describes), the
production reset itself, and any frontend change.

## Approach

### Behavior

1. **One revision, generated from the models.** `backend/alembic/versions/`
   currently holds 39 revision modules plus `__init__.py`. One of those modules
   is **already** named `0001_initial_schema.py` (it carries
   `revision: str = "0001"`): that path is **overwritten in place** with the new
   consolidated content — not renamed, not deleted and re-added — and the other
   **38** revision modules are deleted. `__init__.py` stays. The end state of
   the directory is exactly two `.py` files: `__init__.py` and
   `0001_initial_schema.py`, the latter rewritten from scratch with
   `revision = "0001_initial_schema"` (replacing the old `"0001"`) (19 chars — `alembic_version.version_num`
   holds **32**, and a longer descriptive slug fails only on the first real
   `upgrade`, as `0037`'s docstring records) and `down_revision = None`. Produce
   it with `alembic revision --autogenerate` against an **empty real Postgres**
   (`env.py` already exposes `SQLModel.metadata`), then review it by hand: it
   must contain every table, index, constraint name, `server_default` and JSON
   column the models declare, and nothing else.
2. **What the final state means, stated so review can check it:** no
   `role.landing_path` (APRAS-57, `f3ff483`); `tenant.logo_url` and
   `construction_project.planned_progress_json` present and nullable (absorbed
   from `0037`); no `userrole` enum type and no `user.role` column; and **no
   `f5_backfill_journal`** — that table had no SQLModel model and existed only
   so `0033`'s downgrade could run, so it disappears with `0033`.
3. **Data the migration seeds:** the default tenant row
   (`00000000-0000-0000-0000-000000000001`, `Condomínio Padrão`, the id every
   scoped column's `server_default` names) and the six legacy roles of that
   tenant, named **without** the `" (papel)"` suffix, matching
   `TenantService.LEGACY_ROLE_NAMES`, each with **`permissions = []`** — the
   standing "no migration and no script ever seeds a permission" rule
   (`app/seed.py`, `ensure_legacy_roles`). `0033`'s `_LEGACY_BUNDLES` backfill
   was a one-off rescue of pre-F5 access on a live database and is **not**
   carried over into a fresh install.
4. **The migration keeps a module-level `_TENANT_SCOPED_TABLES` literal**
   naming every directly-scoped table, equal to
   `{m.__tablename__ for m in TENANT_SCOPED_MODELS}`, because two test modules
   read that literal out of the migration with `ast` (see below).
5. **`migrate.yml` loses the "Stamp squashed revision if needed" step** (lines
   26-30) — a leftover of the `0005 → 0001` consolidation, and after a reset
   there is nothing to stamp.

### Files touched

| Path | What changes |
|---|---|
| `backend/alembic/versions/*.py` (38 revision modules, i.e. all but `0001_initial_schema.py` and `__init__.py`) | deleted |
| `backend/alembic/versions/0001_initial_schema.py` | **overwritten in place** (existing module, `revision = "0001"`): becomes the consolidated revision with `revision = "0001_initial_schema"`, `down_revision = None`, plus the tenant/roles seed and `_TENANT_SCOPED_TABLES` |
| `backend/alembic/versions/__init__.py` | untouched, kept |
| `.github/workflows/migrate.yml` | the stamp step removed |
| `.github/workflows/ci.yml` | the `backend-migrations` comment stating "roughly 30 of the 53 cases" re-stated for the rewritten module |
| `backend/scripts/assert_no_skips.py` | `MIN_CASES` lowered to the rewritten module's real case count, its docstring/comment re-stated |
| `backend/tests/test_migrations_postgres.py` | rewritten (see *Test criteria*) |
| `backend/tests/test_tenant_models.py` | `MIGRATION` repointed at the new file; `POST_0028_SCOPED_TABLES` and both unions removed (the new literal names every scoped table) |
| `backend/tests/test_tenant_context.py` | same, plus `_RENAMED_SINCE_0028` removed (`role` is now the literal's own spelling) |
| `backend/tests/test_purchase_isolation.py` | `MIGRATION` dropped from `SCANNED`; the migration-only cases (`test_migration_touches_only_allowed_tables`, `test_migration_chain_link_is_explicit`, the three `rule_three` self-tests, the `MIGRATION in SCANNED` assertion) replaced by **one** case asserting every FK of `purchase_request`/`purchase_quote`/`purchase_quote_decision` in `SQLModel.metadata` targets only `ALLOWED_TABLES`; docstring updated to say why (one autogenerated migration creates every table, so an AST scan of it can no longer mean "this module's migration") |
| `backend/tests/test_infraction_isolation.py` | the same treatment over the seven `infraction*` tables |
| `backend/app/seed.py`, `backend/app/seed_demo.py`, `backend/app/services/tenant_service.py`, `backend/tests/conftest.py`, ~15 `backend/tests/test_*.py` | the working-tree `" (papel)"` removal, committed as-is |
| `backend/pyproject.toml` | **only if** the coverage gate fails: `app/seed_demo.py` added to `[tool.coverage.run] omit`, beside `app/seed.py`, for the same reason (a demo-data script with no test). No other lever on the gate is allowed |
| `AGENTS.md` | the claims that name dead revisions: the `0028`-seeds-`Condomínio Padrão` note, the `0028` frozen-literal paragraph, `migration 0031/0034/0035/0036/0037` attributions, "Six rows per tenant carry the pre-F5 bundles because migration `0033` put them there", and the whole `0033` runbook block (one-way door / refuses to run / `f5_backfill_journal` / `alembic downgrade -1` reversibility) |
| `backend/tests/test_docs_agents_md.py` | the three claims that become false — `"f5_backfill_journal"`, `"one-way door"`, `"refuses to run"` — removed from the claim list |

### Test criteria

`backend/tests/test_migrations_postgres.py` is rewritten to validate **only the
single migration**, against a real Postgres (`TEST_POSTGRES_URL`) — never
SQLite, which stores enums as `VARCHAR` and enforces nothing. It keeps the
existing harness shape: the `_alembic` subprocess call site, the module-level
`skipif`, the `DROP SCHEMA public CASCADE` fixtures, and `HEAD_REVISION`
spelled once. The cases, and nothing beyond them:

1. `versions/` holds exactly one revision module; its `revision` is
   `"0001_initial_schema"`, `len(revision) <= 32`, `down_revision is None`.
2. `upgrade head` succeeds on an empty database; `downgrade base` leaves the
   `public` schema with no table but `alembic_version`; `upgrade head` again
   succeeds (replayable).
3. The live table set equals `set(SQLModel.metadata.tables)` — so
   `f5_backfill_journal` is absent and nothing is missing.
4. Every table's column names and nullability match `SQLModel.metadata`
   (the whole-schema generalisation of the retired
   `test_0036_matches_the_model_metadata`).
5. `role.landing_path` absent; `tenant.logo_url` and
   `construction_project.planned_progress_json` present and nullable.
6. No `userrole` enum type; no `user.role` column.
7. Exactly one `tenant` row, with the fixed id and the name `Condomínio Padrão`
   read back intact (the UTF-8 check).
8. The default tenant's roles are exactly the six `LEGACY_ROLE_NAMES`, none
   containing `"(papel)"`, each with `permissions == []`.
9. `TENANT_SCOPED_TABLES` (exact set) each carry a NOT NULL `tenant_id` with an
   FK named `fk_<table>_tenant_id`; the inherited tables carry no `tenant_id`.
10. The per-tenant uniques (`category.name`, `role.name`, `lot.(block,
    lot_number)`, `occurrence.protocol_number`, `reservable_space.name`,
    `asset.asset_tag`, `finance_category.(name, type)`) admit the same value in
    two tenants, and `user.email`, `user.cpf`, `tenant.name`,
    `access_device.device_key` stay global.

No case may skip (the `assert_no_skips.py` guard stays armed), and `MIN_CASES`
is set to the number of cases this module actually collects, verified against a
real run.

## Publication order — hard safety constraint

Pushing this to `master` triggers `.github/workflows/migrate.yml`, which runs
`alembic upgrade head` against production. Production's `alembic_version` holds
`0037_logo_and_planned_progress`, a revision this commit deletes: the upgrade
**fails**, and it would fail on every later push too.

Therefore:

* **The work lands on a dedicated branch, never on `master`.** Other sessions
  share this repository and push from `master`; a commit sitting on local
  `master` would be carried by any of their pushes and would fire
  `migrate.yml` against a production still stamped
  `0037_logo_and_planned_progress`.
* Exact sequence, in this order:
  1. **Before staging anything**, with the 19 modified files still uncommitted
     in the working tree, create and switch to the branch:
     `git checkout -b apras-58-squash-migrations`. Checkout carries the
     uncommitted changes across; **`git stash` is forbidden in this
     repository** (concurrent worktrees share stash refs), so the changes must
     be carried in the working tree, never stashed.
  2. Do the work and commit it on `apras-58-squash-migrations`.
  3. Leave `master` untouched at `origin/master`
     (`git rev-parse master` == `git rev-parse origin/master`).
* The implementer **never runs `git push`** and never opens a PR for this
  task. Finishing the task means a clean commit on
  `apras-58-squash-migrations`, `master` still at `origin/master`, the branch
  absent from the remote, a clean `git status`, and a green local run.
* Before any push, the operator must complete the production reset
  (APRAS-59, another session): `DROP SCHEMA public CASCADE; CREATE SCHEMA
  public;` on the production database — which drops `alembic_version` with
  everything else — after which `migrate.yml` runs the single migration on an
  empty database. The superuser is then re-created by signup plus a SQL
  `UPDATE user SET is_superuser = true`.
* State the constraint in the commit body so a later reader cannot push it by
  accident.

## Expected Results

- [ ] `backend/alembic/versions/` contains exactly two `.py` files,
      `__init__.py` and `0001_initial_schema.py`; the latter declares
      `revision = "0001_initial_schema"` (≤ 32 chars) and
      `down_revision = None`, and no other revision module remains anywhere in
      the directory.
- [ ] Against a real PostgreSQL (`TEST_POSTGRES_URL`), `alembic upgrade head`
      → `downgrade base` → `upgrade head` all succeed, `downgrade base` leaves
      no table but `alembic_version`, and at head the live table set, column
      names and column nullability equal `SQLModel.metadata`.
- [ ] At head the default tenant (`00000000-0000-0000-0000-000000000001`,
      `Condomínio Padrão`) exists exactly once and owns exactly the six
      `TenantService.LEGACY_ROLE_NAMES` roles, no name containing `"(papel)"`,
      each with `permissions == []`.
- [ ] At head `role.landing_path` and `f5_backfill_journal` do not exist, and
      `tenant.logo_url` and `construction_project.planned_progress_json` do.
- [ ] `.github/workflows/migrate.yml` no longer contains the string
      `Stamp squashed revision if needed`.
- [ ] `backend/tests/test_migrations_postgres.py` contains no reference to any
      retired revision id, and `backend/scripts/assert_no_skips.py`'s
      `MIN_CASES` equals the number of cases the rewritten module collects;
      `test_tenant_models.py`, `test_tenant_context.py`,
      `test_purchase_isolation.py`, `test_infraction_isolation.py` and
      `test_docs_agents_md.py` pass with no reference to a deleted file.
- [ ] `uv run python -m app.seed_demo` (working-tree version) completes against
      a database built by the single migration and is re-runnable without
      error.
- [ ] `cd backend && uv run pytest` is green with the 90% coverage gate, and
      `uv run ruff check .` and `uv run ruff format --check .` report nothing.
      The frontend ESLint gate is judged diff-scoped (≈375 pre-existing errors
      live in files this task does not touch).
- [ ] The work is committed on the branch `apras-58-squash-migrations` and
      **not pushed**: `git log master..apras-58-squash-migrations` shows the
      commit, `git rev-parse master` equals `git rev-parse origin/master`,
      `git ls-remote --heads origin apras-58-squash-migrations` returns
      nothing, `git status --porcelain` is empty, and `git stash list` shows no
      entry created by this task.

## Out of Scope

- The production reset and the superuser re-creation (APRAS-59, human).
- Any schema change beyond reproducing the current model state.
- Frontend `"(papel)"` fixture strings and backend docstring prose that merely
  mentions the old names: only assertion values change, and those are already
  changed in the working tree.
- Re-pinning `HARNESS_SHA256` / `EXPECTED_CELL_COUNT`: neither
  `test_permission_alignment.py` nor `test_permission_parity_matrix.py` reads a
  migration, so this task must leave both literals **untouched**. If either
  moves, something outside this scope was edited.
