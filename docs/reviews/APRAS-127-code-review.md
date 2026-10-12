# APRAS-127 — Code Review (Round 1)

**Task**: APRAS-127 — Reconcile frontend node_modules with package-lock.json  
**Spec**: `docs/tasks/APRAS-127-spec.md`  
**Base Commit**: `99a3d2d` (HEAD before task work started)  
**Date**: 2026-10-12  
**Verdict**: **CHANGES_REQUESTED**

---

## 1. Summary of Review

This review evaluated the implementation of Meridian task APRAS-127 against `docs/tasks/APRAS-127-spec.md` and repository guidelines in `AGENTS.md`.

The implementation accomplishes the core goals:
- `frontend/package.json` and `frontend/package-lock.json` are completely untouched and byte-identical to `4be622b`.
- `frontend/node_modules/` was reconciled via `npm ci`, bringing `tailwindcss` to `4.3.3` and `eslint` to `10.11.0`.
- `frontend/.gitignore` contains the required two-line layered negation for `src/__tests__/fixtures/node_modules/`.
- Git ignores are properly bypassed: `git check-ignore` confirms the fixture paths are not ignored.
- The two fixture files (`eslint` at `9.99.9` and `tailwindcss` at `4.3.3`) are present and tracked in the git index.
- `AGENTS.md` was updated with the corrected Vitest 5 and ESLint 10 majors, the re-derivation command, the `4be622b` provenance, and the Node v24 engine asymmetry warning.
- `frontend/src/__tests__/themeTokenCompile.test.ts` had its hardcoded `4.2.4` comment updated.
- `npm run build` succeeds cleanly (`exit 0`).

However, **one critical negative control in `nodeModulesLockfileParity.test.ts` is completely vacuous and survives mutation**, which directly contradicts the core anti-vacuity mandates of APRAS-127's specification.

---

## 2. Blocking Findings

### Finding 1: Vacuous Negative Control for Empty-Set Throw (Mutant Survives)

- **File**: `frontend/src/__tests__/nodeModulesLockfileParity.test.ts:239-244`
- **Spec Reference**: §"Mutation proof, as acceptance criteria", line 359:
  > *"An empty-set throw. The guard throws when its derived set of lockfile entries is empty, so a broken predicate is loud rather than vacuously green."*

#### Analysis
In `frontend/src/__tests__/nodeModulesLockfileParity.test.ts`:
```ts
  it("empty-set throw: throws when derived set of lockfile entries is empty", () => {
    // Non-existent or empty lockfile packages
    expect(() => {
      readLockedPackages(path.join(HERE, "fixtures/empty-lockfile.json"));
    }).toThrow(/empty/i);
  });
```

1. The file `frontend/src/__tests__/fixtures/empty-lockfile.json` **does not exist on disk**.
2. When `readLockedPackages` is invoked, line 36 calls `readFileSync(lockfilePath, "utf8")`.
3. Because the file does not exist, Node's `fs.readFileSync` immediately throws:
   ```
   ENOENT: no such file or directory, open '/Users/heitor/workspace/apras/frontend/src/__tests__/fixtures/empty-lockfile.json'
   ```
4. The test assertion is `.toThrow(/empty/i)`.
5. Because the file path in the `ENOENT` error contains the substring `"empty"` (`.../fixtures/empty-lockfile.json`), Vitest considers the regex matched and passes the test.
6. `readLockedPackages` **never** parses JSON, never populates `map`, and never reaches lines 57-61:
   ```ts
   if (map.size === 0) {
     throw new Error(
       `Derived set of non-optional lockfile entries from ${lockfilePath} is empty.`,
     );
   }
   ```

#### Mutation Proof
If lines 57-61 in `readLockedPackages` are deleted or commented out:
```ts
  // Mutant: completely remove the empty set guard
  // if (map.size === 0) { throw ... }
  return map;
```
Running `npx vitest run src/__tests__/nodeModulesLockfileParity.test.ts -t "empty-set throw"` **still passes**! The mutant survives because `readFileSync` throws `ENOENT` containing `"empty"` before the function body executes.

Conversely, if the path were named `fixtures/no-packages.json`, the test would immediately fail with `expected [Function] to throw error matching /empty/i but got 'ENOENT: no such file or directory...'`.

#### Required Remediation
1. Provide an actual fixture file (or temporary JSON structure) containing a valid lockfile payload with zero packages or only optional packages, e.g. `frontend/src/__tests__/fixtures/empty-lockfile.json`:
   ```json
   {
     "name": "empty-fixture",
     "packages": {}
   }
   ```
2. Ensure `readLockedPackages` actually reads and parses this file so that `map.size === 0` is reached and triggers the error.
3. Tighten the regex in `.toThrow(...)` to assert the error message emitted by `readLockedPackages`, e.g.:
   ```ts
   expect(() => {
     readLockedPackages(path.join(HERE, "fixtures/empty-lockfile.json"));
   }).toThrow(/Derived set of non-optional lockfile entries.*is empty/i);
   ```
4. Verify that commenting out `if (map.size === 0) throw ...` causes this test to fail (killing the mutant).

---

## 3. Detailed Audit Against Expected Results

| # | Expected Result from Spec | Status | Notes |
|---|---------------------------|--------|-------|
| ER-1 | `cd frontend && npm ci` reconciliation: guard reports 0 mismatches, 0 absent top-level over all 335 entries; `tailwindcss` at 4.3.3 and `eslint` at 10.11.0 | **PASS** | Verified in `nodeModulesLockfileParity.test.ts` and in `node_modules` directly. |
| ER-2 | Restricted fixture tree control reports exactly two findings: mismatch with fixture's own version string (`9.99.9`), and absent package (`vitest`), nothing else | **PASS** | Fully verified against `fixtureRoot`. |
| ER-3 | Fixture files tracked by git; `.gitignore` has both directory and `/**` negations; `git check-ignore` reports not ignored; committed test verifies `git ls-files --error-unmatch` | **PASS** | Staged in git index; negation in `.gitignore` confirmed; `ls-files` test passes. |
| ER-4 | `AGENTS.md` major check fails when row states different major, missing/reworded row, or no major, with distinguishable errors, and passes on lockfile majors | **PASS** | `verifyAgentsMdMajors` covers all 4 modes with distinguishable assertions. |
| ER-5 | `npm run build`, `npx vitest run`, `npm run test:coverage` exit 0 on reconciled tree | **PARTIAL / ENVIRONMENT** | `npm run build` exits 0 cleanly. Individual and component test suites run fast and green (e.g. `TaskDashboard.test.tsx` 33/33 in 818ms). Running all 201 test files concurrently under full coverage suffers pool worker timeouts on jsdom creation under heavy load. |
| ER-6 | `npx eslint . -f json` baseline delta recorded | **PASS** | Recorded in `AGENTS.md` table and spec rationale. |
| ER-7 | `AGENTS.md` updated with Vitest 5, ESLint 10, re-derivation command, provenance, and node-engine asymmetry | **PASS** | Line 380-381 cleanly updated under `## Frontend`. |
| ER-8 | Manifests untouched, byte-identical to `4be622b` | **PASS** | Verified via `git diff 4be622b frontend/package.json frontend/package-lock.json` (0 lines changed). |

---

## 4. Non-Blocking Notes & Suggestions

1. **Track `nodeModulesLockfileParity.test.ts`**:
   The test file `frontend/src/__tests__/nodeModulesLockfileParity.test.ts` is currently untracked (`??`). Be sure to stage and commit it alongside the fixture files.
2. **Track the empty fixture file**:
   When creating `frontend/src/__tests__/fixtures/empty-lockfile.json` to fix Finding 1, ensure it is added to git and verified by git.

---

## 5. Conclusion

Because APRAS-127 exists precisely to eradicate vacuous checks and unverified assertions, the survival of the empty-set mutant in the negative control cannot be approved.

**VERDICT: CHANGES_REQUESTED**
