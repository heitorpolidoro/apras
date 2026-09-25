/// <reference types="node" />
// @vitest-environment node
//
// The compile-time verification of the mapping table (APRAS-78, §4b).
//
// **What this cannot do, stated up front.** This repository has no
// Playwright, no Storybook, no Chromatic and no Percy, and jsdom does not run
// the Tailwind pipeline, so computed-style assertions and visual regression
// are both unavailable without new infrastructure — deliberately out of scope
// for APRAS-78.
//
// What is available is Tailwind 4.2.4's own `compile()`. This suite compiles
// `src/index.css` through it over a fixture holding **every class pair** in
// §1b–1e of `docs/frontend/theme-token-mapping.md`, resolves both sides
// through the `var()` chain to the value the browser would paint, and asserts
// the published ΔL and ΔE to ±0.1. A table row that lies, or a substitution
// nobody wrote down, fails here.
//
// **It does not prove the right row was chosen at the right call site.** §1f
// names three cases it cannot see: `bg-white` on a page shell mapped to
// `bg-card`; `hover:bg-slate-100` mapped to `bg-muted` instead of `bg-accent`
// (identical numbers — `muted`, `accent` and `secondary` are byte-identical
// in `:root`, which the last case below asserts); and emerald migrated as
// brand where it meant success. All three stay a human review duty.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import { compile } from "tailwindcss";
import {
  contrastRatio,
  hexToOklch,
  MINIMUM_CONTRAST_RATIO,
  parseOklch,
  type Oklch,
} from "../lib/contrast";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(HERE, "..");
const FRONTEND_ROOT = path.resolve(SRC, "..");

/** The tolerance §4b fixes: the table publishes two decimals and is asserted
 *  to a tenth, so a rounding disagreement is not a failure and a wrong token
 *  is. Asserted as an absolute difference and deliberately not with
 *  `toBeCloseTo`, whose second argument is a digit count rather than a
 *  tolerance and would quietly widen this to ±0.397. */
const TOLERANCE = 0.1;

/** `actual` is within {@link TOLERANCE} of `expected`. */
const within = (actual: number, expected: number): number =>
  Math.abs(actual - expected);

/** One row of §1b–1e: a source palette class, the token class it becomes,
 *  and the ΔL / ΔE the document publishes for the pair. */
interface Row {
  source: string;
  target: string;
  dL: number;
  dE: number;
  /** §1i: the target carries this alpha, checked structurally, never
   *  composited. The colour comparison uses the base token. */
  alpha?: number;
}

/** The nine brand **text** classes §1k routes to `*-primary-text` rather
 *  than to `*-primary` (APRAS-88). Their rows below are retargeted **in
 *  place**; appending new ones would leave nine stale `text-primary` rows
 *  that still pass — `--primary` does not move — and green a suite that
 *  contradicts the table it guards. */
const BRAND_TEXT_CLASSES: readonly string[] = [
  "text-indigo-300",
  "text-indigo-500",
  "text-indigo-600",
  "text-indigo-700",
  "text-indigo-800",
  "text-indigo-900",
  "text-emerald-500",
  "text-emerald-600",
  "text-emerald-700",
];

/** Every class pair in §1b–1e, published values included. */
const ROWS: readonly Row[] = [
  // §1b — neutral surfaces. `bg-muted`, `bg-accent` and `bg-secondary` are
  // byte-identical in `:root`, so the 50/100/200 fills are listed against
  // both candidates §1f case 2 admits.
  { source: "bg-white", target: "bg-card", dL: 0.0, dE: 0.0 },
  { source: "bg-white", target: "bg-background", dL: 1.0, dE: 1.0 },
  { source: "bg-slate-50", target: "bg-muted", dL: 2.4, dE: 2.61 },
  { source: "bg-slate-50", target: "bg-accent", dL: 2.4, dE: 2.61 },
  { source: "bg-gray-50", target: "bg-muted", dL: 2.5, dE: 2.7 },
  { source: "bg-gray-50", target: "bg-accent", dL: 2.5, dE: 2.7 },
  { source: "bg-slate-100", target: "bg-muted", dL: 0.8, dE: 1.44 },
  { source: "bg-slate-100", target: "bg-accent", dL: 0.8, dE: 1.44 },
  { source: "bg-gray-100", target: "bg-muted", dL: 0.7, dE: 1.32 },
  { source: "bg-gray-100", target: "bg-accent", dL: 0.7, dE: 1.32 },
  { source: "bg-slate-200", target: "bg-muted", dL: 3.1, dE: 3.54 },
  { source: "bg-slate-200", target: "bg-accent", dL: 3.1, dE: 3.54 },
  { source: "bg-gray-200", target: "bg-muted", dL: 3.2, dE: 3.45 },
  { source: "bg-gray-200", target: "bg-accent", dL: 3.2, dE: 3.45 },
  { source: "bg-slate-300", target: "bg-primary", dL: 24.9, dE: 29.21 },
  { source: "bg-slate-900", target: "bg-foreground", dL: 6.8, dE: 8.2 },
  { source: "bg-slate-950", target: "bg-foreground", dL: 1.1, dE: 4.69 },

  // §1c — borders, dividers and rings.
  { source: "border-slate-200", target: "border-border", dL: 0.9, dE: 1.94 },
  { source: "border-gray-200", target: "border-border", dL: 0.8, dE: 1.52 },
  { source: "divide-slate-200", target: "divide-border", dL: 0.9, dE: 1.94 },
  { source: "divide-gray-200", target: "divide-border", dL: 0.8, dE: 1.52 },
  { source: "border-slate-300", target: "border-input", dL: 5.1, dE: 5.66 },
  { source: "border-gray-300", target: "border-input", dL: 4.8, dE: 5.03 },
  { source: "border-white", target: "border-card", dL: 0.0, dE: 0.0 },

  // §1d — neutral text.
  { source: "text-slate-900", target: "text-foreground", dL: 6.8, dE: 8.2 },
  { source: "text-gray-900", target: "text-foreground", dL: 7.0, dE: 7.95 },
  { source: "text-slate-600", target: "text-muted-foreground", dL: 8.4, dE: 9.76 },
  { source: "text-gray-600", target: "text-muted-foreground", dL: 8.4, dE: 9.22 },
  { source: "text-slate-500", target: "text-muted-foreground", dL: 2.4, dE: 5.77 },
  { source: "text-gray-500", target: "text-muted-foreground", dL: 2.1, dE: 4.29 },
  { source: "text-slate-400", target: "text-muted-foreground", dL: 17.4, dE: 18.02 },
  { source: "text-gray-400", target: "text-muted-foreground", dL: 17.7, dE: 18.0 },
  { source: "text-white", target: "text-primary-foreground", dL: 85.0, dE: 85.02 },
  { source: "text-white", target: "text-destructive-foreground", dL: 2.0, dE: 2.0 },

  // §1e — brand, accent and destructive.
  { source: "bg-indigo-500", target: "bg-primary", dL: 3.5, dE: 33.15 },
  { source: "text-indigo-500", target: "text-primary-text", dL: 6.5, dE: 30.66 },
  { source: "border-indigo-500", target: "border-primary", dL: 3.5, dE: 33.15 },
  { source: "ring-indigo-500", target: "ring-ring", dL: 3.5, dE: 33.15 },
  { source: "bg-indigo-600", target: "bg-primary", dL: 10.9, dE: 37.24 },
  { source: "text-indigo-600", target: "text-primary-text", dL: 0.9, dE: 32.71 },
  { source: "border-indigo-600", target: "border-primary", dL: 10.9, dE: 37.24 },
  { source: "accent-indigo-600", target: "accent-primary-foreground", dL: 36.1, dE: 45.18 },
  { source: "bg-indigo-700", target: "bg-primary/90", dL: 16.3, dE: 37.33, alpha: 90 },
  { source: "text-indigo-700", target: "text-primary-text", dL: 6.3, dE: 31.25 },
  { source: "text-indigo-800", target: "text-primary-text", dL: 12.2, dE: 29.11 },
  { source: "text-indigo-900", target: "text-primary-text", dL: 16.1, dE: 27.2 },
  { source: "text-indigo-300", target: "text-primary-text", dL: 26.5, dE: 32.58 },
  { source: "border-indigo-400", target: "border-primary", dL: 5.3, dE: 28.84 },
  { source: "bg-indigo-50", target: "bg-accent", dL: 0.2, dE: 2.38 },
  { source: "bg-indigo-100", target: "bg-accent", dL: 3.0, dE: 4.92 },
  { source: "bg-indigo-200", target: "bg-accent", dL: 9.0, dE: 11.38 },
  { source: "border-indigo-100", target: "border-border", dL: 1.0, dE: 4.02 },
  { source: "border-indigo-200", target: "border-border", dL: 5.0, dE: 8.58 },
  { source: "bg-emerald-500", target: "bg-primary", dL: 7.6, dE: 7.89 },
  { source: "text-emerald-500", target: "text-primary-text", dL: 17.6, dE: 18.6 },
  { source: "border-emerald-500", target: "border-primary", dL: 7.6, dE: 7.89 },
  { source: "ring-emerald-500", target: "ring-ring", dL: 7.6, dE: 7.89 },
  { source: "bg-emerald-600", target: "bg-primary", dL: 2.4, dE: 2.59 },
  { source: "text-emerald-600", target: "text-primary-text", dL: 7.6, dE: 8.4 },
  { source: "border-emerald-600", target: "border-primary", dL: 2.4, dE: 2.59 },
  { source: "ring-emerald-600", target: "ring-ring", dL: 2.4, dE: 2.59 },
  { source: "bg-emerald-700", target: "bg-primary/90", dL: 11.2, dE: 11.72, alpha: 90 },
  { source: "text-emerald-700", target: "text-primary-text", dL: 1.2, dE: 1.82 },
  { source: "text-red-600", target: "text-destructive", dL: 0.3, dE: 0.6 },
  { source: "bg-red-600", target: "bg-destructive", dL: 0.3, dE: 0.6 },
  { source: "text-red-500", target: "text-destructive", dL: 5.7, dE: 5.75 },
  { source: "bg-red-500", target: "bg-destructive", dL: 5.7, dE: 5.75 },
  { source: "text-red-700", target: "text-destructive", dL: 7.5, dE: 7.97 },
  { source: "bg-red-700", target: "bg-destructive", dL: 7.5, dE: 7.97 },
];

// --- the stylesheet reader -------------------------------------------------

interface Rule {
  selector: string;
  body: string;
}

/**
 * Every rule in `css`, with `@layer` wrappers flattened away.
 *
 * A brace scanner rather than a regular expression: `bg-primary/90` nests an
 * `@supports` block inside its own rule, and the theme layer nests hundreds
 * of declarations inside an at-rule.
 */
const rules = (source: string): Rule[] => {
  // Comments and statement at-rules (`@layer theme, base, …;`) are dropped
  // first: left in, they end up glued to the front of the next selector and
  // `:root, :host` stops being findable by name.
  const css = source.replace(/\/\*[\s\S]*?\*\//g, "");
  const found: Rule[] = [];
  let selector = "";
  for (let index = 0; index < css.length; index += 1) {
    const character = css[index];
    if (character === ";") {
      selector = "";
      continue;
    }
    if (character !== "{") {
      selector += character;
      continue;
    }
    let depth = 1;
    let end = index + 1;
    for (; end < css.length && depth > 0; end += 1) {
      if (css[end] === "{") depth += 1;
      if (css[end] === "}") depth -= 1;
    }
    const body = css.slice(index + 1, end - 1);
    const name = selector.trim();
    if (name.startsWith("@layer")) {
      found.push(...rules(body));
    } else {
      found.push({ selector: name, body });
    }
    selector = "";
    index = end - 1;
  }
  return found;
};

/** The `name: value` pairs declared directly in a rule body, nested blocks
 *  excluded. */
const declarations = (body: string): Map<string, string> => {
  const pairs = new Map<string, string>();
  let depth = 0;
  let buffer = "";
  const flush = () => {
    const colon = buffer.indexOf(":");
    if (colon > 0) {
      pairs.set(buffer.slice(0, colon).trim(), buffer.slice(colon + 1).trim());
    }
    buffer = "";
  };
  for (const character of body) {
    if (character === "{") depth += 1;
    if (character === "}") depth -= 1;
    if (character === ";" && depth === 0) {
      flush();
      continue;
    }
    if (depth === 0) buffer += character;
  }
  flush();
  return pairs;
};

const VAR_REFERENCE = /^var\((--[a-z0-9-]+)\)$/;
const PERCENT_LIGHTNESS = /^oklch\(\s*([\d.]+)%/;
const SHORT_HEX = /^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$/;

/**
 * The colour a value string denotes, as OKLCH.
 *
 * Both readers come from `src/lib/contrast.ts` and neither is reimplemented
 * here — that module's gamut-mapped arithmetic is the repository's single
 * measurement and a second copy would disagree with it in the third decimal.
 * Two shapes need normalising before `parseOklch` will accept them, and both
 * are Tailwind's, not ours:
 *
 * - Tailwind authors its palette with a **percentage** lightness
 *   (`oklch(98.4% 0.003 247.858)`), which `parseOklch`'s grammar rejects;
 * - `--color-white` and `--color-black` are three-digit hex.
 */
const readColour = (value: string): Oklch => {
  const percent = PERCENT_LIGHTNESS.exec(value);
  const normalised =
    percent === null
      ? value
      : value.replace(`${percent[1]}%`, String(Number(percent[1]) / 100));
  const oklch = parseOklch(normalised);
  if (oklch !== null) {
    return oklch;
  }
  const short = SHORT_HEX.exec(value.trim());
  const hex = hexToOklch(
    short === null
      ? value.trim()
      : `#${short[1]}${short[1]}${short[2]}${short[2]}${short[3]}${short[3]}`,
  );
  if (hex === null) {
    throw new Error(`not a colour this resolver understands: ${value}`);
  }
  return hex;
};

/** OKLab coordinates in the units §1's ΔE is defined in: L over 0–100 and
 *  chroma scaled by 100. */
const lab = (colour: Oklch): [number, number, number] => [
  colour.l * 100,
  colour.c * 100 * Math.cos((colour.h * Math.PI) / 180),
  colour.c * 100 * Math.sin((colour.h * Math.PI) / 180),
];

const deltaL = (from: Oklch, to: Oklch): number => Math.abs(lab(from)[0] - lab(to)[0]);

const deltaE = (from: Oklch, to: Oklch): number => {
  const [l1, a1, b1] = lab(from);
  const [l2, a2, b2] = lab(to);
  return Math.hypot(l1 - l2, a1 - a2, b1 - b2);
};

/** The compiled stylesheet, plus the two lookups §4b requires be kept apart. */
interface Sheet {
  css: string;
  rule: (className: string) => Rule;
  variable: (name: string) => string;
  colourOf: (className: string) => Oklch;
}

const escapeClass = (className: string): string =>
  className.replace(/\//g, "\\/").replace(/\./g, "\\.");

const build = async (candidates: readonly string[]): Promise<Sheet> => {
  const loadStylesheet = async (id: string, base: string) => {
    const file =
      id === "tailwindcss"
        ? path.join(FRONTEND_ROOT, "node_modules", "tailwindcss", "index.css")
        : id.startsWith("tailwindcss/")
          ? path.join(FRONTEND_ROOT, "node_modules", id)
          : path.resolve(base, id);
    return {
      path: file,
      base: path.dirname(file),
      content: readFileSync(file, "utf8"),
    };
  };
  const compiler = await compile(
    readFileSync(path.join(SRC, "index.css"), "utf8"),
    { base: SRC, loadStylesheet },
  );
  const css = compiler.build([...candidates]);
  const parsed = rules(css);

  // Requirement 1: the `:root` block **`index.css` contributes** — the last
  // unqualified `:root` rule that declares `--primary`. Tailwind's own theme
  // layer emits `:root, :host` before it, so the selector is not unique even
  // before `.dark` is considered.
  // Requirement 2: never `.dark`. The stylesheet declares `--primary` twice,
  // `0.62` in `:root` and `0.65` in `.dark`; a last-wins resolver would
  // validate the dark scheme against the light table and pass.
  const authored = parsed.filter(
    (candidate) =>
      candidate.selector === ":root" &&
      declarations(candidate.body).has("--primary"),
  );
  if (authored.length === 0) {
    throw new Error("no unqualified :root rule declares --primary");
  }
  const root = declarations(authored[authored.length - 1].body);
  const theme = new Map<string, string>();
  for (const candidate of parsed) {
    if (candidate.selector !== ":root, :host") {
      continue;
    }
    for (const [name, value] of declarations(candidate.body)) {
      theme.set(name, value);
    }
  }

  const variable = (name: string): string => {
    const value = root.get(name) ?? theme.get(name);
    if (value === undefined) {
      throw new Error(`no declaration for ${name} outside .dark`);
    }
    return value;
  };

  const rule = (className: string): Rule => {
    const selector = `.${escapeClass(className)}`;
    const found = parsed.find((candidate) => candidate.selector === selector);
    if (found === undefined) {
      throw new Error(`Tailwind emitted no rule for ${className}`);
    }
    return found;
  };

  const colourOf = (className: string): Oklch => {
    // §1i: the **unconditional** declaration, never the `@supports` one —
    // `parseOklch` returns `null` for `color-mix`, and a resolver that read
    // the second declaration would silently measure nothing at all.
    const body = rule(className).body.split("@supports")[0];
    const reference = /var\((--color-[a-z0-9-]+)\)/.exec(body);
    if (reference === null) {
      throw new Error(`no var(--color-…) in the rule for ${className}`);
    }
    let value = variable(reference[1]);
    for (let hop = 0; hop < 8; hop += 1) {
      const next = VAR_REFERENCE.exec(value);
      if (next === null) {
        break;
      }
      value = variable(next[1]);
    }
    return readColour(value);
  };

  return { css, rule, variable, colourOf };
};

const base = (className: string): string => className.split("/")[0];

let sheet: Sheet;

beforeAll(async () => {
  const candidates = new Set<string>();
  for (const row of ROWS) {
    candidates.add(row.source);
    candidates.add(row.target);
    candidates.add(base(row.target));
  }
  candidates.add("bg-muted");
  candidates.add("bg-accent");
  candidates.add("bg-secondary");
  // §1k's four text surfaces, plus the token the nine rows no longer target:
  // `text-primary` is still measured, as the *before* side of the repair.
  candidates.add("bg-background");
  candidates.add("bg-card");
  candidates.add("text-primary");
  sheet = await build([...candidates]);
});

describe("the resolver", () => {
  it("reads --primary from :root and never from .dark", () => {
    // The trap, asserted directly so a later simplification to a last-wins
    // lookup fails loudly rather than certifying the dark scheme.
    expect(sheet.variable("--primary")).toBe("oklch(0.62 0.15 160)");
    expect(sheet.variable("--primary")).not.toBe("oklch(0.65 0.15 160)");
    expect(sheet.css).toContain("oklch(0.65 0.15 160)");
  });

  it("normalises Tailwind's percentage lightness before parsing it", () => {
    // `parseOklch` rejects `oklch(98.4% …)` outright, so a resolver that
    // handed it straight over would throw on every palette class.
    expect(parseOklch("oklch(98.4% 0.003 247.858)")).toBeNull();
    expect(readColour("oklch(98.4% 0.003 247.858)")?.l).toBeCloseTo(0.984, 6);
  });

  it("reads --color-white, which Tailwind authors as three-digit hex", () => {
    expect(readColour("#fff").l).toBeCloseTo(1, 3);
  });
});

describe("every class pair in §1b–1e", () => {
  it.each(ROWS.map((row) => [row.source, row.target, row] as const))(
    "%s → %s matches the published ΔL and ΔE",
    (_source, _target, row) => {
      const from = sheet.colourOf(row.source);
      // §1i: the colour is measured against the **base** token; the alpha is
      // declared unmeasured and is checked structurally below.
      const to = sheet.colourOf(base(row.target));

      expect(within(deltaL(from, to), row.dL)).toBeLessThanOrEqual(TOLERANCE);
      expect(within(deltaE(from, to), row.dE)).toBeLessThanOrEqual(TOLERANCE);
    },
  );

  it("covers every utility prefix the table maps", () => {
    const prefixes = new Set(ROWS.map((row) => row.source.split("-")[0]));

    expect([...prefixes].sort()).toEqual([
      "accent",
      "bg",
      "border",
      "divide",
      "ring",
      "text",
    ]);
  });
});

describe("§1i, the opacity-modified targets", () => {
  const withAlpha = ROWS.filter((row) => row.alpha !== undefined);

  it("has one target carrying an alpha, bg-primary/90", () => {
    expect(new Set(withAlpha.map((row) => row.target))).toEqual(
      new Set(["bg-primary/90"]),
    );
  });

  it.each(withAlpha.map((row) => [row.target, row.alpha] as const))(
    "declares %s unconditionally and composites it under @supports",
    (target, alpha) => {
      const body = sheet.rule(target).body;
      const token = base(target).split("-").slice(1).join("-");

      expect(body.split("@supports")[0]).toContain(`var(--color-${token})`);
      expect(body).toContain(
        `color-mix(in oklab, var(--color-${token}) ${alpha}%, transparent)`,
      );
    },
  );
});

describe("what the numbers cannot see (§1f case 2)", () => {
  it("resolves muted, accent and secondary to the same colour", () => {
    // Which is exactly why a `hover:bg-slate-100` mapped to `bg-muted`
    // instead of `bg-accent` passes this suite with identical figures. Case 2
    // is a review duty on every sibling, not a test.
    const muted = sheet.colourOf("bg-muted");
    const accent = sheet.colourOf("bg-accent");
    const secondary = sheet.colourOf("bg-secondary");

    expect(deltaE(muted, accent)).toBe(0);
    expect(deltaE(muted, secondary)).toBe(0);
  });
});

describe("§1k, the brand text token (APRAS-88)", () => {
  it("routes every one of the nine brand text classes to text-primary-text", () => {
    for (const source of BRAND_TEXT_CLASSES) {
      const rows = ROWS.filter((row) => row.source === source);

      expect(rows.map((row) => row.target), source).toEqual([
        "text-primary-text",
      ]);
    }
  });

  it("leaves every non-text brand utility on *-primary", () => {
    // The other half of §1k: `bg-`, `border-`, `ring-` and `accent-` are
    // graphical objects at a 3:1 floor and do not move.
    const graphical = ROWS.filter(
      (row) =>
        /^(bg|border|ring|accent)-(indigo|emerald)-[567]00$/.test(row.source),
    );

    expect(graphical.length).toBe(14);
    for (const row of graphical) {
      expect(row.target, row.source).toMatch(/^(bg|border|ring|accent)-(primary|ring)/);
      expect(row.target).not.toContain("primary-text");
    }
  });

  it("measures the token AA-clean on all four text surfaces, and --primary not", () => {
    // Measured with `src/lib/contrast.ts` — the repository's single contrast
    // implementation, imported and never reimplemented — on the values the
    // compiled `index.css` actually resolves to.
    const text = sheet.colourOf("text-primary-text");
    const primary = sheet.colourOf("text-primary");
    const surfaces = {
      card: 5.2096,
      background: 5.0622,
      muted: 4.6547,
      accent: 4.6547,
    } as const;
    const before = { card: 3.4054, background: 3.3091, muted: 3.0427 } as const;

    for (const [surface, ratio] of Object.entries(surfaces)) {
      const measured = contrastRatio(text, sheet.colourOf(`bg-${surface}`));

      expect(measured, `--primary-text on --${surface}`).toBeCloseTo(ratio, 3);
      expect(measured).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
    }
    for (const [surface, ratio] of Object.entries(before)) {
      const measured = contrastRatio(primary, sheet.colourOf(`bg-${surface}`));

      expect(measured, `--primary on --${surface}`).toBeCloseTo(ratio, 3);
      expect(measured).toBeLessThan(MINIMUM_CONTRAST_RATIO);
    }
  });
});
