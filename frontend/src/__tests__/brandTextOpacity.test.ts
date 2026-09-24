/// <reference types="node" />
// @vitest-environment node
//
// The brand-text-at-opacity guard (APRAS-90).
//
// Brand text painted at a fractional opacity over a brand tint composites to a
// colour nobody measured: the theme-token contract's row measures the *token*
// (`--primary-text` on `--accent`, 4.6547), while the pixels a person at the
// gate reads are the composite (3.2883 at `/80`, below AA). APRAS-80 could not
// repair it — §1i forbids a migration child from adding or removing a class —
// so it declared the failure instead. This task repaired it, and this file is
// what keeps it repaired.
//
// The guard is deliberately **ordering-independent**: it re-runs the sweep
// against the tree as it stands at run time rather than reading a frozen list
// of files or sites, so a sibling migration landing before or after this task
// changes nothing here, and a later commit that introduces such a class fails.
//
// Nothing below reimplements the measurement: `contrastRatio`, `parseOklch`
// and `compositeOver` come from `src/lib/contrast.ts`, the repository's single
// contrast implementation, and both colours are read out of `src/index.css`'s
// `:root` block — never out of `.dark`, never as a literal.
//
// The node environment is what makes `import.meta.url` a `file:` URL, exactly
// as `src/__tests__/themeTokenMigration.test.ts` needs it to be.
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  compositeOver,
  contrastRatio,
  parseOklch,
  MINIMUM_CONTRAST_RATIO,
  type Oklch,
} from "../lib/contrast";

/** Every ratio below is published to four decimals; assert to ±0.001. */
const DECIMALS = 3;
/** The alpha the repaired class carried, as `/80` means it. */
const DELETED_ALPHA = 0.8;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(HERE, "..", "..");
const SRC_ROOT = path.join(FRONTEND_ROOT, "src");

// --- the grammar -----------------------------------------------------------

/**
 * A brand **text** class carrying an opacity modifier.
 *
 * `text-primary-text` and `text-primary` are the two brand text tokens §1k
 * admits; `text-indigo-<scale>` is the pre-migration palette shape, matched so
 * that a directory the migration has not reached yet cannot introduce the same
 * defect under its old spelling. The boundaries are what keep
 * `text-primary-foreground` and `text-muted-foreground` out: `-` is excluded
 * on both sides, so only a `/` may follow the token name.
 *
 * Built fresh on every call because a `g` regex carries `lastIndex`.
 */
export const brandTextOpacityGrammar = (): RegExp =>
  new RegExp(
    String.raw`(?<![\w-])text-(?:primary-text|primary)\/(\d{1,3})(?![\w-])`,
    "g",
  );

/** The same shape under the un-migrated palette spelling. */
export const indigoTextOpacityGrammar = (): RegExp =>
  new RegExp(
    String.raw`(?<![\w-])text-indigo-(?:50|[1-9]00|950)\/(\d{1,3})(?![\w-])`,
    "g",
  );

/**
 * The brand-text-at-opacity class inside one whitespace-split token, or
 * `null`. The class is returned rather than the token so that the JSX
 * punctuation a token may carry (`text-primary-text/80">`) does not become
 * part of a site's name.
 */
const brandTextAtOpacity = (token: string): string | null =>
  brandTextOpacityGrammar().exec(token)?.[0] ??
  indigoTextOpacityGrammar().exec(token)?.[0] ??
  null;

/** Whether one whitespace-split class token is a brand-text-at-opacity class. */
const isBrandTextAtOpacity = (token: string): boolean =>
  brandTextAtOpacity(token) !== null;

// --- the sweep -------------------------------------------------------------

const isSwept = (name: string): boolean =>
  /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name);

/** Every swept source file under `src/`, excluding `__tests__/` directories. */
const sourceFiles = (directory: string = SRC_ROOT): string[] => {
  const found: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__") {
        found.push(...sourceFiles(full));
      }
      continue;
    }
    if (isSwept(entry.name)) {
      found.push(full);
    }
  }
  return found;
};

/** One site the sweep found, named the way the spec names sites. */
interface Site {
  site: string;
  class: string;
}

/**
 * Every brand-text-at-opacity site in the tree **as it stands right now**.
 *
 * Matched per whitespace-split token rather than by substring, so a longer
 * identifier that merely contains the text cannot register as a site.
 */
const sweep = (): Site[] => {
  const found: Site[] = [];
  for (const file of sourceFiles()) {
    const source = readFileSync(file, "utf8");
    source.split("\n").forEach((text, index) => {
      for (const token of text.split(/\s+/)) {
        const matched = brandTextAtOpacity(token);
        if (matched !== null) {
          found.push({
            site: `${path.relative(FRONTEND_ROOT, file)}:${index + 1}`,
            class: matched,
          });
        }
      }
    });
  }
  return found;
};

/**
 * The sites permitted to paint brand text at a fractional opacity.
 *
 * **Empty at this commit**, and an entry may only be added together with the
 * surface it paints on and the measured composite over that surface — which
 * the case below holds to `MINIMUM_CONTRAST_RATIO`. That is how the migration
 * contract's "leave the opacity alone where the composite still clears the
 * floor" survives without becoming a silent exemption.
 */
const PASSING_BRAND_TEXT_OPACITY: readonly {
  site: string;
  class: string;
  surface: string;
  ratio: number;
}[] = [];

// --- the token reader ------------------------------------------------------

const STYLESHEET = readFileSync(
  path.join(FRONTEND_ROOT, "src", "index.css"),
  "utf8",
);

/**
 * The `:root` block of `index.css`, and only it.
 *
 * Never `.dark`: the stylesheet declares `--primary` twice, and a last-wins
 * reader would silently measure the dark scheme. Sliced from the `:root {`
 * opener because `@custom-variant dark (&:is(.dark *))` carries the text
 * `.dark` before `:root` ever opens.
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

// --- the cases -------------------------------------------------------------

describe("the brand-text-at-opacity sweep", () => {
  it("finds no site anywhere in the tree as it stands", () => {
    // Re-run against the live tree, not against a recorded list: a sibling
    // migration landing before or after this task cannot falsify it, and a
    // later commit that introduces such a class fails here.
    expect(sweep().map((found) => `${found.site} ${found.class}`)).toEqual(
      PASSING_BRAND_TEXT_OPACITY.map(
        (entry) => `${entry.site} ${entry.class}`,
      ),
    );
  });

  it("permits a site only with its surface and a composite that clears AA", () => {
    for (const entry of PASSING_BRAND_TEXT_OPACITY) {
      expect(entry.surface.length).toBeGreaterThan(0);
      expect(entry.ratio).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
    }
    // The allow-list is empty at this commit; growing it is a visible,
    // reviewable act that must carry a measurement.
    expect(PASSING_BRAND_TEXT_OPACITY).toHaveLength(0);
  });

  it("reads enough of the tree to be capable of failing", () => {
    // A sweep that silently walked nothing would pass the case above for the
    // wrong reason.
    const files = sourceFiles();
    expect(files.length).toBeGreaterThan(20);
    expect(files.every((file) => isSwept(path.basename(file)))).toBe(true);
    expect(files.some((file) => file.includes(`${path.sep}__tests__`))).toBe(
      false,
    );
  });
});

describe("the grammar the sweep runs on", () => {
  it.each(["text-primary-text/80", "text-indigo-600/80"])(
    "matches %s",
    (candidate) => {
      expect(isBrandTextAtOpacity(candidate)).toBe(true);
    },
  );

  it.each([
    "text-primary-text",
    "text-primary-foreground",
    "text-primary",
    "text-foreground",
    "bg-primary/10",
    "text-muted-foreground/80",
  ])("does not match %s", (candidate) => {
    expect(isBrandTextAtOpacity(candidate)).toBe(false);
  });
});

describe("the pair this task replaced, measured", () => {
  it("measures the deleted composite at 3.2883, below the floor", () => {
    // `--primary-text` at alpha 0.8 over `--accent`, measured against
    // `--accent` — the pixels the gatehouse counter label used to paint.
    const composited = compositeOver(
      token("primary-text"),
      token("accent"),
      DELETED_ALPHA,
    );
    const ratio = contrastRatio(composited, token("accent"));

    expect(ratio).toBeCloseTo(3.2883, DECIMALS);
    expect(ratio).toBeLessThan(MINIMUM_CONTRAST_RATIO);
  });

  it("measures the replacement at 17.7626, at or above the floor", () => {
    // Solid `--foreground` on `--accent` — the counter label after this task.
    const ratio = contrastRatio(token("foreground"), token("accent"));

    expect(ratio).toBeCloseTo(17.7626, DECIMALS);
    expect(ratio).toBeGreaterThanOrEqual(MINIMUM_CONTRAST_RATIO);
  });
});
