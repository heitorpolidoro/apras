/// <reference types="node" />
// @vitest-environment node
//
// The single-focus-trap guard (APRAS-98).
//
// APRAS-118 extracted the `Tab` half of a modal's focus trap into one module;
// APRAS-98 moved it to `src/lib/focusTrap.ts` and gave the slug-change dialog a
// second caller through `src/hooks/useDialogFocus.ts`. Two dialogs now depend on
// one algorithm, and the cheapest way for a third to go wrong is for somebody to
// paste the selector list rather than import it. This file is what makes that
// paste fail.
//
// It follows `src/__tests__/brandTextOpacity.test.ts`: a tree walk over the real
// tree, plus a positive control proving the walk can match something. The node
// environment is what makes `import.meta.url` a `file:` URL, exactly as that
// precedent and `themeTokenMigration.test.ts` need it to be.
//
// **What this guard does NOT detect**, so that no reader over-trusts it. It is a
// copy detector for *this* module in non-test code, and that is the whole of its
// claim:
//
// - a trap written as `if (event.key === "Tab")` with manual `.focus()` calls
//   and no `tabindex` selector at all;
// - any third-party trap — Radix, headlessui, the `focus-trap` package, a
//   native `<dialog>` with its own top-layer behaviour;
// - a focusable-element selector that enumerates tags (`button, a, input, …`)
//   without ever writing the word `tabindex`;
// - a selector assembled from fragments at run time, so no single line carries
//   the text;
// - **anything under `__tests__/`**, which the sweep excludes. That exclusion is
//   what keeps the moved `src/lib/__tests__/focusTrap.test.ts` — which
//   legitimately names `FOCUSABLE_SELECTOR` — and this file itself out of both
//   counts, and the price of it is that a second trap, or a second
//   `skipcq: JS-R1005`, planted in a test helper there is invisible to
//   assertions 1 and 2.
//
// One further honesty note, about `M2` specifically: it is a **forbid-only**
// matcher whose regex has never fired against a real file in this repository,
// because no file inlines the selector string. The positive control below
// exercises `M1` only. A typo in `M2` would therefore be invisible; it is kept
// because a false negative there costs nothing `M1` does not already cover, and
// it is not evidence of anything on its own.
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(HERE, "..");
const FRONTEND_ROOT = path.resolve(SRC_ROOT, "..");

/** The one legitimate home of the algorithm, relative to the frontend root. */
const CANONICAL = "src/lib/focusTrap.ts";

/** The line-scoped DeepSource suppression that must exist exactly once. */
const SUPPRESSION = "skipcq: JS-R1005";

// --- the two matchers ------------------------------------------------------

/** `M1` — the identifier, as a whole word, so a longer name cannot register. */
const M1 = /\bFOCUSABLE_SELECTOR\b/;

/**
 * `M2` — a `querySelectorAll` call whose argument text mentions `tabindex`,
 * which is the shape a hand-rolled copy of the selector list takes.
 *
 * The optional `<…>` group is the TypeScript generic the canonical module's own
 * call carries (`querySelectorAll<HTMLElement>(…)`).
 *
 * `M2` deliberately does **not** match the canonical module, and must not be
 * "repaired" until it does: there the argument is the identifier
 * `FOCUSABLE_SELECTOR`, so the argument text holds no `tabindex`. The canonical
 * site is found by `M1`; `M2` exists only to catch a copy that *inlines* the
 * string.
 */
const M2 = /querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i;

// --- the sweep -------------------------------------------------------------

const isSwept = (name: string): boolean => /\.tsx?$/.test(name);

/**
 * Every `.ts`/`.tsx` file under `src/`, excluding `__tests__/` directories —
 * the precedent's own boundary (`brandTextOpacity.test.ts:96-111`).
 */
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

/** A swept file, named the way the exceptions file names files. */
interface Swept {
  /** POSIX-separated and relative to the frontend root. */
  file: string;
  source: string;
}

const swept = (): Swept[] =>
  sourceFiles().map((full) => ({
    file: path.relative(FRONTEND_ROOT, full).split(path.sep).join("/"),
    source: readFileSync(full, "utf8"),
  }));

/** The matchers a file trips, named so a failure reads as a report. */
const matchersHit = (source: string): string[] =>
  [
    M1.test(source) ? "M1" : null,
    M2.test(source) ? "M2" : null,
  ].filter((name): name is string => name !== null);

// --- the documented exception route ----------------------------------------

interface Exception {
  file: string;
  matcher: string;
  reason: string;
  task: string;
}

/**
 * The sibling pattern of `themeTokenMigration.exceptions.json`: a task that
 * deliberately adopts a dialog library or a second trap adds a row here rather
 * than deleting a test, so an exemption is a reviewable act with a paper trail.
 * Ships as `[]`.
 */
const exceptions = (): Exception[] =>
  JSON.parse(
    readFileSync(
      path.join(HERE, "focusTrapSingleImplementation.exceptions.json"),
      "utf8",
    ),
  ) as Exception[];

const readFrontend = (relative: string): string =>
  readFileSync(path.join(FRONTEND_ROOT, relative), "utf8");

describe("the focus trap has exactly one implementation (APRAS-98)", () => {
  it("has no second copy of the algorithm outside src/lib/focusTrap.ts", () => {
    const exempt = new Set(exceptions().map((entry) => entry.file));
    const copies = swept()
      .filter((file) => file.file !== CANONICAL && !exempt.has(file.file))
      .flatMap((file) =>
        matchersHit(file.source).map((matcher) => `${file.file} (${matcher})`),
      );

    expect(copies).toEqual([]);
  });

  it("carries every exception with a reason and a task", () => {
    for (const entry of exceptions()) {
      expect(entry.file).not.toBe("");
      expect(["M1", "M2"]).toContain(entry.matcher);
      expect(entry.reason.trim()).not.toBe("");
      expect(entry.task.trim()).not.toBe("");
    }
  });

  it("carries the JS-R1005 suppression exactly once, in the canonical module", () => {
    // This sweep **includes** the canonical module: the suppression lives there
    // and the claim is about the total, not about everybody else.
    const sites = swept().filter((file) => file.source.includes(SUPPRESSION));

    expect(sites.map((file) => file.file)).toEqual([CANONICAL]);
    const occurrences = sites[0]?.source.split(SUPPRESSION).length ?? 1;
    expect(occurrences - 1).toBe(1);
  });

  it("is really used by the hook and by both dialogs", () => {
    // A forbid-only guard passes trivially if both dialogs lose the trap
    // entirely, so the consumers are pinned from the other side.
    expect(readFrontend("src/hooks/useDialogFocus.ts")).toContain(
      '"../lib/focusTrap"',
    );
    expect(
      readFrontend(
        "src/features/project-management/components/ObraPrintDialog.tsx",
      ),
    ).toContain("useDialogFocus");
    expect(
      readFrontend(
        "src/features/user-administration/pages/TenantProfilePage.tsx",
      ),
    ).toContain("useDialogFocus");
  });

  it("proves the sweep and M1 work against the real tree", () => {
    // The positive control, and the two load-bearing halves of it.
    const files = swept();

    // One: the walk opened real files, so a zero-file walk cannot pass the
    // forbidding assertions above for the wrong reason.
    expect(files.length).toBeGreaterThan(20);

    // Two: `M1` can match. Run over the sweep *with* the canonical module in
    // it, it finds exactly one file, and that file is the canonical module.
    const hits = files
      .filter((file) => M1.test(file.source))
      .map((file) => file.file);
    expect(hits).toEqual([CANONICAL]);

    // Kept for shape only, and self-referential: these assert the walk against
    // its own filter and can fail only on a walk bug, so neither is evidence
    // that `M1` or `M2` works.
    expect(files.every((file) => /\.tsx?$/.test(file.file))).toBe(true);
    expect(files.some((file) => file.file.includes("/__tests__/"))).toBe(false);
  });
});
