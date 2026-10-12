/// <reference types="node" />
// @vitest-environment node
//
// No third contrast implementation (APRAS-100).
//
// The WCAG relative-luminance weight `0.2126` is the fingerprint of a contrast
// computation. Excluding test files, exactly two files in the repository may
// hold it: the frontend port and the backend original. The warning panel reads
// ratios from `profile.contrast_warnings` or from `auditHexPalette`, never from
// a luminance formula of its own. The exclusion is load-bearing:
// `themeContrast.test.ts` carries `RED_WEIGHT = 0.2126` and lives under
// `frontend/src`.
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(here, "..", "..");
const repoRoot = path.resolve(frontendRoot, "..");

const WEIGHT = "0.2126";
const TEST_FILE = /(^|\/)test_[^/]*\.py$|\.test\.tsx?$/;

const walk = (dir: string): string[] =>
  readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === "__tests__" || entry.name === "node_modules" || entry.name === "__pycache__") {
      return [];
    }
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });

const holders = (root: string): string[] =>
  walk(path.join(repoRoot, root))
    .filter((file) => !TEST_FILE.test(file))
    .filter((file) => readFileSync(file, "utf8").includes(WEIGHT))
    .map((file) => path.relative(repoRoot, file).split(path.sep).join("/"));

describe("the WCAG luminance weight has exactly two homes", () => {
  it("appears only in lib/contrast.ts and core/branding.py, tests excluded", () => {
    const found = [...holders("frontend/src"), ...holders("backend/app")].sort();

    expect(found).toEqual([
      "backend/app/core/branding.py",
      "frontend/src/lib/contrast.ts",
    ]);
  });
});
