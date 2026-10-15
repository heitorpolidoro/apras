# APRAS-89 — Read the obra dataset from the contractor's schedule instead of a hard-coded list

## What changed since this task was written

The task's `justification` (2026-09-23) and its original `expected_results`
describe `backend/scripts/sync_drive_obras.py`, a hard-coded
`REAL_MACEDO_DATASET` literal, and the `.xlsx`
`Cronograma_Fisico_Financeiro_Altos_da_Serra_VI(2).xlsx`. Facts on the ground
on 2026-10-05:

- The hard-coded literal still exists, in `backend/scripts/sync_drive_obras.py`
  (465 lines, `REAL_MACEDO_DATASET` at line 22, three projects with 6/4/3
  hand-written milestones). The file is **untracked and git-excluded**
  (`.git/info/exclude` lines 21-22), so it is not part of the repository and
  never was. Its dates for *Coberturas e Portaria (Edificação)* are
  2026-09-01 → 2027-02-28.
- **It no longer feeds anything.** The obra rows that `GET /api/v1/projects`,
  `GET /api/v1/projects/report` and the public
  `GET /api/v1/public/tenants/{slug}/projects/report` serve for tenant
  `aprasvi` were produced by a *different*, also-untracked operator tool,
  `backend/scripts/sync_obras_from_drive.py`, which downloads the contractor's
  two `.mpp` schedules from Drive, flattens them with MPXJ, derives stages and
  a planned curve, and **replaces** the tenant's projects. Its output is on
  disk at `docs/obras-fonte/backup-obras.json` (gitignored): *Portarias —
  Entradas e Saídas* (26 milestones, 3.1%, 2026-09-14 → 2027-03-04) and *Sede
  Social — Reforma* (17 milestones, 4.2%, 2026-09-21 → 2027-02-25).

So the premise "the API serves a hard-coded list" is **already false**, and the
defect the task diagnosed (wrong hard-coded dates) is **already fixed in
production data**. What is *not* fixed is that every rule which interprets the
contractor's schedule — which nodes are stages, which tasks are purchases,
which container to collapse, how a percentage is weighted, what the
`detail_json` contract is — lives exclusively in an untracked file that no
reviewer sees, no test covers and no CI run exercises, while its **reader**
(`app/services/project_report_service.decode_stage_detail`,
`planned_to_date`) is committed, documented and tested. This task closes that
asymmetry.

## Scope

Move the contractor-schedule **interpretation** into the repository as a pure,
tested service, and pin it with a committed fixture so CI exercises it.

In scope:

- A new pure module under `backend/app/services/` that turns flattened
  schedule rows plus project metadata into the payload
  `ConstructionProject` + `ProjectMilestone` rows are built from — including
  `planned_progress_json` and each milestone's `detail_json`.
- A committed fixture of flattened rows derived from the real Portarias
  schedule, and a committed expected-output pair.
- Tests that fail if any single interpretation rule is removed.
- A round-trip test proving the module's `detail_json` output is accepted by
  `decode_stage_detail`, and its `planned_progress_json` output by
  `planned_to_date`.

Explicitly **not** in scope (see "Out of Scope" for the rest): any network
call, any Google Drive or OAuth code, any `.mpp`/JVM parsing, any database
write, any endpoint change, any frontend change, any schema change, and the
financial `.xlsx`.

## Approach

### Behavior

`backend/app/services/obra_schedule_import.py` exposes a transform with no
I/O: given a list of flattened schedule rows — each row carrying an id, an
outline level, a name, a summary flag, a duration in days, an ISO start, an
ISO finish and a percentage complete — and the project's own metadata (title,
description), it returns the project payload the sync writes:
`physical_progress_pct`, `start_date`, `estimated_completion_date`, `status`,
`planned_progress_json`, and an ordered list of milestone payloads each with
`title`, `description`, `detail_json`, `status`, `due_date`,
`completion_date`, `display_order`.

The interpretation rules it must implement are the ones
`sync_obras_from_drive.py` already applies, and the spec adopts them as
behaviour to preserve, not to redesign:

1. **Purchase tasks are excluded** from both dates and percentages (a task
   whose name matches *solicita* or *compra*). Keeping them in one number but
   not the other stops the parts summing to the whole.
2. **A level-2 node holding more than 80% of the total duration is a
   container**, not a stage, and is replaced by its children.
3. **A stage is the deepest grouping level above the leaves** — not a fixed
   outline level; it lands on 2, 3 or 4 depending on how deep the branch goes.
   A summary node qualifies only when all its immediate children are leaves.
4. **Percentage is duration-weighted** over a stage's non-purchase leaves, and
   the project's own percentage is duration-weighted over all such leaves.
5. **A stage at or above 99.5% is `DONE`**, above 0% is `IN_PROGRESS`,
   otherwise `NEXT_STEPS`; a `DONE` stage's `completion_date` is its finish.
6. **The planned curve** is the cumulative duration-weighted percentage by
   finish month, each point `{month, pct}` with `pct` rounded to 2 places.
7. **Titles are title-cased with Portuguese minor words left lowercase**, the
   `INFRAS E LANÇAMENTOS DE [INSTALAÇÕES] ` prefix stripped, `- ` normalised
   to ` — `, and a child's prefix dropped when every significant word of it
   appears in the parent. A stage under a non-container parent is titled
   `"<parent> · <stage>"`.
8. **`detail_json` is exactly `{pct, start, leaves:[{name, pct, start,
   finish}]}`** with leaf names stored **raw**, as the schedule spells them.
   Leaf `start`/`finish` may be `null`. No other keys. This is the contract
   `decode_stage_detail` reads and `backend/tests/data/obras_stage_detail_fixture.json`
   is pinned against; title-casing a leaf name here would invalidate a fixture
   that already passed review.
9. **A schedule that yields no stage is an error**, raised with a message
   naming the project, not a silently empty project.

The module must contain no hard-coded project dataset: every title that
belongs to the *contractor's* data comes from its arguments. The only
literals it owns are the rules above (the purchase pattern, the thresholds,
the minor-word set).

The module does **not** read a file, does not know what `.mpp` is, does not
import `sqlmodel`, and does not touch a `Session`. `MilestoneStatus` and
`ProjectStatus` from `app.models.enums` are the only model imports it needs.

It is also **deterministic and clockless**: nothing it returns depends on the
current date. A stage's status comes from its percentage, never from comparing
a date to today. Beyond keeping the golden fixture from rotting, this is the
lint gate — `tests/test_lint_hygiene.py` text-scans everything under `app/` for
`date.today(`, `datetime.utcnow` and `datetime.now(` with any argument, and
`app/core/clock.py` is the only module allowed a clock.

### Where the operator script fits

`backend/scripts/sync_obras_from_drive.py` stays untracked, unmodified by this
task, and keeps everything this task deliberately leaves out: the Drive
listing and download, the OAuth token under `~/.jarvis/data/sync_tokens/`, the
JVM/MPXJ `.mpp` read, the snapshot, and the DB replace. That split is the
decision this task makes explicit: **access stays operator-side, interpretation
moves in-repo**, because access changes with credentials and sharing while
interpretation changes with the schedule's format, and the two must not be one
file.

To make the eventual swap a one-line import rather than a translation layer,
the module's **input row shape must be exactly what that script's `read_mpp`
already produces** (`id`, `lvl`, `name`, `summary`, `dur`, `start`, `finish`,
`pct`) and its **output shape exactly what that script's `replace` already
consumes**. Re-pointing the script at the module is an operator-side edit,
outside this task's diff and outside its expected results; until it happens
the rules exist in two places, which is a known and accepted cost of not
editing an uncommittable file, and the follow-up is named in "Out of Scope".

### Files touched

- `backend/app/services/obra_schedule_import.py` — new. The pure transform and
  its rule constants.
- `backend/tests/data/obra_schedule_rows_fixture.json` — new. Flattened rows
  derived from the real Portarias schedule, **trimmed** to the smallest subset
  that exercises every rule: the 80%-container and a sibling phase below it,
  at least three stages at differing outline depths, at least one purchase
  task, at least one leaf with a null date, and at least one stage above 99.5%.
  Derived by running the operator script's `read_mpp` locally once; the `.mpp`
  itself stays gitignored under `docs/obras-fonte/`.
- `backend/tests/data/obra_schedule_expected.json` — new. The transform's
  expected output for that fixture, committed as a golden file in the manner of
  the existing `parity_matrix_baseline*.json` files.
- `backend/tests/test_obra_schedule_import.py` — new. The golden comparison,
  one test per rule, and the round-trip into
  `project_report_service.decode_stage_detail` / `planned_to_date`.

Nothing else changes. No endpoint, no model, no migration, no frontend file,
and no dependency — so `backend/requirements.txt` is **not** regenerated. If a
dependency does become necessary, that manifest is generated from the uv lock
(`uv export --format requirements-txt --no-hashes -o requirements.txt`) and
regenerating it is part of the same change, because it is the Vercel
function's install manifest.

### Test criteria

Every test must fail when the rule it names is removed. The project's standing
defect — recorded in `docs/audits/APRAS-111-test-suite-audit.md` — is a test
whose prose claims a guarantee no assertion holds, so each test must assert on
a **value that moves** when the rule is deleted, not merely that the call
returns something:

- **Golden**: the transform over the committed fixture equals
  `obra_schedule_expected.json` exactly, compared as parsed JSON.
- **Purchase exclusion**: adding a purchase-named leaf with a large duration
  and a 100% completion to the fixture rows leaves both the project
  percentage and the containing stage's percentage unchanged, and the project
  `start_date` unchanged.
- **Container collapse**: the stage titles include the container's children
  and exclude the container's own name; raising the container's share above
  the threshold in a copy of the rows changes the stage count.
- **Weighting**: a stage whose two leaves have durations 1 and 9 and
  completions 100 and 0 reports 10%, not 50%.
- **Done threshold**: a stage at 99.5% is `DONE` with a `completion_date`
  equal to its finish; one at 99.4% is `IN_PROGRESS` with
  `completion_date is None`.
- **Planned curve**: the points are in ascending month order, strictly
  non-decreasing in `pct`, and the last point is 100.0.
- **Titles**: a known raw stage name maps to its known cleaned title, and the
  parent-prefix drop is asserted on a case whose parent carries the prefix
  *and* on a case whose parent does not, so a greedier rule reddens.
- **Leaf names raw**: at least one asserted leaf name is a SHOUTING string
  identical to the fixture's, so title-casing it reddens.
- **Round trip**: every milestone's `detail_json` passed to
  `decode_stage_detail` returns a non-`None` `StageDetail` whose leaf count and
  `pct` match the payload, and `planned_to_date` over the emitted
  `planned_progress_json` with a pinned `today` returns the expected point —
  so the writer cannot drift from the committed reader.
- **Empty schedule**: rows that yield no stage raise, and the raised message
  contains the project title.

Run with `cd backend && SECRET_KEY=test uv run pytest tests/test_obra_schedule_import.py`;
the suite's `--cov=app --cov-fail-under=90` gate applies, and because the new
module sits under `app/` it is measured.

### What cannot be verified in CI, and the surrogate

Three things in this area touch the outside world and therefore **cannot** be
expected results:

- **Google Drive and the OAuth token.** No test may list a Drive folder,
  download a file, or read `~/.jarvis/data/sync_tokens/`. The surrogate is that
  this task contains no network code at all, which is itself checkable by grep
  (see the results below).
- **The `.mpp` parse.** MPXJ needs a JVM and the file is gitignored. The
  surrogate is the committed flattened-rows fixture: the transform is tested
  against the rows a real parse produced, and the parse stays operator-side.
- **The whole-schedule aggregate against production** — that the full
  Portarias file yields 26 milestones, 3.1% and 2026-09-14 → 2027-03-04.
  Reproducing it needs the gitignored `.mpp` and a JVM, so it is an
  operator-side check, recorded here as *not* a CI criterion. Its CI surrogate
  is the trimmed golden pair above.

## Expected Results

- [ ] `grep -rl REAL_MACEDO_DATASET backend/app backend/tests` returns nothing,
      and `git ls-files backend | xargs grep -l REAL_MACEDO_DATASET` returns
      nothing — no tracked file carries a hard-coded obra dataset.
- [ ] `backend/app/services/obra_schedule_import.py` exists and contains no
      contractor project title: grepping it for `Portarias`, `Sede Social`,
      `Macedo`, `Muro Perimetral` and `Quadra` returns nothing.
- [ ] The module makes no network call and reads no file: grepping it for
      `requests`, `httpx`, `urllib`, `googleapi`, `gspread`, `oauth`, `jpype`,
      `mpxj`, `open(`, `Path(` and `sqlmodel` returns nothing.
- [ ] `cd backend && SECRET_KEY=test uv run pytest tests/test_obra_schedule_import.py`
      passes, and `--collect-only -q` on that file reports at least 10 tests.
- [ ] `backend/tests/data/obra_schedule_rows_fixture.json` and
      `backend/tests/data/obra_schedule_expected.json` exist, are tracked by
      git, and the golden test compares the transform's output against the
      latter with no field excluded.
- [ ] Removing the purchase-exclusion rule from the module makes at least one
      named test fail; the same holds independently for the container
      threshold, the 99.5% done threshold, the duration weighting, and the raw
      leaf-name rule. A reviewer verifies this by deleting each rule in turn
      and re-running the file.
- [ ] Every milestone the transform emits for the committed fixture is accepted
      by `app.services.project_report_service.decode_stage_detail`: the
      round-trip test asserts a non-`None` `StageDetail` per milestone, with
      matching leaf count and `pct`, and fails if the emitted payload gains or
      loses a key.
- [ ] The transform's `planned_progress_json` for the fixture is accepted by
      `planned_to_date` with a pinned `today`, returning a pinned numeric
      value, not `None`.
- [ ] Rows that yield no stage raise, and the test asserts the project title
      appears in the message — asserted on the message text, not merely that
      an exception type was raised.
- [ ] `cd backend && uv run ruff check . && uv run ruff format --check .` passes.
- [ ] `cd backend && SECRET_KEY=test uv run pytest` passes with the existing
      `--cov-fail-under=90` gate, and `git diff --stat` shows
      `backend/requirements.txt` unchanged and no file under `backend/alembic/`
      added or modified.

## Out of Scope

- **The financial `.xlsx`.** `Cronograma_Fisico_Financeiro_Altos_da_Serra_VI(2).xlsx`
  is the only source that carries money, and `total_budget` is still typed by
  hand (0.00 on *Sede Social — Reforma* today, preserved across syncs by the
  operator script's `keep_budget`). Reading it is a separate task, and whether
  it is what this task was meant to be is question 1 below.
- **`executed_budget` and measured actuals.** The task's own justification
  established that no available source carries them; nothing here changes that.
- **Drive access, OAuth, the `.mpp` parse, the DB replace** — all stay in
  `backend/scripts/sync_obras_from_drive.py`, untracked and unmodified.
- **Re-pointing that script at the new module.** A follow-up task, operator-side.
- **Deleting the dead `backend/scripts/sync_drive_obras.py`.** Untracked, so
  not a repository change; question 2 below.
- **`backend/app/seed_demo.py`'s obra list.** Deliberately fictional demo data
  for the demo tenant, with relative dates; not the contractor's data and not
  this task's concern.
- **Muro Perimetral and Quadra Poliesportiva.** Absent from every schedule.
- **Frontend, endpoints, schema.** Untouched.

## Questions for the operator

1. The task was written against the financial `.xlsx`; production has since
   been fed from the two `.mpp` schedules, so the hard-coded list the title
   names is already dead. Is APRAS-89 satisfied by bringing the `.mpp`
   interpretation into the repository under test (this spec), with reading the
   `.xlsx` for `total_budget` as a separate task — or did you want the `.xlsx`
   money ingestion here, in which case this spec's scope is wrong?
2. May `backend/scripts/sync_drive_obras.py` be deleted from the working tree?
   It is untracked, superseded, and its dates are the wrong ones; running it
   today would clobber the correct data.
3. Committing a trimmed, real-derived subset of the Portarias schedule rows to
   `backend/tests/data/` publishes contractor task names into git, which
   `.gitignore`'s rule for `**/obras-fonte/` deliberately avoids — though
   `backend/tests/data/obras_stage_detail_fixture.json` already does exactly
   that. Confirm the precedent holds, or the fixture must be anonymised, which
   costs the golden test its tie to reality.
