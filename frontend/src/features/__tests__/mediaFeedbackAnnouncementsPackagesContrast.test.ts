/// <reference types="node" />
// @vitest-environment node
//
// APRAS-84 — the contrast half of the media, feedback, announcements and
// packages token migration.
//
// Every foreground/background pair this task changes is re-measured here by
// **importing** `contrastRatio`, `parseOklch`, `hexToOklch`, `MEASURED_PAIRS`
// and `MINIMUM_CONTRAST_RATIO` from `src/lib/contrast.ts`. The arithmetic is
// never reimplemented — a verbatim copy of `compositeOver` was rejected in
// APRAS-87's review — and no token or palette value is written down: token
// values are read from `src/index.css`'s `:root` block, never `.dark`, which
// is unapplied, and palette values from Tailwind 4's own
// `node_modules/tailwindcss/theme.css`.
//
// **The one colour-literal exception**, and the only colour literals in this
// file, are the five tenant brands the zoom-slider risk table names and the
// `oklch()` strings `backend/app/core/branding.py`'s `build_theme` emits for
// each. Those are backend *output quoted as data*: they appear in neither
// stylesheet this file is otherwise required to read, and re-deriving them in
// TypeScript would be a second theme derivation, which APRAS-68 D-D forbids.
// The **product default is not among them** — it is the shipped theme rather
// than a `build_theme` output, so its three tokens are read from
// `src/index.css` exactly like every other token here.
//
// The node environment is what makes `import.meta.url` a `file:` URL, so the
// two stylesheets can be read from disk; `src/__tests__/themeContrast.test.ts`
// and the migration guard do the same, for the same reason.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  MEASURED_PAIRS,
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
const PRIMARY_FOREGROUND = token("primary-foreground");
const DESTRUCTIVE = token("destructive");
const WHITE = palette("white");

describe("the measurement is the repository's own", () => {
  // APRAS-78's, APRAS-80's, APRAS-83's and APRAS-88's published figures. If
  // these drift, `src/lib/contrast.ts` changed underneath this task and every
  // other number below is suspect.
  it.each([
    ["--primary-text on --card", token("primary-text"), CARD, 5.2096],
    ["--primary-text on --accent", token("primary-text"), ACCENT, 4.6547],
    ["--muted-foreground on --card", token("muted-foreground"), CARD, 5.2249],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--primary-foreground on --primary", PRIMARY_FOREGROUND, PRIMARY, 5.7588],
    ["--primary on --card", PRIMARY, CARD, 3.4054],
    ["--primary on --background", PRIMARY, BACKGROUND, 3.3091],
    ["--primary on --accent", PRIMARY, ACCENT, 3.0427],
  ])("reproduces %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
  });
});

describe("the tokens this task paints with", () => {
  it.each([
    ["--foreground on --card", token("foreground"), CARD, 19.8801],
    ["--muted-foreground on --card", token("muted-foreground"), CARD, 5.2249],
    ["--muted-foreground on --muted", token("muted-foreground"), MUTED, 4.6684],
    ["--primary-text on --card", token("primary-text"), CARD, 5.2096],
    ["--primary-text on --accent", token("primary-text"), ACCENT, 4.6547],
    ["--primary-foreground on --primary", PRIMARY_FOREGROUND, PRIMARY, 5.7588],
    [
      "--destructive-foreground on --destructive",
      token("destructive-foreground"),
      DESTRUCTIVE,
      4.5381,
    ],
    ["--destructive on --card", DESTRUCTIVE, CARD, 4.8073],
  ])("holds AA as text: %s", (_name, foreground, background, expected) => {
    expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
    expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it("leaves --destructive-foreground on --destructive as the tightest text pair", () => {
    // 4.5381, then `--primary-text` on `--accent` at 4.6547 and
    // `--muted-foreground` on `--muted` at 4.6684. No full-opacity text pair
    // this task produces falls below AA.
    const tightest = [
      ratio(token("destructive-foreground"), DESTRUCTIVE),
      ratio(token("primary-text"), ACCENT),
      ratio(token("muted-foreground"), MUTED),
    ];

    expect(tightest).toEqual([4.5381, 4.6547, 4.6684]);
    for (const measured of tightest) {
      expect(measured).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
    }
  });

  it.each([
    ["--primary on --card", PRIMARY, CARD, 3.4054],
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

describe("the text pairs APRAS-84 changes", () => {
  // Each row carries its *own* background before and after, because several
  // of these move surface as well as foreground.
  it.each([
    ["headings", palette("gray-900"), WHITE, token("foreground"), CARD, 17.7467, 19.8801],
    ["secondary, gray-500", palette("gray-500"), WHITE, token("muted-foreground"), CARD, 4.8357, 5.2249],
    ["secondary, slate-500", palette("slate-500"), WHITE, token("muted-foreground"), CARD, 4.7670, 5.2249],
    ["secondary, gray-600", palette("gray-600"), WHITE, token("muted-foreground"), CARD, 7.5608, 5.2249],
    ["secondary, slate-600", palette("slate-600"), WHITE, token("muted-foreground"), CARD, 7.5635, 5.2249],
    // A surface that migrates with its foreground.
    ["table head on bg-gray-50", palette("gray-500"), palette("gray-50"), token("muted-foreground"), MUTED, 4.6325, 4.6684],
    // The primary fills. White on `indigo-600` was already AA; white on
    // `emerald-600` was not, and the brand pair repairs it.
    ["primary button", WHITE, palette("indigo-600"), PRIMARY_FOREGROUND, PRIMARY, 6.4414, 5.7588],
    ["approve buttons", WHITE, palette("emerald-600"), PRIMARY_FOREGROUND, PRIMARY, 3.7194, 5.7588],
    ["confirm-reject button", WHITE, palette("red-600"), token("destructive-foreground"), DESTRUCTIVE, 4.8619, 4.5381],
    // §1k's two character sites.
    ["crop-adjust link", palette("indigo-600"), WHITE, token("primary-text"), CARD, 6.4414, 5.2096],
    ["\"Ver Detalhes\" control", palette("indigo-600"), palette("indigo-50"), token("primary-text"), ACCENT, 5.7621, 4.6547],
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

  it("repairs the two approve buttons, which failed AA before", () => {
    expect(ratio(WHITE, palette("emerald-600"))).toBeLessThan(
      MINIMUM_CONTRAST_RATIO,
    );
    expect(ratio(PRIMARY_FOREGROUND, PRIMARY)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it("repairs the twelve text-*-400 sites, which failed AA before", () => {
    // Eight `text-gray-400` and four `text-slate-400`, all of them secondary
    // text or glyphs on a card.
    expect(ratio(palette("gray-400"), CARD)).toBeCloseTo(2.6023, 3);
    expect(ratio(palette("slate-400"), CARD)).toBeCloseTo(2.6282, 3);
    for (const failing of [
      ratio(palette("gray-400"), CARD),
      ratio(palette("slate-400"), CARD),
    ]) {
      expect(failing).toBeLessThan(MINIMUM_CONTRAST_RATIO);
    }
    expect(ratio(token("muted-foreground"), CARD)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });
});

describe("the graphical pairs APRAS-84 changes", () => {
  // §1k routes a brand class on an element that paints no glyphs to
  // `--primary`, whose floor is 1.4.11's 3:1 and not 4.5:1.
  it.each([
    ["brand icons on a card", palette("indigo-600"), WHITE, PRIMARY, CARD, 6.4414, 3.4054],
    ["the Eye glyph on a card", palette("indigo-500"), WHITE, PRIMARY, CARD, 4.5587, 3.4054],
    ["the tile glyphs on a brand tint", palette("indigo-600"), palette("indigo-50"), PRIMARY, ACCENT, 5.7621, 3.0427],
    // `AnnouncementFormModal`'s `<Paperclip/>` and `NewFeedbackForm`'s
    // checkbox, both inside a `bg-gray-50` label. The spec's §1k table quotes
    // 5.7621 for this group, which is the `bg-indigo-50` tiles' before figure;
    // on the neutral `bg-gray-50` label the same glyph measures 6.1708. Both
    // land on the same `--accent`/`--muted` 3.0427 after.
    ["the inline glyph on a neutral fill", palette("indigo-600"), palette("gray-50"), PRIMARY, MUTED, 6.1708, 3.0427],
    ["the PDF glyph", palette("red-600"), WHITE, DESTRUCTIVE, CARD, 4.8619, 4.8073],
    ["the delete glyph on a card", palette("red-600"), WHITE, DESTRUCTIVE, CARD, 4.8619, 4.8073],
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

  it("measures the carousel's active dot against its own container", () => {
    // `MediaCarousel`'s active dot moves from `bg-indigo-600` to `bg-primary`
    // against the carousel's `bg-gray-100` → `--muted` container. When media
    // is present the dot sits over the image and the pair is unmeasurable, as
    // it is today. Graphical either way.
    expect(ratio(palette("indigo-600"), palette("gray-100"))).toBeCloseTo(
      5.8539,
      3,
    );
    expect(ratio(PRIMARY, MUTED)).toBeCloseTo(3.0427, 3);
    expect(ratio(PRIMARY, MUTED)).toBeGreaterThanOrEqual(
      GRAPHICAL_CONTRAST_RATIO,
    );
  });
});

describe("§7 — the zoom slider, the one design change this child carries", () => {
  // The operator's decision: the **track** carries the tenant's brand and the
  // **thumb** carries the token the theme declares legible against it. Both
  // halves are graphical — an `<input type="range">` paints no glyphs — so 3:1
  // is the floor for both, and both now clear it. The earlier draft left the
  // thumb on `accent-primary`, putting it on a track of exactly its own
  // colour (1.0000); the operator rejected that and chose the swap.

  it("repairs the track, which failed 1.4.11 before", () => {
    // `bg-slate-300` on `bg-slate-50` → `--primary` on `--muted`.
    expect(ratio(palette("slate-300"), palette("slate-50"))).toBeCloseTo(
      1.4181,
      3,
    );
    expect(ratio(palette("slate-300"), palette("slate-50"))).toBeLessThan(
      GRAPHICAL_CONTRAST_RATIO,
    );
    expect(ratio(PRIMARY, MUTED)).toBeCloseTo(3.0427, 3);
    expect(ratio(PRIMARY, MUTED)).toBeGreaterThanOrEqual(
      GRAPHICAL_CONTRAST_RATIO,
    );
  });

  it("improves the thumb, measured against its own track", () => {
    // `accent-indigo-600` on `bg-slate-300` → `--primary-foreground` on
    // `--primary`. It passed before and passes by more now.
    expect(ratio(palette("indigo-600"), palette("slate-300"))).toBeCloseTo(
      4.3394,
      3,
    );
    expect(ratio(PRIMARY_FOREGROUND, PRIMARY)).toBeCloseTo(5.7588, 3);
    expect(ratio(PRIMARY_FOREGROUND, PRIMARY)).toBeGreaterThanOrEqual(
      GRAPHICAL_CONTRAST_RATIO,
    );
  });

  it("measures what the rejected candidates would have given the thumb", () => {
    // Recorded so the decision is not re-litigated. `accent-primary` on a
    // `bg-primary` track is a colour on exactly itself.
    expect(ratio(PRIMARY, PRIMARY)).toBeCloseTo(1.0, 3);
    expect(ratio(PRIMARY, token("muted-foreground"))).toBeCloseTo(1.5343, 3);
    for (const rejected of [
      ratio(PRIMARY, PRIMARY),
      ratio(PRIMARY, token("muted-foreground")),
    ]) {
      expect(rejected).toBeLessThan(GRAPHICAL_CONTRAST_RATIO);
    }
    // The chosen pairing clears the floor on both halves, which no other
    // placement that keeps the control following the brand does.
    expect(ratio(PRIMARY, MUTED)).toBeGreaterThanOrEqual(
      GRAPHICAL_CONTRAST_RATIO,
    );
    expect(ratio(PRIMARY_FOREGROUND, PRIMARY)).toBeGreaterThanOrEqual(
      GRAPHICAL_CONTRAST_RATIO,
    );
  });

  it("is platform-guaranteed on the thumb and unguarded on the track", () => {
    // The two facts behind the thumb pair being *guaranteed* rather than a
    // measurement that happens to pass, both imported rather than written
    // down. The guarantee is delivered by a different mechanism in each
    // palette mode:
    //
    //   * **advanced** — `TenantService.validated_brand_theme`
    //     (`backend/app/services/tenant_service.py:646-657`, the only non-test
    //     caller of `audit_contrast`; `build_theme` itself never raises)
    //     audits every scheme against `MEASURED_PAIRS` and answers 422 with
    //     each failing pair's measured ratio, so a hand-authored palette whose
    //     thumb is illegible on its own track cannot be stored;
    //   * **simple** — that function returns before building anything whose
    //     mode is not advanced, so nothing is measured at request time. It is
    //     not needed: both sides of this pair come out of
    //     `derive_brand_surface`, whose `_pick_foreground` + `_repair_surface`
    //     walk moves the surface in 0.01 lightness steps until the pair clears
    //     4.5:1, and that loop's convergence over every emittable brand is
    //     swept by `test_the_brand_surface_lattice_never_fails_and_never_leaves_the_gamut`.
    //
    // The **track** has no equivalent: `--border`, `--input` and `--ring` are
    // outside `MEASURED_PAIRS` by APRAS-68's explicit decision, and no pair
    // involving `--primary` as a *surface* under a graphical floor is measured
    // anywhere. That is the accepted risk, recorded below.
    expect(
      MEASURED_PAIRS.some(
        ([foreground, background]) =>
          foreground === "primary-foreground" && background === "primary",
      ),
    ).toBe(true);
    expect(MINIMUM_CONTRAST_RATIO).toBe(4.5);
    for (const unmeasured of ["border", "input", "ring"]) {
      expect(
        MEASURED_PAIRS.some(
          ([foreground, background]) =>
            foreground === unmeasured || background === unmeasured,
        ),
      ).toBe(false);
    }
  });

  /**
   * The six themes — the product default plus the five tenant brands a
   * síndico could type.
   *
   * The five brands carry the `oklch()` strings `build_theme` emits for each,
   * quoted verbatim as data and never re-derived in TypeScript: this is the
   * one colour-literal exception this file permits, because they are backend
   * output rather than a value readable from either stylesheet. The
   * **product-default row carries no literal at all** — it is the shipped
   * theme, so its three tokens are read from `src/index.css`.
   */
  const THEMES: ReadonlyArray<{
    readonly name: string;
    readonly primary: Oklch;
    readonly primaryForeground: Oklch;
    readonly muted: Oklch;
    readonly track: number;
    readonly thumb: number;
    readonly trackPasses: boolean;
  }> = [
    {
      name: "the product default (the shipped theme, read from index.css)",
      primary: PRIMARY,
      primaryForeground: PRIMARY_FOREGROUND,
      muted: MUTED,
      track: 3.0427,
      thumb: 5.7588,
      trackPasses: true,
    },
    {
      name: "#059669 — a síndico types the green",
      primary: parseOklch("oklch(0.60 0.12 163.23)") as Oklch,
      primaryForeground: parseOklch("oklch(0.15 0.02 163.23)") as Oklch,
      muted: parseOklch("oklch(0.96 0.01 163.23)") as Oklch,
      track: 3.3246,
      thumb: 5.2705,
      trackPasses: true,
    },
    {
      name: "#dc2626",
      primary: parseOklch("oklch(0.58 0.22 27.33)") as Oklch,
      primaryForeground: parseOklch("oklch(0.98 0.00 0.00)") as Oklch,
      muted: parseOklch("oklch(0.96 0.01 27.33)") as Oklch,
      track: 4.2451,
      thumb: 4.5159,
      trackPasses: true,
    },
    {
      name: "#2563eb",
      primary: parseOklch("oklch(0.55 0.22 262.88)") as Oklch,
      primaryForeground: parseOklch("oklch(0.98 0.00 0.00)") as Oklch,
      muted: parseOklch("oklch(0.96 0.01 262.88)") as Oklch,
      track: 4.5361,
      thumb: 4.8098,
      trackPasses: true,
    },
    {
      name: "#7c3aed",
      primary: parseOklch("oklch(0.54 0.22 293.01)") as Oklch,
      primaryForeground: parseOklch("oklch(0.98 0.00 0.00)") as Oklch,
      muted: parseOklch("oklch(0.96 0.01 293.01)") as Oklch,
      track: 4.9895,
      thumb: 5.3007,
      trackPasses: true,
    },
    {
      name: "#facc15 — the pale brand, an expected and named failure",
      primary: parseOklch("oklch(0.86 0.17 91.94)") as Oklch,
      primaryForeground: parseOklch("oklch(0.15 0.02 91.94)") as Oklch,
      muted: parseOklch("oklch(0.96 0.01 91.94)") as Oklch,
      track: 1.3661,
      thumb: 12.8247,
      trackPasses: false,
    },
  ];

  it.each(THEMES)(
    "$name measures its track and thumb as the spec records",
    (theme) => {
      expect(ratio(theme.primary, theme.muted)).toBeCloseTo(theme.track, 3);
      expect(ratio(theme.primaryForeground, theme.primary)).toBeCloseTo(
        theme.thumb,
        3,
      );
    },
  );

  it("holds the thumb above AA in all six themes, which is more than it needs", () => {
    for (const theme of THEMES) {
      expect(ratio(theme.primaryForeground, theme.primary)).toBeGreaterThanOrEqual(
        MINIMUM_CONTRAST_RATIO,
      );
      expect(ratio(theme.primaryForeground, theme.primary)).toBeGreaterThanOrEqual(
        GRAPHICAL_CONTRAST_RATIO,
      );
    }
  });

  it("clears the track's 3:1 floor in five themes and fails it in the pale one", () => {
    // **The accepted, named risk.** `--primary` is re-derived per tenant, so
    // 3.0427 — which clears 3:1 by 0.0427 — is the default theme's figure and
    // not a guarantee. A pale-branded condominium ships an invisible track:
    // `#facc15` yields 1.3661, *worse than the 1.4181 the track has today*.
    //
    // Stated rather than guarded, because nothing in this repository can guard
    // it: no test can enumerate the brands tenants will type, `--border`,
    // `--input` and `--ring` are outside `MEASURED_PAIRS` by APRAS-68's own
    // decision, and adding a graphical floor to `build_theme`'s refusal
    // contract would start rejecting palettes that are stored and working
    // today. The operator accepted this knowingly; the tree-wide 1.4.11 repair
    // remains APRAS-90's.
    const passing = THEMES.filter(
      (theme) => ratio(theme.primary, theme.muted) >= GRAPHICAL_CONTRAST_RATIO,
    );
    const failing = THEMES.filter(
      (theme) => ratio(theme.primary, theme.muted) < GRAPHICAL_CONTRAST_RATIO,
    );

    expect(passing).toHaveLength(5);
    expect(failing).toHaveLength(1);
    expect(failing[0].name).toContain("#facc15");
    for (const theme of THEMES) {
      expect(
        ratio(theme.primary, theme.muted) >= GRAPHICAL_CONTRAST_RATIO,
      ).toBe(theme.trackPasses);
    }
    // The pale brand is worse than what the track has today, which is the
    // sharpest statement of the risk and is asserted rather than asserted-to.
    expect(failing[0].track).toBeLessThan(
      ratio(palette("slate-300"), palette("slate-50")),
    );
  });

  it("records the thumb against the panel the native widget overhangs", () => {
    // A browser paints the range thumb taller than the 4 px track, so a sliver
    // overhangs onto the panel. Recorded as a named observation and **not
    // repaired**: repairing it would mean adding a ring or a border class,
    // which §1i forbids — a class added, not swapped. For the three brands
    // whose `--primary-foreground` `build_theme` derives as the near-white
    // `oklch(0.98 0.00 0.00)`, the sliver blends into the panel and the thumb
    // reads as the shape the track cuts around it, still 4.5:1-separated from
    // the track it sits on.
    const againstPanel: ReadonlyArray<readonly [string, number]> = [
      ["the product default", 17.5222],
      ["#059669", 17.5221],
      ["#dc2626", 1.0638],
      ["#2563eb", 1.0603],
      ["#7c3aed", 1.0624],
      ["#facc15", 17.5198],
    ];

    for (const [name, expected] of againstPanel) {
      const theme = THEMES.find((candidate) => candidate.name.includes(name));

      expect(theme).toBeDefined();
      expect(
        ratio(
          (theme as (typeof THEMES)[number]).primaryForeground,
          (theme as (typeof THEMES)[number]).muted,
        ),
      ).toBeCloseTo(expected, 3);
    }
    // Strictly better than the rejected draft, which would have put the thumb
    // at 1.0000 on its own track in every theme.
    expect(ratio(PRIMARY, PRIMARY)).toBeCloseTo(1.0, 3);
  });
});

describe("every kept text foreground whose surface migrates still clears AA", () => {
  // A kept foreground can sit on a migrated background. None of these text
  // pairs crosses 4.5:1, so this migration converts no passing text pair into
  // a failing one.
  it.each([
    ["text-gray-800, was on bg-gray-50", palette("gray-800"), palette("gray-50"), MUTED, 14.0676, 13.1205],
    ["text-gray-800, was on bg-gray-100", palette("gray-800"), palette("gray-100"), MUTED, 13.3451, 13.1205],
    ["text-gray-800, was on bg-slate-50", palette("gray-800"), palette("slate-50"), MUTED, 14.0283, 13.1205],
    ["text-gray-700, was on bg-gray-100", palette("gray-700"), palette("gray-100"), MUTED, 9.3658, 9.2081],
    ["text-slate-700, was on bg-slate-200", palette("slate-700"), palette("slate-200"), MUTED, 8.3972, 9.2424],
  ])("%s", (_name, foreground, before, after, beforeRatio, afterRatio) => {
    expect(ratio(foreground, before)).toBeCloseTo(beforeRatio, 3);
    expect(ratio(foreground, after)).toBeCloseTo(afterRatio, 3);
    expect(ratio(foreground, after)).toBeGreaterThanOrEqual(
      MINIMUM_CONTRAST_RATIO,
    );
  });

  it.each([
    ["text-gray-800", palette("gray-800"), 14.6846],
    ["text-gray-700", palette("gray-700"), 10.3058],
    ["text-slate-700", palette("slate-700"), 10.3442],
    ["text-slate-800", palette("slate-800"), 14.6574],
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

describe("declared sub-AA or unmeasurable, and which are this task's", () => {
  /**
   * Every kept or migrated pair this task leaves below 4.5:1, each with its
   * measured before and after ratio and the floor that actually applies to
   * it. The list is explicit so that nothing below AA can pass unnamed.
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
      // The three `bg-indigo-50` tiles, the `bg-gray-50` label glyph, the
      // checkbox and the `hover:` edit glyph — six sites. Clears 1.4.11 by
      // 0.043; §1k routes them here deliberately and this is APRAS-68
      // behaviour predating APRAS-77.
      site: "graphical --primary on --accent/--muted, 6 sites",
      foreground: PRIMARY,
      background: ACCENT,
      before: 3.0427,
      after: 3.0427,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `FeedbackChannelPage`'s `<Filter/>`, `AnnouncementFormModal`'s
      // `<Plus/>` and `FeedbackHistoryList`'s `<Eye/>`.
      site: "graphical --primary on --card, 3 sites",
      foreground: PRIMARY,
      background: CARD,
      before: 3.4054,
      after: 3.4054,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `CommentThread`'s `<Trash2/>` hover glyph, whose host row's
      // `bg-gray-50` becomes `--muted`. Graphical, above 3. APRAS-88 §7
      // already records this pair as a named follow-up.
      site: "CommentThread.tsx's delete glyph, --destructive on --muted",
      foreground: DESTRUCTIVE,
      background: MUTED,
      before: 4.8073,
      after: 4.2953,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // `AvatarWithFallback`'s avatar fill, `bg-slate-200` on `bg-white` →
      // `--muted` on `--card`. It fails the 3:1 graphical floor **before**
      // this task as well as after. Its only §1b row is `bg-muted`, §1i
      // permits swapping a class but never adding or removing one, and no
      // operator decision names it, so it is migrated and logged. Ruled *not*
      // a swatch deliberately: §1h code 2's head clause is "a data-encoding
      // colour", and this fill is one constant neutral for every user,
      // encoding nothing. APRAS-90 owns the repair.
      site: "AvatarWithFallback.tsx's avatar fill, --muted on --card",
      foreground: MUTED,
      background: CARD,
      before: 1.2319,
      after: 1.1192,
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
      // `AnnouncementCard`'s read-receipt glyph, status set 12.
      site: "kept text-emerald-600 on --card",
      foreground: palette("emerald-600"),
      background: CARD,
      before: 3.7194,
      after: 3.7194,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // A *text* pair that fails AA today, kept verbatim inside status set 11.
      site: "kept text-white on bg-rose-500",
      foreground: WHITE,
      background: palette("rose-500"),
      before: 3.7327,
      after: 3.7327,
      floor: GRAPHICAL_CONTRAST_RATIO,
    },
    {
      // The other, inside status set 10.
      site: "kept text-white on bg-amber-500",
      foreground: WHITE,
      background: palette("amber-500"),
      before: 2.1452,
      after: 2.1452,
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
    // The two that move do so because their surface migrates; the rest are
    // inherited verbatim on a surface that does not move.
    expect(ratio(DESTRUCTIVE, CARD)).toBeCloseTo(4.8073, 3);
    expect(ratio(palette("slate-200"), WHITE)).toBeCloseTo(1.2319, 3);
    for (const entry of DECLARED) {
      if (
        !entry.site.startsWith("CommentThread") &&
        !entry.site.startsWith("AvatarWithFallback")
      ) {
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
    // task inherits and §1i forbids repairing in place. The avatar fill fails
    // the 3:1 floor before this task as well as after, which is why its
    // `before` is recorded and asserted above.
    const unrepaired = DECLARED.filter((entry) => entry.floor === 0);

    expect(unrepaired).toHaveLength(2);
    for (const entry of unrepaired) {
      expect(entry.before).toBeLessThan(GRAPHICAL_CONTRAST_RATIO);
      expect(entry.after).toBeLessThan(GRAPHICAL_CONTRAST_RATIO);
    }
    // Neither half of the zoom slider appears here: the chosen pairing
    // introduces no sub-floor pair in the default theme.
    for (const entry of DECLARED) {
      expect(entry.site).not.toContain("slider");
      expect(entry.site).not.toContain("AvatarCropEditor");
    }
  });

  it("clears AA at the kept status pairs the spec quotes above the floor", () => {
    for (const [foreground, background, expected] of [
      [palette("red-700"), palette("red-50"), 5.9842],
      [palette("red-700"), palette("red-100"), 5.3552],
      [palette("amber-700"), palette("amber-50"), 4.8611],
      [palette("amber-800"), palette("amber-100"), 6.4027],
      [palette("emerald-700"), palette("emerald-50"), 5.1582],
      [palette("emerald-800"), palette("emerald-50"), 7.2679],
      [palette("emerald-900"), palette("emerald-50"), 9.1968],
      [palette("gray-700"), palette("gray-50"), 9.8728],
    ] as ReadonlyArray<readonly [Oklch, Oklch, number]>) {
      expect(ratio(foreground, background)).toBeCloseTo(expected, 3);
      expect(ratio(foreground, background)).toBeGreaterThanOrEqual(
        MINIMUM_CONTRAST_RATIO,
      );
    }
  });
});
