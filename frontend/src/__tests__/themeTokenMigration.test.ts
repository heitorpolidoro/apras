/// <reference types="node" />
// @vitest-environment node
//
// The migration guard (APRAS-78, deliverable 3).
//
// A directory named in `MIGRATED_DIRECTORIES` has been through the class ->
// token migration described in `docs/frontend/theme-token-mapping.md`. From
// that moment on, no Tailwind palette class may reappear in it: the guard
// re-reads every file with `node:fs` and fails on any match of the §3b
// grammar that is not listed, as an exact `(file, class)` pair, in
// `themeTokenMigration.exceptions.json`.
//
// The node environment is what makes `import.meta.url` a `file:` URL — under
// the project-wide jsdom default it is the dev server's `http:` URL and the
// tree cannot be located from it. `src/__tests__/themeContrast.test.ts` does
// the same, for the same reason.
import { readFileSync, readdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * The directories whose palette classes have been migrated (§3a).
 *
 * Seeded with exactly one entry by APRAS-78; **each sibling appends exactly
 * one**. Paths are `src/`-relative and match non-recursively unless suffixed
 * with a `/**` recursion marker. APRAS-85 inverts the list into a repo-wide
 * deny by replacing it with the single recursive `src` entry and changes
 * nothing else here (§3d), which is why nothing below assumes an allow-list
 * shape.
 */
export const MIGRATED_DIRECTORIES: readonly string[] = [
  "src/components/ui",
  "src/features/lot-management/components",
  "src/features/visitor-management/components",
  // APRAS-82's operator-given scope is two directories, not one, so this
  // child appends two entries where its siblings appended one.
  "src/features/document-management/components",
  "src/features/occurrence-management/components",
  // APRAS-81's operator-given scope is two directories as well, so this child
  // also appends two entries where most siblings appended one.
  "src/features/project-management/components",
  "src/features/asset-management/components",
  // APRAS-83's operator-given scope is three directories, so this child
  // appends three entries where its siblings appended one or two.
  "src/features/finance/components",
  "src/features/purchase-management/components",
  "src/features/access-control/components",
  // APRAS-84's operator-given scope is four directories, so this child appends
  // four entries where its siblings appended one, two or three.
  "src/features/media-management/components",
  "src/features/feedback-management/components",
  "src/features/announcement-feed/components",
  "src/features/package-management/components",
];

/** The eight gap codes of §1h, in precedence order. Closed set: an entry
 *  carrying anything else fails, so hiding a migratable class requires
 *  editing the published table — a visible, reviewable act (§3c rule 1). */
export const GAP_CODES: readonly string[] = [
  "GAP-OVERLAY",
  "GAP-SWATCH",
  "GAP-NO-TOKEN",
  "GAP-TINT",
  "GAP-NO-SURFACE",
  "GAP-BORDER-100",
  "GAP-OUT-OF-BUDGET",
  "GAP-UNLISTED",
];

// --- §3b, the grammar, built from named parts rather than one literal ------

const VARIANTS = String.raw`(?:[a-z0-9][a-z0-9.\-]*(?:\[[^\]]*\])?:)*`;
const PREFIX = String.raw`(?:bg|text|border|ring|outline|divide|placeholder|caret|accent|decoration|shadow|fill|stroke|from|via|to)`;
const FAMILY = String.raw`(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)`;
// Longest-first, and this ordering is load-bearing: with `50` before `500`
// the engine matches `text-gray-50` inside `text-gray-500` and silently
// under-reports. Revision 1 of the spec counted the tree with the other
// order and was wrong by hundreds of occurrences.
const SCALE = String.raw`(?:950|900|800|700|600|500|400|300|200|100|50)`;
const OPACITY = String.raw`(?:/(?:[0-9]{1,3}|\[[^\]]*\]))?`;

/** The §3b `palette` production. The lookbehind and lookahead boundaries
 *  keep it from matching inside a longer identifier or compound class. */
export const paletteGrammar = (): RegExp =>
  new RegExp(
    String.raw`(?<![\w-])${VARIANTS}${PREFIX}-(?:${FAMILY}-${SCALE}|white|black)(?![\w-])${OPACITY}`,
    "g",
  );

/** The third pattern: a six-digit hex literal. Only a match inside a class
 *  context counts, so a hex in a chart palette or a comment is not a
 *  migration defect. */
export const hexGrammar = (): RegExp =>
  new RegExp(String.raw`#[0-9a-fA-F]{6}(?![0-9a-fA-F])`, "g");

const CONTEXT_KEYWORD = /\b(?:className|cva|cn)\b/g;
const OPENERS: Readonly<Record<string, string>> = {
  "{": "}",
  "(": ")",
  "[": "]",
};
const QUOTES = new Set(['"', "'", "`"]);

const endOfString = (source: string, start: number): number => {
  const quote = source[start];
  for (let index = start + 1; index < source.length; index += 1) {
    if (source[index] === "\\") {
      index += 1;
      continue;
    }
    if (source[index] === quote) {
      return index + 1;
    }
  }
  return source.length;
};

const endOfGroup = (source: string, start: number): number => {
  const stack: string[] = [];
  for (let index = start; index < source.length; index += 1) {
    const character = source[index];
    if (QUOTES.has(character)) {
      index = endOfString(source, index) - 1;
      continue;
    }
    if (character in OPENERS) {
      stack.push(OPENERS[character]);
      continue;
    }
    if (stack.length > 0 && character === stack[stack.length - 1]) {
      stack.pop();
      if (stack.length === 0) {
        return index + 1;
      }
    }
  }
  return source.length;
};

/**
 * The spans of `source` that are a class context — the argument of
 * `className=`, of `cva(` or of `cn(`.
 *
 * Written as a delimiter scanner rather than a regular expression because a
 * `className={cn("a", cond ? "b" : "c")}` argument nests, and a regex that
 * stopped at the first closing brace would miss most of it.
 */
export const classContexts = (
  source: string,
): ReadonlyArray<readonly [number, number]> => {
  const spans: Array<readonly [number, number]> = [];
  for (const keyword of source.matchAll(CONTEXT_KEYWORD)) {
    let index = (keyword.index ?? 0) + keyword[0].length;
    while (index < source.length && /[\s=:]/.test(source[index])) {
      index += 1;
    }
    const opener = source[index];
    if (QUOTES.has(opener)) {
      spans.push([index, endOfString(source, index)]);
      continue;
    }
    if (!(opener in OPENERS)) {
      continue;
    }
    spans.push([index, endOfGroup(source, index)]);
  }
  return spans;
};

/** One palette class (or class-context hex) found in a file. */
export interface Match {
  file: string;
  line: number;
  text: string;
}

const lineOf = (source: string, index: number): number =>
  source.slice(0, index).split("\n").length;

/** Every §3b match in one source text, in document order. */
export const matchesIn = (file: string, source: string): Match[] => {
  const found: Match[] = [];
  for (const match of source.matchAll(paletteGrammar())) {
    found.push({ file, line: lineOf(source, match.index ?? 0), text: match[0] });
  }
  const spans = classContexts(source);
  for (const match of source.matchAll(hexGrammar())) {
    const at = match.index ?? 0;
    if (spans.some(([start, end]) => at >= start && at < end)) {
      found.push({ file, line: lineOf(source, at), text: match[0] });
    }
  }
  return found;
};

// --- the tree walk ---------------------------------------------------------

const HERE = path.dirname(fileURLToPath(import.meta.url));
/** The `frontend` directory. */
export const FRONTEND_ROOT = path.resolve(HERE, "..", "..");
/** The repository root — what the ledger's `file` column is relative to. */
export const REPO_ROOT = path.resolve(FRONTEND_ROOT, "..");

const RECURSION_MARKER = "/**";

const isSource = (name: string): boolean =>
  /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name);

const collect = (directory: string, recursive: boolean): string[] => {
  if (!existsSync(directory)) {
    return [];
  }
  const found: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (recursive && entry.name !== "__tests__") {
        found.push(...collect(full, true));
      }
      continue;
    }
    if (isSource(entry.name)) {
      found.push(full);
    }
  }
  return found;
};

/** Every source file a `MIGRATED_DIRECTORIES` entry pins, `src/`-relative. */
export const pinnedFiles = (
  entries: readonly string[] = MIGRATED_DIRECTORIES,
): string[] => {
  const files = new Set<string>();
  for (const entry of entries) {
    const recursive = entry.endsWith(RECURSION_MARKER);
    const relative = recursive
      ? entry.slice(0, -RECURSION_MARKER.length)
      : entry;
    for (const file of collect(path.join(FRONTEND_ROOT, relative), recursive)) {
      files.add(path.relative(FRONTEND_ROOT, file).split(path.sep).join("/"));
    }
  }
  return [...files].sort();
};

// --- the exceptions file and the ledger ------------------------------------

/** One narrow exception: this class, in this file, under this code (§3c). */
export interface Exception {
  file: string;
  class: string;
  code: string;
  task: string;
}

export const EXCEPTIONS: readonly Exception[] = JSON.parse(
  readFileSync(path.join(HERE, "themeTokenMigration.exceptions.json"), "utf8"),
) as Exception[];

/** One row of `docs/frontend/unmapped-colours.md`. */
export interface LedgerRow {
  task: string;
  file: string;
  line: string;
  class: string;
  code: string;
  why: string;
}

const LEDGER_PATH = path.join(
  REPO_ROOT,
  "docs",
  "frontend",
  "unmapped-colours.md",
);

/**
 * The ledger's six-column table rows.
 *
 * A row is recognised by shape — six cells, and a `code` cell that is one of
 * the eight — so the prose around the table, and the column legend inside
 * it, cannot be mistaken for data.
 */
export const readLedger = (text: string): LedgerRow[] => {
  const rows: LedgerRow[] = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) {
      continue;
    }
    const cells = trimmed
      .slice(1, -1)
      .split("|")
      .map((cell) => cell.trim());
    if (cells.length !== 6 || !GAP_CODES.includes(cells[4])) {
      continue;
    }
    rows.push({
      task: cells[0],
      file: cells[1],
      line: cells[2],
      class: cells[3],
      code: cells[4],
      why: cells[5],
    });
  }
  return rows;
};

export const LEDGER: readonly LedgerRow[] = readLedger(
  readFileSync(LEDGER_PATH, "utf8"),
);

/** The ledger writes repo-relative paths; the guard works `src/`-relative. */
const toSrcRelative = (file: string): string =>
  file.startsWith("frontend/") ? file.slice("frontend/".length) : file;

const SEPARATOR = " :: ";
const key = (file: string, className: string): string =>
  `${file}${SEPARATOR}${className}`;

/**
 * `matchesIn`, memoised at module scope on the file path *and* its source.
 *
 * One scan per file, not one per exception: `matchesIn` is linear in the file
 * and `lineOf` is linear in the match offset, so re-scanning inside the
 * exception loop is cubic once several directories are pinned. With 331
 * exceptions over 37 pinned files the per-`violations()` cache of the first
 * four children re-scanned every file on each of the 331 calls
 * `it("fails when any single exception is removed")` makes, and that one test
 * alone ran for seconds. Hoisting the memo out of `violations` makes those
 * calls share it.
 *
 * Keyed on the file *and* the source it was scanned from, so the memo stays a
 * pure function of its arguments: the mutated-argument tests below hand
 * `violations` a file whose source carries a reintroduced class, get a key
 * that has never been seen, and still bite.
 */
const SCAN_MEMO = new Map<string, Map<string, Match[]>>();

const scan = (file: string, source: string): Match[] => {
  let bySource = SCAN_MEMO.get(file);
  if (bySource === undefined) {
    bySource = new Map<string, Match[]>();
    SCAN_MEMO.set(file, bySource);
  }
  const cached = bySource.get(source);
  if (cached !== undefined) {
    return cached;
  }
  const matches = matchesIn(file, source);
  bySource.set(source, matches);
  return matches;
};

/**
 * Every reason the guard has to fail, as one list of sentences.
 *
 * A pure function of (pinned files, exceptions, ledger) so the suite can
 * prove the guard *bites*: removing an entry, corrupting a code or dropping a
 * ledger row are all exercised by calling this with a mutated argument,
 * never by editing the shipped files.
 */
export const violations = (
  files: ReadonlyArray<{ file: string; source: string }>,
  exceptions: readonly Exception[],
  ledger: readonly LedgerRow[],
): string[] => {
  const problems: string[] = [];
  // The scan memo is at module scope — see `scan` above. The path index is
  // per call because `files` is an argument: a linear `find` inside the
  // exception loop is quadratic, and this function is called once per
  // exception by `it("fails when any single exception is removed")`.
  const byPath = new Map(files.map((file) => [file.file, file]));
  const excused = new Set(
    exceptions.map((entry) => key(entry.file, entry.class)),
  );
  const ledgered = new Set(
    ledger.map((row) => key(toSrcRelative(row.file), row.class)),
  );

  // Rules 1–3, plus rule 4 in the exception-to-ledger direction.
  for (const entry of exceptions) {
    const keys = Object.keys(entry).sort().join(",");
    if (keys !== "class,code,file,task") {
      problems.push(
        `exception for ${entry.class} in ${entry.file} must have exactly the keys file, class, code, task (has ${keys})`,
      );
    }
    if (!GAP_CODES.includes(entry.code)) {
      problems.push(
        `unknown code "${entry.code}" on ${entry.class} in ${entry.file}; use one of ${GAP_CODES.join(", ")} — see docs/frontend/theme-token-mapping.md §1h`,
      );
    }
    if (/[*?]/.test(entry.file) || /[*?]/.test(entry.class)) {
      problems.push(
        `exception ${entry.file} / ${entry.class} is not an exact pair; globs and directory-wide entries are refused (§3c rule 3)`,
      );
    }
    const source = byPath.get(entry.file);
    if (source === undefined) {
      problems.push(
        `exception names ${entry.file}, which is not a source file under a pinned directory (§3c rule 2)`,
      );
      continue;
    }
    if (
      !scan(entry.file, source.source).some(
        (match) => match.text === entry.class,
      )
    ) {
      problems.push(
        `stale exception: ${entry.class} no longer appears in ${entry.file} (§3c rule 2)`,
      );
    }
    if (!ledgered.has(key(entry.file, entry.class))) {
      problems.push(
        `exception ${entry.class} in ${entry.file} has no matching row in docs/frontend/unmapped-colours.md (§3c rule 4)`,
      );
    }
  }

  // Rule 4, the ledger-to-exception direction.
  const pinned = new Set(files.map((file) => file.file));
  for (const row of ledger) {
    const file = toSrcRelative(row.file);
    if (!pinned.has(file)) {
      continue;
    }
    if (!excused.has(key(file, row.class))) {
      problems.push(
        `ledger row ${row.class} in ${row.file} has no entry in themeTokenMigration.exceptions.json (§3c rule 4)`,
      );
    }
  }

  // The guard proper.
  for (const { file, source } of files) {
    for (const match of scan(file, source)) {
      if (excused.has(key(file, match.text))) {
        continue;
      }
      problems.push(
        `${file}:${match.line} still carries "${match.text}"; migrate it to the token its row names in docs/frontend/theme-token-mapping.md, or log it under one of the §1h codes`,
      );
    }
  }
  return problems;
};

const read = (file: string) => ({
  file,
  source: readFileSync(path.join(FRONTEND_ROOT, file), "utf8"),
});

const PINNED = pinnedFiles().map(read);

// --- the suite -------------------------------------------------------------

describe("the §3b grammar", () => {
  it.each([
    "hover:dark:bg-slate-800/40",
    "data-[state=open]:bg-gray-100",
    "sm:text-indigo-600",
    "bg-black/40",
    "text-white",
    "border-emerald-500/50",
    "text-gray-500",
  ])("matches %s whole", (candidate) => {
    const matches = [...candidate.matchAll(paletteGrammar())];

    expect(matches).toHaveLength(1);
    expect(matches[0][0]).toBe(candidate);
  });

  it.each([
    "bg-primary",
    "bg-primary/90",
    "bg-[var(--priority-low-bg)]",
    "text-muted-foreground",
    "shadow-sm",
    "border-2",
    "bg-destructive/5",
  ])("does not match %s", (candidate) => {
    expect([...candidate.matchAll(paletteGrammar())]).toHaveLength(0);
  });

  it("lists its scale alternatives longest-first", () => {
    // The whole class, never the `text-gray-50` prefix of it. An engine given
    // `50|100|…|950` returns the prefix and under-reports by hundreds of
    // occurrences — the defect that cost revision 1 its tree-wide count.
    const [match] = [..."text-gray-500".matchAll(paletteGrammar())];

    expect(match[0]).toBe("text-gray-500");
    expect(match[0]).not.toBe("text-gray-50");
  });

  it("finds a six-digit hex only inside a class context", () => {
    const inside = `const x = <div className="bg-[#1e293b] p-2" />;`;
    const outside = `// palette note: #1e293b is slate-800\nconst SERIES = "#1e293b";`;

    expect(matchesIn("a.tsx", inside).map((match) => match.text)).toEqual([
      "#1e293b",
    ]);
    expect(matchesIn("b.tsx", outside)).toEqual([]);
  });
});

describe("MIGRATED_DIRECTORIES", () => {
  // Written as containment plus uniqueness rather than `toEqual`, so that
  // every child after APRAS-79 appends exactly one `toContain` and edits
  // nothing else. A `toEqual` here would have to be rewritten seven times.
  it("holds every directory a child has pinned, each exactly once", () => {
    expect(MIGRATED_DIRECTORIES).toContain("src/components/ui");
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/lot-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/visitor-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/document-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/occurrence-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/project-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/asset-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain("src/features/finance/components");
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/purchase-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/access-control/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/media-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/feedback-management/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/announcement-feed/components",
    );
    expect(MIGRATED_DIRECTORIES).toContain(
      "src/features/package-management/components",
    );
    expect(new Set(MIGRATED_DIRECTORIES).size).toBe(
      MIGRATED_DIRECTORIES.length,
    );
  });

  it("pins every non-test source file in those directories", () => {
    const roots = MIGRATED_DIRECTORIES.map((entry) =>
      entry.endsWith(RECURSION_MARKER)
        ? entry.slice(0, -RECURSION_MARKER.length)
        : entry,
    );

    expect(PINNED.map((file) => file.file)).toContain(
      "src/components/ui/button.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/lot-management/components/LotTable.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/visitor-management/components/GatekeeperDashboard.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/document-management/components/DocumentGridTable.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/occurrence-management/components/OccurrenceTable.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/project-management/components/ConstructionTrackerPage.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/asset-management/components/AssetTable.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/finance/components/CashBalanceCard.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/purchase-management/components/QuoteComparisonTable.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/access-control/components/DeviceTable.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/media-management/components/PhotoApprovalQueuePage.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/feedback-management/components/FeedbackInboxTable.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/announcement-feed/components/MediaCarousel.tsx",
    );
    expect(PINNED.map((file) => file.file)).toContain(
      "src/features/package-management/components/PackageStatusPage.tsx",
    );
    expect(
      PINNED.every((file) =>
        roots.some((root) => file.file.startsWith(`${root}/`)),
      ),
    ).toBe(true);
    expect(PINNED.some((file) => /\.test\.tsx?$/.test(file.file))).toBe(false);
  });

  it("pins the files of every entry and nothing else", () => {
    // Derived, never a literal: a hard total would have to be edited by each
    // of the six children still to come, which is the edit items 1 and 2 of
    // this rewrite exist to remove. Each child asserts its own directory's
    // count in its own scoped block instead.
    const perDirectory = MIGRATED_DIRECTORIES.map(
      (entry) => pinnedFiles([entry]).length,
    );

    expect(perDirectory.every((count) => count > 0)).toBe(true);
    expect(PINNED).toHaveLength(
      perDirectory.reduce((total, count) => total + count, 0),
    );
  });
});

describe("the guard", () => {
  it("reports no violation in any migrated directory", () => {
    expect(violations(PINNED, EXCEPTIONS, LEDGER)).toEqual([]);
  });

  it("fails on a palette class reintroduced into a pinned file", () => {
    const reintroduced = PINNED.map((file) =>
      file.file === "src/components/ui/button.tsx"
        ? { ...file, source: `${file.source}\n// hover:dark:bg-slate-800/40\n` }
        : file,
    );

    expect(violations(reintroduced, EXCEPTIONS, LEDGER)).toContainEqual(
      expect.stringContaining("hover:dark:bg-slate-800/40"),
    );
  });

  it("fails on a six-digit hex reintroduced into a className there", () => {
    const reintroduced = PINNED.map((file) =>
      file.file === "src/components/ui/button.tsx"
        ? {
            ...file,
            source: `${file.source}\nconst x = <i className="text-[#1e293b]" />;\n`,
          }
        : file,
    );

    expect(violations(reintroduced, EXCEPTIONS, LEDGER)).toContainEqual(
      expect.stringContaining("#1e293b"),
    );
  });

  it("fails when any single exception is removed", () => {
    for (let index = 0; index < EXCEPTIONS.length; index += 1) {
      const without = EXCEPTIONS.filter((_, at) => at !== index);

      expect(violations(PINNED, without, LEDGER)).not.toEqual([]);
    }
  });

  it("fails on an unknown code", () => {
    const corrupted = EXCEPTIONS.map((entry, index) =>
      index === 0 ? { ...entry, code: "GAP-BECAUSE-I-SAID-SO" } : entry,
    );

    expect(violations(PINNED, corrupted, LEDGER)).toContainEqual(
      expect.stringContaining("unknown code"),
    );
  });

  it("fails on an entry whose class is absent from its file", () => {
    const stale: Exception[] = [
      ...EXCEPTIONS,
      {
        file: "src/components/ui/button.tsx",
        class: "bg-emerald-600",
        code: "GAP-TINT",
        task: "APRAS-78",
      },
    ];

    expect(violations(PINNED, stale, LEDGER)).toContainEqual(
      expect.stringContaining("stale exception"),
    );
  });

  it("fails on an entry with no matching ledger row", () => {
    const dropped = LEDGER.filter((row) => row.class !== EXCEPTIONS[0].class);

    expect(violations(PINNED, EXCEPTIONS, dropped)).toContainEqual(
      expect.stringContaining("no matching row"),
    );
  });

  it("refuses a glob in place of an exact pair", () => {
    const globbed: Exception[] = [
      ...EXCEPTIONS,
      {
        file: "src/components/ui/*.tsx",
        class: "bg-amber-100",
        code: "GAP-NO-TOKEN",
        task: "APRAS-78",
      },
    ];

    expect(violations(PINNED, globbed, LEDGER)).toContainEqual(
      expect.stringContaining("not an exact pair"),
    );
  });
});

describe("the exceptions file", () => {
  it("gives every entry exactly the keys file, class, code, task", () => {
    for (const entry of EXCEPTIONS) {
      expect(Object.keys(entry).sort()).toEqual([
        "class",
        "code",
        "file",
        "task",
      ]);
    }
  });

  it("carries no line number, which would rot on every edit", () => {
    for (const entry of EXCEPTIONS) {
      expect(entry).not.toHaveProperty("line");
    }
  });

  it("names only codes from the closed set of §1h", () => {
    for (const entry of EXCEPTIONS) {
      expect(GAP_CODES).toContain(entry.code);
    }
  });

  it("uses src/-relative paths, so APRAS-85's inversion is a one-line change", () => {
    for (const entry of EXCEPTIONS) {
      expect(entry.file.startsWith("src/")).toBe(true);
    }
  });
});

describe("the pilot's own ledger arithmetic", () => {
  const pilot = LEDGER.filter((row) =>
    toSrcRelative(row.file).startsWith("src/components/ui/"),
  );
  const count = (code: string) =>
    pilot.filter((row) => row.code === code).length;

  it("logs 24 occurrences: 12 GAP-TINT, 10 GAP-NO-TOKEN, 1 GAP-NO-SURFACE, 1 GAP-OVERLAY", () => {
    expect(pilot).toHaveLength(24);
    expect(count("GAP-TINT")).toBe(12);
    expect(count("GAP-NO-TOKEN")).toBe(10);
    expect(count("GAP-NO-SURFACE")).toBe(1);
    expect(count("GAP-OVERLAY")).toBe(1);
  });

  it("leaves 24 of the pilot's 31 palette occurrences in place", () => {
    // Scoped to the pilot's own directory exactly as `pilot` above is: over
    // all of PINNED this figure grows with every child and would never be 24
    // again, which would make APRAS-78's arithmetic a later child's to edit.
    const remaining = PINNED.filter((file) =>
      file.file.startsWith("src/components/ui/"),
    ).flatMap((file) => matchesIn(file.file, file.source));

    expect(remaining).toHaveLength(24);
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of pilot) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});

describe("APRAS-79's ledger arithmetic", () => {
  // One scoped `describe` per child, appended. A child never edits another
  // child's block, which is what keeps seven migrations from colliding in
  // one file.
  const DIRECTORY = "src/features/lot-management/components/";
  const rows = LEDGER.filter((row) =>
    toSrcRelative(row.file).startsWith(DIRECTORY),
  );
  const count = (code: string) => rows.filter((row) => row.code === code).length;

  it("logs 211 occurrences under six codes", () => {
    expect(rows).toHaveLength(211);
    expect(count("GAP-SWATCH")).toBe(58);
    expect(count("GAP-OUT-OF-BUDGET")).toBe(49);
    expect(count("GAP-TINT")).toBe(46);
    expect(count("GAP-NO-TOKEN")).toBe(38);
    expect(count("GAP-BORDER-100")).toBe(12);
    expect(count("GAP-OVERLAY")).toBe(8);
  });

  it("uses no code it does not account for", () => {
    expect(count("GAP-NO-SURFACE")).toBe(0);
    expect(count("GAP-UNLISTED")).toBe(0);
  });

  it("leaves 211 of the directory's 520 palette occurrences in place", () => {
    // 520 = 166 migrated + 143 deleted `dark:` siblings + 211 left and logged.
    const remaining = PINNED.filter((file) =>
      file.file.startsWith(DIRECTORY),
    ).flatMap((file) => matchesIn(file.file, file.source));

    expect(remaining).toHaveLength(211);
  });

  it("excepts the 148 distinct (file, class) pairs those 211 occupy", () => {
    const entries = EXCEPTIONS.filter((entry) =>
      entry.file.startsWith(DIRECTORY),
    );
    const pairs = new Set(rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`));

    expect(entries).toHaveLength(148);
    expect(pairs.size).toBe(148);
    expect(entries.every((entry) => entry.task === "APRAS-79")).toBe(true);
  });

  it("keeps the four red tint triples whole, each on one line", () => {
    const triples = [
      ["LinkUserAccountModal.tsx", 67, "text-red-600"],
      ["ResidentFormModal.tsx", 99, "text-red-600"],
      ["LotFormModal.tsx", 112, "text-red-700"],
      ["UserLotAssignmentModal.tsx", 91, "text-red-700"],
    ] as const;

    for (const [name, line, foreground] of triples) {
      const file = `${DIRECTORY}${name}`;
      const source = PINNED.find((pinned) => pinned.file === file);
      const onThatLine = matchesIn(file, source?.source ?? "")
        .filter((match) => match.line === line)
        .map((match) => match.text);

      // Same line, not merely somewhere in the file: a future edit that split
      // a triple across two elements would pass the weaker assertion.
      expect(onThatLine).toContain("bg-red-50");
      expect(onThatLine).toContain(foreground);
    }

    // And no fifth triple was created: `bg-red-50` occurs exactly four times.
    const surfaces = PINNED.filter((file) =>
      file.file.startsWith(DIRECTORY),
    ).flatMap((file) =>
      matchesIn(file.file, file.source).filter(
        (match) => match.text === "bg-red-50",
      ),
    );

    expect(surfaces).toHaveLength(4);
  });

  it("pins the directory's nine source files", () => {
    expect(PINNED.filter((file) => file.file.startsWith(DIRECTORY))).toHaveLength(
      9,
    );
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of rows) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});

describe("APRAS-80's ledger arithmetic", () => {
  // Appended, directory-scoped, in the shape APRAS-79 established. Nothing
  // above this line is edited by this child.
  const DIRECTORY = "src/features/visitor-management/components/";
  const rows = LEDGER.filter((row) =>
    toSrcRelative(row.file).startsWith(DIRECTORY),
  );
  const count = (code: string) => rows.filter((row) => row.code === code).length;
  const files = PINNED.filter((file) => file.file.startsWith(DIRECTORY));
  const matchesOn = (name: string, line: number): string[] => {
    const file = `${DIRECTORY}${name}`;
    const source = files.find((pinned) => pinned.file === file);

    return matchesIn(file, source?.source ?? "")
      .filter((match) => match.line === line)
      .map((match) => match.text);
  };

  it("pins the directory's eight source files", () => {
    expect(files).toHaveLength(8);
  });

  it("logs 113 occurrences under six codes", () => {
    expect(rows).toHaveLength(113);
    expect(count("GAP-TINT")).toBe(61);
    expect(count("GAP-OUT-OF-BUDGET")).toBe(22);
    expect(count("GAP-BORDER-100")).toBe(16);
    expect(count("GAP-NO-TOKEN")).toBe(6);
    expect(count("GAP-OVERLAY")).toBe(5);
    expect(count("GAP-NO-SURFACE")).toBe(3);
  });

  it("uses no code it does not account for", () => {
    // No chart series, no avatar fill and no category-per-enum badge set in
    // this directory: every badge set in it encodes a *status*.
    expect(count("GAP-SWATCH")).toBe(0);
    expect(count("GAP-UNLISTED")).toBe(0);
  });

  it("leaves 113 of the directory's 464 palette occurrences in place", () => {
    // 464 = 193 migrated + 158 deleted `dark:` siblings + 113 left and logged,
    // with both halves closing independently: 254 non-`dark:` = 193 + 61 and
    // 210 `dark:` = 158 + 52.
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source),
    );

    expect(remaining).toHaveLength(113);
    expect(
      remaining.filter((match) => match.text.startsWith("dark:")),
    ).toHaveLength(52);
  });

  it("excepts the 84 distinct (file, class) pairs those 113 occupy", () => {
    const entries = EXCEPTIONS.filter((entry) =>
      entry.file.startsWith(DIRECTORY),
    );
    const pairs = new Set(
      rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );

    expect(entries).toHaveLength(84);
    expect(pairs.size).toBe(84);
    expect(entries.every((entry) => entry.task === "APRAS-80")).toBe(true);
  });

  it("carries no six-digit hex literal in any of the eight files", () => {
    for (const file of files) {
      expect(file.source).not.toMatch(hexGrammar());
    }
  });

  it("keeps all twelve status sets whole, each member on its own line", () => {
    // Every member of every set, at the line the spec names. A future edit
    // that migrated one member of a set — splitting a ternary branch away
    // from the ternary it belongs to — fails here before the guard sees it.
    const sets: ReadonlyArray<readonly [string, number, readonly string[]]> = [
      ["AccessLogTimeline.tsx", 56, ["border-white", "bg-slate-100"]],
      [
        "AccessLogTimeline.tsx",
        58,
        ["bg-emerald-100", "text-emerald-600", "dark:bg-emerald-950"],
      ],
      [
        "AccessLogTimeline.tsx",
        59,
        ["bg-slate-100", "text-slate-500", "dark:bg-slate-800"],
      ],
      ["AccessLogTimeline.tsx", 78, ["bg-emerald-50", "text-emerald-700"]],
      ["AccessLogTimeline.tsx", 82, ["bg-slate-100", "text-slate-600"]],
      [
        "AuthorizationFormModal.tsx",
        131,
        ["border-red-200", "bg-red-50", "text-red-700"],
      ],
      [
        "GatekeeperDashboard.tsx",
        159,
        ["border-red-200", "bg-red-50", "text-red-700"],
      ],
      ["GatekeeperEntryModal.tsx", 65, ["bg-emerald-50", "text-emerald-800"]],
      ["GatekeeperEntryModal.tsx", 66, ["bg-red-50", "text-red-800"]],
      ["GatekeeperEntryModal.tsx", 70, ["text-emerald-600"]],
      ["GatekeeperEntryModal.tsx", 72, ["text-red-600"]],
      ["GatekeeperEntryModal.tsx", 80, ["bg-red-50", "text-red-700"]],
      ["VisitorTable.tsx", 26, ["bg-emerald-50", "text-emerald-700"]],
      ["VisitorTable.tsx", 40, ["bg-red-50", "text-red-700"]],
      [
        "VisitorTable.tsx",
        119,
        ["text-red-600", "border-red-200", "hover:bg-red-50"],
      ],
      ["VisitorAuthPage.tsx", 144, ["border-red-200"]],
    ];
    const ledgered = new Set(
      rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );

    for (const [name, line, members] of sets) {
      const onThatLine = matchesOn(name, line);
      for (const member of members) {
        expect(onThatLine).toContain(member);
        expect(ledgered).toContain(`${DIRECTORY}${name} :: ${member}`);
      }
    }
  });

  it("splits no status set: exactly one span mixes a migrated class with a kept tint", () => {
    // A split set is, by construction, a class-context span holding both a
    // migrated occurrence and a kept `GAP-TINT` occurrence. Run mechanically
    // over every span in the directory, the check must return exactly one —
    // `VisitorAuthPage:144`, where the kept `border-red-200` sits beside the
    // migrated `bg-card`. That span is not a split set: the panel's neutral
    // surface takes its §1f case 1 row, the panel's red border has no row,
    // and the red foreground for that panel lives on a different element.
    // A span mixing a migrated occurrence with a kept occurrence under any
    // *other* gap code is expected and is not counted here.
    const MIGRATED_TARGETS = [
      "bg-card",
      "bg-muted",
      "bg-accent",
      "bg-accent/50",
      "bg-primary",
      "hover:bg-accent",
      "hover:bg-accent/50",
      "hover:bg-primary/90",
      "border-border",
      "border-input",
      "border-primary",
      "divide-border",
      "text-foreground",
      "text-muted-foreground",
      "text-primary",
      "text-primary-text",
      "text-primary-foreground",
      "text-destructive",
    ];
    const target = new RegExp(
      String.raw`(?<![\w-])(?:${MIGRATED_TARGETS.map((name) =>
        name.replace("/", String.raw`\/`),
      ).join("|")})(?![\w-])`,
      "g",
    );
    const tinted = new Set(
      rows
        .filter((row) => row.code === "GAP-TINT")
        .map((row) => `${toSrcRelative(row.file)} :: ${row.line} :: ${row.class}`),
    );
    const mixed: string[] = [];

    for (const { file, source } of files) {
      for (const [start, end] of classContexts(source)) {
        const span = source.slice(start, end);
        if ([...span.matchAll(target)].length === 0) {
          continue;
        }
        // Matched on the span's own offsets, never by searching the file for
        // the class text: several spans carry the same class, and an
        // `indexOf` would attribute one span's occurrence to another.
        for (const match of span.matchAll(paletteGrammar())) {
          const line = lineOf(source, start + (match.index ?? 0));
          if (tinted.has(`${file} :: ${line} :: ${match[0]}`)) {
            mixed.push(`${file}:${line} ${match[0]}`);
            break;
          }
        }
      }
    }

    expect([...new Set(mixed)]).toEqual([
      "src/features/visitor-management/components/VisitorAuthPage.tsx:144 border-red-200",
    ]);
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of rows) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});

describe("APRAS-82's ledger arithmetic", () => {
  // Appended, directory-scoped, in the shape APRAS-79 and APRAS-80
  // established. Nothing above this line is edited by this child beyond the
  // two `MIGRATED_DIRECTORIES` entries, their four `toContain` assertions and
  // the hoist of the scan memo to module scope.
  //
  // Two directories, because the operator scoped this child that way. They
  // exercise opposite halves of §1g: `document-management` holds all 100 of
  // the pair's `dark:` occurrences, `occurrence-management` holds none.
  const DOCUMENTS = "src/features/document-management/components/";
  const OCCURRENCES = "src/features/occurrence-management/components/";
  const DIRECTORIES = [DOCUMENTS, OCCURRENCES];
  const inDirectories = (file: string) =>
    DIRECTORIES.some((directory) => file.startsWith(directory));
  const rows = LEDGER.filter((row) => inDirectories(toSrcRelative(row.file)));
  const count = (code: string) => rows.filter((row) => row.code === code).length;
  const files = PINNED.filter((file) => inDirectories(file.file));
  const sourceOf = (name: string) =>
    files.find((file) => file.file.endsWith(`/${name}`))?.source ?? "";
  const matchesOn = (name: string, line: number): string[] => {
    const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));

    return matchesIn(file?.file ?? "", file?.source ?? "")
      .filter((match) => match.line === line)
      .map((match) => match.text);
  };
  /**
   * One file's source as whole tokens, split on whitespace and on the
   * delimiters a class string can sit inside.
   *
   * Whole tokens, never substrings: `text-primary` and `text-primary-text`
   * are two tokens and neither matches the other, and `hover:bg-accent/80`
   * survives intact rather than becoming `hover:bg-accent`. The ternary
   * branches of a template literal are reached because `{`, `}` and the
   * quote characters are separators, not string boundaries to be paired up.
   */
  const tokensOf = (name: string): string[] =>
    sourceOf(name)
      .split(/[\s"'`{}()<>,;]+/)
      .filter((token) => token.length > 0);

  it("pins the two directories' six and five source files", () => {
    expect(PINNED.filter((file) => file.file.startsWith(DOCUMENTS))).toHaveLength(
      6,
    );
    expect(
      PINNED.filter((file) => file.file.startsWith(OCCURRENCES)),
    ).toHaveLength(5);
    expect(files).toHaveLength(11);
  });

  it("logs 129 occurrences under five codes", () => {
    expect(rows).toHaveLength(129);
    expect(count("GAP-OUT-OF-BUDGET")).toBe(69);
    expect(count("GAP-TINT")).toBe(30);
    expect(count("GAP-NO-TOKEN")).toBe(24);
    expect(count("GAP-OVERLAY")).toBe(3);
    expect(count("GAP-BORDER-100")).toBe(3);
  });

  it("uses no code it does not account for", () => {
    // Neither directory colours a *category*: the occurrence category is one
    // neutral chip for every value, so there is no swatch set. And every
    // `text-white` sat on a background that does have a row.
    expect(count("GAP-SWATCH")).toBe(0);
    expect(count("GAP-NO-SURFACE")).toBe(0);
    expect(count("GAP-UNLISTED")).toBe(0);
  });

  it("leaves 129 of the pair's 447 palette occurrences in place", () => {
    // 447 = 240 migrated + 78 deleted `dark:` siblings + 129 left and logged,
    // with both halves closing independently: 347 non-`dark:` = 240 + 107 and
    // 100 `dark:` = 78 + 22.
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source),
    );
    const inDocuments = files
      .filter((file) => file.file.startsWith(DOCUMENTS))
      .flatMap((file) => matchesIn(file.file, file.source));

    expect(remaining).toHaveLength(129);
    expect(
      remaining.filter((match) => match.text.startsWith("dark:")),
    ).toHaveLength(22);
    expect(inDocuments).toHaveLength(44);
    expect(remaining).toHaveLength(inDocuments.length + 85);
  });

  it("excepts the 77 distinct (file, class) pairs those 129 occupy", () => {
    const entries = EXCEPTIONS.filter((entry) => inDirectories(entry.file));
    const pairs = new Set(
      rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );

    expect(entries).toHaveLength(77);
    expect(pairs.size).toBe(77);
    expect(entries.every((entry) => entry.task === "APRAS-82")).toBe(true);
    expect(
      entries.filter((entry) => entry.file.startsWith(DOCUMENTS)),
    ).toHaveLength(22);
    expect(
      entries.filter((entry) => entry.file.startsWith(OCCURRENCES)),
    ).toHaveLength(55);
  });

  it("carries no six-digit hex literal in any of the eleven files", () => {
    for (const file of files) {
      expect(file.source).not.toMatch(hexGrammar());
    }
  });

  it("keeps all ten status sets whole, each member on its own line", () => {
    // A ternary's or a `switch`'s branches are one set: the same property of
    // the same element in different states. Splitting one — migrating the
    // indigo branch of `getStatusBadgeClass` on its own, say — would break a
    // six-colour status scale, and fails here before the guard sees it.
    const sets: ReadonlyArray<readonly [string, number, readonly string[]]> = [
      ["OccurrenceTable.tsx", 22, ["bg-amber-50", "text-amber-700", "border-amber-200"]],
      ["OccurrenceTable.tsx", 24, ["bg-blue-50", "text-blue-700", "border-blue-200"]],
      ["OccurrenceTable.tsx", 26, ["bg-indigo-50", "text-indigo-700", "border-indigo-200"]],
      ["OccurrenceTable.tsx", 28, ["bg-emerald-50", "text-emerald-700", "border-emerald-200"]],
      ["OccurrenceTable.tsx", 30, ["bg-rose-50", "text-rose-700", "border-rose-200"]],
      ["OccurrenceTable.tsx", 32, ["bg-gray-50", "text-gray-700", "border-gray-200"]],
      ["OccurrenceTable.tsx", 39, ["bg-rose-100", "text-rose-800"]],
      ["OccurrenceTable.tsx", 41, ["bg-orange-100", "text-orange-800"]],
      ["OccurrenceTable.tsx", 43, ["bg-sky-100", "text-sky-800"]],
      ["OccurrenceTable.tsx", 45, ["bg-gray-100", "text-gray-700"]],
      ["OccurrenceTable.tsx", 100, ["text-emerald-600"]],
      ["OccurrenceTable.tsx", 102, ["text-gray-400"]],
      ["NewOccurrenceModal.tsx", 158, ["text-emerald-600", "text-gray-500"]],
      ["OccurrenceDetailsView.tsx", 71, ["text-emerald-700", "bg-emerald-50", "border-emerald-200"]],
      ["OccurrenceDetailsView.tsx", 76, ["text-gray-600", "bg-gray-100", "border-gray-200"]],
      ["OccurrenceDetailsView.tsx", 160, ["bg-emerald-50", "border-emerald-200"]],
      ["OccurrenceDetailsView.tsx", 161, ["text-emerald-900"]],
      ["OccurrenceDetailsView.tsx", 162, ["text-emerald-600"]],
      ["OccurrenceDetailsView.tsx", 165, ["text-emerald-800"]],
      ["DocumentGridTable.tsx", 143, [
        "hover:text-emerald-600",
        "hover:bg-emerald-50",
        "dark:hover:bg-emerald-950/50",
        "dark:hover:text-emerald-400",
      ]],
      ["OccurrenceTimelineLog.tsx", 67, ["text-amber-700", "bg-amber-50", "border-amber-200"]],
      ["DocumentGridTable.tsx", 166, [
        "hover:text-rose-600",
        "hover:bg-rose-50",
        "dark:hover:bg-rose-950/50",
        "dark:hover:text-rose-400",
      ]],
      ["FolderTreeSidebar.tsx", 121, ["hover:text-rose-600", "dark:hover:text-rose-400"]],
    ];
    const ledgered = new Set(
      rows.map((row) => `${row.class} in ${toSrcRelative(row.file)}`),
    );

    for (const [name, line, members] of sets) {
      const onThatLine = matchesOn(name, line);
      const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));
      for (const member of members) {
        expect(onThatLine).toContain(member);
        expect(ledgered).toContain(`${member} in ${file?.file ?? ""}`);
      }
    }

    // The two badge maps together hold 26 classes, all still there.
    const badgeMaps = [22, 24, 26, 28, 30, 32, 39, 41, 43, 45].flatMap((line) =>
      matchesOn("OccurrenceTable.tsx", line),
    );

    expect(badgeMaps).toHaveLength(26);
  });

  it("splits no status set: exactly one span mixes a migrated class with a kept tint", () => {
    // Same mechanical check APRAS-80 ran, over this child's targets. The one
    // span it returns is `DocumentGridTable:143`, where the download button's
    // *resting* neutral foreground takes its §1d row while the button's
    // *hover* pair is the emerald unit. That is not a split set, and it is
    // the shape APRAS-80 recorded at `VisitorAuthPage:144`.
    const MIGRATED_TARGETS = [
      "bg-card",
      "focus:bg-card",
      "bg-muted",
      "bg-accent",
      "hover:bg-accent",
      "hover:bg-accent/80",
      "bg-primary",
      "hover:bg-primary/90",
      "bg-foreground/70",
      "border-border",
      "border-input",
      "border-card",
      "focus:border-primary",
      "divide-border",
      "focus:ring-ring",
      "text-foreground",
      "text-muted-foreground",
      "hover:text-muted-foreground",
      "text-primary",
      "hover:text-primary",
      "text-primary-text",
      "hover:text-primary-text",
      "text-primary-foreground",
    ];
    const target = new RegExp(
      String.raw`(?<![\w-])(?:${MIGRATED_TARGETS.map((name) =>
        name.replace("/", String.raw`\/`),
      ).join("|")})(?![\w-])`,
      "g",
    );
    const tinted = new Set(
      rows
        .filter((row) => row.code === "GAP-TINT")
        .map(
          (row) => `${toSrcRelative(row.file)} :: ${row.line} :: ${row.class}`,
        ),
    );
    const mixed: string[] = [];

    for (const { file, source } of files) {
      for (const [start, end] of classContexts(source)) {
        const span = source.slice(start, end);
        if ([...span.matchAll(target)].length === 0) {
          continue;
        }
        for (const match of span.matchAll(paletteGrammar())) {
          const line = lineOf(source, start + (match.index ?? 0));
          if (tinted.has(`${file} :: ${line} :: ${match[0]}`)) {
            mixed.push(`${file}:${line} ${match[0]}`);
            break;
          }
        }
      }
    }

    expect([...new Set(mixed)]).toEqual([
      `${DOCUMENTS}DocumentGridTable.tsx:143 hover:text-emerald-600`,
    ]);
  });

  it("routes exactly twelve brand-text occurrences to the character token", () => {
    // §1k: the element paints glyphs of text, so the floor is 4.5:1 and the
    // token is `*-primary-text`. Every other brand class in the pair is on an
    // element that paints none, and keeps `*-primary` at the 3:1 floor.
    const perFile: ReadonlyArray<readonly [string, number]> = [
      ["FolderTreeSidebar.tsx", 4],
      ["OccurrenceTable.tsx", 3],
      ["OccurrenceDetailsView.tsx", 4],
      ["OccurrenceTimelineLog.tsx", 1],
    ];
    const characters = (name: string) =>
      tokensOf(name).filter(
        (token) =>
          token === "text-primary-text" || token === "hover:text-primary-text",
      );
    let total = 0;

    for (const [name, expected] of perFile) {
      expect(characters(name)).toHaveLength(expected);
      total += expected;
    }
    expect(total).toBe(12);

    // And at those sites only: no other file carries one.
    for (const file of files) {
      const name = file.file.split("/").pop() ?? "";
      if (!perFile.some(([named]) => named === name)) {
        expect(characters(name)).toHaveLength(0);
      }
      // `-primary-text` never appears on a non-`text-` utility anywhere.
      expect(
        [...file.source.matchAll(/[\w:-]*-primary-text\b/g)].every((match) =>
          /(?:^|:)text-primary-text$/.test(match[0]),
        ),
      ).toBe(true);
    }
  });

  it("routes twenty-two text-prefixed brand occurrences to the graphical token", () => {
    const perFile: ReadonlyArray<readonly [string, number]> = [
      ["DocumentCenterPage.tsx", 2],
      ["DocumentGridTable.tsx", 3],
      ["DocumentUploadModal.tsx", 1],
      ["FolderFormModal.tsx", 2],
      ["FolderTreeSidebar.tsx", 4],
      ["PDFViewerModal.tsx", 1],
      ["NewOccurrenceModal.tsx", 4],
      ["OccurrenceBookPage.tsx", 2],
      ["OccurrenceTimelineLog.tsx", 2],
      ["OccurrenceDetailsView.tsx", 1],
    ];
    let total = 0;

    for (const [name, expected] of perFile) {
      const graphical = tokensOf(name).filter(
        (token) => token === "text-primary" || token === "hover:text-primary",
      );

      expect(graphical).toHaveLength(expected);
      total += expected;
    }
    expect(total).toBe(22);
  });

  it("leaves indigo only in the status map's IN_PROGRESS branch", () => {
    const indigo = files.flatMap((file) =>
      matchesIn(file.file, file.source).filter((match) =>
        match.text.includes("indigo"),
      ),
    );

    expect(
      indigo.map((match) => `${match.file}:${match.line} ${match.text}`).sort(),
    ).toEqual([
      `${OCCURRENCES}OccurrenceTable.tsx:26 bg-indigo-50`,
      `${OCCURRENCES}OccurrenceTable.tsx:26 border-indigo-200`,
      `${OCCURRENCES}OccurrenceTable.tsx:26 text-indigo-700`,
    ]);
  });

  it("gives the PDF download button the brand fill and leaves the grid's emerald whole", () => {
    // The operator's ruling, and §1f case 3's two branches in one diff: an
    // interactive emerald *fill* migrates, an emerald *status* hover pair
    // whose surface has no row stays. A reviewer should check this pair.
    expect(sourceOf("PDFViewerModal.tsx")).not.toContain("emerald");
    expect(sourceOf("PDFViewerModal.tsx")).toContain(
      "bg-primary hover:bg-primary/90 text-primary-foreground",
    );
    expect(sourceOf("DocumentGridTable.tsx")).toContain(
      "hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 dark:hover:text-emerald-400",
    );

    // No red occurs in either directory, so no destructive token appears.
    for (const file of files) {
      expect(file.source).not.toContain("text-destructive");
      expect(matchesIn(file.file, file.source).map((match) => match.text)).not.
        toContainEqual(expect.stringContaining("red-"));
    }
  });

  it("carries every opacity modifier over verbatim and creates no brand-text alpha", () => {
    const occurrences = (needle: string) =>
      files.flatMap((file) =>
        tokensOf(file.file.split("/").pop() ?? "").filter(
          (token) => token === needle,
        ),
      );

    expect(occurrences("bg-foreground/70")).toHaveLength(3);
    expect(occurrences("hover:bg-accent/80")).toHaveLength(2);
    expect(occurrences("hover:bg-primary/90")).toHaveLength(8);
    expect(occurrences("bg-black/40")).toHaveLength(3);

    for (const file of files) {
      expect(file.source).not.toMatch(/text-primary(?:-text)?\/\d/);
    }
  });

  it("deletes every dark: sibling of a migrated base and keeps exactly 22", () => {
    const DELETED = [
      "dark:bg-slate-900",
      "dark:bg-slate-950",
      "dark:bg-slate-800",
      "dark:bg-slate-800/50",
      "dark:bg-slate-800/40",
      "dark:border-slate-800",
      "dark:border-slate-700",
      "dark:divide-slate-800",
      "dark:text-white",
      "dark:text-slate-400",
      "dark:text-indigo-400",
      "dark:bg-indigo-950/50",
      "dark:bg-indigo-950/60",
      "dark:hover:bg-slate-800",
      "dark:hover:text-slate-200",
      "dark:hover:bg-indigo-950/50",
      "dark:hover:text-indigo-400",
    ];
    const documents = files.filter((file) => file.file.startsWith(DOCUMENTS));
    const surviving = documents.flatMap((file) =>
      matchesIn(file.file, file.source).filter((match) =>
        match.text.startsWith("dark:"),
      ),
    );
    const ledgered = new Set(rows.map((row) => row.class));

    for (const deleted of DELETED) {
      expect(surviving.map((match) => match.text)).not.toContain(deleted);
      expect(ledgered).not.toContain(deleted);
    }
    expect(surviving).toHaveLength(22);
    expect(
      surviving.every((match) => ledgered.has(match.text)),
    ).toBe(true);

    // `occurrence-management` had none before and has none now.
    expect(
      files
        .filter((file) => file.file.startsWith(OCCURRENCES))
        .flatMap((file) => [...file.source.matchAll(/\bdark:/g)]),
    ).toHaveLength(0);
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of rows) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});

describe("APRAS-81's ledger arithmetic", () => {
  // Appended, directory-scoped, in the shape APRAS-79, APRAS-80 and APRAS-82
  // established. Nothing above this line is edited by this child beyond the
  // two `MIGRATED_DIRECTORIES` entries and their four `toContain` assertions;
  // the scan memo APRAS-80 conditionally assigned to this child was already
  // hoisted to module scope by APRAS-82, so there is nothing left to hoist.
  //
  // Two directories, because the operator scoped this child that way. They
  // exercise opposite halves of §1g: `project-management` holds all 140 of
  // the pair's `dark:` occurrences, `asset-management` holds none.
  const PROJECTS = "src/features/project-management/components/";
  const ASSETS = "src/features/asset-management/components/";
  const DIRECTORIES = [PROJECTS, ASSETS];
  const inDirectories = (file: string) =>
    DIRECTORIES.some((directory) => file.startsWith(directory));
  const rows = LEDGER.filter((row) => inDirectories(toSrcRelative(row.file)));
  const count = (code: string) => rows.filter((row) => row.code === code).length;
  const files = PINNED.filter((file) => inDirectories(file.file));
  const sourceOf = (name: string) =>
    files.find((file) => file.file.endsWith(`/${name}`))?.source ?? "";
  const matchesOn = (name: string, line: number): string[] => {
    const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));

    return matchesIn(file?.file ?? "", file?.source ?? "")
      .filter((match) => match.line === line)
      .map((match) => match.text);
  };
  /**
   * One file's source as whole tokens, split on whitespace and on the
   * delimiters a class string can sit inside.
   *
   * Whole tokens, never substrings: `text-primary` and `text-primary-text`
   * are two tokens and neither matches the other, and `hover:bg-primary/90`
   * survives intact rather than becoming `hover:bg-primary`.
   */
  const tokensOf = (name: string): string[] =>
    sourceOf(name)
      .split(/[\s"'`{}()<>,;]+/)
      .filter((token) => token.length > 0);

  it("pins the two directories' eight and six source files", () => {
    expect(PINNED.filter((file) => file.file.startsWith(PROJECTS))).toHaveLength(
      8,
    );
    expect(PINNED.filter((file) => file.file.startsWith(ASSETS))).toHaveLength(6);
    expect(files).toHaveLength(14);
  });

  it("logs 276 occurrences under seven codes", () => {
    expect(rows).toHaveLength(276);
    expect(count("GAP-NO-TOKEN")).toBe(87);
    expect(count("GAP-TINT")).toBe(77);
    expect(count("GAP-OUT-OF-BUDGET")).toBe(51);
    expect(count("GAP-BORDER-100")).toBe(23);
    expect(count("GAP-SWATCH")).toBe(21);
    expect(count("GAP-OVERLAY")).toBe(11);
    expect(count("GAP-NO-SURFACE")).toBe(6);
  });

  it("uses no code it does not account for", () => {
    expect(count("GAP-UNLISTED")).toBe(0);
    expect(rows.every((row) => row.task === "APRAS-81")).toBe(true);
  });

  it("leaves 276 of the pair's 587 palette occurrences in place", () => {
    // 587 = 228 migrated + 83 deleted `dark:` siblings + 276 left and logged,
    // with both halves closing independently: 447 non-`dark:` = 228 + 219 and
    // 140 `dark:` = 83 + 57.
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source),
    );
    const inProjects = files
      .filter((file) => file.file.startsWith(PROJECTS))
      .flatMap((file) => matchesIn(file.file, file.source));

    expect(remaining).toHaveLength(276);
    expect(
      remaining.filter((match) => match.text.startsWith("dark:")),
    ).toHaveLength(57);
    expect(inProjects).toHaveLength(133);
    expect(remaining).toHaveLength(inProjects.length + 143);
  });

  it("excepts the 200 distinct (file, class) pairs those 276 occupy", () => {
    const entries = EXCEPTIONS.filter((entry) => inDirectories(entry.file));
    const pairs = new Set(
      rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );

    expect(entries).toHaveLength(200);
    expect(pairs.size).toBe(200);
    expect(entries.every((entry) => entry.task === "APRAS-81")).toBe(true);
    expect(
      entries.filter((entry) => entry.file.startsWith(PROJECTS)),
    ).toHaveLength(101);
    expect(
      entries.filter((entry) => entry.file.startsWith(ASSETS)),
    ).toHaveLength(99);
  });

  it("carries no six-digit hex literal in any of the fourteen files", () => {
    for (const file of files) {
      expect(file.source).not.toMatch(hexGrammar());
    }
  });

  it("keeps all sixteen status sets whole, each member still on its line", () => {
    // A ternary's or a `switch`'s branches are one set: the same property of
    // the same element in different states. Splitting one — migrating the
    // slate branch of `STATUS_BADGES` on its own, say — would break a
    // four-colour status scale, and fails here before the guard sees it.
    const sets: ReadonlyArray<readonly [string, number, readonly string[]]> = [
      // 1 — MilestoneTimeline's three column badges.
      ["MilestoneTimeline.tsx", 28, ["bg-emerald-100", "text-emerald-800", "border-emerald-200"]],
      ["MilestoneTimeline.tsx", 35, ["bg-blue-100", "text-blue-800", "border-blue-200"]],
      ["MilestoneTimeline.tsx", 42, ["bg-slate-100", "text-slate-800", "border-slate-200"]],
      // 2 — ProjectSummaryCard's four STATUS_BADGES.
      ["ProjectSummaryCard.tsx", 23, ["bg-slate-100", "text-slate-800", "border-slate-200"]],
      ["ProjectSummaryCard.tsx", 28, ["bg-blue-100", "text-blue-800", "border-blue-200"]],
      ["ProjectSummaryCard.tsx", 33, ["bg-amber-100", "text-amber-800", "border-amber-200"]],
      ["ProjectSummaryCard.tsx", 38, ["bg-emerald-100", "text-emerald-800", "border-emerald-200"]],
      // 3 — the budget-bar fill ternary.
      ["ProjectSummaryCard.tsx", 172, ["bg-red-500"]],
      ["ProjectSummaryCard.tsx", 173, ["bg-emerald-500"]],
      // 4 — `progressColor`.
      ["BudgetVsActualProgressBar.tsx", 23, ["bg-emerald-500"]],
      ["BudgetVsActualProgressBar.tsx", 25, ["bg-red-500"]],
      ["BudgetVsActualProgressBar.tsx", 27, ["bg-amber-500"]],
      // 5 — the executed-value ternary.
      ["BudgetVsActualProgressBar.tsx", 79, ["text-red-600", "dark:text-red-400"]],
      ["BudgetVsActualProgressBar.tsx", 80, ["text-slate-800", "dark:text-slate-200"]],
      // 6 — the remaining-value ternary.
      ["BudgetVsActualProgressBar.tsx", 94, ["text-red-600", "dark:text-red-400"]],
      ["BudgetVsActualProgressBar.tsx", 95, ["text-emerald-600", "dark:text-emerald-400"]],
      // 7 — the budget glyphs.
      ["BudgetVsActualProgressBar.tsx", 34, ["text-emerald-600", "dark:text-emerald-400"]],
      ["BudgetVsActualProgressBar.tsx", 46, ["text-emerald-600"]],
      // 8, 9, 10 — the report alerts and the delete-project control.
      ["ConstructionTrackerPage.tsx", 271, ["border-emerald-200", "bg-emerald-50", "text-emerald-800"]],
      ["ConstructionTrackerPage.tsx", 272, ["border-red-200", "bg-red-50", "text-red-800"]],
      ["ConstructionTrackerPage.tsx", 317, ["text-red-600", "border-red-200", "hover:bg-red-50", "dark:hover:bg-red-950"]],
      // 11 — `getConditionBadgeClass`, six branches.
      ["AssetTable.tsx", 32, ["bg-emerald-100", "text-emerald-800", "border-emerald-200"]],
      ["AssetTable.tsx", 34, ["bg-blue-100", "text-blue-800", "border-blue-200"]],
      ["AssetTable.tsx", 36, ["bg-amber-100", "text-amber-800", "border-amber-200"]],
      ["AssetTable.tsx", 39, ["bg-orange-100", "text-orange-800", "border-orange-200"]],
      ["AssetTable.tsx", 41, ["bg-red-100", "text-red-800", "border-red-200"]],
      ["AssetTable.tsx", 43, ["bg-gray-100", "text-gray-800", "border-gray-200"]],
      // 12 — the low-stock badge.
      ["AssetTable.tsx", 162, ["bg-amber-100", "text-amber-800"]],
      ["AssetTable.tsx", 164, ["text-amber-600"]],
      // 13 — the four movement-type badges.
      ["AssetMovementHistoryModal.tsx", 27, ["bg-emerald-100", "text-emerald-800"]],
      ["AssetMovementHistoryModal.tsx", 28, ["text-emerald-600"]],
      ["AssetMovementHistoryModal.tsx", 34, ["bg-blue-100", "text-blue-800"]],
      ["AssetMovementHistoryModal.tsx", 35, ["text-blue-600"]],
      ["AssetMovementHistoryModal.tsx", 41, ["bg-amber-100", "text-amber-800"]],
      ["AssetMovementHistoryModal.tsx", 42, ["text-amber-600"]],
      ["AssetMovementHistoryModal.tsx", 48, ["bg-red-100", "text-red-800"]],
      ["AssetMovementHistoryModal.tsx", 49, ["text-red-600"]],
      // 14 — the two error alerts.
      ["AssetFormModal.tsx", 152, ["bg-red-50", "text-red-700", "border-red-200"]],
      ["StockMovementModal.tsx", 113, ["bg-red-50", "text-red-700", "border-red-200"]],
      // 15 — AssetSummaryCards' metric tiles.
      ["AssetSummaryCards.tsx", 37, ["bg-blue-50", "text-blue-600"]],
      ["AssetSummaryCards.tsx", 61, ["border-amber-300", "bg-amber-50/20"]],
      ["AssetSummaryCards.tsx", 66, ["text-amber-700"]],
      ["AssetSummaryCards.tsx", 69, ["text-amber-900"]],
      ["AssetSummaryCards.tsx", 73, ["bg-amber-100", "text-amber-600"]],
      ["AssetSummaryCards.tsx", 84, ["text-emerald-700"]],
      ["AssetSummaryCards.tsx", 88, ["bg-emerald-50", "text-emerald-600"]],
      // 16 — the inventory header tile and tab strip.
      ["AssetsInventoryPage.tsx", 149, ["bg-blue-50", "text-blue-600"]],
      ["AssetsInventoryPage.tsx", 168, ["bg-blue-600", "hover:bg-blue-700"]],
      ["AssetsInventoryPage.tsx", 191, ["bg-blue-50", "text-blue-700"]],
      ["AssetsInventoryPage.tsx", 203, ["bg-blue-50", "text-blue-700"]],
      ["AssetsInventoryPage.tsx", 215, ["bg-blue-50", "text-blue-700"]],
      ["AssetsInventoryPage.tsx", 227, ["bg-amber-50", "text-amber-700"]],
      ["AssetsInventoryPage.tsx", 231, ["text-amber-500"]],
      ["AssetsInventoryPage.tsx", 234, ["bg-amber-200", "text-amber-900"]],
    ];
    const ledgered = new Set(
      rows.map((row) => `${row.class} in ${toSrcRelative(row.file)}`),
    );

    for (const [name, line, members] of sets) {
      const onThatLine = matchesOn(name, line);
      const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));
      for (const member of members) {
        expect(onThatLine).toContain(member);
        expect(ledgered).toContain(`${member} in ${file?.file ?? ""}`);
      }
    }
  });

  it("keeps the one swatch map whole, all seven branches of it", () => {
    // §1h code 2: a *category* scale must not follow the brand, or it loses
    // two of its seven hues to it. `getConditionBadgeClass` above is not a
    // swatch — a condition is a record's status — so it takes codes 3 and 4
    // by family; both codes forbid migration, so only the label differs.
    const swatch = [50, 52, 54, 56, 58, 60, 62].flatMap((line) =>
      matchesOn("AssetTable.tsx", line),
    );

    expect(swatch).toHaveLength(21);
    expect(swatch).toContain("bg-indigo-50");
    expect(swatch).toContain("text-indigo-700");
    expect(swatch).toContain("border-indigo-200");
    expect(swatch).toContain("bg-gray-50");
    expect(swatch).toContain("text-gray-700");
    expect(swatch).toContain("border-gray-200");
    expect(
      rows.filter((row) => row.code === "GAP-SWATCH").every((row) =>
        toSrcRelative(row.file).endsWith("/AssetTable.tsx"),
      ),
    ).toBe(true);
  });

  it("splits no status set: no span mixes a migrated class with a kept tint", () => {
    // The same mechanical check APRAS-80 and APRAS-82 ran, over this child's
    // targets. Spans that mix a migrated occurrence with a kept occurrence
    // under any *other* code are expected and are not counted — the filter
    // chip at `ConstructionTrackerPage:426–427` and the tab strip at
    // `AssetsInventoryPage:191–192` are both of that shape.
    const MIGRATED_TARGETS = [
      "bg-background",
      "bg-card",
      "bg-muted",
      "bg-accent",
      "hover:bg-accent",
      "hover:bg-accent/75",
      "bg-primary",
      "hover:bg-primary/90",
      "bg-foreground",
      "border-border",
      "border-border/80",
      "border-border/60",
      "border-input",
      "divide-border",
      "text-foreground",
      "text-muted-foreground",
      "hover:text-muted-foreground",
      "text-primary",
      "hover:text-primary",
      "text-primary-text",
      "text-primary-foreground",
      "hover:text-destructive",
    ];
    const target = new RegExp(
      String.raw`(?<![\w-])(?:${MIGRATED_TARGETS.map((name) =>
        name.replace("/", String.raw`\/`),
      ).join("|")})(?![\w-])`,
      "g",
    );
    const tinted = new Set(
      rows
        .filter((row) => row.code === "GAP-TINT")
        .map(
          (row) => `${toSrcRelative(row.file)} :: ${row.line} :: ${row.class}`,
        ),
    );
    const mixed: string[] = [];

    for (const { file, source } of files) {
      for (const [start, end] of classContexts(source)) {
        const span = source.slice(start, end);
        if ([...span.matchAll(target)].length === 0) {
          continue;
        }
        for (const match of span.matchAll(paletteGrammar())) {
          const line = lineOf(source, start + (match.index ?? 0));
          if (tinted.has(`${file} :: ${line} :: ${match[0]}`)) {
            mixed.push(`${file}:${line} ${match[0]}`);
            break;
          }
        }
      }
    }

    expect([...new Set(mixed)]).toEqual([]);
  });

  it("routes exactly two brand-text occurrences to the character token", () => {
    // §1k: the element paints glyphs of text, so the floor is 4.5:1 and the
    // token is `*-primary-text`. Both are in the physical-progress gauge —
    // its label and its percentage figure. Every other brand class in the
    // pair is on an element that paints none.
    const characters = (name: string) =>
      tokensOf(name).filter(
        (token) =>
          token === "text-primary-text" || token === "hover:text-primary-text",
      );

    expect(characters("ConstructionTrackerPage.tsx")).toHaveLength(2);
    for (const file of files) {
      const name = file.file.split("/").pop() ?? "";
      if (name !== "ConstructionTrackerPage.tsx") {
        expect(characters(name)).toHaveLength(0);
      }
      // `-primary-text` never appears on a non-`text-` utility anywhere.
      expect(
        [...file.source.matchAll(/[\w:-]*-primary-text\b/g)].every((match) =>
          /(?:^|:)text-primary-text$/.test(match[0]),
        ),
      ).toBe(true);
    }
  });

  it("routes ten text-prefixed brand occurrences to the graphical token", () => {
    const perFile: ReadonlyArray<readonly [string, number]> = [
      ["ConstructionTrackerPage.tsx", 3],
      ["MilestoneTimeline.tsx", 2],
      ["ProjectUpdateFeed.tsx", 1],
      ["ProjectSummaryCard.tsx", 1],
      ["AssetMovementHistoryModal.tsx", 1],
      ["AssetSummaryCards.tsx", 1],
      ["AssetTable.tsx", 1],
    ];
    let total = 0;

    for (const [name, expected] of perFile) {
      const graphical = tokensOf(name).filter(
        (token) => token === "text-primary" || token === "hover:text-primary",
      );

      expect(graphical).toHaveLength(expected);
      total += expected;
    }
    expect(total).toBe(10);
  });

  it("sends the one page root to bg-background and nothing else", () => {
    // §1f case 1 as this task amends it: an element that *is* the page takes
    // `bg-background` whatever its source class. `--background` and `--muted`
    // are different colours with different tenant behaviour, so this is the
    // one context-dependent choice of the migration a test can check.
    const roots = files.filter((file) =>
      tokensOf(file.file.split("/").pop() ?? "").includes("bg-background"),
    );

    expect(roots.map((file) => file.file)).toEqual([
      `${PROJECTS}ConstructionTrackerPage.tsx`,
    ]);
    expect(sourceOf("ConstructionTrackerPage.tsx")).toContain(
      "min-h-screen bg-background",
    );
    for (const absent of ["bg-slate-50", "bg-muted", "dark:bg-slate-950"]) {
      expect(matchesOn("ConstructionTrackerPage.tsx", 198)).not.toContain(absent);
    }
    // The inventory page declares no background class and is not the page, so
    // its root is untouched.
    expect(sourceOf("AssetsInventoryPage.tsx")).toContain(
      'className="container mx-auto px-4 py-8 max-w-7xl space-y-6"',
    );
  });

  it("migrates no emerald and no text-red-*, and moves red at three sites only", () => {
    const KEPT = [
      "bg-emerald-500",
      "bg-emerald-50",
      "bg-emerald-100",
      "text-emerald-600",
      "text-emerald-700",
      "text-emerald-800",
      "border-emerald-200",
      "bg-red-50",
      "bg-red-100",
      "bg-red-500",
      "text-red-600",
      "text-red-700",
      "text-red-800",
      "border-red-200",
    ];
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source).map((match) => match.text),
    );
    const ledgered = new Set(rows.map((row) => row.class));

    for (const kept of KEPT) {
      expect(remaining).toContain(kept);
      expect(ledgered).toContain(kept);
    }

    const destructive = files.filter((file) =>
      tokensOf(file.file.split("/").pop() ?? "").includes(
        "hover:text-destructive",
      ),
    );

    expect(destructive.map((file) => file.file).sort()).toEqual([
      `${ASSETS}AssetTable.tsx`,
      `${PROJECTS}MilestoneTimeline.tsx`,
      `${PROJECTS}ProjectUpdateFeed.tsx`,
    ]);
    expect(remaining.filter((text) => text === "hover:text-red-600")).toEqual([]);
  });

  it("deletes every dark: sibling of a migrated base and keeps exactly 57", () => {
    const DELETED = [
      "dark:bg-slate-900",
      "dark:bg-slate-950",
      "dark:bg-slate-800/40",
      "dark:bg-slate-800/60",
      "dark:text-slate-100",
      "dark:text-slate-400",
      "dark:text-slate-500",
      "dark:text-indigo-400",
      "dark:text-indigo-300",
      "dark:text-indigo-100",
      "dark:bg-indigo-950/50",
      "dark:bg-indigo-800",
      "dark:border-indigo-900",
      "dark:hover:text-slate-200",
      "dark:hover:bg-slate-800",
    ];
    const projects = files.filter((file) => file.file.startsWith(PROJECTS));
    const surviving = projects.flatMap((file) =>
      matchesIn(file.file, file.source).filter((match) =>
        match.text.startsWith("dark:"),
      ),
    );
    const ledgered = new Set(rows.map((row) => row.class));

    for (const deleted of DELETED) {
      expect(surviving.map((match) => match.text)).not.toContain(deleted);
      expect(ledgered).not.toContain(deleted);
    }
    expect(surviving).toHaveLength(57);
    expect(surviving.every((match) => ledgered.has(match.text))).toBe(true);

    // `asset-management` had no `dark:` occurrence before and has none now.
    expect(
      files
        .filter((file) => file.file.startsWith(ASSETS))
        .flatMap((file) => [...file.source.matchAll(/\bdark:/g)]),
    ).toHaveLength(0);
  });

  it("carries every opacity modifier over verbatim and creates no brand-text alpha", () => {
    const occurrences = (needle: string) =>
      files.flatMap((file) =>
        tokensOf(file.file.split("/").pop() ?? "").filter(
          (token) => token === needle,
        ),
      );

    expect(occurrences("border-border/80")).toHaveLength(2);
    expect(occurrences("border-border/60")).toHaveLength(1);
    expect(occurrences("hover:bg-accent/75")).toHaveLength(1);
    expect(occurrences("hover:bg-primary/90")).toHaveLength(3);

    for (const file of files) {
      for (const dropped of [
        "border-slate-200/80",
        "border-gray-200/60",
        "hover:bg-gray-50/75",
        "hover:bg-indigo-700",
      ]) {
        expect(file.source).not.toContain(dropped);
      }
      expect(file.source).not.toMatch(/text-primary(?:-text)?\/\d/);
    }
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of rows) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});

describe("APRAS-83's ledger arithmetic", () => {
  // Appended, directory-scoped, in the shape APRAS-79, APRAS-80, APRAS-82 and
  // APRAS-81 established. Nothing above this line is edited by this child
  // beyond the three `MIGRATED_DIRECTORIES` entries and their six `toContain`
  // assertions; the scan memo is already at module scope, hoisted by APRAS-82,
  // so this child verifies the hoist still holds under a larger input and
  // changes nothing.
  //
  // Three directories, because the operator scoped this child that way. They
  // exercise both halves of §1g: `finance` and `access-control` hold all 162
  // of the trio's `dark:` occurrences between them, `purchase-management`
  // holds none.
  const FINANCE = "src/features/finance/components/";
  const PURCHASES = "src/features/purchase-management/components/";
  const ACCESS = "src/features/access-control/components/";
  const DIRECTORIES = [FINANCE, PURCHASES, ACCESS];
  const inDirectories = (file: string) =>
    DIRECTORIES.some((directory) => file.startsWith(directory));
  const rows = LEDGER.filter((row) => inDirectories(toSrcRelative(row.file)));
  const count = (code: string) =>
    rows.filter((row) => row.code === code).length;
  const files = PINNED.filter((file) => inDirectories(file.file));
  const sourceOf = (name: string) =>
    files.find((file) => file.file.endsWith(`/${name}`))?.source ?? "";
  const matchesOn = (name: string, line: number): string[] => {
    const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));

    return matchesIn(file?.file ?? "", file?.source ?? "")
      .filter((match) => match.line === line)
      .map((match) => match.text);
  };
  /**
   * One file's source as whole tokens, split on whitespace and on the
   * delimiters a class string can sit inside.
   *
   * Whole tokens, never substrings: `text-primary` and `text-primary-text`
   * are two tokens and neither matches the other, and `hover:bg-primary/90`
   * survives intact rather than becoming `hover:bg-primary`.
   */
  const tokensOf = (name: string): string[] =>
    sourceOf(name)
      .split(/[\s"'`{}()<>,;]+/)
      .filter((token) => token.length > 0);

  it("pins the three directories' ten, six and six source files", () => {
    expect(PINNED.filter((file) => file.file.startsWith(FINANCE))).toHaveLength(
      10,
    );
    expect(
      PINNED.filter((file) => file.file.startsWith(PURCHASES)),
    ).toHaveLength(6);
    expect(PINNED.filter((file) => file.file.startsWith(ACCESS))).toHaveLength(
      6,
    );
    expect(files).toHaveLength(22);
  });

  it("logs 190 occurrences under six codes", () => {
    expect(rows).toHaveLength(190);
    expect(count("GAP-TINT")).toBe(83);
    expect(count("GAP-OUT-OF-BUDGET")).toBe(33);
    expect(count("GAP-BORDER-100")).toBe(33);
    expect(count("GAP-NO-TOKEN")).toBe(29);
    expect(count("GAP-OVERLAY")).toBe(10);
    expect(count("GAP-SWATCH")).toBe(2);
  });

  it("uses no code it does not account for", () => {
    expect(count("GAP-NO-SURFACE")).toBe(0);
    expect(count("GAP-UNLISTED")).toBe(0);
    expect(rows.every((row) => row.task === "APRAS-83")).toBe(true);
  });

  it("leaves 190 of the trio's 534 palette occurrences in place", () => {
    // 534 = 233 migrated + 111 deleted `dark:` siblings + 190 left and
    // logged, with both halves closing independently: 372 non-`dark:` =
    // 233 + 139 and 162 `dark:` = 111 + 51.
    const remainingIn = (directory: string) =>
      files
        .filter((file) => file.file.startsWith(directory))
        .flatMap((file) => matchesIn(file.file, file.source));
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source),
    );

    expect(remaining).toHaveLength(190);
    expect(
      remaining.filter((match) => match.text.startsWith("dark:")),
    ).toHaveLength(51);
    expect(remainingIn(FINANCE)).toHaveLength(49);
    expect(remainingIn(PURCHASES)).toHaveLength(78);
    expect(remainingIn(ACCESS)).toHaveLength(63);
  });

  it("excepts the 145 distinct (file, class) pairs those 190 occupy", () => {
    const entries = EXCEPTIONS.filter((entry) => inDirectories(entry.file));
    const pairs = new Set(
      rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );

    expect(entries).toHaveLength(145);
    expect(pairs.size).toBe(145);
    expect(entries.every((entry) => entry.task === "APRAS-83")).toBe(true);
    expect(
      entries.filter((entry) => entry.file.startsWith(FINANCE)),
    ).toHaveLength(37);
    expect(
      entries.filter((entry) => entry.file.startsWith(PURCHASES)),
    ).toHaveLength(52);
    expect(
      entries.filter((entry) => entry.file.startsWith(ACCESS)),
    ).toHaveLength(56);
  });

  it("carries no six-digit hex literal in any of the twenty-two files", () => {
    for (const file of files) {
      expect(file.source).not.toMatch(hexGrammar());
    }
  });

  it("keeps all twenty-four status sets whole, each member still on its line", () => {
    // A ternary's or a lookup map's branches are one set: the same property of
    // the same element in different states. Splitting one — migrating the
    // OFFLINE branch of `DeviceTable`'s `StatusBadge` map on its own, say —
    // would break a three-colour status scale, and fails here before the
    // guard sees it. 109 classes over the twenty-four sets.
    const sets: ReadonlyArray<readonly [string, number, readonly string[]]> = [
      // 1 — the granted/denied glyph ternary.
      ["AccessEventFeed.tsx", 27, ["text-emerald-500"]],
      ["AccessEventFeed.tsx", 29, ["text-red-500"]],
      // 2 — the granted/denied badge ternary.
      ["AccessEventFeed.tsx", 47, ["bg-emerald-100", "text-emerald-700", "dark:bg-emerald-950/50", "dark:text-emerald-400"]],
      ["AccessEventFeed.tsx", 48, ["bg-red-100", "text-red-700", "dark:bg-red-950/50", "dark:text-red-400"]],
      // 3 — `DeviceTable`'s `StatusBadge` config map, three branches.
      ["DeviceTable.tsx", 18, ["bg-emerald-100", "text-emerald-700", "dark:bg-emerald-950/50", "dark:text-emerald-400"]],
      ["DeviceTable.tsx", 22, ["bg-slate-100", "text-slate-600", "dark:bg-slate-800", "dark:text-slate-400"]],
      ["DeviceTable.tsx", 26, ["bg-amber-100", "text-amber-700", "dark:bg-amber-950/50", "dark:text-amber-400"]],
      // 4 — the SYNCED / PENDING / FAILED map.
      ["FacialTemplateSyncPanel.tsx", 8, ["bg-emerald-100", "text-emerald-700", "dark:bg-emerald-950/50", "dark:text-emerald-400"]],
      ["FacialTemplateSyncPanel.tsx", 9, ["bg-amber-100", "text-amber-700", "dark:bg-amber-950/50", "dark:text-amber-400"]],
      ["FacialTemplateSyncPanel.tsx", 10, ["bg-red-100", "text-red-700", "dark:bg-red-950/50", "dark:text-red-400"]],
      // 5 and 6 — the two error alerts, the same six classes each.
      ["FacialTemplateSyncPanel.tsx", 58, ["border-red-200", "bg-red-50", "text-red-700", "dark:border-red-900/50", "dark:bg-red-950/50", "dark:text-red-400"]],
      ["RegisterDeviceModal.tsx", 68, ["border-red-200", "bg-red-50", "text-red-700", "dark:border-red-900/50", "dark:bg-red-950/50", "dark:text-red-400"]],
      // 7 — the income card.
      ["CashBalanceCard.tsx", 40, ["bg-emerald-50", "dark:bg-emerald-950"]],
      ["CashBalanceCard.tsx", 41, ["text-emerald-600", "dark:text-emerald-400"]],
      ["CashBalanceCard.tsx", 47, ["text-emerald-600", "dark:text-emerald-400"]],
      // 8 — the expense card.
      ["CashBalanceCard.tsx", 54, ["bg-red-50", "dark:bg-red-950"]],
      ["CashBalanceCard.tsx", 55, ["text-red-600", "dark:text-red-400"]],
      ["CashBalanceCard.tsx", 61, ["text-red-600", "dark:text-red-400"]],
      // 9 — the variance ternary.
      ["BudgetVsActualTable.tsx", 99, ["text-red-600", "text-emerald-600"]],
      // 10 — the credit and debit columns.
      ["StatementTable.tsx", 41, ["text-emerald-600", "dark:text-emerald-400"]],
      ["StatementTable.tsx", 44, ["text-red-600", "dark:text-red-400"]],
      // 11 — the chart bars, the only `GAP-SWATCH` of this child.
      ["StatementChart.tsx", 53, ["bg-emerald-500"]],
      ["StatementChart.tsx", 59, ["bg-red-500"]],
      // 12 — the justification panel.
      ["PurchaseRequestDetailModal.tsx", 136, ["bg-amber-50", "border-amber-200"]],
      ["PurchaseRequestDetailModal.tsx", 137, ["text-amber-800"]],
      ["PurchaseRequestDetailModal.tsx", 140, ["text-amber-900"]],
      // 13 — the approved panel.
      ["PurchaseRequestDetailModal.tsx", 237, ["border-emerald-200", "bg-emerald-50"]],
      ["PurchaseRequestDetailModal.tsx", 239, ["text-emerald-600"]],
      ["PurchaseRequestDetailModal.tsx", 240, ["text-emerald-900"]],
      ["PurchaseRequestDetailModal.tsx", 248, ["text-emerald-900"]],
      ["PurchaseRequestDetailModal.tsx", 251, ["text-emerald-700"]],
      // 14, 17, 21, 22 — the four red error triples.
      ["PurchaseRequestFormModal.tsx", 184, ["bg-red-50", "text-red-700", "border-red-200"]],
      ["QuoteComparisonTable.tsx", 386, ["border-red-200", "bg-red-50", "text-red-700"]],
      ["QuoteFormModal.tsx", 280, ["bg-red-50", "text-red-700", "border-red-200"]],
      ["SelectQuoteModal.tsx", 88, ["bg-red-50", "text-red-700", "border-red-200"]],
      // 15 — the amber warning triple.
      ["PurchaseRequestFormModal.tsx", 281, ["border-amber-200", "bg-amber-50", "text-amber-800"]],
      // 16 — the lowest-price total ternary, whose neutral half is kept with it.
      ["QuoteComparisonTable.tsx", 337, ["text-emerald-700", "text-gray-900"]],
      // 18 and 19 — the lowest-price head and cell tints.
      ["QuoteComparisonTable.tsx", 406, ["bg-emerald-50/60"]],
      ["QuoteComparisonTable.tsx", 447, ["bg-emerald-50/40"]],
      ["QuoteComparisonTable.tsx", 466, ["bg-emerald-50/40"]],
      ["QuoteComparisonTable.tsx", 494, ["bg-emerald-50/40"]],
      // 20 — the lowest-price card ternary, neutral half kept with it.
      ["QuoteComparisonTable.tsx", 527, ["border-emerald-300", "bg-emerald-50/40"]],
      ["QuoteComparisonTable.tsx", 528, ["border-gray-200"]],
      // 23 and 24 — the two warning panels.
      ["SelectQuoteModal.tsx", 113, ["border-amber-200", "bg-amber-50"]],
      ["SelectQuoteModal.tsx", 116, ["text-amber-600"]],
      ["SelectQuoteModal.tsx", 117, ["text-amber-900"]],
      ["SelectQuoteModal.tsx", 140, ["border-amber-200", "bg-amber-50"]],
      ["SelectQuoteModal.tsx", 143, ["text-amber-600"]],
      ["SelectQuoteModal.tsx", 144, ["text-amber-900"]],
      ["SelectQuoteModal.tsx", 159, ["text-amber-700"]],
    ];
    const ledgered = new Set(
      rows.map((row) => `${row.class} in ${toSrcRelative(row.file)}`),
    );
    let members = 0;

    for (const [name, line, classes] of sets) {
      const onThatLine = matchesOn(name, line);
      const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));
      for (const member of classes) {
        expect(onThatLine).toContain(member);
        expect(ledgered).toContain(`${member} in ${file?.file ?? ""}`);
        members += 1;
      }
    }
    expect(members).toBe(109);
  });

  it("splits no status set: no span mixes a migrated class with a kept tint", () => {
    // The same mechanical check APRAS-80, APRAS-82 and APRAS-81 ran, over this
    // child's targets. Exactly one span mixes, and it is not a split set:
    // `QuoteComparisonTable` 405–406, where the migrating `border-gray-200`
    // every column head carries sits beside set 18's kept `bg-emerald-50/60`,
    // which only the lowest-price head carries. The same shape APRAS-80
    // recorded at `VisitorAuthPage:144`.
    const MIGRATED_TARGETS = [
      "bg-background",
      "bg-card",
      "bg-muted",
      "bg-accent",
      "hover:bg-accent",
      "file:bg-accent",
      "hover:file:bg-accent",
      "bg-primary",
      "hover:bg-primary/90",
      "bg-foreground/70",
      "border-border",
      "border-input",
      "text-foreground",
      "text-muted-foreground",
      "hover:text-muted-foreground",
      "text-primary",
      "text-primary-text",
      "file:text-primary-text",
      "text-primary-foreground",
      "text-destructive",
    ];
    const target = new RegExp(
      String.raw`(?<![\w-])(?:${MIGRATED_TARGETS.map((name) =>
        name.replace("/", String.raw`\/`),
      ).join("|")})(?![\w-])`,
      "g",
    );
    const tinted = new Set(
      rows
        .filter((row) => row.code === "GAP-TINT")
        .map(
          (row) => `${toSrcRelative(row.file)} :: ${row.line} :: ${row.class}`,
        ),
    );
    const mixed: string[] = [];

    for (const { file, source } of files) {
      for (const [start, end] of classContexts(source)) {
        const span = source.slice(start, end);
        if ([...span.matchAll(target)].length === 0) {
          continue;
        }
        for (const match of span.matchAll(paletteGrammar())) {
          const line = lineOf(source, start + (match.index ?? 0));
          if (tinted.has(`${file} :: ${line} :: ${match[0]}`)) {
            mixed.push(`${file}:${line} ${match[0]}`);
            break;
          }
        }
      }
    }

    expect([...new Set(mixed)]).toEqual([
      `${PURCHASES}QuoteComparisonTable.tsx:406 bg-emerald-50/60`,
    ]);
  });

  it("routes exactly two brand-text occurrences to the character token", () => {
    // §1k: the element paints glyphs of text, so the floor is 4.5:1 and the
    // token is `*-primary-text`. The revealed device-key chip renders the key
    // itself; the `file:` variant paints the file-selector button, which
    // renders the browser's own label characters. Every other brand class in
    // the trio is on an element that paints none.
    const characters = (name: string) =>
      tokensOf(name).filter(
        (token) =>
          token === "text-primary-text" || token === "file:text-primary-text",
      );

    expect(characters("DeviceTable.tsx")).toEqual(["text-primary-text"]);
    expect(characters("TransactionFormModal.tsx")).toEqual([
      "file:text-primary-text",
    ]);
    for (const file of files) {
      const name = file.file.split("/").pop() ?? "";
      if (name !== "DeviceTable.tsx" && name !== "TransactionFormModal.tsx") {
        expect(characters(name)).toHaveLength(0);
      }
      // `-primary-text` never appears on a non-`text-` utility anywhere.
      expect(
        [...file.source.matchAll(/[\w:-]*-primary-text\b/g)].every((match) =>
          /(?:^|:)text-primary-text$/.test(match[0]),
        ),
      ).toBe(true);
    }
  });

  it("routes nine text-prefixed brand occurrences to the graphical token", () => {
    // Nine indigo, plus the one emerald Award glyph asserted separately.
    const perFile: ReadonlyArray<readonly [string, number]> = [
      ["AccessControlPage.tsx", 1],
      ["FacialTemplateSyncPanel.tsx", 1],
      ["GateMonitorPage.tsx", 2],
      ["RegisterDeviceModal.tsx", 1],
      ["CashBalanceCard.tsx", 1],
      ["CategoryTransactionDrilldown.tsx", 1],
      ["FinanceDashboardPage.tsx", 1],
      ["InvoicePreviewModal.tsx", 1],
    ];
    let total = 0;

    for (const [name, expected] of perFile) {
      expect(
        tokensOf(name).filter((token) => token === "text-primary"),
      ).toHaveLength(expected);
      total += expected;
    }
    expect(total).toBe(9);
    // No indigo of any prefix or variant survives anywhere in the trio.
    for (const file of files) {
      expect(file.source).not.toMatch(/\bindigo-/);
    }
  });

  it("sends the one page root to bg-background and nothing else", () => {
    // §1f case 1 as amended by the operator's ruling on APRAS-81 and
    // APRAS-83: an element that *is* the page takes `bg-background` whatever
    // its source class, and case 1 is consulted before the class's §1b row
    // and before case 2. `--background` and `--muted` are different colours
    // with different tenant behaviour — `_LIGHT_BACKGROUND` is a fixed
    // neutral, `_LIGHT_MUTED` is placed at the tenant hue — so this is the one
    // context-dependent choice of the migration a test can check.
    const roots = files.filter((file) =>
      tokensOf(file.file.split("/").pop() ?? "").includes("bg-background"),
    );

    expect(roots.map((file) => file.file)).toEqual([
      `${FINANCE}FinanceDashboardPage.tsx`,
    ]);
    expect(sourceOf("FinanceDashboardPage.tsx")).toContain(
      "min-h-screen bg-background",
    );
    // Read off the root's own class string, not the whole file: the page
    // carries `bg-card` on its header card and its panels, which is right.
    const root = /<div className="(min-h-screen[^"]*)"/.exec(
      sourceOf("FinanceDashboardPage.tsx"),
    )?.[1];

    expect(root?.split(/\s+/)).toContain("bg-background");
    for (const absent of [
      "bg-slate-50",
      "bg-muted",
      "bg-card",
      "dark:bg-slate-950",
    ]) {
      expect(matchesOn("FinanceDashboardPage.tsx", 48)).not.toContain(absent);
      expect(root?.split(/\s+/)).not.toContain(absent);
    }
    expect(tokensOf("FinanceDashboardPage.tsx")).not.toContain("bg-slate-50");
    // The other three roots declare no background class at all, so they are
    // untouched. `AccessControlPage` and `GateMonitorPage` are bare
    // `space-y-6` wrappers; `PurchaseRequestsPage`'s root is a `p-8` container
    // — the spec's prose calls all three `space-y-6`, which is right for the
    // first two only. What matters, and what is asserted, is that none of the
    // three declares a background class, so none is a page shell case 1
    // reaches.
    for (const [name, root] of [
      ["AccessControlPage.tsx", '<div className="space-y-6">'],
      ["GateMonitorPage.tsx", '<div className="space-y-6">'],
      ["PurchaseRequestsPage.tsx", '<div className="p-8 max-w-7xl mx-auto">'],
    ] as ReadonlyArray<readonly [string, string]>) {
      expect(sourceOf(name)).toContain(root);
      expect(/^\s*<div className="[^"]*"/m.exec(sourceOf(name))?.[0]).not.toMatch(
        /\bbg-/,
      );
    }
  });

  it("moves eleven neutral fills and exactly seven of them to bg-muted", () => {
    const occurrences = (needle: string) =>
      files.flatMap((file) =>
        tokensOf(file.file.split("/").pop() ?? "").filter(
          (token) => token === needle,
        ),
      );

    expect(occurrences("bg-muted")).toHaveLength(7);
    expect(occurrences("bg-background")).toHaveLength(1);
    // Five `hover:bg-accent` in all, not four: the four §1f case 2 interaction
    // fills (`InvoicePreviewModal:56`, `RegisterDeviceModal:61`,
    // `BudgetVsActualTable:73`, `PurchaseRequestsPage:199`) plus
    // `CategoryTransactionDrilldown:69`'s `hover:bg-indigo-50`, which reaches
    // `accent` through §1e's own brand-tint row rather than through case 2.
    expect(occurrences("hover:bg-accent")).toHaveLength(5);
    for (const [name, line] of [
      ["PurchaseRequestDetailModal.tsx", 271],
      ["PurchaseRequestFormModal.tsx", 295],
      ["QuoteFormModal.tsx", 497],
      ["SelectQuoteModal.tsx", 93],
      ["BudgetVsActualTable.tsx", 112],
      ["FacialTemplateSyncPanel.tsx", 64],
      ["InvoicePreviewModal.tsx", 63],
    ] as ReadonlyArray<readonly [string, number]>) {
      for (const gone of ["bg-gray-50", "bg-slate-50", "bg-slate-100"]) {
        expect(matchesOn(name, line)).not.toContain(gone);
      }
    }
  });

  it("splits emerald at two sites and red at six, and keeps the rest", () => {
    const KEPT = [
      "text-emerald-500",
      "text-emerald-600",
      "text-emerald-700",
      "text-emerald-900",
      "bg-emerald-50",
      "bg-emerald-100",
      "bg-emerald-500",
      "bg-emerald-50/40",
      "bg-emerald-50/60",
      "border-emerald-200",
      "border-emerald-300",
      "text-red-500",
      "text-red-600",
      "text-red-700",
      "bg-red-50",
      "bg-red-100",
      "bg-red-500",
      "border-red-200",
    ];
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source).map((match) => match.text),
    );
    const ledgered = new Set(rows.map((row) => row.class));

    for (const kept of KEPT) {
      expect(remaining).toContain(kept);
      expect(ledgered).toContain(kept);
    }
    // The download link is the only interactive emerald fill, so it is the
    // only one §1f case 3 migrates; the Award glyph is the only interactive
    // emerald control glyph.
    expect(sourceOf("InvoicePreviewModal.tsx")).not.toMatch(/\bemerald-/);
    expect(sourceOf("InvoicePreviewModal.tsx")).toContain(
      "bg-primary hover:bg-primary/90 text-primary-foreground",
    );
    expect(matchesOn("QuoteComparisonTable.tsx", 300)).toEqual([]);
    expect(tokensOf("QuoteComparisonTable.tsx")).toContain("text-primary");
    // The six free-standing `<Trash2/>` controls, and no seventh.
    const destructive: ReadonlyArray<readonly [string, number]> = [
      ["PurchaseRequestFormModal.tsx", 1],
      ["PurchaseRequestsPage.tsx", 1],
      ["QuoteComparisonTable.tsx", 2],
      ["QuoteFormModal.tsx", 2],
    ];
    let total = 0;

    for (const [name, expected] of destructive) {
      expect(
        tokensOf(name).filter((token) => token === "text-destructive"),
      ).toHaveLength(expected);
      total += expected;
    }
    expect(total).toBe(6);
    expect(matchesOn("AccessEventFeed.tsx", 29)).toContain("text-red-500");
  });

  it("carries every opacity modifier over verbatim and creates no brand-text alpha", () => {
    const occurrences = (needle: string) =>
      files.flatMap((file) =>
        tokensOf(file.file.split("/").pop() ?? "").filter(
          (token) => token === needle,
        ),
      );
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source).map((match) => match.text),
    );

    expect(occurrences("bg-foreground/70")).toHaveLength(1);
    expect(occurrences("hover:bg-primary/90")).toHaveLength(2);
    // The ten `bg-black/N` scrims are §1h code 1 and stay exactly as they are.
    expect(remaining.filter((text) => text === "bg-black/50")).toHaveLength(6);
    expect(remaining.filter((text) => text === "bg-black/60")).toHaveLength(3);
    expect(remaining.filter((text) => text === "bg-black/40")).toHaveLength(1);
    for (const file of files) {
      for (const dropped of [
        "bg-slate-950/70",
        "hover:bg-indigo-700",
        "hover:bg-emerald-700",
      ]) {
        expect(file.source).not.toContain(dropped);
      }
      expect(file.source).not.toMatch(/text-primary(?:-text)?\/\d/);
    }
  });

  it("deletes every dark: sibling of a migrated base and keeps exactly 51", () => {
    const DELETED = [
      "dark:bg-slate-900",
      "dark:text-white",
      "dark:text-slate-100",
      "dark:text-indigo-400",
      "dark:text-indigo-300",
      "dark:border-slate-700",
      "dark:border-indigo-900/50",
      "dark:bg-indigo-950",
      "dark:bg-indigo-950/40",
      "dark:bg-slate-950",
      "dark:bg-slate-900/60",
      "dark:bg-slate-800/40",
      "dark:hover:text-slate-200",
      "dark:hover:bg-slate-800",
      "dark:hover:bg-slate-800/50",
      "dark:hover:bg-indigo-950",
    ];
    const KEPT: ReadonlyArray<readonly [string, number]> = [
      ["dark:border-slate-800", 13],
      ["dark:text-red-400", 7],
      ["dark:text-emerald-400", 6],
      ["dark:bg-red-950/50", 4],
      ["dark:bg-emerald-950/50", 3],
      ["dark:text-slate-200", 3],
      ["dark:divide-slate-800/80", 2],
      ["dark:bg-amber-950/50", 2],
      ["dark:text-amber-400", 2],
      ["dark:border-red-900/50", 2],
      ["dark:text-slate-300", 2],
      ["dark:bg-slate-800", 1],
      ["dark:text-slate-400", 1],
      ["dark:bg-emerald-950", 1],
      ["dark:bg-red-950", 1],
      ["dark:text-slate-700", 1],
    ];
    const surviving = files.flatMap((file) =>
      matchesIn(file.file, file.source)
        .filter((match) => match.text.startsWith("dark:"))
        .map((match) => match.text),
    );
    const ledgered = new Set(rows.map((row) => row.class));

    for (const deleted of DELETED) {
      expect(surviving).not.toContain(deleted);
      expect(ledgered).not.toContain(deleted);
    }
    let total = 0;

    for (const [kept, expected] of KEPT) {
      expect(surviving.filter((text) => text === kept)).toHaveLength(expected);
      total += expected;
    }
    expect(total).toBe(51);
    expect(surviving).toHaveLength(51);
    expect(surviving.every((text) => ledgered.has(text))).toBe(true);

    // `purchase-management` had no `dark:` occurrence before and has none now.
    expect(
      files
        .filter((file) => file.file.startsWith(PURCHASES))
        .flatMap((file) => [...file.source.matchAll(/\bdark:/g)]),
    ).toHaveLength(0);
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of rows) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});

describe("APRAS-84's ledger arithmetic", () => {
  // Appended, directory-scoped, in the shape APRAS-79, APRAS-80, APRAS-82,
  // APRAS-81 and APRAS-83 established. Nothing above this line is edited by
  // this child beyond the four `MIGRATED_DIRECTORIES` entries and their eight
  // `toContain` assertions; the scan memo is already at module scope, hoisted
  // by APRAS-82, so this child verifies the hoist still holds under a larger
  // input and changes nothing.
  //
  // Four directories, because the operator scoped this child that way. What
  // makes them a coherent unit, and what no earlier child had: **not one of
  // the 351 occurrences carries a `dark:` variant**, so §1g never fires —
  // zero deletions, zero orphan siblings, zero `dark:` rows.
  const MEDIA = "src/features/media-management/components/";
  const FEEDBACK = "src/features/feedback-management/components/";
  const ANNOUNCEMENTS = "src/features/announcement-feed/components/";
  const PACKAGES = "src/features/package-management/components/";
  const DIRECTORIES = [MEDIA, FEEDBACK, ANNOUNCEMENTS, PACKAGES];
  const inDirectories = (file: string) =>
    DIRECTORIES.some((directory) => file.startsWith(directory));
  const rows = LEDGER.filter((row) => inDirectories(toSrcRelative(row.file)));
  const count = (code: string) =>
    rows.filter((row) => row.code === code).length;
  const files = PINNED.filter((file) => inDirectories(file.file));
  const sourceOf = (name: string) =>
    files.find((file) => file.file.endsWith(`/${name}`))?.source ?? "";
  const matchesOn = (name: string, line: number): string[] => {
    const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));

    return matchesIn(file?.file ?? "", file?.source ?? "")
      .filter((match) => match.line === line)
      .map((match) => match.text);
  };
  /**
   * One file's source as whole tokens, split on whitespace and on the
   * delimiters a class string can sit inside.
   *
   * Whole tokens, never substrings: `accent-primary` and
   * `accent-primary-foreground` are two tokens and neither matches the other,
   * which is the distinction §7's amendment turns on.
   */
  const tokensOf = (name: string): string[] =>
    sourceOf(name)
      .split(/[\s"'`{}()<>,;]+/)
      .filter((token) => token.length > 0);
  const occurrences = (needle: string) =>
    files.flatMap((file) =>
      tokensOf(file.file.split("/").pop() ?? "").filter(
        (token) => token === needle,
      ),
    );

  it("pins the four directories' five, five, five and one source files", () => {
    expect(PINNED.filter((file) => file.file.startsWith(MEDIA))).toHaveLength(
      5,
    );
    expect(
      PINNED.filter((file) => file.file.startsWith(FEEDBACK)),
    ).toHaveLength(5);
    expect(
      PINNED.filter((file) => file.file.startsWith(ANNOUNCEMENTS)),
    ).toHaveLength(5);
    expect(
      PINNED.filter((file) => file.file.startsWith(PACKAGES)),
    ).toHaveLength(1);
    // Sixteen, not the seventeen the task reported: `package-management` holds
    // one component, and its second non-test file is `hooks/usePackages.ts`,
    // which the non-recursive walk does not reach and which carries no palette
    // class. The occurrence count is unaffected.
    expect(files).toHaveLength(16);
  });

  it("logs 109 occurrences under six codes", () => {
    expect(rows).toHaveLength(109);
    expect(count("GAP-OUT-OF-BUDGET")).toBe(47);
    expect(count("GAP-TINT")).toBe(28);
    expect(count("GAP-NO-TOKEN")).toBe(14);
    expect(count("GAP-BORDER-100")).toBe(9);
    expect(count("GAP-OVERLAY")).toBe(8);
    // The first child to use the no-surface code outside the pilot.
    expect(count("GAP-NO-SURFACE")).toBe(3);
  });

  it("uses no code it does not account for", () => {
    expect(count("GAP-SWATCH")).toBe(0);
    expect(count("GAP-UNLISTED")).toBe(0);
    expect(rows.every((row) => row.task === "APRAS-84")).toBe(true);
  });

  it("leaves 109 of the quartet's 351 palette occurrences in place", () => {
    // 351 = 242 migrated + 109 left and logged, with no third term: §1g's
    // `dark:` half is empty on both sides here.
    const remainingIn = (directory: string) =>
      files
        .filter((file) => file.file.startsWith(directory))
        .flatMap((file) => matchesIn(file.file, file.source));
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source),
    );

    expect(remaining).toHaveLength(109);
    expect(remainingIn(MEDIA)).toHaveLength(49);
    expect(remainingIn(FEEDBACK)).toHaveLength(43);
    expect(remainingIn(ANNOUNCEMENTS)).toHaveLength(15);
    expect(remainingIn(PACKAGES)).toHaveLength(2);
    // The one file that migrates completely, with no ledger row.
    expect(matchesIn("", sourceOf("AnnouncementFeedPage.tsx"))).toHaveLength(0);
  });

  it("carries no `dark:` occurrence before or after, so §1g never fires", () => {
    // The whole of this child's risk sits in §1f, §1j and §1k. An implementer
    // who finds a `dark:` class in these four directories has mis-measured.
    for (const file of files) {
      expect(file.source).not.toMatch(/\bdark:/);
    }
    expect(
      rows.filter((row) => row.class.startsWith("dark:")),
    ).toHaveLength(0);
  });

  it("excepts the 80 distinct (file, class) pairs those 109 occupy", () => {
    const entries = EXCEPTIONS.filter((entry) => inDirectories(entry.file));
    const pairs = new Set(
      rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );

    expect(entries).toHaveLength(80);
    expect(pairs.size).toBe(80);
    expect(entries.every((entry) => entry.task === "APRAS-84")).toBe(true);
    expect(
      entries.filter((entry) => entry.file.startsWith(MEDIA)),
    ).toHaveLength(36);
    expect(
      entries.filter((entry) => entry.file.startsWith(FEEDBACK)),
    ).toHaveLength(33);
    expect(
      entries.filter((entry) => entry.file.startsWith(ANNOUNCEMENTS)),
    ).toHaveLength(9);
    expect(
      entries.filter((entry) => entry.file.startsWith(PACKAGES)),
    ).toHaveLength(2);
  });

  it("resolves the one class logged twice in one file by §1h precedence", () => {
    // `FeedbackInboxTable.tsx`'s `text-gray-700` is status set 1's neutral
    // `default` branch at line 19 and an ordinary table cell at line 82. The
    // ledger is per occurrence and carries a line, so both are logged under
    // their own code; the exceptions file is keyed `(file, class)` and carries
    // one, so the pair takes the earlier of the two in `GAP_CODES`, which is
    // declared in precedence order.
    const both = rows.filter(
      (row) =>
        toSrcRelative(row.file) === `${FEEDBACK}FeedbackInboxTable.tsx` &&
        row.class === "text-gray-700",
    );

    expect(both.map((row) => row.code).sort()).toEqual([
      "GAP-OUT-OF-BUDGET",
      "GAP-TINT",
    ]);
    expect(
      GAP_CODES.indexOf("GAP-TINT") < GAP_CODES.indexOf("GAP-OUT-OF-BUDGET"),
    ).toBe(true);
    expect(
      EXCEPTIONS.find(
        (entry) =>
          entry.file === `${FEEDBACK}FeedbackInboxTable.tsx` &&
          entry.class === "text-gray-700",
      )?.code,
    ).toBe("GAP-TINT");
  });

  it("carries no six-digit hex literal in any of the sixteen files", () => {
    for (const file of files) {
      expect(file.source).not.toMatch(hexGrammar());
    }
  });

  it("keeps all twelve status sets whole, each member still on its line", () => {
    // A ternary's or a lookup map's branches are one set. 44 classes over the
    // twelve sets, every one of them with a ledger row. Sets 1, 2, 5, 9, 10
    // and 11 are blocked by a family with no token (amber in five, rose in the
    // sixth); 4, 6, 7 and 8 are red tint triples; 3 is blocked by
    // `bg-emerald-50` and `text-emerald-900`; 12 is §1f case 3's
    // non-interactive status glyph.
    const sets: ReadonlyArray<readonly [string, number, readonly string[]]> = [
      // 1 — `getStatusBadgeClass`, three branches, the third of them neutral.
      ["FeedbackInboxTable.tsx", 15, ["bg-amber-50", "text-amber-700", "border-amber-200"]],
      ["FeedbackInboxTable.tsx", 17, ["bg-emerald-50", "text-emerald-700", "border-emerald-200"]],
      ["FeedbackInboxTable.tsx", 19, ["bg-gray-50", "text-gray-700", "border-gray-200"]],
      // 2 — the ANSWERED / PENDING ternary.
      ["FeedbackHistoryList.tsx", 66, ["bg-emerald-50", "text-emerald-700", "border-emerald-200"]],
      ["FeedbackHistoryList.tsx", 67, ["bg-amber-50", "text-amber-700", "border-amber-200"]],
      // 3 — the board-response panel.
      ["FeedbackDetailsView.tsx", 75, ["bg-emerald-50", "border-emerald-200"]],
      ["FeedbackDetailsView.tsx", 76, ["text-emerald-900"]],
      ["FeedbackDetailsView.tsx", 77, ["text-emerald-600"]],
      ["FeedbackDetailsView.tsx", 80, ["text-emerald-800"]],
      // 4 — the reject button, a destructive *control* that nonetheless stays.
      ["PhotoApprovalQueuePage.tsx", 106, ["text-red-700", "bg-red-50", "hover:bg-red-100", "border-red-200"]],
      // 5 — the "Tirar Outra" button.
      ["WebcamCaptureDialog.tsx", 157, ["text-amber-700", "bg-amber-50", "border-amber-300", "hover:bg-amber-100"]],
      // 6, 7 and 8 — the three error alerts, the same three classes each.
      ["PhotoApprovalQueuePage.tsx", 53, ["bg-red-50", "text-red-700", "border-red-200"]],
      ["PhotoUploadModal.tsx", 87, ["bg-red-50", "text-red-700", "border-red-200"]],
      ["WebcamCaptureDialog.tsx", 118, ["bg-red-50", "text-red-700", "border-red-200"]],
      // 9 — the pending count chip.
      ["PhotoApprovalQueuePage.tsx", 44, ["bg-amber-100", "text-amber-800"]],
      // 10 — the "Em Aprovação" badge.
      ["AvatarWithFallback.tsx", 48, ["bg-amber-500/90", "text-white"]],
      // 11 — the unread badge.
      ["FeedbackHistoryList.tsx", 51, ["bg-rose-500", "text-white"]],
      // 12 — the read-receipt glyph, §1f case 3's non-interactive branch.
      ["AnnouncementCard.tsx", 53, ["text-emerald-600"]],
    ];
    const ledgered = new Set(
      rows.map((row) => `${row.class} in ${toSrcRelative(row.file)}`),
    );
    let members = 0;

    for (const [name, line, classes] of sets) {
      const onThatLine = matchesOn(name, line);
      const file = files.find((pinned) => pinned.file.endsWith(`/${name}`));
      for (const member of classes) {
        expect(onThatLine).toContain(member);
        expect(ledgered).toContain(`${member} in ${file?.file ?? ""}`);
        members += 1;
      }
    }
    expect(members).toBe(44);
  });

  it("splits no status set: no span mixes a migrated class with a kept tint", () => {
    // The same mechanical check the siblings ran, over this child's targets.
    // This is the first child with **zero** mixed spans: no
    // `QuoteComparisonTable`-shaped span occurs here. Spans mixing a migrated
    // occurrence with a kept occurrence under any *other* code are expected
    // and not counted — `FeedbackDetailsView:49`'s category chip, where
    // `bg-gray-100` and `border-gray-200` migrate beside a kept
    // out-of-budget `text-gray-800`, is the commonest shape.
    const MIGRATED_TARGETS = [
      "bg-card",
      "bg-card/80",
      "bg-card/70",
      "hover:bg-card",
      "focus:bg-card",
      "bg-muted",
      "bg-accent",
      "hover:bg-accent",
      "hover:bg-accent/80",
      "bg-primary",
      "hover:bg-primary/90",
      "bg-foreground",
      "bg-destructive",
      "hover:bg-destructive",
      "border-border",
      "border-input",
      "border-primary",
      "focus:ring-ring",
      "accent-primary-foreground",
      "text-foreground",
      "text-muted-foreground",
      "hover:text-muted-foreground",
      "text-primary",
      "hover:text-primary",
      "text-primary-text",
      "hover:text-primary-text",
      "text-primary-foreground",
      "text-destructive",
      "hover:text-destructive",
      "text-destructive-foreground",
    ];
    const target = new RegExp(
      String.raw`(?<![\w-])(?:${MIGRATED_TARGETS.map((name) =>
        name.replace("/", String.raw`\/`),
      ).join("|")})(?![\w-])`,
      "g",
    );
    const tinted = new Set(
      rows
        .filter((row) => row.code === "GAP-TINT")
        .map(
          (row) => `${toSrcRelative(row.file)} :: ${row.line} :: ${row.class}`,
        ),
    );
    const mixed: string[] = [];

    for (const { file, source } of files) {
      for (const [start, end] of classContexts(source)) {
        const span = source.slice(start, end);
        if ([...span.matchAll(target)].length === 0) {
          continue;
        }
        for (const match of span.matchAll(paletteGrammar())) {
          const line = lineOf(source, start + (match.index ?? 0));
          if (tinted.has(`${file} :: ${line} :: ${match[0]}`)) {
            mixed.push(`${file}:${line} ${match[0]}`);
            break;
          }
        }
      }
    }

    expect([...new Set(mixed)]).toEqual([]);
  });

  it("routes exactly four brand-text occurrences to the character token", () => {
    // §1k: the element paints glyphs of text, so the floor is 4.5:1 and the
    // token is `*-primary-text`. Two call sites, two occurrences each — the
    // resting class and its `hover:` variant. `FeedbackInboxTable`'s is §1k's
    // "mixed element wins for text": one `currentColor` paints both the
    // `<Eye/>` and the label "Ver Detalhes".
    const characters = (name: string) =>
      tokensOf(name).filter(
        (token) =>
          token === "text-primary-text" || token === "hover:text-primary-text",
      );

    expect(characters("PhotoUploadModal.tsx").sort()).toEqual([
      "hover:text-primary-text",
      "text-primary-text",
    ]);
    expect(characters("FeedbackInboxTable.tsx").sort()).toEqual([
      "hover:text-primary-text",
      "text-primary-text",
    ]);
    for (const file of files) {
      const name = file.file.split("/").pop() ?? "";
      if (name !== "PhotoUploadModal.tsx" && name !== "FeedbackInboxTable.tsx") {
        expect(characters(name)).toHaveLength(0);
      }
      // `-primary-text` never appears on a non-`text-` utility anywhere.
      expect(
        [...file.source.matchAll(/[\w:-]*-primary-text\b/g)].every((match) =>
          /(?:^|:)text-primary-text$/.test(match[0]),
        ),
      ).toBe(true);
    }
  });

  it("routes nine text-prefixed brand occurrences to the graphical token", () => {
    const perFile: ReadonlyArray<readonly [string, number]> = [
      ["FeedbackChannelPage.tsx", 2],
      ["AnnouncementFeedPage.tsx", 1],
      ["AnnouncementFormModal.tsx", 2],
      ["PackageStatusPage.tsx", 1],
      ["NewFeedbackForm.tsx", 1],
      ["FeedbackHistoryList.tsx", 1],
    ];
    let total = 0;

    for (const [name, expected] of perFile) {
      expect(
        tokensOf(name).filter((token) => token === "text-primary"),
      ).toHaveLength(expected);
      total += expected;
    }
    // The ninth is `AnnouncementCard`'s `hover:` variant.
    expect(
      tokensOf("AnnouncementCard.tsx").filter(
        (token) => token === "hover:text-primary",
      ),
    ).toHaveLength(1);
    expect(total + 1).toBe(9);
    // No indigo of any prefix or variant survives anywhere in the quartet.
    for (const file of files) {
      expect(file.source).not.toMatch(/\bindigo-/);
    }
  });

  it("puts the brand on the zoom-slider track and its foreground on the thumb", () => {
    // §7, the one operator-authorised decision this child carries. The track
    // takes the tenant's brand and the thumb takes the token the theme
    // guarantees is legible on it — the swap of the colour-carrying roles the
    // operator chose after every other candidate was measured. Both halves are
    // graphical (an `<input type="range">` paints no glyphs), so 3:1 is the
    // floor for both, and both clear it: 3.0427 and 5.7588.
    const slider = /<input\b[\s\S]*?className="([^"]*)"[\s\S]*?\/>/.exec(
      sourceOf("AvatarCropEditor.tsx"),
    )?.[1];
    const tokens = (slider ?? "").split(/\s+/);

    expect(tokens).toContain("bg-primary");
    expect(tokens).toContain("accent-primary-foreground");
    // Whitespace-split token equality, so `accent-primary` does not match
    // `accent-primary-foreground` — the distinction §7 turns on.
    for (const absent of [
      "bg-muted",
      "bg-slate-300",
      "accent-indigo-600",
      "accent-primary",
    ]) {
      expect(tokens).not.toContain(absent);
    }
    // The panel that encloses the slider is the `bg-muted` the track is
    // measured against.
    expect(sourceOf("AvatarCropEditor.tsx")).toContain(
      "p-4 bg-muted rounded-lg border border-border",
    );
    // §1i: one class swapped for one class, none added and none removed.
    expect(tokens).toHaveLength(7);
    // Neither source class survives anywhere in the quartet, and neither is
    // logged — both migrate.
    for (const file of files) {
      expect(file.source).not.toContain("bg-slate-300");
      expect(file.source).not.toContain("accent-indigo");
    }
    expect(rows.some((row) => row.class === "bg-slate-300")).toBe(false);
  });

  it("produces bg-primary 14 times and bg-muted 24, with no bg-slate-300 among them", () => {
    // 11 from `bg-indigo-600`, 2 from `bg-emerald-600` and 1 from the slider
    // track — which is *not* §1f case 2, whose candidate set is `muted` /
    // `accent` and whose scope is the 50/100/200 scales.
    expect(occurrences("bg-primary")).toHaveLength(14);
    // `bg-slate-50` 9, `bg-gray-50` 7 of 8, `bg-gray-100` 6, and one each of
    // `bg-slate-100` and `bg-slate-200`.
    expect(occurrences("bg-muted")).toHaveLength(24);
    // 15 §1f case 2 interaction fills plus `hover:bg-indigo-100`, which
    // reaches `accent` through §1e's own brand-tint row rather than case 2.
    expect(occurrences("hover:bg-accent")).toHaveLength(16);
    expect(occurrences("bg-accent")).toHaveLength(4);
  });

  it("sends all 41 white surfaces to the card family and none to background", () => {
    // §1f case 1. No white fill here is a page shell: the four page roots are
    // bare `container`/`p-6` wrappers carrying no background class at all, so
    // the page surface is `App.tsx`'s `min-h-screen bg-background` and nothing
    // here competes with it. None is a floating layer with popover semantics.
    expect(occurrences("bg-card")).toHaveLength(34);
    expect(occurrences("focus:bg-card")).toHaveLength(2);
    expect(occurrences("hover:bg-card")).toHaveLength(2);
    expect(occurrences("bg-card/80")).toHaveLength(2);
    expect(occurrences("bg-card/70")).toHaveLength(1);
    expect(occurrences("bg-background")).toHaveLength(0);
    expect(occurrences("bg-popover")).toHaveLength(0);
    // The two `focus:bg-white` selects are the one genuinely new shape: their
    // resting fill is case 2's `bg-muted` and their focus fill is case 1's
    // `bg-card`, because case 2's candidate set does not contain `card` and
    // case 1's does not contain `accent`.
    expect(sourceOf("FeedbackChannelPage.tsx")).toContain(
      "bg-muted focus:bg-card",
    );
    // The four page roots declare no background class at all.
    for (const name of [
      "FeedbackChannelPage.tsx",
      "AnnouncementFeedPage.tsx",
      "PackageStatusPage.tsx",
      "PhotoApprovalQueuePage.tsx",
    ]) {
      expect(/^\s*<div className="[^"]*"/m.exec(sourceOf(name))?.[0]).not.toMatch(
        /\bbg-/,
      );
    }
  });

  it("splits emerald four to twelve and red five to thirteen", () => {
    // The two interactive emerald fills migrate, carrying their `hover:` with
    // them; the other twelve are status tints or glyphs and stay.
    for (const name of ["PhotoApprovalQueuePage.tsx", "PackageStatusPage.tsx"]) {
      expect(sourceOf(name)).toContain(
        "bg-primary hover:bg-primary/90",
      );
    }
    expect(occurrences("hover:bg-primary/90")).toHaveLength(12);
    // Five red occurrences migrate. The confirm-reject button at :150 is a
    // solid fill with every member rowed; the reject button at :106 is the
    // free-standing destructive control §1j would send to `text-destructive`,
    // except that its `text-red-700` shares a class string with two rowless
    // classes, so the unit rule freezes the whole set. A reviewer should check
    // precisely these two against each other.
    expect(matchesOn("PhotoApprovalQueuePage.tsx", 150)).toEqual([]);
    expect(matchesOn("PhotoApprovalQueuePage.tsx", 106)).toHaveLength(4);
    expect(occurrences("text-destructive-foreground")).toHaveLength(1);
    expect(occurrences("bg-destructive")).toHaveLength(1);
    // §1e gives `bg-red-700` the plain `*-destructive` row with no `/90`
    // target, so this pair loses its interaction distinction and §1i forbids
    // repairing it in place.
    expect(occurrences("hover:bg-destructive")).toHaveLength(1);
    expect(occurrences("text-destructive")).toHaveLength(1);
    expect(occurrences("hover:text-destructive")).toHaveLength(2);
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source).map((match) => match.text),
    );

    expect(
      remaining.filter((text) => /-emerald-/.test(text)),
    ).toHaveLength(12);
    expect(remaining.filter((text) => /-red-/.test(text))).toHaveLength(13);
  });

  it("carries every opacity modifier over verbatim and creates no brand-text alpha", () => {
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source).map((match) => match.text),
    );

    expect(occurrences("bg-card/80")).toHaveLength(2);
    expect(occurrences("bg-card/70")).toHaveLength(1);
    expect(occurrences("hover:bg-accent/80")).toHaveLength(2);
    // The eight `bg-black/N` scrims are §1h code 1 and stay as they are; the
    // three floating white surfaces in `MediaCarousel` are controls and an
    // indicator painted *on top of* media, not scrims, so code 1 does not
    // reach them and the §1b row governs.
    expect(remaining.filter((text) => text === "bg-black/20")).toHaveLength(1);
    expect(remaining.filter((text) => text === "bg-black/40")).toHaveLength(3);
    expect(remaining.filter((text) => text === "bg-black/60")).toHaveLength(3);
    expect(remaining.filter((text) => text === "bg-black/80")).toHaveLength(1);
    expect(remaining.filter((text) => text === "bg-amber-500/90")).toHaveLength(
      1,
    );
    for (const file of files) {
      for (const dropped of [
        "hover:bg-indigo-700",
        "hover:bg-emerald-700",
        "hover:bg-gray-50/80",
        "bg-white/",
      ]) {
        expect(file.source).not.toContain(dropped);
      }
      // No APRAS-90 site: every opacity modifier this child carries or creates
      // is a background utility.
      expect(file.source).not.toMatch(/text-primary(?:-text)?\/\d/);
    }
  });

  it("keeps text-white at exactly the three rowless surfaces", () => {
    const remaining = files.flatMap((file) =>
      matchesIn(file.file, file.source).filter(
        (match) => match.text === "text-white",
      ),
    );

    expect(remaining.map((match) => match.file).sort()).toEqual(
      [
        `${FEEDBACK}FeedbackHistoryList.tsx`,
        `${MEDIA}AvatarWithFallback.tsx`,
        `${MEDIA}PhotoApprovalQueuePage.tsx`,
      ].sort(),
    );
    expect(
      rows.filter((row) => row.class === "text-white").map((row) => row.code),
    ).toEqual(["GAP-NO-SURFACE", "GAP-NO-SURFACE", "GAP-NO-SURFACE"]);
    // The other thirteen baseline occurrences.
    expect(occurrences("text-primary-foreground")).toHaveLength(12);
    expect(occurrences("text-destructive-foreground")).toHaveLength(1);
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of rows) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});
