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
export const MIGRATED_DIRECTORIES: readonly string[] = ["src/components/ui"];

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
    const source = files.find((candidate) => candidate.file === entry.file);
    if (source === undefined) {
      problems.push(
        `exception names ${entry.file}, which is not a source file under a pinned directory (§3c rule 2)`,
      );
      continue;
    }
    if (
      !matchesIn(entry.file, source.source).some(
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
    for (const match of matchesIn(file, source)) {
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
  it("is seeded with exactly src/components/ui", () => {
    expect(MIGRATED_DIRECTORIES).toEqual(["src/components/ui"]);
  });

  it("pins every non-test source file in that directory", () => {
    expect(PINNED.map((file) => file.file)).toContain(
      "src/components/ui/button.tsx",
    );
    expect(
      PINNED.every((file) => file.file.startsWith("src/components/ui/")),
    ).toBe(true);
    expect(PINNED.some((file) => /\.test\.tsx?$/.test(file.file))).toBe(false);
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
    const remaining = PINNED.flatMap((file) =>
      matchesIn(file.file, file.source),
    );

    expect(remaining).toHaveLength(24);
  });

  it("keeps every `why` under 120 characters and off the code", () => {
    for (const row of pilot) {
      expect(row.why.length).toBeLessThanOrEqual(120);
      expect(row.why).not.toContain("GAP-");
    }
  });
});
