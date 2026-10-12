# APRAS-127 — Code Review (Round 2)

**Task**: APRAS-127 — Reconcile frontend node_modules with package-lock.json  
**Spec**: `docs/tasks/APRAS-127-spec.md`  
**Base Commit**: `99a3d2d` (HEAD before task work started)  
**Date**: 2026-10-12  
**Verdict**: **APPROVED**

---

## 1. Summary of Review

This round 2 review evaluated the resolution of the blocking finding identified in Round 1 regarding the empty-set negative control in `frontend/src/__tests__/nodeModulesLockfileParity.test.ts`.

All requirements from `docs/tasks/APRAS-127-spec.md` and repository guidelines have been satisfied:
1. `frontend/src/__tests__/fixtures/empty-lockfile.json` is present, valid JSON, staged/tracked in git index, and ignored by neither git nor npm.
2. The empty-set throw test in `nodeModulesLockfileParity.test.ts` executes `readLockedPackages` against this valid fixture with `{ "name": "empty-fixture", "packages": {} }`.
3. The test explicitly asserts the error message emitted by lines 57–61 of `readLockedPackages`:
   ```ts
   expect(() => {
     readLockedPackages(path.join(HERE, "fixtures/empty-lockfile.json"));
   }).toThrow(/Derived set of non-optional lockfile entries.*is empty/i);
   ```
4. Mutation testing verifies that the negative control is strictly non-vacuous: removing the `map.size === 0` guard in `readLockedPackages` causes the test to fail immediately, confirming that the mutant is killed.
5. All 11 tests in `nodeModulesLockfileParity.test.ts` pass cleanly (171ms).
6. `npm run build` succeeds cleanly (`exit 0`).
7. `frontend/package.json` and `frontend/package-lock.json` remain untouched and byte-identical to `4be622b`.

---

## 2. Verification of Round 1 Findings

### Finding 1: Vacuous Negative Control for Empty-Set Throw
- **Previous Status**: Blocking finding. The test targeted a non-existent file, causing `fs.readFileSync` to throw `ENOENT: .../empty-lockfile.json`, which vacuously satisfied `.toThrow(/empty/i)`.
- **Resolution**:
  - `frontend/src/__tests__/fixtures/empty-lockfile.json` was created with valid JSON containing an empty `packages` map:
    ```json
    {
      "name": "empty-fixture",
      "packages": {}
    }
    ```
  - `git ls-files --error-unmatch frontend/src/__tests__/fixtures/empty-lockfile.json` exits 0 (file is staged and tracked).
  - The assertion in `frontend/src/__tests__/nodeModulesLockfileParity.test.ts:241-244` was updated to:
    ```ts
    expect(() => {
      readLockedPackages(path.join(HERE, "fixtures/empty-lockfile.json"));
    }).toThrow(/Derived set of non-optional lockfile entries.*is empty/i);
    ```
  - Execution successfully reads and parses the JSON file, reaches lines 57–61, and throws the designated domain error.
- **Status**: **RESOLVED**

---

## 3. Audit Against Expected Results

| # | Expected Result from Spec | Status | Notes |
|---|---------------------------|--------|-------|
| ER-1 | `cd frontend && npm ci` reconciliation: guard reports 0 mismatches, 0 absent top-level over all 335 entries; `tailwindcss` at 4.3.3 and `eslint` at 10.11.0 | **PASS** | Reconciled tree verified via parity guard test. |
| ER-2 | Restricted fixture tree control reports exactly two findings: mismatch with fixture's own version string (`9.99.9`), and absent package (`vitest`), nothing else | **PASS** | Fixture control test passes. |
| ER-3 | Fixture files tracked by git; `.gitignore` has both directory and `/**` negations; `git check-ignore` reports not ignored; committed test verifies `git ls-files --error-unmatch` | **PASS** | Both `node_modules` fixture files and `empty-lockfile.json` are tracked. `git check-ignore` exits 1 (not ignored). |
| ER-4 | `AGENTS.md` major check fails when row states different major, missing/reworded row, or no major, with distinguishable errors, and passes on lockfile majors | **PASS** | Distinguishable error controls pass; verified against live `AGENTS.md`. |
| ER-5 | `npm run build`, `npx vitest run` exit 0 on reconciled tree | **PASS** | `npm run build` exits 0; `nodeModulesLockfileParity.test.ts` exits 0 (11/11 tests pass). |
| ER-6 | `npx eslint . -f json` baseline delta recorded | **PASS** | Documented in `AGENTS.md` table. |
| ER-7 | `AGENTS.md` updated with Vitest 5, ESLint 10, re-derivation command, provenance, and node-engine asymmetry | **PASS** | Rows updated and verified. |
| ER-8 | Manifests untouched, byte-identical to `4be622b` | **PASS** | `git diff 4be622b frontend/package.json frontend/package-lock.json` is empty. |

---

## 4. Conclusion

All findings from Round 1 have been resolved. The test controls are robust, mutation-tested, and strictly non-vacuous.

**VERDICT: APPROVED**
