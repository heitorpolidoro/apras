/// <reference types="node" />
// @vitest-environment node
//
// This suite reads documents and does no rendering. The node environment is
// what makes `import.meta.url` a `file:` URL: under the project-wide jsdom
// default it is the dev server's `http:` URL and the documents outside
// `frontend/` cannot be located from it. `themeContrast.test.ts` and
// `themeTokenCompile.test.ts` are set up the same way.
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { contrastRatio, isInGamut, oklchToHex, parseOklch } from "../lib/contrast";

/**
 * Every colour figure a document publishes is re-derived from
 * `src/lib/contrast.ts` (APRAS-123).
 *
 * The defect this closes is not an arithmetic slip. Three agents in a row
 * computed `oklch()` to `#rrggbb` by clipping each sRGB channel into `[0, 1]`
 * instead of gamut-mapping as CSS Color 4 §13 requires, reported the result as
 * independently re-derived, and published it. A clip is not a rounding error:
 * it is a different colour, and it differs in the second decimal of a contrast
 * ratio, where no reader can see it. Independence of agent is not independence
 * of method, so the remedy is mechanical — the only way to write a colour
 * figure into this repository is to let `contrast.ts` produce it.
 *
 * Four properties make this a guard rather than a restatement of the palette:
 *
 * 1. **Nothing here converts.** `parseOklch`, `oklchToHex`, `contrastRatio`
 *    and `isInGamut` are imported from the one module permitted to produce a
 *    colour figure, and `describe("the guard adds no arithmetic of its own")`
 *    pins the import list so a second colour library cannot enter.
 * 2. **The subjects are found, never listed.** The scan walks the document set
 *    and matches syntactic shapes authors already write, so a document added
 *    later is guarded by existing.
 * 3. **It cannot pass vacuously.** `describe("the positive control")` asserts
 *    floors on documents read, documents contributing and claims checked, all
 *    measured against the *committed* tree, where untracked drafts do not
 *    exist.
 * 4. **The out-of-gamut inventory lives in one place.** The 19 rows are
 *    parsed out of `docs/frontend/contrast-provenance.md` and compared for set
 *    equality against `src/index.css`; this file holds no copy of them.
 */

/** The repository root, from `frontend/src/__tests__/`. */
const REPO_ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..", "..", "..");

/** The guarded document set: everything under these directories. */
const SCANNED_DIRECTORIES: ReadonlyArray<{
  readonly directory: string;
  readonly extensions: readonly string[];
}> = [
  { directory: join("docs", "tasks"), extensions: [".md", ".html"] },
  { directory: join("docs", "frontend"), extensions: [".md"] },
];

/**
 * Deliberately outside the scan, and why.
 *
 * `docs/reviews/**` and `docs/suggestions-log.md` are **records of a
 * conversation**: they quote wrong values precisely in order to condemn them.
 * `docs/reviews/APRAS-98-spec-review-round3.md` states, with an arrow
 * connector, that `oklch(0.62 0.15 160)` paints the clip value the finding was
 * written against — that sentence is the evidence, and guarding a review would
 * mean rewriting its evidence to keep CI green. The remaining three are
 * long-lived planning and vendored material that publishes no colour claim and
 * is not maintained against the stylesheet.
 */
const EXCLUDED_PATHS: readonly string[] = [
  "docs/reviews",
  "docs/suggestions-log.md",
  "docs/features_planning_and_questions.md",
  "docs/obras-fonte",
  "docs/superpowers",
];

/** The authoritative provenance document, and the only copy of the inventory. */
const PROVENANCE_DOCUMENT = "docs/frontend/contrast-provenance.md";

/** The stylesheet the inventory is measured against. */
const STYLESHEET = join("frontend", "src", "index.css");

/**
 * The sentinel pair, and the one inventory pair this file is allowed to carry
 * literally: `:root`'s `--primary` and `--ring` both hold it, and the
 * positive control has to count it by value.
 */
const SENTINEL_OKLCH = "oklch(0.62 0.15 160)";
const SENTINEL_HEX = "#009f68";

/** An emitted `oklch(L C H)`, as `parseOklch` accepts it. */
const OKLCH_SOURCE = String.raw`oklch\(\s*-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s*\)`;
/** A six-digit hex, in either case. */
const HEX_SOURCE = String.raw`#[0-9a-fA-F]{6}`;
/**
 * The equality connectors, and only these. `≠` is deliberately absent: a
 * document that must quote a wrong value writes it with `≠`, which is true
 * prose and mechanically inert. The hex-first direction is absent too — see
 * `extractClaims`.
 */
const CONNECTOR_SOURCE = String.raw`(?:==|=|→|->|≈)`;

/** Shape A, declaration first: `--ring: oklch(0.62 0.15 160); /* #009f68 *\/`. */
const SHAPE_A_DECLARATION_FIRST = new RegExp(
  String.raw`--[\w-]+\s*:\s*(${OKLCH_SOURCE})\s*;?\s*/\*\s*(${HEX_SOURCE})\s*\*/`,
  "g",
);
/** Shape A, gloss first: `--primary: #009f68; /* oklch(0.62 0.15 160) *\/`. */
const SHAPE_A_GLOSS_FIRST = new RegExp(
  String.raw`--[\w-]+\s*:\s*(${HEX_SOURCE})\s*;?\s*/\*\s*(${OKLCH_SOURCE})\s*\*/`,
  "g",
);
/** Shape B, the tuple row `docs/tasks/APRAS-76-mock.html` drives its table with. */
const SHAPE_B_TUPLE = new RegExp(
  String.raw`"--[\w-]+"\s*,\s*"(${OKLCH_SOURCE})"\s*,\s*"(${HEX_SOURCE})"`,
  "g",
);
/** Shape C, an equality connector, matched on flattened text. */
const SHAPE_C_CONNECTOR = new RegExp(
  String.raw`(${OKLCH_SOURCE})\s*${CONNECTOR_SOURCE}\s*(${HEX_SOURCE})`,
  "g",
);

/**
 * The one escape, and it is line-anchored: a line whose entire content,
 * ignoring only leading and trailing whitespace, is
 * `<!-- contrast-guard: ignore — reason -->` suppresses the next claim found
 * after it. Detection runs on the **raw** line, so an occurrence inside
 * backticks or with any prose beside it is documentation of the marker, not a
 * use of it. Documentation of either marker may therefore never place the
 * marker alone on a line.
 */
const ANCHORED_IGNORE_MARKER = /^<!--\s*contrast-guard:\s*ignore\s*—\s*\S.*?-->$/;
/**
 * The opt-in ratio marker, anchored identically. The anchor is deliberately
 * loose — anything that opens `<!-- ratio:` and closes `-->` on a line of its
 * own is a marker — so that a malformed one **fails** instead of being quietly
 * skipped. `parseOklch` returns `null` for anything it does not recognise and
 * the module then yields `NaN` silently, so a skip would let a typo disable
 * the check.
 */
const ANCHORED_RATIO_MARKER = /^<!--\s*ratio:(.*?)-->$/;
/** The body a well-formed ratio marker must carry, at exactly four decimals. */
const RATIO_MARKER_BODY = new RegExp(
  String.raw`^\s*(${OKLCH_SOURCE})\s+on\s+(${OKLCH_SOURCE})\s*=\s*(-?\d+\.\d{4})\s*$`,
);

/** The four decimals the ratio comparison is made on. */
const RATIO_DECIMALS = 4;

/** One published equivalence between an `oklch()` and the hex it paints. */
interface Claim {
  readonly file: string;
  readonly line: number;
  readonly oklch: string;
  readonly hex: string;
}

/** One anchored `<!-- ratio: … -->` marker, well-formed or not. */
interface RatioMarker {
  readonly file: string;
  readonly line: number;
  readonly body: string;
}

/** One anchored ignore marker. */
interface IgnoreMarker {
  readonly file: string;
  readonly line: number;
}

/** Every file under `directory` whose name ends in one of `extensions`. */
const collectFiles = (directory: string, extensions: readonly string[]): string[] => {
  const found: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const full = join(directory, entry.name);
    if (entry.isDirectory()) {
      found.push(...collectFiles(full, extensions));
      continue;
    }
    if (extensions.some((extension) => entry.name.endsWith(extension))) {
      found.push(full);
    }
  }
  return found;
};

/** A repository-relative path with forward slashes, whatever the platform. */
const repoPath = (absolute: string): string =>
  relative(REPO_ROOT, absolute).split(sep).join("/");

/**
 * The document as one string a cross-line match can run on, with a line
 * number for every character.
 *
 * HTML tags and the Markdown characters that interrupt a claim — backticks,
 * emphasis, table pipes — are removed, because
 * `docs/tasks/APRAS-68-mock.html:93` ends a line with `≈` and carries its hex
 * inside a `<code>` element on the next, and `docs/tasks/APRAS-87-spec.md:23`
 * writes its claim inside a Markdown table row.
 */
const flatten = (lines: readonly string[]): { text: string; lineOf: number[] } => {
  let text = "";
  const lineOf: number[] = [];
  lines.forEach((line, index) => {
    const sanitized = line.replace(/<[^>]*>/g, " ").replace(/[`*_|]/g, "");
    for (const character of sanitized) {
      text += character;
      lineOf.push(index + 1);
    }
    text += "\n";
    lineOf.push(index + 1);
  });
  return { text, lineOf };
};

/** Every match of `pattern`, as `[first group, second group]` pairs. */
const matchesOf = (pattern: RegExp, text: string): Array<[string, string]> => {
  pattern.lastIndex = 0;
  const pairs: Array<[string, string]> = [];
  let match = pattern.exec(text);
  while (match !== null) {
    pairs.push([match[1], match[2]]);
    match = pattern.exec(text);
  }
  return pairs;
};

/**
 * Every paint claim in one document.
 *
 * **The `oklch()` comes first in shape C, and the hex-first direction is not a
 * paint claim.** `oklch(…) → #rrggbb` says "this is the colour a browser
 * paints", which is exact. `#rrggbb → oklch(…)` says "this hex reads back as
 * roughly this OKLCH", a derivation through a 2dp-rounded emitted string that
 * legitimately lands one 8-bit step away: `docs/tasks/APRAS-68-spec.md:235`
 * publishes `#008a5a` as `oklch(0.56 0.13 160.15)`, whose round trip is a
 * neighbouring hex, and treating that as a mismatch would be the guard being
 * wrong about the document rather than the reverse.
 *
 * Connector anchoring is also the only thing that keeps two further lines out:
 * `docs/tasks/APRAS-68-spec.md:477` puts an unrelated `oklch()` and an
 * unrelated hex in one sentence, and `docs/tasks/APRAS-92-spec.md:717` has a
 * hex inside a "contains none of" assertion. A same-line "one oklch and one
 * hex" scan reports all four as mismatches, and all four are false.
 */
const extractClaims = (file: string, lines: readonly string[]): Claim[] => {
  const claims: Claim[] = [];
  lines.forEach((line, index) => {
    for (const [oklch, hex] of matchesOf(SHAPE_A_DECLARATION_FIRST, line)) {
      claims.push({ file, line: index + 1, oklch, hex });
    }
    for (const [hex, oklch] of matchesOf(SHAPE_A_GLOSS_FIRST, line)) {
      claims.push({ file, line: index + 1, oklch, hex });
    }
    for (const [oklch, hex] of matchesOf(SHAPE_B_TUPLE, line)) {
      claims.push({ file, line: index + 1, oklch, hex });
    }
  });

  const { text, lineOf } = flatten(lines);
  SHAPE_C_CONNECTOR.lastIndex = 0;
  let match = SHAPE_C_CONNECTOR.exec(text);
  while (match !== null) {
    claims.push({
      file,
      line: lineOf[match.index],
      oklch: match[1],
      hex: match[2],
    });
    match = SHAPE_C_CONNECTOR.exec(text);
  }

  return [...claims].sort((first, second) => first.line - second.line);
};

/** The two anchored markers in one document, detected on the raw line. */
const extractMarkers = (
  file: string,
  lines: readonly string[],
): { ignores: IgnoreMarker[]; ratios: RatioMarker[] } => {
  const ignores: IgnoreMarker[] = [];
  const ratios: RatioMarker[] = [];
  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (ANCHORED_IGNORE_MARKER.test(trimmed)) {
      ignores.push({ file, line: index + 1 });
    }
    const ratio = ANCHORED_RATIO_MARKER.exec(trimmed);
    if (ratio !== null) {
      ratios.push({ file, line: index + 1, body: ratio[1] });
    }
  });
  return { ignores, ratios };
};

/** Everything one walk of the document set produces. */
interface Scan {
  readonly files: readonly string[];
  readonly claims: readonly Claim[];
  readonly suppressed: readonly Claim[];
  readonly ignores: readonly IgnoreMarker[];
  readonly ratios: readonly RatioMarker[];
}

const scan = (): Scan => {
  const files: string[] = [];
  for (const { directory, extensions } of SCANNED_DIRECTORIES) {
    files.push(...collectFiles(join(REPO_ROOT, directory), extensions));
  }
  files.sort();

  const claims: Claim[] = [];
  const suppressed: Claim[] = [];
  const ignores: IgnoreMarker[] = [];
  const ratios: RatioMarker[] = [];

  for (const absolute of files) {
    const file = repoPath(absolute);
    const lines = readFileSync(absolute, "utf8").split("\n");
    const found = extractClaims(file, lines);
    const markers = extractMarkers(file, lines);
    ignores.push(...markers.ignores);
    ratios.push(...markers.ratios);

    // An anchored ignore marker suppresses the next claim after it, once.
    const silenced = new Set<number>();
    for (const marker of markers.ignores) {
      const next = found.findIndex(
        (claim, position) => claim.line > marker.line && !silenced.has(position),
      );
      if (next !== -1) {
        silenced.add(next);
      }
    }
    found.forEach((claim, position) => {
      if (silenced.has(position)) {
        suppressed.push(claim);
        return;
      }
      claims.push(claim);
    });
  }

  return { files: files.map(repoPath), claims, suppressed, ignores, ratios };
};

const SCAN = scan();

/** One row of the out-of-gamut inventory, flattened to a comparable string. */
const rowKey = (block: string, token: string, oklch: string, hex: string): string =>
  `${block} | ${token} | ${oklch} | ${hex}`;

/** A table cell with its padding and its Markdown backticks removed. */
const cellOf = (raw: string): string => raw.replace(/`/g, "").trim();

/** One side of the inventory comparison, plus whatever could not be read. */
interface Inventory {
  readonly rows: readonly string[];
  readonly problems: readonly string[];
}

/**
 * The inventory as the provenance document publishes it.
 *
 * The header row is what locates the table, and every row after it is
 * consumed until the table ends — so a row cannot be hidden from the parse by
 * malforming it. A row whose `oklch()` cell does not parse is a failure
 * naming the row, never a skip.
 */
const parsePublishedInventory = (lines: readonly string[]): Inventory => {
  const header = lines.findIndex(
    (line) => cellOf(line).replace(/\s+/g, " ") === "| block | token | oklch | hex |",
  );
  if (header === -1) {
    return {
      rows: [],
      problems: [
        `${PROVENANCE_DOCUMENT} carries no out-of-gamut inventory table: no "| block | token | oklch | hex |" header row was found, so the set equality would compare against nothing`,
      ],
    };
  }

  const rows: string[] = [];
  const problems: string[] = [];
  for (let index = header + 1; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line.startsWith("|")) {
      break;
    }
    if (/^\|[\s|:-]+\|$/.test(line)) {
      continue;
    }
    const cells = line.slice(1, -1).split("|").map(cellOf);
    if (cells.length !== 4) {
      problems.push(
        `${PROVENANCE_DOCUMENT}:${index + 1} is not a four-column inventory row: ${line}`,
      );
      continue;
    }
    const [block, token, oklch, hex] = cells;
    if (parseOklch(oklch) === null) {
      problems.push(
        `${PROVENANCE_DOCUMENT}:${index + 1} has an oklch cell "${oklch}" that parseOklch cannot read, so the row ${rowKey(block, token, oklch, hex)} could not be checked`,
      );
      continue;
    }
    rows.push(rowKey(block, token, oklch, hex));
  }
  return { rows: rows.sort(), problems };
};

/**
 * The inventory as `src/index.css` dictates it: every `--token: oklch(…)`
 * declaration for which `isInGamut` is false, painted with `oklchToHex`.
 *
 * The derivation is per-declaration and line-anchored, which the stylesheet
 * allows: there is no `oklch()` inside a gradient, a `color-mix()` or a
 * shorthand, and every one of them shares a line with its own `--token:`.
 * An occurrence that fails to parse fails the test rather than being skipped.
 */
const deriveStylesheetInventory = (lines: readonly string[]): Inventory => {
  const declaration = new RegExp(String.raw`(--[\w-]+)\s*:\s*(${OKLCH_SOURCE})`);
  const anyOklch = /oklch\(/;
  const rows: string[] = [];
  const problems: string[] = [];
  let block = "";
  lines.forEach((line, index) => {
    const selector = /^\s*([^{}]+?)\s*\{\s*$/.exec(line);
    if (selector !== null) {
      block = selector[1];
    }
    if (!anyOklch.test(line)) {
      return;
    }
    const match = declaration.exec(line);
    if (match === null) {
      problems.push(
        `${STYLESHEET}:${index + 1} carries an oklch() this guard cannot read as a "--token: oklch(L C H)" declaration, so it would be silently unmeasured: ${line.trim()}`,
      );
      return;
    }
    const colour = parseOklch(match[2]);
    if (colour === null) {
      problems.push(
        `${STYLESHEET}:${index + 1} declares ${match[1]} as "${match[2]}", which parseOklch cannot read`,
      );
      return;
    }
    if (isInGamut(colour)) {
      return;
    }
    rows.push(rowKey(block, match[1], match[2], oklchToHex(colour)));
  });
  return { rows: rows.sort(), problems };
};

describe("the colour claims published under docs/", () => {
  it("re-derives every published hex from its oklch with contrast.ts", () => {
    const mismatches = SCAN.claims.flatMap((claim) => {
      const colour = parseOklch(claim.oklch);
      if (colour === null) {
        return [
          `${claim.file}:${claim.line} publishes ${claim.hex} as the paint of ${claim.oklch}, which parseOklch cannot read`,
        ];
      }
      const derived = oklchToHex(colour);
      if (derived.toLowerCase() === claim.hex.toLowerCase()) {
        return [];
      }
      return [
        `${claim.file}:${claim.line} publishes ${claim.hex} as the paint of ${claim.oklch}, but contrast.ts derives ${derived}`,
      ];
    });
    expect(mismatches).toEqual([]);
  });

  it("does not read the hex-first derivation direction as a paint claim", () => {
    // `#008a5a → oklch(0.56 0.13 160.15)` round-trips to a neighbouring hex and
    // is legitimate; the same line read as a paint claim would be a false
    // mismatch. The two sentences that carry an unrelated oklch() and an
    // unrelated hex are kept out by connector anchoring alone.
    const notClaims = [
      "docs/tasks/APRAS-68-spec.md:235",
      "docs/tasks/APRAS-68-spec.md:477",
      "docs/tasks/APRAS-92-spec.md:717",
    ];
    const located = SCAN.claims.map((claim) => `${claim.file}:${claim.line}`);
    for (const line of notClaims) {
      expect(located, `${line} is not a colour claim and must not be scanned as one`).not.toContain(
        line,
      );
    }
    // The connector claim one line away in the same mock is found, and is
    // checked against the emitted oklch rather than against the brand input
    // hex that shares its line.
    const mock = SCAN.claims.filter(
      (claim) => claim.file === "docs/tasks/APRAS-68-mock.html" && claim.line === 93,
    );
    expect(mock).toHaveLength(1);
    expect(mock[0].oklch).toBe("oklch(0.68 0.14 237.32)");
    expect(mock[0].hex).not.toBe("#0ea5e9");
  });

  it("scans no document that an exclusion rule names", () => {
    const wrongly = SCAN.files.filter((file) =>
      EXCLUDED_PATHS.some((excluded) => file === excluded || file.startsWith(`${excluded}/`)),
    );
    expect(wrongly).toEqual([]);
  });
});

describe("the positive control", () => {
  // Floors, not measurements: they hold against the **committed** tree, where
  // untracked drafts do not exist. Measured at the landing commit: 126
  // documents read, 9 contributing, 20 claims. They may be raised, never
  // lowered, and a re-measurement that comes out below them is a defect to
  // investigate rather than a lower floor to assert.
  it("reads enough documents for a green run to mean something", () => {
    expect(SCAN.files.length).toBeGreaterThanOrEqual(100);
  });

  it("finds claims in enough documents", () => {
    const contributing = new Set(SCAN.claims.map((claim) => claim.file));
    expect(contributing.size).toBeGreaterThanOrEqual(8);
  });

  it("checks enough claims", () => {
    expect(SCAN.claims.length).toBeGreaterThanOrEqual(17);
  });

  it("finds the named sentinels, all of them committed", () => {
    const inFile = (file: string): number =>
      SCAN.claims.filter((claim) => claim.file === file).length;
    expect(inFile("docs/tasks/APRAS-90-mock.html")).toBeGreaterThanOrEqual(5);
    expect(inFile("docs/tasks/APRAS-76-mock.html")).toBeGreaterThanOrEqual(4);
    const sentinels = SCAN.claims.filter(
      (claim) =>
        claim.oklch === SENTINEL_OKLCH && claim.hex.toLowerCase() === SENTINEL_HEX,
    );
    expect(sentinels.length).toBeGreaterThanOrEqual(2);
  });
});

describe("the anchored markers", () => {
  it("suppresses nothing, and says so by exact list", () => {
    // An anchored ignore marker is the only escape from this guard. The list is
    // empty at landing, so the escape cannot spread without a visible diff.
    const located = SCAN.ignores.map((marker) => `${marker.file}:${marker.line}`);
    expect(located).toEqual([]);
    expect(SCAN.suppressed).toEqual([]);
  });

  it("re-derives every anchored ratio marker, and fails rather than skipping a malformed one", () => {
    const failures = SCAN.ratios.flatMap((marker) => {
      const at = `${marker.file}:${marker.line}`;
      const body = RATIO_MARKER_BODY.exec(marker.body);
      if (body === null) {
        return [
          `${at} is an anchored ratio marker whose body "${marker.body.trim()}" is not "oklch(L C H) on oklch(L C H) = N.NNNN" with exactly ${RATIO_DECIMALS} decimal digits`,
        ];
      }
      const first = parseOklch(body[1]);
      const second = parseOklch(body[2]);
      if (first === null || second === null) {
        return [
          `${at} is an anchored ratio marker whose operands "${body[1]}" and "${body[2]}" do not both parse, so contrastRatio would silently yield NaN`,
        ];
      }
      const derived = contrastRatio(first, second).toFixed(RATIO_DECIMALS);
      if (derived === body[3]) {
        return [];
      }
      return [
        `${at} publishes ${body[1]} on ${body[2]} at ${body[3]}, but contrast.ts derives ${derived}`,
      ];
    });
    expect(failures).toEqual([]);
    expect(SCAN.ratios.length).toBeGreaterThanOrEqual(4);
  });
});

describe("the out-of-gamut inventory", () => {
  // The document is the only authoritative copy, and this file holds none of
  // the rows: a token added, moved out of gamut or repainted fails until the
  // *document* is updated. Set equality is satisfied by two empty sets, so
  // both sides must carry at least the 19 rows measured at landing — a floor
  // on the parse, never the authority. The authority is `index.css` through
  // `isInGamut` and `oklchToHex`.
  const readLines = (path: string): string[] =>
    readFileSync(join(REPO_ROOT, path), "utf8").split("\n");
  const published = parsePublishedInventory(readLines(PROVENANCE_DOCUMENT));
  const derived = deriveStylesheetInventory(readLines(STYLESHEET));

  it("is read on both sides with no row silently skipped", () => {
    expect([...published.problems, ...derived.problems]).toEqual([]);
  });

  it("is parsed from the provenance document, not duplicated here", () => {
    expect(published.rows.length).toBeGreaterThanOrEqual(19);
    expect(derived.rows.length).toBeGreaterThanOrEqual(19);
  });

  it("agrees exactly with src/index.css", () => {
    const onlyInDocument = published.rows.filter((row) => !derived.rows.includes(row));
    const onlyInStylesheet = derived.rows.filter((row) => !published.rows.includes(row));
    expect({ onlyInDocument, onlyInStylesheet }).toEqual({
      onlyInDocument: [],
      onlyInStylesheet: [],
    });
  });
});

describe("the guard adds no arithmetic of its own", () => {
  // A self-scan for the WCAG luminance weights, the sRGB transfer constants,
  // the Ottosson matrix coefficients and the cube-root calls cannot work: an
  // assertion that names its needles and reads its own source finds its own
  // needles. Every way out of that — needles built by concatenation, excising
  // the declaration before scanning — is an unspecified device, and the net is
  // weak anyway: a weight written as a division passes it, and so does a
  // second colour library. No such literal is written anywhere in this file,
  // which is a property a reviewer confirms by reading it.
  //
  // The mechanism is an import pin instead. Any arithmetic this guard could
  // reimplement must either arrive as a fourth dependency, which the closed
  // set rejects, or be written inline — and inline arithmetic has no import to
  // hide behind, which is what code review looks for.
  const source = readFileSync(fileURLToPath(import.meta.url), "utf8");

  it("imports nothing outside the closed set, and imports contrast.ts", () => {
    const permitted = ["node:fs", "node:path", "node:url", "vitest", "../lib/contrast"];
    const importLine = /^[ \t]*import\b[^\n]*?from\s*["']([^"']+)["']/gm;
    const specifiers: string[] = [];
    let match = importLine.exec(source);
    while (match !== null) {
      specifiers.push(match[1]);
      match = importLine.exec(source);
    }
    expect(specifiers.filter((specifier) => !permitted.includes(specifier))).toEqual([]);
    expect(specifiers).toContain("../lib/contrast");
  });

  it("reaches no module dynamically, so the pin cannot be stepped around", () => {
    // The two patterns below are written as regex literals on purpose: a regex
    // literal's own source text is not what the pattern matches, because
    // `\s+` and `\(` do not match themselves. The assertion can therefore be
    // written literally, read its own source, and still pass on a correct
    // file — no excision, no concatenation, and no notion of comment-ness.
    expect(/await\s+import\s*\(/.test(source)).toBe(false);
    expect(/\brequire\s*\(/.test(source)).toBe(false);
  });
});
