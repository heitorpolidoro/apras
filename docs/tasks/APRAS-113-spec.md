# APRAS-113 — Render the obra stages the way the approved mock does

## Scope

The three milestone cards of the obras report (`<div class="groups">` and its
`grp done` / `grp doing` / `grp next` children) start reading
`ProjectMilestone.detail_json` through APRAS-114's `decode_stage_detail` and
render the shapes the approved mock `docs/tasks/APRAS-113-mock.html` shows: a
percentage per item in the two left cards, date-grouped Próximos passos with a
count, a hoisted parent kicker and an inline comma list, and a remainder line.

Not covered: the `<details class="all">` stage-detail section (APRAS-115); the
progress bar, which must come out byte-identical; the `previsto` value; page
pagination. The card markup stays self-contained so APRAS-115 can add its
section without touching it.

## Decisions taken (do not re-litigate during implementation)

1. **Where the parent comes from.** `ProjectMilestone` has no parent column.
   The operator's sync tool writes `title = f"{top} · {name}"` when a stage has
   a parent and `title = name` when it does not
   (`backend/scripts/sync_obras_from_drive.py`, `to_project`). The renderer
   therefore splits `title` on the **first** `" · "` (space, U+00B7, space),
   `maxsplit=1`: left part is the parent, right part the name. No `" · "` means
   no parent and the whole title is the name. This is the only place the
   parent/name pair is derived, and it is used by all three cards — **including
   the NULL-`detail_json` path**, which is every production row today: the
   kicker is the two-line title treatment the operator approved and it applies
   there too. What that path preserves is the same rows, in the same order,
   carrying the same name text; what changes is the markup (`<li>` now nests
   `<div class="ttl">`) and the disappearance of the `" · "` glyph, which
   becomes the boundary between the kicker and the name instead of being
   printed. Today's card emits `<li>{_e(m.title)}</li>` — the whole title,
   separator included (`project_report_service.py:723`) — so the new output is
   *not* identical to it, and no test or review may be written as if it were.
2. **No case transform is applied here.** `title` arrives already title-cased
   from the sync script (`tidy`/`title_case`, `sync_obras_from_drive.py:207`,
   used for both `top` and `name` at lines 443 and 452), so both halves of the
   split are printed verbatim. Running a title-caser over an already-cased
   `title` would **lowercase an all-caps suffix**, so wiring one in is a defect,
   not a no-op. The Portuguese-aware title-caser concerns **leaf** names, which
   this task renders nowhere; porting it belongs to APRAS-115, the task that
   prints leaves. Do not wire a title-caser into the card.
3. **`description` is not read at all.** It is not rendered today
   (`_groups_html` emits `m.title` only) and it stays unrendered. It is never
   split, never counted, never displayed. ER7 is a *prohibition*, not a
   feature.
4. **Percentages come from `decode_stage_detail(m.detail_json).pct`**, formatted
   with the existing `_pct` (`49.5588…` → `"50%"`, which is exactly the mock's
   Sede Social value). No detail → the percentage element is not emitted at
   all; the item still renders its name.
5. **Start dates come from the decoded `StageDetail.start`.** `due_date` is the
   stage *finish* and is not used here. A milestone with no detail has no start
   and cannot join a date group.
6. **The cap is 3 slots, not 3 items** (see `_select_milestones` below).
7. **The mock's `.pc` modifier is dropped.** The mock emits `class="pc d"`
   everywhere in these cards and never uses `.pc.w` there, so production emits
   `class="pc"` and `CSS_BODY` gains one `.grp .pc` rule rather than a live rule
   plus a dead one. Visually identical to the mock.
8. **Every new selector is scoped under `.grp`.** In the mock `.ttl`, `.nm`,
   `.top` and `.pc` are unscoped, and the mock's `<details class="all">`
   subtree reuses two of them (`<span class="ttl"><span class="nm">…`), so
   leaving them unscoped here would publish a styling hook for APRAS-115 —
   which this task's Out of Scope forbids, and which would also make 115 unable
   to change a card class without changing the cards. Scoped rules force 115 to
   declare its own, deliberately. The scoping has a second, mechanical payoff:
   `.grp ul` (`padding-left:4mm`), `.grp li` and `.grp li::marker` already
   exist and survive the zero-deletions rule, so the new list rules must
   out-specify them — `.grp ul.fr` (0,2,1) beats `.grp ul` (0,1,1) and
   `.grp ul.fr li` (0,2,2) beats `.grp li` (0,1,1). They must also *reset* what
   they inherit: `list-style:none` and `padding:0` on `.grp ul.fr`, and
   `.grp ul.fr li::marker { content:"" }` is unnecessary once `list-style` is
   none — without the reset the flat rows keep their bullet and a 4mm indent,
   a visible drift from the approved mock that no assertion below would catch.
   The full selector list is in **CSS** under Approach.

## Approach

### Behavior

**Item markup (both left cards, and the undated tail of the third).** Each item
is an `<li>` inside `<ul class="fr">`. The `<li>` holds exactly two children,
and the second is a **sibling** of the first, not nested in it: first
`<div class="ttl">`, containing an optional `<span class="top">parent</span>`
followed by `<span class="nm">name</span>`; then — only when the detail decoded
— `<span class="pc">NN%</span>`, a direct child of the `<li>`. The mock shows
the shape literally: `<li><div class="ttl"><span class="nm">…</span></div><span
class="pc d">100%</span></li>`. The sibling relation is load-bearing: `.grp
ul.fr li` is the flex row and `.pc` is its non-shrinking right-hand cell, so
nesting `.pc` inside `.ttl` silently moves the percentage under the name. An
empty card keeps today's `<p class="none">—</p>`.

**Sort key.** Everywhere this task orders rows — inside a date group, and the
undated tail — the key is `(display_order, title)`, never `display_order`
alone. `ConstructionProject.milestones` is ordered by `display_order` only, so
equal values fall back to whatever order the DB returns, which is not stable
across plans or after an update. Production's current data has no duplicate
`display_order`, so nothing is wrong today; state it anyway, because APRAS-114
hit exactly this with bulletins.

**`_select_milestones`.** Single change: NEXT_STEPS loses its `[:3]` and returns
every row ordered by `(display_order, title)`. DONE keeps `sorted(…, key=_done_sort_key)[:3]`,
IN_PROGRESS stays uncapped. The function keeps its one job — choosing rows — and
gains no knowledge of `detail_json`. Note a deliberate divergence from the
dispatch brief: NEXT_STEPS is **not** ordered by `(start_date, display_order)`
here, because the start date lives in `detail_json` and decoding it inside a row
selector would put payload decoding in two places. Ordering by date happens in
the grouping step, which is where the date is already decoded; the rendered
result is identical, since groups are emitted in ascending date order and
`(display_order, title)` orders items within a group.

**Próximos passos, grouping.** For every NEXT_STEPS row, decode the detail.
Rows with a detail are *datable* and are bucketed by `StageDetail.start`;
buckets are emitted in ascending date order, items inside a bucket in
`(display_order, title)`. Rows without a detail are *undated* and are never
bucketed.

A date group emits `<div class="dgrp">`, a `<div class="dhead">` reading
`a partir de <b>DD/MM/YYYY</b>` (existing `_fmt_date`) plus
`<span class="cnt">K</span>` where K is the number of items in that group, then
— only when every item in the group has the same non-empty parent —
`<div class="dsub">parent</div>`, then `<p class="flow">` with the item *names*
joined by `", "`. When the parents differ or are absent, the `dsub` element is
omitted entirely (the mock's Sede Social first group shows exactly this case).

**The 3-slot cap.** `_NEXT_SLOTS = 3`. Date groups consume slots first, in date
order. Any slot left over is filled with one undated row each, in
`(display_order, title)`, rendered with the item markup above — kicker where the
title has a `" · "`, name, no percentage, no date — in a single trailing
`<ul class="fr">`. Consequences worth stating: with detail everywhere the card
is the mock's three date groups and no tail; with `detail_json` NULL everywhere
— **today's live production state** — the card is the first three rows as items
and never an empty card. Those are the same three rows in the same order as
today, with the same name text; see Decision 1 for what changes.

**The remainder line.** Emitted as `<p class="rest">` only when
`N > 0`, where

- `N` = number of NEXT_STEPS rows whose name is printed nowhere in the card
  (omitted date groups' items plus undated rows that got no slot);
- `M` = number of **distinct start dates** among the omitted *datable* rows.

Text: `f"e mais {N} frentes em {M} datas"` when `M > 0`, and
`f"e mais {N} frentes sem data prevista"` when `M == 0` (the all-NULL state,
where "em 0 datas" would be false rather than merely ugly). Both derived; no
literal in the renderer. Check against the mock: Portarias has 23 next steps,
3 groups rendering 5+4+1=10, so N=13 and M=7 → "e mais 13 frentes em 7 datas",
byte-for-byte the mock's line.

**The mixed case, stated so it is not read as a bug later.** When both kinds of
row are omitted — say 5 date groups exist, 3 consume the slots, and 2 undated
rows get none — N counts the undated rows too while M counts only the distinct
dates among the omitted *datable* rows. So 2 omitted date groups of 4 and 3 rows
plus 2 undated rows reads `e mais 9 frentes em 2 datas`: nine names are missing,
two dates are missing, and the two figures are deliberately not counts of the
same set. This case does not occur in either mock page; it is derivable from the
rule above and is pinned by a test case (case 4 below) precisely because it
looks like an inconsistency to a reader who has not read this paragraph.

**Em andamento distinction (ER4).** Already in `CSS_BODY`:
`.grp.doing { border-color:var(--brand-alt); … }`, and no `.grp.done` /
`.grp.next` rule declares `border-color`. Nothing to add; the deliverable here
is the test that pins it.

**The bar.** Not touched. `_one_bar`, `CLOSE_LABEL_GAP` and every `.one` / `.pv`
CSS rule must be absent from this task's diff.

### CSS — selectors and the mock→production colour mapping

`CSS_BODY` gains exactly these rules, in this order, **every selector prefixed
`.grp`** (Decision 8). Nothing else is added and nothing existing is edited:

| New selector | Colour declarations, in production variables |
| --- | --- |
| `.grp ul.fr` | none — `margin:0; padding:0; list-style:none` (the reset that beats `.grp ul`/`.grp li::marker`) |
| `.grp ul.fr li` | `border-bottom:1px solid var(--line)` |
| `.grp ul.fr li:last-child` | none — `border:0` |
| `.grp .ttl` | none |
| `.grp .top` | `color:var(--muted)` |
| `.grp .nm` | none — inherits `var(--ink)` from the existing `.grp ul` rule |
| `.grp .pc` | `color:var(--brand-text)` |
| `.grp .dgrp`, `.grp .dgrp:last-of-type` | none |
| `.grp .dhead` | `color:var(--muted)`; `border-bottom:1px solid var(--line)` |
| `.grp .dhead b` | `color:var(--ink)` |
| `.grp .dhead .cnt` | `background:var(--surface)`; `border:1px solid var(--line)`; `color:var(--muted)` |
| `.grp .dsub` | `color:var(--muted)` |
| `.grp .flow` | `color:var(--ink)` — declared, not inherited: `.flow` is a `<p>` outside any `ul`, so it would otherwise take `body`'s `var(--text)`, which no pair in `REPORT_TEXT_PAIRS` covers |
| `.grp .rest` | `color:var(--muted)` |

`.grp .none` already exists and is reused unchanged. Geometry is re-expressed in
the report's `pt`/`mm` print scale; the mock's `px` values are screen-scale and
must not be copied.

**The four substitutions the mock cannot express, and why each is what it is.**
The mock declares its own nine-variable `:root`; production has nineteen, keyed
by `REPORT_ROLE_SOURCES`, and **no new variable may be introduced** (the
`REPORT_ROLE_SOURCES`/`FALLBACK_PALETTE` equality test pins the count at 19).
Measured against `FALLBACK_PALETTE`:

1. **`var(--bg)` → `var(--surface)`.** Mock `--bg` is `#f7f1e5`, which is
   `FALLBACK_PALETTE["surface"]` exactly. It is **not** `--soft` (`#eee6d7`).
   Affected rule: `.grp .dhead .cnt` background.
2. **`rgba(221,209,182,.45)` → `var(--line)`.** `#ddd1b6` is
   `FALLBACK_PALETTE["line"]`; the literal is that colour at 45% alpha, which is
   wrong under any branded theme because the alpha silently blends the tenant's
   border into the card instead of using it. Solid `var(--line)` is the port.
   Affected rule: `.grp ul.fr li` border-bottom.
3. **`var(--gold)` → `var(--brand-alt)`.** `#c6a04a` is
   `FALLBACK_PALETTE["brand-alt"]`. No *new* rule uses it — the two mock rules
   that do (`.grp.doing`, `.grp.doing h4 i`) already exist in production with
   `--brand-alt`. Recorded so nobody re-ports them.
4. **`var(--brand)` → `var(--brand-text)` for every *text* use.** This is the
   trap APRAS-115's review found and it applies unchanged here: mock `--brand`
   is `#174b40`, and production's `--brand` **and** `--brand-text` are both
   `#174b40`, so the mock cannot distinguish them. Fills may keep
   `var(--brand)`; anything setting `color` must use `var(--brand-text)`.
   `("brand", "card")` is **absent** from `REPORT_TEXT_PAIRS` and is already
   recorded in `GRAPHICAL_PAIRS_BELOW_THREE` at 1.5338 for a yellow brand, so
   `color:var(--brand)` on a card ships a real contrast regression with a fully
   green suite. The one affected new rule is `.grp .pc`.
   A fifth collision, for the same reason: mock `--ink` is `#1d2925`, which is
   production `--text`, *not* production `--ink` (`#082f2a`). The new rules use
   `var(--ink)`.

**The rule the two colour decisions above follow.** The mock's variable *names*
carry no authority; only its rendered hexes do. When one hex maps to two
production roles, take the role the contract suite covers. That is why a text
use of mock `--brand` becomes `var(--brand-text)` (`("brand", "card")` is absent
from `REPORT_TEXT_PAIRS`) and why card text takes `var(--ink)` rather than
`var(--text)` (`("ink", "card")` is in `REPORT_TEXT_PAIRS`; no pair names
`text`, so `--text` on a card would sit outside the contrast suite entirely).
Two further facts close the `--ink` case: the card's own body text is already
`var(--ink)`, set by the existing `.grp ul { color:var(--ink) }` rule, so using
`--text` here would mean **editing an existing rule**, which the zero-deletions
constraint forbids — the alternative is not merely weaker, it is unavailable;
and `#082f2a` is darker than `#1d2925`, so the substitution moves contrast up,
never down.

**How this is checked (test criteria case 9).** Two halves, and the first is
what makes the second non-vacuous: (a) the added `CSS_BODY` text contains **no
colour literal at all** — no `#`-hex, no `rgb(`, no `rgba(`, no `hsl(` — and
(b) every `var(--x)` it contains names a key of `REPORT_ROLE_SOURCES`. (b) alone
passes vacuously over an `rgba()` literal, which is precisely the mock's
`ul.fr li` mistake.

### Files touched

- `backend/app/services/project_report_service.py` — `_select_milestones` drops
  the NEXT_STEPS cap; `_groups_html` rewritten to delegate to new private
  helpers for the title split, one item, one date group and the Próximos passos
  body; `CSS_BODY` gains the fourteen `.grp`-prefixed rules tabulated under
  **CSS** above, expressed in production's `pt`/`mm` print scale and in the
  existing 19 palette variables — **no new CSS variable** may be introduced,
  since `REPORT_ROLE_SOURCES` and `FALLBACK_PALETTE` are pinned equal elsewhere.
  The title-split helper carries a comment naming
  `backend/scripts/sync_obras_from_drive.py` as the (deliberately uncommitted)
  producer of the `" · "` format, so the coupling is discoverable by grep from
  the renderer.
- `backend/tests/test_project_report.py` — **rewrite**, not patch,
  `test_milestone_cards_select_three_all_and_three`: it breaks twice, on its
  `<li>` count assertions and on its
  `body.split('class="grp done"')[1].split("</div>")[0]` extraction, which stops
  working the moment an `<li>` nests a `<div>`. Replace the string surgery with
  one card-extraction helper, shared by every card test here, slicing from
  `<div class="grp X">` to the next `<div class="grp ` or to the end of the
  `groups` block; add the new cases below.
- `backend/tests/data/report_css_shared_baseline.json` — regenerated by the
  command in `test_project_report_bar_geometry.py`'s header comment, never
  hand-patched. Evidence that it only grew is `git diff --numstat` reporting **0
  deletions** for this path. That is a **review-time gate, not a test case** —
  it inspects the working tree, not the renderer, and no assertion in the suite
  can or should carry it.
- `backend/tests/data/report_page_null_detail_baseline.html` — regenerated by
  the command in `test_the_all_null_page_renders_the_committed_baseline`'s
  docstring (`backend/tests/test_project_stage_detail.py`), never hand-patched.
  Its *localisation* cannot be a diff claim: the file is a single line with no
  trailing newline (4295 bytes, `wc -l` = 0), so git renders any regeneration as
  one whole-file replacement with no hunks to localise and nothing a human can
  read. It is checked against a committed pre-change artifact instead — case 10
  below.
- `backend/tests/data/report_page_pre113_frame.json` — **new**, and generated
  **before** the renderer change, from the pre-change code, then committed
  alongside it. It is the frame of the all-NULL page as it stood before this
  task: the non-groups prefix, the non-groups suffix, and the milestone titles
  the old groups block printed. Contents and use: case 10.

### Test criteria — and what breaks each one

Each case names the source change that makes it fail; a case that survives its
own named change is vacuous and must be rewritten rather than kept.

1. **ER1 — percentages.** Seed a project with three milestones carrying real
   payloads from `backend/tests/data/obras_stage_detail_fixture.json`: DONE with
   `pct` 100 (fixture payload with `pct` overridden), IN_PROGRESS with the
   Demolições payload (49.5588 → `50%`), IN_PROGRESS with a 63 payload. Assert
   the done card contains `<span class="pc">100%</span>` and the doing card
   contains both `63%` and `50%` inside `pc` spans, in `display_order`.
   *Fails if:* the `pc` span is dropped, `_pct` is replaced by truncation
   (49.5588 would give 49%), or the value is read from
   `project.physical_progress_pct` instead of the milestone payload.
2. **ER1b — no detail, no percentage.** Same shape with `detail_json=None`:
   assert the card contains the milestone name and `class="pc"` does not appear
   in it. *Fails if:* the renderer emits `0%` for a missing payload.
3. **ER2 — grouping.** Seed 10 NEXT_STEPS milestones across 3 start dates in
   the mock's 5/4/1 split, titles built as `"Fundações · X"` for one group and
   with mixed parents in another. Assert: exactly 3 `<div class="dgrp">`; the
   `dhead` dates appear in ascending order as `a partir de <b>25/09/2026</b>`
   etc.; each `cnt` badge equals its group size (`5`, `4`, `1`); the
   5-item group emits `<div class="dsub">Fundações</div>` once and its `flow`
   paragraph equals the five names joined by `", "`; the mixed-parent group
   emits no `dsub`; the card contains no `<li>` for any grouped item.
   *Fails if:* groups are ordered by `display_order`, the count is hardcoded,
   the kicker is emitted when parents differ, or items are rendered one per
   bullet.
4. **ER3 — remainder arithmetic.** Extend case 3 to the mock's full Portarias
   shape: 23 NEXT_STEPS rows over 10 distinct dates. Assert the card ends with
   `<p class="rest">e mais 13 frentes em 7 datas</p>`. Add a second case with
   23 rows all `detail_json=None`: assert 3 named items and
   `e mais 20 frentes sem data prevista`. Add a third with exactly 3 date
   groups covering every row: assert `class="rest"` is absent. Add a fourth, the
   **mixed** case of the paragraph above: 5 date groups (sizes 5, 4, 1, 4, 3)
   plus 2 undated rows, so 3 groups render, 2 groups and both undated rows are
   omitted; assert exactly `e mais 9 frentes em 2 datas`.
   *Fails if:* N or M is written as a literal, M counts rendered dates instead
   of omitted ones, N omits the undated rows (the mixed case would read
   `e mais 7 …`), M counts the undated rows as a date (it would read `3 datas`),
   or the line is emitted with N=0.
5. **ER4 — distinguished card.** Three assertions in one case: the rendered page
   contains exactly one `class="grp doing"`; the three cards' class attributes
   collected in document order are `["grp done", "grp doing", "grp next"]`,
   pairwise distinct; and, parsing `CSS_BODY` with
   `test_project_report_bar_geometry.parse_css`, the selector `.grp.doing`
   declares `border-color` while no rule whose selector is `.grp.done` or
   `.grp.next` declares `border-color`.
   *Fails if:* the `doing` border-color declaration is removed, or the same
   declaration is added to the other two cards (which is what makes this test
   about the distinction rather than about any cosmetic difference).
6. **ER5 — the bar is untouched.** Reusing `_TWO_VALUE_MARKUP` is sufficient at
   the unit level and it must stay byte-identical: it already pins the far case
   (13.2/22.0, gap 8.8), the close case (20.0/22.0, gap 2.0) and the behind
   case (45.0/22.0), which is exactly ER5's "far apart" and "close" pair, and
   this task must not edit one byte of that literal. Because this task edits the
   same module, add one page-level case on top of it: render two seeded
   projects, one far pair and one close pair, and assert the full pinned string
   `_TWO_VALUE_MARKUP[(13.2, 22.0)]` and `_TWO_VALUE_MARKUP[(20.0, 22.0)]`
   appear **verbatim** in the response body, so the pin is checked through the
   real page and not only through `_one_bar`. The page-level case must be
   **date-independent**, which the unit pins are and a page is not:
   `planned_to_date` reads the clock, so seed `planned_progress_json` as an
   all-past-month curve in the shape of `test_project_stage_detail.PLANNED_CURVE`
   (`2020-01`…`2020-03`, every month already elapsed) whose **last** month's
   `pct` is the planned figure the key names — `13.2` for the far project, `20.0`
   for the close one — and pin `physical_progress_pct = 22.0` on both, which is
   the `realized` half of each key. A future-dated month would make the
   assertions pass today and fail on some later date.
   *Fails if:* `_one_bar`'s markup, `CLOSE_LABEL_GAP`, or any `.one` CSS rule is
   changed, or the card markup is wrapped around the bar block.
7. **ER6 — empty and all-complete.** Two cases, each asserting content rather
   than absence of exceptions. *Empty project* (no milestones): all three cards
   present, and each contains `<p class="none">—</p>`, with no `ul`, `dgrp` or
   `rest` anywhere in the groups block. *All-complete project* (every milestone
   DONE, three of them with payloads): the done card holds three items with
   their percentages, and the doing and next cards each hold exactly
   `<p class="none">—</p>`. Both cases also assert HTTP 200.
   *Fails if:* a renderer emits an empty `<div class="grp …">` with no body, or
   an empty `<ul></ul>`, or raises on `max()`/`min()` of an empty group.
8. **ER7 — `description` is never split.** Seed one NEXT_STEPS milestone with
   `description="Piso, Parede, Teto, Rodapé, Soleira"` (five comma-separated
   tokens, the shape 48 of the 152 real names take) and a valid one-leaf
   `detail_json`. Assert: the group's `cnt` badge reads `1`; the `flow`
   paragraph equals the milestone's own name exactly; and none of `Piso`,
   `Parede`, `Teto`, `Rodapé`, `Soleira` nor the joined `description` string
   appears anywhere in the rendered page.
   *Fails if:* anyone reintroduces `m.description.split(", ")` as the source of
   the inline list or of the count — the badge would read 5 and the tokens would
   appear. Pair it with the all-complete case above so the guard holds for the
   left-hand cards too.
9. **The palette contract (see CSS above).** Isolate the added block of
   `CSS_BODY` — parse it with `test_project_report_bar_geometry.parse_css` and
   take the rules whose selector starts `.grp ul.fr`, `.grp .ttl`, `.grp .top`,
   `.grp .nm`, `.grp .pc`, `.grp .dgrp`, `.grp .dhead`, `.grp .dsub`,
   `.grp .flow`, `.grp .rest`. Assert, over their declaration text: (a) no
   `#`, no `rgb(`, no `rgba(`, no `hsl(` appears at all; (b) every
   `var(--NAME)` occurrence has `NAME` in `REPORT_ROLE_SOURCES`; (c) no
   declaration whose property is `color` uses `var(--brand)` — the one that must
   be `var(--brand-text)`. Also assert every new selector begins with `.grp`,
   which is Decision 8 made mechanical rather than advisory.
   *Fails if:* the mock's `rgba(221,209,182,.45)` or any hex is pasted in ((a),
   which (b) alone would let through), a tenth variable is invented, `.pc` keeps
   `color:var(--brand)`, or a rule ships unscoped as the mock has it.
10. **ER9/ER11 — the page frame is unchanged and no name was lost.** The old
    bytes must **not** be read with
    `git show HEAD:backend/tests/data/report_page_null_detail_baseline.html`.
    From the commit onward — in CI, in review, and forever after — `HEAD` holds
    the *regenerated* baseline, and
    `test_the_all_null_page_renders_the_committed_baseline` pins that same file
    byte-for-byte against the rendered page; so `old` and `new` would be the
    same bytes, and both halves below would compare a value to itself. That
    mechanism works only in the developer's uncommitted worktree, which is
    exactly what makes it convincing on review.

    Capture the pre-change frame instead, **once, as a committed artifact**:
    `backend/tests/data/report_page_pre113_frame.json`, produced from the
    pre-change renderer (generate it as the first step of the task, before
    editing `project_report_service.py`; put the generator command in the test's
    docstring, as the other baselines do) from the same all-NULL seed the
    baseline test uses. Three keys, all human-readable:
    - `"prefix"` — the page text before `<div class="groups">`, verbatim;
    - `"suffix"` — the page text after the `</div>` that closes the groups block,
      verbatim;
    - `"titles"` — the milestone titles the old groups block printed, in document
      order; today's `<li>{_e(m.title)}</li>` makes each entry the whole title,
      `" · "` separator included.

    In `test_project_stage_detail.py`, beside the regenerated baseline, render
    that page and assert, with one helper that splits a page on
    `<div class="groups">` and the `</div>` closing it: (a) the new prefix and
    suffix are **byte-equal** to the artifact's — the localisation claim the
    one-line diff cannot express — and (b) for every entry in `"titles"`, both
    halves of its `" · "` split (the kicker and the name, per Decision 1) appear
    inside the **new** groups block, so the all-NULL page loses no row text even
    though the markup changed and the separator glyph is gone. No `subprocess`,
    no `git`, and therefore no skip: the case is as meaningful after the commit
    as before it.
    *Fails if:* the regeneration touches the bar, the masthead or the footer, or
    the new card drops rows the old one printed — for instance by treating a
    NULL payload as "not datable, therefore not shown". The artifact itself is
    only trustworthy if generated pre-change; a reviewer checks that by
    confirming its `"titles"` entries still carry the `" · "` separator, which
    the new renderer never emits.
11. **ER8 — the title split, its comment, and the three title shapes.** Two
    parts. (a) A grep-shaped assertion that the split helper's own comment (or
    docstring) contains the string `sync_obras_from_drive.py`, so the coupling to
    the uncommitted producer is discoverable from the renderer — the reason the
    separator matters cannot be rediscovered from this repository alone.
    (b) One case seeding three NEXT_STEPS milestones with `detail_json=None`,
    titled `"Totem"` (no separator), `"Fundações · Totem"` (one) and
    `"Fundações · Bloco A · Totem"` (two): assert the first item contains
    `class="nm">Totem<` and **no** `class="top"` element at all; the second
    renders `Fundações` as the kicker and `Totem` as the name; the third renders
    kicker `Fundações` and name `Bloco A · Totem`, which is what `maxsplit=1`
    means.

    The two-separator title is a **defensive shape the producer does not emit**,
    not sanctioned product behaviour: `sync_obras_from_drive.py` writes
    `f"{stage['top']} · {stage['name']}"` with `top` exactly one level, and the
    only separator substitution inside `name` is `"- "` → `" — "` (em dash, not
    U+00B7). So no two-level path exists to build on, and none may be built on
    this case. It is kept because the failure it pins is real: an unpack raises
    `ValueError`, and taking `[0]`/`[1]` of a plain `split` silently drops
    `Bloco A`. `maxsplit=1` degrades safely under an input the producer should
    never produce.

    Assert `class="top"></span>` and `class="top"> <` never appear
    anywhere in the page — no empty kicker, ever.
    *Fails if:* the comment is dropped, the split is `split(" · ")` without
    `maxsplit` (the third title would lose `Bloco A`), or an empty
    `<span class="top">` is emitted for a title with no separator.

## Expected Results

- [ ] Every item listed in the Concluidos and Em andamento cards is followed by
      its own completion percentage, taken from the milestone it renders; the
      mock's Portarias page shows 100%, 63% and 50%.
- [ ] Items in Proximos passos are grouped by start date. Each group prints the
      date once, a count of the items in it, the parent stage name shared by
      those items as a kicker above them, and the item names as a single
      comma-separated inline list -- not one bullet per item.
- [ ] When the rendered groups do not cover every remaining item, a trailing
      line reports the remainder as 'e mais N frentes em M datas', with N and M
      derived from the items and dates actually omitted.
- [ ] The Em andamento card is visually distinguished from the other two by a
      border, and a test asserts the three cards do not all carry identical
      class attributes.
- [ ] The progress bar is untouched: for a project whose planned and realized
      values are far apart, and for one where they are close, the bar markup
      this change emits is byte-identical to the markup emitted before it.
      Production's bar layout is the one kept -- the mock's single-line bar is
      rejected, because it places each label at a position on the track
      unrelated to the value it states.
- [ ] Rendering a project with no milestones, and one whose every milestone is
      complete, each produce a page with the three cards present and no
      exception raised.
- [ ] The percentages and start dates come from the detail payload APRAS-114
      persists, not from any re-parse of the `description` column. A test
      asserts the renderer never splits `description` on ', ': 48 of the 152
      real servico names contain a comma, so that split is wrong and must not
      be reintroduced.
- [ ] The parent kicker comes from splitting `title` on its first ' · ' (space,
      U+00B7, space), because ProjectMilestone has NO parent column: the
      operator's sync tool writes title = f"{top} · {name}". This is a hidden
      coupling to the format of a script that is deliberately never committed,
      so it must carry a comment saying so -- otherwise the next reader cannot
      discover why the separator matters. A title with no separator renders
      with no kicker, not with an empty one.
- [ ] The NULL-payload path -- every production row today -- renders the
      milestone name with NO percentage element at all (not '0%') and no date
      group. Undated rows cannot be bucketed, so the leftover slots render the
      first three by (display_order, title) as plain items, and the remainder
      line reads 'e mais N frentes sem data prevista', never 'em 0 datas',
      which would be false. What this path preserves is the same rows, in the
      same order, carrying the same name text. What changes is the markup and
      the ' · ' glyph: today the card emits `<li>{title}</li>` with the WHOLE
      title, separator included, while the new item markup splits it into a
      kicker plus a name and the separator disappears. The output is therefore
      NOT identical to today's, and no test or review may be written as if it
      were. The kicker DOES apply on the NULL path -- it is the two-line title
      treatment the operator approved.
- [ ] Two committed byte-pins WILL fail and must be regenerated, never
      hand-patched: backend/tests/data/report_css_shared_baseline.json and
      backend/tests/data/report_page_null_detail_baseline.html. The CSS pin's
      evidence is `git diff --numstat` showing ZERO deletions -- a REVIEW-TIME
      GATE, not a test case: it inspects the working tree, not the renderer.
      For the page, capture the PRE-CHANGE frame as its own committed artifact
      at regeneration time -- the non-groups prefix and suffix plus the list of
      milestone titles from the old groups block, written to
      backend/tests/data/report_page_pre113_frame.json -- and assert the
      freshly rendered page against THAT. It stays meaningful after the commit,
      a human can read it (unlike a 4295-byte single line), and it needs no
      git. TWO MECHANISMS ARE FORBIDDEN, both vacuous. (1) 'the page baseline
      diff lies inside the groups block': the file is ONE LINE with no trailing
      newline, so git renders any regeneration as a whole-file replacement --
      there are no hunks to localise. (2) reading the old bytes with `git show
      HEAD:...baseline.html`: that is the previous page only in the developer's
      uncommitted worktree. From the commit onward -- so in CI, in review, and
      forever after -- HEAD holds the REGENERATED baseline, and
      test_the_all_null_page_renders_the_committed_baseline pins that file
      byte-for-byte against the rendered page, so old and new are the same
      bytes and both halves compare a value to itself. It is worse than an
      ordinary empty test because it DOES work during the one window the
      developer sees it, which is exactly what makes it convincing on review.
- [ ] test_milestone_cards_select_three_all_and_three is rewritten, not
      patched. It breaks twice: its <li> count assertions, and its extraction
      by body.split('class="grp done"')[1].split('</div>')[0], which stops
      working the moment an <li> nests a <div>. Replace the string surgery with
      a card-extraction helper the other card tests share.
- [ ] This task applies NO case transform. It renders ProjectMilestone.title
      only -- _groups_html prints f'<li>{_e(m.title)}</li>' and nothing else --
      and the sync script already stored both halves of that title cased.
      Running a title-caser over it would LOWERCASE an all-caps suffix, so
      wiring one in is a defect, not a no-op. Title-casing leaf NAMES is not
      this task's: leaf names appear only in the <details> section, which is
      APRAS-115's, and that requirement lives there.
- [ ] The mock's colour variables must be mapped, not ported: THREE of them
      collide with production names one position over. Verified against
      FALLBACK_PALETTE: mock --bg #f7f1e5 is production --surface (not --soft,
      #eee6d7); mock --ink #1d2925 is production --TEXT (production --ink is
      #082f2a); and mock --brand #174b40 equals BOTH production --brand and
      --brand-text, so the mock cannot distinguish them. mock --gold is
      --brand-alt, and ul.fr li hardcodes rgba(221,209,182,.45), which is
      --line at 45% alpha. Two of these are contrast decisions, not naming
      ones: every TEXT use of the mock's --brand becomes var(--brand-text),
      because ('brand','card') is absent from REPORT_TEXT_PAIRS and already
      recorded below 3:1; and card text uses var(--ink) rather than a faithful
      var(--text), because ('ink','card') IS in REPORT_TEXT_PAIRS while NO pair
      names 'text' -- a faithful port would put card text outside the contrast
      suite entirely. The check is 'no colour literal' (no hex, rgb(), rgba(),
      hsl()) AND every var() naming a REPORT_ROLE_SOURCES key: the second half
      alone passes vacuously over an rgba(), because a literal is not a var().

## Out of Scope

- **The `<details class="all">` stage-detail section — APRAS-115.** Do not
  design it and leave no hooks for it. Its own card requires these three cards
  to be byte-identical afterwards, so the card markup must be self-contained.
- **The `previsto` value.** Whether it should be `planned_to_date`'s monthly
  step (6%) or the mock's daily proration (7.9%) is an open operator question
  and is not decided here; `planned_to_date` is not touched.
- **The mock's single-line bar** is rejected by ER5 — production's layout is the
  one kept.
- **The ~361mm-per-obra A4 overrun.** A separate, unopened matter; this task may
  not shrink or paginate the page to chase it.
- **`ProjectMilestone.description`** remains unrendered, as today.
- **Writing `detail_json`.** The writer is the uncommitted operator tool
  `backend/scripts/sync_obras_from_drive.py`, and it **already emits the
  column**: the operator extended it — `_stage_detail` at line 163, wired into
  `to_project`'s milestone dict at line 504 — and verified the round trip through
  `decode_stage_detail` (26 frentes / 82 serviços and 17 / 70, zero refusals).
  What that does not change is the rendering: every row in the database stays
  NULL until the operator re-runs the sync, so the NULL path of Decision 1 is
  still the live path this task must render correctly. Maintaining that script
  remains outside this repository's history.
- **Title-casing leaf names** (the `title_case` port) belongs to
  APRAS-115: these three cards print `title`, which the script already
  title-cases, and no leaf name (see Decision 2).
