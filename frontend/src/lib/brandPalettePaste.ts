/**
 * The two grammars advanced mode accepts as a pasted palette (APRAS-95).
 *
 * Text in, either thirteen validated `#rrggbb` values out or a list of
 * problems. No React and no sentences: a problem is an i18n key plus its
 * parameters, so every visible string stays in `pt.json`/`en.json` the way the
 * rest of `TenantBrandColors` keeps them.
 *
 * **This module validates; it never normalises and never derives.** Values are
 * carried through exactly as typed — `#174B40` stays uppercase — because the
 * thirteen pickers do the same and `backend/app/core/branding.py` is the single
 * normalisation point. A palette pasted here and the same palette typed into
 * the fields therefore produce a byte-identical `PATCH` body.
 *
 * **Why a partial paste is refused rather than merged.**
 * `branding._normalized_palette` requires `set(palette) == set(AUTHORED_KEYS)`
 * exactly, so a half-palette is not the thing the contract describes; six of
 * the eight `MEASURED_PAIRS` read two different keys, so a palette half pasted
 * and half left over from the previous condominium yields a contrast verdict
 * nobody authored; and a single colour is what the thirteen pickers are already
 * for. An unknown key is refused by name rather than dropped, because the
 * server refuses it too and the two judgements must agree.
 */

import {
  BRAND_AUTHORED_KEYS,
  isValidHexColor,
  type BrandPalette,
  type BrandPaletteKey,
} from "../api/tenantProfile";

/** One reason a paste was refused: an i18n key and the values it interpolates. */
export interface PasteProblem {
  key: string;
  params?: Record<string, string>;
}

/**
 * What a paste yielded.
 *
 * `dark: undefined` means the text said nothing about the dark scheme — a CSS
 * block always does, since CSS carries no mode wrapper — and then the dark
 * draft and the derive-dark flag are left exactly as they were. `dark: null`
 * means the text said `"dark": null`, which is the derive-dark checkbox on.
 */
export type PasteResult =
  | { ok: true; light: BrandPalette; dark?: BrandPalette | null }
  | { ok: false; problems: PasteProblem[] };

const PROBLEM = "tenantProfile.brand.paste.problems";

const WRAPPER_KEYS = ["mode", "light", "dark"] as const;

/** `--key: value`, with the leading `--` optional and any inner whitespace. */
const DECLARATION = /^(?:--)?([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.+)$/;
const COMMENT = /\/\*[\s\S]*?\*\//g;

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/** How a refused value is quoted back to the person: the string they wrote. */
const shown = (value: unknown): string =>
  typeof value === "string" ? value : JSON.stringify(value);

/**
 * The thirteen-key rule, applied to one candidate palette.
 *
 * Every fault is collected rather than the first one reported: a block copied
 * out of a brand guide typically has more than one, and a reader who fixes one
 * fault per round trip through a dialog gives up.
 */
const validatePalette = (
  candidate: Record<string, unknown>,
  scheme: "light" | "dark",
): { palette: BrandPalette | null; problems: PasteProblem[] } => {
  const problems: PasteProblem[] = [];

  const missing = BRAND_AUTHORED_KEYS.filter((key) => !(key in candidate));
  if (missing.length > 0) {
    problems.push({
      key: `${PROBLEM}.missingKeys`,
      params: { keys: missing.join(", "), scheme },
    });
  }

  const allowed = new Set<string>(BRAND_AUTHORED_KEYS);
  for (const key of Object.keys(candidate)) {
    if (!allowed.has(key)) {
      problems.push({ key: `${PROBLEM}.unknownKey`, params: { key, scheme } });
    }
  }

  for (const key of BRAND_AUTHORED_KEYS) {
    if (!(key in candidate)) continue;
    const value = candidate[key];
    if (typeof value === "string" && isValidHexColor(value)) continue;
    const text = shown(value);
    problems.push({
      // `oklch()` gets its own message: the "Variáveis CSS emitidas" panel is
      // the likeliest place text is copied from, and it emits exactly that.
      key: text.trimStart().startsWith("oklch(")
        ? `${PROBLEM}.oklchValue`
        : `${PROBLEM}.badValue`,
      params: { key, value: text, scheme },
    });
  }

  if (problems.length > 0) {
    return { palette: null, problems };
  }
  return {
    palette: Object.fromEntries(
      BRAND_AUTHORED_KEYS.map((key) => [key, candidate[key] as string]),
    ) as BrandPalette,
    problems: [],
  };
};

/** A wrapped `{mode?, light, dark?}` object, or a bare palette. */
const readJsonObject = (parsed: Record<string, unknown>): PasteResult => {
  const wrapped = WRAPPER_KEYS.some((key) => key in parsed);
  if (!wrapped) {
    const { palette, problems } = validatePalette(parsed, "light");
    return palette === null ? { ok: false, problems } : { ok: true, light: palette };
  }

  const problems: PasteProblem[] = [];
  if ("mode" in parsed && parsed.mode !== "advanced") {
    // A simple-mode object has no thirteen values to apply, and silently
    // reading its `primary`/`accent` into two of the thirteen fields would be
    // a merge — which this module never does.
    return {
      ok: false,
      problems: [{ key: `${PROBLEM}.notAdvanced`, params: { mode: shown(parsed.mode) } }],
    };
  }
  for (const key of Object.keys(parsed)) {
    if (!(WRAPPER_KEYS as readonly string[]).includes(key)) {
      problems.push({ key: `${PROBLEM}.unknownTopLevel`, params: { key } });
    }
  }
  if (problems.length > 0) {
    return { ok: false, problems };
  }

  if (!isPlainObject(parsed.light)) {
    return { ok: false, problems: [{ key: `${PROBLEM}.missingLight` }] };
  }
  const light = validatePalette(parsed.light, "light");

  let dark: BrandPalette | null | undefined;
  if ("dark" in parsed && parsed.dark !== null) {
    if (!isPlainObject(parsed.dark)) {
      return { ok: false, problems: [{ key: `${PROBLEM}.darkNotPalette` }] };
    }
    const read = validatePalette(parsed.dark, "dark");
    if (read.palette === null || light.palette === null) {
      return { ok: false, problems: [...light.problems, ...read.problems] };
    }
    dark = read.palette;
  } else if ("dark" in parsed) {
    dark = null;
  }

  if (light.palette === null) {
    return { ok: false, problems: light.problems };
  }
  return "dark" in parsed
    ? { ok: true, light: light.palette, dark }
    : { ok: true, light: light.palette };
};

/**
 * A block of `--key: #hex;` declarations.
 *
 * One wrapping selector is tolerated because a chunk of `index.css` carries
 * one: everything up to and including the first `{`, and a trailing `}`, are
 * dropped and the selector itself ignored. A second brace after that strip is
 * two blocks pasted at once, and reading only the first silently would apply
 * the light palette of a paste whose author meant both schemes.
 */
const readCss = (text: string): PasteResult => {
  let body = text.replace(COMMENT, "");
  const opening = body.indexOf("{");
  if (opening >= 0) {
    body = body.slice(opening + 1).trimEnd();
    if (body.endsWith("}")) {
      body = body.slice(0, -1);
    }
  }
  if (body.includes("{") || body.includes("}")) {
    return { ok: false, problems: [{ key: `${PROBLEM}.multipleBlocks` }] };
  }

  const candidate: Record<string, unknown> = {};
  const problems: PasteProblem[] = [];
  for (const chunk of body.split(/[;\n]/)) {
    const line = chunk.trim();
    if (line === "") continue;
    const match = DECLARATION.exec(line);
    if (match === null) {
      problems.push({ key: `${PROBLEM}.cssDeclaration`, params: { line } });
      continue;
    }
    // Last-wins, the way `JSON.parse` resolves a repeated key: a palette
    // assembled by hand out of two sources is how a duplicate arises, and the
    // intent is unambiguous.
    candidate[match[1]] = match[2].trim();
  }

  // Syntax before semantics: text with a line that is not a declaration is not
  // a declaration block at all, and adding "the thirteen keys are missing" to
  // that verdict buries the one fault the person can act on.
  if (problems.length > 0) {
    return { ok: false, problems };
  }
  if (Object.keys(candidate).length === 0) {
    return { ok: false, problems: [{ key: `${PROBLEM}.empty` }] };
  }
  const { palette, problems: paletteProblems } = validatePalette(candidate, "light");
  return palette === null
    ? { ok: false, problems: paletteProblems }
    : { ok: true, light: palette };
};

/**
 * Read a pasted palette, choosing the grammar by looking at the text.
 *
 * `JSON.parse` decides: text it reads as an object is JSON, anything else is a
 * declaration block — `:root { --background: #fff; }` is not valid JSON, so the
 * split is unambiguous. Text that *opens* with `{` and is neither valid JSON
 * nor a readable block is reported as malformed JSON with `JSON.parse`'s own
 * message, because that is the parser its author was writing for and the
 * message carries the position.
 */
export const parseBrandPalettePaste = (text: string): PasteResult => {
  const trimmed = text.trim();
  if (trimmed === "") {
    return { ok: false, problems: [{ key: `${PROBLEM}.empty` }] };
  }

  let parsed: unknown;
  let jsonError: string | null = null;
  try {
    parsed = JSON.parse(trimmed);
  } catch (error) {
    // `JSON.parse` throws a `SyntaxError` whose message carries the position,
    // which is the whole value of reporting it: it is quoted verbatim.
    jsonError = String(error);
  }

  if (jsonError === null && isPlainObject(parsed)) {
    return readJsonObject(parsed);
  }

  const css = readCss(trimmed);
  if (!css.ok && jsonError !== null && trimmed.startsWith("{")) {
    return {
      ok: false,
      problems: [{ key: `${PROBLEM}.malformed`, params: { detail: jsonError } }],
    };
  }
  return css;
};

export type { BrandPaletteKey };
