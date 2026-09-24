/**
 * The contrast measurement, and nothing else (APRAS-68 D-D).
 *
 * `backend/app/core/branding.py` is the **only** theme derivation in the
 * repository. This module is deliberately not a port of it: it converts,
 * gamut-maps and measures two given colours, and it cannot produce a theme.
 * It exists so the profile screen can tell someone a pair is illegible while
 * they are still typing, instead of after a round trip — the server refuses
 * the same palette with the same numbers either way (D-B).
 *
 * Three rules are carried over verbatim from the Python, because each closes
 * a defect whose failure mode is silent:
 *
 * 1. **Luminance runs on linear light.** {@link oklchToLinearSrgb} already
 *    returns linear-light channels, so the sRGB transfer must not be applied
 *    again. A double transfer does not halve a ratio — it *inflates* it for
 *    light-on-light pairs (the shipped `--muted-foreground`/`--muted` pair
 *    reads 4.29 correctly and 10.96 under the bug), so illegible palettes
 *    would pass.
 * 2. **Out-of-gamut colours are chroma-reduced, never clipped.** CSS Color 4
 *    §13 requires a browser to gamut-map an out-of-range `oklch()` by
 *    reducing chroma at constant lightness and hue. A naive per-channel clip
 *    is a *different colour*: it certifies `oklch(0.52 0.22 210)` on
 *    `oklch(0.15 0.02 210)` at 4.52 where the browser paints 3.74.
 * 3. **The measured value is the emitted string.** Everything here starts
 *    from an `oklch(L C H)` string the API sent or a `#rrggbb` someone typed,
 *    never from an internal float.
 *
 * Both halves are pinned against `backend/tests/data/contrast_fixtures.json`,
 * by `src/lib/__tests__/contrast.test.ts` here and by
 * `backend/tests/test_branding.py` there. Neither language may import the
 * other, so that file is the contract.
 */

/** One colour in OKLCH: `l` 0–1, `c` ≥ 0, `h` in degrees. */
export interface Oklch {
  l: number;
  c: number;
  h: number;
}

/** One measured pair that does not reach {@link MINIMUM_CONTRAST_RATIO}. */
export interface ContrastFailure {
  pair: string;
  ratio: number;
  minimum: number;
}

/** WCAG 2.1 AA for normal text — `branding.MINIMUM_CONTRAST_RATIO`. */
export const MINIMUM_CONTRAST_RATIO = 4.5;

/**
 * The eight text/surface pairs, as `[foreground, background]` —
 * `branding.MEASURED_PAIRS`, in the same order, so the screen lists them in
 * the order the 422 body names them.
 *
 * `muted-foreground` appears three times on purpose: one token carries text
 * over three surfaces and none of the three may move. `border`, `input` and
 * `ring` are not measured at all — the 3:1 non-text minimum is out of scope.
 */
export const MEASURED_PAIRS: ReadonlyArray<readonly [string, string]> = [
  ["foreground", "background"],
  ["card-foreground", "card"],
  ["primary-foreground", "primary"],
  ["secondary-foreground", "secondary"],
  ["accent-foreground", "accent"],
  ["muted-foreground", "muted"],
  ["muted-foreground", "background"],
  ["muted-foreground", "card"],
];

/** How far outside `[0, 1]` a linear channel may sit and still count as in
 *  gamut — floating-point slack, not a colour allowance. */
const GAMUT_TOLERANCE = 1e-4;
/** The just-noticeable difference CSS Color 4 §13 allows a gamut-mapped
 *  colour to keep from the requested one, in OKLab units. */
const JND = 0.02;
const BISECTION_EPSILON = 1e-5;
const SRGB_KNEE = 0.04045;
const MAX_CHANNEL = 255;
const FULL_TURN = 360;
const LUMINANCE_OFFSET = 0.05;
const WCAG_WEIGHTS: readonly [number, number, number] = [0.2126, 0.7152, 0.0722];
const DECIMALS = 2;

/** `branding._OKLCH_STRING`, plus the surrounding and inner whitespace a
 *  stylesheet or a hand-written fixture may carry. */
const OKLCH_STRING =
  /^oklch\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)$/;
const HEX = /^#[0-9a-fA-F]{6}$/;

type LinearRgb = readonly [number, number, number];

const srgbToLinear = (channel: number): number =>
  channel <= SRGB_KNEE ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;

const linearToOklab = (rgb: LinearRgb): [number, number, number] => {
  const [red, green, blue] = rgb;
  const long = Math.cbrt(
    0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue,
  );
  const medium = Math.cbrt(
    0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue,
  );
  const short = Math.cbrt(
    0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue,
  );
  return [
    0.2104542553 * long + 0.793617785 * medium - 0.0040720468 * short,
    1.9779984951 * long - 2.428592205 * medium + 0.4505937099 * short,
    0.0259040371 * long + 0.7827717662 * medium - 0.808675766 * short,
  ];
};

/**
 * OKLCH to **linear-light** sRGB, possibly outside `[0, 1]`.
 *
 * The result is what {@link relativeLuminance} consumes directly: applying
 * the sRGB transfer to it is rule 1's bug.
 */
export const oklchToLinearSrgb = (colour: Oklch): [number, number, number] => {
  const radians = (colour.h * Math.PI) / 180;
  const axisA = colour.c * Math.cos(radians);
  const axisB = colour.c * Math.sin(radians);
  const long = (colour.l + 0.3963377774 * axisA + 0.2158037573 * axisB) ** 3;
  const medium = (colour.l - 0.1055613458 * axisA - 0.0638541728 * axisB) ** 3;
  const short = (colour.l - 0.0894841775 * axisA - 1.291485548 * axisB) ** 3;
  return [
    4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
    -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
    -0.0041960863 * long - 0.7034186147 * medium + 1.707614701 * short,
  ];
};

/** Whether all three linear channels sit inside `[0, 1] ± 1e-4`. */
export const isInGamut = (colour: Oklch): boolean =>
  oklchToLinearSrgb(colour).every(
    (channel) => channel >= -GAMUT_TOLERANCE && channel <= 1 + GAMUT_TOLERANCE,
  );

const clip = (rgb: LinearRgb): [number, number, number] => [
  Math.min(1, Math.max(0, rgb[0])),
  Math.min(1, Math.max(0, rgb[1])),
  Math.min(1, Math.max(0, rgb[2])),
];

/**
 * The linear-light colour a browser actually **paints** (rule 2).
 *
 * Chroma is bisected at constant lightness and hue until the result is inside
 * sRGB, clipping only once the remaining OKLab error is under the JND. This
 * is the snap loop, not merely the predicate: without it the ratio below
 * would be measured on a colour nobody renders.
 */
export const gamutMap = (colour: Oklch): [number, number, number] => {
  if (colour.l >= 1) {
    return [1, 1, 1];
  }
  if (colour.l <= 0) {
    return [0, 0, 0];
  }
  if (isInGamut(colour)) {
    return clip(oklchToLinearSrgb(colour));
  }

  let low = 0;
  let high = colour.c;
  const radians = (colour.h * Math.PI) / 180;
  while (high - low > BISECTION_EPSILON) {
    const middle = (low + high) / 2;
    const candidate: Oklch = { l: colour.l, c: middle, h: colour.h };
    if (isInGamut(candidate)) {
      low = middle;
      continue;
    }
    const clipped = clip(oklchToLinearSrgb(candidate));
    const [lightness, axisA, axisB] = linearToOklab(clipped);
    const error = Math.hypot(
      colour.l - lightness,
      middle * Math.cos(radians) - axisA,
      middle * Math.sin(radians) - axisB,
    );
    if (error < JND) {
      return clipped;
    }
    high = middle;
  }
  // Reached only if the bisection closes without any out-of-gamut candidate
  // ever landing within the JND — which the geometry makes unreachable,
  // because a candidate just above the boundary clips to an arbitrarily small
  // error. It is kept because `branding.gamut_map` has the same line: the two
  // implementations are read side by side, and a missing fallback reads as an
  // omission rather than as a proof.
  /* v8 ignore next */
  return clip(oklchToLinearSrgb({ l: colour.l, c: low, h: colour.h }));
};

/** WCAG 2.1 relative luminance of already-**linear** channels (rule 1). */
export const relativeLuminance = (linearRgb: LinearRgb): number =>
  WCAG_WEIGHTS[0] * linearRgb[0] +
  WCAG_WEIGHTS[1] * linearRgb[1] +
  WCAG_WEIGHTS[2] * linearRgb[2];

/** The WCAG 2.1 ratio between two colours **as the browser paints them**. */
export const contrastRatio = (first: Oklch, second: Oklch): number => {
  const luminances = [first, second]
    .map((colour) => relativeLuminance(gamutMap(colour)))
    .sort((a, b) => a - b);
  return (
    (luminances[1] + LUMINANCE_OFFSET) / (luminances[0] + LUMINANCE_OFFSET)
  );
};

const LINEAR_KNEE = 0.0031308;

const linearToSrgb = (channel: number): number =>
  channel <= LINEAR_KNEE ? 12.92 * channel : 1.055 * channel ** (1 / 2.4) - 0.055;

/**
 * The `#rrggbb` a browser paints for `colour` — `branding.oklch_to_hex`.
 *
 * For **display only**: prefilling the 13 advanced inputs from the scheme the
 * server already derived, so nobody starts from a blank palette. It converts;
 * it does not derive, and it is never what gets sent — the field the person
 * then edits is.
 */
export const oklchToHex = (colour: Oklch): string =>
  `#${gamutMap(colour)
    .map((channel) =>
      Math.round(Math.min(1, Math.max(0, linearToSrgb(channel))) * MAX_CHANNEL)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;

/** Parse `#rrggbb` in either case into OKLCH, or `null` if it is not one. */
export const hexToOklch = (value: string): Oklch | null => {
  if (!HEX.test(value)) {
    return null;
  }
  const digits = value.slice(1);
  const srgb = [0, 2, 4].map(
    (offset) => parseInt(digits.slice(offset, offset + 2), 16) / MAX_CHANNEL,
  ) as [number, number, number];
  const [lightness, axisA, axisB] = linearToOklab(
    srgb.map(srgbToLinear) as [number, number, number],
  );
  return {
    l: lightness,
    c: Math.hypot(axisA, axisB),
    h: ((Math.atan2(axisB, axisA) * 180) / Math.PI + FULL_TURN) % FULL_TURN,
  };
};

/**
 * What a browser paints for `foreground` at `alpha` over `background`
 * (APRAS-80's compositing model, APRAS-90's single home).
 *
 * An opacity modifier such as `/80` is not a colour the theme declares: the
 * pixels someone reads are the blend, and measuring the token instead of the
 * blend certifies a pair the screen never paints. Composited the way the paint
 * pipeline does it — both colours taken to the 8-bit sRGB values the
 * compositor holds ({@link oklchToHex}, which gamut-maps), blended in that
 * space, and read back ({@link hexToOklch}). Blending the linear-light or the
 * OKLab coordinates instead gives a different number, for a colour nobody
 * renders.
 *
 * Like the rest of this module it only measures: it cannot produce a theme,
 * and `backend/app/core/branding.py` remains the only derivation.
 */
export const compositeOver = (
  foreground: Oklch,
  background: Oklch,
  alpha: number,
): Oklch => {
  const over = oklchToHex(foreground).slice(1);
  const under = oklchToHex(background).slice(1);
  const channels = [0, 2, 4].map((offset) =>
    Math.round(
      alpha * parseInt(over.slice(offset, offset + 2), 16) +
        (1 - alpha) * parseInt(under.slice(offset, offset + 2), 16),
    ),
  );
  const mixed = hexToOklch(
    `#${channels.map((value) => value.toString(16).padStart(2, "0")).join("")}`,
  );
  // Unreachable: three rounded 0-255 channels always render as six hex
  // digits. Kept, and ignored for coverage exactly as `gamutMap`'s fallback
  // above is, because the alternative is a non-null assertion on a parse.
  /* v8 ignore next 3 */
  if (mixed === null) {
    throw new Error("the composited colour is not a six-digit hex");
  }
  return mixed;
};

/** Read an emitted `oklch(L C H)` string back, or `null` if it is not one. */
export const parseOklch = (value: string): Oklch | null => {
  const match = OKLCH_STRING.exec(value.trim());
  if (match === null) {
    return null;
  }
  return {
    l: Number(match[1]),
    c: Number(match[2]),
    h: Number(match[3]),
  };
};

/** The same string the backend emits, at the 2dp `index.css` is authored at. */
export const formatOklch = (colour: Oklch): string =>
  `oklch(${colour.l.toFixed(DECIMALS)} ${colour.c.toFixed(DECIMALS)} ${colour.h.toFixed(
    DECIMALS,
  )})`;

/**
 * Measure one **emitted** scheme's eight pairs, in document order.
 *
 * A value this cannot parse is skipped rather than guessed at: the server
 * remains the authority, and a screen that invented a ratio for a string it
 * did not understand would be worse than one that stayed quiet. Nothing here
 * derives a colour — every value measured came out of `build_theme` or out of
 * a field somebody typed.
 */
export const auditScheme = (
  scheme: Readonly<Record<string, string>>,
): ContrastFailure[] => {
  const failures: ContrastFailure[] = [];
  for (const [foreground, background] of MEASURED_PAIRS) {
    const text = parseOklch(scheme[foreground] ?? "");
    const surface = parseOklch(scheme[background] ?? "");
    if (text === null || surface === null) {
      continue;
    }
    const ratio = contrastRatio(text, surface);
    if (ratio < MINIMUM_CONTRAST_RATIO) {
      failures.push({
        pair: `${foreground}/${background}`,
        ratio: Number(ratio.toFixed(DECIMALS)),
        minimum: MINIMUM_CONTRAST_RATIO,
      });
    }
  }
  return failures;
};

/** Measure a palette of `#rrggbb` values — the live feedback in advanced
 *  mode, where the eight pairs are whatever the person has typed so far. */
export const auditHexPalette = (
  palette: Readonly<Record<string, string>>,
): ContrastFailure[] =>
  auditScheme(
    Object.fromEntries(
      Object.entries(palette).map(([key, value]) => {
        const colour = hexToOklch(value);
        return [key, colour === null ? "" : formatOklch(colour)];
      }),
    ),
  );
