/// <reference types="node" />
// @vitest-environment node
//
// APRAS-85 — the contrast half of the six remaining feature directories'
// token migration, and the closer of the APRAS-77 split.
//
// Every foreground/background pair this task changes is re-measured here by
// **importing** `contrastRatio`, `parseOklch`, `hexToOklch` and
// `MINIMUM_CONTRAST_RATIO` from `src/lib/contrast.ts`. The arithmetic is never
// reimplemented — a verbatim copy of `compositeOver` was rejected in
// APRAS-87's review — and no colour literal is written down: token values are
// read from `src/index.css`'s `:root` block, never `.dark`, which is
// unapplied, and palette values from Tailwind 4's own
// `node_modules/tailwindcss/theme.css`.
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

const CARD = token("card");
const MUTED = token("muted");
const PRIMARY = token("primary");
const PRIMARY_FOREGROUND = token("primary-foreground");
const DESTRUCTIVE = token("destructive");
const WHITE = palette("white");


// --- the palette values the six directories are migrating away from -------

const GRAY_400 = palette("gray-400");
const GRAY_500 = palette("gray-500");
const GRAY_600 = palette("gray-600");
const GRAY_700 = palette("gray-700");
const GRAY_900 = palette("gray-900");
const GRAY_50 = palette("gray-50");
const GRAY_100 = palette("gray-100");
const INDIGO_600 = palette("indigo-600");
const EMERALD_700 = palette("emerald-700");
const RED_700 = palette("red-700");
const SLATE_500 = palette("slate-500");
const SLATE_100 = palette("slate-100");
const AMBER_600 = palette("amber-600");
const EMERALD_600 = palette("emerald-600");

describe("the measurement is the repository's own", () => {
  // APRAS-78's, APRAS-80's, APRAS-83's and APRAS-88's published figures. If
  // these drift, `src/lib/contrast.ts` changed underneath this task and every
  // other number below is suspect.
  it.each([
    ["--primary-foreground on --primary", PRIMARY_FOREGROUND, PRIMARY, 5.7588],
    ["--muted-foreground on --card", token("muted-foreground"), CARD, 5.2249],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--primary-text on --card", token("primary-text"), CARD, 5.2096],
    ["--foreground on --card", token("foreground"), CARD, 19.8801],
    ["--destructive on --card", DESTRUCTIVE, CARD, 4.8073],
    ["text-gray-700 on --muted", GRAY_700, MUTED, 9.2081],
  ])("reproduces %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
  });
});

describe("the tokens this task paints with", () => {
  // The six token pairs this child produces, each above AA as text.
  it.each([
    ["--primary-text on --card", token("primary-text"), CARD, 5.2096],
    ["--muted-foreground on --card", token("muted-foreground"), CARD, 5.2249],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--foreground on --card", token("foreground"), CARD, 19.8801],
    ["--foreground on --muted", token("foreground"), MUTED, 17.7626],
    ["--primary-foreground on --primary", PRIMARY_FOREGROUND, PRIMARY, 5.7588],
    ["--destructive on --card", DESTRUCTIVE, CARD, 4.8073],
  ])("holds AA as text: %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
    expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it("leaves --muted-foreground on --muted as the tightest pair", () => {
    // 4.6684, and the tightest pair the task *creates* is `--destructive` on
    // `--card` at 4.8073. No full-opacity text pair this task produces falls
    // below AA, and this child produces no `text-primary-text/N` and no
    // `text-primary/N`, so it names no APRAS-90 site.
    const produced = [
      ratio(token("muted-foreground"), MUTED),
      ratio(DESTRUCTIVE, CARD),
      ratio(token("primary-text"), CARD),
      ratio(token("muted-foreground"), CARD),
      ratio(PRIMARY_FOREGROUND, PRIMARY),
      ratio(token("foreground"), MUTED),
      ratio(token("foreground"), CARD),
    ];

    expect([...produced].sort((left, right) => left - right)).toEqual(produced);
    expect(produced[0]).toBe(4.6684);
  });
});

describe("every pair this task moves", () => {
  /**
   * `[name, before, after]` for each of the nine changed pairs, measured
   * against its declared background — the palette value before, the token
   * after.
   */
  const MOVED: ReadonlyArray<readonly [string, number, number]> = [
    [
      "headings text-gray-900 -> text-foreground on the card",
      ratio(GRAY_900, WHITE),
      ratio(token("foreground"), CARD),
    ],
    [
      "text-gray-900 on bg-gray-50 -> text-foreground on bg-muted",
      ratio(GRAY_900, GRAY_50),
      ratio(token("foreground"), MUTED),
    ],
    [
      "secondary text-gray-500 x64 -> text-muted-foreground",
      ratio(GRAY_500, WHITE),
      ratio(token("muted-foreground"), CARD),
    ],
    [
      "text-gray-600 x2 -> text-muted-foreground",
      ratio(GRAY_600, WHITE),
      ratio(token("muted-foreground"), CARD),
    ],
    [
      "text-gray-600 on bg-gray-100 -> text-muted-foreground on bg-muted",
      ratio(GRAY_600, GRAY_100),
      ratio(token("muted-foreground"), MUTED),
    ],
    [
      "text-gray-400 x2 -> text-muted-foreground",
      ratio(GRAY_400, WHITE),
      ratio(token("muted-foreground"), CARD),
    ],
    [
      "links text-indigo-600 x5 -> text-primary-text",
      ratio(INDIGO_600, WHITE),
      ratio(token("primary-text"), CARD),
    ],
    [
      "success buttons text-white on bg-emerald-700 -> on --primary",
      ratio(WHITE, EMERALD_700),
      ratio(PRIMARY_FOREGROUND, PRIMARY),
    ],
    [
      "error message text-red-700 -> text-destructive",
      ratio(RED_700, WHITE),
      ratio(DESTRUCTIVE, CARD),
    ],
  ];

  it("records the nine before/after ratios the task publishes", () => {
    expect(MOVED.map(([name, before, after]) => [name, before, after])).toEqual([
      [
        "headings text-gray-900 -> text-foreground on the card",
        17.7467,
        19.8801,
      ],
      [
        "text-gray-900 on bg-gray-50 -> text-foreground on bg-muted",
        17.001,
        17.7626,
      ],
      ["secondary text-gray-500 x64 -> text-muted-foreground", 4.8357, 5.2249],
      ["text-gray-600 x2 -> text-muted-foreground", 7.5608, 5.2249],
      [
        "text-gray-600 on bg-gray-100 -> text-muted-foreground on bg-muted",
        6.8711,
        4.6684,
      ],
      ["text-gray-400 x2 -> text-muted-foreground", 2.6023, 5.2249],
      ["links text-indigo-600 x5 -> text-primary-text", 6.4414, 5.2096],
      [
        "success buttons text-white on bg-emerald-700 -> on --primary",
        5.4381,
        5.7588,
      ],
      ["error message text-red-700 -> text-destructive", 6.5373, 4.8073],
    ]);
  });

  it("moves no pair from passing AA to failing it", () => {
    for (const [name, before, after] of MOVED) {
      if (before >= MINIMUM_CONTRAST_RATIO) {
        expect(after, name).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
      }
    }
  });

  it("repairs the one pre-existing AA failure it touches", () => {
    // `text-gray-400` at two sites — `AttachmentUploader.tsx:190` and
    // `InfractionStageTimeline.tsx:39` — was below AA before this task and is
    // above it after. It is the only pair here that crosses the floor.
    const repaired = MOVED.filter(
      ([, before]) => before < MINIMUM_CONTRAST_RATIO,
    );

    expect(repaired.map(([name]) => name)).toEqual([
      "text-gray-400 x2 -> text-muted-foreground",
    ]);
    expect(repaired[0][1]).toBe(2.6023);
    expect(repaired[0][2]).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
  });

  it("keeps the one kept foreground whose surface moves above AA", () => {
    // `text-gray-700` on a chip whose `bg-gray-100` becomes `bg-muted`, at
    // `InfractionsPage.tsx:269` and `MyInfractionsPage.tsx:57`. Every other
    // kept class sits on a surface this task does not touch.
    expect(ratio(GRAY_700, GRAY_100)).toBe(9.3658);
    expect(ratio(GRAY_700, MUTED)).toBe(9.2081);
    expect(ratio(GRAY_700, MUTED)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });
});

describe("the sub-AA pairs this task leaves alone", () => {
  /** Declared, kept verbatim, and failing **before** this task as well as
   *  after: all three sit inside a status set this child freezes. */
  const DECLARED: ReadonlyArray<readonly [string, number, number]> = [
    // `SpaceBookingPage.tsx:22,24`, status set 13's neutral branches.
    ["text-slate-500 on bg-slate-100", ratio(SLATE_500, SLATE_100), 4.3481],
    // `Navbar.tsx:153` and `ReservableSpacesPage.tsx:243`.
    ["text-amber-600 on white", ratio(AMBER_600, WHITE), 3.1884],
    // `AuditTimeline.tsx:111`, the read-only audit diff's "new value".
    ["text-emerald-600 on white", ratio(EMERALD_600, WHITE), 3.7194],
  ];

  it("measures each at the ratio it had before this task", () => {
    for (const [name, measured, expected] of DECLARED) {
      expect(measured, name).toBeCloseTo(expected, 3);
      expect(measured, name).toBeLessThan(MINIMUM_CONTRAST_RATIO);
    }
  });

  it("introduces no other sub-AA pair", () => {
    // The declared three are the whole list: every pair the task *produces*
    // is measured above, and all seven clear AA.
    const produced = [
      ratio(token("primary-text"), CARD),
      ratio(token("muted-foreground"), CARD),
      ratio(token("muted-foreground"), MUTED),
      ratio(token("foreground"), CARD),
      ratio(token("foreground"), MUTED),
      ratio(PRIMARY_FOREGROUND, PRIMARY),
      ratio(DESTRUCTIVE, CARD),
    ];

    expect(
      produced.filter((measured) => measured < MINIMUM_CONTRAST_RATIO),
    ).toEqual([]);
    expect(DECLARED).toHaveLength(3);
  });
});
