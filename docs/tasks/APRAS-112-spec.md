# APRAS-112 — Stop the Início and Conclusão labels colliding with the progress bar

## Scope

The vertical layout of the `avanço físico` bar in the obras report
(`backend/app/services/project_report_service.py`): the `Início` / `Conclusão`
ends row must not overlap the track, the `previsto` label or the `realizado`
label, in any of the bar's **three** layout cases — values close (`previsto`
label below the track), values far apart (both labels above the track), and no
planned curve at all (APRAS-103, which takes the `close` layout
unconditionally).

The fix is a stylesheet change inside `CSS_BODY`, confined to rules whose
selector names the close layout (`close` or `below`). The emitted markup of
`_one_bar` does not change, in any branch.

Not in scope: the `CLOSE_LABEL_GAP` threshold (8.0) and which branch fires;
the horizontal placement of any label; the `%` label defect recorded in
`_cylinder_svg`; pagination, print rules and `@page`; any other section of the
report.

## Approach

### Behavior

The diagnosis on the card is confirmed by reading the source and by
recomputing the geometry arithmetically (see *Calibration* below — the model
reproduces the reported browser measurement to the pixel). The single cause is

```css
.one.close .ends { position:absolute; left:0; right:0; bottom:6.5mm; }
```

which takes the ends row out of flow and drops it into the same 9mm band that
`.one.close`'s `padding-bottom` reserves for `.tag.below`. Relative to the top
of `.one`, today's close layout is: track `34–45px`, ends `40–54px`,
`previsto` label `45–79px` — two intersections.

Required behavior after the change:

1. In all three layout cases the ends row is laid out **in normal flow**,
   after the track, and the band reserved for the `below` label begins at or
   after the bottom edge of the ends row.
2. The four vertical bands — above-track label band, track, ends row,
   below-label band — are pairwise non-intersecting in all three cases.
   **Non-intersection is strict inequality: two bands intersect only if one
   starts strictly before the other ends.** Bands that merely touch — one
   ending at exactly the pixel the next begins — do not intersect. This is not
   a convenience: the fixed layout is flush at two of its boundaries (track top
   = above-tag bottom at 34.0157px; below-band top = ends bottom at 64.69px,
   0.0px of clearance), so inclusive semantics would fail the correct layout.
   No minimum clearance is demanded; flush contact is accepted.
3. The total height of `.one` in the close case grows by **no more than 6mm**
   over today's. This bound is a guard against the fix costing materially more
   vertical space than it must — **not** a proof that a project page fits on
   A4. It does not fit today: a single obra's content measures ~356.2mm against
   a 297mm sheet, so every obra already spills onto a second sheet. The bound
   keeps that known overrun from growing materially; it does not address it.
   (Simply deleting the rule above costs +5.204mm and satisfies this.)
4. Rules whose selector mentions neither `close` nor `below` are untouched,
   so the far-apart layout is unaffected (ER4).

### Files touched

- `backend/app/services/project_report_service.py` — `CSS_BODY` only: the
  close-layout rules listed above. No change to `_one_bar` or to any other
  function.
- `backend/tests/test_project_report_bar_geometry.py` — **new**: the CSS
  parser, the band model, the calibration test, the three case tests, the
  close-layout rule pin and the shared-rule pin.
- `backend/tests/data/report_css_shared_baseline.json` — **new**: the
  byte-for-byte baseline of every `CSS_BODY` rule whose selector does not
  mention `close`/`below`, captured from HEAD before the fix.

### How the geometric assertion is made, and why

Three options were considered.

- **Vitest + jsdom — rejected as unusable.** jsdom implements the DOM but no
  layout engine: `getBoundingClientRect()` returns all zeroes and
  `offsetHeight` is `0` for every element. A non-overlap assertion there
  passes for every stylesheet, broken or not. This is precisely the vacuous
  shape the card warns about.
- **Playwright — rejected as disproportionate.** It is the only option that
  measures real layout, but the repository has no Playwright or browser
  dependency (`backend/pyproject.toml`, `frontend/package.json`), and this
  would be the suite's only browser test, with a browser download in CI, for
  one bar.
- **Arithmetic band model in pytest — chosen.** Every length in the `.one`
  family is a literal `mm`, `pt` or `px` in `CSS_BODY`, and the box heights
  involved are all either declared `height` values or single line boxes
  (`font-size × line-height`). The bands are therefore computable exactly,
  without a layout engine.

#### The parser

`CSS_BODY` is **not** one rule per line, and a line-splitting parser is
forbidden. Three shapes in the shipped stylesheet break it, and each must be
handled explicitly:

- **Two rules on one line.** Three lines carry two rules each —
  `.grp.done h4 { … } .grp.done h4 i { … }`, and the same shape for `.doing`
  and `.next`. A line-keyed parser drops or garbles one rule of each pair,
  which would also corrupt ER4's shared baseline.
- **Duplicate selectors.** `body` and `.page` are each declared twice: once at
  the top level and once inside `@media print`. A parser keyed on selector
  alone overwrites the top-level `body` with the print block's
  `{ background:#fff; }` and thereby **loses `line-height:1.5`** — the value
  the 14px ends row height is computed from. The model would then measure the
  wrong thing, or nothing, and still report "no intersection".
- **At-rule blocks.** `@page { … }` and `@media print { … }`.

Required parser behavior:

1. Tokenize by brace matching over the whole string, not by lines, so several
   rules on one line are separate rules.
2. `@page` and `@media` are parsed as at-rule blocks. Their nested rules are
   collected into a **separate, print namespace** and are never merged into the
   screen cascade the model resolves against. The model resolves screen layout
   only; the print block is recorded and excluded.
3. Within the screen namespace, a selector appearing more than once accumulates
   declarations in source order (later wins per property), so no rule is lost
   to a duplicate key.
4. **Completeness assertion (its own test).** Reassembling the parsed rules —
   screen namespace and at-rule blocks, in source order, with their captured
   original text — reproduces `CSS_BODY` byte for byte. If byte-exact
   reassembly proves brittle over insignificant whitespace, the fallback is
   equally strict: every non-blank, non-`"""`-delimiter line of `CSS_BODY` is
   accounted for by the rules parsed out of it, with the count of parsed rules
   per line asserted. A rule the parser cannot see must turn the suite red, not
   vanish.

#### The model

1. Convert units to CSS px (`1mm = 96/25.4`, `1pt = 96/72`).
2. Build, for a given case (`far`, `close`, `no_curve`), the four bands from
   the parsed declarations: `padding-top`/`padding-bottom` of `.one` and
   `.one.close`; the declared `height` of `.one .track` and `.one .tag`; the
   ends row as `margin-top` of `.one .ends` plus `font-size × line-height`
   (`7pt` from `.one .ends`, `1.5` inherited from the top-level `body` rule);
   and — crucially — whether a `.one.close .ends` rule sets
   `position:absolute`, in which case the model places the ends row from that
   rule's `bottom` offset against the padding box and removes it from the flow
   height.
3. **No defaults, anywhere.** Every declaration the model needs
   (`.one{padding-top}`, `.one.close{padding-bottom}`, `.one .track{height}`,
   `.one .tag{height}`, `.one .ends{margin-top,font-size}`,
   `body{line-height}`) is looked up in the parsed cascade and **raises** if
   absent or unparseable. It is never assumed, substituted with a CSS initial
   value, or defaulted to zero. This is the guarantee that makes the
   calibration control meaningful: a parser that reads *nothing* out of
   `CSS_BODY` must explode, not produce plausible geometry.
4. `position`/`bottom` on `.one.close .ends` are the exception to (3): their
   absence is meaningful (in-flow layout) and is the expected post-fix state.
   Their absence is recorded in the returned model, not silently ignored.
5. **Declared-height boxes must fit their content.** For each box whose height
   the model takes from a declaration, it also computes the content height from
   the font sizes and line heights inside it and asserts the content fits. For
   `.one .tag` that is `7.5pt × 1.2 + 10pt × 1.2 = 28px` inside a declared
   `9mm = 34.02px` — 6px of headroom. Without this assertion a later font-size
   bump overflows the box in a real browser while the test stays green.
   Recorded limitation: the model cannot see text wrapping, so a long label
   wrapping to a second line is outside what it can detect.
6. Assert every pair of bands in every case is disjoint under the strict
   semantics of behavior item 2, and assert the close-case total height bound
   of behavior item 3.

All of the above is reached through **one entry function** — the same function
the case tests call with `CSS_BODY` and the calibration control calls with the
HEAD `.one` family. There is no second, test-only code path.

### What change to the source makes each test fail

State it plainly, because a test that survives the deletion of the offending
rule is worthless:

- **Restoring `.one.close .ends { position:absolute; …; bottom:6.5mm; }`**
  makes the close-case and no-curve non-overlap assertions fail: step 3 reads
  `position` and `bottom` out of that rule, so the model places ends at
  `40–54px` again and the intersections with the track and the `previsto`
  label reappear. Any other value of `bottom` that lands the row inside the
  track or the below band fails the same way.
- **Reducing `.one.close`'s `padding-bottom` below the height of
  `.one .tag.below`** makes the below band start above the ends row and fails
  the same assertions.
- **Raising `.one.close`'s `padding-bottom` past +6mm** fails the height
  bound.
- **Calibration (the positive control).** One test feeds the checker the
  **complete `.one` family exactly as it stands at HEAD** — every rule whose
  selector begins with `.one`, plus the top-level `body` rule that supplies
  `line-height:1.5` — as a literal stylesheet string embedded in the test, and
  asserts the model returns the bands `track 34–45`, `ends 40–54`,
  `previsto 45–79` (±1px, relative to the top of `.one`) **and reports both
  intersections**. Three rules are not enough input and must not be used: the
  bands depend on `.one{padding-top:9mm}`, `.one .track{height:11px}`,
  `.one .tag{height:9mm}`, `.one .ends{margin-top:1.5mm;font-size:7pt}` and
  `body{line-height:1.5}`, and with the no-defaults rule above a partial input
  raises instead of producing geometry.

  It enters through the **same entry function** the case tests call with
  `CSS_BODY` — same parser, same cascade resolution, same band construction,
  same intersection predicate. A control on a private or simplified path would
  prove nothing about the code the case tests run.

  Those are the numbers measured in a real browser against the live document,
  quoted on the card. This is what proves the checker can produce a failure at
  all, and pins the model to observed reality rather than to its own
  arithmetic. It does not use `skip` or `xfail` —
  `backend/tests/test_assert_no_skips.py` forbids both.
- **Not a second control: the far-apart case test.** It passes both before and
  after the fix, because today's far layout is already disjoint. It is a
  legitimate forward regression guard — it catches a future change that breaks
  the far layout — but it is **not** evidence that the checker is capable of
  failing. Only the calibration control carries that.

### ER3 — the pins

- **Markup.** `_one_bar` is unchanged, so the existing byte-for-byte pin
  `_TWO_VALUE_MARKUP[(20.0, 22.0)]` in `backend/tests/test_project_report.py`
  (gap 2.0, inside `CLOSE_LABEL_GAP`) already is the close-case markup pin and
  must keep passing untouched. Do not edit it.
- **Stylesheet.** A new test asserts that the **set** of `CSS_BODY` rules
  whose selector mentions `close` or `below` equals an expected list, rule
  text byte for byte. Equality of the set, not containment: adding a fourth
  close-scoped rule — an absolute reposition of `.ends` by another name, for
  instance — fails the test instead of slipping past it.

### ER4 — how byte-identity is checked, and against what

ER4 cannot be read as whole-document byte identity, and the spec says so
rather than pretending: the stylesheet is inlined in every document, so any
`CSS_BODY` edit changes the bytes of the far-apart report too. The statement
that carries ER4's intent and is mechanically checkable is *the far-apart
layout consumes no rule that this task changes, and its markup is unchanged*,
verified by two assertions:

1. `_one_bar(13.2, 22.0)` and `_one_bar(45.0, 22.0)` still equal their
   existing `_TWO_VALUE_MARKUP` entries byte for byte (already in the suite;
   they must pass unmodified).
2. Every `CSS_BODY` rule whose selector mentions neither `close` nor `below`
   is byte-identical to `backend/tests/data/report_css_shared_baseline.json`,
   a baseline captured from the current HEAD **before** the CSS is edited, as
   an ordered list of `[selector, declarations]` pairs. Order and text both
   compared, so a reordering or a whitespace change in a shared rule fails.

A golden HTML file of the whole rendered document was considered and rejected:
the document carries the generation date, the tenant name and database ids, so
a golden file would need normalization broad enough to hide exactly the kind of
change it exists to catch.

### Test criteria

- Three case tests (far, close, no-curve) asserting pairwise band disjointness
  under strict inequality (ER1, ER2).
- The calibration/positive-control test on the complete HEAD `.one` family
  through the shared entry function (proves the checker can fail).
- The parse-completeness test (proves the parser reads the whole stylesheet).
- The declared-height content-fit assertions.
- The close-case height-bound test.
- The close-layout rule pin (ER3) and the shared-rule baseline pin (ER4.2).
- The existing `_TWO_VALUE_MARKUP` parametrization untouched and green
  (ER3 markup, ER4.1).
- `cd backend && uv run pytest` green in full (ER5).

### Mockup

`docs/tasks/APRAS-112-mock.html` reproduces the `.one` family from `CSS_BODY`
and renders the three layout cases side by side, **before** (today's rules) and
**after** (ends row in flow), with each band outlined so the two intersections
in the before column are visible. No open question for the operator — it is
there to show what the fix looks like before approval, and its measurement
panel reports the live bands from a real layout engine, which is the number the
calibration test is pinned to.

## Expected Results

- [ ] In the close case (`abs(planned - realized) < CLOSE_LABEL_GAP`) the
      `Início`/`Conclusão` row, the track, the `previsto` label and the
      `realizado` label occupy pairwise non-intersecting vertical bands, and a
      test computed from the shipped `CSS_BODY` asserts it. Bands that merely
      touch — one ending at exactly the pixel the next begins — do not count as
      intersecting; the comparison is strict inequality.
- [ ] The same non-intersection holds for the far-apart case and for the
      no-planned-curve case, asserted by the same checker.
- [ ] A calibration test calls the same function the other geometry tests call,
      feeding it the complete `.one` rule family as it stands before the fix
      (including `body`'s `line-height`), and asserts it reports the bands
      `track 34–45px`, `ends 40–54px`, `previsto 45–79px` relative to the top of
      `.one` (±1px) **and** both intersections — so restoring the current CSS
      turns the case tests red.
- [ ] A test asserts the CSS parser accounts for the whole of `CSS_BODY` — no
      rule silently lost — specifically covering the three lines that carry two
      rules each (`.grp.done h4 { … } .grp.done h4 i { … }` and the `.doing`
      and `.next` equivalents) and the duplicate `body` and `.page`
      declarations (top level plus `@media print`), where the top-level
      `body{line-height:1.5}` must survive.
- [ ] The close-layout rules of `CSS_BODY` (selectors mentioning `close` or
      `below`) are pinned as an exact set, byte for byte, and
      `_TWO_VALUE_MARKUP[(20.0, 22.0)]` in
      `backend/tests/test_project_report.py` still passes unmodified.
- [ ] The modelled total height of `.one` in the close case is at most 6mm
      greater than today's, asserted by a test.
- [ ] `_one_bar(13.2, 22.0)` and `_one_bar(45.0, 22.0)` are byte-identical to
      their existing pins, and every `CSS_BODY` rule whose selector mentions
      neither `close` nor `below` is byte-identical, in the same order, to
      `backend/tests/data/report_css_shared_baseline.json` captured from HEAD
      before the fix.
- [ ] `cd backend && uv run pytest` passes in full.

## Out of Scope

- Changing `CLOSE_LABEL_GAP` or which branch of `_one_bar` fires.
- Any change to `_one_bar`'s emitted markup.
- Adding Playwright or any browser to the test stack.
- The `_cylinder_svg` `%`-label defect and every other report section.
- **The A4 overrun.** A single obra's content already measures ~356.2mm against
  a 297mm sheet, so every obra spills onto a second sheet today, before this
  fix. This task's 6mm height bound only keeps that overrun from growing
  materially; making an obra fit on one sheet is a separate task and deserves
  to be filed as one.
- Text wrapping: the band model computes single line boxes only and cannot
  detect a label wrapping to a second line.
