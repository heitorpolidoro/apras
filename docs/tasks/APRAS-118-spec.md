# APRAS-118 — Print one obra at a time from a selector instead of linking to the API

## Scope

`/c/<slug>/obras` (`PublicObrasReportPage`) today offers a plain
`<a target="_blank">` to
`${apiClient.defaults.baseURL}/public/tenants/{slug}/projects/report`, which puts
the API host in front of a resident. This task replaces that link with a modal
that lists the condominium's obras, and prints **one chosen obra** from a
top-level blob document built out of the HTML the page already holds in state.

Frontend only. `project_report_service.py` and the public route are **not
touched**: every transformation (splitting the document per obra, dropping the
stage-detail section, stripping the page's `brk` class, placing the forced break)
happens in the browser over the parsed HTML. The backend document's markup is
pinned by `tests/test_project_report*.py` baselines, and this task deliberately
does not move that baseline.

### Out of scope

- Any change to the backend renderer, its stylesheet, or the public endpoint.
- Loosening the iframe's `sandbox=""` (expressly forbidden: a test pins it).
- Any `@page` rule, injected or literal, and any measurement of the rendered
  document. The sheet size is inherited, not computed — see **Sheet size** below.
- Any script inside the printed document.
- A rule that splits the stages between date groups, or that shrinks or drops
  content to protect sheet 1's slack (see **Recorded decision** below).
- Printing several obras in one document; the authenticated
  `ConstructionTrackerPage` report keeps doing that, unchanged.
- Server-side PDF generation.

## Approach

### Behaviour

**Obra list — client-side split, no second fetch.** The fetched document already
contains every obra as one `<div class="page">` (the first) / `<div class="page
brk">` (each subsequent), emitted by `_page_html`. The page parses the HTML it
already holds with `DOMParser` and reads one entry per `div.page`: the title from
that page's `section.hero h1.serif`, the kind from **`section.hero > .kicker`**,
and the index. The `.kicker` class is not unique within a page — `_masthead_html`,
`_hero_html`, `_stages_html` and the bulletins section each emit one, four per
`div.page`, and the masthead's is first in document order, so a bare
`page.querySelector(".kicker")` would label every modal row `Obras em foco`. The
hero-scoped child selector is the requirement. No request is issued for the list
and none for the print document — the backend has no single-obra route to call
anyway.

**The modal.** The print control becomes a `<button>` that opens
`ObraPrintDialog`, a new component beside the page. It lists the obras by title,
one row per obra, each row a button that prints that obra. With exactly **one**
obra the modal still opens and lists that single obra — the control's contract is
"opens a modal listing the obras" for every tenant, and auto-printing on a
one-obra tenant would make expected result 1 unverifiable there. With **zero**
`div.page` elements the modal opens onto a short empty state and offers no print
row.

**The printed document.** Choosing a row builds a full HTML document from the
cloned `<head>` (the backend's inline `<style>` and font import come with it) and
a `<body>` carrying only the chosen `div.page`, then opens it with
`URL.createObjectURL(new Blob([html], { type: "text/html" }))` and
`window.open(url, "_blank")` — the technique `ConstructionTrackerPage`'s
`handleGenerateReport` already uses.

It must be a top-level document rather than the existing iframe for one reason:
**a sandboxed iframe cannot print itself.** The on-screen report lives in an
iframe with `sandbox=""`, and that attribute is not negotiable (it is what forced
`<details>` over a JS accordion in APRAS-115); a top-level window sidesteps it
instead of weakening it.

**Printing is invoked by the opener, not by the document.** The printed document
carries no script of its own. `openObraPrintWindow` keeps the handle returned by
`window.open` and calls `w.print()` once that window has loaded (its `load` event,
with `w.document.fonts.ready` awaited where available). This is legal because a
blob URL inherits the creating document's origin, so the opener may reach into the
new window. The alternative — an inline `<script>` in the printed document —
is **forbidden**: it would make printing depend on a CSP that permits
`'unsafe-inline'` (and `blob:` in `script-src`), and `frontend/vercel.json`
shipping no CSP today is a fact that can change. The opener form removes that
dependency rather than shrinking it, and keeps the printed document script-free.

Three transformations are applied to the clone:

1. **Stage detail removed.** Every `details.all` inside the chosen page is
   dropped. Cost of keeping it, measured: 15.0mm collapsed, and 1771mm expanded
   for Portarias — and the backend's second `@media print` block carries
   `details.all:not([open]) > .inner { display:block }`, so print gets the 1.8m
   form, not the 15mm one.
2. **The `brk` class stripped from the chosen page.** The clone's root `div.page`
   has `brk` removed. For obra 2..n the backend emitted `<div class="page brk">`,
   and the cloned stylesheet's `.page + .page, .page.brk { page-break-before:
   always; break-before: page }` would then force a break before the printed
   document's own first element, in addition to the one before the budget.
   Browsers usually collapse a break at the start of the flow; "usually" is not
   something a test can rest on.
3. **One forced break before the budget.** The budget section is located
   structurally, as `page.querySelector(".budget-col").closest("section")` —
   `.budget-col` is emitted once per page and only by `_budget_html`, inside the
   section whose first child is the `Orçamento da obra` head. It receives a class
   whose appended rule is `break-before: page; page-break-before: always`. Sheet 1
   is then masthead + hero + `Etapas da obra`; sheet 2 is budget + bulletins +
   footer. The heading string `Orçamento da obra` is the human description of
   where the break goes; **no code and no test matches on it**, because that
   string belongs to the backend and to Portuguese.

**Sheet size: nothing is done.** `CSS_BODY` already contains
`@page { size:A4; margin:0; }` (`backend/app/services/project_report_service.py:451`),
and the cloned `<head>` brings it along, so the printed document is A4 by
inheritance. No `@page` is injected, no height is measured, no height is written
as a literal. A derived height was considered and rejected: a sheet taller than
297mm sent to a printer loaded with real A4 is shrink-to-fit scaled, so the whole
obra would print *smaller* — worse than the overflow it was meant to avoid.

**Recorded decision (operator, not to be re-litigated).** Portarias leaves
**8.4mm** of slack on sheet 1 and one date group averages **21.4mm**, so a single
extra group overflows sheet 1: the stages then **spill onto sheet 2, pushing the
budget to sheet 3**. That is accepted, and it is not a violation of the two-sheet
map above, which describes today's data. The forced break before the budget stays;
nothing splits the stages between date groups and nothing is shrunk or dropped to
defend the 8.4mm. The simpler behaviour was chosen over the more robust one,
knowing the cost. Bulletins cost ~24.5mm each and none exist in production; two
fit sheet 2's 131.5mm of slack.

**Keyboard.** `ObraPrintDialog` follows `src/components/ui/alert-modal.tsx` for
`role="dialog"`, `aria-modal="true"`, the backdrop and the Escape listener, and
adds the two things that component lacks: focus moves into the dialog on open and
`Tab`/`Shift+Tab` cycle within it, and on close focus returns to the button that
opened it (captured at open time, restored in the cleanup path so Escape,
backdrop click, the close button and a completed print all restore it).

### Files touched

- `frontend/src/features/project-management/components/PublicObrasReportPage.tsx`
  — the `<a>` becomes a print button plus `ObraPrintDialog`; the iframe and its
  `sandbox=""` are untouched; `publicReportUrl` is no longer imported here.
- `frontend/src/features/project-management/components/ObraPrintDialog.tsx` (new)
  — the modal: obra rows, empty state, Escape, focus trap, focus restore.
- `frontend/src/features/project-management/lib/obraPrintDocument.ts` (new) —
  `listObrasFromReport(html)`, `buildObraPrintDocument(html, index)`,
  `openObraPrintWindow(html, index)` (which calls `print()` on the opened window).
  A file-level comment records the DOMParser coupling and its guard: this module
  reads `div.page`, `section.hero h1.serif`, `section.hero > .kicker`,
  `.budget-col` and `details.all` out of backend-rendered HTML, and those
  selectors are pinned on the backend by
  `backend/tests/data/report_page_null_detail_baseline.html` and
  `backend/tests/data/report_css_shared_baseline.json` — renaming any of them
  fails the backend suite, which is the signal a backend author gets for a
  frontend they never opened.
- `frontend/src/i18n/locales/pt.json`, `frontend/src/i18n/locales/en.json` — the
  modal's strings under `projects.publicReport`; `openForPrinting` is re-used as
  the button label.
- `frontend/src/features/project-management/__tests__/PublicObrasReportPage.test.tsx`
  — the existing test *offers a direct link so the report's own print CSS
  applies* pins the link this task deletes and is replaced by the modal tests;
  the `sandbox=""` assertion stays.
- `frontend/src/features/project-management/__tests__/obraPrintDocument.test.ts`
  (new), `.../ObraPrintDialog.test.tsx` (new). Their fixture is **derived from
  `backend/tests/data/report_page_null_detail_baseline.html`**, not hand-written:
  that page, duplicated with `class="page brk"` on the second copy, wrapped in the
  head the backend emits, with the `<details class="all">` markup `_stage_detail_html`
  produces inserted into each stages section. A hand-written fixture is how the
  details-removal test's presence half becomes a no-op.
- `frontend/src/api/publicProjects.ts` keeps `publicReportUrl` and its own test:
  nothing else imports it, but deleting a tested export is not this task's
  business.

No backend file changes, so the backend half of the suite result is satisfied by
the suite being unchanged.

### Test criteria

Each of these names the source change that breaks it.

- **Modal replaces the link** — with a two-obra document, the page renders no
  `link` whose accessible name matches `/impress/i` and no element whose `href`
  contains `apiClient.defaults.baseURL`; clicking the button shows both obra
  titles. *Fails if* the `<a>` is kept, or the button opens something without the
  titles.
- **Obra kind comes from the hero** — with the two-obra fixture, the two modal
  rows show the two *different* kinds from their heroes, and neither shows
  `Obras em foco`. *Fails if* the selector is a bare `.kicker` — which would make
  both rows read `Obras em foco`, so the assertion that they differ is what pins
  it.
- **No second fetch** — opening the modal and printing issues no further call on
  the mocked `fetchPublicProjectsReport` (call count stays 1) and no `fetch`.
  *Fails if* a per-obra read is added.
- **Blob, top level, one obra** — `window.open` is called with a
  `URL.createObjectURL` result and `"_blank"`; the blob's text contains the chosen
  obra's title and **not** the other obra's. *Fails if* the document is built
  from the whole report, or rendered into the iframe.
- **The opener prints, the document does not** — the stubbed window returned by
  `window.open` has its `print` called after its `load` fires and not before; and
  the built document's text contains **no** `<script`. *Fails if* printing is
  moved into an inline script, or never invoked.
- **No sheet-size work** — the built document contains no `@page` rule beyond the
  one the cloned `<head>` already carries (asserted as: the count of `@page`
  occurrences equals the count in the fixture's own head), and contains no
  `size: 210mm`. *Fails if* a measurement or a height literal is reintroduced.
- **Exactly one break** — in the built document, exactly **one** element carries
  a break (counting the appended break class and any `page`/`brk` combination the
  cloned stylesheet would act on), and that element is the `section` containing
  `.budget-col`; the root `div.page` has no `brk` class; the stages section
  (`.grp`'s ancestor section) carries none. Asserted for the obra built from index
  **1**, not only index 0, since index 0 was never the case at risk. *Fails if*
  `brk` survives the clone, or the break is placed elsewhere — a test that merely
  says "the budget section has a break" passes with two breaks and does not
  qualify.
- **Details removed from print only** — the same fixture yields `details.all`
  **present** in the on-screen `srcDoc` the iframe receives and **absent** from
  the built print document. *Fails if* the renderer never emitted it (absence
  alone would pass) — the presence half, and the fixture being derived from the
  backend baseline, is what pins that.
- **Sandbox intact** — the iframe still has `sandbox=""`. *Fails if* the sandbox
  is relaxed to make the iframe printable.
- **Keyboard** — Escape closes and focus is back on the print button; Tab from
  the last focusable wraps to the first; focus is inside the dialog after open.
  *Fails if* the trap or the restore is dropped.
- **One obra / no obra** — a one-`div.page` document still opens the modal with
  one row and does not print unprompted; a zero-page document opens the modal
  with the empty state.
- **Suites and linters** — `pytest` (unchanged), `npm test`, `ruff check` clean,
  and `npm run lint` with no more errors than the ~375-across-64-files baseline
  captured before the change. Any `eslint-disable` is line-scoped with a reason.

## Expected Results

- [ ] The public obras report page's print control opens a modal listing the
      condominium's obras by title, one selectable at a time. It no longer
      navigates to the backend URL: today it is an `<a>` to
      `${apiClient.defaults.baseURL}/public/tenants/{slug}/projects/report`,
      which hands a resident the API host.
- [ ] Choosing an obra opens a TOP-LEVEL document built from a blob URL over
      the HTML the page already holds in state -- no second fetch to the
      backend, and no backend origin in front of the reader.
      `ConstructionTrackerPage` already does exactly this for the
      authenticated report and is the precedent to follow.
- [ ] The printed document is A4, and NOTHING is injected to make it so:
      `@page { size:A4; margin:0 }` is already in CSS_BODY
      (project_report_service.py:451) and arrives with the cloned stylesheet.
      No height is measured, no literal is written, no script computes one.
      This CORRECTS an earlier version of this card that also demanded a
      self-measuring document whose sheet height differed between obras -- the
      two were never simultaneously satisfiable. Do not reintroduce
      measurement, and do not compromise with a `max(297, measured)` sheet: a
      310mm sheet sent to a printer loaded with A4 gets shrink-to-fit scaled,
      so the whole obra prints SMALLER. The operator's decision is that the
      stages spill onto sheet 2, pushing the budget to sheet 3.
- [ ] The `<details>` stage-detail section is removed from the printed
      document. Measured cost of leaving it: 15.0mm collapsed, against 1771mm
      expanded for Portarias -- the expanded form is 1.8 metres and
      unprintable.
- [ ] The printed document is A4, with ONE forced page break placed
      immediately before the 'Orcamento da obra' section -- so sheet 1 carries
      the masthead, the hero and 'Etapas da obra', and sheet 2 carries the
      budget, the bulletins and the footer. Measured with the details section
      removed: sheet 1 is 288.6mm for Portarias and 267.2mm for Sede Social
      against A4's 297mm; sheet 2 is 165.5mm for both. OPERATOR DECISION,
      recorded because the margin is thin and someone will ask: Portarias
      leaves only 8.4mm of slack on sheet 1, and one date group averages
      21.4mm, so a single extra group overflows it. That is ACCEPTED -- the
      stages are allowed to break naturally onto sheet 2 when they grow, and
      the forced break before the budget stays. Do NOT add a rule that splits
      the stages between date groups, and do NOT shrink or drop content to
      protect the 8.4mm: the operator chose the simpler behaviour over the
      more robust one, knowing the cost.
- [ ] A test asserts the report iframe still carries `sandbox=""`. The
      tempting fix for 'JavaScript cannot run in the report' is to loosen that
      attribute, and it must not be taken -- the same constraint forced
      `<details>` over a JS accordion in APRAS-115. The printed document is
      still a top-level blob document, for a different reason: a sandboxed
      iframe cannot print itself. But it carries NO script of its own.
      `window.print()` is called by the OPENER on the new window's load --
      legal, because a blob URL inherits the creating origin -- which removes
      the inline-script dependency entirely and with it any exposure to a
      future CSP. An inline `<script>` in the printed document is a finding.
- [ ] The modal is reachable and operable by keyboard: it traps focus, closes
      on Escape, and returns focus to the control that opened it.
- [ ] The whole backend test suite passes, the whole frontend test suite
      passes, `ruff check` is clean, and `npm run lint` reports no more errors
      than the current baseline (~375 across 64 files; 'zero repo-wide' is
      unsatisfiable).
- [ ] The existing test that pins the link being removed is REPLACED, not left
      passing:
      frontend/src/features/project-management/__tests__/PublicObrasReportPage.test.tsx
      carries 'offers a direct link so the report's own print CSS applies',
      which asserts the href IS the API URL. A task that deletes the link and
      leaves that test green has either not deleted it or has a test asserting
      nothing.
- [ ] Removing the details section from print matters MORE than its collapsed
      15.0mm suggests, and the reason must be recorded: CSS_BODY's second
      @media print block contains `details.all:not([open]) > .inner {
      display:block }`, so printing today expands it -- the printed form is
      the 1771mm one, not the 15mm one. A test asserts the printed document
      contains no `details.all`, anchored by first asserting the on-screen
      report does.
- [ ] The chosen page is stripped of its `brk` class before printing. The
      backend emits `<div class="page brk">` for every obra after the first,
      and the cloned stylesheet gives `.page.brk { page-break-before:always }`
      -- so a single-obra document built from obra 2 would carry a forced
      break before its own first element, on top of the one before the budget.
      The break test must assert EXACTLY ONE element in the document carries a
      break, not merely that the budget section does: as written it passes
      with two. Browsers usually drop a break at the start of the flow, and
      'usually' is not a test.
- [ ] The obra's kind is read from `section.hero > .kicker`, not from
      `.kicker`. Each page carries FOUR elements with that class -- the
      masthead's 'Obras em foco', the hero's 'Obra 01 - <kind>', the stages
      section's 'Desenvolvimento', and the bulletins section's 'Acompanhamento
      visual' -- so `page.querySelector('.kicker')` labels every row in the
      modal 'Obras em foco'. This is visible to the operator in the modal,
      which is why it is a result and not a note.
- [ ] No sheet-size work is done, and a test pins the ABSENCE in a way that
      catches BOTH mutations. Assert (a) the built document's `@page` rule
      count equals the fixture head's own count -- which is 1, the only other
      @page in the module being inside a comment -- and (b) EVERY @page block
      in the built document still reads `size:A4`. Half (b) must be written as
      a match on `size:A4`, NOT as 'no `size: 210mm` appears'. The count
      catches an INJECTED rule but not a REWRITTEN one, and a literal with a
      space would miss a rewrite emitted in this stylesheet's own space-free
      house style (`size:A4`, `margin:0`). That whitespace is the difference
      between a live criterion and one that passes on the mutation it was
      written for.
- [ ] The print-ordering test's fake window must OMIT `document.fonts`. The
      implementation awaits `w.document.fonts.ready` where available, so an
      unguarded reach would throw inside the test rather than assert -- a
      pass-by-accident in reverse. Omitting it is what exercises the guard.
