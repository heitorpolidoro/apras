# APRAS-54 — Quitar a dívida de lint pré-existente do backend e tornar ruff um gate de CI

> **One deliverable, one PR, zero behaviour change.** Everything below is
> mechanical. The moment a slice cannot be proven inert by the harness in §5,
> the right answer is to leave the finding and silence it with a justified
> `# noqa` — never to "improve" the code while paying the lint debt.

## 1. Scope

**In scope — the backend only.**

1. Bring `ruff check` and `ruff format --check` over `backend/` to **zero
   findings** under the project's *existing* rule selection
   (`backend/pyproject.toml`, `select = ["ALL"]`, `line-length = 88`,
   `target-version = "py313"`).
2. Replace **every** clock read in `backend/app/` with **one** helper module,
   `backend/app/core/clock.py` — both the naive sites ruff flags
   (`datetime.utcnow()`, `date.today()`, `datetime.now()` without `tz`, bare
   `datetime(...)`) and the **20 tz-aware `datetime.now(UTC)` sites ruff does
   not flag**, 17 of which write aware values into naive columns (§4.4) —
   without a schema change and without changing the instant any column stores.
3. Make CI fail on any finding: a new `backend-lint` job in
   `.github/workflows/ci.yml`, plus `ruff` pinned as a dev dependency so the
   version CI runs is the version a developer runs.
4. Document the gate and the `# noqa` convention in `AGENTS.md`.

**Explicitly not in scope** — see §9.

**Not a behaviour change.** No route, no schema, no permission string, no
response body, no OpenAPI node, and no migration may move. The lint debt is
paid *around* the behaviour, and §5 is how that is proven rather than asserted.

## 2. Measured baseline

Measured on **d39ff1c** in a detached worktree (`git worktree add
/tmp/apras-54-base d39ff1c`), with **ruff 0.16.5**, from `backend/`:

```
ruff check .   --statistics   ->  1145 findings in 134 files
                                  289 safe-fixable, 310 unsafe-fixable, 546 manual
ruff format --check .         ->  183 files would be reformatted, 110 already formatted
```

**Per top-level area** (findings / files-to-reformat):

| Area | findings | safe-fix | unsafe-fix | manual | to reformat |
|---|---:|---:|---:|---:|---:|
| `app/` (127 .py) | 781 | 84 | 303 | 394 | 68 |
| `alembic/versions/` (≈38 .py) | 192 | 190 | 0 | 2 | 28 |
| `tests/` (121 .py) | 171 | 15 | 7 | 149 | 87 |
| `index.py` | 1 | 0 | 0 | 1 | 0 |
| `scripts/`, `alembic/env.py` | **0** | — | — | — | 0 |
| **total** | **1145** | **289** | **310** | **546** | **183** |

`app/` splits further: `app/api/` 455, `app/services/` 227, `app/schemas/` 46,
`app/models/` 38, `app/*.py` 15.

**Rule codes ≥ 4 findings, by area:**

| Code | total | app | tests | alembic/versions | fix |
|---|---:|---:|---:|---:|---|
| FAST001 redundant `response_model` | 150 | 150 | 0 | 0 | unsafe |
| FAST002 dependency without `Annotated` | 132 | 132 | 0 | 0 | unsafe (126) |
| DTZ003 `datetime.utcnow()` | 129 | 99 | 30 | 0 | manual |
| B008 call in argument default | 101 | 101 | 0 | 0 | manual |
| PLC0415 import outside top level | 100 | 10 | 90 | 0 | manual |
| E501 line too long | 89 | 89 | 0 | 0 | manual |
| UP007 non-PEP604 union | 72 | 0 | 0 | 72 | safe |
| Q000 bad quotes | 64 | 0 | 0 | 64 | safe |
| I001 unsorted imports | 61 | 36 | 1 | 24 | safe |
| A002 argument shadows builtin | 36 | 35 | 1 | 0 | manual |
| UP035 deprecated import | 25 | 5 | 0 | 20 | safe |
| PLR2004 magic value | 22 | 20 | 0 | 2 | manual |
| RSE102 unnecessary parens on `raise` | 21 | 21 | 0 | 0 | unsafe |
| UP045 non-PEP604 optional | 20 | 20 | 0 | 0 | safe |
| F401 unused import | 19 | 15 | 0 | 4 | safe |
| COM819 prohibited trailing comma | 14 | 0 | 12 | 2 | safe |
| DTZ011 `date.today()` | 11 | 5 | 6 | 0 | manual |
| BLE001 blind `except Exception` | 7 | 6 | 1 | 0 | manual |
| RUF003 ambiguous unicode in comment | 7 | 0 | 7 | 0 | manual |
| UP006 non-PEP585 annotation | 6 | 6 | 0 | 0 | safe |
| PIE790 unnecessary placeholder | 6 | 4 | 0 | 2 | safe |
| E402 import not at top of file | 5 | 5 | 0 | 0 | manual |
| DTZ001 naive `datetime(...)` | 4 | 0 | 4 | 0 | manual |
| E712 `== True` | 4 | 4 | 0 | 0 | unsafe |
| RUF059 unused unpacked variable | 4 | 0 | 4 | 0 | unsafe |
| W293 blank line with whitespace | 4 | 2 | 2 | 0 | safe |

The 24 remaining codes have ≤ 3 findings each (SLF001 3, ARG001 3, F841 3,
SIM102 2, SIM117 2, G004 2, Q003 2, RUF043 2, and 16 singletons including
`S603`, `S311`, `S107`, `PGH003`, `B904`, `B007`, `PERF102`, `FURB110`,
`E741`, `PT011`, `PLW0127`, `DTZ005`, `PLR5501`).

**Two facts that shape the whole plan, both verified in the base worktree:**

* **`ruff` is not a dependency of this project.** It appears nowhere in
  `backend/pyproject.toml`, `requirements.txt` or `uv.lock`; the 1145 above
  come from a Homebrew `ruff 0.16.5`. A CI gate cannot exist until the version
  is pinned (§4.6), and until it is, "1145" is a property of one laptop.
* **Every datetime column in this database is naive.** `timezone=True` appears
  in **zero** of the 38 migrations, so every `sa.DateTime()` is
  `TIMESTAMP WITHOUT TIME ZONE`. §4.4 is built on that.

**Post-automation residual, measured by actually running the plan** on a copy
of the base tree (this is the number the manual slices must retire, not an
estimate):

```
after `ruff format` (alembic/versions excluded)            1145 -> 1059
after `ruff check --fix` (safe only, same exclusion)        1059 ->  971
after `--fix --unsafe-fixes --select FAST001,FAST002`        971 ->  695   (276 fixed, 6 left)
after the per-file ignores of §4.2 + §4.5                    695 ->  302
```

The 302 that survive are the judgement work: DTZ 145, RSE102 21, E501 20,
PLR2004 20, RUF100 18 *(newly redundant `# noqa` unmasked by the per-file
ignores — measured: exactly 18 under the ignore set of §4.1/§4.5, see §4.5)*,
PLC0415 10, RUF003 7, BLE001 7, FAST002 6, B008 6, E402 5, I001 5, E712 4,
RUF059 4, ARG001 3, F841 3, and ~18 single-site findings — the last figure now
including `S107`, `PT011` and the one `tests/` `A002`, which §4.5 no longer
covers with a file-wide ignore (they become per-line `# noqa`s instead) and
which therefore survive this step rather than vanishing into it.

## 3. Preconditions

1. **Branch off master *after* APRAS-53 has landed.** APRAS-53 edits
   `backend/tests/test_uploads.py` and `backend/app/api/v1/endpoints/uploads.py`
   — `uploads.py` is one of the six files §4.3 has to touch by hand. Rebasing a
   250-file reformat is not a thing anyone should attempt.
2. **Re-measure at the branch point** and record the numbers in the PR body —
   the ruff counts, the collected-test count, the coverage percentage, the
   OpenAPI byte count, and the `# noqa` base for `app/` + `tests/` (94 at
   d39ff1c). §2 is the d39ff1c reading and is documentation, not the target.
   **The target is `0`, never a delta.**
3. `git stash` is forbidden in this repository (concurrent worktrees share the
   stash ref). Use `git worktree add` for any before/after comparison.

## 4. Approach

Six slices. The developer stages one commit (pipeline convention), but each
slice is a self-contained step whose harness (§5) must be green before the next
begins, and **the PR body lists the six with their file counts** so a reviewer
can read the diff in the order it was produced.

### 4.1 Slice 0 — pin the tool, fence the migrations (config only, 2 files)

*Nothing in this slice edits Python.* It exists so that the automation in
slices 1–2 **cannot** reach `alembic/versions/`.

`backend/pyproject.toml`:

```toml
[dependency-groups]
dev = [
    ...,
    "ruff==0.16.5",     # exact: a floating pin turns CI red on an unrelated PR
]
```

An **exact** pin, not `>=`: ruff's rule set and its formatter both move between
minor releases, and the one thing this task must not produce is a gate that
fails on a change that did not cause it. Bumping ruff becomes a deliberate,
one-line PR that re-runs the same harness.

```toml
[tool.ruff.lint.per-file-ignores]
# Migrations are frozen history. `alembic upgrade` replays them verbatim
# against production; a reformat or an import-sort of a file that already ran
# buys nothing and puts 28 files of pure noise in front of a reviewer. A
# previous slice's `ruff --fix` touched 24 of them and had to be reverted --
# this entry is what makes that structurally impossible rather than a habit.
"alembic/versions/**" = [
    "UP007", "UP045", "UP006", "UP035",   # PEP 604/585 rewrites of settled code
    "Q000", "Q003",                       # quote style of generated stubs
    "I001",                               # import order of generated stubs
    "F401",                               # `sqlmodel` imported for its side effect
    "PLR2004", "PIE790", "COM819",
    "RUF100",                             # a stale noqa here is also history
]

[tool.ruff.format]
# Same reason. The linter still reads these files (the ignores above are
# narrow and a genuinely new problem still fails the gate); the formatter is
# simply never allowed to rewrite them.
exclude = ["alembic/versions/*.py"]
```

**Verified:** with those two entries, `alembic/versions/` reports **0** lint
findings and **0** files to reformat, without a single migration byte moving.

`scripts/` needs **no** new entry: it reports 0 findings today under its
existing `INP001` ignore. Do not add ignores for findings that do not exist.

### 4.2 Slice 1 — the automation (≈195 files, 0 judgement)

```bash
cd backend
ruff format .                 # 155 files (alembic/versions excluded by config)
ruff check . --fix            # safe fixes only: 90 findings
ruff format .                 # idempotency pass
```

`ruff format` alone retires 86 findings, almost all `E501` (89 → 20) and
`COM819` (14 → 2): the formatter re-wraps the code that was over 88 columns,
which is why formatting **precedes** any manual line-length work.

`--fix` **without** `--unsafe-fixes` here, deliberately: the safe set is
ruff's own guarantee of semantic equivalence, and mixing it with the unsafe
set in one step would make a harness failure impossible to attribute.

Run the §5 harness. Nothing in this slice may move a byte of behaviour.

### 4.3 Slice 2 — FAST001, FAST002 and B008 (≈35 files)

**FAST001 is a removal, not an addition.** All 150 sites are routes that carry
*both* `response_model=X` *and* `-> X`; ruff flags the redundancy, and the fix
is to drop the decorator argument, because FastAPI derives the identical
response model from the return annotation. (The board record's phrasing —
"`response_model=` reintroduced where FAST001 asked" — describes the *goal*,
an unchanged OpenAPI document, not the direction of the edit. The goal is what
ER-3 keeps.) This is precisely why the OpenAPI proof in §5.3 is a mandatory
gate and not a nicety.

**FAST002 and B008 are one edit.** Both fire on
`x: T = Depends(f)` / `= Query(...)` / `= File(...)` / `= Form(...)`; moving
the call into `Annotated[T, Depends(f)]` retires both. B008's 101 findings are
72 `Depends`, 24 `Query`, 3 `File`, 2 `Form`.

```bash
cd backend
ruff check . --fix --unsafe-fixes --select FAST001,FAST002
ruff format .
```

**Verified on the base tree:** 282 findings, **276 fixed automatically**, and
the resulting `app.openapi()` is **byte-identical** to the base — same 157
paths, same 735 480 bytes. B008 collapses **101 → 6** as a side effect.

The **6 remaining** (identical sites for FAST002 and B008) are in
`app/api/v1/endpoints/documents.py` (2) and
`app/api/v1/endpoints/uploads.py` (4), where ruff refuses because *"a required
parameter would follow an optional parameter"*. Fix by hand: reorder the
handler's parameters so the required ones precede the defaulted ones, then
apply `Annotated`. Parameter order is not part of the URL contract, but the
§5.3 OpenAPI diff must still be empty — if reordering moves a `parameters`
array entry, restore the original order and take a
`# noqa: B008,FAST002  # reordering would move an OpenAPI parameter` instead.

**Keep APRAS-51's guard singletons.** `feedback.py` and `uploads.py` hold five
module-level `_require_* = require_permission("...")` objects. The `Annotated`
rewrite must read them, not inline the factory call:

```python
current_user: Annotated[User, Depends(_require_photo_create)]     # yes
current_user: Annotated[User, Depends(require_permission("uploads:photo_create"))]   # no
```

`tests/test_permission_alignment.py` classifies enforcement by walking
`route.dependant`, which is form-agnostic, so the rewrite is invisible to it —
but the singleton is APRAS-51's stated shape and there is no reason to lose it
while paying lint debt.

### 4.4 Slice 3 — one clock (≈54 files, 1 new module + 1 new test)

**The constraint, measured rather than assumed.** Writing a tz-aware UTC
`datetime` and its `tzinfo`-stripped twin into the same naive column produces
**byte-identical stored values** and both read back **naive**; but a value
loaded from the database can no longer be compared to an aware `datetime.now(UTC)`
— Python raises `TypeError: can't compare offset-naive and offset-aware
datetimes`. So the instant is safe either way, and the *comparisons* are not.

Measured, on the suite's own engine (SQLAlchemy 2.0.49 / SQLite, one table with
two `DateTime` columns, `datetime.now(UTC)` into one and its
`.replace(tzinfo=None)` twin into the other):

```
stored: ('2026-09-07 12:02:11.828433', '2026-09-07 12:02:11.828433')   # identical
read  : (datetime(...828433), datetime(...828433))                     # both naive
```

The Postgres path is *not* the same, and this is the one place the task
fixes behaviour rather than preserving it (measured by QA, 2026-09-08):
psycopg2 adapts the aware value to an ISO literal carrying `+00:00`, and
PostgreSQL casts it to `TIMESTAMP WITHOUT TIME ZONE` by **converting it into
the session's `TimeZone` first** — a non-UTC session stored `10:13` where a
UTC session stores `13:13` for the same instant. So the aware writers were
storing session-zone-dependent field values; `db_now()` writes naive UTC and
removes the dependence. Every reader already assumed UTC, so the correct
instant is the one `db_now()` stores. Hence:

**`backend/app/core/clock.py`** — the single helper, one source of the instant:

```python
"""The one clock (APRAS-54).

Every datetime column in this database is naive: `timezone=True` appears in
none of the 38 migrations, so every `sa.DateTime()` is
`TIMESTAMP WITHOUT TIME ZONE`. Making them aware would be a migration over
every dated table and is deliberately not this task. The consequence is
stated once, here: a value *loaded* from the database is naive, so the value
*written* to it must be naive too, or every `loaded < now` comparison in the
codebase becomes a TypeError.
"""

from datetime import UTC, date, datetime


def utc_now() -> datetime:
    """The current instant, timezone-aware, in UTC. For computation only."""
    return datetime.now(UTC)


def db_now() -> datetime:
    """`utc_now()` with `tzinfo` dropped: the same instant, in the shape the
    naive `TIMESTAMP WITHOUT TIME ZONE` columns already hold."""
    return utc_now().replace(tzinfo=None)


def today_utc() -> date:
    """The calendar date of `utc_now()`."""
    return utc_now().date()
```

The module has no imports beyond `datetime`, lints clean and formats clean
under the project config (verified). `db_now` and `today_utc` are one-line
derivations of `utc_now`, so there is exactly one place the clock is read.

**The substitution table.** One row per *shape*, because the shape is what
decides the target: a call site whose value reaches a column becomes
`db_now()`; one whose value never touches a column stays aware and becomes
`utc_now()`.

| # | Was (shape) | Becomes | Sites |
|---|---|---|---|
| 1 | `datetime.utcnow()` — naive UTC call (DTZ003) | `clock.db_now()` | 129 (99 app, 30 tests) |
| 2 | `date.today()` — **local** date call (DTZ011) | `clock.today_utc()` | 11 (5 app, 6 tests) |
| 3 | `datetime(...)` literal, tests (DTZ001) | naive literal is intended → `# noqa: DTZ001  # naive literal matching the naive column` | 4 |
| 4 | `datetime.now()` in `app/seed.py:207` — **local** naive call (DTZ005) | `clock.db_now()` — **a local→UTC shift**, see the note below | 1 |
| 5 | `default_factory=datetime.utcnow` — naive UTC *reference* **(unflagged)** | `default_factory=clock.db_now` | 65 |
| 6 | `app/models/task.py::get_utc_now` — **aware** helper into naive columns **(unflagged)** | deleted; its 12 references import `clock.db_now` | 1 + 12 |
| 7 | `app/models/plan.py::_now`, `app/models/subscription.py::_now` (`# noqa: DTZ003`) | deleted; call `clock.db_now` | 2 + refs |
| 8 | `default_factory=lambda: datetime.now(UTC)` — **aware** into naive columns **(unflagged)** | `default_factory=clock.db_now` (the lambda disappears with it) | 8 |
| 9 | `now = datetime.now(UTC)` / `obj.updated_at = datetime.now(UTC)` in services — **aware** into naive columns **(unflagged)** | `clock.db_now()` | 9 |
| 10 | `datetime.now(UTC)` in `app/core/security.py` — **aware**, never reaches a column | `clock.utc_now()` | 2 |

Rows 5–10 are **in scope on purpose, and this is the one place the task goes
beyond "make ruff quiet"**: ruff flags neither a bare *reference* to
`datetime.utcnow` nor a *tz-aware* `datetime.now(UTC)`, so a zero-findings run
is compatible with 65 surviving references to a callable Python deprecated in
3.12, three private re-implementations of the same helper (`get_utc_now`, two
`_now`s), and the four asset/purchase modules keeping their own inline **aware**
clock. Leaving any of them would make ER-2's "a single helper" false the day it
was written.

**Rows 6, 8, 9 and 10 are the complete inventory of tz-aware clock reads in
`app/` — 20 sites in six files**, measured at d39ff1c with
`grep -rnE "\.now\(UTC\)|\.now\(timezone\.utc\)" app/`:

| File | n | Lines (d39ff1c) | Row | Target |
|---|---:|---|---:|---|
| `app/models/task.py` | 1 | 40 (`get_utc_now`) | 6 | `clock.db_now` |
| `app/models/purchase.py` | 5 | 34, 37, 84, 87, 114 | 8 | `default_factory=clock.db_now` |
| `app/models/asset.py` | 3 | 43, 46, 80 | 8 | `default_factory=clock.db_now` |
| `app/services/purchase_service.py` | 6 | 228, 458, 506, 532, 573, 623 | 9 | `clock.db_now()` |
| `app/services/asset_service.py` | 3 | 52, 242, 313 | 9 | `clock.db_now()` |
| `app/core/security.py` | 2 | 42, 80 | 10 | `clock.utc_now()` |
| **total** | **20** | | | |

`grep -rn "timezone=True" alembic/versions/` returns nothing, so the asset,
purchase, inventory-movement and quote columns are naive exactly like the rest.
**18 of the 20 sites write an aware value into a naive column today** — the 17
in assets and purchases (rows 8–9) plus `get_utc_now` (row 6) — and the
database coerces every one of them, as measured above. Only the 2 JWT sites
(row 10) never reach a column, which is why they and only they stay aware.

**The aware→naive rows need response-body evidence, not just a green suite,**
because they change the in-memory shape of an attribute between assignment and
`session.refresh()`. All three subsystems refresh on every write path —
`TaskService` after every create and update; `AssetService` at lines 76, 245,
331; `PurchaseService` at 238, 461, 509, 545, 576, 636 — so the serialized
value already comes back naive from the database and the switch is
response-invisible. **Prove it rather than infer it.** The developer records in
the PR body a captured before/after response body for each of the three:

* `POST /api/v1/tasks/` — identical `created_at`, no `+00:00` on either side;
* `POST /api/v1/assets` — identical `created_at`/`updated_at`;
* `POST /api/v1/purchase-requests` — identical `created_at`/`updated_at`.

And `tests/test_tasks_api.py`, `tests/test_task_comments.py`,
`tests/test_assets.py`, `tests/test_purchase_requests.py`,
`tests/test_purchase_quotes.py` and `tests/test_purchase_decision.py` must stay
green **with no edit to any asserted timestamp string**. (There is no
`tests/test_tasks.py`; the task suite is `test_tasks_api.py` +
`test_tasks_coverage.py`.)

**One read-back test per model**, in a new `backend/tests/test_clock.py`, and
the concrete form of ER-2's assertion: write a row through `AssetService.create_asset`,
through `PurchaseService.create_request`, and through `TaskService`'s create;
read each back from the session; assert `stored.tzinfo is None` and that the
value is within one second of `datetime.now(UTC).replace(tzinfo=None)`. This is
what demonstrates that the stored instant did not move when the writer stopped
being aware.

**`today_utc()` is a real, deliberate semantic decision, not a rename.**
`date.today()` reads the *local* clock; `today_utc()` reads UTC. In production
this is a no-op (Vercel runs UTC), and on a UTC-3 developer machine between
21:00 and midnight the date advances by one — which makes local behaviour match
production rather than diverge from it. The affected columns are
`infraction_stage.applied_on` (`infraction_service.py:1106`), the
`defense_due_on` comparison (`infraction_service.py:1188`), the project
milestone dates and one finance date. Say so in the PR body; do not silently
rename.

**This retires an APRAS-44 decision, so retire it explicitly.**
`tests/test_infractions.py:44-70` carries a comment block titled *"Two clocks,
and which column each one belongs to (CR1)"* plus two helpers — `_utc_today()`
(`datetime.utcnow().date()`, row 1) and `_local_today()` (`date.today()`,
row 2), the second documented as *"The date the service computes (`applied_on`,
`defense_due_on`)"*. After this slice both clocks are UTC and the two helpers
return the same value. Do not leave a comment describing the old semantics:
collapse the two helpers into one, and rewrite the block to say that
`app/core/clock.py` is now the only clock and both columns follow it. That
edit is inside `tests/`, is covered by §5.1, and belongs in the PR body's list
of judgement sites.

**Row 4 is also a local→UTC shift, and the same rule applies.**
`app/seed.py:207` is the codebase's *only* reader of the local naive clock;
mapping it to `db_now()` moves it to UTC, exactly as `today_utc()` does for
row 2. It is demo data (and `[tool.coverage.run].omit`s `app/seed.py`), so
nothing asserts on it — but the shift is stated here for symmetry rather than
left to be discovered.

`app/core/security.py` keeps its instant **aware** — JWT `iat`/`exp` are
converted to POSIX timestamps and never touch a column. Its two sites (lines 42
and 80) call `clock.utc_now()` instead of reading the clock inline: the value is
unchanged, the literal is gone (§4.5's guard requires that), and they are the
only callers of `utc_now()` this task creates.

### 4.5 Slice 4 — the judgement long tail (≈70 files)

Rule by rule. **The default is to fix; a `# noqa` is the fallback and always
carries a reason.**

| Rule | n | Decision |
|---|---:|---|
| **PLC0415** (tests, 90) | 90 | **Per-file ignore** `tests/**`. A test that imports a model or a service inside the test function is controlling import order relative to fixtures and to `app.main`'s import-time side effects; hoisting all 90 is a real risk taken for a cosmetic gain. Precedent: `app/services/task_service.py` already carries this ignore. |
| **PLC0415** (app, 10) | 10 | **Per site.** `app/main.py:29` (`import json` inside `get_origins`) and the two in `app/api/v1/endpoints/auth.py` / `app/api/deps.py` hoist cleanly. The six in `app/api/v1/endpoints/tasks.py::list_tasks` and the one in `occurrence_service.py` are cycle breaks — hoist and run the suite; if the import cycle bites, `# noqa: PLC0415  # import cycle: app.models.task <-> app.schemas.role`. |
| **E402** | 5 | **Fix.** `app/main.py:62-63` (`Path`, `StaticFiles` after `include_router`) and `auth.py:228-230` (`ForgotPasswordRequest`, `httpx`, `os` mid-module) all hoist to the top with no cycle. |
| **A002** (`id`, 35) | 35 | **Per-file ignore** `app/api/v1/endpoints/**`. All 35 are path parameters: FastAPI derives `/{id}` from the parameter name, so renaming `id` would change the **URL** and the OpenAPI path template — a public API break, and an instant ER-3 failure. |
| **A002** (tests, 1) | 1 | **Per-line**, not a file-wide entry: `# noqa: A002  # shadows the builtin `format`; the name mirrors the query parameter` on the one site in `tests/test_uploads.py`. |
| **E712** | 4 | **`# noqa: E712  # SQLAlchemy column expression; `is True` does not compile to SQL`** in `app/services/lot_service.py`. The unsafe fix would silently break the query. 16 such `noqa`s already exist in this codebase — this follows them. |
| **RSE102** | 21 | **Fix**, `--fix --unsafe-fixes --select RSE102`. `raise X()` → `raise X`; Python instantiates identically. |
| **E501** (residual 20) | 20 | **Fix by hand** — `app/seed.py` 7, `visitor_service.py` 4, `package_service.py` 3, `resident_service.py` 2, and 4 singles. These survive the formatter because they are long strings and comments. Re-wrap them; `# noqa: E501  # <unsplittable URL/regex>` only where splitting would change a literal. **Do not** widen the existing `E501` per-file ignore to `app/**`. |
| **PLR2004** | 20 | **Fix.** All are validators in `app/schemas/{user,visitor,resident}.py` and `visitor_service.py` (`len(cpf) != 11`, …). Name the constants at module level (`CPF_DIGITS = 11`). Values unchanged. |
| **RUF003** | 7 | **Fix.** EN DASH in Portuguese comments in `tests/test_roles.py` and `tests/test_migrations_postgres.py`. Replace with `--`, the convention every comment in `app/` already uses. Comments only. |
| **BLE001** | 7 | **All 7 per-line** — the 6 app sites get `# noqa: BLE001  # best-effort <cleanup/notification>; a failure here must not fail the request` (`media_service` ×2, `storage_service`, `occurrence_service`, `project_service`, `auth.py`); narrowing these to a concrete exception type *would* be a behaviour change. The **1 test site** takes its own per-line `noqa` with its own reason rather than a file-wide `tests/**` entry, which for one occurrence would blanket-permit blind `except Exception` in every future test. |
| **S603 / S607** | 2 | **Per-file ignore** `tests/**`. `tests/test_migrations_postgres.py` shells out to `alembic` on purpose; the argv is a literal. |
| **S107** | 1 | **Per-line**, not a file-wide entry: `# noqa: S107  # fixture default, not a credential` on `tests/voting_helpers.py`'s `password="password"`. (`S105`/`S106` stay file-wide — they already are, and they have many sites.) |
| **S311** | 1 | **`# noqa: S311  # demo seed data, not a security decision`** in `app/seed.py`. |
| **SLF001** | 3 | **Per-file ignore** `tests/**`. A test asserting `TaskService._resolve_user` is testing the unit it means to test. **7** per-line `noqa`s in `tests/**` already say this and the ignore replaces them (RUF100 deletes them). The 8th `# noqa: SLF001` in the tree is `app/core/tenant_context.py:65` — outside the ignore's scope, so it stays, and it gains its reason under the `# noqa` rule below. |
| **PT011** | 1 | **Per-line**, not a file-wide entry: `# noqa: PT011  # <the specific broad raise>`. A `tests/**` entry for one site would permit bare `pytest.raises(Exception)` in every test written after this one. |
| **ARG001** | 3 | **Fix.** `authorizations.py`, `lots.py`, `uploads.py` take a parameter they never read; these are **`Depends` guards whose only job is the 403**. Rename to `_current_user` / `_payload` — but only after confirming the parameter is not a body or query field, because renaming one of those changes the OpenAPI. §5.3 catches it either way. |
| **RUF059, F841** | 7 | **Fix.** Unused unpacked/assigned locals in tests; prefix with `_` or delete. |
| **SIM102, SIM117, PLR5501, FURB110, PERF102, B007, Q003, PIE790, COM819, I001, W293, F401** | ~25 | **Fix** with `--fix` / `--fix --unsafe-fixes` per code, one code at a time, harness between. |
| **G004** | 2 | **Fix.** `logger.info(f"...")` → `logger.info("...%s", x)`. Log text unchanged. |
| **B904** | 1 | **Fix.** `raise ... from err` in `media_service.py`. |
| **PGH003** | 1 | **Fix.** `# type: ignore` → `# type: ignore[<code>]` in `auth.py`, or delete it if nothing type-checks this repo (nothing does — see §9). |
| **E741** | 1 | **Fix.** Rename the local `l` in `access_logs.py`. |
| **PLW0127** | 1 | **`# noqa: PLW0127  # Vercel entrypoint: the re-export is the contract`** in `backend/index.py`, which is `app = app` for the serverless handler. Deleting it would break the deploy. |
| **RUF043** | 2 | **Fix.** `pytest.raises(match=...)` patterns → raw strings. |

**Then, and this is not optional:** adding the three per-file-ignore blocks —
`alembic/versions/**` (§4.1), `tests/**` extended with
`PLC0415, SLF001, S603, S607`, and `app/api/v1/endpoints/** = ["A002"]` — makes
existing `# noqa` comments redundant, and `RUF100` (selected by `ALL`) turns
each into a **new finding**. Measured at d39ff1c with exactly that ignore set
applied and the full rule selection active: **18**. Finish the slice with

```bash
ruff check . --select RUF100 --fix     # never run --select RUF100 alone without --fix:
                                       # in isolation every noqa for an unselected rule looks unused
```

and then a **full** `ruff check .`, which is the only reading that counts.

**The `# noqa` rule, and its cap.** The scope of the cap is
`backend/app/` + `backend/tests/`, and **its base there is 94** — 40 in `app/`,
54 in `tests/`, measured at d39ff1c with
`grep -rho "# *noqa" app/ tests/ | wc -l`. (96 is the *whole-backend* figure,
which additionally counts one `noqa` in `alembic/` and one in `index.py`; both
are outside this cap and outside this rule.) After this task:

* every `# noqa` under `backend/app/` and `backend/tests/` is written
  `# noqa: <CODES>  # <reason>` — codes, two spaces, then a sentence saying why
  the finding is correct-as-written. (Verified: ruff parses the trailing
  comment fine and does not report `RUF100` for it.)
* `alembic/versions/**` is exempt (frozen history, and its per-file ignore
  makes its `noqa`s moot anyway). `backend/index.py`'s one `noqa` is outside the
  cap's scope but still carries its reason (`PLW0127`, above).
* **the arithmetic, stated rather than waved at.** RUF100 removes **18**
  (measured). The slices above add **19 firm**: DTZ001 ×4 (§4.4 row 3),
  E712 ×4, BLE001 ×7 (6 app + 1 test), S311 ×1, and the three single-site
  entries narrowed above (`S107`, `PT011`, tests `A002`) ×3. Up to **13 more
  are conditional** and only appear if the harness forces them: PLC0415 ≤ 7
  (`app/` cycle breaks that do not hoist), FAST002/B008 ≤ 6 (§4.3's fallback).
  So the landed count is **95 at the floor and 108 at the ceiling**:
  `94 − 18 + 19 = 95`, `+13 = 108`.
* the gate is therefore **≤ 108**, with the intent being the floor: the PR body
  states the branch-point base (re-measured per §3.2), the landed count, and a
  per-code itemization of every `# noqa` added and every one removed, and each
  conditional one above 95 **names the harness failure that forced it**.

Enforce it mechanically with a new `backend/tests/test_lint_hygiene.py`:

1. every `# noqa` in `app/**` and `tests/**` matches
   `#\s*noqa:\s*[A-Z]+[0-9]+(\s*,\s*[A-Z]+[0-9]+)*\s+#\s+\S`;
2. the total count of `# noqa` in `app/**` + `tests/**` is `<= NOQA_CAP`, a
   module constant set to the number the PR actually lands with (a forward
   regression guard for the *next* task), and that number is itself `<= 108`;
3. **the clock guard, and it is a literal-substring rule.**
   `backend/app/core/clock.py` is the only module under `backend/app/**` whose
   **source text contains** any of the three literals `datetime.utcnow`,
   `date.today(` or `datetime.now(` — the last one **with any argument,
   including `datetime.now(UTC)`**. The test reads every `*.py` under `app/`
   and asserts the set of files containing any of the three is exactly
   `{app/core/clock.py}`. Because it is a text scan and not an AST walk, the
   three literals must not appear in comments or docstrings either: refer to
   "the current instant" or to `clock.utc_now()` in prose. Inside `clock.py`
   the single permitted occurrence is `utc_now`'s own
   `return datetime.now(UTC)`; `db_now` and `today_utc` derive from it and
   contain none of the three. This is what stops the next task reintroducing a
   second clock, and it is why §4.4 row 8/9/10 exist — under this rule a
   surviving `datetime.now(UTC)` in `asset.py` or `security.py` is a red test,
   not a matter of taste.

This test is what makes ER-1's *"only justified per-line `# noqa`"* and ER-2's
*"a single helper"* checkable by someone holding nothing but the ER list.

### 4.6 Slice 5 — the gate (3 files)

**`.github/workflows/ci.yml`** — its own job, for the same reason
`backend-migrations` is its own job: it runs in parallel, `Backend Tests`'s
duration is unchanged by construction, and *"Backend Lint (ruff)"* names the
failure class before anyone opens a log.

```yaml
  backend-lint:
    name: Backend Lint (ruff)
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v6
    - name: Set up uv
      uses: astral-sh/setup-uv@v8.1.0
      with:
        enable-cache: false
        pyproject-file: backend/pyproject.toml
    - name: Set up Python 3.13
      run: uv python install 3.13
    - name: Install dependencies
      run: cd backend && uv sync --all-groups
    # Two commands, not one: `check` and `format` fail for different reasons
    # and a reviewer should not have to read a log to tell which.
    # `--output-format=github` annotates the finding on the diff.
    - name: ruff check
      run: cd backend && uv run ruff check . --output-format=github
    - name: ruff format --check
      run: cd backend && uv run ruff format --check .
```

Neither command takes `--exit-zero`, `--fix`, `--statistics` or a `continue-on-error`:
**any** finding fails the job. `sonarcloud`'s `needs:` is deliberately **not**
extended — this job feeds it no artefact, exactly as the existing comment says
of `backend-migrations`.

**`AGENTS.md`** — three edits, no more:

1. the *CI/CD* bullet list gains: **Lint** — `ci.yml`'s `backend-lint` job runs
   `ruff check` and `ruff format --check` over `backend/` and fails on any
   finding. `ruff` is pinned exactly in `backend/pyproject.toml`'s dev group,
   so the local and CI readings agree.
2. the Backend stack table's *Linting* row: `Ruff 0.16.5 (all rules selected;
   line-length 88; **CI gate**)`.
3. a short subsection under the backend section — the pre-commit hint, the
   `# noqa: CODE  # reason` convention and its cap, the fact that
   `alembic/versions/**` is never reformatted and its migrations are never
   edited, and that `app/core/clock.py` is the only clock:

   ```bash
   # before committing anything under backend/
   cd backend && uv run ruff check . && uv run ruff format --check .
   # or, to apply: uv run ruff format . && uv run ruff check . --fix
   ```

No `.pre-commit-config.yaml` is added — this repository has none, and
introducing a hook framework is a separate decision.

## 5. The proof harness

Run **at every slice boundary**, in this order. A red step means revert the
slice, not "adjust the baseline".

**5.0 Per-slice evidence is required, not implied.** "Green at every slice
boundary" is unfalsifiable after the fact if only the first and last runs are
written down. The PR body therefore carries **one row per slice**, seven rows in
all (branch-point base + the six slices of §4):

| Slice | files | pytest passed/failed/skipped | cov % | `ruff check` residual | OpenAPI diff | artefact sha256s |
|---|---:|---|---:|---:|---|---|

The last two columns are `empty`/`non-empty` and `unchanged`/`changed`. This is
the record that lets a reviewer confirm the six steps happened in the stated
order without re-running a ~250-file diff's worth of work. It is also an honest
cost: §5.1 is the expensive gate — the suite runs in **>25 minutes** — so six
boundaries mean roughly three hours of harness time, and that is budgeted, not
discovered (see §7).

**5.1 Full suite, from the same env as CI.**

```bash
cd backend
SECRET_KEY=test POSTGRES_URL=postgresql://postgres:postgres@localhost/unused \
  uv run pytest -q
```

The base tree collects **3135 tests** (`pytest --collect-only -q -o addopts=`,
measured at d39ff1c; `tests/test_migrations_postgres.py` self-skips without
`TEST_POSTGRES_URL`, so that number is `passed + skipped`).
The **passed/failed/skipped counts must equal the base run's, exactly**, and
`--cov-fail-under=90` (already in `pytest.ini`) must hold with a **coverage
percentage ≥ the base run's**. Capture the base numbers on the branch point
before slice 0 and paste both runs into the PR body. A test count that *rises*
is as much a failure as one that falls — this task adds exactly **two** test
files (`tests/test_clock.py`, §4.4; `tests/test_lint_hygiene.py`, §4.5), and
their case count is the only permitted delta.

**5.2 Migration tests on real Postgres.** Per `AGENTS.md`'s recipe:

```bash
cd backend && TEST_POSTGRES_URL=postgresql://postgres@localhost:55432/apras_test \
  SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v
```

All 53+ cases pass, **none skipped**. This is the direct check that
`alembic/versions/` really was left alone, and it is ER-2's named gate.

**5.3 OpenAPI, offline, byte-for-byte.** No server, no database connection
(`create_engine` does not connect at import; verified):

```bash
# in each of the two worktrees
cd backend && SECRET_KEY=test POSTGRES_URL=postgresql://x:x@localhost/x \
  uv run python -c "import json; from app.main import app; \
    print(json.dumps(app.openapi(), sort_keys=True, indent=2, ensure_ascii=False))" \
  > /tmp/openapi-<base|head>.json

diff -u /tmp/openapi-base.json /tmp/openapi-head.json      # must be empty
```

Base reading: **157 paths, 735 480 bytes**. `sort_keys=True` removes dict
ordering as a source of false diffs; `ensure_ascii=False` keeps the Portuguese
summaries comparable.

**5.4 The five frozen artefacts, byte-identical.**

```bash
cd backend && git diff --stat master...HEAD -- tests/data/     # must be empty

# and the hashes, in BOTH worktrees, compared -- a list of hashes with nothing
# to compare it to proves nothing:
sha256sum tests/data/parity_matrix_baseline.json \
          tests/data/parity_matrix_baseline_40.json \
          tests/data/parity_matrix_baseline_44.json \
          tests/data/parity_matrix_baseline_51.json \
          tests/data/legacy_role_bundles.json > /tmp/artefacts-<base|head>.txt

diff /tmp/artefacts-base.txt /tmp/artefacts-head.txt      # must be empty
```

Five, not four: `parity_matrix_baseline_51.json` joined the set in APRAS-51,
after the board record for this task was written.

**5.5 Diff fences.** All four must print nothing:

```bash
# `master...HEAD`, not `master`: the three-dot form compares against the merge
# base, so a `master` that advances while the branch is open cannot inject
# spurious paths into these fences.
git diff --stat master...HEAD -- frontend/                     # ER-3: frontend untouched
git diff --stat master...HEAD -- backend/alembic/versions/     # §4.1: history untouched
git diff --stat master...HEAD -- backend/tests/data/           # 5.4
git diff --stat master...HEAD -- .meridian/                    # not this agent's file
```

**5.6 The gate itself.** `ruff check .` prints `All checks passed!` and
`ruff format --check .` prints `N files already formatted` with no
`unformatted:` line — run from `backend/`, with the pinned ruff
(`uv run ruff`), not the one on `PATH`.

## 6. Files-touched budget

| Slice | Files | Nature |
|---|---:|---|
| 0 — pin + fences | 2 | `pyproject.toml`, `uv.lock` |
| 1 — format + safe fix | ≈195 | whitespace, wrapping, import order |
| 2 — FAST/B008 | ≈35 | endpoint signatures |
| 3 — clock | ≈54 + 2 new | one-token substitutions; `app/core/clock.py`; ≈50 naive-clock files **plus the four aware-clock files of §4.4 rows 8–9 — `app/models/purchase.py`, `app/models/asset.py`, `app/services/purchase_service.py`, `app/services/asset_service.py` (17 of the 20 aware sites)** — plus `app/core/security.py` (row 10, already inside the ≈50) and the new `tests/test_clock.py` |
| 4 — long tail | ≈70 | per-rule, per-site |
| 5 — gate + docs | 3 + 1 new test | `ci.yml`, `AGENTS.md`, `pyproject.toml`, `tests/test_lint_hygiene.py` |
| **total** | **≈250 of 292 backend `.py` files** (a *union*: slice 3's four aware-clock files are already inside slice 1's ≈195, so naming them does not raise the union — it raises what a reviewer must look at) | **0 behavioural lines** |

Large by line count and trivial by review weight: the reviewer's job is §5's
six gates plus the ~40 sites in slices 3 and 4 that carry a judgement, and the
PR body must list those sites by name so they can be read without a diff hunt.
**Assets and purchases are named here because the diff reaches two subsystems
the rest of this task never mentions**, and a reviewer who does not expect them
will read `purchase_service.py` in the diff as scope creep rather than as §4.4
row 9.

**Harness cost, budgeted rather than discovered.** §5 runs at seven boundaries
(base + six slices) and §5.1 alone takes **>25 minutes**, so the harness is
roughly three hours of wall time across the task. That is the price of §5.0's
per-slice evidence and it is the correct price: the alternative is a
≈250-file diff whose intermediate states nobody can attest to.

## 7. Risks

| Risk | Mitigation |
|---|---|
| `ruff format` rewrites a file the formatter and a human disagree about | The formatter is the arbiter; there is no exception list beyond `alembic/versions/`. |
| FAST001's removal changes a response body for a route whose annotation is a *superset* of its old `response_model` | §5.3 (schema) + §5.1 (bodies). If the diff is non-empty, restore `response_model=` on that route and `# noqa: FAST001  # annotation is wider than the wire contract`. |
| The `Annotated` rewrite moves a parameter and changes the OpenAPI | §5.3. |
| A naive/aware mix escapes into a comparison | §5.1 would raise `TypeError`, loudly. `db_now()` is the only writer and returns naive. |
| **The aware→naive switch in assets and purchases (§4.4 rows 8–9, 17 sites) changes an attribute's in-memory shape between assignment and `session.refresh()`, and something serializes or compares it in that window** | Every write path in both services commits and refreshes (`asset_service.py` 76/245/331, `purchase_service.py` 238/461/509/545/576/636), so the serialized value already comes from the database and is already naive. Proven, not assumed: §4.4's captured `POST /api/v1/assets` and `POST /api/v1/purchase-requests` before/after bodies, `tests/test_clock.py`'s read-back assertion per model, and `test_assets.py` / `test_purchase_*.py` green with no edited timestamp string. If a body does move, the fallback is `clock.utc_now()` at that one site with a `# noqa`-style comment naming the response field, and the site goes in the PR body. |
| `today_utc()` shifts a date on a non-UTC machine | Documented in §4.4 and the PR body; production is UTC. |
| The `today_utc()` change retires APRAS-44's documented two-clock split | §4.4 names `tests/test_infractions.py:44-70`, `applied_on` (`infraction_service.py:1106`) and `defense_due_on` (`:1188`) explicitly, and requires the comment block and the two now-identical helpers be collapsed rather than left describing the old semantics. |
| Ruff version drift turns CI red on an unrelated PR | Exact pin, §4.1. |
| Merge pain against APRAS-53 | §3.1: branch after it lands. |

## 8. Expected Results

- [ ] **ER-1 — `cd backend && uv run ruff check .` exits `0` with `All checks passed!`, and `uv run ruff format --check .` reports zero files to reformat**, under the project's own `pyproject.toml` (`select = ["ALL"]`, line-length 88) with the pinned `ruff==0.16.5`. The global `[tool.ruff.lint].ignore` list gains **no new entry**. Silencing happens only through (a) the three documented `per-file-ignores` blocks of §4.1/§4.5 — `alembic/versions/**`, `tests/**` (extended with `PLC0415, SLF001, S603, S607`), and `app/api/v1/endpoints/** = ["A002"]` — each with its reason in a comment, and no file-wide entry added for a rule with a single occurrence (`S107`, `PT011`, `BLE001` and the `tests/` `A002` take per-line `# noqa`s instead); and (b) per-line `# noqa: <CODES>  # <reason>`, every one of which carries codes and a reason and matches `#\s*noqa:\s*[A-Z]+[0-9]+(\s*,\s*[A-Z]+[0-9]+)*\s+#\s+\S`. The total `# noqa` count under `backend/app/` + `backend/tests/` (base **94** at d39ff1c: app 40, tests 54 — re-measured at the branch point per §3.2) is **≤ 108**, is pinned as `NOQA_CAP` in `backend/tests/test_lint_hygiene.py` and asserted there, and the PR body states base → landed with a per-code itemization of every `# noqa` added and removed.

- [ ] **ER-2 — every clock read in `backend/app/` is served by one helper, `backend/app/core/clock.py`, and the stored instant is unchanged.** `DTZ001/DTZ003/DTZ005/DTZ011` report **0**, and `backend/app/core/clock.py` is **the only module under `backend/app/**` whose source text contains any of the literals `datetime.utcnow`, `date.today(` or `datetime.now(` — the last with *any* argument, `datetime.now(UTC)` included** (asserted by `backend/tests/test_lint_hygiene.py` as a text scan over every `app/**/*.py`; the single permitted occurrence is `utc_now`'s own `return datetime.now(UTC)`). This covers all **20** tz-aware sites measured at d39ff1c — `models/task.py` 1, `models/purchase.py` 5, `models/asset.py` 3, `services/purchase_service.py` 6, `services/asset_service.py` 3 become `clock.db_now`, and `core/security.py`'s 2 JWT sites become `clock.utc_now()`. **No migration is added and no column type changes** — the columns stay `TIMESTAMP WITHOUT TIME ZONE`, and `db_now()` returns the naive UTC value they already hold (today those aware writers are coerced to the same naive UTC value on write), so a row written before this task and one written after are directly comparable. A new `backend/tests/test_clock.py` proves this **once per model** — `Asset`, `PurchaseRequest` and `Task`: write through the service, read back, assert `tzinfo is None` and within one second of `datetime.now(UTC).replace(tzinfo=None)`. The PR body carries before/after response bodies for `POST /api/v1/tasks/`, `POST /api/v1/assets` and `POST /api/v1/purchase-requests` showing identical timestamp fields with no `+00:00` on either side. `tests/test_migrations_postgres.py` runs green against a real `TEST_POSTGRES_URL`, all cases, **none skipped**.

- [ ] **ER-3 — no behaviour changed, and the six slices are evidenced one by one.** The full suite passes with the **same passed/failed/skipped counts** as the pre-task baseline (**3135 tests collected** at d39ff1c), the only permitted delta being the cases of the two new files (`tests/test_clock.py`, `tests/test_lint_hygiene.py`), and **coverage ≥ the baseline percentage**, `--cov-fail-under=90` holding. The five frozen artefacts (`parity_matrix_baseline.json`, `_40`, `_44`, `_51`, `legacy_role_bundles.json`) are **byte-identical** — `git diff --stat master...HEAD -- backend/tests/data/` is empty and the `sha256sum` list matches the base worktree's line for line. `diff` of `app.openapi()` dumped with `sort_keys=True` before and after is **empty** (157 paths, 735 480 bytes at d39ff1c), despite FAST001 rewriting every `response_model=`/return-annotation pair. `git diff --stat master...HEAD -- frontend/` and `git diff --stat master...HEAD -- backend/alembic/versions/` are both **empty**. The PR body carries §5.0's **seven-row per-slice table** (branch-point base + six slices), each row giving file count, pytest passed/failed/skipped, coverage %, `ruff check` residual, OpenAPI diff empty/non-empty and artefact hashes unchanged/changed.

- [ ] **ER-4 — CI fails on any finding, and it is written down.** `.github/workflows/ci.yml` carries a `backend-lint` job running `ruff check .` and `ruff format --check .` from `backend/` with no `continue-on-error` and no `--exit-zero`; a run triggered with `gh workflow run ci.yml --ref <branch>` shows it green on the finished branch, and a deliberately reintroduced finding (e.g. an unsorted import, pushed and then reverted, or reproduced locally) turns it **red**. `ruff==0.16.5` is an exact pin in `backend/pyproject.toml`'s dev group and present in `uv.lock`. `AGENTS.md` states the gate in its CI/CD list, the pre-commit command, the `# noqa: CODE  # reason` convention with its cap, that `alembic/versions/**` is never reformatted, and that `app/core/clock.py` is the only clock.

## 9. Out of Scope

* **Frontend lint.** `npm run lint` reports ~391 problems in `frontend/`. It is
  a different tool, a different rule set and a different reviewer; it gets its
  own task. `git diff --stat master...HEAD -- frontend/` must be empty (ER-3).
* **Expanding or changing the rule set.** `select = ["ALL"]` and the existing
  global `ignore` list are inputs to this task, not outputs. No rule is added
  and none is removed from the global ignore. (Removing an entry — `TRY`, `EM`,
  `ANN` — is a legitimate future task, and it is *only* affordable once the
  gate exists.)
* **`mypy` or any type checker.** None is configured in this repository today.
* **Editing `alembic/versions/**`.** Fenced by §4.1 and by ER-3's diff check.
* **Making datetime columns timezone-aware.** That is a migration over every
  dated table plus a read-path audit; §4.4 exists precisely so it is not
  smuggled in here.
* **Refactoring.** No function is extracted, no module is split, no dead code
  is deleted beyond what `F401`/`F841`/`RUF059` name. If a fix requires
  judgement about *design*, the answer is a justified `# noqa` and a follow-up
  task.
