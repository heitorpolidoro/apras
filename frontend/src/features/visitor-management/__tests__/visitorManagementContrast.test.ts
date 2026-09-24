/// <reference types="node" />
// @vitest-environment node
//
// Every foreground/background pair APRAS-80 changes, measured.
//
// The measurement is not reimplemented here: `contrastRatio` and `parseOklch`
// come from `src/lib/contrast.ts`, the repository's single contrast
// implementation (OKLab -> linear sRGB, chroma-bisection gamut map, WCAG 2.1).
// Neither side is a literal either — token values are read out of
// `src/index.css` and palette values out of Tailwind 4's own
// `node_modules/tailwindcss/theme.css`, so a colour that moves in either file
// moves here. (The Tailwind v3 hexes are off by up to 0.07 and would not
// reproduce APRAS-78's published figures; that is the check that this is the
// same measurement, not a second one.)
//
// The node environment is what makes `import.meta.url` a `file:` URL, exactly
// as `src/__tests__/themeTokenMigration.test.ts` needs it to be.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  compositeOver,
  contrastRatio,
  hexToOklch,
  parseOklch,
  MINIMUM_CONTRAST_RATIO,
  type Oklch,
} from "../../../lib/contrast";

/** WCAG 2.1 1.4.11, the floor a graphical object must clear. */
const GRAPHICAL_CONTRAST_RATIO = 3;
/** Every ratio below is published to four decimals; assert to ±0.001. */
const DECIMALS = 3;
/** The alpha APRAS-90 deleted from the counter label, as `/80` means it. */
const COMPOSITED_ALPHA = 0.8;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(HERE, "..", "..", "..", "..");

const STYLESHEET = readFileSync(
  path.join(FRONTEND_ROOT, "src", "index.css"),
  "utf8",
);
const TAILWIND_THEME = readFileSync(
  path.join(FRONTEND_ROOT, "node_modules", "tailwindcss", "theme.css"),
  "utf8",
);

/**
 * The `:root` block of `index.css`, and only it.
 *
 * Never `.dark`: the stylesheet declares `--primary` twice, `0.62` in `:root`
 * and `0.65` in `.dark`, and a last-wins reader would silently measure the
 * dark scheme. The `.dark` block is not applied by this product and is not
 * this task's to validate. Sliced by the `:root {` opener rather than by the
 * first `.dark` seen, because `@custom-variant dark (&:is(.dark *))` on line 3
 * carries that text before `:root` ever opens.
 */
const ROOT_BLOCK = (() => {
  const start = STYLESHEET.indexOf(":root {");
  return STYLESHEET.slice(start, STYLESHEET.indexOf("}", start));
})();

/** One `--<name>` custom property of `index.css`'s `:root`. */
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

/**
 * One `--color-<name>` of Tailwind's palette.
 *
 * Two authoring formats are normalised, neither of which is a second
 * implementation of `contrast.ts`'s arithmetic: Tailwind writes lightness as a
 * **percentage** (`oklch(96.2% 0.018 272.314)`), which `parseOklch`'s grammar
 * rejects by design, and `--color-white` as a three-digit hex.
 */
const palette = (name: string): Oklch => {
  const declared = new RegExp(String.raw`--color-${name}:\s*([^;]+);`).exec(
    TAILWIND_THEME,
  );
  const raw = (declared?.[1] ?? "").trim();
  if (raw.startsWith("#")) {
    const digits =
      raw.length === 4
        ? `#${raw[1]}${raw[1]}${raw[2]}${raw[2]}${raw[3]}${raw[3]}`
        : raw;
    const colour = hexToOklch(digits);
    if (colour === null) {
      throw new Error(`tailwindcss/theme.css declares no readable ${name}`);
    }
    return colour;
  }
  const percent =
    /^oklch\(\s*([\d.]+)%\s+([\d.]+)\s+([\d.]+)\s*\)$/.exec(raw) ?? undefined;
  if (percent === undefined) {
    throw new Error(`tailwindcss/theme.css declares no readable ${name}`);
  }
  return {
    l: Number(percent[1]) / 100,
    c: Number(percent[2]),
    h: Number(percent[3]),
  };
};

/** One pair the migration moves: what it measured, and what it measures now. */
interface MovedPair {
  /** The call sites, named as the spec names them. */
  site: string;
  /** `class` -> `token`, verbatim. */
  move: string;
  before: () => number;
  after: () => number;
  publishedBefore: number;
  publishedAfter: number;
  /** 4.5 for characters (§1k), 3 for a graphical object (WCAG 1.4.11). */
  floor: number;
}

/**
 * The pairs that clear their floor after the migration.
 *
 * §1k routes brand **text** to `--primary-text` and brand **graphical
 * objects** to `--primary`, which is why the same source class appears in both
 * halves of this table against two different floors.
 */
const CLEARED: readonly MovedPair[] = [
  {
    site: "body headings",
    move: "text-slate-900 -> text-foreground on --card",
    before: () => contrastRatio(palette("slate-900"), token("card")),
    after: () => contrastRatio(token("foreground"), token("card")),
    publishedBefore: 17.8448,
    publishedAfter: 19.8801,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "secondary text on a card",
    move: "text-slate-500 -> text-muted-foreground on --card",
    before: () => contrastRatio(palette("slate-500"), token("card")),
    after: () => contrastRatio(token("muted-foreground"), token("card")),
    publishedBefore: 4.767,
    publishedAfter: 5.2249,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "loading text on the page shell",
    move: "text-slate-500 -> text-muted-foreground on --background",
    before: () => contrastRatio(palette("slate-500"), token("background")),
    after: () => contrastRatio(token("muted-foreground"), token("background")),
    publishedBefore: 4.6322,
    publishedAfter: 5.0771,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "VisitorTable:53 table head",
    move: "text-slate-500 on bg-slate-50 -> text-muted-foreground on bg-muted",
    before: () => contrastRatio(palette("slate-500"), palette("slate-50")),
    after: () => contrastRatio(token("muted-foreground"), token("muted")),
    publishedBefore: 4.554,
    publishedAfter: 4.6684,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "AuthorizationFormModal:253,279 unselected chips",
    move: "text-slate-600 on bg-slate-100 -> text-muted-foreground on bg-muted",
    before: () => contrastRatio(palette("slate-600"), palette("slate-100")),
    after: () => contrastRatio(token("muted-foreground"), token("muted")),
    publishedBefore: 6.8989,
    publishedAfter: 4.6684,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "AuthorizationQrModal:73, VisitorAuthPage:145 free-standing red",
    move: "text-red-600 -> text-destructive on --card",
    before: () => contrastRatio(palette("red-600"), token("card")),
    after: () => contrastRatio(token("destructive"), token("card")),
    publishedBefore: 4.8619,
    publishedAfter: 4.8073,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "GatekeeperDashboard:225,350, GatekeeperEntryModal:131 buttons",
    move: "text-white on bg-emerald-600 -> text-primary-foreground on bg-primary",
    before: () => contrastRatio(palette("white"), palette("emerald-600")),
    after: () => contrastRatio(token("primary-foreground"), token("primary")),
    publishedBefore: 3.7194,
    // Repairs an AA failure: the check-in and pickup buttons fail today.
    publishedAfter: 5.7588,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "GatekeeperDashboard:293 package button",
    move: "text-white on bg-indigo-600 -> text-primary-foreground on bg-primary",
    before: () => contrastRatio(palette("white"), palette("indigo-600")),
    after: () => contrastRatio(token("primary-foreground"), token("primary")),
    publishedBefore: 6.4414,
    publishedAfter: 5.7588,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "AuthorizationFormModal:146 new-visitor link (§1k, mixed element)",
    move: "text-indigo-600 -> text-primary-text on --card",
    before: () => contrastRatio(palette("indigo-600"), token("card")),
    after: () => contrastRatio(token("primary-text"), token("card")),
    publishedBefore: 6.4414,
    publishedAfter: 5.2096,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "AuthorizationFormModal:217,228 selected auth-type chips (§1k)",
    move: "text-indigo-700 on bg-indigo-50 -> text-primary-text on bg-accent",
    before: () => contrastRatio(palette("indigo-700"), palette("indigo-50")),
    after: () => contrastRatio(token("primary-text"), token("accent")),
    publishedBefore: 7.2164,
    publishedAfter: 4.6547,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "GatekeeperDashboard:150 counter label (APRAS-90)",
    move: "text-primary-text/80 -> text-foreground on bg-accent",
    // The pair APRAS-80 could not repair: §1i forbade a migration child from
    // deleting the `/80`, so it carried the modifier over and declared the
    // sub-AA composite. APRAS-90 owns the repair, and the operator chose a
    // neutral caption token over keeping the label branded at 4.6547 — 0.15
    // above the floor on a token `build_theme` re-derives per tenant with no
    // cushion. The counter *number* above stays branded.
    before: () =>
      contrastRatio(
        compositeOver(token("primary-text"), token("accent"), COMPOSITED_ALPHA),
        token("accent"),
      ),
    after: () => contrastRatio(token("foreground"), token("accent")),
    publishedBefore: 3.2883,
    publishedAfter: 17.7626,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "GatekeeperDashboard:147 active-visitor counter (§1k)",
    move: "text-indigo-700 on bg-indigo-50 -> text-primary-text on bg-accent",
    before: () => contrastRatio(palette("indigo-700"), palette("indigo-50")),
    // The tightest full-opacity pair this task produces: it clears the normal
    // -text floor by 0.15, and `--primary-text` is re-derived per tenant with
    // no cushion, so a tenant brand can land it at exactly 4.50. That is
    // APRAS-88's property, not this task's defect.
    after: () => contrastRatio(token("primary-text"), token("accent")),
    publishedBefore: 7.2164,
    publishedAfter: 4.6547,
    floor: MINIMUM_CONTRAST_RATIO,
  },
  {
    site: "AuthorizationFormModal:117, AuthorizationQrModal:61, QrScannerModal:61, GatekeeperDashboard:170,240,266,305 icons (§1k)",
    move: "text-indigo-600 -> text-primary on --card",
    before: () => contrastRatio(palette("indigo-600"), token("card")),
    after: () => contrastRatio(token("primary"), token("card")),
    publishedBefore: 6.4414,
    publishedAfter: 3.4054,
    floor: GRAPHICAL_CONTRAST_RATIO,
  },
  {
    site: "GatekeeperDashboard:129, VisitorAuthPage:58 page-shell icons (§1k)",
    move: "text-indigo-600 -> text-primary on --background",
    before: () => contrastRatio(palette("indigo-600"), token("background")),
    after: () => contrastRatio(token("primary"), token("background")),
    publishedBefore: 6.2592,
    publishedAfter: 3.3091,
    floor: GRAPHICAL_CONTRAST_RATIO,
  },
  {
    site: "GatekeeperDashboard:145 Users glyph in the counter card (§1k)",
    move: "text-indigo-600 on bg-indigo-50 -> text-primary on bg-accent",
    before: () => contrastRatio(palette("indigo-600"), palette("indigo-50")),
    // Clears 1.4.11 by 0.043, and for a pale tenant brand it does not clear it
    // at all. APRAS-68 behaviour predating APRAS-77, with its own named
    // follow-up; this task changes the class and did not introduce the number.
    after: () => contrastRatio(token("primary"), token("accent")),
    publishedBefore: 5.7621,
    publishedAfter: 3.0427,
    floor: GRAPHICAL_CONTRAST_RATIO,
  },
];

/**
 * The pairs below AA **by decision**, declared rather than hidden.
 *
 * All three are classes APRAS-80 left exactly as it found them, measured so
 * that a later reader does not attribute them to it. The fourth entry — the
 * counter label's `/80` composite, the one failure the migration worsened —
 * is gone from this list because APRAS-90 repaired it; it now sits in
 * `CLEARED`, carrying the same 3.2883 as its `publishedBefore`.
 */
const DECLARED_SUB_AA: readonly {
  site: string;
  note: string;
  measure: () => number;
  published: number;
  publishedBefore: number;
}[] = [
  {
    site: "AccessLogTimeline:59 timeline dot glyph, left branch",
    note: "text-slate-500 on bg-slate-100, kept whole under the triple rule. Below AA today and unchanged by this task.",
    measure: () => contrastRatio(palette("slate-500"), palette("slate-100")),
    publishedBefore: 4.3481,
    published: 4.3481,
  },
  {
    site: "AccessLogTimeline:58 timeline dot glyph, on-site branch",
    note: "text-emerald-600 on bg-emerald-100, kept whole under the triple rule. Below AA today and unchanged by this task.",
    measure: () => contrastRatio(palette("emerald-600"), palette("emerald-100")),
    publishedBefore: 3.2766,
    published: 3.2766,
  },
  {
    site: "AccessLogTimeline:98 check-out button label",
    note: "text-white on bg-amber-600, a palette colour with no row. Below AA today and unchanged by this task.",
    measure: () => contrastRatio(palette("white"), palette("amber-600")),
    publishedBefore: 3.1884,
    published: 3.1884,
  },
];

/** Kept pairs that do pass, measured so the ledger's `why` can state them. */
const KEPT_PASSING: readonly [string, () => number, number][] = [
  [
    "text-emerald-700 on bg-emerald-50",
    () => contrastRatio(palette("emerald-700"), palette("emerald-50")),
    5.1582,
  ],
  [
    "text-emerald-800 on bg-emerald-50",
    () => contrastRatio(palette("emerald-800"), palette("emerald-50")),
    7.2679,
  ],
  [
    "text-red-700 on bg-red-50",
    () => contrastRatio(palette("red-700"), palette("red-50")),
    5.9842,
  ],
  [
    "text-red-800 on bg-red-50",
    () => contrastRatio(palette("red-800"), palette("red-50")),
    7.6659,
  ],
  [
    "text-amber-700 on bg-amber-50",
    () => contrastRatio(palette("amber-700"), palette("amber-50")),
    4.8611,
  ],
  [
    "text-slate-600 on bg-slate-100",
    () => contrastRatio(palette("slate-600"), palette("slate-100")),
    6.8989,
  ],
];

describe("the measurement itself", () => {
  it("reproduces APRAS-78's published figures, which is what makes it the same measurement", () => {
    // If Tailwind's palette were read as v3 hex instead of v4 OKLCH, or the
    // `.dark` block were read instead of `:root`, these three would miss.
    expect(contrastRatio(palette("red-700"), palette("red-50"))).toBeCloseTo(
      5.9842,
      DECIMALS,
    );
    expect(
      contrastRatio(token("muted-foreground"), token("muted")),
    ).toBeCloseTo(4.6684, DECIMALS);
    expect(
      contrastRatio(token("primary-foreground"), token("primary")),
    ).toBeCloseTo(5.7588, DECIMALS);
  });

  it("reads --primary from :root and never from .dark", () => {
    expect(token("primary").l).toBeCloseTo(0.62, 2);
    expect(STYLESHEET).toContain("--primary: oklch(0.65 0.15 160)");
  });
});

describe("the pairs APRAS-80 moves", () => {
  it.each(CLEARED.map((pair) => [pair.move, pair] as const))(
    "%s measures what the spec publishes",
    (_move, pair) => {
      expect(pair.before()).toBeCloseTo(pair.publishedBefore, DECIMALS);
      expect(pair.after()).toBeCloseTo(pair.publishedAfter, DECIMALS);
    },
  );

  it.each(CLEARED.map((pair) => [`${pair.site} — ${pair.move}`, pair] as const))(
    "%s clears its floor after the migration",
    (_site, pair) => {
      expect(pair.after()).toBeGreaterThanOrEqual(pair.floor);
    },
  );

  it("routes brand text to --primary-text and brand glyphs to --primary", () => {
    // The §1k split, stated as the two floors it exists to satisfy:
    // `--primary` fails AA as normal text on every light surface, which is
    // why characters may not take it; `--primary-text` clears 4.5 on both
    // surfaces this directory puts brand text on.
    expect(contrastRatio(token("primary"), token("card"))).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(contrastRatio(token("primary"), token("accent"))).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(contrastRatio(token("primary"), token("accent"))).toBeGreaterThanOrEqual(
      GRAPHICAL_CONTRAST_RATIO,
    );
    expect(contrastRatio(token("primary-text"), token("card"))).toBeCloseTo(
      5.2096,
      DECIMALS,
    );
    expect(contrastRatio(token("primary-text"), token("accent"))).toBeCloseTo(
      4.6547,
      DECIMALS,
    );
  });

  it("leaves nothing it moves undeclared", () => {
    // Every moved pair is either in CLEARED, where it clears its floor, or in
    // DECLARED_SUB_AA, where it carries its measured before and after. There
    // is no third list and no silent case.
    for (const pair of CLEARED) {
      expect(pair.after()).toBeGreaterThanOrEqual(pair.floor);
    }
    expect(DECLARED_SUB_AA).toHaveLength(3);
  });
});

describe("the pairs below AA by decision", () => {
  it.each(DECLARED_SUB_AA.map((pair) => [pair.site, pair] as const))(
    "%s is declared, not hidden",
    (_site, pair) => {
      expect(pair.measure()).toBeCloseTo(pair.published, DECIMALS);
      expect(pair.published).toBeLessThan(MINIMUM_CONTRAST_RATIO);
      expect(pair.note.length).toBeGreaterThan(0);
    },
  );

  it("records all three as untouched, the worsened composite having been repaired", () => {
    // APRAS-80's own regression — `text-primary-text/80` at 3.2883, down from
    // 4.0551 — was the one entry here whose `published` moved. APRAS-90
    // deleted it from the markup, so every pair still declared is one no task
    // in this chain has changed.
    expect(DECLARED_SUB_AA).toHaveLength(3);
    for (const pair of DECLARED_SUB_AA) {
      expect(pair.published).toBe(pair.publishedBefore);
    }
  });
});

describe("the kept pairs that pass", () => {
  it.each(KEPT_PASSING)("%s", (_name, measure, published) => {
    expect(measure()).toBeCloseTo(published, DECIMALS);
    expect(measure()).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
  });
});
