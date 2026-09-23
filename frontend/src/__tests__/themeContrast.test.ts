/// <reference types="node" />
// @vitest-environment node
//
// This suite reads a file and does arithmetic; it renders nothing. The node
// environment is what makes `import.meta.url` a `file:` URL — under the
// project-wide jsdom default it is the dev server's `http:` URL and the
// stylesheet cannot be located from it.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * The shipped theme's text/background pairs, measured against WCAG 2.1 AA
 * (APRAS-76).
 *
 * Three properties make this a guard rather than a restatement of the
 * palette:
 *
 * 1. **The pairs are derived from `src/index.css`, never listed here.** A
 *    token added later is enumerated by its own name, and a `-foreground` or
 *    `-fg` token whose partner is missing fails the suite naming the token,
 *    so nothing can be added to the file and dodge measurement.
 * 2. **The measurement is this file's own.** It deliberately does not import
 *    `src/lib/contrast.ts` (APRAS-68): that module is production code this
 *    stylesheet is not otherwise coupled to, and an independent oracle is
 *    what makes a green run evidence. The two may be unified later, on
 *    purpose and with both halves pinned.
 * 3. **The measurement is itself pinned**, in `describe("the measurement")`
 *    below, because its two load-bearing steps each have a silent failure
 *    mode:
 *    - luminance runs on the **linear** channels the converter already
 *      returns; applying the sRGB transfer a second time *inflates*
 *      light-on-light ratios (the pair repaired here reads 10.9585 instead of
 *      4.2913 under that bug) and would certify an illegible palette;
 *    - an out-of-gamut `oklch()` is chroma-reduced at constant lightness and
 *      hue, as CSS Color 4 §13 requires a browser to do. `--primary`
 *      `oklch(0.62 0.15 160)` is out of gamut and is painted as
 *      `oklch(0.62 0.14 160)`; measuring the unmapped value measures a colour
 *      no browser shows.
 */

/** One colour in OKLCH: `l` 0–1, `c` >= 0, `h` in degrees. */
interface Oklch {
  l: number;
  c: number;
  h: number;
}

/** Linear-light sRGB, possibly outside `[0, 1]` before gamut mapping. */
type LinearRgb = [number, number, number];

/** WCAG 2.1 AA for normal text. */
const MINIMUM_RATIO = 4.5;
/** The precision `index.css` is authored and emitted at. */
const EMITTED_SCALE = 100;
/** How far outside `[0, 1]` a linear channel may sit and still count as in
 *  gamut — floating-point slack, not a colour allowance. */
const GAMUT_TOLERANCE = 1e-4;
/** Chroma is reduced on the grid the emitted value lives on. */
const CHROMA_STEP = 0.01;
const LUMINANCE_OFFSET = 0.05;
const RED_WEIGHT = 0.2126;
const GREEN_WEIGHT = 0.7152;
const BLUE_WEIGHT = 0.0722;
const DEGREES_TO_RADIANS = Math.PI / 180;
const RATIO_DECIMALS = 4;

/** Round to the two decimal places the stylesheet emits. */
const toEmitted = (value: number): number =>
  Math.round(value * EMITTED_SCALE) / EMITTED_SCALE;

/**
 * OKLCH to **linear-light** sRGB (Ottosson matrices).
 *
 * It rounds nothing and maps no gamut, so the oracle can call it on
 * arbitrary-precision input; rounding and gamut mapping belong to
 * {@link gamutMap} alone.
 */
const oklchToLinearSrgb = ({ l, c, h }: Oklch): LinearRgb => {
  const radians = h * DEGREES_TO_RADIANS;
  const axisA = c * Math.cos(radians);
  const axisB = c * Math.sin(radians);
  const long = (l + 0.3963377774 * axisA + 0.2158037573 * axisB) ** 3;
  const medium = (l - 0.1055613458 * axisA - 0.0638541728 * axisB) ** 3;
  const short = (l - 0.0894841775 * axisA - 1.291485548 * axisB) ** 3;
  return [
    4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
    -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
    -0.0041960863 * long - 0.7034186147 * medium + 1.707614701 * short,
  ];
};

/** Whether all three linear channels sit inside `[0, 1] ± 1e-4`. */
const isInGamut = (colour: Oklch): boolean =>
  oklchToLinearSrgb(colour).every(
    (channel) => channel >= -GAMUT_TOLERANCE && channel <= 1 + GAMUT_TOLERANCE,
  );

/**
 * The colour a browser actually paints: the emitted 2dp value, with chroma
 * reduced on the 0.01 grid at constant lightness and hue until sRGB holds it.
 */
const gamutMap = (colour: Oklch): Oklch => {
  const mapped: Oklch = {
    l: toEmitted(colour.l),
    c: toEmitted(colour.c),
    h: toEmitted(colour.h),
  };
  while (mapped.c > 0 && !isInGamut(mapped)) {
    mapped.c = toEmitted(mapped.c - CHROMA_STEP);
  }
  return mapped;
};

/** WCAG 2.1 relative luminance, computed on the **linear** channels. */
const relativeLuminance = (colour: Oklch): number => {
  const [red, green, blue] = oklchToLinearSrgb(gamutMap(colour)).map((channel) =>
    Math.min(1, Math.max(0, channel)),
  );
  return RED_WEIGHT * red + GREEN_WEIGHT * green + BLUE_WEIGHT * blue;
};

/** The WCAG 2.1 ratio between two colours as the browser paints them. */
const contrastRatio = (first: Oklch, second: Oklch): number => {
  const [lower, higher] = [
    relativeLuminance(first),
    relativeLuminance(second),
  ].sort((a, b) => a - b);
  return (higher + LUMINANCE_OFFSET) / (lower + LUMINANCE_OFFSET);
};

const stylesheetPath = fileURLToPath(new URL("../index.css", import.meta.url));
const stylesheet = readFileSync(stylesheetPath, "utf8");

const DECLARATION =
  /--([a-z0-9-]+)\s*:\s*oklch\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)/g;

type Tokens = Record<string, Oklch>;

/**
 * Every `--name: oklch(L C H)` declared inside one selector's block.
 *
 * A selector that is not in the file throws rather than returning nothing: a
 * renamed or deleted block must fail the suite loudly, not quietly reduce it
 * to measuring zero pairs.
 */
const tokensOf = (selector: string): Tokens => {
  const block = new RegExp(`${selector}\\s*\\{([^}]*)\\}`).exec(stylesheet);
  if (block === null) {
    throw new Error(`no \`${selector}\` block in src/index.css`);
  }
  const tokens: Tokens = {};
  for (const [, name, l, c, h] of block[1].matchAll(DECLARATION)) {
    tokens[name] = { l: Number(l), c: Number(c), h: Number(h) };
  }
  return tokens;
};

const light = tokensOf(":root");
const darkOnly = tokensOf("\\.dark");
// The dark scheme is the cascade, not the `.dark` block alone: the status and
// priority tokens are declared only in `:root` and are rendered in both.
const dark = { ...light, ...darkOnly };
const schemes: ReadonlyArray<readonly [string, Tokens]> = [
  ["light", light],
  ["dark", dark],
];

/** The lowest number of pairs a working parser can derive; a parser that
 *  silently matched nothing would otherwise pass every assertion. It went
 *  19 → 23 with APRAS-88's four `--primary-text` pairs. */
const MINIMUM_PAIRS = 23;

const FOREGROUND_SUFFIX = "-foreground";
const FG_SUFFIX = "-fg";
const BG_SUFFIX = "-bg";

/**
 * The background each text token is rendered on, by naming convention:
 * `--foreground` on `--background`, every `--X-foreground` on `--X`, every
 * `--Y-fg` on `--Y-bg`. Returns `null` for a token that carries no text.
 */
const backgroundOf = (name: string): string | null => {
  if (name === "foreground") {
    return "background";
  }
  if (name.endsWith(FOREGROUND_SUFFIX)) {
    return name.slice(0, -FOREGROUND_SUFFIX.length);
  }
  if (name.endsWith(FG_SUFFIX)) {
    return `${name.slice(0, -FG_SUFFIX.length)}${BG_SUFFIX}`;
  }
  return null;
};

/**
 * The surfaces `backgroundOf` cannot name, listed by hand.
 *
 * Two of them are the further surfaces muted text is rendered on. The other
 * four are APRAS-88's `--primary-text`: it is a foreground whose name ends in
 * neither `-foreground` nor `-fg`, precisely because it is not the foreground
 * *of* one surface — it is brand text, and §1k of the mapping table puts it on
 * all four of the scheme's text surfaces. `--border` is not among them: it
 * carries no text.
 */
const EXTRA_PAIRS: ReadonlyArray<readonly [string, string]> = [
  ["muted-foreground", "background"],
  ["muted-foreground", "card"],
  ["primary-text", "card"],
  ["primary-text", "background"],
  ["primary-text", "muted"],
  ["primary-text", "accent"],
];

const pairsOf = (tokens: Tokens): Array<readonly [string, string]> => [
  ...Object.keys(tokens)
    .map((name) => [name, backgroundOf(name)] as const)
    .filter((pair): pair is readonly [string, string] => pair[1] !== null),
  ...EXTRA_PAIRS,
];

describe("src/index.css", () => {
  it("declares both schemes", () => {
    expect(Object.keys(light).length).toBeGreaterThanOrEqual(MINIMUM_PAIRS);
    expect(Object.keys(darkOnly).length).toBeGreaterThan(0);
    expect(light.background).toBeDefined();
    expect(dark.background).toBeDefined();
    // The cascade, not the `.dark` block alone.
    expect(dark.background).not.toEqual(light.background);
    expect(dark["status-pending-fg"]).toEqual(light["status-pending-fg"]);
  });

  it.each(schemes)("derives every %s pair from the file", (_scheme, tokens) => {
    const pairs = pairsOf(tokens);
    expect(pairs.length).toBeGreaterThanOrEqual(MINIMUM_PAIRS);
  });

  it.each(schemes)(
    "declares the background of every %s text token",
    (scheme, tokens) => {
      for (const [foreground, background] of pairsOf(tokens)) {
        expect(
          tokens[background],
          `${scheme}: --${foreground} has no --${background} to sit on`,
        ).toBeDefined();
      }
    },
  );

  it.each(schemes)("meets WCAG AA on every %s pair", (scheme, tokens) => {
    for (const [foreground, background] of pairsOf(tokens)) {
      const ratio = contrastRatio(tokens[foreground], tokens[background]);
      expect(
        ratio,
        `${scheme}: --${foreground} on --${background} is ${ratio.toFixed(
          RATIO_DECIMALS,
        )}:1, below ${MINIMUM_RATIO}:1`,
      ).toBeGreaterThanOrEqual(MINIMUM_RATIO);
    }
  });
});

describe("the measurement", () => {
  const black: Oklch = { l: 0, c: 0, h: 0 };
  const white: Oklch = { l: 1, c: 0, h: 0 };

  it("rates black on white at exactly 21", () => {
    expect(contrastRatio(black, white)).toBeCloseTo(21, 9);
  });

  it("converts unrounded, unmapped OKLCH to linear sRGB", () => {
    // sRGB red. Rounding this input to 2dp first would give
    // (1.0149, -0.0017, -0.0009) — an order of magnitude outside the
    // tolerance, and itself out of gamut — which is why step 1 rounds
    // nothing. A second sRGB transfer, or a wrong matrix, misses it too.
    const linear = oklchToLinearSrgb({ l: 0.628, c: 0.2577, h: 29.23 });
    for (const [index, expected] of [1, 0, 0].entries()) {
      expect(Math.abs(linear[index] - expected)).toBeLessThanOrEqual(1e-3);
    }
  });

  it("reduces chroma on an out-of-gamut colour and leaves the rest alone", () => {
    const primary: Oklch = { l: 0.62, c: 0.15, h: 160 };
    expect(isInGamut(primary)).toBe(false);
    expect(gamutMap(primary)).toEqual({ l: 0.62, c: 0.14, h: 160 });

    const muted: Oklch = { l: 0.96, c: 0.01, h: 160 };
    expect(isInGamut(muted)).toBe(true);
    expect(gamutMap(muted)).toEqual(muted);
  });

  it("measures the pairs this task repaired at their stated ratios", () => {
    const mutedSurface: Oklch = { l: 0.96, c: 0.01, h: 160 };
    const primary: Oklch = { l: 0.62, c: 0.15, h: 160 };
    // Before/after for `--muted-foreground` on `--muted`.
    expect(
      contrastRatio({ l: 0.55, c: 0.02, h: 160 }, mutedSurface),
    ).toBeCloseTo(4.2913, 3);
    expect(
      contrastRatio({ l: 0.53, c: 0.02, h: 160 }, mutedSurface),
    ).toBeCloseTo(4.6684, 3);
    // Before/after for `--primary-foreground` on `--primary`.
    expect(contrastRatio({ l: 0.98, c: 0, h: 0 }, primary)).toBeCloseTo(
      3.2169,
      3,
    );
    expect(contrastRatio({ l: 0.15, c: 0.02, h: 160 }, primary)).toBeCloseTo(
      5.7548,
      3,
    );
  });

  it("measures the pair APRAS-88 repaired at its stated ratios", () => {
    const mutedSurface: Oklch = { l: 0.96, c: 0.01, h: 160 };
    const primary: Oklch = { l: 0.62, c: 0.15, h: 160 };
    const primaryText: Oklch = { l: 0.52, c: 0.11, h: 160 };
    // Before: the brand itself as text on the pale tint, below AA.
    expect(contrastRatio(primary, mutedSurface)).toBeLessThan(MINIMUM_RATIO);
    // After: `--primary-text` on the same surface, and its worst of the four.
    expect(contrastRatio(primaryText, mutedSurface)).toBeCloseTo(4.6547, 3);
    expect(contrastRatio(primaryText, { l: 1, c: 0, h: 0 })).toBeCloseTo(
      5.2096,
      3,
    );

    // This oracle reduces chroma on the 0.01 grid; `src/lib/contrast.ts`
    // bisects, so the two disagree in the third decimal on an out-of-gamut
    // colour. `--primary` `oklch(0.62 0.15 160)` is out of gamut and reads
    // 3.0448 here where the mapping document publishes contrast.ts's 3.0427;
    // `--primary-text` is in gamut and both read it identically. The
    // disagreement is recorded rather than smoothed over, because an oracle
    // silently agreeing with the module it exists to cross-check would be
    // worth nothing (see point 2 at the top of this file).
    expect(contrastRatio(primary, mutedSurface)).toBeCloseTo(3.0448, 3);
  });
});
