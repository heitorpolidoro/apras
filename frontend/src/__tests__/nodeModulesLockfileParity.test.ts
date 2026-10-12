/// <reference types="node" />
// @vitest-environment node

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(HERE, "../..");
const REPO_ROOT = path.resolve(FRONTEND_ROOT, "..");

export interface LockedPackage {
  version: string;
  isTopLevel: boolean;
}

export type LockedPackageMap = Map<string, LockedPackage>;

export type InstalledStatus =
  | { status: "installed"; version: string }
  | { status: "absent" };

export type InstalledPackageMap = Map<string, InstalledStatus>;

export type Finding =
  | { type: "mismatch"; path: string; locked: string; installed: string }
  | { type: "absent"; path: string; locked: string };

/**
 * Reads locked versions for all non-optional packages from a package-lock.json file.
 * Throws if the resulting map is empty.
 */
export function readLockedPackages(lockfilePath: string): LockedPackageMap {
  const content = readFileSync(lockfilePath, "utf8");
  const parsed = JSON.parse(content);
  const packages = parsed.packages || {};

  const map: LockedPackageMap = new Map();

  for (const [key, val] of Object.entries<any>(packages)) {
    if (!key || key === "") continue;
    if (val.optional) continue;
    if (typeof val.version !== "string" || !val.version) continue;

    // Determine if it is a top-level or nested node_modules package
    const segments = key.split("node_modules/").filter(Boolean);
    const isTopLevel = segments.length === 1;

    map.set(key, {
      version: val.version,
      isTopLevel,
    });
  }

  if (map.size === 0) {
    throw new Error(
      `Derived set of non-optional lockfile entries from ${lockfilePath} is empty.`,
    );
  }

  return map;
}

/**
 * Reads installed package versions from `<root>/<path>/package.json`.
 * Returns either `{ status: 'installed', version }` or `{ status: 'absent' }`.
 * Never returns undefined or a placeholder for missing files.
 */
export function readInstalledPackages(
  rootDirectory: string,
  paths: Iterable<string>,
): InstalledPackageMap {
  const installedMap: InstalledPackageMap = new Map();

  for (const pkgPath of paths) {
    const manifestPath = path.join(rootDirectory, pkgPath, "package.json");
    if (!existsSync(manifestPath)) {
      installedMap.set(pkgPath, { status: "absent" });
      continue;
    }

    try {
      const content = readFileSync(manifestPath, "utf8");
      const parsed = JSON.parse(content);
      if (typeof parsed.version === "string") {
        installedMap.set(pkgPath, {
          status: "installed",
          version: parsed.version,
        });
      } else {
        installedMap.set(pkgPath, { status: "absent" });
      }
    } catch {
      installedMap.set(pkgPath, { status: "absent" });
    }
  }

  return installedMap;
}

/**
 * Pure comparison between locked packages and installed packages.
 *
 * Rules:
 * - A top-level entry that is absent is a failure.
 * - A nested entry that is absent is skipped (hoisting leniency).
 * - An entry that is present with a different version is a mismatch failure.
 */
export function comparePackages(
  lockedMap: LockedPackageMap,
  installedMap: InstalledPackageMap,
): Finding[] {
  const findings: Finding[] = [];

  for (const [pkgPath, locked] of lockedMap.entries()) {
    const installed = installedMap.get(pkgPath);

    if (!installed || installed.status === "absent") {
      if (locked.isTopLevel) {
        findings.push({
          type: "absent",
          path: pkgPath,
          locked: locked.version,
        });
      }
      // Nested entries absent are tolerated
      continue;
    }

    if (installed.status === "installed") {
      if (installed.version !== locked.version) {
        findings.push({
          type: "mismatch",
          path: pkgPath,
          locked: locked.version,
          installed: installed.version,
        });
      }
    }
  }

  return findings;
}

export interface AgentsMajorCheckResult {
  vitestMajor: string;
  eslintMajor: string;
}

/**
 * Validates the Vitest and ESLint majors declared in the Frontend stack table of AGENTS.md
 * against the provided locked package map.
 * Scopes search exclusively to the table following the `## Frontend` heading.
 * Distinguishes between "no match / missing row / missing major" and "different major".
 */
export function verifyAgentsMdMajors(
  markdownContent: string,
  lockedMap: LockedPackageMap,
): AgentsMajorCheckResult {
  const frontendHeadingMatch = markdownContent.match(/##\s+Frontend\s*\n([\s\S]*?)(?=\n##\s+|$)/);
  if (!frontendHeadingMatch) {
    throw new Error(
      "Missing or reworded '## Frontend' section in AGENTS.md; could not locate frontend stack table.",
    );
  }

  const frontendSection = frontendHeadingMatch[1];

  // Helper to extract major from a row keyed by its first table cell
  const findRowMajor = (rowLabel: string, toolName: string): string => {
    // Match line e.g. | Testing | Vitest 5 ... |
    // Keyed by row label in first cell
    const rowRegex = new RegExp(
      `^\\|\\s*${rowLabel}\\s*\\|([^|\\n]+)\\|`,
      "m",
    );
    const rowMatch = frontendSection.match(rowRegex);
    if (!rowMatch) {
      throw new Error(
        `Row '${rowLabel}' was missing or reworded in AGENTS.md frontend stack table.`,
      );
    }

    const cellContent = rowMatch[1].trim();
    // Match tool name followed by major version digit(s)
    const majorRegex = new RegExp(`\\b${toolName}\\s+(\\d+)\\b`, "i");
    const majorMatch = cellContent.match(majorRegex);
    if (!majorMatch) {
      throw new Error(
        `Row '${rowLabel}' in AGENTS.md frontend stack table does not state a major version for '${toolName}'.`,
      );
    }

    return majorMatch[1];
  };

  const vitestMajorClaimed = findRowMajor("Testing", "Vitest");
  const eslintMajorClaimed = findRowMajor("Linting", "ESLint");

  const vitestLocked = lockedMap.get("node_modules/vitest");
  if (!vitestLocked) {
    throw new Error("Lockfile is missing 'node_modules/vitest' entry.");
  }
  const vitestLockedMajor = vitestLocked.version.split(".")[0];

  const eslintLocked = lockedMap.get("node_modules/eslint");
  if (!eslintLocked) {
    throw new Error("Lockfile is missing 'node_modules/eslint' entry.");
  }
  const eslintLockedMajor = eslintLocked.version.split(".")[0];

  if (vitestMajorClaimed !== vitestLockedMajor) {
    throw new Error(
      `Row 'Testing' stated major '${vitestMajorClaimed}' for Vitest, but lockfile pins major '${vitestLockedMajor}' (${vitestLocked.version}).`,
    );
  }

  if (eslintMajorClaimed !== eslintLockedMajor) {
    throw new Error(
      `Row 'Linting' stated major '${eslintMajorClaimed}' for ESLint, but lockfile pins major '${eslintLockedMajor}' (${eslintLocked.version}).`,
    );
  }

  return {
    vitestMajor: vitestMajorClaimed,
    eslintMajor: eslintMajorClaimed,
  };
}

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

describe("frontend node_modules package-lock guard (APRAS-127)", () => {
  const lockfilePath = path.join(FRONTEND_ROOT, "package-lock.json");

  it("empty-set throw: throws when derived set of lockfile entries is empty", () => {
    // Valid lockfile JSON fixture with empty packages
    expect(() => {
      readLockedPackages(path.join(HERE, "fixtures/empty-lockfile.json"));
    }).toThrow(/Derived set of non-optional lockfile entries.*is empty/i);
  });

  describe("reconciled tree parity", () => {
    it("reports 0 version mismatches and 0 absent non-optional top-level packages over all 335 entries", () => {
      const lockedMap = readLockedPackages(lockfilePath);
      expect(lockedMap.size).toBe(335);

      const installedMap = readInstalledPackages(FRONTEND_ROOT, lockedMap.keys());
      const findings = comparePackages(lockedMap, installedMap);

      const mismatches = findings.filter((f) => f.type === "mismatch");
      const absents = findings.filter((f) => f.type === "absent");

      expect(mismatches).toHaveLength(0);
      expect(absents).toHaveLength(0);

      // Verify specific pins
      const tw = installedMap.get("node_modules/tailwindcss");
      const es = installedMap.get("node_modules/eslint");
      expect(tw).toEqual({ status: "installed", version: "4.3.3" });
      expect(es).toEqual({ status: "installed", version: "10.11.0" });
    });
  });

  describe("fixture-tree disk-read controls", () => {
    const fixtureRoot = path.join(HERE, "fixtures");

    it("verifies fixture files are tracked by git (fails if untracked)", () => {
      const fixtureFiles = [
        "src/__tests__/fixtures/empty-lockfile.json",
        "src/__tests__/fixtures/node_modules/eslint/package.json",
        "src/__tests__/fixtures/node_modules/tailwindcss/package.json",
      ];

      for (const relFile of fixtureFiles) {
        const fullPath = path.resolve(FRONTEND_ROOT, relFile);
        expect(existsSync(fullPath)).toBe(true);

        try {
          execFileSync("git", ["ls-files", "--error-unmatch", relFile], {
            cwd: FRONTEND_ROOT,
            stdio: "pipe",
          });
        } catch (err: any) {
          throw new Error(
            `Fixture file '${relFile}' is untracked by git: ${err.message}`,
          );
        }
      }
    });

    it("reports exactly two findings (one mismatch with fixture version string, one absent) when restricted to the three fixture packages", () => {
      const realLocked = readLockedPackages(lockfilePath);

      // Restrict locked map to the three control packages
      const threeKeys = [
        "node_modules/eslint",
        "node_modules/tailwindcss",
        "node_modules/vitest",
      ];

      const restrictedLocked: LockedPackageMap = new Map();
      for (const key of threeKeys) {
        const lockedEntry = realLocked.get(key);
        if (!lockedEntry) {
          throw new Error(`Real lockfile missing expected package ${key}`);
        }
        restrictedLocked.set(key, lockedEntry);
      }

      // Read installed packages from the fixture root
      const fixtureInstalled = readInstalledPackages(
        fixtureRoot,
        restrictedLocked.keys(),
      );

      const findings = comparePackages(restrictedLocked, fixtureInstalled);

      // Assert findings are exactly two and nothing else
      expect(findings).toHaveLength(2);

      const mismatchFinding = findings.find((f) => f.type === "mismatch");
      const absentFinding = findings.find((f) => f.type === "absent");

      expect(mismatchFinding).toBeDefined();
      expect(absentFinding).toBeDefined();

      // Mismatch must name eslint and carry fixture's own version string as installed
      expect(mismatchFinding).toEqual({
        type: "mismatch",
        path: "node_modules/eslint",
        locked: "10.11.0",
        installed: "9.99.9",
      });

      // Absent must name vitest
      expect(absentFinding).toEqual({
        type: "absent",
        path: "node_modules/vitest",
        locked: "5.0.3",
      });
    });
  });

  describe("in-memory comparison controls", () => {
    it("reports a mismatch naming the package when installed version diverges", () => {
      const locked: LockedPackageMap = new Map([
        ["node_modules/pkg-a", { version: "1.0.0", isTopLevel: true }],
      ]);
      const installed: InstalledPackageMap = new Map([
        ["node_modules/pkg-a", { status: "installed", version: "2.0.0" }],
      ]);

      const findings = comparePackages(locked, installed);
      expect(findings).toEqual([
        {
          type: "mismatch",
          path: "node_modules/pkg-a",
          locked: "1.0.0",
          installed: "2.0.0",
        },
      ]);
    });

    it("reports an absent failure for top-level entry, distinguishable from mismatch", () => {
      const locked: LockedPackageMap = new Map([
        ["node_modules/pkg-top", { version: "1.0.0", isTopLevel: true }],
        ["node_modules/foo/node_modules/pkg-nested", { version: "1.0.0", isTopLevel: false }],
      ]);
      const installed: InstalledPackageMap = new Map([
        ["node_modules/pkg-top", { status: "absent" }],
        ["node_modules/foo/node_modules/pkg-nested", { status: "absent" }],
      ]);

      const findings = comparePackages(locked, installed);
      // Only the top-level absent is reported as a finding; nested absent is tolerated
      expect(findings).toEqual([
        {
          type: "absent",
          path: "node_modules/pkg-top",
          locked: "1.0.0",
        },
      ]);
    });
  });

  describe("AGENTS.md major check", () => {
    const realLocked = readLockedPackages(lockfilePath);

    it("passes when prose states the lockfile majors", () => {
      const sampleMd = `
## Backend
| Testing | pytest |
| Linting | Ruff |

## Frontend
| Testing | Vitest 5 + @testing-library/react |
| Linting | ESLint 10 + typescript-eslint |
`;
      const res = verifyAgentsMdMajors(sampleMd, realLocked);
      expect(res).toEqual({
        vitestMajor: "5",
        eslintMajor: "10",
      });
    });

    it("fails with a distinguishable error when a keyed row states a different major", () => {
      const sampleMd = `
## Frontend
| Testing | Vitest 4 + @testing-library/react |
| Linting | ESLint 10 + typescript-eslint |
`;
      expect(() => verifyAgentsMdMajors(sampleMd, realLocked)).toThrow(
        /Row 'Testing' stated major '4' for Vitest, but lockfile pins major '5'/i,
      );
    });

    it("fails with a distinguishable error when a keyed row is missing or reworded", () => {
      const sampleMd = `
## Frontend
| UnitTests | Vitest 5 |
| Linting | ESLint 10 |
`;
      expect(() => verifyAgentsMdMajors(sampleMd, realLocked)).toThrow(
        /Row 'Testing' was missing or reworded/i,
      );
    });

    it("fails with a distinguishable error when a keyed row states no major", () => {
      const sampleMd = `
## Frontend
| Testing | Vitest + @testing-library/react |
| Linting | ESLint 10 |
`;
      expect(() => verifyAgentsMdMajors(sampleMd, realLocked)).toThrow(
        /Row 'Testing'.*does not state a major version/i,
      );
    });

    it("passes on the real AGENTS.md in repo root", () => {
      const agentsMdPath = path.join(REPO_ROOT, "AGENTS.md");
      const content = readFileSync(agentsMdPath, "utf8");
      const res = verifyAgentsMdMajors(content, realLocked);
      expect(res.vitestMajor).toBe("5");
      expect(res.eslintMajor).toBe("10");
    });
  });
});
