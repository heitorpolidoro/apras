/**
 * The report document the APRAS-118 tests parse, **derived from the backend's
 * own committed baselines** rather than hand-written.
 *
 * Why derived: two of this task's criteria are absence criteria — the printed
 * document carries no `details.all`, and it carries no `@page` rule beyond the
 * one it inherited. An absence asserted against a hand-written fixture is
 * satisfied by the fixture never having contained the thing, which is the
 * no-op shape this repository has already shipped eleven times. Both halves
 * here come out of files the backend suite pins:
 *
 * - `backend/tests/data/report_page_null_detail_baseline.html` — one real
 *   `div.page`, byte-pinned by `tests/test_project_stage_detail.py`. It is the
 *   all-NULL production page, so it carries no `details.all` of its own and
 *   this module inserts the markup `_stage_detail_html` emits.
 * - `backend/tests/data/report_css_shared_baseline.json` — the stylesheet as
 *   `[selector, declarations]` pairs, pinned by
 *   `tests/test_project_report_bar_geometry.py`. Reassembled here into the
 *   `<style>` the backend puts in `<head>`, which is what makes the fixture's
 *   own `@page` count (1) and its `.page.brk` rule real rather than asserted
 *   against a stylesheet written to pass.
 *
 * `../backend/tests/data` is the one directory outside the frontend root that
 * `vitest.config.ts` allows, for exactly this reason (APRAS-68 D-D set the
 * precedent with `contrast_fixtures.json`).
 */
import baselinePage from "../../../../../../backend/tests/data/report_page_null_detail_baseline.html?raw";
import cssBaselineText from "../../../../../../backend/tests/data/report_css_shared_baseline.json?raw";

/** The backend's `<style>` body, rebuilt from the pinned rule pairs. */
const stylesheet = (JSON.parse(cssBaselineText) as [string, string][])
  .map(([selector, declarations]) => `${selector} {${declarations}}`)
  .join("\n");

/**
 * The stage-detail section, shaped as `_stage_detail_html` emits it: a
 * `details.all` whose `.inner` holds one `details.ph` per frente. The baseline
 * page is the all-NULL one, so this is the only part of the fixture that is
 * not a byte out of `backend/tests/data` — and the part the removal test
 * removes, so its presence is asserted before its absence is.
 */
const STAGE_DETAIL_HTML =
  '<details class="all"><summary>Mostrar detalhes ' +
  "<em>— 1 frente, 2 serviços</em></summary>" +
  '<div class="inner">' +
  '<details class="ph"><summary><span class="dot d"></span>' +
  '<span class="ttl"><span class="top">Térreo e Superior</span>' +
  '<span class="nm">Instalações Hidraulicas</span></span>' +
  '<span class="pp">100%</span></summary>' +
  '<ul><li class="d"><span>Prumadas</span><span>100%</span></li>' +
  "<li><span>Ramais</span><span>40%</span></li></ul>" +
  "</details></div></details>";

/**
 * `_stage_detail_html`'s output is the **last child of the stages section**, so
 * it goes immediately before the `</section>` that follows `.pv`'s `.note`.
 * Anchored on those two selectors and not on any heading text; a backend rename
 * throws here loudly rather than silently producing a fixture without it.
 */
const withStageDetail = (page: string): string => {
  const noteAt = page.indexOf('<div class="note">');
  const sectionEnd = page.indexOf("</section>", noteAt);
  if (noteAt < 0 || sectionEnd < 0) {
    throw new Error(
      "report_page_null_detail_baseline.html no longer has a `.note` inside " +
        "the stages section; the APRAS-118 fixture cannot place `details.all`.",
    );
  }
  return page.slice(0, sectionEnd) + STAGE_DETAIL_HTML + page.slice(sectionEnd);
};

const replaceOnce = (html: string, from: string, to: string): string => {
  if (!html.includes(from)) {
    throw new Error(`The report baseline no longer contains ${from}`);
  }
  return html.replace(from, to);
};

/** Obra 01 — the baseline page exactly, plus the stage-detail section. */
const PAGE_ONE = withStageDetail(baselinePage);

/**
 * Obra 02 — the same page as the backend emits every obra after the first:
 * `class="page brk"`. Its title and its **hero kind** both differ from obra
 * 01's, which is what lets the modal test assert the two rows show different
 * kinds; read through a bare `.kicker` both rows would read `Obras em foco`.
 */
const PAGE_TWO = replaceOnce(
  replaceOnce(
    replaceOnce(PAGE_ONE, '<div class="page">', '<div class="page brk">'),
    '<h1 class="serif">Sede Social — Reforma</h1>',
    '<h1 class="serif">Portarias — Ampliação</h1>',
  ),
  '<span class="kicker">Obra 01 • Edificação</span>',
  '<span class="kicker">Obra 02 • Reforma</span>',
);

const wrap = (pages: string): string =>
  "<!DOCTYPE html>" +
  '<html lang="pt-BR"><head><meta charset="UTF-8">' +
  '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
  "<title>Relatório de Obras — Altos da Serra</title>" +
  `<style>${stylesheet}</style>` +
  `</head><body>${pages}</body></html>`;

/** The production shape: two obras, the second carrying `brk`. */
export const TWO_OBRA_REPORT = wrap(PAGE_ONE + PAGE_TWO);

/** One obra: the modal still opens and lists it. */
export const ONE_OBRA_REPORT = wrap(PAGE_ONE);

/** No obra: the modal opens onto the empty state. */
export const NO_OBRA_REPORT = wrap("");

/**
 * One obra whose hero kicker carries **no kind** — `_hero_html` writes plain
 * `Obra 01`, with no `•`, when the project's kind is unset. Every production row
 * today has one, but the renderer's branch exists and the modal must show a
 * title-only row rather than an empty second line.
 */
export const NO_KIND_REPORT = wrap(
  replaceOnce(
    PAGE_ONE,
    '<span class="kicker">Obra 01 • Edificação</span>',
    '<span class="kicker">Obra 01</span>',
  ),
);

/**
 * A hero carrying no `.kicker` element at all, as distinct from
 * `NO_KIND_REPORT`, whose kicker is present and merely lacks the `•`.
 *
 * The two reach the same `kind: ""` by different routes, and only this one
 * reaches the branch where the selector finds nothing: `text(null)`. Without the
 * optional chain in `text`, this fixture is a `TypeError` rather than an empty
 * string.
 */
export const NO_KICKER_REPORT = wrap(
  replaceOnce(PAGE_ONE, '<span class="kicker">Obra 01 • Edificação</span>', ""),
);

export const OBRA_ONE_TITLE = "Sede Social — Reforma";
export const OBRA_TWO_TITLE = "Portarias — Ampliação";
export const OBRA_ONE_KIND = "Edificação";
export const OBRA_TWO_KIND = "Reforma";

/**
 * How many `@page` rules the fixture's own `<head>` carries, counted rather
 * than written: the absence criterion compares the built document's count
 * against this, so an injected rule shows up as a difference.
 */
export const FIXTURE_HEAD_AT_PAGE_COUNT = (stylesheet.match(/@page/g) ?? [])
  .length;
