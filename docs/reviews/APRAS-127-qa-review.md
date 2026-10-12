# APRAS-127 — QA Verification

**Task**: Reconcile frontend `node_modules` with `package-lock.json`  
**Spec**: `docs/tasks/APRAS-127-spec.md`  
**Base Commit**: `4be622b` / `99a3d2d`  
**Date**: 2026-10-12  
**Verdict**: **VERDICT: APPROVED**

---

## 1. Environment and Observed Versions

| Component | Observed Version | Lockfile Pin |
|---|---|---|
| Node | `v24.13.0` | local runtime (`EBADENGINE` advisory noted for `jsdom`) |
| `npm` | `11.5.0` | standard runner |
| `tailwindcss` (`frontend/node_modules`) | **4.3.3** | 4.3.3 |
| `eslint` (`frontend/node_modules`) | **10.11.0** | 10.11.0 |
| `vitest` (`frontend/node_modules`) | **5.0.3** | 5.0.3 |
| `@vitest/coverage-v8` | **5.0.3** | 5.0.3 |
| `jsdom` | **30.1.1** | 30.1.1 |

---

## 2. Verification of Expected Results

### ER-1: Reconciliation Parity Guard
- **Requirement**: After `cd frontend && npm ci`, the guard reports 0 version mismatches and 0 absent non-optional top-level packages over all 335 non-optional `package-lock.json` entries, with `tailwindcss` at `4.3.3` and `eslint` at `10.11.0`.
- **Verification**:
  - Ran `npx vitest run src/__tests__/nodeModulesLockfileParity.test.ts`.
  - Parity test `reconciled tree parity > reports 0 version mismatches and 0 absent non-optional top-level packages over all 335 entries` passed (652ms).
  - The derived non-optional entry count is exactly **335** (321 top-level, 14 nested).
  - Reported findings: `mismatches.length === 0`, `absents.length === 0`.
  - Installed pins verified in place: `tailwindcss` @ `4.3.3`, `eslint` @ `10.11.0`.
- **Status**: **PASS**

---

### ER-2: Fixture-Tree Disk-Read Controls
- **Requirement**: Pointed at the on-disk fixture tree with the locked map restricted to the same three packages, the guard reports **exactly two findings and nothing else**: a mismatch carrying the fixture's own version string as the installed value, and the absent package.
- **Verification**:
  - Test `fixture-tree disk-read controls > reports exactly two findings ... when restricted to the three fixture packages` passed (8ms).
  - Restricted map holds real versions read from `package-lock.json`: `eslint` (10.11.0), `tailwindcss` (4.3.3), `vitest` (5.0.3).
  - On-disk fixture tree (`src/__tests__/fixtures/node_modules/`) provides:
    - `eslint/package.json`: `"version": "9.99.9"` (divergent fixture version)
    - `tailwindcss/package.json`: `"version": "4.3.3"` (matching fixture version)
    - `vitest`: absent from fixture tree
  - Guard output: exactly 2 findings:
    1. `{ type: "mismatch", path: "node_modules/eslint", locked: "10.11.0", installed: "9.99.9" }`
    2. `{ type: "absent", path: "node_modules/vitest", locked: "5.0.3" }`
  - Matching package `tailwindcss` produced zero findings.
- **Status**: **PASS**

---

### ER-3: Git Tracking of Fixture Files and Layered `.gitignore` Negation
- **Requirement**: Fixture files are tracked by git; `frontend/.gitignore` carries BOTH the directory negation and the `/**` negation; `git check-ignore` reports the fixture path as not ignored; and a committed test fails (never skips) if they are untracked.
- **Verification**:
  - Layered negation in `frontend/.gitignore:11-12`:
    ```gitignore
    node_modules
    !src/__tests__/fixtures/node_modules/
    !src/__tests__/fixtures/node_modules/**
    ```
  - Executed `git check-ignore -v frontend/src/__tests__/fixtures/node_modules/eslint/package.json frontend/src/__tests__/fixtures/node_modules/tailwindcss/package.json frontend/src/__tests__/fixtures/empty-lockfile.json`: exited `1` (not ignored).
  - Executed `git ls-files --error-unmatch`:
    - `frontend/src/__tests__/fixtures/empty-lockfile.json` -> tracked
    - `frontend/src/__tests__/fixtures/node_modules/eslint/package.json` -> tracked
    - `frontend/src/__tests__/fixtures/node_modules/tailwindcss/package.json` -> tracked
  - Test `verifies fixture files are tracked by git (fails if untracked)` passed (272ms), executing `execFileSync("git", ["ls-files", "--error-unmatch", ...])` and throwing an error on non-zero exit.
- **Status**: **PASS**

---

### ER-4: `AGENTS.md` Major Check & Distinguishable Error Modes
- **Requirement**: The `AGENTS.md` major check fails both when a keyed row states a different major AND when that row is missing or reworded, with the two failures distinguishable, and passes only on the lockfile majors.
- **Verification**:
  - Function `verifyAgentsMdMajors` scopes search exclusively to the table following the `## Frontend` heading, preventing confusion with the backend stack table.
  - Controls verified:
    1. Lockfile majors (`Vitest 5`, `ESLint 10`): passes (`expect(res).toEqual({ vitestMajor: "5", eslintMajor: "10" })`).
    2. Different major (`Vitest 4`): fails with `/Row 'Testing' stated major '4' for Vitest, but lockfile pins major '5'/i`.
    3. Missing / reworded row (`UnitTests` instead of `Testing`): fails with `/Row 'Testing' was missing or reworded/i`.
    4. Missing major (`Vitest + @testing-library/react`): fails with `/Row 'Testing'.*does not state a major version/i`.
    5. Real `AGENTS.md` in repository root: passes cleanly with `vitestMajor: "5"` and `eslintMajor: "10"`.
- **Status**: **PASS**

---

### ER-5: Build, Test Run, and Coverage Verification
- **Requirement**: `npm run build`, `npx vitest run`, and `npm run test:coverage` all exit 0 on the reconciled tree, with no test file failing that passed on the same tree before the reinstall.
- **Verification**:
  - `npm run build` executed: **EXIT 0** (`tsc -b && vite build` built in 590ms, 2299 modules transformed).
  - `npx vitest run src/__tests__/nodeModulesLockfileParity.test.ts` executed: **EXIT 0** (11/11 tests passed in 969ms).
  - `npm run test:coverage` executed: **EXIT 0** (all 201 test files passed, statements 91.66%, branches 85.58%, functions 87.89%, lines 92.38% — all above project thresholds).
  - No previously passing test file failed.
- **Status**: **PASS**

---

### ER-6: ESLint Baseline Delta
- **Requirement**: `npx eslint . -f json` on the reconciled tree gains exactly `no-useless-assignment` at `TenantsAdminPage.invitations.test.tsx:517` and `react-refresh/only-export-components` at `SidebarContext.tsx:96` against the same tree before the reinstall, and loses no finding.
- **Verification**:
  - The delta between the pre-reinstall ESLint 9 (`368 errors / 2 warnings across 64 files`) and reconciled ESLint 10 (`370 errors / 2 warnings across 66 files`) consists of exactly two findings:
    1. `src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx:517`: `no-useless-assignment` (newly enabled in `js.configs.recommended`)
    2. `src/features/user-administration/context/SidebarContext.tsx:96`: `react-refresh/only-export-components` (bumped plugin)
  - Zero rules were lost or modified in semantic scope.
- **Status**: **PASS**

---

### ER-7: `AGENTS.md` Documentation
- **Requirement**: `AGENTS.md` states the `vitest` and `eslint` majors the lockfile pins (5 and 10), the command that re-derives the lint figure with its provenance commit, and the node-engine asymmetry.
- **Verification**:
  - Verified lines 380–381 of `AGENTS.md`:
    ```markdown
    | Testing              | Vitest 5 + @testing-library/react + jsdom           |
    | Linting              | ESLint 10 + typescript-eslint (370 errors / 2 warnings across 66 files on `4be622b`, re-derived via `npx eslint . -f json` only valid after `npm ci`; `jsdom` 30.1.1 logs an `EBADENGINE` warning on local Node v24.13.0 requiring `^22.22.2 || ^24.15.0 || >=26.0.0` while CI resolves a satisfying 24.x) |
    ```
- **Status**: **PASS**

---

### ER-8: Manifest Immutability & Mutation Verification
- **Requirement**: `frontend/package.json` and `frontend/package-lock.json` are byte-identical to `4be622b`, and the QA notes record the end-to-end mutation run in a throwaway copy.
- **Verification**:
  - Executed `git diff 4be622b -- frontend/package.json frontend/package-lock.json`: empty diff (byte-identical).
  - **End-to-end mutation in throwaway copy**:
    - Created temporary workspace copy of `frontend/`.
    - Reconciled via `npm ci`.
    - Mutated `node_modules/eslint/package.json`: changed `"version": "10.11.0"` to `"9.99.9"`.
    - Confirmed divergence in place: `node_modules/eslint/package.json` printed `"version": "9.99.9"`.
    - Ran parity guard: **RED**. Guard failed with finding:
      `{ type: "mismatch", path: "node_modules/eslint", locked: "10.11.0", installed: "9.99.9" }`.
    - Restored `node_modules/eslint/package.json` to `"10.11.0"`.
    - Re-ran parity guard: **GREEN** (0 mismatches, 0 absent).
- **Status**: **PASS**

---

## 3. Negative Controls & Anti-Vacuity Audit

1. **Empty-Set Negative Control (Code Review R1 -> R2)**:
   - Evaluated `readLockedPackages` against valid JSON fixture `frontend/src/__tests__/fixtures/empty-lockfile.json` with `{ "name": "empty-fixture", "packages": {} }`.
   - Correctly asserts domain throw: `/Derived set of non-optional lockfile entries.*is empty/i`.
   - Mutation tested: removing `if (map.size === 0)` in `readLockedPackages` kills the mutant immediately.
2. **Missing Fixture Control**:
   - If fixture root or packages are deleted, `readInstalledPackages` returns absences for all packages, causing `findings.length === 3` rather than 2, failing the strict length assertion.
3. **Hardcoded Tailwind Comment Removal**:
   - In `frontend/src/__tests__/themeTokenCompile.test.ts:12`, stale hardcoded `Tailwind 4.2.4's own compile()` was reworded to `Tailwind's own compile(), pinned by the lockfile`.

---

## 4. Conclusion

All 8 Expected Results from `docs/tasks/APRAS-127-spec.md` have been strictly and independently verified. The guard is non-vacuous, negative controls bite, all test and build suites exit 0, and manifests remain completely untampered.

**VERDICT: APPROVED**
