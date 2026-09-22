import { describe, expect, it } from "vitest";
// The fixture is read as **text** rather than imported as a module: it lives
// in `backend/tests/data/`, outside this project's `tsconfig.app.json`
// `include`, and `?raw` is the one form that both `tsc -b` (through
// `vite/client`'s declaration) and Vitest resolve there. Copying it into
// `frontend/` would be the very duplication it exists to prevent.
import fixturesText from "../../../../backend/tests/data/contrast_fixtures.json?raw";
import {
  auditHexPalette,
  auditScheme,
  contrastRatio,
  formatOklch,
  hexToOklch,
  isInGamut,
  MEASURED_PAIRS,
  MINIMUM_CONTRAST_RATIO,
  oklchToHex,
  parseOklch,
  type Oklch,
} from "../contrast";

/**
 * The TypeScript half of a two-sided pin (APRAS-68 D-D).
 *
 * `backend/tests/data/contrast_fixtures.json` is the contract: neither
 * language may import the other, so both suites assert the same numbers
 * against the same file. `backend/tests/test_branding.py` holds the other
 * half.
 *
 * The out-of-gamut cases are the load-bearing ones. CSS Color 4 §13 has a
 * browser gamut-map an out-of-range `oklch()` by **chroma reduction** at
 * constant lightness and hue, never by per-channel clipping, so a port that
 * clips reads 4.52 where the fixture says 3.74 — it would certify a pair the
 * browser paints below AA. That is why this file ports the mapping and not
 * only the ratio.
 */

interface FixtureColour {
  hex?: string;
  oklch?: [number, number, number];
}

interface FixtureCase {
  name: string;
  a: FixtureColour;
  b: FixtureColour;
  ratio: number;
  in_gamut: [boolean, boolean];
}

interface Fixtures {
  minimum: number;
  tolerance: number;
  cases: FixtureCase[];
}

const fixtures = JSON.parse(fixturesText) as Fixtures;

const colourOf = (colour: FixtureColour): Oklch => {
  if (colour.hex !== undefined) {
    const parsed = hexToOklch(colour.hex);
    if (parsed === null) {
      throw new Error(`the fixture carries a malformed hex: ${colour.hex}`);
    }
    return parsed;
  }
  const [l, c, h] = colour.oklch as [number, number, number];
  return { l, c, h };
};

describe("contrast.ts against the shared fixture", () => {
  it("pins the same minimum the backend does", () => {
    expect(MINIMUM_CONTRAST_RATIO).toBe(fixtures.minimum);
  });

  it("has cases, so an empty fixture can never pass vacuously", () => {
    expect(fixtures.cases.length).toBeGreaterThan(0);
  });

  it.each(fixtures.cases.map((entry) => [entry.name, entry] as const))(
    "reproduces %s",
    (_name, entry) => {
      const a = colourOf(entry.a);
      const b = colourOf(entry.b);

      expect(contrastRatio(a, b)).toBeCloseTo(entry.ratio, 2);
      // Symmetric: the ratio orders the two luminances itself.
      expect(contrastRatio(b, a)).toBeCloseTo(entry.ratio, 2);
      expect([isInGamut(a), isInGamut(b)]).toEqual(entry.in_gamut);
    },
  );
});

describe("the luminance regression the fixture exists to catch", () => {
  it("reads the shipped muted pair at 4.29 and never at 10.96", () => {
    // A second sRGB→linear transfer does not halve this ratio, it inflates
    // it to 10.96 — which would make illegible palettes pass.
    const ratio = contrastRatio(
      { l: 0.55, c: 0.02, h: 160 },
      { l: 0.96, c: 0.01, h: 160 },
    );

    expect(ratio).toBeCloseTo(4.29, 2);
    expect(ratio).toBeLessThan(5);
  });
});

describe("parseOklch", () => {
  it("reads back what the backend emits", () => {
    expect(parseOklch("oklch(0.68 0.14 237.32)")).toEqual({
      l: 0.68,
      c: 0.14,
      h: 237.32,
    });
  });

  it("tolerates the surrounding whitespace a stylesheet may carry", () => {
    expect(parseOklch("  oklch( 0.15 0.02 237.32 )  ")).toEqual({
      l: 0.15,
      c: 0.02,
      h: 237.32,
    });
  });

  it("returns null for anything that is not an emitted oklch string", () => {
    expect(parseOklch("#ffe680")).toBeNull();
    expect(parseOklch("rgb(1 2 3)")).toBeNull();
    expect(parseOklch("oklch(0.5 0.1)")).toBeNull();
  });
});

describe("hexToOklch", () => {
  it("accepts either case, because the server is the normalisation point", () => {
    expect(hexToOklch("#FFE680")).toEqual(hexToOklch("#ffe680"));
  });

  it("returns null for a malformed value", () => {
    expect(hexToOklch("#GGG")).toBeNull();
    expect(hexToOklch("red")).toBeNull();
    expect(hexToOklch("#abc")).toBeNull();
  });

  it("round-trips a hex back through formatOklch's string", () => {
    const parsed = parseOklch(formatOklch(hexToOklch("#0ea5e9") as Oklch));

    expect(parsed).not.toBeNull();
    expect((parsed as Oklch).h).toBeCloseTo(237.32, 1);
  });
});

describe("oklchToHex", () => {
  it("round-trips an in-gamut hex back to itself", () => {
    for (const hex of ["#7c3aed", "#0ea5e9", "#857046", "#ffe680", "#10b981"]) {
      expect(oklchToHex(hexToOklch(hex) as Oklch)).toBe(hex);
    }
  });

  it("paints the two poles", () => {
    expect(oklchToHex({ l: 1, c: 0, h: 0 })).toBe("#ffffff");
    expect(oklchToHex({ l: 0, c: 0, h: 0 })).toBe("#000000");
  });

  it("paints an out-of-gamut triple as the chroma-reduced colour", () => {
    // Never a per-channel clip: the result must be inside sRGB and keep the
    // requested lightness and hue as closely as the JND allows.
    const painted = oklchToHex({ l: 0.52, c: 0.22, h: 210 });

    expect(painted).toMatch(/^#[0-9a-f]{6}$/);
    expect(isInGamut(hexToOklch(painted) as Oklch)).toBe(true);
  });
});

describe("auditScheme", () => {
  const scheme = (overrides: Record<string, string> = {}) => ({
    background: "oklch(0.99 0 0)",
    foreground: "oklch(0.14 0.01 160)",
    card: "oklch(1 0 0)",
    "card-foreground": "oklch(0.14 0.01 160)",
    primary: "oklch(0.55 0.06 83.88)",
    "primary-foreground": "oklch(0.98 0 0)",
    secondary: "oklch(0.68 0.14 237.32)",
    "secondary-foreground": "oklch(0.15 0.02 237.32)",
    accent: "oklch(0.96 0.01 237.32)",
    "accent-foreground": "oklch(0.2 0.02 237.32)",
    muted: "oklch(0.96 0.01 160)",
    "muted-foreground": "oklch(0.53 0.02 160)",
    border: "oklch(0.92 0.01 160)",
    ...overrides,
  });

  it("measures the eight documented pairs", () => {
    expect(MEASURED_PAIRS).toHaveLength(8);
    expect(MEASURED_PAIRS.filter(([text]) => text === "muted-foreground")).toHaveLength(
      3,
    );
  });

  it("returns nothing for a scheme every pair of which clears AA", () => {
    expect(auditScheme(scheme())).toEqual([]);
  });

  it("names the failing pair and its measured ratio", () => {
    const failures = auditScheme(
      scheme({ "primary-foreground": "oklch(0.56 0.06 83.88)" }),
    );

    expect(failures).toHaveLength(1);
    expect(failures[0].pair).toBe("primary-foreground/primary");
    expect(failures[0].ratio).toBeLessThan(MINIMUM_CONTRAST_RATIO);
    expect(failures[0].minimum).toBe(MINIMUM_CONTRAST_RATIO);
  });

  it("skips a pair it cannot parse rather than inventing a ratio", () => {
    expect(auditScheme(scheme({ primary: "not-a-colour" }))).toEqual([]);
  });

  it("skips a pair whose surface key is absent altogether", () => {
    const partial = scheme();
    delete (partial as Record<string, string>).muted;

    // Three of the eight pairs name `muted`; the other five still measure.
    expect(auditScheme(partial)).toEqual([]);
  });

  it("skips a pair whose text key is absent altogether", () => {
    const partial = scheme();
    delete (partial as Record<string, string>)["muted-foreground"];

    expect(auditScheme(partial)).toEqual([]);
  });
});

describe("auditHexPalette", () => {
  const readable = {
    background: "#fffdf7",
    foreground: "#1d1b16",
    card: "#ffffff",
    "card-foreground": "#1d1b16",
    primary: "#8a2b2b",
    "primary-foreground": "#fff7f5",
    secondary: "#1f6f8b",
    "secondary-foreground": "#ffffff",
    accent: "#e8ddc9",
    "accent-foreground": "#3a3128",
    muted: "#f1ece4",
    "muted-foreground": "#5c5344",
    border: "#e2d9c8",
  };

  it("returns nothing for the readable preset", () => {
    expect(auditHexPalette(readable)).toEqual([]);
  });

  it("names every pair of black text on a near-black background", () => {
    const failures = auditHexPalette({
      ...readable,
      background: "#121212",
      foreground: "#1a1a1a",
      card: "#151515",
      "card-foreground": "#1d1d1d",
    });

    expect(failures.map((failure) => failure.pair)).toContain(
      "foreground/background",
    );
    expect(failures.map((failure) => failure.pair)).toContain(
      "card-foreground/card",
    );
  });

  it("drops a malformed value rather than guessing at a colour", () => {
    expect(auditHexPalette({ ...readable, primary: "#GGG" })).toEqual([]);
  });
});

describe("the one-derivation rule (D-D)", () => {
  /** Every TypeScript source in the app, as text. `import.meta.glob` resolves
   *  at build time, so this cannot silently stop matching files. */
  const sources = import.meta.glob("/src/**/*.{ts,tsx}", {
    query: "?raw",
    import: "default",
    eager: true,
  }) as Record<string, string>;

  it("sees the whole tree, so the assertions below cannot pass vacuously", () => {
    expect(Object.keys(sources).length).toBeGreaterThan(100);
    expect(Object.keys(sources)).toContain("/src/lib/contrast.ts");
  });

  /** The file with its comments removed: naming `build_theme` in prose to say
   *  where the derivation lives is the opposite of porting it, so only code
   *  is scanned. */
  const codeOf = (text: string): string =>
    text.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/(^|[^:])\/\/.*$/gm, "$1");

  it("finds no theme derivation anywhere in TypeScript", () => {
    // `app/core/branding.build_theme` is the only derivation in the
    // repository. A port would have to assemble a scheme, and it cannot do
    // that without a function that says so.
    const markers = [
      "buildTheme",
      "build_theme",
      "deriveBrandSurface",
      "deriveScheme",
      "repairSurface",
      "repairText",
      "neutralFamily",
      "simpleScheme",
      "advancedScheme",
    ];
    const offenders = Object.entries(sources).filter(([, text]) =>
      markers.some((marker) => codeOf(text).includes(marker)),
    );

    expect(offenders.map(([path]) => path)).toEqual([]);
  });

  it("keeps contrast.ts to measurement, with no scheme assembly in it", () => {
    const code = codeOf(sources["/src/lib/contrast.ts"]);

    // The derivation's own vocabulary: the input clamp, the dark brand floor
    // and the repair bound. None of them belongs in a measurement.
    for (const forbidden of [
      "DARK_BRAND_MIN_LIGHTNESS",
      "INPUT_MAX_CHROMA",
      "INPUT_MIN_LIGHTNESS",
      "MAX_STEPS",
      "NEAR_BLACK",
    ]) {
      expect(code).not.toContain(forbidden);
    }
  });
});

describe("gamutMap", () => {
  it("bisects a chroma so far outside sRGB that the JND is never reached", () => {
    // Exercises the loop's exhaustion path: `high - low` closes before any
    // candidate lands within the just-noticeable difference.
    const painted = oklchToHex({ l: 0.5, c: 2, h: 300 });

    expect(painted).toMatch(/^#[0-9a-f]{6}$/);
    expect(isInGamut(hexToOklch(painted) as Oklch)).toBe(true);
  });
});
