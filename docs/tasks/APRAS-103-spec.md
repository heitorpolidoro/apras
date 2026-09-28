# APRAS-103 — Separate the previsto and realizado labels when there is no planned curve

## Scope

One defect in one function: `_one_bar` in
`backend/app/services/project_report_service.py` (line ~494). Its
`planned is None` branch — the branch taken when the project has no usable
planned curve — emits both labels in the same vertical band, so `previsto —`
and `realizado 0%` overprint each other in the public obras report
(`/c/aprasvi/obras`, all three production projects today):

```html
<div class="one">
  <div class="tag plan" style="left:0%"><span>previsto</span><b>—</b></div>
  <div class="tag real" style="left:0%"><span>realizado</span><b>0%</b></div>
```

Both tags at `left:0%`, neither carrying `below`, the wrapper without `close`.

Verified against the source: the two-value branch already solves exactly this
problem. It computes `close = abs(planned - realized) < CLOSE_LABEL_GAP`
(`CLOSE_LABEL_GAP = 8.0`, line 131) and, when close, emits
`class="one close"` plus `class="tag plan below"`. The stylesheet already
supports that pairing — `.one.close { padding-bottom:9mm; }`,
`.one .tag.below { top:auto; bottom:0; … }` and
`.one.close .ends { …bottom:6.5mm; }` (lines ~343–345). The no-curve branch
simply never got the treatment. **This task gives it that treatment and
nothing else.**

Not in scope: the stylesheet (no rule is added, removed or edited), the
two-value branch (must stay byte-identical), `planned_to_date`, the data
behind the production `None` (see *Recorded finding*), and any colour change.

## Approach

### Behavior

The `planned is None` branch of `_one_bar` emits the plan tag in the band
**below** the track and the realized tag above it, using the markup vocabulary
the two-value branch already uses: `class="one close"` on the wrapper and
`class="tag plan below"` on the plan tag. Everything else in that branch is
unchanged — the plan tag stays at `left:0%` and still reads `previsto —`, the
realized tag stays at `left:{realized:.0f}%`, there is still no `seg b` and no
`mark`, `seg a` still has `width:{realized:.0f}%`, and the
`Início`/`Conclusão` ends row is still the last child.

**`below` is applied unconditionally in this branch, not only when realized is
near zero.** The argument, rather than the assertion:

1. *A conditional would make the layout jump.* The plan tag here is a fixed
   `—` at `left:0%`; the only variable is the realized tag's `left`. A
   threshold on `realized` means the same project's report changes structure
   between two consecutive monthly issues, the month its measurement crosses
   ~8%. The report is a document series the síndico compares side by side; a
   silent one-off shift of the whole bar is a worse artifact than a label that
   always sits below.
2. *The cost of being always-stacked is bounded and already paid elsewhere.*
   `.one.close` adds `padding-bottom:9mm` and moves `.ends` up by `6.5mm`.
   That geometry was hand-tuned against the approved mock and is exercised by
   `test_close_values_move_the_plan_tag_below_the_bar`. It is not exercised by
   any project in production today -- all three take the no-curve branch --
   so this change is what will first put it on screen. Applying it in one more
   branch still introduces no new geometry.
3. *One code path is testable; two are a threshold to re-litigate.* There is no
   comparison in this branch — there is no planned number — so a threshold on
   `realized` would be a layout rule invented from a quantity it does not
   describe.

The one thing the reviewer should check with eyes rather than bytes is
vertical fit. `div.page` is `min-height:297mm` with `height` auto and
`overflow:hidden`, and `.foot` sits in normal flow, so the box **grows** with
its content and `overflow:hidden` clips only relative to the grown box -- on
screen there is no headroom to consume and nothing to clip. Under
`@media print` the page is `min-height:auto` with a page break per project,
so the real cost of the extra 9mm is at most a dense project reflowing onto a
second printed sheet. The mock
(`docs/tasks/APRAS-103-mock.html`) renders the affected `.pv` block at
realized 0 / 5 / 37 / 80 next to today's broken output, so the operator can
confirm the separated form before implementation.

### Files touched

- `backend/app/services/project_report_service.py` — `_one_bar`, the
  `planned is None` branch only: wrapper class becomes `one close`, plan tag
  class becomes `tag plan below`. Docstring updated to say why the separation
  is unconditional. **No stylesheet edit, no new colour literal.**
- `backend/tests/test_project_report.py` — §6: extend the no-curve unit test
  and add the two-value regression pin described below.
- `backend/tests/test_public_project_report.py` — the public route's own test
  file, for the end-to-end assertion on the public report body. The renderer is
  shared with the authenticated route, but the expected result names the public
  report, so the assertion belongs with the public route's tests.

Allowed paths (nothing else may be created, edited or staged):
`backend/app/services/project_report_service.py`,
`backend/tests/test_project_report.py`,
`backend/tests/test_public_project_report.py`,
`docs/tasks/APRAS-103-spec.md`, `docs/tasks/APRAS-103-mock.html`.

### Test criteria

- The no-curve branch is asserted at several realized values (at least `0.0`,
  `37.0`, `80.0`) to carry `one close` and `tag plan below` at every one of
  them — the point being that there is no threshold.
- The no-curve branch is asserted to still omit `seg b` and `mark`, to keep
  `seg a` at the rounded realized width, and to keep the `previsto —` tag at
  `left:0%`.
- **A pin on the two-value branch.** One test compares `_one_bar` output to a
  literal expected string for **both** shapes — far apart (`13.2, 22.0`) and
  close (`20.0, 22.0`) — with `==`, not `in`. Any byte change in that branch
  fails it. This is the guard the task requires: that branch renders for every
  project that has a curve and was hand-tuned against the approved mock.
- One route-level test: the public obras report for a project without a usable
  curve contains `<div class="one close">` and no
  `<div class="tag plan" style="left:0%">`.
- The existing §5 `planned_to_date` tests and the existing §6 tests pass
  unmodified except where the no-curve assertions are extended.

### Colour constraint

No hard-coded colour may be introduced; the `.one` roles ride
`REPORT_ROLE_SOURCES` / `FALLBACK_PALETTE` since APRAS-92. **Known
pre-existing exception:** line 337, `.one .seg.b.behind { background:#c0392b;
opacity:.7; }`, carries a literal hex today. It is out of scope, must be left
untouched, and did *not* arrive with this change.

## Recorded finding — there is no planned curve in production (do not fix here)

`_one_bar` receives `planned is None` for all three production projects, so the
no-curve branch this task repairs is the branch production actually takes.

The reason is **not** a malformed payload. `planned_progress_json` is declared
`sa.JSON()` (`0001_initial_schema.py:354`), and a SQL `IS NOT NULL` test on
such a column is **true even when the column holds the JSON literal `null`** —
which is exactly what these rows hold. Checked directly against the production
database: for all three projects `planned_progress_json IS NULL` is false,
`json_typeof(planned_progress_json)` is `null`, and the raw text is `null`.
SQLAlchemy decodes that to Python `None`, so `planned_to_date` is never even
reached with a payload to parse.

`planned_to_date` is never reached and needs no change. An earlier draft of this section concluded
that the rows had been hand-populated in a shape the function rejects; that
conclusion was wrong, and it was wrong because `IS NOT NULL` does not
distinguish SQL NULL from JSON `null` on a JSON column.

**What is actually missing is data**, not code: nobody has supplied the
physical-financial schedule the curve is built from. The model comment
("Written by SQL/seed only") is accurate — a repository-wide grep finds no
writer for this column in any API, service or frontend path, so the only way
to populate it today is the sync script or direct SQL. Two follow-ups are
worth considering, neither of them part of this task: ingesting the schedule
once the contractor supplies it, and adding a writer plus a log line when a
non-null payload is rejected, since today a bad payload would fail silently.

APRAS-103 fixes the overlap only, and the overlap is worth fixing regardless:
any project legitimately without a schedule renders this branch.

## Expected Results

- [ ] `_one_bar` in `backend/app/services/project_report_service.py`, called as
      `_one_bar(None, 0.0)`, returns markup whose wrapper is
      `<div class="one close">` and whose plan tag is
      `<div class="tag plan below" style="left:0%"><span>previsto</span><b>—</b></div>`.
- [ ] `_one_bar(None, r)` emits `class="one close"` and `class="tag plan below"`
      for `r` in 0.0, 37.0 and 80.0 — the separation has no threshold on
      realized.
- [ ] `_one_bar(None, 22.0)` still omits `seg b` and `mark` and still contains
      `class="seg a" style="width:22%"` and
      `<div class="ends"><span>Início</span><span>Conclusão</span></div>`.
- [ ] A test in `backend/tests/test_project_report.py` compares the output of
      `_one_bar` in `backend/app/services/project_report_service.py` with `==`
      against literal expected strings for `(13.2, 22.0)`, `(20.0, 22.0)` and
      `(45.0, 22.0)`, and fails if any byte of the two-value branch changes.
      The three cases cover an ahead-of-plan pair far from the threshold, a
      pair inside it, and a behind-schedule pair, so the `close` wrapper, the
      `below` tag, the `seg b behind` segment and the `mark` are all pinned.
- [ ] A test in `backend/tests/test_public_project_report.py` requests the
      public obras report route for a tenant whose project has no planned
      curve, and asserts the response body contains `<div class="one close">`
      and does not contain `<div class="tag plan" style="left:0%">`.
- [ ] `cd backend && uv run pytest tests/test_project_report.py tests/test_public_project_report.py`
      passes with no test removed or weakened, and the diff adds no hex/rgb
      colour literal to
      `backend/app/services/project_report_service.py` (the only one inside the
      `.one` rules stays the pre-existing `#c0392b` on `.one .seg.b.behind`).

## Out of Scope

- The stylesheet: `.one`, `.one.close`, `.one .tag.below` and `.one.close .ends`
  are used as they are, not edited.
- The two-value branch of `_one_bar` (byte-identical).
- `planned_to_date`, the production `planned_progress_json` payloads, and any
  writer/validation for that column — separate task, see *Recorded finding*.
- `.one .seg.b.behind`'s hard-coded `#c0392b`.
