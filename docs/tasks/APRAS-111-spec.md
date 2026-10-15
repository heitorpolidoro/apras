# APRAS-111 — Audit the test suites for tests that prove nothing

## Scope

This task produces **one document and a set of follow-up task proposals**. It
deletes nothing, rewrites nothing, and leaves both test suites byte-identical
when it finishes.

The document is `docs/audits/APRAS-111-test-suite-audit.md` (new directory
`docs/audits/`). It is the deliberate sweep for the defect this project has hit
nineteen times one accident at a time: a test whose prose claims a guarantee no
assertion holds. It also sweeps for a second, newer species — a test that
reddens when the code moves in the direction its own contract allows, i.e. a
test that forbids a legitimate improvement instead of protecting a contract.

Two suites are in scope: `backend/tests/` (**4181 collected cases**, as reported
by `cd backend && SECRET_KEY=test uv run pytest --collect-only -q --no-cov` on
2026-10-01; the document records the count its own run measures) and
`frontend/src/**/__tests__/` plus colocated `*.test.ts(x)` (**188 files / 2496
collected cases**, as measured by `npx vitest list` from `frontend/` on
2026-10-01). An exhaustive per-test mutation campaign over 6600 cases is not
feasible here, so the audit runs a **stratified sweep** with the pinned
enumeration commands and the minimum mutation budgets given below, and the
document states per stratum how many cases were examined, by what method, and
how many were not examined at all.

**Not in scope** (state this verbatim in the document's "What this audit did not
cover" section, so the next auditor does not assume it was done):

- Any lasting edit to a test file or to production code. Mutations and probe
  files are temporary and removed; the audit's own lasting diff is the new
  document only.
- Every case outside the strata, and every stratum candidate not selected by the
  sampling rule. These get no mutation and no judgement. The document reports
  them as **counts measured during the audit** — collected total, candidate-set
  size, mutated, read-only judged, remainder — never as a percentage estimated
  in advance.
- Exhaustive duplicate detection. Redundancy is only judged where a stratum
  already put two tests side by side.
- Anonymous numeric literals in assertions (the `assert … == 7` /
  `toHaveLength(7)` shape). S1 covers *named* thresholds only; the anonymous
  population is counted by a pinned command and handed to a follow-up.
- A backend analogue of the frontend unhandled-error question (pytest
  `filterwarnings`/`-W error` policy). The audit may note it; sweeping it is a
  separate task.
- Mutation-testing tooling (`mutmut`, Stryker). Adopting a tool is its own
  deliverable; this audit is manual and targeted, and the document says so.
- Any production database or credentialed API call.

## Approach

### Behaviour: the tree-safety contract

This worktree is shared: other tasks' uncommitted work is present and
concurrent agents write files while the audit runs. Two rules therefore come
before any mutation, and the document records both.

**Porcelain baseline.** Before the first mutation, capture

```
git status --porcelain --untracked-files=all > <scratchpad>/porcelain.before
```

and after the last restore capture the same output into `porcelain.after`. The
check is the *diff* of the two, not the content of either: pass means **no entry
is present in `porcelain.after` whose path lies under `backend/` or `frontend/`
and that was absent from `porcelain.before`**. Entries present in both (today:
`?? backend/scripts/sync_obras_from_drive.py`, which is deliberately never
committed and must not be touched) are expected and are not failures; new
entries under `docs/` are either this task's own two files or another agent's
concurrent work, so they are recorded in the document but do not fail the
check. The document quotes both files' relevant lines and the diff command used.

**Never revert someone else's edit.** A file is eligible for mutation only if
`git status --porcelain -- <file>` is **empty** at the moment of snapshotting.
If it is not, the file is skipped and recorded as "not examined — uncommitted
work present". `git stash`, `git checkout`, `git restore` and line-numbered
`sed` restores are forbidden outright.

### Behaviour: the pre-mutation baseline is not assumed green

As observed on 2026-10-01 this checkout's backend suite is **red before the audit
touches anything**, and the red case sits in S1's mandatory module (the audit
records its own observation, which may differ — see the `Environment` rule
below):

```
cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov tests/test_bcrypt_cost.py
FAILED tests/test_bcrypt_cost.py::test_passlib_is_not_installed - AssertionError
1 failed, 9 passed
```

`passlib 1.7.4` is present in `backend/.venv`. The cause is **environment
drift, not a repository defect**: the bcrypt 5 bump removed `passlib` from
`backend/pyproject.toml`, the local venv was never resynced, and CI — which does
a fresh `uv sync --all-groups` — is green. The audit must state this
distinction in `Census and method`, because a reader who sees the failure in the
ledger will otherwise read it as a bug this audit found.

Three rules follow, and the document records all three:

- **The audit does not repair the environment.** It must not run `uv sync`, `uv
  pip install/uninstall`, `npm ci` or any other command that changes an
  installed dependency set. Concurrent agents are running tests against the same
  venv, and changing it mid-audit would silently invalidate every ledger row
  recorded before the change.
- **Dependency-set snapshot, diffed like the porcelain capture.** The audit
  cannot detect a concurrent resync by noticing it, so the detection is
  mechanical and mirrors the tree-safety contract one section above. Before the
  first mutation, capture

  ```
  cd backend && uv pip freeze > <scratchpad>/freeze.before
  ```

  and after the last restore capture the same output into `freeze.after`. The
  check is the **diff** of the two. `uv pip freeze` is read-only and therefore
  does not violate the no-repair rule. A non-empty diff — not an agent happening
  to notice something — is what triggers the stale-baseline rule: every ledger
  row whose step-0 baseline was captured before the audit observed the change is
  either re-run or marked `baseline stale — environment changed mid-audit`, and
  the diff itself is quoted in `Census and method` beside the porcelain pair. An
  empty diff is quoted too, as the positive record that the installed dependency
  set step 0 measured is the one every row was measured against. The two end
  captures are not the only ones: step 0 captures a freeze fingerprint per
  baseline run, and reuse captures an interim freeze — both defined in the
  mutation protocol below.
- **An `Environment` subsection of `Census and method`** names every case found
  failing pre-mutation, the command that showed it, and the attributed cause
  (declared-dependency drift, flake, genuine defect). Cases attributed to drift
  are handed to a follow-up proposal, not to a finding. If
  `test_passlib_is_not_installed` is **not** among the pre-mutation failures, the
  subsection says so explicitly and reports the `passlib` presence check that
  explains why (`cd backend && uv run python -c "import passlib, passlib.__about__"`
  or the `passlib` line of `freeze.before`) — a different failure found instead
  does not discharge this; the named case's change of state must be accounted
  for.

### Behaviour: the mutation protocol (this is the load-bearing part)

Every mutation follows the same **seven** steps (0–6) and the document records
all seven per mutation. Step 0 exists because every word in this protocol —
"reddened", "stays green", "a case that stays green is a finding" — is a
*difference* against the unmutated outcome, and that outcome cannot be assumed
to be green (see "Behaviour: the pre-mutation baseline is not assumed green"
above). Steps 2 and 5 exist because a mutation that silently failed to apply is
indistinguishable from a test that caught nothing, and because a line-numbered
`sed` restore has already landed a file in a third state in this repository (it
restored `due_date` where it had mutated `created_at`, after an import shifted
the line numbers).

0. **Record the pre-mutation baseline.** Run the *same* order-pinned command
   that step 3 will run, on the unmutated file, and record its full pass/fail
   set. Every later claim in the ledger row is a delta against this set:
   - **reddened** = green in step 0 and failing in step 3. Nothing else may be
     called reddened.
   - A case already failing in step 0 is recorded as **"not examined — already
     failing pre-mutation"**, with the failure's first line quoted, and it is
     never counted as evidence for or against any finding — in particular it may
     not be used to support a "stays green" classification, since it was not
     green to begin with.
   - If the entire module is red pre-mutation, the mutation is skipped and the
     module is listed under `Not examined — already failing pre-mutation`.

   Each baseline run also captures its **own** read-only
   `cd backend && uv pip freeze` and the baseline record keeps that capture's
   `shasum -a 256` as a fingerprint. This is adopted deliberately in addition to
   the two end captures: the before/after pair cannot see a resync followed by a
   revert, whereas per-run fingerprints localise any such window to the interval
   between two consecutive baseline runs. Two baseline runs with different
   fingerprints mark every row measured between them `baseline stale —
   environment changed mid-audit`.

   **Baseline reuse.** A step-0 baseline may be reused across several mutations
   of the **same module in the same session**, but only when all three conditions
   are re-asserted and named in the row: `git status --porcelain -- <file>` was
   empty at that mutation's own snapshot, every `cmp` since the baseline run came
   back clean, and the dependency-set diff is still empty. Condition (c) is
   discharged **at reuse time** by an interim read-only
   `cd backend && uv pip freeze` compared against `freeze.before` — `freeze.after`
   does not exist until the audit ends, so the end-of-audit pair cannot discharge
   a condition asserted mid-audit. The row names the interim capture (e.g.
   `freeze.i07`) and states the comparison's result. A row that reuses a
   baseline **names the baseline run it reuses** (an id the document assigns to
   each baseline run, e.g. `B-07`) instead of pasting the output again; pasting
   the same baseline text into several rows without naming the shared run is
   forbidden, because it is indistinguishable from several runs that never
   happened. Any row failing one of the three conditions runs its own baseline.

1. **Check cleanliness, then snapshot by file copy.** Assert
   `git status --porcelain -- <file>` is empty; skip and record otherwise. Copy
   the pristine file into the session scratchpad with `cp` and record the
   pristine copy's checksum (`shasum -a 256`). Restores are `cp` back.
2. **Verify the mutation took, and quote the read-back — scoped to the mutated
   line.** After editing, read back **that one line** from both the pristine
   scratchpad copy of step 1 and the file on disk, and **record both command
   outputs, not a verdict**:

   ```
   sed -n '<line>p' <scratchpad>/<pristine copy>
   sed -n '<line>p' <file>
   ```

   The first must print the original text, the second the new text, and the two
   must differ. Mutations are in-place single-line replacements, so one line
   number serves both; where a mutation changes the file's line count, the row
   records the pristine line number and the mutated one separately and the two
   `sed` commands use their own. The read-back is deliberately **line-scoped and not
   file-scoped**: a file-wide `grep` for the absence of the original text is
   unsatisfiable for a correct mutation whenever the mutated text recurs
   elsewhere in the same file, which is the common case in S3 — 240 of its 551
   frontend candidate lines are byte-identical (whitespace-trimmed) to another
   candidate line in the same file, and `toHaveLength(0)` or `assert not `
   recurs in almost every S3 module in both suites. The `sed` pair is the only
   read-back form this spec permits; auditors do not choose between
   formulations, and no file-scoped emptiness assertion is made anywhere in the
   ledger. A single word such as
   "verified" does not satisfy this step. The reason is the defect this whole
   task exists to catch: a mutation that silently failed to apply produces
   exactly the observation the audit reads as a class-1 finding ("stays green"),
   so the field that separates a real finding from a vacuous one may not itself
   be an unbacked y/n. Restores have the porcelain diff as a backstop; mutation
   application has none but this read-back. A mutation not verified present
   invalidates the run; the test is not run until it verifies.
3. **Run the narrowest order-pinned command that includes the test under
   examination plus its module** — the module, not just the single case, because
   a mutation that reddens a *neighbour* instead of the named test is itself a
   finding. Order pinning is specified under "Test criteria".
4. **Record** which mutation, which command, the step-0 baseline set, which
   cases reddened *relative to it*, and whether the case under examination was
   among them.
5. **Restore and verify byte-identity** with `cmp` against the scratchpad copy.
   The row records the **checksum pair** — the pristine copy's `shasum -a 256`
   from step 1 and the restored file's — so the restore claim carries the same
   kind of evidence the mutation claim now does.
6. **On a `cmp` mismatch, abort — do not re-restore.** A mismatch after a
   `cp`-back means the file changed from a cause outside this audit (a
   concurrent agent) and a second overwrite would destroy that work. The audit
   stops mutating, leaves the file exactly as found, and the document records
   the file, both checksums and the abort under a `Aborted mutations` subsection
   of the ledger. The only mismatch the audit may itself resolve is one it can
   attribute to its own in-flight mutation (step 2 verified present, step 5 not
   yet run) — i.e. a restore that did not execute.

Two further rules carried from the prior nineteen findings:

- **Mutate the field as well as the guard.** A test that pins a guard but not
  the value the guard protects passes on half its claim. Where a test names a
  field, one mutation removes the guard and a second replaces the field's value
  with a neighbouring field's.
- **Mutate in both directions.** For every threshold, floor, cap or limit, run
  the weakening mutation *and* the strengthening one. A test that reddens on the
  strengthening move is a finding (species "over-pin"), because it is a second,
  silent floor contradicting the ratchet the test exists to protect.

### Behaviour: the strata, their pinned enumeration and their budgets

For each stratum the document prints the **verbatim enumeration command**, the
candidate-set size it returns, the selected subset, the mutation count and the
remainder. All commands run from the repository root under `LC_ALL=C` and are
piped through `LC_ALL=C sort` so the ordering is stable across machines.

**Deterministic selection rule (S2–S4).**

- **One stride per suite.** For S2 and S3, which have a backend and a frontend
  enumeration, `N` is the **per-suite** candidate count and `k` is the
  **per-suite floor** — never the combined list against the combined budget. A
  single combined stride over `281 + 312` S2 lines at `k = 24` does not
  guarantee twelve hits in each suite, which is what the budget actually
  requires. S4 is frontend-only, so it has one stride with `k` = its whole
  budget.
- Take the suite's sorted candidate list of size `N` and select the `k` entries
  at indices `ceil(i * N / k)` for `i = 1 … k` (1-based, systematic sampling).
- **Substitution on skip.** If a selected candidate is skipped (its file is
  unclean per the tree-safety contract, or its module is already failing
  pre-mutation), the stride **advances to the next clean, green candidate** in
  sorted order, wrapping to the start of the list once, until `k` usable
  candidates are selected. Every substitution is printed as
  `skipped <file:line> (reason) → substituted <file:line>`.
- **Shortfall is only declared when the usable candidate set itself is smaller
  than `k`** — i.e. after substitution has exhausted the list. "A candidate was
  unclean" is never on its own a reason to report fewer than `k` mutations.
- Then **add** any mandatory path named in the stratum that the stride missed.
  Mandatory paths are additions above the floor, not substitutes for it.

The document prints, per suite per stratum, `N`, `k`, the stride, the selected
`file:line` list and the substitution log, so a reviewer reproduces the selection
exactly. No ad-hoc "interesting-looking" picks.

- **S1 — named thresholds, floors, caps and limits. Swept exhaustively over a
  fixed denominator.** Enumeration, both suites:

  ```
  LC_ALL=C grep -rnE '\b[A-Z][A-Z0-9_]{3,}\b[[:space:]]*(=|==|>=|<=)[[:space:]]*[0-9]+' \
    backend/tests --include='*.py' | LC_ALL=C sort
  LC_ALL=C grep -rnE '\b[A-Z][A-Z0-9_]{3,}\b[[:space:]]*(=|==|>=|<=|:)[[:space:]]*[0-9]+' \
    frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
  ```

  plus the config-declared thresholds, enumerated by file and not by grep:
  `backend/pytest.ini` (`--cov-fail-under`, `timeout`) and
  `frontend/vitest.config.ts` (`test.coverage.thresholds`). As measured on
  2026-10-01 the two greps return 60 and 50 lines; the document records the
  sizes from its own run.

  The grep output is the **candidate set**; the document then prints a triage
  table reducing it to the **threshold subset** (every excluded line listed with
  a one-phrase reason, e.g. "fixture id, not a bound"). Exhaustive bidirectional
  mutation applies to the threshold subset, and "exhaustive" in the document
  means exactly that: candidate set from the commands above, minus the printed
  exclusions. Anonymous numeric assertions are counted, not mutated:

  ```
  LC_ALL=C grep -rnE '^[[:space:]]*assert .*(==|>=|<=|<|>)[[:space:]]*[0-9]+' \
    backend/tests --include='*.py' | wc -l
  LC_ALL=C grep -rnE 'toBe(GreaterThan|LessThan|GreaterThanOrEqual|LessThanOrEqual)?(Equal)?\([0-9]+\)|toHaveLength\([0-9]+\)' \
    frontend/src --include='*.ts' --include='*.tsx' | wc -l
  ```

  `backend/tests/test_bcrypt_cost.py` is a mandatory member. Its two
  historically-suspect spots are **already derived**, as read on 2026-10-01: the
  source anchor is `assert f"BCRYPT_ROUNDS = {security.BCRYPT_ROUNDS}" in code`
  and the ratchet is `>= PRODUCTION_FLOOR`, not an equality on 12. The audit must
  therefore **not** re-describe them as defects. What it must still do is prove
  the ratchet actually ratchets: raise `app/core/security.py`'s
  `BCRYPT_ROUNDS` to 13 under the mutation protocol and record whether the module
  stays green. A red here is an over-pin (class 5). Note that this module is one
  of the pre-mutation failures described above
  (`test_passlib_is_not_installed`), so its step-0 baseline must be captured and
  that case excluded from the evidence.

- **S2 — prose claims. Budget: ≥ 12 per suite (≥ 24 total).** `N` as measured
  on 2026-10-01: 281 backend, 312 frontend. Enumeration:

  ```
  LC_ALL=C grep -rniE 'must never|never |is what keeps|proves that|guarantee' \
    backend/tests --include='*.py' | LC_ALL=C sort
  LC_ALL=C grep -rniE 'must never|never |is what keeps|proves that|guarantee' \
    frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
  ```

  Mandatory modules, **named by path** so there is no category to interpret
  (added to the stride selection):

  - `backend/tests/test_project_report_escaping.py` (escaping/interpolation)
  - `backend/tests/test_branding.py` (branding/contrast)
  - `backend/tests/test_infraction_escalation.py` (infraction escalation)
  - `backend/tests/test_assets_rbac.py` (RBAC parity)
  - `frontend/src/__tests__/themeContrast.test.ts` (branding/contrast)
  - `frontend/src/features/infraction-management/__tests__/access.test.ts`
    (RBAC parity)
  - `frontend/src/features/media-management/__tests__/MediaAssets.test.tsx`
    (media)

  Each selected case gets the mutation its prose names.

- **S3 — vacuous absence. Budget: ≥ 20 per suite (≥ 40 total).** `N` as measured
  on 2026-10-01: 563 backend, 551 frontend. The floor is **doubled relative to
  S2's per-suite floor** on the following reasoning, which the document must
  restate so the follow-up sweep is sized from evidence rather than from this
  spec's arithmetic: S3 has the largest candidate set of any stratum (1114
  lines, nearly twice S2's 593) *and* the cheapest defect to create by accident —
  an absence assertion passes when the subject is never constructed, when a
  selector typo means nothing was ever searched for, or when the fixture arrived
  empty, so a vacuous pass needs no mistake in the assertion itself. A floor of
  10 per suite would have sampled 1.8% of the largest and most defect-dense
  candidate set, a smaller per-candidate rate than S2's 4.0%; 20 per suite brings
  the rate to 3.6%, comparable to S2's. The document reports the realised
  per-candidate rate per stratum, and `Follow-up proposals` sizes the remainder
  sweep from the hit rate this stratum actually observed.
  Enumeration:

  ```
  LC_ALL=C grep -rnE 'assert not |not in ' backend/tests --include='*.py' | LC_ALL=C sort
  LC_ALL=C grep -rnE 'toHaveLength\(0\)|not\.toBeInTheDocument|toBeNull\(\)' \
    frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
  ```

  The mutation makes the forbidden thing *present*; a case that was green in
  step 0 and stays green under the mutation is a finding.

- **S4 — self-mocking frontend tests. Budget: ≥ 10 mutations** (frontend only,
  so one stride with `k = 10`). Raw `N` as measured on 2026-10-01: 269 before
  the filter below. Enumeration:

  ```
  LC_ALL=C grep -rn 'vi\.mock(' frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
  ```

  Selection is restricted, before the stride, to candidates where the mocked
  specifier also appears in the test's own name or describe block — the document
  prints that filtered list as `N`. The mutation breaks the real module; a case
  that was green in step 0 and stays green is classified "mocks the behaviour it
  claims to exercise".

- **S5 — unhandled-error survivors. Swept suite-wide, not sampled**, because it
  is answerable by instrumented runs rather than per-test mutation. See below.

Budgets are floors, not caps: the document may report more, and states for each
stratum the mutations performed against the floor. A stratum reports a shortfall
only under the condition given in the selection rule — the usable candidate set
is itself smaller than `k` after substitution — and then prints the number
reached, the usable set size and the skip reasons that shrank it.

### Behaviour: the frontend unhandled-error question (ER7, ER8)

`frontend/src/features/media-management/__tests__/MediaAssets.test.tsx`'s
"allows file selection and triggers upload" is the known instance and must
appear by name: on the jsdom 30 branch (PR #34) `URL.createObjectURL` raised
inside the handler the test exercises and the test still passed — the run only
went red because Vitest reports unhandled errors separately from assertion
failures.

The shipped configuration constrains how this can be measured, and the audit
must use these invocations and no others:

1. **Does the shipped configuration fail the run on a leaked error?** The
   include glob is root-relative, so a spec file outside `frontend/` is never
   collected (`npx vitest run <scratchpad>/leak.test.ts` returns
   `No test files found, exiting with code 1`, which measures nothing). The
   probe therefore lives **inside the project, transiently**, at
   `frontend/src/test/__audit_probe__/leak.test.ts` — a directory already
   excluded from coverage by `coverage.exclude: ["src/test/**"]`, so it cannot
   move the baseline. It is created, run, and deleted, and it is recorded in the
   ledger as a created-and-removed path, with its removal confirmed by the
   porcelain diff.

   **Its restore rule is deletion, not `cmp`.** The audit created this file, so
   there is no pristine copy to compare against and step 5 of the mutation
   protocol does not apply to it. Its restore is `rm` followed by **verified
   absence** — the path does not exist, and `git status --porcelain --
   frontend/src/test/__audit_probe__/` is empty, with the parent directory
   removed too if the audit created it. This file is deleted **even on an abort**
   (including the step-6 abort that forbids a second overwrite elsewhere): the
   abort rule exists to protect work the audit did not author, and this file is
   nobody else's work. If deletion itself fails, that is reported as the abort,
   with the path named so a human can remove it.

   It is run with the shipped script, from `frontend/`:

   ```
   npm run test -- src/test/__audit_probe__/leak.test.ts; echo "exit=$?"
   npx vitest run src/test/__audit_probe__/leak.test.ts; echo "exit=$?"
   ```

   Both exit codes are recorded (the second cross-checks that npm is not masking
   the runner's code). Because this run uses the shipped `vitest.config.ts`
   unchanged and the shipped `test` script, its conclusion is about the shipped
   configuration — that is the point of running it this way rather than with a
   private config.

2. **Find every further instance.** Instrumentation cannot be a CLI flag
   (`setupFiles` is config-only) and `frontend/vitest.config.ts` must not be
   edited, so the instrumented run uses a scratchpad config that *derives* from
   the shipped one:
   `<scratchpad>/vitest.audit.config.ts` imports
   `/Users/heitor/workspace/apras/frontend/vitest.config.ts` and `mergeConfig`s
   exactly one change — the scratchpad recorder appended after
   `./src/test/setup.ts` in `setupFiles` — with `root` set to the frontend
   directory.

   **Attempt the load bare first; prerequisites are conditional remedies, not
   steps.** Reviewers have reported *opposite* results for this exact procedure —
   one round saw the config fail to load without a `node_modules` symlink and a
   `{"type": "module"}` package.json beside it, a later round built the same
   config in a scratchpad with neither and had it load and collect 2496 cases
   across 188 files, byte-identical to plain `npx vitest list`. This spec
   therefore asserts **neither** outcome. The audit's job is to observe which one
   its own environment produces:

   1. Write `<scratchpad>/vitest.audit.config.ts` with **no** `node_modules`
      symlink and **no** `package.json` in the scratchpad, and run the `list`
      invocation below from `frontend/`.
   2. **Record the actual outcome verbatim** — the collected counts if it loads,
      or the full error text if it does not. This recorded outcome, not this
      spec's prose, is what the document reports.
   3. Only **if** the load fails, apply the remedy the quoted error calls for,
      re-run, and record that the remedy was created together with the error that
      prompted it. The two known remedies are: a `node_modules` symlink beside the
      config (`ln -s /Users/heitor/workspace/apras/frontend/node_modules
      <scratchpad>/node_modules`) for a resolution failure such as
      `[UNRESOLVED_IMPORT] Could not resolve 'vitest/config'`, and a
      `<scratchpad>/package.json` containing exactly `{"type": "module"}` for a
      CJS-interop failure such as
      `TypeError: (0 , …@tailwindcss/vite…default) is not a function`. If the bare
      load succeeded, the document says so and **creates neither**; it must not
      claim a counterfactual error it did not observe.

   Independently of whether a remedy was needed, the audit proves the derived
   config is genuinely honoured rather than silently ignored: make the appended
   recorder setup file `throw` once, confirm the run reports that error with its
   source line, then remove the throw. Invoked from `frontend/`:

   ```
   npx vitest list --config <scratchpad>/vitest.audit.config.ts
   npx vitest run  --config <scratchpad>/vitest.audit.config.ts
   ```

   The `list` invocation is run **first** and is the parity gate: it must report
   the same collected-file and collected-case counts as plain `npx vitest list`
   — **188 files / 2496 cases** as measured on 2026-10-01 — before the `run`
   output is used for any conclusion about the shipped configuration. If the two
   counts differ, the instrumented results are reported as a separate
   configuration and not as a statement about the shipped one. The document
   records both count pairs, the parity verdict, the honoured-config proof, any
   prerequisite path it created **and the error that forced it**, and the derived
   config's diff against the shipped file so a reviewer sees the single delta.

   The recorder captures errors reaching `window.onerror` /
   `unhandledrejection` and attributes each to the currently running case.
   Nothing under `frontend/` changes: the config and any remedy artefact live in
   the scratchpad, which is why ER5 is satisfied by the porcelain diff rather than
   violated.

   Per instance, report whether the suite would have noticed without Vitest's
   separate report — i.e. whether any assertion in that case fails once the
   throw happens.

3. **If the run does not already fail per-case**, propose the configuration that
   makes a leaked error fail **the case that leaked it**, and prove the proposal
   works by re-running the step-1 probe under a scratchpad config carrying it.
   The proposal is described, not committed: implementing it in
   `frontend/vitest.config.ts` is a follow-up task.

### Files touched

- `docs/audits/APRAS-111-test-suite-audit.md` — **new**, the entire deliverable.
  Required sections, in this order: `Census and method` (per-suite, per-stratum
  table with enumeration commands, candidate sizes, budgets, selection stride,
  substitution log and remainder counts, plus the `Environment` subsection, the
  porcelain and `uv pip freeze` before/after diffs, the per-baseline-run freeze
  fingerprints, and the
  `pytest --version --version` banner); `Mutation ledger` (one row per
  mutation: file:line, mutation, the step-2 **quoted read-back** (the
  line-scoped `sed -n '<line>p'` output from the pristine scratchpad copy and
  from the mutated file, side by side),
  order-pinned command including `-p no:randomly --no-cov`, **step-0 baseline
  pass/fail set or the id of the reused baseline run, with that run's
  `uv pip freeze` fingerprint** (and, on a reused baseline, the named interim
  freeze capture and its comparison against `freeze.before`), cases reddened relative
  to that baseline, case-under-examination reddened y/n, and the restore's
  **checksum pair** — plus the `Aborted mutations`,
  `Not examined — uncommitted work present` and
  `Not examined — already failing pre-mutation` subsections); `Findings` (one entry per non-load-bearing test, with its
  class); `Over-pins`; `Unhandled errors` (ER7/ER8, including the porcelain
  diff for the probe file); `Examined and kept`; `Coverage and lint baselines`;
  `Follow-up proposals`; `What this audit did not cover`.
- `docs/tasks/APRAS-111-spec.md` — this file.
- No other lasting path. Transient paths (mutated test files, the frontend probe
  spec) are created and removed inside the protocol; what proves they are gone
  is the porcelain diff defined under "the tree-safety contract", **not** a bare
  `git status --porcelain` being empty — it is not empty today and never will be
  in this worktree.

### Classification (ER3) — a closed list

Every test the audit proposes to delete or rewrite carries exactly one class:

1. **asserts nothing** — no mutation of the code it names reddens it;
2. **already asserted elsewhere** — and the other test is named;
3. **mocks the behaviour it claims to exercise**;
4. **stays green while the code it exercises raises**;
5. **over-pin** — reddens when the pinned value moves in the direction its own
   contract allows (it yields a *rewrite* proposal, never a deletion).

Class 5 is an addition to the four of expected result 3, not a substitution:
classes 1–4 remain the only grounds for proposing a **deletion**. Slowness,
verbosity and age are never grounds for anything, and the document says so.
A test with no verified mutation behind it is never listed as a finding at all
(ER1): it goes in `Examined and kept` or is reported as not examined. Likewise, a
test with no **green step-0 baseline** behind it is never classified: "stays
green" (classes 1, 3, 4) and "reddens on the safe direction" (class 5) are both
deltas, and a test that was already failing before the mutation supports
neither.

### Coverage and lint baselines (ER6)

The audit records the baseline from the exact commands, quoted in the document
with their output summary lines:

- `cd backend && SECRET_KEY=test uv run pytest` (`pytest.ini` already carries
  `--cov=app --cov-fail-under=90`) — this full-suite command keeps the inherited
  coverage gate, because measuring it is the point;
- `cd frontend && npm run test:coverage`;
- `cd frontend && npm run lint` — the error and file counts only (~375 errors
  across 64 files today). Every follow-up proposal inherits "no worse than this
  base", never "zero repo-wide".

Because this task changes no test, there is no "after" to report here. The rule
is carried into the follow-ups instead: **each follow-up proposal quotes this
baseline and requires the same command be re-run after its change, with any drop
explained line by line** rather than accepted as a side effect of a deletion.
The audit also states, per proposed deletion, which lines of production code
that test is the sole cover for — so the follow-up knows in advance where the
drop will land.

### Test criteria

There is no new test; the deliverable is a document, and what proves it is
re-executability.

- **Every ledger command is order-pinned, coverage-free and copy-pasteable.**
  Backend rows carry the full command including environment, and every backend
  ledger command includes:
  - `-p no:randomly` (harmless when the plugin is absent, decisive when it is
    not); if any order-randomising plugin is active, the row additionally records
    the `--randomly-seed` value used;
  - **`--no-cov`**. Narrow runs inherit `--cov=app --cov-fail-under=90` from
    `backend/pytest.ini`'s `addopts`, so a per-module run ends
    `FAIL Required test coverage of 90% not reached. Total coverage: 49.69%` and
    exits non-zero no matter what the tests did — which makes the exit code, the
    thing the ledger reads as "reddened", meaningless. `--no-cov` is required on
    every ledger row. The full-suite baseline command in
    `Coverage and lint baselines` keeps the gate and is the only exception.

  The ledger row's canonical shape is therefore
  `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov <path>`.

  Frontend rows pin the single spec path and record the Vitest version line.
  A reviewer re-running a sampled row must observe the recorded outcome.
- **The plugin banner comes from the doubled flag.** `Census and method` quotes
  the output of

  ```
  cd backend && SECRET_KEY=test uv run pytest --version --version
  ```

  once, as the record of which plugins were loaded. The single `--version` prints
  one line (`pytest 9.1.1`) and **no banner at all**; only `--version --version`
  (equivalently `-VV`) prints `This is pytest version 9.1.1, imported from …`
  followed by `registered third-party plugins:`. As measured on 2026-10-01 that
  list is `pytest-cov-7.1.0`, `pytest-timeout-2.4.0`, `anyio-4.14.2` — three
  entries, including `anyio`, and no order randomiser.
- Every enumeration command in the census table, re-run, yields the recorded
  candidate-set size (or, if another task has since changed the suites, the
  document's `as measured on` date explains the delta).
- The ER8 probe runs (both invocations, both exit codes) and, if a configuration
  is proposed, the same probe under it, are recorded with their commands.
- The porcelain diff described in "the tree-safety contract" contains **no path
  under `backend/` or `frontend/`** that was absent before the audit; both
  captures and the diff command are quoted in the document.

## Expected Results

- [ ] `docs/audits/APRAS-111-test-suite-audit.md` exists with all nine required
      sections, and lists every test judged non-load-bearing with the mutation
      that should have reddened it and the observation that it stayed green.
      No test appears as a finding without a verified-present mutation behind it.
- [ ] The `Census and method` section reports, per suite and per stratum S1–S5:
      total collected (backend stated as 4181 cases, frontend as 188 files /
      2496 cases, or the counts its own run measures), candidate-set size with
      the verbatim enumeration command as written in this spec, the budget and
      selection stride applied, how many were mutated, how many were read-only
      judged, and the remainder as a measured count — no percentage is estimated
      anywhere in the document.
- [ ] Every mutation's ledger row records, in this order: the mutated file and
      line; the mutation; the **line-scoped quoted read-back** proving it
      applied — the output of `sed -n '<line>p'` on the pristine scratchpad copy
      and on the mutated file, showing the original text and the new text
      respectively, as command output rather than a y/n, with no file-scoped
      emptiness assertion anywhere in the ledger; the full
      order-pinned command; a **step-0 pre-mutation baseline**, either its own
      pass/fail set from the same command on the unmutated file or the named id
      of a reused baseline run; which cases reddened against that baseline; and
      whether the case under examination was among them, a mutation that reddens
      only a neighbour being a finding in its own right. "Reddened" is recorded
      only for cases green in step 0 and failing in step 3; a case already
      failing in step 0 appears under `Not examined — already failing
      pre-mutation` with its failure line quoted and is never evidence for any
      finding. A baseline is reused only within one module in one session with
      the three stated conditions re-asserted and the reused run named; pasting
      identical baseline text into several rows without naming the shared run is
      a defect; a reused baseline's row also names the interim `uv pip freeze`
      capture taken at reuse time and its comparison against `freeze.before`.
      Every backend ledger command includes both `-p no:randomly` (or
      an explicitly recorded `--randomly-seed` where a randomiser is active) and
      **`--no-cov`**, so the row's exit code reflects the tests rather than
      `pytest.ini`'s inherited `--cov-fail-under=90`; the full-suite baseline
      command in `Coverage and lint baselines` is the sole exception and keeps
      the gate.
- [ ] `Census and method` contains an `Environment` subsection naming every case
      found failing pre-mutation, the command that showed it, and its attributed
      cause. If `backend/tests/test_bcrypt_cost.py::test_passlib_is_not_installed`
      is among them, the cause is stated as `passlib 1.7.4` installed in
      `backend/.venv` while not declared in `backend/pyproject.toml` — local
      environment drift, CI green. If it is **not** among them, the subsection
      says so and reports the `passlib` presence check that explains why. The
      document states that the audit ran no `uv sync` or other
      dependency-changing command.
- [ ] `Census and method` quotes a `uv pip freeze` capture taken before the first
      mutation and after the last restore, together with their diff. A non-empty
      diff marks every row whose step-0 baseline predates the observed change as
      `baseline stale — environment changed mid-audit` (or re-runs it); an empty
      diff is quoted as the positive record that every row was measured against
      the dependency set step 0 measured. Each baseline run additionally records
      the `shasum -a 256` fingerprint of its own `uv pip freeze` capture, and any
      two consecutive baseline runs with differing fingerprints mark every row
      measured between them stale.
- [ ] S1 is exhaustive over a printed denominator: the two `grep` candidate
      lists plus the `pytest.ini` / `vitest.config.ts` threshold declarations,
      minus a printed triage table in which every excluded line carries a
      reason; every member of the remaining threshold subset has both a
      weakening and a strengthening mutation in the ledger. The anonymous
      numeric-assertion counts are recorded and deferred by name.
- [ ] S2 records ≥ 12 mutations **per suite** (≥ 24 total), S3 ≥ 20 per suite
      (≥ 40 total) and S4 ≥ 10, with `N` and `k` stated **per suite** and each
      suite's stride printing `N`, `k`, the stride and the selected `file:line`
      list so the selection is reproducible without judgement. A skipped
      candidate (unclean file, or module already failing pre-mutation) is
      replaced by the next clean, green candidate in sorted order and logged as
      `skipped <file:line> (reason) → substituted <file:line>`; a shortfall is
      reported only where the usable candidate set is itself smaller than `k`.
      The document states S3's detection reasoning — why its per-suite floor is
      20 rather than 10, given its 563 + 551 candidate set and the cheapness of a
      vacuous absence — reports the realised per-candidate rate for each
      stratum, and sizes the `Follow-up proposals` remainder sweep from the hit
      rate S3 actually observed.
- [ ] S2's mandatory modules are listed and mutated **by path**:
      `backend/tests/test_project_report_escaping.py`,
      `backend/tests/test_branding.py`,
      `backend/tests/test_infraction_escalation.py`,
      `backend/tests/test_assets_rbac.py`,
      `frontend/src/__tests__/themeContrast.test.ts`,
      `frontend/src/features/infraction-management/__tests__/access.test.ts`,
      `frontend/src/features/media-management/__tests__/MediaAssets.test.tsx` —
      each added above the stride, not in place of a stride slot.
- [ ] Every test proposed for deletion or rewrite carries exactly one of the five
      classes (asserts nothing / already asserted by a named test / mocks the
      behaviour it claims / stays green while its subject raises / over-pin), and
      classes 1–4 are the only grounds offered for a deletion. The document
      states explicitly that slowness, verbosity and age are not grounds.
- [ ] An `Examined and kept` section names every test examined and kept despite
      looking redundant, each with its reason.
- [ ] No test file and no production file is changed by the audit, proved by
      diffing `git status --porcelain --untracked-files=all` captured before the
      first mutation against the same output captured after the last restore:
      **no entry under `backend/` or `frontend/` appears in the second that was
      absent from the first** (pre-existing entries, including
      `?? backend/scripts/sync_obras_from_drive.py`, are expected and are not
      failures). Both captures and the diff command are quoted. Every mutation
      row carries a restore checksum pair (pristine scratchpad copy and restored
      file) that matches, and the ledger carries a
      `Not examined — uncommitted work present` subsection listing files skipped
      because `git status --porcelain -- <file>` was non-empty at snapshot time,
      a `Not examined — already failing pre-mutation` subsection, and an
      `Aborted mutations` subsection in which any post-restore `cmp` mismatch not
      attributable to the audit's own mutation is reported with both checksums
      and no second overwrite.
- [ ] A `Coverage and lint baselines` section quotes the backend pytest coverage
      summary, the frontend `npm run test:coverage` summary and the
      `npm run lint` error/file counts from those exact commands; every follow-up
      proposal repeats the baseline and requires a line-by-line explanation of
      any drop it causes.
- [ ] The `Unhandled errors` section names
      `frontend/src/features/media-management/__tests__/MediaAssets.test.tsx`'s
      "allows file selection and triggers upload" explicitly, lists every further
      instance found by the instrumented run, and states for each whether the
      suite would have noticed without Vitest's separate unhandled-error report.
- [ ] The same section records, for a transient probe spec created at
      `frontend/src/test/__audit_probe__/leak.test.ts` and then deleted, the exit
      codes of both `npm run test -- src/test/__audit_probe__/leak.test.ts` and
      `npx vitest run src/test/__audit_probe__/leak.test.ts` run from
      `frontend/`, together with the collected-file/collected-case counts proving
      the probe was actually collected; it states that these runs used the
      shipped `vitest.config.ts` and `test` script unchanged; it records the
      probe's removal as **verified absence** of
      `frontend/src/test/__audit_probe__/` (not a `cmp` against a pristine copy,
      which does not exist for a file the audit created) and states the probe is
      deleted even on an abort; and — if the run does not already fail the case
      that leaked the error — it proposes a configuration that makes it do so,
      with the probe re-run under that configuration as evidence.
- [ ] The instrumented suite run is performed via a scratchpad config
      (`npx vitest run --config <scratchpad>/vitest.audit.config.ts` from
      `frontend/`) derived from `frontend/vitest.config.ts` by appending one
      setup file, and `frontend/vitest.config.ts` is not modified. The document
      records the **observed** result of loading that config with no
      `node_modules` symlink and no `package.json` in the scratchpad — the
      collected counts if it loads, or the error text verbatim if it does not —
      and names each remedy artefact it created **together with the quoted error
      that forced it**, creating none if the bare load succeeded. It records the
      honoured-config proof (the appended setup file made to throw, the run
      reporting that error with its source line). Before any conclusion is drawn
      from the instrumented run, a parity gate is recorded: `npx vitest list
      --config <scratchpad>/vitest.audit.config.ts` and plain `npx vitest list`
      both run from `frontend/`, their collected-file/collected-case counts
      quoted side by side (188 / 2496 as measured on 2026-10-01) with an explicit
      match/mismatch verdict; on a mismatch the instrumented findings are
      labelled as describing a separate configuration, not the shipped one.
- [ ] The `Over-pins` section lists every member of the S1 threshold subset and
      states, for each, whether moving it in the safe direction keeps the suite
      green; `backend/tests/test_bcrypt_cost.py` is covered by name, including
      the evidence from raising `BCRYPT_ROUNDS` to 13 and observing whether the
      module stays green. The document does **not** describe that module's source
      anchor or floor assertion as defects: as of 2026-10-01 the anchor is
      `assert f"BCRYPT_ROUNDS = {security.BCRYPT_ROUNDS}" in code` and the ratchet
      is `>= PRODUCTION_FLOOR`.
- [ ] `Census and method` quotes the pytest plugin banner from
      `cd backend && SECRET_KEY=test uv run pytest --version --version` — the
      doubled flag, because a single `--version` prints only `pytest 9.1.1` and no
      banner — listing `pytest-cov`, `pytest-timeout` and `anyio`, and it quotes
      the Vitest version line.
- [ ] `Follow-up proposals` lists one proposal per remediation cluster, each
      naming the tests it covers, their class, and the coverage baseline it must
      report against; the deferred anonymous-numeric-assertion population and the
      ER8 configuration change are each among them, as is any environment drift
      found by the `Environment` subsection (repairing it is explicitly a
      follow-up, not part of this audit).

## Out of Scope

No test or production file is changed by this task; adopting a mutation-testing
tool, sweeping the stratum remainders counted in `Census and method`, the
anonymous numeric assertions, the pytest warnings-as-errors question, and
implementing the ER8 configuration are all follow-up work.

**No environment repair.** Resyncing `backend/.venv` (removing the undeclared
`passlib`) is a follow-up. The audit records the drift and works around it via
the step-0 baseline; it does not run `uv sync`, `uv pip install/uninstall` or
`npm ci`, because concurrent agents share this venv and changing it mid-audit
would invalidate the ledger.
