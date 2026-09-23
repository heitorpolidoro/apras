/// <reference types="node" />
// @vitest-environment node
//
// APRAS-79 — the contrast half of the lot-management token migration.
//
// Every foreground/background pair this task changes is re-measured here by
// **importing** `contrastRatio` and `parseOklch` from `src/lib/contrast.ts`.
// The arithmetic is never reimplemented: an earlier reimplementation was wrong
// by ~0.02 on every ratio because it missed the module's JND early return in
// the gamut-map bisection.
//
// The node environment is what makes `import.meta.url` a `file:` URL, so the
// two stylesheets can be read from disk; `src/__tests__/themeContrast.test.ts`
// and the migration guard do the same, for the same reason.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  MINIMUM_CONTRAST_RATIO,
  contrastRatio,
  parseOklch,
  type Oklch,
} from "../../../lib/contrast";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(HERE, "..", "..", "..", "..");

/**
 * Tailwind authors its palette with a **percentage** lightness
 * (`oklch(97.1% 0.013 17.38)`), a form `parseOklch`'s grammar rejects.
 * Normalising the literal is not a second implementation of its arithmetic —
 * it only rewrites `97.1%` as `0.971` before handing the value over.
 */
const normalise = (value: string): string =>
  value.replace(/([\d.]+)%/, (_match, digits: string) =>
    String(Number(digits) / 100),
  );

const declaration = (source: string, property: string): Oklch => {
  const match = new RegExp(
    String.raw`(?<![\w-])${property}:\s*(oklch\([^)]*\))`,
  ).exec(source);
  if (match === null) {
    throw new Error(`${property} is not declared`);
  }
  const colour = parseOklch(normalise(match[1]));
  if (colour === null) {
    throw new Error(`${property} is not a parseable oklch() value`);
  }
  return colour;
};

/** The `:root` block of `src/index.css` — never `.dark`, which is unapplied. */
const ROOT = (() => {
  const css = readFileSync(path.join(FRONTEND_ROOT, "src", "index.css"), "utf8");
  const start = css.indexOf(":root {");
  const end = css.indexOf("\n}", start);
  return css.slice(start, end);
})();

const PALETTE = readFileSync(
  path.join(FRONTEND_ROOT, "node_modules", "tailwindcss", "theme.css"),
  "utf8",
);

const token = (name: string): Oklch => declaration(ROOT, `--${name}`);
const palette = (name: string): Oklch => declaration(PALETTE, `--color-${name}`);

const ratio = (foreground: Oklch, background: Oklch): number =>
  Number(contrastRatio(foreground, background).toFixed(4));

// --- the call-site backgrounds, each named once --------------------------

const CARD = token("card");
const BACKGROUND = token("background");
const MUTED = token("muted");
const RED_50 = palette("red-50");

describe("the measurement is the repository's own", () => {
  // If these five drift, the module changed underneath this task and every
  // other number here is suspect. They are APRAS-78's published figures.
  it.each([
    ["text-red-700 on bg-red-50", palette("red-700"), RED_50, 5.9842],
    ["text-destructive on bg-red-50", token("destructive"), RED_50, 4.4006],
    ["text-red-600 on bg-red-50", palette("red-600"), RED_50, 4.4506],
    ["text-muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--primary-foreground on --primary", token("primary-foreground"), token("primary"), 5.7588],
  ])("reproduces %s at %#", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
  });
});

describe("the pairs APRAS-79 changes", () => {
  it.each([
    // Confirm-dialog headings: LotDetailsView:278, LotsPage:238,
    // ResidentsTab:177 — free-standing red on the `bg-card` panel.
    ["confirm-dialog heading", palette("red-600"), token("destructive"), CARD, 4.8619, 4.8073],
    // Page error blocks: LotDetailsView:40, LotsPage:190, ResidentsTab:109 —
    // bare divs in the page flow, so they sit on `--background`, not a card.
    ["page error text", palette("red-500"), token("destructive"), BACKGROUND, 3.7118, 4.6713],
    // Page loading blocks, the siblings of those three.
    ["page loading text", palette("slate-500"), token("muted-foreground"), BACKGROUND, 4.6322, 5.0771],
  ])(
    "%s holds AA before and after",
    (_name, before, after, background, todayRatio, afterRatio) => {
      expect(ratio(before, background)).toBeCloseTo(todayRatio, 3);
      expect(ratio(after, background)).toBeCloseTo(afterRatio, 3);
      expect(ratio(after, background)).toBeGreaterThanOrEqual(
        MINIMUM_CONTRAST_RATIO,
      );
    },
  );

  it("repairs the page error text, which failed AA before the migration", () => {
    expect(ratio(palette("red-500"), BACKGROUND)).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(ratio(token("destructive"), BACKGROUND)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it("keeps body text over both surfaces it lands on", () => {
    expect(ratio(token("muted-foreground"), CARD)).toBeCloseTo(5.2249, 3);
    expect(ratio(token("muted-foreground"), MUTED)).toBeCloseTo(4.6684, 3);
  });
});

/**
 * Pairs that do **not** reach AA, declared rather than hidden.
 *
 * The operator's recorded decision on APRAS-79: a child of APRAS-77 migrates
 * what the mapping table mandates, measures the pair and declares the number —
 * it may not except a pair on the ground that migrating makes it worse, because
 * that would need a gap code no child may add. Every entry therefore names the
 * task that owns the repair.
 *
 * **The background is traced, never assumed.** An entry's `background` is the
 * nearest ancestor that actually paints one, found by walking the JSX. That is
 * the rule the six remaining children inherit from this file: a ratio asserted
 * to +/-0.001 against a surface the element does not sit on is false precision,
 * and it is wrong *while passing*, because the assertion agrees with the wrong
 * reference.
 */
const PRE_EXISTING_SUB_AA = [
  {
    pair: "LotDetailsView active tab label, text-emerald-600 -> text-primary",
    // Traced: the label is in the tab nav at LotDetailsView.tsx:158
    // (`border-b border-border`, no fill), inside the component root at
    // LotDetailsView.tsx:81 (`space-y-6`, no fill), rendered at LotsPage.tsx:93
    // inside LotsPage.tsx:92 (`container mx-auto max-w-7xl px-4 py-8`, no
    // fill). The nearest ancestor that paints anything is App.tsx:86/112,
    // which is `bg-background`. There is no `bg-card` anywhere in that chain.
    foreground: () => palette("emerald-600"),
    after: () => token("primary"),
    background: () => BACKGROUND,
    today: 3.6142,
    then: 3.3091,
    owner: "APRAS-87",
  },
] as const;

/**
 * The same pair measured against `--card`.
 *
 * 3.7194 -> 3.4054 is the figure APRAS-79's spec and APRAS-87's justification
 * originally quoted for this label. It is a **reference measurement on a
 * surface the label does not sit on**, kept here so the older number stays
 * traceable to what it actually measured, and so nobody re-derives it and
 * concludes the call-site figures above are wrong. `--background` is
 * `oklch(0.99 0 0)` and `--card` is `oklch(1 0 0)`: they are not the same
 * colour, which is exactly why the mapping table publishes `bg-white` as
 * 0.00 / 1.00 delta-E depending on which one it becomes.
 *
 * **This constant is APRAS-79 history, not a pattern to copy.** It exists only
 * to document a mistake this task corrected — a figure that was asserted
 * against the wrong surface and is quoted elsewhere on the board. A sibling
 * should have no reason to name a ratio for a surface its element does not sit
 * on: trace the ancestry, assert that one number, and add nothing beside it.
 */
const ACTIVE_TAB_ON_CARD = { today: 3.7194, then: 3.4054 } as const;

describe("the pre-existing sub-AA pairs this task declares", () => {
  it.each(PRE_EXISTING_SUB_AA)(
    "declares $pair as owned by $owner",
    ({ foreground, after, background, today, then, owner }) => {
      const surface = background();

      expect(ratio(foreground(), surface)).toBeCloseTo(today, 3);
      expect(ratio(after(), surface)).toBeCloseTo(then, 3);
      // Both sides fail AA: the failure is inherited, not introduced, and the
      // migration is mandated by §1f case 3 because the label is a <button>.
      expect(ratio(foreground(), surface)).toBeLessThan(MINIMUM_CONTRAST_RATIO);
      expect(ratio(after(), surface)).toBeLessThan(MINIMUM_CONTRAST_RATIO);
      expect(owner).toMatch(/^APRAS-\d+$/);
    },
  );

  it("keeps the --card reference figures traceable, and distinct from the call site", () => {
    expect(ratio(palette("emerald-600"), CARD)).toBeCloseTo(
      ACTIVE_TAB_ON_CARD.today,
      3,
    );
    expect(ratio(token("primary"), CARD)).toBeCloseTo(
      ACTIVE_TAB_ON_CARD.then,
      3,
    );
    // The two surfaces really are different, so the distinction the comment
    // above draws is a fact about the stylesheet, not a preference.
    expect(ACTIVE_TAB_ON_CARD.today).not.toBeCloseTo(
      PRE_EXISTING_SUB_AA[0].today,
      3,
    );
    expect(ratio(token("card"), BACKGROUND)).toBeLessThan(1.1);
    expect(token("card")).not.toEqual(BACKGROUND);
  });

  it("is the only list of sub-AA pairs, and every other changed pair holds AA", () => {
    expect(PRE_EXISTING_SUB_AA).toHaveLength(1);
    for (const { after, background } of PRE_EXISTING_SUB_AA) {
      expect(ratio(after(), background())).toBeLessThan(MINIMUM_CONTRAST_RATIO);
    }
  });
});
