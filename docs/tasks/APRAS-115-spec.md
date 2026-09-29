# APRAS-115 — Add the JavaScript-free stage detail section to the obras report

## Scope

One new collapsible section at the end of each project's `Etapas da obra`
section in the rendered obras report: an outer `<details class="all">` whose
`<summary>` carries the totals it hides, containing one inner
`<details class="ph">` per stage that has a decoded `detail_json` payload, each
listing that stage's serviços with their own percentage and dates. Built
entirely from `<details>`/`<summary>`; the stylesheet gains the rules the mock
already defines for that markup. `docs/tasks/APRAS-113-mock.html`'s
`<details class="all">` block is the approved visual reference — **no new mock
is produced by this task.**

**Not covered.** The three stage cards and the `avanço físico` bar above the
section: they are `APRAS-113`'s, and this task must leave their bytes alone
(ER5). No new column, no schema change, no migration: `detail_json` and
`decode_stage_detail` shipped in `APRAS-114` (`2a94a38`) and are consumed
as-is. No API surface change, no frontend change. No writer for `detail_json` —
the untracked operator script remains the only one, which is why the no-payload
state is production's current state and not an edge case.

Explicitly **out of scope**, and not to be touched or "fixed on the way past":

- the `previsto` value (6% monthly step versus 7.9% daily proration) — an
  undecided operator question;
- the report's ~361mm-per-obra A4 overrun — a separate matter, and this task
  makes the page taller only when a payload exists, which is nobody's page
  today.

## Approach

### Why `<details>` and not a script — record this, it is the whole design

`PublicObrasReportPage.tsx:97` injects the document into an
`<iframe srcDoc sandbox="">`. An empty `sandbox` attribute means every
restriction is on, including `allow-scripts`, so **no JavaScript in this
document ever runs** — a `<script>` accordion is impossible, not merely
unwanted, and neither is an inline `onclick` handler. `<details>`/`<summary>`
is the only collapsible mechanism available to this renderer. The same
constraint is why `CSS_BODY`'s `@media print` block must force the collapsed
contents visible on paper (the mock's rule set already does this), since a
printed report cannot be expanded by anyone.

A future reader who "improves" this into a script produces a section that
cannot be opened at all, with no error anywhere. That is the paragraph to read
before proposing it.

### Behaviour

**Which milestones appear.** Every milestone of the project whose
`detail_json` decodes — `decode_stage_detail(m.detail_json) is not None` —
regardless of `MilestoneStatus` and regardless of whether the cards above show
it. The cards show at most three DONE and three UPCOMING; the section is the
full list, which is the reason it exists. A milestone whose payload is absent
or malformed contributes nothing: `decode_stage_detail` is strict by design and
a partial read is not available.

**No decoded stage at all → no section.** Zero `<details>`, zero `<summary>`,
no wrapper, not an empty one, and no "nenhum detalhe" placeholder. Every
production row's `detail_json` is NULL until the operator re-runs the sync by
hand, so this is the **live** state of every report today, and the report's
bytes in that state must not move (see ER4/ER5 below — one committed baseline
covers both).

**The two totals, derived and never literal.** With `stages` the ordered list
of `(milestone, detail)` pairs built above:

- **frentes** = `len(stages)` — the number of decoded stages, i.e. the number
  of inner `<details class="ph">` the section emits;
- **serviços** = `sum(len(detail.leaves) for _, detail in stages)` — the number
  of `<li>` the section emits.

Both count **only what the section actually shows**. In the mixed state — some
milestones with a payload, some still NULL, which is the normal state during
the rollout — a NULL milestone is counted in neither number, because a summary
that promises 26 frentes and reveals 9 is worse than one that promises 9. The
mock's `26 frentes, 82 serviços` (Portarias) and `17, 70` (Sede Social) are
what these expressions yield when every milestone carries a payload; they are
computed, never written down. A stage with `leaves: []` (valid per APRAS-114
ER8) counts as one frente and zero serviços.

Pluralisation is explicit, not an `s` glued on: `1 frente` / `2 frentes`,
`1 serviço` / `2 serviços`. Zero frentes cannot occur — that is the no-section
case.

**Nesting survives, both levels closed.** The mock's two-level structure is
kept: one outer `<details class="all">`, one inner `<details class="ph">` per
stage. Neither level carries the `open` attribute, so the report opens showing
exactly the cards it shows today plus one collapsed summary line; the
`@media print` rules reveal the contents on paper. Nesting is what keeps the
collapsed page short — a flat list of 82 `<li>` behind one toggle would add
around a page per obra the moment it is expanded, and the per-stage toggle is
what lets the síndico open one frente.

**Markup contract** (the mock's classes, so the mock's CSS applies verbatim):

- outer: `<details class="all"><summary>Mostrar detalhes <em>— {F} frentes, {S}
  serviços</em></summary><div class="inner">…</div></details>`, emitted as the
  **last child of the existing `<section>`** `_stages_html` returns, after the
  `.pv` bar block;
- per stage: `<details class="ph"><summary><span class="dot {d|n}"></span><span
  class="ttl">[<span class="top">{kind}</span>]<span
  class="nm">{title}</span></span><span class="pp">{pct}</span></summary>…`,
  where `title`/`kind` come from `split_title_and_kind(milestone.title)` and the
  `<span class="top">` is omitted when there is no kind, exactly as the cards do
  it; `{pct}` is `_pct(detail.pct)`;
- per serviço: `<li class="{d|w|n}">{name}<b>{pct}</b><i>{dates}</i></li>`
  inside one `<ul>`;
- a decoded stage whose `leaves` is empty renders its `<summary>` and, in place
  of the `<ul>`, the `<p class="none">—</p>` the cards already use for an empty
  group — so the stage is visible rather than silently dropped, and no new CSS
  class is invented for it. The rule styling that class is card-scoped today and
  must be extended; see **The stylesheet** below.

**Leaf names arrive RAW and the renderer title-cases them.** The producer
stores serviço names exactly as the `.mpp` spells them — SHOUTING —
because casing is presentation and `backend/tests/data/obras_stage_detail_fixture.json`
is pinned against the raw form (`"DEMOLIÇÃO DE PAREDES EM ALVENARIA CONFORME
DEMARCAÇÃO DE PROJETO"`). So `{name}` is title-cased **at render time**, by
porting the Portuguese-aware `title_case` from the operator's sync script: it
lowercases, then capitalises each whitespace-separated word except a `MINOR`
preposition in non-initial position (`de`, `da`, `do`, `das`, `dos`, `e`, `em`,
`com`, `para`, `a`, `o`, `as`, `os`, `no`, …), so `"ENTRADA DE CAMINHÕES"`
becomes `"Entrada de Caminhões"` where a naive `str.title()` gives
`"Entrada De Caminhões"`. Two details the port must carry:

- **the milestone `title` is already title-cased by the producer** (the fixture's
  keys read `"Demolições — Térreo e Superior"`), so the stage `<summary>` uses it
  as stored. Title-casing it a second time is a defect, not a no-op: `title_case`
  lowercases first, so a stored `"WC"` or an all-caps kind suffix would be
  reduced. Only leaf names go through the helper;
- **short all-caps acronyms survive.** `title_case` lowercases before
  capitalising, so `"WC E WC PCD"` — which the committed fixture really contains
  — would render `"Wc e Wc Pcd"`. The port carries a small uppercase-preserving
  set for the acronyms the real data holds (at minimum `WC`, `PCD`), asserted
  against that fixture name. This is an addition to the script's version, not a
  divergence in the preposition rule.

Title-casing happens **before** `_e`, so escaping still sees the final text.

**Dot/bullet state classes, read off the mock rather than reinvented.** Stage:
`d` when `detail.pct > 0`, `n` when it is `0`. Serviço: `d` when `pct >= 100`,
`w` when `0 < pct < 100`, `n` when `0`. (`docs/tasks/APRAS-113-mock.html` shows
a 63% and a 50% stage with `dot d` and a 0% stage with `dot n`, and leaves at
100/90/0 as `d`/`w`/`n`.)

**A dateless serviço.** `decode_stage_detail` accepts `start`/`finish` of
`null`, and the producer writes `null` when the schedule carries no date, so
this renders and must be decided here — the mock has no state for it:

- both dates present → `<i>14/09–15/09</i>`, the mock's format: `%d/%m`, joined
  by an en dash `–` (U+2013), no year;
- exactly one present → that one date alone, no dash, no placeholder
  (`<i>14/09</i>`);
- neither present → **the `<i>` element is omitted entirely.** No `—`, no empty
  element: the grid row it occupies would otherwise reserve space for nothing.

The year is deliberately absent, because the approved mock omits it. Recorded
accepted ambiguity: a schedule spanning a year boundary shows `05/01` for two
different years. The stage's own dates are not this section's problem — the
milestone's `due_date` is already on the card.

**Ordering, and it must be total.** Stages sort by
`(milestone.display_order, milestone.title, milestone.id)` — no `or 0`
fallback: `ProjectMilestone.id` is a non-nullable `uuid.UUID` with
`default_factory=uuid4`, so the fallback is dead code that would raise
`TypeError` comparing `uuid.UUID` with `int` if it ever fired. It is the same
primary key the cards use, so the section reads in the same order as the cards,
with `title` and then the database id breaking a tie. Two rows with an equal
`display_order` and an equal `title` are then ordered by a unique, stable
column, so the rendered bytes are identical between two renders of the same
data; without the tiebreaks a duplicated `display_order` (nothing forbids one)
reorders the section between renders and the report's own golden tests become
flaky. Serviços render in **payload order**, not re-sorted: that is the
contractor's schedule order, it is meaningful, and list position is already a
total order — a sort by `pct` or name would both destroy the schedule and need
its own tiebreak.

**Escaping.** Every name, title and kind goes through `_e`. 48 of the 152 real
leaf names contain a comma and several contain an em dash; none is trusted.

**The stylesheet.** `CSS_BODY` gains the mock's `details.all` / `details.ph` /
`.inner` / `.dot` / `.pp` family, appended at the end of the existing string,
plus the print rules for it in a **new `@media print` block appended after the
existing at-rules** — never as a declaration added inside the existing
`@media print { … }`. `shared_rule_pairs` emits one pair per at-rule as
`[prelude, whole raw body]`, so touching the existing print block **rewords an
existing pair** and the baseline diff stops being additions-only; a brand-new
block appends a new pair instead. Plain rules appended after `@page` and
`@media print` are valid CSS and likewise append pairs, so the whole addition
lands at the end of `shared_rule_pairs`' list.

**The mock cannot be ported verbatim: it carries three palette-foreign colour
values, and an undefined custom property fails silently** — the declaration is
invalid at computed-value time, the element simply renders uncoloured, and
neither the browser nor the suite says a word. Verified against
`FALLBACK_PALETTE`:

| in the mock | its value | becomes |
| --- | --- | --- |
| `var(--gold)` | — | `var(--brand-alt)` (`#c6a04a`) |
| `var(--bg)` | `#f7f1e5` | **`var(--surface)`** — `--surface` *is* `#f7f1e5`; **not** `--soft`, which is `#eee6d7` |
| `var(--brand)` | `#174b40` | `var(--brand-text)` for **text**, `var(--brand)` for **fills** (below) |
| `rgba(221,209,182,.4)` | `#ddd1b6` at 40% | `var(--line)` (below) |

**`--brand` is the dangerous one, precisely because the mock cannot show the
bug.** In `FALLBACK_PALETTE`, `brand` and `brand-text` hold the *same* literal
`#174b40`, so the mock renders identically either way and a verbatim port of
`details.all>summary{color:var(--brand)}` looks correct. They diverge for a
branded tenant: `brand` is `primary`, `brand-text` is `primary-text`, the
contrast-corrected one. `("brand", "card")` is **absent** from
`REPORT_TEXT_PAIRS` and is already recorded in `GRAPHICAL_PAIRS_BELOW_THREE` at
**1.5338** and **1.2111**, so that rule would ship summary text at ~1.2:1 for a
yellow-brand tenant with the whole suite green — no test measures a pair nobody
declared. Rule by rule, which is which:

- `details.all>summary{color:…}` — **text** → `var(--brand-text)`. Its
  background is `details.all{background:var(--card)}`, and
  `("brand-text","card")` *is* in `REPORT_TEXT_PAIRS`, so this use becomes
  measured rather than unmeasured.
- `.dot.d{background:…}` — **fill** (a 7×7px state dot) → stays `var(--brand)`.
- `details.ph li.d::before{background:…}` — **fill** (a 5×5px bullet) → stays
  `var(--brand)`. Both are decorative state markers, not text, and their lower
  bound is the risk `GRAPHICAL_PAIRS_BELOW_THREE` already accepts explicitly.
- `.dot.w` and `details.ph li.w::before` take `var(--brand-alt)`; every
  remaining colour is `--muted`, `--line`, `--card` or `--surface`, and every
  text use among them is `--muted` on `--surface` or on `--card`, pairs
  `REPORT_TEXT_PAIRS` already measures.

**The `details.ph li` separator: plain `var(--line)`.** The mock hard-codes
`border-bottom:1px solid rgba(221,209,182,.4)` — `--line`'s own literal at 40%
alpha, softened so an inner row separator reads lighter than the `ul`'s
`border-top`. Decision: **`border-bottom:1px solid var(--line)`**, no
`color-mix`. Two reasons, neither of them tidiness. A literal `rgba()` stays
sand-coloured under a blue or a yellow brand, so the single colour the mock
hard-codes is exactly the one that would refuse to follow the tenant palette.
And `color-mix(in srgb, var(--line) 40%, transparent)` buys 40% fidelity at the
price of a second colour syntax plus a `transparent` keyword that the
"no colour literal" check below would then need an exception for. `--line` at
full strength on `--surface` (`#ddd1b6` on `#f7f1e5`) is the same hairline the
enclosing `details.ph` border and the `ul`'s `border-top` already draw inside
that very block. Recorded accepted deviation from the mock: row separators are
one step heavier than it shows; no test asserts the alpha.

**The colour check, in two halves, because either half alone is empty.** Over
the **appended rules only** (the sheet already carries `rgba(8,47,42,.08)`
shadows and `#c0392b`, which is why the case is scoped rather than sheet-wide):

1. **no colour literal** — no `#`-hex, no `rgb(`, no `rgba(`, no `hsl(`; and
2. every `var(--x)` the appended rules introduce has `x` in
   `REPORT_ROLE_SOURCES`.

Half 2 alone passes **vacuously over a literal**: `rgba(221,209,182,.4)` is not
a `var()`, so a rule that keeps the mock's hard-coded separator satisfies
"every `var()` resolves" while carrying the exact literal the check exists to
forbid. Half 1 alone permits `var(--gold)`. Both, or neither is worth writing.

**And half 2 is a direction the suite does not currently run.**
`test_every_named_variable_is_actually_referenced_by_the_document` iterates
`REPORT_ROLE_SOURCES` and looks each name up in the body: **declared →
referenced**, one way only. Nothing anywhere asserts the converse, so a
reference to an *undefined* property — `var(--gold)`, `var(--bg)` — is invisible
to the entire suite, which is the silent failure this task exists to close. The
new case therefore extracts every `var(--x)` occurrence from the appended rules
with one regex and asserts the set of names is a subset of
`REPORT_ROLE_SOURCES`, reporting the offenders by name.

**`.grp .none` is card-scoped and must be extended.** The empty-stage line
reuses `<p class="none">—</p>`, but the only rule styling it today is
`.grp .none { color:var(--muted); font-style:italic; font-size:8.5pt; margin:0; }`
— a descendant of `.grp`, which the section is not, so inside `details.ph` it
would render as unstyled body text. Extend that selector to cover the section
(`.grp .none, details.ph .none`, or an equivalent appended rule). Note that
editing the existing `.grp .none` rule in place rewords a `shared_rule_pairs`
pair and breaks additions-only, so the coverage must arrive as an **appended**
rule.

Two harmless facts, recorded so the next reader does not treat either as a
defect: `.dot.w` is **dead CSS** under this task's stage rule — a stage is `d`
above 0% and `n` at 0%, never `w` (the mock's 63% and 50% stages both carry
`dot d`); the class stays, ported, because deleting one rule out of a ported
family costs more review than an unused selector. And `.dot{…height:7px…}` is
safe against `APRAS-112`'s geometry suite: `declared_height_boxes` only
considers selectors beginning `.one`.

Two committed baselines are affected and must be handled deliberately:

- `backend/tests/data/report_css_shared_baseline.json` pins every `CSS_BODY`
  rule whose selector mentions neither `close` nor `below`, in order, byte for
  byte. Appending rules therefore **requires regenerating it** with the command
  its docstring records, and the reviewer checks the JSON diff is **purely
  additive** at the end: no existing pair reworded, reordered or removed.
- `backend/tests/data/report_page_null_detail_baseline.html` must **not** be
  regenerated by this task. It is the all-NULL page, and this task emits nothing
  for the all-NULL page, so an unchanged baseline file is a checkable property
  of the diff. A diff that touches that file fails review even with a green
  suite, because regenerating it is exactly how a stage-card change would be
  laundered past ER5.

### Files touched

- `backend/app/services/project_report_service.py` — a new
  `_stage_detail_html(milestones)` fragment, a small day/month date helper and a
  `title_case` helper ported from the operator's sync script; `_stages_html`
  gains **one** interpolation of the fragment before its closing `</section>`
  and changes in no other way; `CSS_BODY` gains the appended `details` family,
  the appended `.none` coverage rule and one new `@media print` block. No
  existing fragment function's output changes and no existing CSS rule's text
  changes.
- `backend/tests/data/report_css_shared_baseline.json` — regenerated,
  additions-only.
- `backend/tests/test_project_report_stage_detail_section.py` (new module, or a
  new section of `backend/tests/test_project_report.py` — developer's choice)
  — every case below.

Deliberately **not** touched: `report_page_null_detail_baseline.html`,
`backend/app/models/project.py`, `backend/app/schemas/project.py`, any Alembic
revision, anything under `frontend/`, and every other task's uncommitted file
in this tree.

### Test criteria

This project has shipped seven tests that asserted nothing, and an eighth was
caught in `APRAS-114`'s review this session (`None == None` under a decoder
that always refused). Two of this task's eleven results have exactly that shape
— "no section when there is no payload" and "no `<script>`" — so each carries an
explicit anti-vacuity anchor, and every case below states what source change
makes it fail.

**The shared fixture.** One project with several milestones, at least three of
them carrying a real `detail_json` payload and at least one with `detail_json =
None`, so the mixed state is the default fixture rather than a special case.
The payloads are hand-written dicts in the test (small, with known leaf counts
and known percentages including a `0` and a `100`), plus at least one stage read
from the committed `backend/tests/data/obras_stage_detail_fixture.json` so the
section is proven to render a payload of the real shape, comma-rich names and
all. Determinism as `APRAS-114` pinned it: literal `generated_at`, literal
`updated_at`, `tenant=None`, `user=None`, past-only `planned_progress_json`,
and bulletins with literal `created_at` or none.

**One extraction helper, shared by every case below, because "inside the
section" has to mean one thing.** `extract_section(html)` returns the substring
that begins at the index of `<details class="all">` and ends at its **matching**
`</details>` — found by walking the `<details` and `</details>` tokens from that
index with a depth counter, since the inner per-stage `<details class="ph">`
nest inside it. **It raises when the opening token is absent or the walk never
returns to depth 0 — it never returns `""`.** Returning empty would satisfy every
count that compares against another count as `0 == 0`, which is the shape this
repository has already shipped nine times; raising makes an absent section a
loud failure at the one place three results depend on.

Every count and every absence assertion in ER1 and ER3 is
taken over *that* substring and never over the rendered document, for a concrete
reason: `_groups_html` emits **bare `<li>`** for each carded milestone
(`f"<li>{_e(m.title)}</li>"`) and `<p class="none">—</p>` for an empty group, so
a document-wide count of either token over-reports by whatever the three cards
happen to hold. `render_report_html` also emits one `div.page` per project, so
the helper is applied per project — the fixture project's `_stages_html` output
in the unit cases, and for the document-level case the assertion is that the
number of extracted sections equals the number of projects with at least one
decoded stage. The exact tokens counted are the literals
**`<details class="ph"`** and **`<li`**; nothing else in the section's markup
contains either.

**ER1 — the totals are derived.** The test computes the two expected numbers
*from the fixture payloads* (sum the leaf lists it wrote) and asserts the
rendered summary contains `Mostrar detalhes` and those two numbers with the
`frentes`/`serviços` wording; it then asserts that **within
`extract_section(html)`** there are exactly `frentes` occurrences of
`<details class="ph"` and exactly `serviços` occurrences of `<li` — the
summary's promise checked against the section's own content, which is the only
check a hard-coded literal cannot survive. The figures the card quotes
(26 frentes / 82 serviços for Portarias, 17 / 70 for Sede Social) come from the
operator's real `.mpp` data and are **not reproducible from this repository** —
no committed fixture carries a full-obra payload — so no test asserts them; the
cross-check is the verifiable form of that result. A second case adds one leaf
to one payload and asserts **both** numbers move. A third asserts the singular
forms for a one-frente, one-serviço project.
*Fails if:* the totals are written as literals, or count all milestones instead
of decoded ones, or count leaves the section does not render.

**ER2 — the content.** For one known stage, assert its `<details class="ph">`
block contains the milestone title, its `_pct(detail.pct)` string, and for each
leaf the escaped name, its own percentage and its `dd/mm–dd/mm` range; assert
the `<span class="top">` appears for a milestone whose title carries a
`(kind)` suffix and is absent for one that does not; assert a comma-rich real
name from the committed fixture survives verbatim **apart from its casing**, and
name that casing explicitly: a raw `"...WC E WC PCD..."` leaf renders with `e`
lowercase, the words capitalised and `WC`/`PCD` still upper, while the stage
`<summary>` carries the stored `title` unchanged.
*Fails if:* the leaf percentage or the dates are dropped, the stage percentage
is taken from the milestone instead of the payload, escaping mangles a name, the
names ship SHOUTING, a naive `.title()` produces `De`, or the stage title is put
through the title-caser too.

**ER2b — the dateless serviço and the empty stage.** Named cases: a leaf with
`start: null, finish: null` renders an `<li>` with its name and percentage and
**no `<i>` element**; a leaf with only `start` renders the single date and no
en dash; a stage with `leaves: []` renders its `<summary>` and the
`<p class="none">` line, and is counted as one frente and zero serviços.
*Fails if:* a null date raises, renders `None`, or renders a dangling `–`.

**ER3 — no `<script>`, no inline handler, anchored so it cannot pass empty.**
One test, in this order:

1. assert the section is **present**: the document contains
   `<details class="all">` and the `Mostrar detalhes` summary;
2. assert it is **non-empty**, in the form the `leaves: []` fixture stage can
   actually satisfy: **each** `<details class="ph">` block contains at least one
   `<li` **or** one `<p class="none"`, and the section contains at least one
   `<li` **overall**. Plus count equality of `<details class="ph"` against the
   fixture's decoded-stage count. The earlier "each block contains at least one
   `<li`" is **unsatisfiable** on this fixture and was a straight contradiction
   with ER2b: an empty stage renders `<p class="none">` and no `<li>` by design,
   so that anchor and that fixture could not both pass. The disjunction still
   cannot pass on an empty section, because of the overall-`<li>` clause and the
   count equality;
3. only then assert, **over `extract_section(html)`** rather than the whole
   document: `"<script"` absent, and no inline event-handler attribute — one
   case-insensitive regex, **anchored inside a tag**: `<[^>]*\son[a-z]+\s*=`.
   A bare `on[a-z]+\s*=` over section text false-positives on serviço names,
   which are punctuation-rich (48 of the 152 real names carry a comma, several
   an em dash or a `/`), and a name ending `... ON=` or containing `ção=` style
   noise would fail the test for nothing. The anchored form still catches a
   handler nobody thought of, which is the point of not hand-listing
   `onclick`/`onload`;
4. and assert the section contains no `javascript:` URL.

The existing `test_the_document_carries_no_gantt_timeline_or_curve` already
asserts `"<script" not in body` for a project **with no payload**, where the
section does not exist; that assertion is vacuous for this task and does not
substitute for the above.
*Fails if:* the developer reaches for a script or an `onclick` toggle; and,
because of steps 1–2, also fails if the section stops being emitted at all.

**ER4 — no payload, no section, anchored against the positive case.** The same
module, sharing the fixture builder: render **two independently built project
instances** — one as built, one whose every milestone has `detail_json = None` —
by calling the fixture builder twice, or by deep-copying before nulling. Never
by nulling the payloads in place on the same instance and rendering again: the
populated render must be taken from a project that still carries its payloads,
and "null it, then render both" is the classic way that test passes while
asserting nothing about the populated case. ER5 builds its two instances the
same way, for the same reason. Assert
the populated render contains `<details class="all">` (the positive anchor) and
the all-NULL render contains **none** of `<details`, `<summary`, `Mostrar
detalhes`, `class="inner"`. The two assertions in one test are what stop it
passing on a renderer that never emits the section. A second, independent
guard, free of charge: `test_the_all_null_page_renders_the_committed_baseline`
in `backend/tests/test_project_stage_detail.py` already renders an all-NULL
page against a committed byte baseline, so if this task emitted anything for
that state the existing suite goes red without a new test — and this task does
not regenerate that file.
*Fails if:* the section is emitted unconditionally, or with an empty `<div
class="inner">`, or with a placeholder when there is nothing to show.

**ER5 — the cards are byte-identical.** `APRAS-114` proved "rendering
unchanged" with a committed golden baseline plus a diff-level "no rendering
function changed" constraint. **That approach does not transfer**, and the
reason is worth stating: this task *must* edit `_stages_html` and `CSS_BODY`, so
"no rendering code path changed" is false by construction, and a "before" byte
capture of the populated page cannot exist — no populated page renders today.
What is provable instead is a **property of the output**, checked twice:

1. **The section is additive, asserted against the same fixture.** Take
   `card_html` = `_stages_html(project)` on the all-NULL instance and
   `full_html` = `_stages_html(project)` on the populated instance — two
   independently built projects, as ER4 requires. Then assert
   `prefix = card_html.removesuffix("</section>")` is non-empty and contains
   `Etapas da obra` and each card's milestone titles; `full_html.startswith(
   prefix)`; `full_html[len(prefix):].startswith('<details class="all">')`; and
   `full_html.endswith("</details></section>")`. That is byte equality of
   everything above the section, derived from the same milestone rows, with the
   only difference being the payload the cards do not read. The three anchor
   assertions on `prefix` are what stop this passing on two empty strings.
   `removesuffix` is safe here and stays: `_stages_html` ends in exactly one
   `</section>` (`"</div></section>"`, the `.pv` div's close followed by the
   section's), so the strip removes precisely that one tag, and if a future
   change to the function's tail invalidates the assumption the following
   `startswith`/`endswith` assertions fail loudly rather than silently passing.
2. **The all-NULL page baseline is untouched**, both as a passing existing test
   and as a review check that
   `backend/tests/data/report_page_null_detail_baseline.html` does not appear in
   the diff. Since `APRAS-113` regenerates that file with its new cards, an
   unchanged file after this task means this task did not move a card byte.

*Fails if:* the section is inserted between the cards and the bar, or anywhere
but last; if any card markup or the `.pv` block is reworded; or if the cards
start reading `detail_json`.

**ER6 — the stylesheet's own two-way colour case.** A named test over the
appended rules alone, both halves as **The stylesheet** specifies them: no
colour literal (`#`, `rgb(`, `rgba(`, `hsl(`) and every introduced `var(--x)`
name in `REPORT_ROLE_SOURCES`. This is the referenced → declared direction the
existing suite never runs, so it is a new case rather than a restatement of
`test_every_named_variable_is_actually_referenced_by_the_document`.
*Fails if:* `--gold`, `--bg` or any other undefined property is ported, or the
mock's `rgba()` separator is kept.

**ER7 — the suite.** `uv run pytest` green in `backend/`, including
`test_project_report_bar_geometry.py` (whose CSS baseline this task
regenerates) and the branding suite (which asserts every named palette variable
is referenced and that no colour is derived here).
*Fails if:* the appended CSS rewords an existing rule — which is what editing
the existing `@media print` block or the existing `.grp .none` rule would do —
introduces a literal colour, or references an undefined variable.

**Pre-implementation check, not a test.** Run the backend suite *before*
starting. If `test_the_all_null_page_renders_the_committed_baseline` is already
failing, `APRAS-113` landed a card change without regenerating its baseline;
stop and report that rather than regenerating it here, because doing so from
this task's working tree is indistinguishable from laundering a card change
past ER5.

## Expected Results

- [ ] Below the three stage cards the report renders a collapsible section built
      from <details>/<summary>, whose summary carries the totals it hides -- e.g.
      'Mostrar detalhes - 26 frentes, 82 servicos'. NOTE FOR VERIFICATION: those
      figures are the mock's illustration and are NOT reproducible from this
      repository -- no committed fixture carries a payload. Do not fail the task
      for not producing 26; the verifiable requirement is the cross-check below.
      Both numbers are derived, and the test proves it by CROSS-CHECK rather than
      by reading a literal: frentes must equal the emitted count of <details
      class="ph"> and servicos the emitted count of <li>. They count ONLY what the
      section renders -- in the mixed rollout state a milestone with no payload is
      counted in neither and rendered nowhere, because a summary promising 26 and
      revealing 9 is worse than one promising 9. A decoded stage with leaves:[] is
      one frente and zero servicos. Singular and plural are both spelled ('1
      frente', '1 servico').
      Both counts are taken over the substring from `<details class="all">` to its
      matching `</details>`, never over the whole document: the stage cards emit
      bare `<li>` too, so a document-wide count over-reports.
- [ ] Expanding it shows, per stage, the stage name, its percentage, and its
      servicos with each servico's own percentage and its start-finish dates, as
      docs/tasks/APRAS-113-mock.html renders them.
- [ ] The section contains no <script> element and no inline event-handler
      attribute. The report iframe carries sandbox="" and would execute neither,
      so a JavaScript accordion is impossible, not merely unwanted. This assertion
      must be anchored: the same test first asserts the section is present and
      contains at least one <details> per stage with non-empty contents, so it
      cannot pass by the section being absent.
- [ ] A project whose milestones carry no detail payload renders no section at all
      rather than an empty one, and a test covers that case.
- [ ] The three stage cards above the section are unchanged: their markup is
      byte-identical to what the preceding task produces.
- [ ] The whole existing backend test suite passes.
- [ ] The mock's stylesheet cannot be ported verbatim: it carries THREE
      palette-foreign colour values, and an undefined custom property fails
      SILENTLY -- the element just renders uncoloured. Verified against
      FALLBACK_PALETTE: (a) --bg #f7f1e5 is the report's --surface, NOT --soft
      (#eee6d7) -- an earlier version of this card said --soft and was wrong; (b)
      --gold maps to --brand-alt; (c) the mock's --brand #174b40 equals BOTH
      --brand and --brand-text in the fallback, so the mock cannot distinguish
      them -- every TEXT use must become --brand-text (fills such as .dot.d may
      stay --brand), because ('brand','card') is absent from REPORT_TEXT_PAIRS and
      already recorded in GRAPHICAL_PAIRS_BELOW_THREE at 1.53 and 1.21, so --brand
      text on --card would ship at ~1.2:1 for a yellow-brand tenant with a green
      suite; (d) details.ph li's border uses a hard-coded rgba(221,209,182,.4),
      which is --line at 40% alpha.
      The assertion is 'the added rules contain NO colour literal' -- no hex, no
      rgb(), no rgba(), no hsl() -- AND every var(--x) they introduce names a key
      of REPORT_ROLE_SOURCES. The second half alone is not enough: it passes
      VACUOUSLY over an rgba() literal, because a literal is not a var(). Note the
      suite today only checks declared-to-referenced, never
      referenced-to-declared, so a var(--gold) reference is invisible to it
      without this new case.
- [ ] backend/tests/data/report_css_shared_baseline.json (APRAS-112's
      byte-for-byte pin of every non-close/below rule, in order) is regenerated
      additions-only, with the new rules appended at the end. Before starting, run
      the existing baseline test: if it is ALREADY red, stop and report it rather
      than regenerating from a tree that is out of step -- regenerating a red pin
      launders whatever broke it.
- [ ] The dateless case is specified, since decode_stage_detail accepts a leaf
      whose start and finish are null: both dates render as '14/09-15/09' (%d/%m,
      en dash, no year); exactly one renders that date alone with no dash; neither
      OMITS the element entirely rather than emitting an empty one or a bare dash.
- [ ] Leaf names arrive RAW from the producer -- SHOUTING, exactly as the .mpp
      spells them -- because casing is presentation and
      backend/tests/data/obras_stage_detail_fixture.json is pinned against the raw
      form. The renderer must title-case them, porting the Portuguese-aware
      title_case from the operator's sync script (it leaves prepositions like
      'de'/'e' lowercase; a naive .title() would render 'Entrada De Caminhoes').
      The stage title stored in `title` is ALREADY title-cased by the script --
      only the leaf names are not.
- [ ] The anti-vacuity anchor for the no-script check and the leaves:[] case must
      not contradict each other: a stage with no leaves renders <p class="none">
      and NO <li>, so 'every <details class="ph"> contains at least one <li>' is
      unsatisfiable on a fixture that includes one. The anchor is 'each stage
      block contains at least one <li> OR one <p class="none">, and the section
      contains at least one <li> overall'. Also: .none is styled today only as
      `.grp .none`, which is card-scoped, so inside the section it would render
      unstyled -- extend the selector. And anchor the inline-handler regex inside
      a tag (`<[^>]*\son[a-z]+\s*=`): 48 of the real servico names are
      punctuation-rich and would false-positive on a bare text scan.

## Out of Scope

- The `previsto` value (6% monthly step versus 7.9% daily proration): an open
  operator question, untouched here.
- The report's ~361mm-per-obra A4 overrun: a separate task.
- Writing `detail_json` from anywhere in the application; the untracked operator
  script remains the only writer.
- Any change to the stage cards, the `avanço físico` bar, the API schemas or the
  frontend.
