/// <reference types="node" />
// @vitest-environment node
//
// APRAS-83 — the contrast half of the finance, purchase-management and
// access-control token migration.
//
// Every foreground/background pair this task changes is re-measured here by
// **importing** `contrastRatio`, `parseOklch`, `hexToOklch` and `compositeOver`
// from `src/lib/contrast.ts`. The arithmetic is never reimplemented — a
// verbatim copy of `compositeOver` was rejected in APRAS-87's review — and no
// colour literal is written down: token values are read from `src/index.css`'s
// `:root` block, never `.dark`, which is unapplied, and palette values from
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
  compositeOver,
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
 * Located by the `:root {` opener rather than by a bare `indexOf(".dark")`:
 * the substring `.dark` first occurs at character 51, inside the
 * `@custom-variant dark (&:is(.dark *));` declaration on line 3, long before
 * the `:root {` block at line 32 — so using it as a block delimiter slices an
 * empty range. The `.dark {` block itself is at line 90, after `:root {`.
 */
const ROOT = (() => {
  const css = readFileSync(
    path.join(FRONTEND_ROOT, "src", "index.css"),
    "utf8",
  );
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
    ["--primary-text on --accent", token("primary-text"), ACCENT, 4.6547],
    ["--primary on --card", PRIMARY, CARD, 3.4054],
    ["--primary on --background", PRIMARY, BACKGROUND, 3.3091],
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
    ["--foreground on --background", token("foreground"), BACKGROUND, 19.3178],
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
    ["--primary on --background", PRIMARY, BACKGROUND, 3.3091],
    ["--primary on --accent", PRIMARY, ACCENT, 3.0427],
    ["--primary on --muted", PRIMARY, MUTED, 3.0427],
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

describe("the text pairs APRAS-83 changes", () => {
  // Each row carries its *own* background before and after, because several
  // of these move surface as well as foreground: a table head's `bg-slate-50`
  // becomes `--muted`, a device-key chip's `bg-indigo-50` becomes `--accent`.
  it.each([
    ["headings, slate", palette("slate-900"), WHITE, token("foreground"), CARD, 17.8448, 19.8801],
    ["headings, gray", palette("gray-900"), WHITE, token("foreground"), CARD, 17.7467, 19.8801],
    ["secondary, slate-500", palette("slate-500"), WHITE, token("muted-foreground"), CARD, 4.7670, 5.2249],
    ["secondary, gray-500", palette("gray-500"), WHITE, token("muted-foreground"), CARD, 4.8357, 5.2249],
    ["secondary, slate-600", palette("slate-600"), WHITE, token("muted-foreground"), CARD, 7.5635, 5.2249],
    ["secondary, gray-600", palette("gray-600"), WHITE, token("muted-foreground"), CARD, 7.5608, 5.2249],
    // Surfaces that migrate with their foreground.
    ["table head on bg-slate-50", palette("slate-500"), palette("slate-50"), token("muted-foreground"), MUTED, 4.5540, 4.6684],
    ["table head on bg-gray-50", palette("gray-500"), palette("gray-50"), token("muted-foreground"), MUTED, 4.6325, 4.6684],
    // The two primary fills. White on `indigo-600` was already AA; white on
    // `emerald-600` was not, and the brand pair repairs it.
    ["primary button", WHITE, palette("indigo-600"), token("primary-foreground"), PRIMARY, 6.4414, 5.7588],
    ["download link", WHITE, palette("emerald-600"), token("primary-foreground"), PRIMARY, 3.7194, 5.7588],
    // §1k's two character sites, both on a brand tint that becomes `--accent`.
    ["device-key chip", palette("indigo-700"), palette("indigo-50"), token("primary-text"), ACCENT, 7.2164, 4.6547],
    ["file-input button", palette("indigo-700"), palette("indigo-50"), token("primary-text"), ACCENT, 7.2164, 4.6547],
  ])(
    "%s holds AA after, and its before ratio is measured too",
    (_name, before, beforeOn, after, afterOn, todayRatio, afterRatio) => {
      expect(ratio(before, beforeOn)).toBeCloseTo(todayRatio, 3);
      expect(ratio(after, afterOn)).toBeCloseTo(afterRatio, 3);
      expect(ratio(after, afterOn)).toBeGreaterThanOrEqual(
        MINIMUM_CONTRAST_RATIO,
      );
    },
  );

  it("repairs the download link, which failed AA before", () => {
    expect(ratio(WHITE, palette("emerald-600"))).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(
      ratio(token("primary-foreground"), PRIMARY),
    ).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
  });

  it("repairs the fifteen text-*-400 sites, which failed AA before", () => {
    // Eight `text-slate-400` and seven `text-gray-400`, all of them secondary
    // text or glyphs on a card.
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

  it("measures the page heading on the shell the operator ruled on", () => {
    // `FinanceDashboardPage`'s `<h1>` sits inside the `bg-white` header card,
    // not on the shell, so its own move is the `--card` row above. The shell
    // itself moves `bg-slate-50` → `--background`, and the spec's "page
    // headings" row quotes both of its figures against `--background`
    // (17.3401 → 19.3178). The ratio a heading would *actually* have measured
    // on the old `bg-slate-50` is 17.0474, recorded here so neither reading is
    // hidden. Every one of the three is far above AA.
    expect(ratio(palette("slate-900"), BACKGROUND)).toBeCloseTo(17.3401, 3);
    expect(ratio(palette("slate-900"), palette("slate-50"))).toBeCloseTo(
      17.0474,
      3,
    );
    expect(ratio(token("foreground"), BACKGROUND)).toBeCloseTo(19.3178, 3);
    for (const measured of [
      ratio(palette("slate-900"), BACKGROUND),
      ratio(palette("slate-900"), palette("slate-50")),
      ratio(token("foreground"), BACKGROUND),
    ]) {
      expect(measured).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
    }
  });
});

describe("the graphical pairs APRAS-83 changes", () => {
  // §1k routes a brand class on an element that paints no glyphs to
  // `--primary`, whose floor is 1.4.11's 3:1 and not 4.5:1.
  it.each([
    ["brand icons on a card", palette("indigo-600"), WHITE, PRIMARY, CARD, 6.4414, 3.4054],
    ["the FileText glyph on a card", palette("indigo-500"), WHITE, PRIMARY, CARD, 4.5587, 3.4054],
    ["page-header brand icons", palette("indigo-600"), BACKGROUND, PRIMARY, BACKGROUND, 6.2592, 3.3091],
    ["the tile glyph on a brand tint", palette("indigo-600"), palette("indigo-50"), PRIMARY, ACCENT, 5.7621, 3.0427],
    ["the inline glyph on a neutral cell", palette("indigo-600"), palette("slate-50"), PRIMARY, MUTED, 6.1536, 3.0427],
    ["the Award control glyph", palette("emerald-600"), WHITE, PRIMARY, CARD, 3.7194, 3.4054],
    ["the six delete glyphs", palette("red-500"), WHITE, DESTRUCTIVE, CARD, 3.8199, 4.8073],
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

  it("measures the Award glyph on the lowest-price column too", () => {
    // `QuoteComparisonTable:300`'s `<Award/>` sits in a column head that
    // carries set 18's kept `bg-emerald-50/60` when that column is the
    // lowest-price one. Read as the opaque tint the spec quotes, `--primary`
    // measures 3.2301 there; composited at its declared 60% over `--card` with
    // the module's own `compositeOver` it measures 3.3067. Above 3 both ways,
    // and above the 3.5279 → 3.2301 the same glyph loses in emerald.
    const opaque = palette("emerald-50");
    const tinted = compositeOver(palette("emerald-50"), CARD, 0.6);

    expect(ratio(PRIMARY, opaque)).toBeCloseTo(3.2301, 3);
    expect(ratio(PRIMARY, tinted)).toBeCloseTo(3.3067, 3);
    expect(ratio(palette("emerald-600"), opaque)).toBeCloseTo(3.5279, 3);
    for (const measured of [
      ratio(PRIMARY, opaque),
      ratio(PRIMARY, tinted),
      ratio(palette("emerald-600"), opaque),
    ]) {
      expect(measured).toBeGreaterThanOrEqual(GRAPHICAL_CONTRAST_RATIO);
    }
  });
});

describe("every kept text foreground whose surface migrates still clears AA", () => {
  // A kept foreground can sit on a migrated background. None of these text
  // pairs crosses 4.5:1, so this migration converts no passing text pair into
  // a failing one.
  it.each([
    ["text-gray-700, was on bg-gray-50", palette("gray-700"), palette("gray-50"), MUTED, 9.8728, 9.2081],
    ["text-slate-800, was on bg-slate-50", palette("slate-800"), palette("slate-50"), MUTED, 14.0024, 13.0962],
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
    ["text-gray-700", palette("gray-700"), 10.3058],
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

  it("measures no kept text foreground against --background", () => {
    // Nothing paints on `FinanceDashboardPage:48`'s shell: its children are
    // the `bg-white` header card, `CashBalanceCard`'s three `bg-white` tiles,
    // the two `bg-white` panels and three modals. The rows of this block are
    // therefore all against `--card` or `--muted`, and that is asserted rather
    // than left to the reader.
    const keptSurfaces = [MUTED, MUTED, CARD, CARD, CARD, CARD];

    expect(keptSurfaces).not.toContain(BACKGROUND);
    expect(
      keptSurfaces.every((surface) => surface === MUTED || surface === CARD),
    ).toBe(true);
  });
});

describe("declared sub-AA or unmeasurable, none of it introduced by this task", () => {
  /**
   * Every kept or migrated pair this task leaves below 4.5:1, each with its
   * measured before and after ratio and the floor that actually applies to it.
   * The list is explicit so that nothing below AA can pass unnamed, and so
   * that a reviewer can see at a glance which of these APRAS-83 moved and
   * which it merely inherited.
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
      // `CashBalanceCard:24`'s `<Wallet/>` in its `bg-indigo-50` tile and
      // `CategoryTransactionDrilldown:69`'s `<FileText/>` button on
      // `BudgetVsActualTable:112`'s cell. Clears 1.4.11 by 0.043 — APRAS-68
      // behaviour predating APRAS-77, which §1k routes here deliberately.
      site: "graphical --primary on --accent/--muted, 2 sites",
      foreground: PRIMARY,
      background: ACCENT,
      before: 3.0427,
      after: 3.0427,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `AccessControlPage:34`'s `<ScanFace/>` and `GateMonitorPage:27`'s
      // `<Radio/>`, both in a page header carrying no background class.
      site: "graphical --primary on --background, 2 sites",
      foreground: PRIMARY,
      background: BACKGROUND,
      before: 3.3091,
      after: 3.3091,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `CategoryTransactionDrilldown:79`'s empty-state `<FileX2/>`, kept
      // verbatim while its host cell's `bg-slate-50` becomes `--muted`. It
      // fails the 3:1 floor **before** this task as well as after; §1i forbids
      // repairing it in place and the tree-wide repair is APRAS-90's.
      site: "CategoryTransactionDrilldown.tsx:79 kept text-slate-300, host cell migrates",
      foreground: palette("slate-300"),
      background: MUTED,
      before: 1.4181,
      after: 1.3263,
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
    {
      // `AccessEventFeed:27`'s granted `<CheckCircle2/>`, set 1.
      site: "kept text-emerald-500 on white",
      foreground: palette("emerald-500"),
      background: WHITE,
      before: 2.5032,
      after: 2.5032,
      floor: 0,
    },
    {
      // `AccessEventFeed:29`'s denied `<XCircle/>`, the other half of set 1.
      site: "kept text-red-500 on white",
      foreground: palette("red-500"),
      background: WHITE,
      before: 3.8199,
      after: 3.8199,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `CashBalanceCard:55`, a pre-existing AA failure §1j already records.
      site: "kept text-red-600 on bg-red-50",
      foreground: palette("red-600"),
      background: palette("red-50"),
      before: 4.4506,
      after: 4.4506,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      site: "kept text-amber-600 on bg-amber-50",
      foreground: palette("amber-600"),
      background: palette("amber-50"),
      before: 3.0755,
      after: 3.0755,
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
    // The one that moves does so because its surface migrates; the rest are
    // inherited verbatim on a surface that does not move.
    expect(ratio(palette("slate-300"), palette("slate-50"))).toBeCloseTo(
      1.4181,
      3,
    );
    for (const entry of DECLARED) {
      if (!entry.site.startsWith("CategoryTransactionDrilldown")) {
        expect(entry.before).toBe(entry.after);
      }
    }
  });

  it("names every pair it leaves below AA and no more", () => {
    for (const entry of DECLARED) {
      expect(entry.after).toBeLessThan(MINIMUM_CONTRAST_RATIO);
      expect([0, GRAPHICAL_CONTRAST_RATIO]).toContain(entry.floor);
    }
    expect(DECLARED).toHaveLength(8);

    // The entries that meet no floor at all are pre-existing failures this
    // task inherits and §1i forbids repairing in place. One of them — the
    // `text-slate-300` glyph — fails the 3:1 floor before this task as well as
    // after, which is why its `before` is recorded and asserted above.
    const unrepaired = DECLARED.filter((entry) => entry.floor === 0);

    expect(unrepaired).toHaveLength(2);
    for (const entry of unrepaired) {
      expect(entry.before).toBeLessThan(GRAPHICAL_CONTRAST_RATIO);
      expect(entry.after).toBeLessThan(GRAPHICAL_CONTRAST_RATIO);
    }
  });

  it("clears AA at the kept status pairs the spec quotes above the floor", () => {
    // Named alongside the sub-AA list so the whole of §1j's inherited set is
    // measured in one place rather than half of it.
    for (const [foreground, background, expected] of [
      [palette("amber-700"), palette("amber-50"), 4.8611],
      [palette("amber-700"), palette("amber-100"), 4.5273],
      [palette("emerald-700"), palette("emerald-50"), 5.1582],
      [palette("emerald-700"), palette("emerald-100"), 4.7907],
      [palette("red-700"), palette("red-50"), 5.9842],
      [palette("red-700"), palette("red-100"), 5.3552],
    ] as ReadonlyArray<readonly [Oklch, Oklch, number]>) {
      expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
      expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
        MINIMUM_CONTRAST_RATIO,
      );
    }
  });

  it("creates no brand-text alpha pair, so no APRAS-90 site", () => {
    // APRAS-90 owns brand text carrying an opacity modifier over a brand tint.
    // The one opacity modifier this task carries over (`/70`) and the two it
    // creates (`/90`) are all background utilities, so the only composited
    // reading this file needs is the graphical Award glyph above.
    const scrim = compositeOver(token("foreground"), CARD, 0.7);

    expect(ratio(WHITE, scrim)).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
  });
});
