/// <reference types="node" />
// @vitest-environment node
//
// APRAS-82 — the contrast half of the document- and occurrence-management
// token migration.
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
 * `--color-white` and `--color-black` are the two palette entries Tailwind
 * writes as a hex literal rather than an `oklch()`. Read from the same file
 * as every other colour and handed to the module's own `hexToOklch`;
 * expanding `#fff` to six digits is the same kind of normalisation as
 * `normalise` above, not arithmetic.
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
const palette = (name: string): Oklch =>
  name === "white" || name === "black"
    ? hexDeclaration(PALETTE, `--color-${name}`)
    : declaration(PALETTE, `--color-${name}`);

const ratio = (foreground: Oklch, background: Oklch): number =>
  Number(contrastRatio(foreground, background).toFixed(4));

// --- the surfaces, each named once ----------------------------------------

const CARD = token("card");
const MUTED = token("muted");
const ACCENT = token("accent");
const PRIMARY = token("primary");
const WHITE = palette("white");

describe("the measurement is the repository's own", () => {
  // APRAS-78's, APRAS-80's and APRAS-88's published figures. If these drift,
  // `src/lib/contrast.ts` changed underneath this task and every other number
  // below is suspect.
  it.each([
    ["--primary-foreground on --primary", token("primary-foreground"), PRIMARY, 5.7588],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--primary-text on --card", token("primary-text"), CARD, 5.2096],
    ["--primary-text on --accent", token("primary-text"), ACCENT, 4.6547],
    ["--primary on --card", PRIMARY, CARD, 3.4054],
  ])("reproduces %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
  });
});

describe("the tokens this task paints with", () => {
  it.each([
    ["--primary-text on --card", token("primary-text"), CARD, 5.2096],
    ["--primary-text on --accent", token("primary-text"), ACCENT, 4.6547],
    ["--primary-text on --muted", token("primary-text"), MUTED, 4.6547],
    ["--muted-foreground on --card", token("muted-foreground"), CARD, 5.2249],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--foreground on --card", token("foreground"), CARD, 19.8801],
    ["--primary-foreground on --primary", token("primary-foreground"), PRIMARY, 5.7588],
  ])("holds AA as text: %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
    expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it.each([
    ["--primary on --card", PRIMARY, CARD, 3.4054],
    ["--primary on --accent", PRIMARY, ACCENT, 3.0427],
    ["--primary on --muted", PRIMARY, MUTED, 3.0427],
  ])("clears the 3:1 graphical floor: %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
    expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
      GRAPHICAL_CONTRAST_RATIO,
    );
  });
});

describe("the text pairs APRAS-82 changes", () => {
  // Each row carries its *own* background before and after, because several
  // of these move surface as well as foreground: a brand chip's `bg-indigo-50`
  // becomes `--accent`, a table head's `bg-slate-50` becomes `--muted`.
  it.each([
    // Headings: slate-900 and gray-900 both become --foreground on a card.
    ["headings, slate", palette("slate-900"), WHITE, token("foreground"), CARD, 17.8448, 19.8801],
    ["headings, gray", palette("gray-900"), WHITE, token("foreground"), CARD, 17.7467, 19.8801],
    // Secondary text on a card, whose surface does not move.
    ["secondary, slate-500", palette("slate-500"), WHITE, token("muted-foreground"), CARD, 4.7670, 5.2249],
    ["secondary, gray-500", palette("gray-500"), WHITE, token("muted-foreground"), CARD, 4.8357, 5.2249],
    ["secondary, slate-600", palette("slate-600"), WHITE, token("muted-foreground"), CARD, 7.5635, 5.2249],
    ["secondary, gray-600", palette("gray-600"), WHITE, token("muted-foreground"), CARD, 7.5608, 5.2249],
    // Table heads and the tag chip, whose surfaces migrate with them.
    ["table head, slate", palette("slate-500"), palette("slate-50"), token("muted-foreground"), MUTED, 4.5540, 4.6684],
    ["table head, gray", palette("gray-500"), palette("gray-50"), token("muted-foreground"), MUTED, 4.6325, 4.6684],
    ["tag chip", palette("slate-600"), palette("slate-100"), token("muted-foreground"), MUTED, 6.8989, 4.6684],
    // Primary buttons: white on indigo becomes the brand pair.
    ["primary buttons", WHITE, palette("indigo-600"), token("primary-foreground"), PRIMARY, 6.4414, 5.7588],
    // §1k's twelve character sites.
    ["selected tree rows", palette("indigo-700"), palette("indigo-50"), token("primary-text"), ACCENT, 7.2164, 4.6547],
    ["protocol and evidence chips", palette("indigo-600"), palette("indigo-50"), token("primary-text"), ACCENT, 5.7621, 4.6547],
    ["links and the protocol cell", palette("indigo-600"), WHITE, token("primary-text"), CARD, 6.4414, 5.2096],
    ["timeline transition", palette("indigo-700"), palette("gray-50"), token("primary-text"), MUTED, 7.7283, 4.6547],
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

  it("repairs the eighteen text-*-400 sites, which failed AA before", () => {
    // Eleven `text-slate-400` and seven `text-gray-400`, all on a card.
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
  });

  it("repairs the PDF viewer's download button, the operator's ruling", () => {
    // `bg-emerald-600 … text-white` becomes the brand triple. It follows each
    // condominium's brand, and `--primary-foreground` is chosen per brand —
    // a light brand gets dark text, a dark one keeps white — so this is not
    // universally dark-on-green.
    expect(ratio(WHITE, palette("emerald-600"))).toBeCloseTo(3.7194, 3);
    expect(ratio(WHITE, palette("emerald-600"))).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(ratio(token("primary-foreground"), PRIMARY)).toBeCloseTo(5.7588, 3);
    expect(ratio(token("primary-foreground"), PRIMARY)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });
});

describe("the graphical pairs APRAS-82 changes", () => {
  // §1k routes a brand class on an element that paints no glyphs to
  // `--primary`, whose floor is 1.4.11's 3:1 and not 4.5:1.
  it.each([
    ["brand icons, indigo-600 on a card", palette("indigo-600"), WHITE, PRIMARY, CARD, 6.4414, 3.4054],
    ["brand icons, indigo-500 on a card", palette("indigo-500"), WHITE, PRIMARY, CARD, 4.5587, 3.4054],
    ["tile glyphs on a brand tint", palette("indigo-600"), palette("indigo-50"), PRIMARY, ACCENT, 5.7621, 3.0427],
    ["inline glyphs on a neutral fill", palette("indigo-600"), palette("gray-50"), PRIMARY, MUTED, 6.1708, 3.0427],
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

describe("every kept text foreground whose surface migrates still clears AA", () => {
  // A kept foreground can sit on a migrated background. None of these text
  // pairs crosses 4.5:1, so this migration converts no passing text pair into
  // a failing one.
  it.each([
    ["text-gray-800, was on bg-gray-50", palette("gray-800"), palette("gray-50"), MUTED, 14.0676, 13.1205],
    ["text-gray-800, was on bg-gray-100", palette("gray-800"), palette("gray-100"), MUTED, 13.3451, 13.1205],
    ["text-gray-700, was on bg-gray-50", palette("gray-700"), palette("gray-50"), MUTED, 9.8728, 9.2081],
    ["text-gray-700, was on bg-gray-100", palette("gray-700"), palette("gray-100"), MUTED, 9.3658, 9.2081],
  ])("%s", (_name, foreground, before, after, beforeRatio, afterRatio) => {
    expect(ratio(foreground, before)).toBeCloseTo(beforeRatio, 3);
    expect(ratio(foreground, after)).toBeCloseTo(afterRatio, 3);
    expect(ratio(foreground, after)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
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

describe("declared sub-AA, none of it introduced by this task", () => {
  /**
   * Every pair this task leaves or puts below 4.5:1, each with its measured
   * before and after ratio and the floor that actually applies to it. The
   * list is explicit so that nothing below AA can pass unnamed, and so that
   * a reviewer can see at a glance which of these APRAS-82 moved and which
   * it merely inherited.
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
      // §1k routes a brand class on a glyph to `--primary`. Six sites:
      // DocumentCenterPage:100, OccurrenceBookPage:35,
      // NewOccurrenceModal:136,140,154 and OccurrenceDetailsView:173. It
      // clears 1.4.11 by 0.043 — APRAS-68 behaviour predating APRAS-77.
      site: "graphical --primary on --accent/--muted, six sites",
      foreground: PRIMARY,
      background: ACCENT,
      before: 3.0427,
      after: 3.0427,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // Kept by status set 4; its `bg-gray-50` label migrates to `--muted`.
      // It is an icon, so 1.4.11's 3:1 applies — but it crosses 4.5, so it
      // is named here rather than left for a reviewer to find.
      site: "NewOccurrenceModal.tsx:158 kept text-gray-500 Lock glyph",
      foreground: palette("gray-500"),
      background: MUTED,
      before: 4.6325,
      after: 4.3206,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      site: "NewOccurrenceModal.tsx:158 kept text-emerald-600 Globe glyph",
      foreground: palette("emerald-600"),
      background: MUTED,
      before: 3.5631,
      after: 3.3232,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // Set 3 keeps it, so it is the one `text-gray-400` in this pair that
      // the migration does not repair. Its surface does not move.
      site: "OccurrenceTable.tsx:102 kept text-gray-400 Lock glyph",
      foreground: palette("gray-400"),
      background: CARD,
      before: 2.6023,
      after: 2.6023,
      // Below even 1.4.11's floor, and unchanged: neither foreground nor
      // surface moves. A pre-existing failure this task inherits and §1i
      // forbids repairing in place; the repair tree is APRAS-90's.
      floor: 0,
    },
    {
      site: "kept text-emerald-600 on bg-emerald-50",
      foreground: palette("emerald-600"),
      background: palette("emerald-50"),
      before: 3.5279,
      after: 3.5279,
      floor: GRAPHICAL_CONTRAST_RATIO,
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
    // The two that move do so because their surface migrates; the three that
    // do not move are inherited verbatim.
    expect(ratio(palette("gray-500"), palette("gray-50"))).toBeCloseTo(4.6325, 3);
    expect(ratio(palette("emerald-600"), palette("gray-50"))).toBeCloseTo(3.5631, 3);
    expect(ratio(PRIMARY, ACCENT)).toBeCloseTo(3.0427, 3);
    expect(ratio(palette("gray-400"), CARD)).toBeCloseTo(2.6023, 3);
    expect(ratio(palette("emerald-600"), palette("emerald-50"))).toBeCloseTo(3.5279, 3);
  });

  it("names every pair it leaves below AA and no more", () => {
    for (const entry of DECLARED) {
      expect(entry.after).toBeLessThan(MINIMUM_CONTRAST_RATIO);
      expect([0, GRAPHICAL_CONTRAST_RATIO]).toContain(entry.floor);
    }
    expect(DECLARED).toHaveLength(5);

    // The one entry that meets no floor at all is the one this task does not
    // move: its before and after ratio are the same number.
    const unrepaired = DECLARED.filter((entry) => entry.floor === 0);

    expect(unrepaired).toHaveLength(1);
    expect(unrepaired[0].before).toBe(unrepaired[0].after);
  });

  it.each([
    // Unchanged pre-existing figures, every one inside a kept status set.
    ["text-emerald-700 on bg-emerald-50", palette("emerald-700"), palette("emerald-50"), 5.1582],
    ["text-emerald-800 on bg-emerald-50", palette("emerald-800"), palette("emerald-50"), 7.2679],
    ["text-emerald-900 on bg-emerald-50", palette("emerald-900"), palette("emerald-50"), 9.1968],
    ["text-amber-700 on bg-amber-50", palette("amber-700"), palette("amber-50"), 4.8611],
  ])("keeps %s verbatim", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
  });
});
