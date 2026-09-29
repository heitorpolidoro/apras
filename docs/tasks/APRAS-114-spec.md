# APRAS-114 — Persist the stage detail the obras report needs

## Scope

`ProjectMilestone` gains one nullable JSON column, `detail_json`, holding the
stage payload `{pct, start, leaves: [{name, pct, start, finish}]}`; one Alembic
revision adds it; one strict decoder in `app/services/project_report_service.py`
turns that column into a typed value; one committed fixture pins the real
payload shape; and tests prove the report is unchanged for the NULL state every
production row will be in until the operator re-runs the sync.

**Not covered.** No rendering change of any kind — the three stage cards are
`APRAS-113`, the `<details>` leaf list is `APRAS-115`, and both are blocked
on this task. No API surface: the column is deliberately invisible to every
request/response schema. No frontend change, no TypeScript type. No backfill,
no server default, no data migration. No child table. No parsing of the
existing `description` column, now or later.

### Why the producer is not part of this diff

The thing that will *write* `detail_json` is
`backend/scripts/sync_obras_from_drive.py`, an operator tool run by hand
against production, deliberately never committed to this repository (the
contractor's `.mpp` sources are likewise gitignored under
`docs/obras-fonte/`). This task therefore cannot be verified by reading its
producer, and must not be specified as if it could.

What the repository owns instead is the **contract**: the column, the
migration, a decoder that defines exactly which payloads are readable, and a
committed fixture carrying one real payload the decoder is asserted to read.
That is the whole reason ER3, ER4 and ER5 exist in a task that otherwise looks like
a one-line schema change. A reviewer who expects to see the writer in the diff
should read this paragraph rather than ask for it.

**Consequences the operator must act on, stated here because nothing in the
repository will state them:**

1. After this lands, the untracked sync script must be updated to emit the
   `detail_json` payload and re-run against production. Until it is, **every
   row's `detail_json` is NULL** — which is exactly the state ER6 makes safe.
2. The producer needs no key mapping, by design. The script's own leaf dicts
   already carry `name` / `pct` / `start` / `finish` (verified in
   `sync_obras_from_drive.py` — leaves are built at lines 338–348, stages at
   405–417), and `start` / `finish` are already ISO `YYYY-MM-DD` **strings**
   there, not `date` objects, so `json.dumps` of what the script holds is
   already a valid payload. The committed fixture remains the single artefact
   both sides are checked against.

### Why the stored keys are English and identical to the producer's

An earlier draft of this task specified `nome` / `pct` / `inicio` / `fim`.
That was wrong twice over and is recorded here so it is not reintroduced:

- it forced a translation step, and that step would live in the one file that
  is never reviewed (the untracked producer) — precisely where a silent key
  mismatch would hide. A producer emitting `name` into a decoder expecting
  `nome` decodes to "no detail" with no error anywhere;
- this project's language policy requires code and technical artefacts in
  English, so Portuguese keys were wrong on their own terms.

The stored shape is therefore exactly the keys the producer already holds. The
stage object is still a **projection**, not a verbatim dump: `fronts()` stage
dicts also carry `name`, `top` and `finish`, which are dropped because the
milestone's `title` and `due_date` columns already hold them. Leaf dicts
likewise carry `id`, `lvl`, `summary` and `dur` alongside the four keys above;
if the producer dumps leaves verbatim those extra keys will be present in
production payloads, which is safe only because the decoder ignores unknown
keys — see the decoder contract below, where that tolerance is asserted rather
than assumed.

### Why one JSON column and not a child table (operator decision, 2026-09-28)

Recorded so it is not re-argued: the sync deletes and recreates the whole
dataset on every run, so referential integrity guards a problem that does not
exist; nothing queries these values in SQL; `APRAS-89` may replace the data
source outright; and a child table would cost an FK, delete ordering inside the
script, and an N+1 risk across 43 milestones. `ConstructionProject.planned_progress_json`
already stores a contractor curve exactly this way.

## Approach

### Behaviour

**The column.** `ProjectMilestone` gains `detail_json`, nullable JSON, declared
the way `ConstructionProject.planned_progress_json` is — an explicit
`sa_column=Column(JSON, nullable=True)`, for the reason that model already
records: the test harness builds this schema on `sqlite://` via
`SQLModel.metadata.create_all()`. NULL means "this stage has no detail" and is
the only value production holds until the sync is re-run. Nothing in
application code writes it.

**The stored payload.** One object per milestone:
`pct` (number, the stage's weighted physical progress, 0–100, unrounded),
`start` (ISO `YYYY-MM-DD`, the stage's earliest leaf start — `due_date`
already holds the finish), and `leaves`, a list of
`{name: str, pct: number, start: ISO date | null, finish: ISO date | null}`.
A leaf's `start`/`finish` are nullable because the contractor's schedule
genuinely lacks dates on some leaves and the producer writes `null` there; a
*present but unparseable* date is not the same thing and is malformed.

**The decoder.** A module-level function in
`app/services/project_report_service.py`, placed beside `planned_to_date` and
strict in the same way and for the same reason: it returns a typed result (a
frozen dataclass pair — the stage, and one entry per leaf) or "no detail",
never a partial read.

**Its parameter type is `object`**, exactly as `planned_to_date`'s is: the JSON
column deserializes to a `dict` before it reaches application code, so the
decoder never parses a JSON string and must not grow a string-accepting wrapper.
This is not cosmetic — the fixture case arrives via `json.load` while the
strictness cases are literal dicts, and a wrapper for the former would put the
positive control on a different entry point from the guards it exists to
validate (ER10, ER4).

Specifically, "no detail" for: `None`; a non-object
payload; an empty object; a missing or non-numeric or out-of-range (`<0`,
`>100`) `pct`, booleans rejected as `planned_to_date` rejects them; a missing
stage `start` or one that is not a parseable ISO date string; a `leaves` value
that is not a list **or absent entirely** — the key is required, exactly as
`pct` and the stage `start` are, because the producer always emits it and its
absence therefore means the payload did not come from the producer;
`payload.get("leaves", [])` is the wrong reading and must not be used. And
"no detail" for **any** single unparseable entry inside `leaves` — a
leaf whose `name` is not a non-empty string, whose `pct` is unusable, or whose
*present* `start`/`finish` will not parse. One bad entry invalidates the whole
stage: a partially-read stage understates the work, and that is the number the
síndico holds against the measurement.

Two cases are explicitly **valid**, not corruption, and the decoder must accept
both:

- a leaf whose `start` or `finish` is `null` — the producer writes `null` when
  the schedule carries no date. Only a present-but-unparseable value is
  malformed;
- `leaves: []` — a stage that is its own leaf is a real stage in the
  contractor's schedule, and decoding it as "no detail" would silently drop it
  from the report. It decodes to an empty tuple; the caller (`APRAS-115`)
  decides what that renders as.

Unknown extra keys are ignored, as `planned_to_date` ignores them — and this is
load-bearing rather than incidental, because the producer's leaf dicts carry
`id`, `lvl`, `summary` and `dur` that may reach the column untouched.
No rounding anywhere: presentation rounds, the decoder does not.

**Validate with Pydantic, not a hand-rolled walker (decided, not left open).**
Two small `BaseModel`s — one stage, one leaf — behind a single `TypeAdapter`,
with the whole decode wrapped in one `except ValidationError: return "no
detail"`. Reason: it buys ISO date parsing, the `pct` range via `Field(ge=0,
le=100)`, `extra="ignore"` for the producer's `id`/`lvl`/`summary`/`dur`, and
rejection of a malformed nested leaf, in one place, on the stack this project
already depends on everywhere. **One trap that must be handled explicitly:** in
Pydantic's default lax mode `pct: True` coerces to `1.0` and `pct: "12.5"` to
`12.5`, which would silently accept the booleans this spec requires be rejected
(parity with `planned_to_date`). The numeric fields therefore carry
`Field(strict=True)`, and a named test asserts `pct: True` yields "no detail"
and `pct: "12.5"` does too.

Two smaller declaration details follow from the behaviour above and should not be
rediscovered by trial and error: `leaves` is declared **required with no
default**, which is what turns an absent key into a `ValidationError` (and also
what rejects `{}`); and `pct` must accept both `int` and `float` while rejecting
`bool` and numeric strings — a named test asserts `pct: 0` (int) decodes.

A field-level `Field(strict=True)` on a plain `float` already gives exactly that
contract, with no union. Measured on this project's own pydantic 2.13.3:
`12` → `12.0`, `0` → `0.0`, `12.5` → `12.5`, `True` → rejected (`float_type`),
`"12.5"` → rejected (`float_type`).

Two mechanisms are **forbidden**, both measured rather than assumed:

* `Annotated[int | float, Field(strict=True, ...)]` raises at class-definition
  time — `RuntimeError: Unable to apply constraint 'strict' to schema of type
  'union'`. A developer who reaches for a union to "accept both" gets an import
  error, not a validation error.
* `model_config = {"strict": True}` is worse than wrong: strict `date` rejects
  the ISO **string** `"2026-10-16"`, so the decoder would refuse every real
  payload. The ER4 positive control is the only thing that would catch it — which
  is a good reason that control exists, and a bad way to find out.

The rule this illustrates, and which the rest of this spec follows: pin the
observable behaviour, and name a library mechanism only when it has been run.

If the developer prefers a bespoke validator, that is acceptable, but then every
one of the properties listed in this section must be reproduced by hand and the
choice recorded in the module; the default is Pydantic.

**Rendering.** Untouched. No fragment function gains a call to the decoder in
this task, and no existing line of any rendering code path is edited — the
decoder and its result types are pure additions to the module. ER7 states this
as a checkable property of the diff, and it is what makes the ER6 golden file
mean anything about this task: no rendering function changed, so the baseline
cannot have been regenerated from altered output. A diff that touches a
rendering function fails ER7 even if every test is green.

**Schemas.** `MilestoneBase` / `MilestoneCreate` / `MilestoneUpdate` /
`MilestoneRead` in `app/schemas/project.py` list their fields explicitly and
must keep doing so — the new column is not added to any of them, so no
serialized milestone payload gains the key.

### Files touched

- `backend/app/models/project.py` — `ProjectMilestone` gains `detail_json`; a
  comment states why it is JSON, why it is nullable with no backfill, and that
  only the operator script writes it.
- `backend/alembic/versions/0007_milestone_detail_json.py` — new revision,
  `down_revision = '0006_tenant_brand_theme'` (the current head; `0004` does not
  exist and the digits skip it, since Alembic orders by `down_revision`, never
  by digits). `upgrade` adds the column, `downgrade` drops it. Revision id is 26
  characters, inside the `VARCHAR(32)` `alembic_version.version_num` limit.
  Imports nothing from `app/`. This is an **ordinary new revision**, not an edit
  to `0001_initial_schema` — that rule expired when production applied `0001` on
  2026-09-19.
- `backend/app/services/project_report_service.py` — the decoder and its
  result types, beside `planned_to_date`. Nothing else in this module changes.
- `backend/tests/test_migrations_postgres.py` — `HEAD_REVISION` and
  `EXPECTED_HISTORY` extended by the new slug. No other edit.
- `backend/tests/data/obras_stage_detail_fixture.json` — new, the real payload
  (see below).
- `backend/tests/data/report_page_null_detail_baseline.html` — new, the
  render bytes for the all-NULL state (see ER6 below).
- `backend/tests/test_project_report.py` (or a new sibling module, developer's
  choice) — the decoder cases, the fixture case, the unchanged-render case.
- `backend/tests/test_projects.py` (or wherever the project-detail endpoint is
  already exercised) — the no-leak-into-the-API case.

### How the fixture is obtained

The fixture is extracted locally, once, with no Drive credentials, no
production database and no production API call: the contractor's schedules are
already cached in the working tree under `docs/obras-fonte/drive/` (gitignored),
and the untracked sync script's own `read_mpp` + `fronts` produce the stage
dicts. A throwaway script in the scratchpad loads the sync module by path, runs
those two functions over the cached `SEDE SOCIAL` `.mpp`, projects each stage to
`{pct, start, leaves}` and each leaf to `{name, pct, start, finish}`, and writes
the result. `jpype` and `mpxj` are already installed in this project's `uv`
environment. The `.mpp` files and the extraction script are **not** committed;
only the derived JSON is.

This extraction was **run**, not proposed: the numbers below are measured
output, re-measured under the corrected English keys, and stated here so a
reviewer can tell an extracted fixture from an invented one.

The fixture file is a JSON object keyed by milestone title, carrying **two**
real stages — one comma-rich, one with non-zero progress, because every
comma-rich stage in the real schedule has `pct == 0.0` and a test asserting
`0.0` cannot distinguish a decoded value from a default:

| stage | pct | start | leaves | names containing a comma |
|---|---|---|---|---|
| `Instalações Hidraulicas — Térreo e Superior` | 0.0 | 2026-10-16 | 5 | 4 |
| `Demolições — Térreo e Superior` | ≈49.56 (49.55882352941177) | 2026-09-25 | 8 | 0 |

48 of the 152 real leaf names contain a comma, which is why the `description`
column (leaf names joined with `", "`) cannot be split back and is not to be
parsed. (The 2000-character truncation on `description` does not currently bite
— the largest is 1178 characters — so it is a latent risk, not a present
defect.)

**Recorded observation, deliberately not fixed here.** `fronts()` in the
untracked producer raises on a leaf whose `start` is absent, so today it cannot
emit the `null` date the decoder is required to accept. That belongs to the
script, not to this repository, and fixing it is not in this task's diff. It is
written down because it will bite the first time a schedule carries a dateless
leaf, and the decoder's tolerance (ER8) is what makes fixing it a one-line
script change rather than a schema change.

### Test criteria

This project has shipped seven tests that asserted nothing. ER6 and ER7 are
both shapes that go vacuous, so each carries an explicit anti-vacuity
requirement.

**Decoder (ER3, ER4, ER10).** One named case per rejected input — `None`, `{}`, a
non-object, a bad `pct`, `pct: True` (the lax-mode trap above), a bad/absent
stage `start`, a non-list `leaves`, **an absent `leaves` key**, a leaf with a
non-string `name`, a leaf with a present-but-unparseable `start` — each
asserting "no detail". **Plus a positive control in the same module**, using the
same single entry point, which takes `object`: the ER5 fixture, loaded with
`json.load`, decodes to real values. Without it, "malformed yields no detail" is
satisfied by a decoder that always returns no detail; and if the fixture reached
a different entry point from these cases, the control would vouch for code the
guards never exercise.

**Accepted edge cases (ER8, ER9).** Two further named cases, on the *accepting*
side: a payload whose leaf has `start: null` and `finish: null` decodes, with
both fields `None` on the decoded leaf and the leaf's `name` and `pct` intact;
and a payload with `leaves: []` decodes to a stage whose `pct` and `start` are
read and whose leaf tuple is empty — asserted as "decoded, zero leaves", never
as "no detail". A third case covers unknown-key tolerance: a leaf carrying the
producer's extra `id` / `lvl` / `summary` / `dur` keys decodes identically to
the same leaf without them. Note the asymmetry these cases pin, and pin it
deliberately: `leaves: []` is **accepted** while an absent `leaves` key is
**rejected**, so the two must be separate named cases and the implementation
must not collapse them with a defaulting `.get`.

Neither pinned fixture stage carries a null leaf date or an empty `leaves` list,
so all of these payloads are hand-written in the test rather than read from the
fixture.

**Fixture (ER5).** The test reads
`backend/tests/data/obras_stage_detail_fixture.json`, decodes **both** stages,
and asserts, against literals written in the test and not read back out of the
fixture dict: the stage `pct` (exact `0.0` for the hydraulics stage, `approx` to
0.01 for `49.56`), the stage `start` as a `datetime.date`, the leaf count, the
full ordered list of leaf `name`s, and that at least one of those names contains
a `,` and survives verbatim. Both stages are required precisely because the
comma-rich one has `pct == 0.0`: only the second stage proves `pct` was decoded
rather than defaulted.

**Unchanged render (ER6).** The committed golden file is **future-drift
protection**, not proof that this task left the render alone. Be plain about
the difference:

- what it guards: from the next commit onwards, any change to a rendering
  fragment that alters the all-NULL page will fail this test. That is its whole
  job, and it is the reason `APRAS-113` and `APRAS-115` inherit a tripwire
  instead of a promise;
- what it does **not** guard: that the bytes in the file were produced by the
  pre-change module. Nothing in the repository can check when a human ran a
  command, so the spec makes no such claim. What makes the baseline meaningful
  for *this* task is ER7's diff-checkable assertion that **no rendering code
  path, no API schema and no frontend file is changed here** — if no rendering
  function changed, the baseline cannot have been regenerated from altered
  output, whatever order the developer worked in.

The test therefore reads: build the fixture project, call
`_page_html(project, 1, None, None, generated_at)` against the module as
committed, assert byte equality with
`backend/tests/data/report_page_null_detail_baseline.html`. `_page_html` is
every rendered fragment of a page; the stylesheet is pinned separately and
independently by `tests/data/report_css_shared_baseline.json`. The docstring
states what the file guards and what it does not, in the two bullets above, and
records the command that regenerates it from the *current* module — the same
convention `tests/test_project_report_bar_geometry.py` already uses.

**The fixture project must be fully deterministic, and that is the part most
easily got wrong.** Everything below reaches the rendered bytes, and every
unpinned one of them defaults to `clock.db_now()`, which makes the baseline pass
on the day it is written and fail at the next UTC date change:

1. `generated_at` — a literal `datetime`.
2. `tenant=None` and `user=None` — default palette, no author clause.
3. `planned_progress_json` — every `month` in the past, so `planned_to_date` is
   clock-independent and stable forever.
4. `ConstructionProject.updated_at` — **a literal `datetime`.** The masthead
   renders `Última atualização {_fmt_date(last_update)}` where `last_update` is
   `max(update.created_at for update in updates) if updates else
   project.updated_at` (`project_report_service.py:721-722`, rendered at 738).
5. The bulletins — **either zero of them, or every one with a literal
   `created_at`.** Each bulletin renders its own date (`<small>{_fmt_date(
   update.created_at)}</small>`, same file, line 657), and a non-empty list also
   takes over `last_update` above.
6. Several milestones spanning all three `MilestoneStatus` values, **every one
   with `detail_json` NULL**.

Anti-vacuity: the test first asserts the baseline is non-empty and contains each
fixture milestone title and the `Etapas da obra` heading, and asserts every
fixture milestone's `detail_json is None` — so the case cannot pass by comparing
two empty strings or by silently exercising the populated state.

**No API leak and no rendering change (ER7).** One test against `GET /api/v1/projects/{id}`
(`ProjectDetailRead.milestones: list[MilestoneRead]`) creating a project with at
least two milestones, which **first asserts `len(payload["milestones"]) >= 1`**
and only then asserts `"detail_json" not in m` for every `m` — the quantified
set is proven non-empty before it is quantified over. The same test asserts
`"detail_json"` is absent from `MilestoneBase`, `MilestoneCreate`,
`MilestoneUpdate` and `MilestoneRead` `model_fields`, and **present** in
`ProjectMilestone.model_fields` — the positive control that stops the whole case
from passing because the column was never added. All four schemas list their
fields explicitly, so these four checks cover every milestone response schema
there is. ER7's other half — no rendering code path, no API schema and no
frontend file changed — is not a test but a **review check on the diff**, and
the reviewer is expected to apply it; it is the assertion the ER6 baseline
leans on.

**Migration (ER2).** `alembic upgrade head` then `alembic downgrade -1` against
a real Postgres leaves the schema as it started, and
`tests/test_migrations_postgres.py` passes unchanged in behaviour — its existing
`test_versions_holds_exactly_the_expected_revision_modules`,
`test_the_history_is_a_line_from_one_root_within_the_version_num_limit`,
`test_no_revision_imports_anything_from_app`,
`test_upgrade_downgrade_base_and_upgrade_again_all_succeed` and
`test_every_column_name_and_nullability_matches_the_model` all cover the new
revision once `EXPECTED_HISTORY` names it.

## Expected Results

Verbatim from the task card's `expected_results` (ten results, ER1-ER10 in
this order; every reference in the body above uses these numbers).

- [ ] ProjectMilestone has exactly one new column, detail_json, nullable JSON,
      holding {pct, start, leaves:[{name, pct, start, finish}]} -- the keys the
      operator's sync script already produces, so no translation layer exists to
      drift, and English as this project's policy requires. No other column is
      added and no new table is created.
- [ ] One new Alembic revision, 0007_milestone_detail_json, chains onto
      0006_tenant_brand_theme. `alembic upgrade head` followed by `alembic
      downgrade -1` against a real Postgres leaves the schema as it started, and
      tests/test_migrations_postgres.py passes with HEAD_REVISION/EXPECTED_HISTORY
      extended.
- [ ] A single decoder in app/services/project_report_service.py, beside
      planned_to_date, returns a typed stage result or 'no detail'. Named tests
      cover None, an empty payload, a non-object payload, a bad pct, a missing or
      unparseable stage start, a non-list leaves, a leaf with a non-string name,
      and a leaf with a present-but-unparseable date -- each yielding 'no detail'
      and never a partial read.
- [ ] A positive control in the same module feeds the ER5 fixture to the SAME
      entry point and gets parsed values back, so the strictness cases above
      cannot pass on a decoder that always refuses.
- [ ] backend/tests/data/obras_stage_detail_fixture.json is committed, extracted
      from the cached contractor schedule, and is a JSON object keyed by milestone
      title. It carries two real stages, whose keys are EXACTLY these strings,
      accents and em dash included: "Instalações Hidraulicas — Térreo e Superior"
      (pct 0.0, start 2026-10-16, 5 leaves, 4 with a comma in the name) and
      "Demolições — Térreo e Superior" (pct 49.55882352941177, start 2026-09-25, 8
      leaves). A test decodes both and asserts the stage pct, the start as a date,
      the leaf count and the ordered leaf names against literals. Two stages are
      required because the comma-rich one's pct is 0.0 and cannot distinguish a
      decoded value from a default.
- [ ] Rendering is unchanged:
      backend/tests/data/report_page_null_detail_baseline.html is committed and a
      test re-renders the same fixture with the new code and asserts byte
      equality. The fixture must be FULLY deterministic, which requires pinning
      ConstructionProject.updated_at and either zero bulletins or bulletins with a
      literal created_at -- both default to clock.db_now() and both reach the
      rendered bytes (the masthead's 'Ultima atualizacao' takes
      max(update.created_at) or project.updated_at, and each bulletin renders its
      own created_at). A baseline that does not pin them passes on the day it is
      written and fails at the next UTC date change. Also pinned: generated_at,
      tenant=None, user=None, the planned_progress_json months, and every
      milestone's detail_json is None. The test first asserts the baseline is
      non-empty and contains each milestone title and the string 'Etapas da obra'.
- [ ] No rendering code path, no API schema and no frontend file is changed by
      this task. This is the guard that makes the golden baseline meaningful and
      it is checkable from the diff: if no rendering function changed, the
      baseline cannot have been regenerated from altered output. Do NOT rely on
      the baseline having been captured before the edit -- that is a claim about
      when a human ran a command and nothing in the repository can verify it. The
      whole backend test suite passes, and the new column is absent from every API
      response schema: a test on GET /api/v1/projects/{id} asserts it returned at
      least one serialized milestone payload and only then that none carries a
      detail_json key; it also asserts detail_json is absent from MilestoneBase,
      MilestoneCreate, MilestoneUpdate and MilestoneRead, and present on
      ProjectMilestone.
- [ ] A leaf's start and finish may be null and the decoder accepts that while
      still rejecting a present-but-unparseable date; leaves:[] decodes as a valid
      stage with zero leaves rather than as 'no detail'. A named test covers each
      case. Neither pinned fixture stage contains a null leaf date or an empty
      leaves list, so both cases must be hand-written payloads in the test rather
      than read from the fixture. A payload with NO `leaves` key at all is 'no
      detail' -- the key is required, exactly as `pct` and the stage `start` are.
      The producer always emits it, so its absence means the payload did not come
      from the producer. `payload.get('leaves', [])` is the wrong reading and must
      not be used.
- [ ] A leaf dict carrying the producer's extra keys (id, lvl, summary, dur)
      alongside the four contract keys decodes identically to one carrying only
      the four. The producer emits those extras, so unknown-key tolerance is a
      correctness requirement, not politeness.
- [ ] The decoder takes `object`, as planned_to_date does -- the column
      deserializes to a dict, and the decoder never parses a JSON string. This
      matters for the positive control: the fixture case arrives via json.load
      while the strictness cases are literal dicts, and a string-parsing wrapper
      for the former would put the control on a different entry point from the
      guards it exists to validate.

## Out of Scope

- Writing `detail_json` from anywhere in the application; the untracked
  operator script is the only writer and is not part of this diff.
- Rendering the stage cards (`APRAS-113`) or the leaf `<details>` list
  (`APRAS-115`), both blocked on this task.
- Any change to `description`, including parsing it or altering its truncation.
- Backfill, server default, or data migration of any kind.
