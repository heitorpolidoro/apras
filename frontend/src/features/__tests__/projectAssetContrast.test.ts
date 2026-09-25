/// <reference types="node" />
// @vitest-environment node
//
// APRAS-81 — the contrast half of the project- and asset-management token
// migration.
//
// Every foreground/background pair this task changes is re-measured here by
// **importing** `contrastRatio`, `parseOklch` and `hexToOklch` from
// `src/lib/contrast.ts`. The arithmetic is never reimplemented and no colour
// literal is written down: token values are read from `src/index.css`'s
// `:root` block — never `.dark`, which is unapplied — and palette values from
// Tailwind 4's own `node_modules/tailwindcss/theme.css`.
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
  hexToOklch,
  parseOklch,
  type Oklch,
} from "../../lib/contrast";

/** WCAG 2.1 SC 1.4.11 — the floor for a glyph that is not text. */
const GRAPHICAL_CONTRAST_RATIO = 3;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(HERE, "..", "..", "..");

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

/**
 * `--color-white` is the palette entry Tailwind writes as a hex literal
 * rather than an `oklch()`. Read from the same file as every other colour and
 * handed to the module's own `hexToOklch`; expanding `#fff` to six digits is
 * the same kind of normalisation as `normalise` above, not arithmetic.
 */
const hexDeclaration = (source: string, property: string): Oklch => {
  const match = new RegExp(
    String.raw`(?<![\w-])${property}:\s*(#[0-9a-fA-F]{3,6})`,
  ).exec(source);
  if (match === null) {
    throw new Error(`${property} is not declared`);
  }
  const digits = match[1].slice(1);
  const colour = hexToOklch(
    `#${
      digits.length === 3
        ? digits
            .split("")
            .map((digit) => `${digit}${digit}`)
            .join("")
        : digits
    }`,
  );
  if (colour === null) {
    throw new Error(`${property} is not a parseable hex literal`);
  }
  return colour;
};

/**
 * The `:root` block of `src/index.css`.
 *
 * Located by the `:root {` opener rather than by position: `.dark` is written
 * **before** `:root` in that file, so slicing from the start of the file
 * returns the unapplied dark block instead.
 */
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
const palette = (name: string): Oklch =>
  name === "white" || name === "black"
    ? hexDeclaration(PALETTE, `--color-${name}`)
    : declaration(PALETTE, `--color-${name}`);

const ratio = (foreground: Oklch, background: Oklch): number =>
  Number(contrastRatio(foreground, background).toFixed(4));

// --- the surfaces, each named once ----------------------------------------

const BACKGROUND = token("background");
const CARD = token("card");
const MUTED = token("muted");
const ACCENT = token("accent");
const PRIMARY = token("primary");
const DESTRUCTIVE = token("destructive");
const WHITE = palette("white");

describe("the measurement is the repository's own", () => {
  // APRAS-78's, APRAS-80's and APRAS-88's published figures. If these drift,
  // `src/lib/contrast.ts` changed underneath this task and every other number
  // below is suspect.
  it.each([
    ["--primary-foreground on --primary", token("primary-foreground"), PRIMARY, 5.7588],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--primary-text on --card", token("primary-text"), CARD, 5.2096],
    ["text-red-700 on bg-red-50", palette("red-700"), palette("red-50"), 5.9842],
  ])("reproduces %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
  });
});

describe("the tokens this task paints with", () => {
  it.each([
    ["--primary-text on --accent", token("primary-text"), ACCENT, 4.6547],
    ["--muted-foreground on --card", token("muted-foreground"), CARD, 5.2249],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--foreground on --card", token("foreground"), CARD, 19.8801],
    ["--primary-foreground on --primary", token("primary-foreground"), PRIMARY, 5.7588],
    ["--destructive on --card", DESTRUCTIVE, CARD, 4.8073],
  ])("holds AA as text: %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
    expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it.each([
    ["--primary on --card", PRIMARY, CARD, 3.4054],
    ["--primary on --muted", PRIMARY, MUTED, 3.0427],
    ["--primary on --accent", PRIMARY, ACCENT, 3.0427],
    // The two `ConstructionTrackerPage` spinners sit on the page root, which
    // the operator's §1f case 1 ruling sends to `bg-background` — so they are
    // measured against `--background` and not against `--muted`.
    ["--primary on --background", PRIMARY, BACKGROUND, 3.3091],
  ])(
    "clears the 3:1 graphical floor: %s",
    (_name, foreground, background, expected) => {
      expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
      expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
        GRAPHICAL_CONTRAST_RATIO,
      );
    },
  );
});

describe("the text pairs APRAS-81 changes", () => {
  // Each row carries its *own* background before and after, because several
  // of these move surface as well as foreground: a gauge's `bg-indigo-50`
  // becomes `--accent`, a table head's `bg-gray-50` becomes `--muted`.
  it.each([
    ["headings, slate", palette("slate-900"), WHITE, token("foreground"), CARD, 17.8448, 19.8801],
    ["headings, gray", palette("gray-900"), WHITE, token("foreground"), CARD, 17.7467, 19.8801],
    ["secondary, slate-500", palette("slate-500"), WHITE, token("muted-foreground"), CARD, 4.7670, 5.2249],
    ["secondary, gray-500", palette("gray-500"), WHITE, token("muted-foreground"), CARD, 4.8357, 5.2249],
    ["secondary, gray-600", palette("gray-600"), WHITE, token("muted-foreground"), CARD, 7.5608, 5.2249],
    // Surfaces that migrate with their foreground.
    ["panel text on bg-slate-50", palette("slate-500"), palette("slate-50"), token("muted-foreground"), MUTED, 4.5540, 4.6684],
    ["asset-tag chip on bg-gray-100", palette("gray-600"), palette("gray-100"), token("muted-foreground"), MUTED, 6.8711, 4.6684],
    // Primary buttons: white on indigo becomes the brand pair.
    ["primary buttons", WHITE, palette("indigo-600"), token("primary-foreground"), PRIMARY, 6.4414, 5.7588],
    // §1k's two character sites, both in the physical-progress gauge.
    ["gauge label", palette("indigo-700"), palette("indigo-50"), token("primary-text"), ACCENT, 7.2164, 4.6547],
    ["gauge figure", palette("indigo-900"), palette("indigo-50"), token("primary-text"), ACCENT, 10.2604, 4.6547],
  ])(
    "%s holds AA before and after",
    (_name, before, beforeOn, after, afterOn, todayRatio, afterRatio) => {
      expect(ratio(before, beforeOn)).toBeCloseTo(todayRatio, 3);
      expect(ratio(after, afterOn)).toBeCloseTo(afterRatio, 3);
      expect(ratio(after, afterOn)).toBeGreaterThanOrEqual(
        MINIMUM_CONTRAST_RATIO,
      );
    },
  );

  it("repairs the nineteen text-*-400 sites, which failed AA before", () => {
    // Eleven `text-slate-400` and eight `text-gray-400`, all of them secondary
    // text or glyphs on a card or a panel.
    expect(ratio(palette("slate-400"), CARD)).toBeCloseTo(2.6282, 3);
    expect(ratio(palette("gray-400"), CARD)).toBeCloseTo(2.6023, 3);
    expect(ratio(palette("slate-400"), CARD)).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(ratio(palette("gray-400"), CARD)).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(ratio(token("muted-foreground"), CARD)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(ratio(token("muted-foreground"), MUTED)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });
});

describe("the graphical pairs APRAS-81 changes", () => {
  // §1k routes a brand class on an element that paints no glyphs to
  // `--primary`, whose floor is 1.4.11's 3:1 and not 4.5:1.
  it.each([
    ["brand icons on a card", palette("indigo-600"), WHITE, PRIMARY, CARD, 6.4414, 3.4054],
    ["spinners on the page root", palette("indigo-600"), palette("slate-50"), PRIMARY, BACKGROUND, 6.1536, 3.3091],
    ["tile glyph on a brand tint", palette("indigo-600"), palette("indigo-50"), PRIMARY, ACCENT, 5.7621, 3.0427],
    ["progress fill on a neutral track", palette("indigo-600"), palette("slate-100"), PRIMARY, MUTED, 5.8754, 3.0427],
    ["delete icon on a card", palette("red-600"), WHITE, DESTRUCTIVE, CARD, 4.8619, 4.8073],
  ])(
    "%s clears the 3:1 floor before and after",
    (_name, before, beforeOn, after, afterOn, todayRatio, afterRatio) => {
      expect(ratio(before, beforeOn)).toBeCloseTo(todayRatio, 3);
      expect(ratio(after, afterOn)).toBeCloseTo(afterRatio, 3);
      expect(ratio(after, afterOn)).toBeGreaterThanOrEqual(
        GRAPHICAL_CONTRAST_RATIO,
      );
    },
  );
});

describe("every kept foreground whose surface migrates still clears AA", () => {
  // A kept foreground can sit on a migrated background. None of these text
  // pairs crosses 4.5:1, so this migration converts no passing text pair into
  // a failing one.
  it.each([
    ["text-slate-700, was on bg-slate-50", palette("slate-700"), palette("slate-50"), MUTED, 9.8820, 9.2424],
    ["text-gray-700, was on bg-gray-50", palette("gray-700"), palette("gray-50"), MUTED, 9.8728, 9.2081],
    ["text-slate-800, was on bg-slate-50", palette("slate-800"), palette("slate-50"), MUTED, 14.0024, 13.0962],
    ["text-gray-800, was on bg-gray-100", palette("gray-800"), palette("gray-100"), MUTED, 13.3451, 13.1205],
  ])("%s", (_name, foreground, before, after, beforeRatio, afterRatio) => {
    expect(ratio(foreground, before)).toBeCloseTo(beforeRatio, 3);
    expect(ratio(foreground, after)).toBeCloseTo(afterRatio, 3);
    expect(ratio(foreground, after)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it("measures no kept foreground against --background", () => {
    // Nothing paints text directly on `ConstructionTrackerPage`'s page root:
    // its only descendants painting on it are the two spinner icons, which
    // are graphical and are measured above. The rows of this block are
    // therefore all against `--muted`, and that is asserted rather than left
    // to the reader.
    const keptSurfaces = [MUTED, MUTED, MUTED, MUTED];

    expect(keptSurfaces.every((surface) => surface === MUTED)).toBe(true);
    expect(keptSurfaces).not.toContain(BACKGROUND);
  });

  it.each([
    ["text-slate-700", palette("slate-700"), 10.3442],
    ["text-slate-800", palette("slate-800"), 14.6574],
    ["text-gray-800", palette("gray-800"), 14.6846],
  ])(
    "%s is unchanged to the digit when bg-white becomes --card",
    (_name, foreground, expected) => {
      // `--card` is `oklch(1 0 0)` and `bg-white` is `#fff`: the same colour.
      expect(ratio(foreground, WHITE)).toBeCloseTo(expected, 3);
      expect(ratio(foreground, CARD)).toBeCloseTo(expected, 3);
      expect(ratio(foreground, CARD)).toBeGreaterThanOrEqual(
        MINIMUM_CONTRAST_RATIO,
      );
    },
  );
});

describe("declared sub-AA or unmeasurable, none of it introduced by this task", () => {
  /**
   * Every pair this task leaves or puts below 4.5:1, each with its measured
   * before and after ratio and the floor that actually applies to it. The
   * list is explicit so that nothing below AA can pass unnamed, and so that
   * a reviewer can see at a glance which of these APRAS-81 moved and which it
   * merely inherited.
   */
  const DECLARED: ReadonlyArray<{
    readonly site: string;
    readonly foreground: Oklch;
    readonly background: Oklch;
    readonly before: number;
    readonly after: number;
    readonly floor: number;
  }> = [
    {
      // `ProjectUpdateFeed:92`, an icon-only delete `<button>` in a card whose
      // `bg-slate-50` becomes `--muted`. Today the same icon measures 4.6446.
      site: "ProjectUpdateFeed.tsx:92 --destructive on --muted, icon-only",
      foreground: DESTRUCTIVE,
      background: MUTED,
      before: 4.6446,
      after: 4.2953,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `AssetSummaryCards:52`'s tile glyph and the two progress fills. It
      // clears 1.4.11 by 0.043 — APRAS-68 behaviour predating APRAS-77, which
      // §1k routes here deliberately.
      site: "graphical --primary on --accent/--muted",
      foreground: PRIMARY,
      background: ACCENT,
      before: 3.0427,
      after: 3.0427,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // Kept by status set 12; its surface does not move either.
      site: "AssetTable.tsx:164 kept text-amber-600 on bg-amber-100",
      foreground: palette("amber-600"),
      background: palette("amber-100"),
      before: 2.8643,
      after: 2.8643,
      // Below even 1.4.11's floor, and unchanged: neither foreground nor
      // surface moves. A pre-existing failure this task inherits and §1i
      // forbids repairing in place.
      floor: 0,
    },
    {
      site: "AssetSummaryCards.tsx:88 kept text-emerald-600 on bg-emerald-50",
      foreground: palette("emerald-600"),
      background: palette("emerald-50"),
      before: 3.5279,
      after: 3.5279,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `ConstructionTrackerPage:442`'s empty-state `<Building2 />`, kept
      // verbatim on a surface that does not move.
      site: "ConstructionTrackerPage.tsx:442 kept text-slate-300 on --card",
      foreground: palette("slate-300"),
      background: CARD,
      before: 1.4844,
      after: 1.4844,
      floor: 0,
    },
  ];

  it.each(DECLARED)("$site measures as declared", (entry) => {
    expect(ratio(entry.foreground, entry.background)).toBeCloseTo(
      entry.after,
      3,
    );
    expect(ratio(entry.foreground, entry.background)).toBeGreaterThanOrEqual(
      entry.floor,
    );
  });

  it("measures each declared pair's *before* ratio too", () => {
    // The one that moves does so because its surface migrates; the rest are
    // inherited verbatim.
    expect(ratio(palette("red-600"), palette("slate-50"))).toBeCloseTo(4.6446, 3);
    expect(ratio(PRIMARY, ACCENT)).toBeCloseTo(3.0427, 3);
    expect(ratio(palette("amber-600"), palette("amber-100"))).toBeCloseTo(2.8643, 3);
    expect(ratio(palette("emerald-600"), palette("emerald-50"))).toBeCloseTo(3.5279, 3);
    expect(ratio(palette("slate-300"), CARD)).toBeCloseTo(1.4844, 3);
  });

  it("names every pair it leaves below AA and no more", () => {
    for (const entry of DECLARED) {
      expect(entry.after).toBeLessThan(MINIMUM_CONTRAST_RATIO);
      expect([0, GRAPHICAL_CONTRAST_RATIO]).toContain(entry.floor);
    }
    expect(DECLARED).toHaveLength(5);

    // The entries that meet no floor at all are the ones this task does not
    // move: their before and after ratio are the same number.
    const unrepaired = DECLARED.filter((entry) => entry.floor === 0);

    expect(unrepaired).toHaveLength(2);
    for (const entry of unrepaired) {
      expect(entry.before).toBe(entry.after);
    }
  });

  it("leaves one pair unmeasurable by construction, and says so", () => {
    // `ProjectSummaryCard:94`'s `hover:text-primary` sits on a `bg-black/50`
    // scrim over a user-uploaded cover photo: the background carries no token
    // and no fixed colour, so there is no pair to measure. Declared, not
    // asserted — the class is still logged, and its scrim is `GAP-OVERLAY`.
    const UNMEASURABLE = [
      "ProjectSummaryCard.tsx:94 hover:text-primary over a bg-black/50 scrim",
    ];

    expect(UNMEASURABLE).toHaveLength(1);
  });

  it.each([
    // The three kept status fills whose track migrates from `bg-slate-100` to
    // `--muted`. Every one moves by under a tenth of a ratio point and none
    // of them crosses the 3:1 graphical floor in either direction, so this
    // task neither repairs nor breaks them: pre-existing, declared, kept.
    ["bg-emerald-500", palette("emerald-500"), 2.2832, 2.2366],
    ["bg-red-500", palette("red-500"), 3.4842, 3.4130],
    ["bg-amber-500", palette("amber-500"), 1.9567, 1.9167],
  ])("keeps %s, whose track migrates, on its side of the floor", (_name, fill, before, after) => {
    expect(ratio(fill, palette("slate-100"))).toBeCloseTo(before, 3);
    expect(ratio(fill, MUTED)).toBeCloseTo(after, 3);
    expect(Math.abs(before - after)).toBeLessThan(0.1);
    expect(after >= GRAPHICAL_CONTRAST_RATIO).toBe(
      before >= GRAPHICAL_CONTRAST_RATIO,
    );
  });
});
