/// <reference types="node" />
// @vitest-environment node
//
// The landing page's four preview status badges (APRAS-75, review round 2).
//
// The page is the first screen a prospective tenant sees and the one screen
// shown under a tenant's own branding at `/c/<slug>`, so the spec forbids new
// colour literals on it. The first implementation shipped four badges painted
// with raw Tailwind palette classes (`bg-blue-100 text-blue-700` and three
// siblings) — exactly the shape APRAS-79/APRAS-80 are removing from the rest
// of the tree.
//
// The replacement is **not** the brand. `docs/frontend/theme-token-mapping.md`
// carries the operator's binding status-colour ruling — "a status colour is
// semantic, not brand … a condominium whose brand is red must not see
// 'success' rendered in red" — so binding "In Progress" or "Authorized" to
// `--primary` would be the wrong kind of semantic. The codebase already has a
// status-tint scheme for precisely this: the `--status-*-bg/fg` and
// `--priority-*-bg/fg` pairs declared in `src/index.css`'s `:root` and
// consumed by `src/components/ui/badge.tsx`'s variants. The four previews
// mirror four real app states, so they take the four matching pairs.
//
// Nothing below reimplements the measurement: `contrastRatio` and `parseOklch`
// come from `src/lib/contrast.ts`, the repository's single contrast
// implementation, and both colours of every pair are read out of
// `src/index.css`'s `:root` block — never out of `.dark`, never as a literal.
// No pair carries an opacity modifier, so `compositeOver` is not needed here:
// each tint surface is opaque and the pixels read are the declared tokens.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  contrastRatio,
  parseOklch,
  MINIMUM_CONTRAST_RATIO,
  type Oklch,
} from "../../../lib/contrast";

/** Ratios are published to four decimals; assert to ±0.001. */
const DECIMALS = 3;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(HERE, "..", "..", "..", "..");
const SOURCE = readFileSync(
  path.join(HERE, "..", "pages", "LandingPage.tsx"),
  "utf8",
);

// --- the palette grammar (§3b of the theme token mapping) ------------------

const VARIANTS = String.raw`(?:[a-z0-9][a-z0-9.\-]*(?:\[[^\]]*\])?:)*`;
const PREFIX =
  "(?:bg|text|border|ring|outline|divide|placeholder|caret|accent|" +
  "decoration|shadow|fill|stroke|from|via|to)";
const FAMILY =
  "(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|" +
  "green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)";
// Longest-first, or `50` matches inside `500` and the sweep under-reports.
const SCALE = "(?:950|900|800|700|600|500|400|300|200|100|50)";
const OPACITY = String.raw`(?:/(?:[0-9]{1,3}|\[[^\]]*\]))?`;

/** Built fresh on every call because a `g` regex carries `lastIndex`. */
const paletteGrammar = (): RegExp =>
  new RegExp(
    String.raw`(?<![\w-])${VARIANTS}${PREFIX}-(?:${FAMILY}-${SCALE}|white|black)(?![\w-])${OPACITY}`,
    "g",
  );

const HEX_LITERAL = /#[0-9a-fA-F]{6}/g;

// --- the token reader ------------------------------------------------------

const STYLESHEET = readFileSync(
  path.join(FRONTEND_ROOT, "src", "index.css"),
  "utf8",
);

/**
 * The `:root` block of `index.css`, and only it.
 *
 * Never `.dark`: the stylesheet declares several tokens twice and a last-wins
 * reader would silently measure the dark scheme. Sliced from the `:root {`
 * opener because `@custom-variant dark (&:is(.dark *))` carries the text
 * `.dark` before `:root` ever opens.
 */
const ROOT_BLOCK = (() => {
  const start = STYLESHEET.indexOf(":root {");
  return STYLESHEET.slice(start, STYLESHEET.indexOf("}", start));
})();

const token = (name: string): Oklch => {
  const declared = new RegExp(String.raw`--${name}:\s*([^;]+);`).exec(
    ROOT_BLOCK,
  );
  const colour = parseOklch((declared?.[1] ?? "").trim());
  if (colour === null) {
    throw new Error(`index.css :root declares no readable --${name}`);
  }
  return colour;
};

// --- the four badges -------------------------------------------------------

/**
 * One preview badge: the app state it mirrors, the `badge.tsx` variant whose
 * token pair it therefore takes, and the ratio that pair measures.
 */
interface Badge {
  readonly label: string;
  readonly pair: string;
  readonly ratio: number;
}

const BADGES: readonly Badge[] = [
  // "Em Andamento" / "In Progress" — badge.tsx's `in_progress` variant.
  { label: "landing.previews.tasks.status", pair: "status-in-progress", ratio: 7.2707 },
  // "Prioridade Alta" / "High Priority" — badge.tsx's `high` variant.
  { label: "landing.previews.tasks.priority", pair: "priority-high", ratio: 5.2736 },
  // "Autorizado pelo morador" — the authorization succeeded: `completed`.
  { label: "landing.previews.access.status", pair: "status-completed", ratio: 7.3568 },
  // "Notificação Emitida … prazo de manifestação": awaiting a response, so
  // `pending` rather than a colour chosen to look like the old orange.
  { label: "landing.previews.infractions.status", pair: "status-pending", ratio: 5.3789 },
];

// --- the cases -------------------------------------------------------------

describe("the landing page's colour classes", () => {
  it("carries no raw Tailwind palette class anywhere", () => {
    expect(SOURCE.match(paletteGrammar()) ?? []).toEqual([]);
  });

  it("carries no six-digit hex literal", () => {
    expect(SOURCE.match(HEX_LITERAL) ?? []).toEqual([]);
  });

  it("reads the page it claims to sweep", () => {
    // A sweep pointed at an empty string would pass both cases above for the
    // wrong reason.
    expect(SOURCE).toContain("landing.previews.tasks.status");
    expect(paletteGrammar().test("bg-blue-100")).toBe(true);
  });
});

describe("the four preview status badges", () => {
  it.each(BADGES)(
    "paints $label with the $pair token pair",
    ({ label, pair }) => {
      const site = SOURCE.split("\n").find((line) => line.includes(label));
      expect(site, `${label} is not rendered`).toBeDefined();
      // The whole badge is on the span above the label line in the JSX, so
      // the class string is matched against the source as a whole and the
      // label's presence is asserted separately.
      expect(SOURCE).toContain(
        `bg-[var(--${pair}-bg)] text-[var(--${pair}-fg)]`,
      );
    },
  );

  it.each(BADGES)(
    "measures $pair at or above the AA floor",
    ({ pair, ratio }) => {
      const measured = contrastRatio(token(`${pair}-fg`), token(`${pair}-bg`));

      expect(measured).toBeCloseTo(ratio, DECIMALS);
      expect(measured).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
    },
  );

  it("uses four distinct pairs, one per badge", () => {
    expect(new Set(BADGES.map((badge) => badge.pair)).size).toBe(BADGES.length);
  });
});
