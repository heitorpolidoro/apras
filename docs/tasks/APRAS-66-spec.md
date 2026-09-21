# APRAS-66 — Condominium slug: a stable address for each tenant

Deliverable 1 of
`docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`
(commit `5d7e8b7`). The decisions recorded there — D2 (`/c/<slug>`, so no
reserved-word list is needed), D3 (a tenant's existence is not a secret) and
D5 (the slug feeds `X-Tenant-Id`, it does not replace it) — are settled and are
not reopened here.

## Scope

Give every tenant a unique, URL-safe `slug`, derived from its name, stored on
`tenant`, backfilled for existing rows by a **new** Alembic revision, returned
by `GET /api/v1/tenant-profile`, and **editable by hand** on the condominium
profile screen APRAS-61 built, through the existing
`PATCH /api/v1/tenant-profile`.

**Not covered:** the `/c/<slug>` route, the public branding endpoint, any
slug→tenant resolution (APRAS-69); tenant onboarding (APRAS-67); white-label
colours (APRAS-68); **slug history and redirects** (see D-F); exposing the slug
on `GET /auth/me`, `/tenants` list filters or any public/unauthenticated
surface.

## Decisions

**D-A — Derivation rule.** One function, `slugify(name)`, in a new
`backend/app/core/slug.py`, is the single producer of a slug string:

1. Unicode NFKD-normalise and drop combining marks, then encode/decode to
   ASCII, discarding anything that does not fold (`Condomínio` → `Condominio`,
   `ção` → `cao`).
2. Lowercase.
3. Replace every maximal run of characters outside `[a-z0-9]` with a single
   `-`. Punctuation, spaces, `&`, `/` and emoji are all covered by this one
   rule; there is no per-character table.
4. Strip leading and trailing `-`.
5. Truncate to **60** characters, then strip a trailing `-` again, so a
   truncated slug never ends in a hyphen.
6. If the result is shorter than **3** characters — empty (a name made only of
   CJK, emoji or punctuation) or a short name such as `AB` — discard it and use
   the literal `condominio`. There is **one** minimum length in this task, the
   3-character floor of D-C.4, and it binds generated slugs exactly as it binds
   typed ones: `slugify` never returns a value `is_valid_slug` would reject, so
   no row can exist that fails the rule its own API enforces. The floor is put
   on the slug and **not** on `tenant.name` (which stays `min_length=1` in
   `TenantCreate`/`TenantUpdate`/`TenantProfileUpdate`): `AB` is a legitimate
   condominium name and the operator's to choose, while the slug is our derived
   artefact and ours to constrain. Padding a short slug was rejected — it
   invents characters the name does not contain.

The `condominio` fallback is a base, not a final slug: D-B then makes it
unique, and its output is safe by construction — `condominio` is 10 characters
and `condominio-<n>` only ever grows, so the fallback-plus-suffix path cannot
itself produce a value under the floor or over the 64-character column.

The stored column is `VARCHAR(64)`: 60 for the base plus room for the
uniqueness suffix. `tenant.name` keeps its 120-character bound; a long name
simply yields a truncated slug.

**D-B — Collision rule for *generated* slugs.** Slugs are unique across the
installation, enforced by a unique index, and resolved deterministically **when
the system is the one choosing**: the first tenant to claim a base keeps it
bare; every later one gets the **smallest integer ≥ 2 not already taken**,
appended as `-<n>` (`altos-da-serra`, `altos-da-serra-2`, `altos-da-serra-3`).
The candidate set is computed from the slugs already in `tenant`; because the
unique index is the real arbiter, an `IntegrityError` on insert is retried with
a recomputed suffix, bounded to a small number of attempts, after which the
create fails loudly rather than looping. This rule applies **only** to
creation-time derivation from the name — never to a value a person typed
(D-C.3).

**D-C — The slug is editable after creation** (operator decision, 2026-09-21,
replacing the immutability this spec previously proposed). Four sub-rules, and
they are load-bearing together:

1. *Who.* Editing the slug carries the **same** permission as the rest of the
   screen, `tenants:profile_update`, on the **same** route,
   `PATCH /api/v1/tenant-profile`. No new permission string, no new route, no
   `ROUTE_PERMISSIONS` entry, no parity-matrix baseline change. A stricter
   permission was considered and rejected: the two candidate holders of a
   tighter grant are the superuser (who would then be needed for a routine
   self-service rename, defeating APRAS-61 D7) and the tenant admin, who by
   APRAS-47's whole-catalogue short-circuit already holds every permission
   implicitly — so a new `tenants:slug_update` would restrict nobody who can
   reach the screen today, while costing a catalogue entry, a role-editor row
   and a permission-matrix baseline churn. The blast radius of a slug change
   (broken bookmarks) is also not larger than that of the renames and logo
   changes the same permission already authorises.
2. *Rename never touches the slug.* `PATCH /api/v1/tenant-profile` and
   `PATCH /api/v1/tenants/{id}` change `slug` **only when `slug` is present in
   the request body**. Changing `name` alone leaves the slug exactly as it was,
   whether that slug was generated or hand-picked. This is what keeps the two
   rules from interacting badly: there is no "regenerate on rename" path at
   all, so a hand-picked slug can never be silently overwritten, and no
   `slug_customized` flag is needed to protect it. Derivation from the name
   happens exactly once, at tenant creation.
3. *A typed slug that collides is refused, never suffixed.* If the submitted
   slug is already held by another tenant, the request fails with **409** and
   an error code `SLUG_ALREADY_TAKEN`, so the person chooses another value.
   The `-2` walk of D-B is deliberately **not** applied: it exists to let the
   system invent a value nobody asked for, and applying it here would save a
   value different from the one typed, which is the classic silent-corruption
   bug — someone would print `/c/altos-da-serra` on a notice board having seen
   it accepted, while the database holds `altos-da-serra-2`. Submitting the
   tenant's own current slug is a no-op, not a conflict.
4. *A typed slug is validated, not slugified.* Accepted values match
   `^[a-z0-9]+(-[a-z0-9]+)*$` with length **3–64** — lowercase ASCII letters
   and digits in hyphen-separated groups, so no leading, trailing or doubled
   hyphen, no spaces, no accents, no uppercase, no underscores. The server does
   **not** quietly fold `Altos da Serra` into `altos-da-serra`: a value outside
   the set is rejected with **422** and error code `SLUG_INVALID`, for the same
   reason as 3 — what the person sees accepted must be what is stored. This
   3–64 bound is the *same* rule D-A.6 applies to generated slugs, expressed
   once in `is_valid_slug`; the two cannot disagree. No
   reserved-word list is needed (design D2: every slug lives under `/c/<slug>`,
   so it can never shadow an application route), and none is added. The
   frontend mirrors the same regex for inline feedback and disables Save while
   the field is invalid, but the server is the enforcer; the client also offers
   a "suggest from name" affordance that fills the field with `slugify(name)`
   — the person still has to submit it.

**D-D — Exposure.** The slug appears in exactly two read schemas —
`TenantProfileRead` (the screen this task touches) and `TenantRead` (the
`POST`/`PATCH`/`GET {id}` tenants body, which APRAS-67 will read back after
creating a condominium) — and as an optional field on `TenantProfileUpdate`.
**No new route is added**, so there is no `ROUTE_PERMISSIONS` entry, no
`UNGUARDED_ROUTES` change and **no parity-matrix baseline change**: the
APRAS-60/61/63 precedent applies to new routes, and the parity matrix records
route × role reachability, not request or response bodies. A reviewer should
confirm the recorded baseline is byte-identical after this task.

**D-E — Backfill.** A single new revision `0002_tenant_slug`
(`down_revision = "0001_initial_schema"`, 16 characters, inside the 32-character
`alembic_version.version_num` limit) adds the column nullable, backfills every
existing row, then sets `NOT NULL` and creates the unique index. The backfill
iterates tenants ordered by `(created_at, id)` — deterministic, so two
databases with the same rows get the same slugs — and applies D-A (including
the 3-character floor and the `condominio` fallback) and D-B, so an existing
tenant named `AB` is backfilled with `condominio` (or `condominio-<n>` if that
base is already taken), never with an invalid two-character slug. The
default tenant `00000000-0000-0000-0000-000000000001` (`Condomínio Padrão`)
therefore gets `condominio-padrao`, and the dev database's
`Condomínio Solar da Serra` gets `condominio-solar-da-serra`. `downgrade`
drops the index and the column.

The revision **imports nothing from `app`**: it carries its own frozen,
module-private copy of the D-A derivation (and of the D-B suffix walk over the
rows it is backfilling). This duplication is deliberate. `AGENTS.md` (the
migration rule, "`alembic/versions/**` … are frozen history that
`alembic upgrade` replays verbatim against production") means a revision must
replay identically years from now; a live `from app.core.slug import slugify`
silently rewrites history the day a later task changes `slugify`. `0001` sets
exactly this precedent — its only imports are `uuid`, `datetime`, `typing`,
`alembic.op`, `sqlalchemy` and `sqlmodel`, and it **re-declares**
`DEFAULT_TENANT_ID` and `LEGACY_ROLE_NAMES` as local literals rather than
importing them, noting that importing under `alembic/` also shadows the
third-party library. Copying a dozen lines is the cheaper mistake than an
un-replayable migration, and APRAS-58's clean-up is what the alternative
costs. A future reader must not "fix" this by importing `app.core.slug`; the
revision carries a comment saying so. `tests/test_slug.py` pins `slugify`'s
behaviour, and the Postgres migration test pins the copy's output
(`condominio-padrao`), so the two cannot drift unnoticed while this revision
is the head.

**D-F — Broken links are a known, accepted cost.** Changing a slug breaks
every bookmark, printed notice and shared link that used the old one: the old
address will simply 404 once APRAS-69 lands `/c/<slug>`, with no redirect and
no grace period. The operator accepted this explicitly (2026-09-21, *"vamos
aceitar a dor de perder o favorito"*) rather than pay for redirects now. A
historical-slug table is therefore **deliberately out of scope**, not
overlooked. The follow-up, if the pain ever materialises, is a single task of
this shape:

> **Slug history and redirects** — a `tenant_slug_history` table
> (`slug` unique, `tenant_id`, `retired_at`), written whenever
> `PATCH /tenant-profile` changes a slug; `/c/<slug>` resolves the live
> `tenant.slug` first and falls back to history with a `301` to the current
> address; a retired slug is not reusable by another tenant while it is in
> history. Depends on APRAS-69.

Until then the UI states the consequence in plain language before the change
is saved (D-G).

**D-G — Confirmation before saving a slug change.** Because the cost is
irreversible and invisible, submitting a *changed* slug opens a confirmation
dialog naming the old and the new address and saying that links using the old
one will stop working. It is a client-side guard only; the API has no
confirmation parameter.

## Approach

### Behaviour

- `Tenant` carries `slug`: non-null, unique, indexed. Constructing
  `Tenant(name=...)` without a slug yields `slugify(name)`; this fallback
  never consults the database, so the twelve existing direct constructions in
  `tests/` and `seed_demo.py` keep working unchanged.
- `TenantService` gains the authoritative producer: given a session and a
  name, it returns the collision-resolved slug (D-A + D-B). `create_tenant`
  uses it and sets `slug` explicitly; a duplicate *name* still raises
  `TenantAlreadyExistsError` (409) before any slug is computed.
- `TenantService` gains a second, separate path for an **explicit** slug:
  validate against the D-C.4 pattern (else a 422-mapped error), then check
  uniqueness excluding the acting tenant (else a 409-mapped
  `SlugAlreadyTakenError`). The unique index remains the arbiter: an
  `IntegrityError` here surfaces as the same 409, never as a suffix walk.
- `update_profile` / `update_tenant` write `slug` **only** when the field is
  present in the payload; a name-only update leaves it untouched (D-C.2).
- `GET /api/v1/tenant-profile` returns `slug` alongside `id`, `name`,
  `is_active`, `logo_url`. The route stays in `UNGUARDED_ROUTES` and stays
  self-scoped to the acting tenant.
- The profile screen renders the slug as an editable text input with the
  `/c/` prefix shown as static adornment, inline format validation, a
  "suggest from name" action, a warning that changing it breaks existing
  links, and the D-G confirmation dialog; the server's 409 renders as a
  field-level "this address is already in use" message.

### Files touched

| Path | Change |
|---|---|
| `backend/app/core/slug.py` | new — `slugify` (D-A), the length/fallback constants, and `SLUG_PATTERN` + `is_valid_slug` (D-C.4) |
| `backend/app/models/tenant.py` | `slug` field; init-time fallback derivation; docstring note that it is editable and carries no history |
| `backend/alembic/versions/0002_tenant_slug.py` | new revision: add nullable, backfill, `NOT NULL`, unique index; `downgrade` reverses; frozen local copy of the derivation, no `app` import (D-E) |
| `backend/app/services/tenant_service.py` | generated-slug producer with collision resolution; explicit-slug validation + uniqueness check; `SlugAlreadyTakenError` / `InvalidSlugError` |
| `backend/app/api/v1/endpoints/tenant_profile.py` | map the two new errors to 409 / 422; docstring note that the slug rides the existing `tenants:profile_update` guard |
| `backend/app/schemas/tenant.py` | `slug` on `TenantProfileRead` and `TenantRead`; optional `slug` on `TenantProfileUpdate` |
| `backend/tests/test_migrations_postgres.py` | `HEAD_REVISION` becomes `0002_tenant_slug`; the "exactly one module" and "single root revision" tests are rewritten for a two-revision linear history; a case asserts the backfilled default-tenant slug |
| `backend/scripts/assert_no_skips.py` | `MIN_CASES` re-pinned to the module's new real collected count; the APRAS-64 comment extended with this task's raise |
| `backend/tests/test_slug.py` | new — derivation table, validation table, collision cases |
| `backend/tests/test_tenant_profile.py`, `tests/test_tenants.py` | the new field in the read bodies; slug edit accepted; collision 409; invalid 422; name-only rename leaves the slug |
| `frontend/src/api/tenantProfile.ts` | `slug: string` on `TenantProfile`; optional `slug` on the update payload |
| `frontend/src/features/user-administration/pages/TenantProfilePage.tsx` | editable slug field, inline validation, suggest-from-name, confirmation dialog, 409/422 handling |
| `frontend/src/i18n/locales/{pt,en}.json` | `tenantProfile.slug*` keys (label, hint, warning, confirm title/body, taken, invalid, suggest) in both, key-identical |
| `frontend/src/features/user-administration/__tests__/TenantProfilePage.test.tsx` | edit + confirm saves; invalid value blocks Save; a 409 renders the field error |
| `docs/tasks/APRAS-66-mock.html` | new — the screen with the editable field and its states |
| `AGENTS.md` | the migration section: the history is no longer a single revision |

### Test criteria

- **Derivation** (`test_slug.py`, SQLite/unit): a table of names → slugs
  covering accents (`Condomínio Padrão` → `condominio-padrao`), punctuation and
  runs of separators (`Res.  Altos da Serra VI!` → `res-altos-da-serra-vi`),
  leading/trailing junk, a name over 60 characters (truncated, no trailing
  hyphen), a name that reduces to nothing (`"!!!"` → base `condominio`), and a
  name that reduces to fewer than 3 characters (`"AB"` → base `condominio`,
  `"A. B"` → base `condominio`). A property/table assertion states the
  invariant directly: for every name in the table, `is_valid_slug(slugify(name))`
  is true.
- **Validation** (`test_slug.py`): `is_valid_slug` accepts `altos-da-serra`,
  `bloco-2`, `abc`; rejects `""`, `ab` (too short), 65 characters, `Altos`,
  `altos da serra`, `altos--da-serra`, `-altos`, `altos-`, `altos_da_serra`,
  `condomínio`.
- **Collision on generation**: creating three tenants whose names share a base
  yields `x`, `x-2`, `x-3` — the smallest free integer, not a counter — and two
  tenants never share a slug (the unique constraint asserted directly, not only
  through the service).
- **Editing**: `PATCH /api/v1/tenant-profile` with a valid free `slug` returns
  **200** with the new value and `GET` reads it back; with a slug another
  tenant holds returns **409** and the stored slug is unchanged; with
  `Altos da Serra` returns **422** and nothing is stored; with the tenant's own
  current slug returns 200 (no-op, not 409).
- **Rename independence**: `PATCH` with `name` only — both after a generated
  slug and after a hand-picked one — returns the slug unchanged; a
  hand-picked slug survives a subsequent rename.
- **Permission**: a role without `tenants:profile_update` gets 403 on a
  slug-only `PATCH`, and a tenant admin without any explicit grant gets 200 —
  the same guard as the rest of the screen, verified in
  `test_tenant_profile.py`.
- **Migration** (Postgres, per `AGENTS.md` ~line 200, throwaway DB on 55432,
  UTF-8, never a dev database): `upgrade head` → `downgrade base` →
  `upgrade head` succeeds; at head, `tenant.slug` is `NOT NULL` with a unique
  index, the model/migration column comparison still matches, and the seeded
  default tenant's slug is `condominio-padrao`; a row inserted before the
  upgrade with a two-character name is backfilled with a slug that satisfies
  the 3–64 rule.
- **Migration guard** (`backend/scripts/assert_no_skips.py`): this task changes
  how many cases `tests/test_migrations_postgres.py` collects, and
  `tests/test_assert_no_skips.py::test_the_floor_is_the_modules_real_case_count`
  asserts `collected == MIN_CASES` — an equality, whatever the "a floor, not an
  equality" comment says about the CI-XML check. `MIN_CASES` is therefore
  re-pinned from `22` to the count a real `pytest --collect-only` of the module
  reports after this task's edits (measured, not counted by eye), and the
  comment gains an APRAS-66 line the way APRAS-64 added its own.
- **Gates**: backend `pytest` green with the 90% coverage gate, `ruff check`
  and `ruff format --check` clean; frontend `tsc -b`, `vitest` above
  **80 lines / 78 functions / 76 branches / 80 statements**
  (`frontend/vitest.config.ts`), `eslint` diff-scoped against the repository
  baseline of 375 errors + 2 warnings across 64 files (no new finding in a
  touched file).

## Operator decision (2026-09-21)

*"Sim, mas não vamos fazer o histórico de slugs agora, vamos aceitar a dor de
perder o favorito."* — the slug is editable (D-C) and there is deliberately no
historical-slug table (D-F). The previously open question is closed.

## Mockup

`docs/tasks/APRAS-66-mock.html` — the profile screen with the editable field,
in five states (generated, edited + confirmation dialog, invalid format,
already taken, long name truncated).

## Expected Results

- [ ] `tenant` carries a non-null, unique, indexed `slug` derived from the
      name by lowercasing, accent-stripping and hyphenating, capped at 60
      characters of base in a `VARCHAR(64)` column, with `condominio` as the
      base whenever the derivation yields fewer than 3 characters (empty or
      short, e.g. a tenant named `AB`), so `is_valid_slug(slugify(name))` holds
      for every name — one 3–64 rule shared by generated and typed slugs, and
      `name` keeps `min_length=1`.
- [ ] A new Alembic revision `0002_tenant_slug` on top of `0001_initial_schema`
      adds it — `0001_initial_schema.py` is not edited — and
      `tests/test_migrations_postgres.py` passes against real PostgreSQL
      (`TEST_POSTGRES_URL`), including `upgrade → downgrade base → upgrade`.
- [ ] A **generated** slug that collides takes the smallest free integer suffix
      from `-2` upward; a test creates three same-base tenants and gets
      `x`, `x-2`, `x-3`, and two tenants never share a slug.
- [ ] The migration backfills every existing tenant, and the default tenant
      `00000000-0000-0000-0000-000000000001` ends with slug
      `condominio-padrao`, and every backfilled slug satisfies the same 3–64
      rule (a pre-existing two-character name yields `condominio`/`condominio-<n>`,
      not a two-character slug).
- [ ] `0002_tenant_slug.py` imports nothing from `app` — it carries its own
      frozen copy of the derivation, with a comment saying the duplication is
      deliberate — and `tests/test_assert_no_skips.py` passes with
      `MIN_CASES` in `backend/scripts/assert_no_skips.py` equal to the real
      collected case count of `tests/test_migrations_postgres.py`.
- [ ] The slug is editable through the existing
      `PATCH /api/v1/tenant-profile` under the existing
      `tenants:profile_update` permission: a valid, free slug returns 200 and
      is read back by `GET`; a caller lacking the permission gets 403; no new
      route, no new permission string, and the parity-matrix baseline and
      `ROUTE_PERMISSIONS` are unchanged.
- [ ] A hand-typed slug is validated, never silently rewritten: values outside
      `^[a-z0-9]+(-[a-z0-9]+)*$` / length 3–64 (uppercase, accents, spaces,
      leading, trailing or doubled hyphens) return **422** and store nothing,
      while the UI blocks Save and shows an inline format message.
- [ ] A hand-typed slug that another tenant already holds returns **409** with
      no suffix applied and the stored slug unchanged; resubmitting the
      tenant's own current slug returns 200 as a no-op.
- [ ] Renaming the condominium never changes the slug: `PATCH` with `name`
      only returns the slug unchanged, both for a generated slug and for one
      that was previously edited by hand.
- [ ] The spec records that changing a slug breaks existing links as a known,
      accepted cost, that a historical-slug table is out of scope, and the
      shape of the future task that would add it; the UI warns about broken
      links and asks for confirmation before saving a changed slug.
- [ ] `GET /api/v1/tenant-profile` returns `slug`, and the tenant profile
      screen shows it in an editable field with the `/c/` prefix and a
      suggest-from-name action.
- [ ] Backend pytest green at the 90% gate and ruff clean; frontend `tsc -b`,
      vitest above 80 lines / 78 functions / 76 branches / 80 statements, and
      diff-scoped eslint clean against the 375-error baseline; `pt.json` and
      `en.json` stay key-identical.

## Out of Scope

`/c/<slug>` routing and the public branding endpoint (APRAS-69), tenant
onboarding (APRAS-67), white-label colours (APRAS-68), **slug history,
redirects and reservation of retired slugs** (D-F), rate-limiting how often a
slug may change, subdomains, and any exposure of the slug on an
unauthenticated surface.
