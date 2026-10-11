/// <reference types="node" />
// @vitest-environment node
//
// APRAS-125 — the `dark:`-gated paint tokens reach Tailwind, not just the
// class list.
//
// **The hole this fills.** APRAS-110's `TenantHeaderLogo.test.tsx` asserts the
// logo plate's class list *equals* five tokens, in a light render and inside a
// `.dark` ancestor. That is a strong assertion and it still cannot do the job:
// replacing the literal with an assembled token — `` `dark:bg-${"foreground"}`
// `` — keeps the class list identical while generating **no CSS**, because
// Tailwind v4 finds utilities by scanning **source text** and an assembled
// token never appears there. jsdom runs no Tailwind, so no render test in this
// repository can tell the two apart.
//
// **Why the obvious guard does not work.** "Compile `index.css` and assert the
// rule is in the sheet" was tried in APRAS-110 and defeats itself: the test
// file's own literal is inside Tailwind's scanned set, so the rule survives
// even when the component assembles its token. The guard would pass on exactly
// the mutant it exists to kill.
//
// **The repair: this suite never lets Tailwind scan anything.**
// `compiler.build(candidates)` takes its candidate list as an argument and
// reads no filesystem candidates, so the "scanned set" is this suite's own
// construction. Two compiles over **disjoint** candidate sets:
//
//   - Compile A, the fixture compile — a literal array declared below. It is
//     the positive control on the harness and the carrier of the negative
//     controls and the sentinel. It says nothing about any component.
//   - Compile B, the scanned compile — exactly the tokens the extractor found
//     in the shipped sources. The test file is not in the scanned file list
//     and Compile A's array is never merged in.
//
// This is deliberately **stricter than the production build**, which lets
// Tailwind auto-scan the whole project, test files included, and is for that
// reason blind to the mutant. That asymmetry is the point.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import {
  compileIndexCss,
  declarationsDeep,
  escape,
  rulesDeep,
  SRC,
  type Rule,
} from "./helpers/tailwindSheet";

/** Compile A's candidates. Every one of these lives **only** here; none is
 *  ever merged into the scanned candidate list. */
const FIXTURE_CANDIDATES: readonly string[] = [
  "dark:bg-foreground",
  "dark:text-sm",
  "dark:bg-[url('/x.png')]",
  "dark:bg-nosuchcolour",
  "dark:bg-fuchsia-300",
  "bg-foreground",
];

// --- the family alternation and the paint it must produce ------------------
//
// These two **must move together**: widening the guard to another `dark:`
// family costs one branch of the alternation and one entry of the property
// map, and nothing else. They are written adjacent so that cost is visible —
// an understated extension cost is how a guard stops being extended.
//
// `bg-*` and `text-*` only, deliberately (§3): a missing `dark:bg-*` or
// `dark:text-*` is silently invisible, since the element inherits and still
// renders, and they are the two families `docs/frontend/theme-token-mapping.md`
// §1b–1e migrates. The 14 `dark:border-*` / `dark:divide-*` classes in the
// tree are all palette values with no theme-token call site to protect.
// `divide-*` would additionally need the matcher to admit a
// `:where(… > :not(:last-child))` selector.
const TOKEN = /dark:(?:[a-z-]+:)*(?:bg|text)-[A-Za-z0-9][A-Za-z0-9./_-]*/g;

const PAINT: Readonly<Record<string, string>> = {
  bg: "background-color",
  text: "color",
};

/** The utility at the end of `token`, past every stacked variant. */
const utilityOf = (token: string): string =>
  token.slice(token.lastIndexOf(":") + 1);

/** The property `token` must declare: `background-color` or `color`. */
const paintOf = (token: string): string => {
  const family = utilityOf(token).split("-")[0];
  const property = PAINT[family];
  if (property === undefined) {
    throw new Error(`no paint property for the ${family}-* family`);
  }
  return property;
};

/** What the checker concluded about one token. Four outcomes rather than a
 *  boolean, so the negative controls can assert *why* a rejection happened
 *  and a checker that collapsed them would be caught. */
type Verdict = "painted" | "no-rule" | "not-gated" | "wrong-property";

/**
 * Whether `token` compiles to a dark-gated rule that really paints.
 *
 * **The gate and the paint must come from the same rule.** A token's matched
 * set can hold several rules, and a checker that took the gate from one and
 * the paint from another would accept a token that is gated but unpainted in
 * the dark, or painted but ungated. Hence the `.filter()` to the gated rules
 * before any declaration is read.
 *
 * `startsWith` rather than equality on the gate, because a stacked token's
 * selector continues past it:
 * `.dark\:hover\:bg-white\/10:is(.dark *):hover`.
 */
const verdict = (sheet: readonly Rule[], token: string): Verdict => {
  const selector = `.${escape(token)}`;
  const matched = sheet.filter(
    (rule) =>
      rule.selector === selector || rule.selector.startsWith(`${selector}:`),
  );
  if (matched.length === 0) {
    return "no-rule";
  }
  const gated = matched.filter((rule) =>
    rule.selector.startsWith(`${selector}:is(.dark *)`),
  );
  if (gated.length === 0) {
    return "not-gated";
  }
  const property = paintOf(token);
  const painted = gated.some((rule) =>
    declarationsDeep(rule.body).some(
      ([name, value]) => name === property && value.trim().length > 0,
    ),
  );
  return painted ? "painted" : "wrong-property";
};

/** {@link verdict} over a whole token list, loud when the list is empty. */
const verdicts = (
  sheet: readonly Rule[],
  tokens: readonly string[],
): Map<string, Verdict> => {
  if (tokens.length === 0) {
    throw new Error("no tokens to check: the extractor found nothing");
  }
  return new Map(tokens.map((token) => [token, verdict(sheet, token)]));
};

// --- the scanned set and the extractor -------------------------------------

/** A path this guard must never scan, so no literal written for a test's own
 *  benefit can prop up a rule the shipped sources no longer earn. The `test`
 *  segment is what excludes `src/test/setup.ts`; `__tests__` is what excludes
 *  both `src/__tests__/**` — this file and its helper included — and every
 *  co-located feature test directory. */
const EXCLUDED =
  /(^|\/)(__tests__|test|__mocks__|__fixtures__)\/|\.(test|spec)\.[^/]+$|\.stories\.tsx$|\.d\.ts$/;

const SCANNABLE = /\.(ts|tsx|css)$/;

/**
 * Whether `file`, a path relative to `src`, is a shipped source to scan.
 *
 * Named rather than inlined into the filter below so the cases can assert it
 * against a **hand-written table of paths** (`SCANNER_EXPECTATIONS`). The
 * first round of this suite asserted `SCANNED_FILES` against `EXCLUDED`
 * itself — a list compared with the very filter that produced it, which
 * cannot fail for a wrong exclusion set. Every arm of `EXCLUDED` was
 * deletable with the whole suite green.
 */
const isScanned = (file: string): boolean =>
  SCANNABLE.test(file) && !EXCLUDED.test(file);

/** Every shipped source file under `src`, as a path relative to `src`.
 *  `readdirSync(…, { recursive: true })` rather than a new dependency. */
const SCANNED_FILES: readonly string[] = readdirSync(SRC, { recursive: true })
  .map((entry) => String(entry).split(path.sep).join("/"))
  .filter(
    (file) => isScanned(file) && statSync(path.join(SRC, file)).isFile(),
  )
  .sort();

/** token → the scanned files it was found in, sorted. */
const PROVENANCE: ReadonlyMap<string, readonly string[]> = (() => {
  const found = new Map<string, string[]>();
  for (const file of SCANNED_FILES) {
    const text = readFileSync(path.join(SRC, file), "utf8");
    for (const match of text.matchAll(TOKEN)) {
      const seen = found.get(match[0]) ?? [];
      if (!seen.includes(file)) {
        seen.push(file);
      }
      found.set(match[0], seen);
    }
  }
  return new Map(
    [...found].map(([token, files]) => [token, [...files].sort()]),
  );
})();

/** Compile B's candidates: exactly what the extractor found. */
const TOKENS: readonly string[] = [...PROVENANCE.keys()].sort();

/**
 * The literals that must be present *and* compile, with the file each must be
 * found in.
 *
 * This table is what makes the assembled-token mutant red. The mutant removes
 * the token's text from the shipped sources, so the extractor stops finding it
 * — without this table the mutant would merely shrink the candidate list by
 * one and nothing would notice.
 */
const REQUIRED_LITERALS: Readonly<Record<string, string>> = {
  "dark:bg-foreground":
    "features/user-administration/components/TenantHeaderLogo.tsx",
};

/**
 * Hand-written expectations for {@link isScanned}: the oracle is stated
 * intent, never a constant the scanner also reads.
 *
 * One entry per arm of `EXCLUDED` and per half of `SCANNABLE`, so deleting any
 * arm turns a case red; plus **near-miss keepers**, so the table cannot be
 * satisfied by an exclusion that swallows everything, and so an arm that
 * widened from a path *segment* to a bare substring (`latest.ts`,
 * `spectrum.ts`) is caught too. Synthetic paths are fine here and necessary:
 * `src` holds no `__mocks__`, no `__fixtures__`, no `*.stories.tsx` and no
 * `*.d.ts` today, so those four arms have no real file to name and would
 * otherwise be asserted by nothing at all.
 */
const SCANNER_EXPECTATIONS: ReadonlyArray<readonly [string, boolean, string]> =
  [
    // --- must be excluded, one per arm ---
    ["__tests__/App.test.tsx", false, "__tests__ segment"],
    [
      "__tests__/helpers/tailwindSheet.ts",
      false,
      "__tests__ segment, with no .test. in the basename",
    ],
    [
      "features/user-administration/__tests__/TenantHeaderLogo.test.tsx",
      false,
      "a co-located feature test directory",
    ],
    ["test/setup.ts", false, "the `test` segment"],
    ["lib/focusTrap.test.ts", false, ".test. basename outside any __tests__"],
    ["lib/focusTrap.spec.tsx", false, ".spec. basename"],
    ["api/__mocks__/client.ts", false, "__mocks__ segment"],
    ["lib/__fixtures__/palette.ts", false, "__fixtures__ segment"],
    ["components/ui/button.stories.tsx", false, ".stories.tsx"],
    ["vite-env.d.ts", false, ".d.ts"],
    ["lib/schema.d.ts", false, ".d.ts, nested"],
    ["lib/palette.json", false, "not a scannable extension"],
    ["assets/logo.svg", false, "not a scannable extension"],
    // --- must be kept, including the near misses ---
    ["index.css", true, "the stylesheet the guard compiles"],
    [
      "features/user-administration/components/TenantHeaderLogo.tsx",
      true,
      "the component APRAS-110 shipped",
    ],
    ["lib/contrast.ts", true, "an ordinary module"],
    ["lib/latest.ts", true, "contains `test`, but not as a path segment"],
    ["lib/spectrum.ts", true, "contains `spec`, but not as `.spec.`"],
    ["lib/stories.tsx", true, "named stories.tsx, but not `*.stories.tsx`"],
    ["lib/schema.ts", true, "a .ts that is not a .d.ts"],
    ["testing/helpers.ts", true, "a `testing` segment is not a `test` one"],
  ];

/**
 * Files that **do** carry a matching token and must still reach neither the
 * scanned set nor any token's provenance.
 *
 * Each is asserted to exist and to really contain a token, because
 * `not.toContain("some/path")` passes just as happily for a path that was
 * renamed or that never had a token — which would be the same vacuity one
 * level down. `TenantHeaderLogo.test.tsx` is the one that matters: it is where
 * APRAS-110's defeat came from.
 */
const TOKEN_BEARING_AND_UNSCANNED: readonly string[] = [
  "__tests__/darkVariantCompile.test.ts",
  "__tests__/themeTokenMigration.test.ts",
  "features/user-administration/__tests__/TenantHeaderLogo.test.tsx",
];

/** Directory names that are themselves an excluded path segment. A directory
 *  so named legitimately contributes nothing to the scanned set, and this
 *  literal list is the only exception the coverage rule below admits. */
const EXCLUDED_DIRECTORY_NAMES: readonly string[] = [
  "__tests__",
  "test",
  "__mocks__",
  "__fixtures__",
];

/**
 * Immediate subdirectories of `src/<root>` that hold at least one file with a
 * scannable extension, judged from the **raw** listing.
 *
 * `EXCLUDED` is deliberately not consulted: this has to be an oracle
 * *independent* of the scanner, or the coverage assertion becomes another
 * restatement of the thing it checks. Only `SCANNABLE` and the literal
 * {@link EXCLUDED_DIRECTORY_NAMES} are applied.
 */
const sourceDirectories = (root: string): string[] =>
  readdirSync(path.join(SRC, root), { withFileTypes: true })
    .filter(
      (entry) =>
        entry.isDirectory() && !EXCLUDED_DIRECTORY_NAMES.includes(entry.name),
    )
    .map((entry) => (root === "" ? entry.name : `${root}/${entry.name}`))
    .filter((directory) =>
      readdirSync(path.join(SRC, directory), { recursive: true }).some(
        (entry) => SCANNABLE.test(String(entry)),
      ),
    );

let fixtureSheet: readonly Rule[];
let scannedSheet: readonly Rule[];

beforeAll(async () => {
  // Two compiles, two `compileIndexCss` calls, therefore two fresh
  // `compile()` instances. Never one compiler built twice.
  fixtureSheet = rulesDeep(await compileIndexCss(FIXTURE_CANDIDATES));
  scannedSheet = rulesDeep(await compileIndexCss(TOKENS));
});

describe("the harness, on the fixture compile", () => {
  it("resolves dark:bg-foreground to a gated rule carrying background-color", () => {
    // The exact selector holds on **both** installed Tailwinds: 4.3.3 emits it
    // as the rule's own selector, 4.2.4 as a nested `&:is(.dark *)` block that
    // the effective-selector reader resolves against its parent. So this pins
    // the selector without pinning either nesting shape.
    const gated = fixtureSheet.filter(
      (rule) => rule.selector === ".dark\\:bg-foreground:is(.dark *)",
    );
    expect(gated).toHaveLength(1);
    const paint = declarationsDeep(gated[0].body).filter(
      ([name]) => name === "background-color",
    );
    expect(paint).not.toHaveLength(0);
    expect(paint[0][1].trim().length).toBeGreaterThan(0);
  });

  it("escapes the colon a dark: token carries", () => {
    expect(escape("dark:bg-foreground")).toBe("dark\\:bg-foreground");
  });

  it("reads both emission shapes to the same effective selector", () => {
    // Only one Tailwind is installed at a time, so the cross-version contract
    // is pinned here on the two literal shapes rather than left to whichever
    // package happens to be on disk: 4.2.4 nests the variant, 4.3.3 flattens
    // it into the parent selector. A reader that matched a selector *equal*
    // to `"." + escape(token)` would match every token on 4.2.4 and none on
    // 4.3.3 — green on a developer tree and red in CI.
    const nested =
      ".dark\\:bg-foreground { &:is(.dark *) { background-color: var(--x); } }";
    const flat =
      ".dark\\:bg-foreground:is(.dark *) { background-color: var(--x); }";
    for (const shape of [nested, flat]) {
      const gated = rulesDeep(shape).filter(
        (rule) => rule.selector === ".dark\\:bg-foreground:is(.dark *)",
      );
      expect(gated, shape).toHaveLength(1);
      expect(declarationsDeep(gated[0].body)).toContainEqual([
        "background-color",
        "var(--x)",
      ]);
    }
  });

  it("joins a nested selector with no & to its parent as a descendant", () => {
    // The other arm of the effective-selector resolution. No sheet Tailwind
    // emits here takes it, so it is asserted directly rather than left as the
    // one unexercised branch of the reader.
    expect(
      rulesDeep(".a { .b { color: red; } }").map((rule) => rule.selector),
    ).toStrictEqual([".a", ".a .b"]);
  });

  it("never reads a selector or a declaration out of a comment", () => {
    const css =
      "/* .dark\\:bg-foreground:is(.dark *) { background-color: red; } */" +
      ".other { color: blue; }";
    expect(
      rulesDeep(css).map((rule) => rule.selector),
    ).toStrictEqual([".other"]);
  });
});

// --- the negative controls -------------------------------------------------
//
// Naming every token in `it.each`, flooring the inputs and throwing on an
// empty list are **all** satisfied by a checker that returns `true`
// unconditionally: an earlier task in this repository shipped exactly that
// apparatus and it was shown to hold for a checker that decided nothing.
// Compile A is explicitly a *positive* control. So the guard
// asserts its own discriminating power here, at the one call site, over four
// candidates whose outcomes are each asserted individually.
describe("the checker can fail", () => {
  it("accepts dark:bg-foreground", () => {
    expect(verdict(fixtureSheet, "dark:bg-foreground")).toBe("painted");
  });

  it("rejects dark:text-sm, which emits font-size and no color", () => {
    // `text-*` is not purely a colour family. No such token exists in the
    // sources today, which is why it is a live control rather than a comment.
    expect(verdict(fixtureSheet, "dark:text-sm")).toBe("wrong-property");
  });

  it("rejects dark:bg-[url('/x.png')], which emits background-image", () => {
    expect(verdict(fixtureSheet, "dark:bg-[url('/x.png')]")).toBe(
      "wrong-property",
    );
  });

  it("rejects dark:bg-nosuchcolour, for which Tailwind emits no rule", () => {
    expect(verdict(fixtureSheet, "dark:bg-nosuchcolour")).toBe("no-rule");
  });

  it("rejects an ungated bg-foreground, which paints in both schemes", () => {
    // The other half of the per-token assertion, which no `dark:` candidate
    // can exercise: every token in the tree today *is* gated, so without this
    // control the gate filter could be deleted and all 59 cases would stay
    // green. `bg-foreground` compiles to a real `background-color` and is
    // rejected only because no `.dark` ancestor conditions it.
    expect(verdict(fixtureSheet, "bg-foreground")).toBe("not-gated");
  });

  it("never takes the gate from one rule and the paint from another", () => {
    // A token's matched set can hold several rules. A checker that read the
    // gate from one and the paint from another would accept a token that is
    // gated but unpainted in the dark — exactly the sheet below, where the
    // paint is unconditional and the gated rule carries no `background-color`.
    // No Tailwind output in this tree emits that pair, so the sheet is written
    // by hand: without it the `.filter()` to the gated rules could be deleted
    // and all 59 per-token cases would stay green.
    const css =
      ".dark\\:bg-foreground { background-color: red; }" +
      ".dark\\:bg-foreground:is(.dark *) { background-image: none; }";
    expect(verdict(rulesDeep(css), "dark:bg-foreground")).toBe(
      "wrong-property",
    );
  });

  it("throws on an empty token list", () => {
    // `it.each` over an empty array registers no cases and a suite with no
    // cases is green, so an extractor that found nothing must be loud.
    expect(() => verdicts(fixtureSheet, [])).toThrow(/no tokens/);
  });
});

// --- the scanned compile ---------------------------------------------------

describe("the scanned file list", () => {
  it.each(SCANNER_EXPECTATIONS)(
    "%s is scanned: %s — %s",
    (file, expected) => {
      // The oracle is this literal table, not `EXCLUDED`. Asserting
      // `SCANNED_FILES` against `EXCLUDED` compares a list with its own
      // filter: every arm was deletable with the suite green.
      expect(isScanned(file)).toBe(expected);
    },
  );

  it("excludes the real test, helper and setup paths on disk", () => {
    // The wiring, as opposed to the predicate: these paths exist, carry a
    // scannable extension, and are still absent from the scanned set.
    for (const [file, expected] of SCANNER_EXPECTATIONS) {
      if (!existsSync(path.join(SRC, file))) {
        continue;
      }
      expect(SCANNABLE.test(file), `${file} is not scannable at all`).toBe(
        true,
      );
      expect(SCANNED_FILES.includes(file), `${file}`).toBe(expected);
    }
    // And the two the reviewer set as the minimum bar, named outright.
    expect(SCANNED_FILES).not.toContain("test/setup.ts");
    expect(SCANNED_FILES).not.toContain("__tests__/darkVariantCompile.test.ts");
    expect(SCANNED_FILES).toContain("index.css");
  });

  it.each([[""], ["features"]])(
    "scans every source directory under src/%s",
    (root) => {
      // The complement of the exclusion assertions above, and the one thing
      // they cannot see. An exclusion set that **widens** is caught by
      // `SCANNER_EXPECTATIONS`; an exclusion set that **swallows** a whole
      // token-bearing directory is not. Adding `|^features\/lot-management\//`
      // removes 14 of the 59 guarded tokens and leaves 265 scanned files —
      // still over the 200 floor, so every other case stays green.
      //
      // A bare floor on the token count would only half-close this: it catches
      // swallowing `lot-management` (59 → 45) but not swallowing
      // `features/dashboard` (59 → 51). Directory coverage catches both, and
      // needs no threshold to be revisited as the palette→token migration
      // keeps deleting `dark:text-slate-*` classes.
      for (const directory of sourceDirectories(root)) {
        expect(
          SCANNED_FILES.filter((file) => file.startsWith(`${directory}/`)),
          `nothing under ${directory} reaches the scanned set`,
        ).not.toHaveLength(0);
      }
      // So the loop above cannot be green over an empty directory list.
      expect(sourceDirectories(root).length).toBeGreaterThanOrEqual(5);
    },
  );

  it("keeps the shared helper free of any paint-token literal", () => {
    // §6's requirement on `tailwindSheet.ts`, which until now was asserted by
    // nothing — and was in fact violated: a doc comment there named a stacked
    // token, so the helper carried a literal the extractor matches. Harmless
    // while the helper is excluded from the scan, and exactly the kind of
    // thing that stops being harmless when an exclusion arm is dropped.
    const helper = readFileSync(
      path.join(SRC, "__tests__", "helpers", "tailwindSheet.ts"),
      "utf8",
    );
    expect([...helper.matchAll(TOKEN)].map((match) => match[0])).toStrictEqual(
      [],
    );
  });

  it("keeps token-bearing test files out of every token's provenance", () => {
    // Asserted over *all* provenance rather than as "the provenance of
    // dark:bg-foreground is exactly TenantHeaderLogo.tsx", which would encode
    // an accident and redden for a second legitimate call site.
    const scanned = new Set(SCANNED_FILES);
    const seen = new Set([...PROVENANCE.values()].flat());
    for (const file of TOKEN_BEARING_AND_UNSCANNED) {
      const absolute = path.join(SRC, file);
      // Both halves, or the absence below proves nothing: the file is still
      // there, and it still carries a token the extractor would match.
      expect(existsSync(absolute), `${file} has moved`).toBe(true);
      expect(
        [...readFileSync(absolute, "utf8").matchAll(TOKEN)].length,
        `${file} no longer carries a token`,
      ).toBeGreaterThan(0);
      expect(scanned.has(file), `${file} is in the scanned set`).toBe(false);
      expect(seen.has(file), `${file} is in some token's provenance`).toBe(
        false,
      );
    }
    for (const [token, file] of Object.entries(REQUIRED_LITERALS)) {
      expect(PROVENANCE.get(token) ?? []).toContain(file);
    }
  });
});

describe("the extracted token set", () => {
  it("clears the structural floors", () => {
    // Structural, not a bare count: dropping the stacked-variant group loses
    // exactly 8 tokens and dropping `text` loses 26, and both still clear any
    // count a palette→token migration would survive. These also survive that
    // migration, which keeps deleting `dark:text-slate-*` classes.
    expect(SCANNED_FILES.length).toBeGreaterThanOrEqual(200);
    expect(TOKENS.filter((token) => utilityOf(token).startsWith("bg-")).length)
      .toBeGreaterThanOrEqual(1);
    expect(
      TOKENS.filter((token) => utilityOf(token).startsWith("text-")).length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      TOKENS.filter((token) => token.split(":").length > 2).length,
    ).toBeGreaterThanOrEqual(1);
    expect(TOKENS).toContain("dark:bg-foreground");
  });

  it("never sees the fixture's sentinel in the scanned sheet", () => {
    // The mechanical proof of the disjointness this whole design rests on.
    // `dark:bg-fuchsia-300` is in Compile A's array and nowhere in `src`; one
    // `compile()` instance accumulates candidates across `build()` calls, so
    // the moment `compileIndexCss` caches anything this rule appears and this
    // case goes red.
    // First that the sentinel is a token Tailwind really compiles. Without
    // this half, a misspelled sentinel — `dark:bg-fuchsia-3000`, say — would
    // satisfy the `no-rule` below for the wrong reason entirely: not because
    // the two compiles are disjoint, but because it is not a utility at all.
    // That is the same self-referential vacuity as comparing `SCANNED_FILES`
    // with `EXCLUDED`, one level down.
    expect(verdict(fixtureSheet, "dark:bg-fuchsia-300")).toBe("painted");
    expect(verdict(scannedSheet, "dark:bg-fuchsia-300")).toBe("no-rule");
    expect(TOKENS).not.toContain("dark:bg-fuchsia-300");
  });
});

describe("every dark:-gated paint token in the shipped sources", () => {
  it.each(TOKENS)("%s compiles to a gated, painted rule", (token) => {
    expect(verdict(scannedSheet, token)).toBe("painted");
  });
});
