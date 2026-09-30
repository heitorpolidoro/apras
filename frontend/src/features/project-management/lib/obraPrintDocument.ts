/**
 * APRAS-118 — splitting the backend's obras report into one printable obra,
 * entirely in the browser.
 *
 * The public page already holds the whole report as a string. Everything here
 * works over that string with `DOMParser`: no request is issued (the backend
 * has no single-obra route to call) and `project_report_service.py` is not
 * touched.
 *
 * **The DOMParser coupling, and its guard.** This module reads five selectors
 * out of backend-rendered HTML — `div.page`, `section.hero h1.serif`,
 * `section.hero > .kicker`, `.budget-col` and `details.all`. None of them is
 * declared anywhere the backend author would look, so the guard is that all
 * five are pinned on the backend side by
 * `backend/tests/data/report_page_null_detail_baseline.html` and
 * `backend/tests/data/report_css_shared_baseline.json`: renaming any of them
 * fails the backend suite, which is the signal someone gets for a frontend they
 * never opened. The frontend fixture is derived from those same two files.
 *
 * **What is deliberately NOT done: sheet sizing.** `CSS_BODY` already carries
 * `@page { size:A4; margin:0; }` and it arrives with the cloned `<head>`, so the
 * printed document is A4 by inheritance. Nothing is measured and no height is
 * written. A derived height was considered and rejected: a sheet taller than
 * 297mm sent to a printer loaded with real A4 is shrink-to-fit scaled, so the
 * whole obra prints *smaller* than it would have.
 */

/**
 * The one rule this module appends, on the budget section. Exported so the test
 * can count break-carrying elements rather than trust a string.
 */
export const PRINT_BREAK_CLASS = "obra-print-break";

/** The obra list the modal shows. */
export interface ObraEntry {
  /** Position of the obra's `div.page` in the report, and the print argument. */
  index: number;
  title: string;
  /** The obra's kind, or `""` when the hero's kicker carries none. */
  kind: string;
}

const parseReport = (html: string): Document =>
  new DOMParser().parseFromString(html, "text/html");

const text = (node: Element | null): string => node?.textContent?.trim() ?? "";

/**
 * The obra's kind, out of the hero's own kicker.
 *
 * `.kicker` is **not** unique within a page: the masthead, the hero, the stages
 * section and the bulletins section each emit one, so a bare
 * `page.querySelector(".kicker")` returns the masthead's and labels every obra
 * `Obras em foco`. The child selector on `section.hero` is the requirement.
 *
 * The backend writes the kicker as `Obra 01 • <kind>`, or `Obra 01` alone when
 * the project has no kind; the ordinal is already the row's position, so only
 * the part after the separator is kept.
 */
const heroKind = (page: Element): string => {
  const kicker = text(page.querySelector("section.hero > .kicker"));
  const separator = kicker.indexOf("•");
  return separator < 0 ? "" : kicker.slice(separator + 1).trim();
};

/** One entry per obra in the report, in the order the backend rendered them. */
export const listObrasFromReport = (html: string): ObraEntry[] =>
  Array.from(parseReport(html).querySelectorAll("div.page")).map(
    (page, index) => ({
      index,
      title: text(page.querySelector("section.hero h1.serif")),
      kind: heroKind(page),
    }),
  );

/**
 * A complete HTML document carrying one obra, ready to hand to a blob URL.
 *
 * The `<head>` is cloned whole, so the backend's `<style>` — font import, theme
 * variables, `@page`, both `@media print` blocks — comes along untouched. Three
 * transformations are applied to the chosen page and nothing else:
 *
 * 1. **`details.all` removed.** On screen it is a 15.0mm collapsed summary, but
 *    `CSS_BODY`'s second `@media print` block forces
 *    `details.all:not([open])>.inner { display:block }`, so on paper it is the
 *    expanded 1771mm form — 1.8 metres, unprintable.
 * 2. **`brk` stripped from the page.** The backend emits `<div class="page brk">`
 *    for every obra after the first and the cloned stylesheet gives
 *    `.page.brk { page-break-before:always }`, so an obra 2 printed as-is would
 *    carry a forced break before the document's own first element. Browsers
 *    usually collapse a break at the start of the flow; "usually" is not
 *    something to ship.
 * 3. **One forced break before the budget.** The budget section is located
 *    structurally — `.budget-col` is emitted once per page and only by
 *    `_budget_html` — so sheet 1 is masthead + hero + stages and sheet 2 is
 *    budget + bulletins + footer. When the stages grow past sheet 1 they are
 *    allowed to spill onto sheet 2 and push the budget to sheet 3: that is the
 *    operator's decision, taken over any rule that would split the stages or
 *    shrink content to defend the remaining slack.
 *
 * The document carries **no `<script>`**: printing is invoked by the opener (see
 * `openObraPrintWindow`), which keeps this free of any dependency on a CSP that
 * permits `'unsafe-inline'`.
 */
export const buildObraPrintDocument = (html: string, index: number): string => {
  const report = parseReport(html);
  const source = report.querySelectorAll("div.page")[index];
  if (!source) {
    throw new Error(`The obras report has no page at index ${index}.`);
  }

  const page = source.cloneNode(true) as HTMLElement;
  page.classList.remove("brk");
  for (const detail of Array.from(page.querySelectorAll("details.all"))) {
    detail.remove();
  }
  page
    .querySelector(".budget-col")
    ?.closest("section")
    ?.classList.add(PRINT_BREAK_CLASS);

  const head = report.head.cloneNode(true) as HTMLElement;
  const breakRule = report.createElement("style");
  // Appended, never an `@page`: the sheet size stays the one the clone brought.
  breakRule.textContent = `.${PRINT_BREAK_CLASS} { break-before:page; page-break-before:always; }`;
  head.append(breakRule);

  return (
    "<!DOCTYPE html>" +
    `<html lang="pt-BR">${head.outerHTML}<body>${page.outerHTML}</body></html>`
  );
};

/**
 * Await the opened window's webfonts when it exposes them.
 *
 * Guarded rather than assumed: `document.fonts` is absent in some engines, and an
 * unguarded reach would throw where the only cost of skipping the wait is
 * printing before DM Sans has swapped in.
 *
 * The rejection is absorbed on the promise (`.catch`) and **not** in a `try`
 * around the property read, deliberately. A `try/catch` wrapping both would
 * swallow the `TypeError` from a missing `fonts` as well, which makes the guard
 * above unreachable-in-effect and unpinnable: the test's window stub omits
 * `document.fonts`, and with the broader `try` that stub passes whether or not
 * the guard is there. This shape fails loudly when the guard is removed, which
 * is the only version worth having.
 */
const whenFontsReady = async (opened: Window): Promise<void> => {
  const fonts: FontFaceSet | undefined = opened.document.fonts;
  if (!fonts) return;
  // A window whose fonts never settle still gets printed.
  await fonts.ready.catch(() => undefined);
};

/**
 * Open the chosen obra as a top-level document and print it.
 *
 * **Top level, not the iframe**, for one reason: the on-screen report lives in
 * an `<iframe sandbox="">` and a sandboxed iframe cannot print itself. That
 * attribute is not negotiable — it is what forced `<details>` over a JS
 * accordion in APRAS-115 — so this sidesteps it instead of weakening it. The
 * blob-URL-plus-`window.open` technique is `ConstructionTrackerPage`'s, already
 * shipped for the authenticated report.
 *
 * **The opener prints, the document does not.** `print()` is called here, on the
 * new window's `load`, which is legal because a blob URL inherits the creating
 * document's origin. The alternative — an inline `<script>` in the printed
 * document — would make printing depend on a CSP permitting `'unsafe-inline'`
 * and `blob:` in `script-src`; `frontend/vercel.json` ships no CSP today and
 * that is a fact which can change.
 *
 * Returns the opened window, or `null` when the popup was blocked. Synchronous
 * on purpose: the wait for the new window's `load` and its webfonts happens in
 * the listener below, so there is nothing here for a caller to await.
 */
export const openObraPrintWindow = (
  html: string,
  index: number,
): Window | null => {
  const url = URL.createObjectURL(
    new Blob([buildObraPrintDocument(html, index)], { type: "text/html" }),
  );
  const opened = window.open(url, "_blank");
  if (!opened) return null;

  opened.addEventListener(
    "load",
    () => {
      // `whenFontsReady` swallows its own failure, so `.then` is the whole
      // story and there is nothing here that can reject. No `void` operator:
      // it reads as if a rejection were being discarded, and DeepSource's
      // JS-0098 objects to it for that reason.
      whenFontsReady(opened).then(() => {
        opened.print();
      });
    },
    { once: true },
  );
  return opened;
};
