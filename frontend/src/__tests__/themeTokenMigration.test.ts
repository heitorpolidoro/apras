/// <reference types="node" />
// @vitest-environment node
//
// The migration guard (APRAS-78, deliverable 3).
//
// APRAS-85 closed the guard. `SCANNED_ROOTS` is the single recursive `src`
// entry that replaced APRAS-78's allow-list of `MIGRATED_DIRECTORIES`, so the
// guard is now a repo-wide deny: every non-test `.ts`/`.tsx` file under
// `frontend/src` has been through the class -> token migration described in
// `docs/frontend/theme-token-mapping.md`, and no Tailwind palette class may
// appear anywhere in the tree. The guard re-reads every file with `node:fs`
// and fails on any match of the §3b grammar that is not listed, as an exact
// `(file, class)` pair, in `themeTokenMigration.exceptions.json`.
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
 * The roots the guard scans (§3a, §3d).
 *
 * APRAS-78 seeded an allow-list of migrated directories and each sibling
 * appended its own; APRAS-85, the closer, inverted it into the repo-wide deny
 * this single recursive entry expresses. Everything the inversion needed was
 * already in place: `pinnedFiles()` honours the `/**` recursion marker,
 * `collect()` skips `__tests__` directories, `isSource()` skips
 * `*.test.ts(x)`, and every exceptions entry is `src/`-relative — which is
 * what §3d was designed for.
 *
 * From here on a palette class in a file **no child ever migrated** fails CI
 * too, so the guard's promise needs no directory qualifier.
 */
export const SCANNED_ROOTS: readonly string[] = ["src/**"];

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
// The side qualifier `(?:-[trblxyse])?` on `border` and on `divide` is
// APRAS-85 job (c)'s amendment to APRAS-78's published §3b, made under the
// operator authorisation recorded on that task. The sixteen alternatives are
// the pre-amendment sixteen, in the pre-amendment order, none added and none
// dropped: `describe("the widened prefix")` pins each one by name.
const PREFIX = String.raw`(?:bg|text|border(?:-[trblxyse])?|ring|outline|divide(?:-[trblxyse])?|placeholder|caret|accent|decoration|shadow|fill|stroke|from|via|to)`;
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

/** Every source file a `SCANNED_ROOTS` entry pins, `src/`-relative. */
export const pinnedFiles = (
  entries: readonly string[] = SCANNED_ROOTS,
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
 * Everything `violations` needs to know about one file, derived once.
 *
 * `matches` is `matchesIn`'s output verbatim. The other two are the same
 * information in the shapes the two hot loops actually ask for, so neither
 * loop has to build a string or a set of its own:
 *
 * - `keys` is `key(file, match.text)` for each match, at the same index, for
 *   the guard loop's excused-or-not test;
 * - `classes` is the distinct match texts, for the exception loop's "does this
 *   class still appear in this file?" test, which was a linear `.some()` over
 *   every match in the file on every one of the calls
 *   `it("fails when any single exception is removed")` makes.
 */
interface FileScan {
  matches: Match[];
  keys: string[];
  classes: Set<string>;
}

/**
 * The per-file derivation, memoised at module scope on the file path *and* its
 * source.
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
 * that has never been seen, and still bite. The key covers everything all
 * three fields are derived from — `matchesIn(file, source)` and nothing else —
 * which is what keeps a memo hit from returning a stale scan and letting the
 * removal test pass when it should fail.
 */
const SCAN_MEMO = new Map<string, Map<string, FileScan>>();

const scanOf = (file: string, source: string): FileScan => {
  let bySource = SCAN_MEMO.get(file);
  if (bySource === undefined) {
    bySource = new Map<string, FileScan>();
    SCAN_MEMO.set(file, bySource);
  }
  const cached = bySource.get(source);
  if (cached !== undefined) {
    return cached;
  }
  const matches = matchesIn(file, source);
  const derived: FileScan = {
    matches,
    keys: matches.map((match) => key(file, match.text)),
    classes: new Set(matches.map((match) => match.text)),
  };
  bySource.set(source, derived);
  return derived;
};

/**
 * Rules 1–3 for one exception entry, memoised on the entry object.
 *
 * The three checks — key shape, closed code set, exact pair — read nothing but
 * the entry, so they are a pure function of it and a `WeakMap` on the object
 * is a sound memo: an entry with different keys, a different code or a glob is
 * a different object and misses the memo, so all three assertions still bite.
 *
 * APRAS-85's reason for adding it to the two optimisations its spec names:
 * `it("fails when any single exception is removed")` calls `violations()` once
 * per exception, so with 882 exceptions these three checks — one of them an
 * `Object.keys().sort().join()` — ran 778,000 times and put that one test over
 * its 2 s budget on their own.
 */
const ENTRY_PROBLEMS = new WeakMap<Exception, readonly string[]>();

/**
 * `key(entry.file, entry.class)` for one entry, memoised on the entry object.
 *
 * A pure function of the two fields the key is built from, and an entry with a
 * different `file` or `class` is a different object that misses the memo. It
 * exists so the `excused` set — rebuilt on every call, because a call whose
 * exceptions differ must get a different set — is 882 insertions of strings
 * that already exist rather than 882 string concatenations.
 */
const ENTRY_KEYS = new WeakMap<Exception, string>();

const entryKey = (entry: Exception): string => {
  const cached = ENTRY_KEYS.get(entry);
  if (cached !== undefined) {
    return cached;
  }
  const built = key(entry.file, entry.class);
  ENTRY_KEYS.set(entry, built);
  return built;
};

const entryProblems = (entry: Exception): readonly string[] => {
  const cached = ENTRY_PROBLEMS.get(entry);
  if (cached !== undefined) {
    return cached;
  }
  const found: string[] = [];
  const keys = Object.keys(entry).sort().join(",");
  if (keys !== "class,code,file,task") {
    found.push(
      `exception for ${entry.class} in ${entry.file} must have exactly the keys file, class, code, task (has ${keys})`,
    );
  }
  if (!GAP_CODES.includes(entry.code)) {
    found.push(
      `unknown code "${entry.code}" on ${entry.class} in ${entry.file}; use one of ${GAP_CODES.join(", ")} — see docs/frontend/theme-token-mapping.md §1h`,
    );
  }
  if (/[*?]/.test(entry.file) || /[*?]/.test(entry.class)) {
    found.push(
      `exception ${entry.file} / ${entry.class} is not an exact pair; globs and directory-wide entries are refused (§3c rule 3)`,
    );
  }
  ENTRY_PROBLEMS.set(entry, found);
  return found;
};

/** One file's entry in the file index, plus its derived scan. */
interface IndexedFile {
  file: string;
  source: string;
  scan: FileScan;
}

/** `files` as a path index and as the set of pinned paths. */
interface FileIndex {
  byPath: Map<string, IndexedFile>;
  pinned: Set<string>;
}

/**
 * `files` indexed by path and as a set of paths, and `ledger` prepared as its
 * `(file, class)` keys, memoised on the argument array itself.
 *
 * The same reason as `keyShape` above, and the reason the removal test's cost
 * stopped scaling with the corpus: these derivations depend on `files` and on
 * `ledger`, **not** on `exceptions`, so they are invariant across all 882 calls
 * `it("fails when any single exception is removed")` makes and rebuilding them
 * per call — a 262-entry map, a 262-entry set and a 1,197-key set, plus 2,394
 * string concatenations — was most of what that test spent. Both arguments are
 * typed `readonly`, and every test that hands `violations` a mutated input
 * builds a **new** array — so identity is a sound memo key here, and a fresh
 * array always misses the memo and is rebuilt.
 */
const FILE_INDEX = new WeakMap<object, FileIndex>();

const indexFiles = (
  files: ReadonlyArray<{ file: string; source: string }>,
): FileIndex => {
  const cached = FILE_INDEX.get(files);
  if (cached !== undefined) {
    return cached;
  }
  const index: FileIndex = {
    byPath: new Map(
      files.map((file) => [
        file.file,
        { ...file, scan: scanOf(file.file, file.source) },
      ]),
    ),
    pinned: new Set(files.map((file) => file.file)),
  };
  FILE_INDEX.set(files, index);
  return index;
};

/** One ledger row reduced to what rule 4's ledger-to-exception pass reads. */
interface IndexedRow {
  row: LedgerRow;
  file: string;
  key: string;
}

/** `ledger` as the set of its keys and as those keys row by row. */
interface LedgerIndex {
  keys: Set<string>;
  rows: IndexedRow[];
}

const LEDGER_INDEX = new WeakMap<object, LedgerIndex>();

const indexLedger = (ledger: readonly LedgerRow[]): LedgerIndex => {
  const cached = LEDGER_INDEX.get(ledger);
  if (cached !== undefined) {
    return cached;
  }
  const rows = ledger.map((row) => {
    const file = toSrcRelative(row.file);

    return { row, file, key: key(file, row.class) };
  });
  const index: LedgerIndex = {
    keys: new Set(rows.map((indexed) => indexed.key)),
    rows,
  };
  LEDGER_INDEX.set(ledger, index);
  return index;
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
  // Everything derived from `files` and from `ledger` is hoisted into the two
  // module-scope memos above, and every `(file, class)` key this function
  // compares is built there too. What is left inside the three loops is a set
  // insertion or a set lookup per item and no allocation at all, which is what
  // makes the cost of one call to this function independent of how many other
  // calls `it("fails when any single exception is removed")` is making around
  // it — 882 calls over 262 files, with 1,197 matches and 1,197 ledger rows.
  const { byPath, pinned } = indexFiles(files);
  const ledgered = indexLedger(ledger);
  const excused = new Set<string>();
  for (const entry of exceptions) {
    excused.add(entryKey(entry));
  }

  // Rules 1–3, plus rule 4 in the exception-to-ledger direction.
  for (const entry of exceptions) {
    // Guarded rather than an unconditional spread: `entryProblems` returns the
    // same empty array 882 times out of 882 on a clean tree, and spreading it
    // anyway was 882 × 882 spread calls for no result.
    const shape = entryProblems(entry);
    if (shape.length > 0) {
      problems.push(...shape);
    }
    const indexed = byPath.get(entry.file);
    if (indexed === undefined) {
      problems.push(
        `exception names ${entry.file}, which is not a source file under a pinned directory (§3c rule 2)`,
      );
      continue;
    }
    if (!indexed.scan.classes.has(entry.class)) {
      problems.push(
        `stale exception: ${entry.class} no longer appears in ${entry.file} (§3c rule 2)`,
      );
    }
    if (!ledgered.keys.has(entryKey(entry))) {
      problems.push(
        `exception ${entry.class} in ${entry.file} has no matching row in docs/frontend/unmapped-colours.md (§3c rule 4)`,
      );
    }
  }

  // Rule 4, the ledger-to-exception direction.
  for (const indexed of ledgered.rows) {
    if (!pinned.has(indexed.file)) {
      continue;
    }
    if (!excused.has(indexed.key)) {
      problems.push(
        `ledger row ${indexed.row.class} in ${indexed.row.file} has no entry in themeTokenMigration.exceptions.json (§3c rule 4)`,
      );
    }
  }

  // The guard proper.
  for (const { file, source } of files) {
    const { matches, keys } = scanOf(file, source);
    for (let index = 0; index < matches.length; index += 1) {
      if (excused.has(keys[index])) {
        continue;
      }
      const match = matches[index];
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

  // The one test in the suite with an explicit timeout, and the reason is
  // recorded here rather than inherited from Vitest's 5 s default: this test
  // calls `violations()` once per exception — 882 calls today and one more for
  // every exception any future work adds — so it is the only test whose cost
  // grows with the corpus. Measured at HEAD it runs in ~390 ms in isolation,
  // but it is the guard that closes tree coverage for the whole APRAS-77
  // umbrella and CI runs it on a two-core runner under contention from 178
  // other test files. 20 s is ~50× the measured cost: wide enough that a
  // loaded runner cannot make it flake, narrow enough that a regression which
  // put the shape back to quadratic would still fail here rather than hang.
  // Whoever trips this limit should fix the shape, not raise the number.
  it(
    "fails when any single exception is removed",
    () => {
      for (let index = 0; index < EXCEPTIONS.length; index += 1) {
        const without = EXCEPTIONS.filter((_, at) => at !== index);

        expect(violations(PINNED, without, LEDGER)).not.toEqual([]);
      }
    },
    20_000,
  );

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

describe("the widened prefix", () => {
  // Job (c) of APRAS-85, under the operator authorisation recorded on that
  // task: §3b's `prefix` production gains an optional single-letter side
  // qualifier on `border` and on `divide`, so side-qualified utilities
  // (`border-t-slate-400`, `divide-y-gray-100`) stop sitting outside the
  // grammar. Appended, never written into APRAS-78's own
  // `describe("the §3b grammar")` block, whose fourteen cases were re-run
  // against the widened production and all still hold.
  const SIDE_QUALIFIER = "(?:-[trblxyse])?";

  /** The published production as it read before job (c), derived from the
   *  widened one by removing the two side qualifiers — so the test proves the
   *  two productions differ in exactly those two places and nowhere else. */
  const preAmendmentGrammar = (): RegExp =>
    new RegExp(paletteGrammar().source.split(SIDE_QUALIFIER).join(""), "g");

  /** Whether the grammar matches `input` as a whole, not as a prefix of it. */
  const matchesWhole = (input: string): boolean => {
    const found = input.match(paletteGrammar());

    return found !== null && found.length === 1 && found[0] === input;
  };

  it("differs from the pre-amendment production in exactly two places", () => {
    expect(paletteGrammar().source.split(SIDE_QUALIFIER)).toHaveLength(3);
    expect(preAmendmentGrammar().source).not.toContain(SIDE_QUALIFIER);
  });

  it.each([
    "border-t-slate-400",
    "divide-y-gray-100",
    "border-x-slate-200",
    "border-s-red-500",
    "border-e-white",
    "dark:hover:border-b-amber-500/40",
  ])("matches the side-qualified %s whole", (candidate) => {
    expect(matchesWhole(candidate)).toBe(true);
  });

  it.each([
    // A side qualifier on a prefix that never takes one.
    "bg-t-slate-400",
    "text-x-gray-500",
    "ring-t-blue-500",
    // Two letters is not a Tailwind side qualifier.
    "border-tr-slate-400",
    // Widths, keywords and near-misses the widening must still refuse.
    "border-t-2",
    "divide-y-reverse",
    "border-collapse",
    "border-t-slate-4000",
    "border-t-mauve-400",
    // The boundary lookarounds, the specific thing a widened alternation can
    // break.
    "xborder-t-red-500",
    "order-t-red-500",
  ])("refuses %s entirely", (candidate) => {
    expect(candidate.match(paletteGrammar())).toBeNull();
  });

  it.each([
    "bg-slate-800",
    "text-gray-500",
    "border-slate-100",
    "ring-blue-500",
    "outline-gray-300",
    "divide-gray-200",
    "placeholder-gray-400",
    "caret-slate-500",
    // `accent` earns its place in the list: the tree's one `accent` palette
    // occurrence was migrated away by APRAS-84, so an alternative dropped
    // while rewriting the production would move no count anywhere and only
    // this assertion would notice.
    "accent-indigo-600",
    "decoration-sky-500",
    "shadow-slate-900",
    "fill-emerald-600",
    "stroke-rose-500",
    "from-blue-500",
    "via-purple-500",
    "to-pink-500",
  ])("keeps the alternative that matches %s", (candidate) => {
    expect(matchesWhole(candidate)).toBe(true);
  });

  it("describes the same grammar as the published production in §3b", () => {
    // The document and the code are one grammar. The production is quoted out
    // of the file rather than retyped, so a drift in either direction fails
    // here instead of being noticed by nobody.
    const document = readFileSync(
      path.join(REPO_ROOT, "docs", "frontend", "theme-token-mapping.md"),
      "utf8",
    );
    const quoted = /prefix\s+= (\(\?:bg[\s\S]*?to\))/.exec(document);
    expect(quoted).not.toBeNull();
    const production = (quoted?.[1] ?? "").replace(/\s+/g, "");

    expect(production).toContain("border(?:-[trblxyse])?");
    expect(production).toContain("divide(?:-[trblxyse])?");
    expect(paletteGrammar().source).toContain(production);
    // Sixteen alternatives, in the published order, none added and none
    // dropped — `accent` included.
    expect(
      production
        .slice("(?:".length, -")".length)
        .split("|")
        .map((alternative) => alternative.replace("(?:-[trblxyse])?", "")),
    ).toEqual([
      "bg",
      "text",
      "border",
      "ring",
      "outline",
      "divide",
      "placeholder",
      "caret",
      "accent",
      "decoration",
      "shadow",
      "fill",
      "stroke",
      "from",
      "via",
      "to",
    ]);
  });

  it("newly catches exactly TaskBoard's five header stripes, tree-wide", () => {
    const sites = (grammar: RegExp) => {
      const found = new Set<string>();
      for (const { file, source } of PINNED) {
        for (const match of source.matchAll(grammar)) {
          found.add(`${file}:${lineOf(source, match.index)}:${match[0]}`);
        }
      }
      return found;
    };
    const widened = sites(paletteGrammar());
    const before = sites(preAmendmentGrammar());
    const STRIPES = "src/features/task-management/components/TaskBoard.tsx";

    // The old-only difference is empty: the amendment narrowed nothing and
    // lost no alternative.
    expect([...before].filter((site) => !widened.has(site))).toEqual([]);
    expect([...widened].filter((site) => !before.has(site)).sort()).toEqual([
      `${STRIPES}:100:border-t-red-400`,
      `${STRIPES}:76:border-t-slate-400`,
      `${STRIPES}:82:border-t-blue-400`,
      `${STRIPES}:88:border-t-amber-500`,
      `${STRIPES}:94:border-t-green-400`,
    ]);
  });

  it("finds no other side-qualified palette class anywhere under src", () => {
    // Every *palette* match whose utility carries a side qualifier. Width and
    // keyword utilities (`border-b-2`, `divide-y-reverse`) are outside the
    // grammar and so outside this set, which is the point of the widening:
    // it admits palette classes only.
    const qualified = /^(?:[^:]*:)*(?:border|divide)-[trblxyse]-/;
    const found = PINNED.flatMap(({ source }) =>
      [...source.matchAll(paletteGrammar())]
        .map((match) => match[0])
        .filter((text) => qualified.test(text)),
    );

    expect(found.filter((text) => !text.startsWith("border-t-"))).toEqual([]);
    expect(found).toHaveLength(5);
  });
});

describe("SCANNED_ROOTS — the repo-wide deny", () => {
  // Replaces the retired allow-list block, which asserted membership of
  // `MIGRATED_DIRECTORIES` and that `PINNED` held nothing outside the pinned
  // roots — the two properties the inversion abolishes. These assertions are
  // the opposite and stronger ones. The retired name is spelled nowhere in
  // this file as a declaration or as a block title, which is what the second
  // test below checks.
  const SELF = readFileSync(
    path.join(HERE, "themeTokenMigration.test.ts"),
    "utf8",
  );

  /** A recursive walk of `frontend/src`, written independently of `collect`,
   *  so `pinnedFiles()` is compared against something and not against
   *  itself. */
  const walk = (directory: string): string[] => {
    const found: string[] = [];
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const full = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        if (entry.name !== "__tests__") {
          found.push(...walk(full));
        }
      } else if (/\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)) {
        found.push(path.relative(FRONTEND_ROOT, full).split(path.sep).join("/"));
      }
    }
    return found;
  };

  it("is exactly the single recursive src entry", () => {
    expect(SCANNED_ROOTS).toEqual(["src/**"]);
  });

  it("leaves no MIGRATED_DIRECTORIES binding or block behind", () => {
    // The retired name is spelled in two pieces, so this assertion's own
    // source does not satisfy the substring it refuses.
    const retired = `${"MIGRATED"}_DIRECTORIES`;

    expect(SELF).not.toContain(`export const ${retired}`);
    expect(SELF).not.toContain(`describe("${retired}"`);
  });

  it("pins every non-test source file under frontend/src", () => {
    // An equality against an independently computed walk, never a literal:
    // 262 files at this HEAD, and the number moves whenever any task adds a
    // component. The property that matters is that the two walks agree.
    const independent = walk(path.join(FRONTEND_ROOT, "src")).sort();

    expect(pinnedFiles()).toEqual(independent);
    expect(PINNED.map((file) => file.file)).toEqual(independent);
  });

  it("reaches files no child ever migrated and nested directories", () => {
    const files = PINNED.map((file) => file.file);

    // Two files no `MIGRATED_DIRECTORIES` entry ever named, carrying no
    // palette class — the guard now defends them anyway.
    expect(files).toContain("src/App.tsx");
    expect(files).toContain("src/lib/contrast.ts");
    // A `pages/` file: every allow-list entry was a `components/` directory
    // matched non-recursively, so no earlier walk could reach this one.
    expect(files).toContain(
      "src/features/infraction-management/pages/InfractionsPage.tsx",
    );
    expect(matchesIn("src/App.tsx", read("src/App.tsx").source)).toEqual([]);
    expect(
      matchesIn("src/lib/contrast.ts", read("src/lib/contrast.ts").source),
    ).toEqual([]);
  });

  it("excludes every test file and every __tests__ directory", () => {
    for (const pinned of PINNED) {
      expect(pinned.file.split("/")).not.toContain("__tests__");
      expect(pinned.file).not.toMatch(/\.test\.tsx?$/);
    }
  });

  it("makes rule 4 total: no src ledger row is skipped any more", () => {
    // Before the inversion the ledger-to-exception direction began
    // `if (!pinned.has(file)) continue;`, which silently skipped every row in
    // a not-yet-migrated directory. With every file under `src` pinned, that
    // `continue` never fires for a `src/` row.
    const pinned = new Set(PINNED.map((file) => file.file));
    const srcRows = LEDGER.filter((row) =>
      toSrcRelative(row.file).startsWith("src/"),
    );
    const skipped = srcRows.filter(
      (row) => !pinned.has(toSrcRelative(row.file)),
    );
    const excused = new Set(
      EXCEPTIONS.map((entry) => `${entry.file} :: ${entry.class}`),
    );

    expect(skipped).toEqual([]);
    expect(
      srcRows.filter(
        (row) => !excused.has(`${toSrcRelative(row.file)} :: ${row.class}`),
      ),
    ).toHaveLength(0);
    expect(
      EXCEPTIONS.filter(
        (entry) =>
          !srcRows.some(
            (row) =>
              toSrcRelative(row.file) === entry.file &&
              row.class === entry.class,
          ),
      ),
    ).toHaveLength(0);
  });

  it("balances matches against ledger rows against excused occurrences", () => {
    // Three equalities between things the test computes, never against a
    // literal: the projection published on APRAS-85 was 1,197 matches over 882
    // exceptions entries, and a drift from it is a thing to report, not a
    // thing to assert.
    const matches = PINNED.flatMap(({ file, source }) =>
      matchesIn(file, source),
    );
    const srcRows = LEDGER.filter((row) =>
      toSrcRelative(row.file).startsWith("src/"),
    );
    const excused = new Set(
      EXCEPTIONS.map((entry) => `${entry.file} :: ${entry.class}`),
    );
    const covered = PINNED.flatMap(({ file, source }) =>
      matchesIn(file, source).filter((match) =>
        excused.has(`${file} :: ${match.text}`),
      ),
    );

    expect(matches).toHaveLength(srcRows.length);
    expect(covered).toHaveLength(matches.length);
  });
});

describe("the closed guard", () => {
  // The property no earlier child could assert: a palette class reintroduced
  // into a file **no child ever migrated** fails CI. `src/App.tsx` is that
  // file — it carries zero grammar matches and no allow-list entry ever
  // reached it.
  const UNMIGRATED = "src/App.tsx";
  const withSuffix = (suffix: string) =>
    PINNED.map((file) =>
      file.file === UNMIGRATED
        ? { ...file, source: `${file.source}\n// ${suffix}\n` }
        : file,
    );

  it.each([
    "bg-slate-800",
    "hover:dark:bg-slate-800/40",
    "text-gray-500",
    "bg-white",
    "text-black",
  ])("fails on %s reintroduced into a file no child migrated", (reintroduced) => {
    const found = violations(withSuffix(reintroduced), EXCEPTIONS, LEDGER);

    expect(found.join("\n")).toContain(reintroduced);
    expect(found.some((problem) => problem.startsWith(UNMIGRATED))).toBe(true);
    const whole = reintroduced.match(paletteGrammar());
    expect(whole).not.toBeNull();
    expect(whole).toHaveLength(1);
    expect(whole?.[0]).toBe(reintroduced);
  });

  it("fails on a hex literal in a class context in that same file", () => {
    const injected = PINNED.map((file) =>
      file.file === UNMIGRATED
        ? {
            ...file,
            source: `${file.source}\nconst a = <i className="text-[#1e293b]" />;\n`,
          }
        : file,
    );
    const found = violations(injected, EXCEPTIONS, LEDGER);

    expect(found.join("\n")).toContain("#1e293b");
    const hex = matchesIn(
      UNMIGRATED,
      'const a = <i className="text-[#1e293b]" />;',
    );
    expect(hex.map((match) => match.text)).toEqual(["#1e293b"]);
  });
});

describe("APRAS-85's ledger arithmetic", () => {
  // Appended, directory-scoped, in the shape APRAS-79 through APRAS-84
  // established. What is different here is only that two of the six trees span
  // two subdirectories — `infraction-management` and `user-administration` each
  // hold `components/` and `pages/` — which the repo-wide recursive walk
  // reaches and no per-directory allow-list entry ever did.
  const INFRACTIONS = "src/features/infraction-management/";
  const USERS = "src/features/user-administration/";
  const TASKS = "src/features/task-management/";
  const DASHBOARD = "src/features/dashboard/";
  const SPACES = "src/features/space-reservation-management/";
  const ASSEMBLIES = "src/features/assembly-voting/";
  const DIRECTORIES = [INFRACTIONS, USERS, TASKS, DASHBOARD, SPACES, ASSEMBLIES];
  const inDirectories = (file: string) =>
    DIRECTORIES.some((directory) => file.startsWith(directory));
  const rows = LEDGER.filter((row) => inDirectories(toSrcRelative(row.file)));
  const count = (code: string) =>
    rows.filter((row) => row.code === code).length;
  const files = PINNED.filter((file) => inDirectories(file.file));
  const remainingIn = (directory: string) =>
    files
      .filter((file) => file.file.startsWith(directory))
      .flatMap((file) => matchesIn(file.file, file.source));
  const sourceOf = (name: string) =>
    files.find((file) => file.file.endsWith(`/${name}`))?.source ?? "";
  /** One file's source as whole whitespace-delimited tokens, never as
   *  substrings: `text-primary` and `text-primary-text` are two tokens and
   *  neither matches the other, which is what §1k's amendment turns on. */
  const tokensOf = (name: string): string[] =>
    sourceOf(name)
      .split(/[\s"'`{}()<>,;]+/)
      .filter((token) => token.length > 0);
  const tokensEverywhere = (): string[] =>
    files.flatMap((file) =>
      file.source.split(/[\s"'`{}()<>,;]+/).filter((token) => token.length > 0),
    );

  /**
   * The thirteen substitutions §"Behaviour" publishes, as
   * `class -> token, occurrences`, plus the one free-standing `text-red-700`.
   *
   * Declared rather than derived: the pre-change sources are not in the tree
   * at test time. What the tests below *do* derive is that every one of these
   * classes is now absent from the six trees, and that the counts close
   * against the 145 the ledger holds.
   */
  const MIGRATED: ReadonlyArray<readonly [string, string, number]> = [
    ["text-gray-500", "text-muted-foreground", 64],
    ["border-gray-200", "border-border", 41],
    ["text-gray-900", "text-foreground", 23],
    ["bg-white", "bg-card", 18],
    ["text-indigo-600", "text-primary-text", 5],
    ["bg-gray-100", "bg-muted", 3],
    ["text-gray-400", "text-muted-foreground", 2],
    ["text-gray-600", "text-muted-foreground", 2],
    ["border-gray-300", "border-input", 2],
    ["bg-emerald-700", "bg-primary", 2],
    ["text-white", "text-primary-foreground", 2],
    ["bg-gray-50", "bg-muted", 1],
    ["hover:bg-gray-50", "hover:bg-accent", 1],
    ["text-red-700", "text-destructive", 1],
  ];

  it("pins all 86 non-test source files of the six trees", () => {
    // Recursive, so `pages/` counts: 30 of the 86 carried a palette class.
    expect(files.length).toBeGreaterThanOrEqual(86);
    expect(
      files.filter((file) => file.file.startsWith(`${INFRACTIONS}pages/`))
        .length,
    ).toBeGreaterThan(0);
    expect(
      files.filter((file) => file.file.startsWith(`${USERS}pages/`)).length,
    ).toBeGreaterThan(0);
  });

  it("logs 145 occurrences under six codes", () => {
    expect(rows).toHaveLength(145);
    expect(count("GAP-NO-TOKEN")).toBe(53);
    expect(count("GAP-TINT")).toBe(46);
    expect(count("GAP-SWATCH")).toBe(24);
    expect(count("GAP-OVERLAY")).toBe(10);
    expect(count("GAP-OUT-OF-BUDGET")).toBe(7);
    expect(count("GAP-BORDER-100")).toBe(5);
  });

  it("uses no code it does not account for", () => {
    // No `GAP-NO-SURFACE`, because both `text-white` occurrences sat on a
    // migrating `bg-emerald-700`.
    expect(count("GAP-NO-SURFACE")).toBe(0);
    expect(count("GAP-UNLISTED")).toBe(0);
    expect(rows.every((row) => row.task === "APRAS-85")).toBe(true);
  });

  it("splits the twelve code halves as non-dark:/dark: exactly", () => {
    const half = (code: string, dark: boolean) =>
      rows.filter(
        (row) => row.code === code && row.class.startsWith("dark:") === dark,
      ).length;

    expect([
      half("GAP-NO-TOKEN", false),
      half("GAP-NO-TOKEN", true),
      half("GAP-TINT", false),
      half("GAP-TINT", true),
      half("GAP-SWATCH", false),
      half("GAP-SWATCH", true),
      half("GAP-OVERLAY", false),
      half("GAP-OVERLAY", true),
      half("GAP-OUT-OF-BUDGET", false),
      half("GAP-OUT-OF-BUDGET", true),
      half("GAP-BORDER-100", false),
      half("GAP-BORDER-100", true),
    ]).toEqual([41, 12, 44, 2, 16, 8, 8, 2, 7, 0, 5, 0]);
  });

  it("accounts for all 312 as 167 migrated + 0 deleted + 145 logged", () => {
    const migrated = MIGRATED.reduce((total, [, , n]) => total + n, 0);
    const keptDark = rows.filter((row) => row.class.startsWith("dark:")).length;

    expect(migrated).toBe(167);
    expect(migrated + rows.length).toBe(312);
    // Both halves close independently: 288 non-`dark:` = 167 + 121, and 24
    // `dark:` = 0 + 24. §1g's first half never fires in this child.
    expect(migrated + (rows.length - keptDark)).toBe(288);
    expect(keptDark).toBe(24);
  });

  it("leaves 145 of the six trees' 312 palette occurrences in place", () => {
    expect(remainingIn("")).toHaveLength(145);
    expect(remainingIn(INFRACTIONS)).toHaveLength(29);
    expect(remainingIn(USERS)).toHaveLength(44);
    expect(remainingIn(TASKS)).toHaveLength(35);
    expect(remainingIn(DASHBOARD)).toHaveLength(28);
    expect(remainingIn(SPACES)).toHaveLength(9);
    // `assembly-voting` migrates completely and keeps no row.
    expect(remainingIn(ASSEMBLIES)).toHaveLength(0);
    // Zero six-digit hex literals in a class context anywhere in the six.
    expect(
      remainingIn("").filter((match) => match.text.startsWith("#")),
    ).toEqual([]);
  });

  it("removes every migrated class from the six trees", () => {
    const surviving = remainingIn("").map((match) => match.text);

    for (const [migrated] of MIGRATED) {
      // `text-red-700` is the one class both migrated and kept — once at
      // `NextStepPanel.tsx:82`, and four times inside error tints in four
      // *other* files, so no file excuses a class it also migrates.
      const expected = migrated === "text-red-700" ? 4 : 0;
      expect(surviving.filter((text) => text === migrated)).toHaveLength(
        expected,
      );
    }
    expect(sourceOf("NextStepPanel.tsx")).toContain("text-destructive");
    expect(sourceOf("NextStepPanel.tsx")).not.toContain("text-red-700");
    // No `dark:` sibling was deleted because no migrated class had one.
    for (const [migrated] of MIGRATED) {
      expect(tokensEverywhere()).not.toContain(`dark:${migrated}`);
    }
  });

  it("excepts the 126 distinct (file, class) pairs those 145 occupy", () => {
    const entries = EXCEPTIONS.filter((entry) => inDirectories(entry.file));
    const pairs = new Set(
      rows.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );

    expect(entries).toHaveLength(126);
    expect(pairs.size).toBe(126);
    expect(entries.every((entry) => entry.task === "APRAS-85")).toBe(true);
    const inDirectory = (directory: string) =>
      entries.filter((entry) => entry.file.startsWith(directory)).length;
    expect([
      inDirectory(INFRACTIONS),
      inDirectory(USERS),
      inDirectory(TASKS),
      inDirectory(DASHBOARD),
      inDirectory(SPACES),
      inDirectory(ASSEMBLIES),
    ]).toEqual([25, 35, 33, 26, 7, 0]);
  });

  it("resolves the two classes logged twice in one file by §1h precedence", () => {
    // `GeneralDashboardPage.tsx`'s `bg-amber-500/10` and `dark:text-amber-400`
    // are module swatches in the colour map and warning tints in the preview
    // badge at line 116. The ledger is per occurrence, so both codes appear;
    // the exceptions file is keyed `(file, class)` and carries one, so the
    // pair takes the earlier of the two in `GAP_CODES`.
    const dashboardFile = `${DASHBOARD}components/GeneralDashboardPage.tsx`;
    for (const className of ["bg-amber-500/10", "dark:text-amber-400"]) {
      const both = rows.filter(
        (row) =>
          toSrcRelative(row.file) === dashboardFile && row.class === className,
      );
      expect(new Set(both.map((row) => row.code))).toEqual(
        new Set(["GAP-SWATCH", "GAP-NO-TOKEN"]),
      );
      expect(
        EXCEPTIONS.find(
          (entry) => entry.file === dashboardFile && entry.class === className,
        )?.code,
      ).toBe("GAP-SWATCH");
    }
  });

  it("keeps TaskBoard's five header stripes verbatim, ledgered and excepted", () => {
    const board = `${TASKS}components/TaskBoard.tsx`;
    const source = sourceOf("TaskBoard.tsx");
    const STRIPES: ReadonlyArray<readonly [string, string]> = [
      ["border-t-slate-400", "GAP-TINT"],
      ["border-t-blue-400", "GAP-NO-TOKEN"],
      ["border-t-amber-500", "GAP-NO-TOKEN"],
      ["border-t-green-400", "GAP-NO-TOKEN"],
      ["border-t-red-400", "GAP-TINT"],
    ];

    for (const [stripe, code] of STRIPES) {
      expect(source.split(stripe)).toHaveLength(2);
      expect(
        rows.filter(
          (row) => toSrcRelative(row.file) === board && row.class === stripe,
        ).map((row) => row.code),
      ).toEqual([code]);
      expect(
        EXCEPTIONS.filter(
          (entry) => entry.file === board && entry.class === stripe,
        ).map((entry) => entry.code),
      ).toEqual([code]);
    }
  });

  it("puts the five stripes in no class-context span yet still reports them", () => {
    // They are values of a `headerColorClass` object property, not arguments
    // of `className`, `cn` or `cva`, so `classContexts()` returns no span
    // containing them — and the palette grammar finds them anyway, because it
    // runs over the whole source and only the hex pattern is span-restricted.
    const source = sourceOf("TaskBoard.tsx");
    const spans = classContexts(source);
    const stripes = [...source.matchAll(/border-t-[a-z]+-\d+/g)];

    expect(stripes).toHaveLength(5);
    for (const stripe of stripes) {
      const at = stripe.index ?? 0;
      expect(spans.some(([start, end]) => at >= start && at < end)).toBe(false);
    }
    expect(
      matchesIn("", source)
        .map((match) => match.text)
        .filter((text) => text.startsWith("border-t-")),
    ).toHaveLength(5);
  });

  it("puts exactly five brand-text occurrences on text-primary-text", () => {
    const CHARACTERS: ReadonlyArray<readonly [string, number]> = [
      ["AttachmentUploader.tsx", 1],
      ["InfractionDetailsView.tsx", 2],
      ["InfractionStageTimeline.tsx", 1],
      ["NewInfractionModal.tsx", 1],
    ];
    let total = 0;
    for (const [name, expected] of CHARACTERS) {
      expect(
        tokensOf(name).filter((token) => token === "text-primary-text"),
      ).toHaveLength(expected);
      total += expected;
    }

    expect(total).toBe(5);
    // §1k's graphical branch is empty here: this child produces no bare
    // `text-primary`, and `-primary-text` lands on no non-`text-` utility.
    const tokens = tokensEverywhere();
    for (const prefix of [
      "bg",
      "border",
      "ring",
      "divide",
      "outline",
      "fill",
      "stroke",
      "accent",
    ]) {
      expect(tokens).not.toContain(`${prefix}-primary-text`);
    }
  });

  it("leaves no indigo in infraction-management and three in dashboard", () => {
    expect(
      remainingIn(INFRACTIONS).filter((match) =>
        match.text.includes("indigo"),
      ),
    ).toEqual([]);
    expect(
      remainingIn(DASHBOARD)
        .filter((match) => match.text.includes("indigo"))
        .map((match) => `${match.line}:${match.text}`),
    ).toEqual(["54:text-indigo-500", "54:dark:text-indigo-400", "55:bg-indigo-500/10"]);
    // All three are module-identity swatches, not brand.
    expect(
      rows
        .filter((row) => row.class.includes("indigo"))
        .map((row) => row.code),
    ).toEqual(["GAP-SWATCH", "GAP-SWATCH", "GAP-SWATCH"]);
  });

  it("migrates exactly the two success-panel buttons and nothing around them", () => {
    // §1f case 3's single test — is the element interactive? The panels the
    // two buttons sit inside are kept whole, and `TenantsAdminPage`'s other
    // two buttons stay palette because `border-emerald-300` has no row at any
    // scale and a triple migrates as a unit or not at all.
    expect(tokensEverywhere()).not.toContain("bg-emerald-700");
    expect(tokensEverywhere()).not.toContain("text-white");
    for (const name of ["InviteAdministratorDialog.tsx", "TenantsAdminPage.tsx"]) {
      expect(tokensOf(name)).toContain("bg-primary");
      expect(tokensOf(name)).toContain("text-primary-foreground");
    }
    const admin = remainingIn(USERS)
      .filter((match) => match.file.endsWith("/TenantsAdminPage.tsx"))
      .map((match) => match.text);
    expect(admin.filter((text) => text === "border-emerald-300")).toHaveLength(
      2,
    );
    expect(admin.filter((text) => text === "text-emerald-800")).toHaveLength(5);
  });

  it("mixes no migrated occurrence with a kept tint in one class span", () => {
    // Grouped by `(file, span)` with the guard's own `classContexts()`, not by
    // line. `INTRODUCED` names, per changed file, the tokens *this task* put
    // there — declared because the pre-change sources are not in the tree at
    // test time, and cross-checked while implementing against
    // `git show HEAD:<file>`, which returns the same three spans.
    const I_ = INFRACTIONS;
    const INTRODUCED: ReadonlyArray<readonly [string, readonly string[]]> = [
      [`${I_}components/AttachmentUploader.tsx`, ["text-muted-foreground", "text-primary-text"]],
      [`${I_}components/ContestationForm.tsx`, ["border-border", "text-muted-foreground"]],
      [`${I_}components/CycleCloseModal.tsx`, ["bg-card", "border-border", "text-foreground", "text-muted-foreground"]],
      [`${I_}components/InfractionDetailsView.tsx`, ["bg-card", "border-border", "text-foreground", "text-muted-foreground", "text-primary-text"]],
      [`${I_}components/InfractionStageTimeline.tsx`, ["text-foreground", "text-muted-foreground", "text-primary-text"]],
      [`${I_}components/NewInfractionModal.tsx`, ["bg-card", "bg-muted", "border-border", "text-foreground", "text-muted-foreground", "text-primary-text"]],
      [`${I_}components/NextStepPanel.tsx`, ["bg-card", "border-border", "text-destructive", "text-foreground", "text-muted-foreground"]],
      [`${I_}pages/InfractionRulesPage.tsx`, ["bg-card", "bg-muted", "border-border", "text-foreground", "text-muted-foreground"]],
      [`${I_}pages/InfractionsPage.tsx`, ["bg-card", "bg-muted", "border-border", "hover:bg-accent", "text-foreground", "text-muted-foreground"]],
      [`${I_}pages/MyInfractionsPage.tsx`, ["bg-card", "bg-muted", "border-border", "text-foreground", "text-muted-foreground"]],
      [`${USERS}components/InviteAdministratorDialog.tsx`, ["bg-primary", "text-primary-foreground"]],
      [`${USERS}components/PermissionMatrix.tsx`, ["border-input"]],
      [`${USERS}pages/AdminUserDashboard.tsx`, ["border-input"]],
      [`${USERS}pages/TenantsAdminPage.tsx`, ["bg-primary", "text-primary-foreground"]],
      [`${ASSEMBLIES}components/AssemblyMinutesView.tsx`, ["bg-card"]],
    ];
    const codeOf = new Map(
      rows.map((row) => [
        `${toSrcRelative(row.file)} :: ${row.class}`,
        row.code,
      ]),
    );
    const mixed: string[] = [];
    for (const [file, tokens] of INTRODUCED) {
      const source = files.find((pinned) => pinned.file === file)?.source ?? "";
      expect(source).not.toBe("");
      for (const [start, end] of classContexts(source)) {
        const span = source.slice(start, end);
        const introduced = span
          .split(/[\s"'`{}()<>,;]+/)
          .filter((token) => tokens.includes(token));
        const kept = matchesIn(file, span).map((match) => match.text);
        if (introduced.length > 0 && kept.length > 0) {
          mixed.push(
            `${file} ${kept.map((text) => codeOf.get(`${file} :: ${text}`)).join(",")}`,
          );
        }
      }
    }

    // Zero spans mix a migrated occurrence with a kept `GAP-TINT` one — the
    // first child in the split to return zero rather than one.
    expect(mixed.filter((entry) => entry.includes("GAP-TINT"))).toEqual([]);
    expect(mixed).toEqual([
      `${I_}pages/InfractionsPage.tsx GAP-BORDER-100`,
      `${I_}pages/InfractionsPage.tsx GAP-OUT-OF-BUDGET`,
      `${I_}pages/MyInfractionsPage.tsx GAP-OUT-OF-BUDGET`,
    ]);
  });

  it("leaves the two known no-token gaps untouched and fully recorded", () => {
    // Repo-wide, not only in the six trees: every child leaves these four
    // classes alone, so the figure survives APRAS-81 through APRAS-84.
    const KNOWN: ReadonlyArray<readonly [string, number]> = [
      ["text-gray-700", 73],
      ["text-slate-700", 69],
      ["border-slate-100", 41],
      ["border-gray-100", 12],
    ];
    const everywhere = PINNED.flatMap(({ file, source }) =>
      matchesIn(file, source).map((match) => ({ file, text: match.text })),
    );
    const excused = new Set(
      EXCEPTIONS.map((entry) => `${entry.file} :: ${entry.class}`),
    );
    const ledgered = new Set(
      LEDGER.map((row) => `${toSrcRelative(row.file)} :: ${row.class}`),
    );
    let total = 0;
    for (const [known, expected] of KNOWN) {
      const found = everywhere.filter((match) => match.text === known);
      expect(found).toHaveLength(expected);
      total += expected;
      // The row and the entry must exist; no code is asserted, because §1h's
      // precedence legitimately codes some of them `GAP-SWATCH` or `GAP-TINT`.
      for (const match of found) {
        expect(excused.has(`${match.file} :: ${match.text}`)).toBe(true);
        expect(ledgered.has(`${match.file} :: ${match.text}`)).toBe(true);
      }
    }

    expect(total).toBe(195);
  });
});
