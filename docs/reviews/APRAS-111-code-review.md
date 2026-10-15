# APRAS-111 — Code review (document deliverable)

VERDICT: NEEDS_REVISION

Reviewed: one staged path, `docs/audits/APRAS-111-test-suite-audit.md`, new,
5407 lines. Branch `master` at `2cb0d48`.

## Method

The deliverable is a document, so this review is almost entirely about whether
the document's claims are true. I sampled deliberately and verified by
execution rather than reading all 5407 lines. Six claims were re-run end to
end; eight enumeration/consistency claims were re-measured; the ledger's
internal bookkeeping was counted mechanically.

Five files were mutated during verification and all five were restored by
`cp` from a pristine scratchpad copy and `cmp`-verified. No `git stash`, no
`git checkout`, no `git restore`, no line-numbered `sed`. Mutations were
applied by exact-string replacement with a uniqueness assertion, never by line
number.

## Re-executed claims — all reproduced exactly

### F-15 (the neighbour-only reddening) — both halves confirmed

Re-ran `S2-MAND-BE-branding-c`: `backend/app/core/branding.py:141`,
`_STEP = 0.01 → 0.02`.

- Pristine `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`
  — **identical to the checksum the ledger row records**.
- Step-0 baseline: `116 passed` — matches the row's reused baseline `B-49`
  (`116 passed, 1 warning in 8.46s`).
- Mutated run: `108 passed, 8 failed`. The eight failing cases are **the exact
  eight the ledger names**, no more and no fewer.
- `test_primary_text_clears_aa_on_every_text_surface_over_the_lattice` — the
  case whose docstring claims to be "what alarms if `_STEP` … ever moves" —
  **stayed green**.
- Both named real alarms reddened:
  `test_the_two_zero_margin_witnesses_are_pinned_to_the_float` and
  `test_the_default_brand_derives_the_stylesheets_own_primary_text`.

Both halves of the finding hold. The class-2 classification and the remedy
(move the claim into the two witnesses' docstrings, or make the lattice case
assert the zero-margin property it says it has) are correct. This is the
strongest row in the document and it is sound.

### F-01 (`GRAPHIC_FLOOR` 3.0 → 21.0) — confirmed

`LC_ALL=C grep -n "GRAPHIC_FLOOR" backend/tests/test_project_report_branding.py`
returns exactly lines 100 and 449, as claimed, and line 449 is
`assert ratio < GRAPHIC_FLOOR` — an upper bound on the accepted-risk list, not a
floor.

Raising the constant to 21.0 — a value no colour pair can clear — left the
module at `39 passed`, exactly as the row records. The constant's comment
("the 1.4.11 floor for a meaningful graphic") does claim a guarantee the module
does not hold. Class 1 is right.

### F-06 (`--cov-fail-under=90` is pinned by nothing) — both directions confirmed

`backend/pytest.ini:4`. Mutated to 1: `tests/test_suite_hygiene.py` → `9 passed`.
Mutated to 100: `9 passed, 1 warning in 0.85s` — the row's wording verbatim.

I also read the module's own assertions. It pins `timeout` as
`assert 0 < timeout <= MAX_PER_TEST_TIMEOUT` (line 138) — a ceiling plus a
non-zero floor, not an exact pin, which is exactly how the audit describes it —
pins `timeout_method == "thread"` and pins `pytest-timeout` as a declared dev
dependency. Nothing in the module reads `--cov-fail-under`. The 90% gate could
be lowered to 1 and no test would say so. Accurate.

### BCRYPT_ROUNDS 12 → 13 (the "zero over-pins" conclusion) — confirmed

`backend/app/core/security.py:27`. Pristine checksum
`7f9ff25e27959c23eeff9fcd31b3f36c7316cecb1944c4c0d9ffa9a3685b17c9` — identical
to the ledger's. Mutated run: `1 failed, 9 passed, 1 warning`, the single
failure being the pre-existing `test_passlib_is_not_installed`. Nothing
reddened, so the ratchet genuinely ratchets and the module is not an over-pin.
The row's handling of the pre-existing failure — quoted, excluded from
evidence, never used to support a classification — follows the spec.

### F-13 (`SubscriptionPage` OVERRIDE filter) — case count exact, file count wrong

`513` is exact. `npx vitest list src/features/user-administration/__tests__`
returns 513 cases. `npx vitest run` on the same path returns
`Test Files 51 passed (51)` / `Tests 513 passed (513)`.

The **134 is not a file count.** The row's command uses
`--reporter=json`, and the JSON reports `numTotalTestSuites = 134` while
`len(testResults) = 51`. 134 is the number of `describe` blocks. See the
blocking finding below.

The finding's substance is unaffected: 513 cases across the directory stay
green with `row.source !== "OVERRIDE"` dropped, so class 1 (not class 2) is
right.

## Re-measured enumerations — all reproduced exactly

| claim in the document | my measurement | verdict |
|---|---|---|
| S1 backend candidate set 62 lines | 62 | match |
| S1 frontend candidate set 50 lines | 50 | match |
| S2 backend `N` = 287 | 287 | match |
| S2 frontend `N` = 315 | 315 | match |
| S3 backend `N` = 577 | 577 | match |
| S3 frontend `N` = 551 | 551 | match |
| S4 raw `N` = 269 | 269 | match |
| anonymous numeric assertions 1674 / 454 | 1674 / 454 | match |
| whole frontend suite 188 files / 2503 cases | 188 / 2503 | match |

Every enumeration command in the census is copy-pasteable and reproduces its
printed denominator. The document correctly flags its own deltas against the
spec's 2026-10-01 figures (backend S1 60 → 62; frontend 2496 → 2503 cases) and
attributes the latter to a day of other tasks' work, which is the right form:
the measurement, not the spec's prose, is what it reports.

## Dependency-set claim — independently corroborated

`cd backend && uv pip freeze | shasum -a 256` right now gives
`cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75` — byte-identical
to the document's `freeze.before2`, `freeze.after`, and all 84 per-baseline-run
fingerprints. 46 packages. `sqlmodel==0.0.47`, `passlib==1.7.4`, `pytest==9.1.1`.

This is strong corroboration of a claim that would otherwise rest entirely on
the agent's own report, and it also means none of my own `uv run` invocations
moved the venv.

## Ledger internal consistency

Counted mechanically:

- `183` `####` ledger rows — matches the claimed 183 mutations.
- By prefix: S1-BE 39, S1-CFG 4, S1-FE 42, S2-BE 16, S2-MAND-BE 9, S2-FE 15,
  S2-MAND-FE 3, S3-BE 22, S3-FE 20, S4-FE 13. Sum = 183.
- Against the budgets: S1 backend 19 subset members × 2 directions + 1
  BCRYPT_ROUNDS production probe + 4 config = 43; S1 frontend 21 × 2 = 42;
  S2 25 backend / 18 frontend (floor 12 each); S3 22 / 20 (floor 20 each);
  S4 13 rows = 10 valid + 3 invalidated, so the floor of 10 is met by valid
  rows and **not** padded with the invalid ones. All budgets met, all arithmetic
  checks out.
- `84` distinct baseline-run ids `B-01`…`B-84` — matches the claimed 84.
- `84` rows say "own run, same command on the unmutated file"; `99` rows say
  "reused run". 84 + 99 = 183 exactly.
- `99` distinct interim freeze captures, each named exactly once, one per
  reusing row. The spec's reuse bookkeeping is discharged 99/99.
- All 7 S2 mandatory module paths appear by path.
- `Aborted mutations`: none, consistent with 183 matching checksum pairs.
- `Not examined — uncommitted work present`: none.
- `Not examined — already failing pre-mutation`: the `passlib` case and
  `test_migrations_postgres.py`'s 38 skipped cases, both with quoted summary
  lines and both routed to follow-ups.

## The three things flagged beyond the spec

### 1. The bare derived-config load — sound, and usable as evidence for APRAS-123

The account is sound and the methodology is better than the spec required. The
decisive detail is that the scratchpad is shared across sessions and **already
contained** a `node_modules` symlink and a `{"type":"module"}` `package.json`
dated 2026-10-01 17:02 from an earlier session, and the agent moved both to
`<scratchpad>/preexisting/` **before** attempting the bare load. Without that
move the "bare" attempt would not have been bare, and the agent would have
reproduced the contrary result by accident.

That is exactly the mechanism that explains the APRAS-123 dispute: a reviewer
who built the config in a scratchpad that already held leftover artefacts would
observe a successful bare load and attribute it to the config, not to the
leftovers. The document records both errors verbatim
(`[UNRESOLVED_IMPORT] Could not resolve 'vitest/config'`, then
`TypeError: (0 , …@tailwindcss/vite…default) is not a function`), each paired
with the remedy it forced, and states the order. It creates no counterfactual.

Judgement: **sound and clearly recorded.** One improvement would make it more
directly usable by the sibling task — the section records the preexisting
artefacts as a fact about this run but never says in so many words that they
are the likely explanation of the earlier contrary observation. A single
sentence pointing at APRAS-123 would turn a correct observation into citable
evidence. Suggestion S-04.

### 2. Re-basing on `freeze.before2` after `uv run` re-synced — the right call

`uv run` moved `sqlmodel 0.0.38 → 0.0.47` to the lockfile pin on the session's
first `uv run pytest`. Re-basing rather than aborting was right, for three
reasons the document gets onto the page:

- The change happened **before the first mutation**, so no ledger row was ever
  measured against the old set. There was no stale row to mark stale. Aborting
  would have discarded nothing and bought nothing.
- `uv run` is the invocation the spec itself mandates in every ledger row. The
  audit did not choose it, and it cannot comply with the spec's command shape
  without it. Aborting would have made the task unexecutable rather than safe.
- The spec's own detection mechanism — not an agent noticing — is what caught
  it, which is the behaviour the mechanism was specified for. The audit then
  took a stabilised capture and every one of the 84 fingerprints matches it.

This is also not a violation of the no-repair rule: `uv run`'s implicit sync is
not `uv sync`, and the document says plainly that no `uv sync`,
`uv pip install/uninstall`, `npm install` or `npm ci` was run.

Can a later reader tell which measurements predate the resync? **Yes, and
unambiguously** — because the answer is "none". The `Environment` section
quotes the `diff freeze.before → freeze.chk1` showing the single line, states
the change preceded the first mutation, names `freeze.before2` as the capture
every row is measured against, and the `Dependency-set snapshot` section then
quotes `freeze.before2` in full and reports all 84 fingerprints equal to it. A
reader can place every measurement after the resync without inference.

One residual: the reuse rows say the interim capture was "compared against
`freeze.before`" — the pre-resync capture — where the stabilised baseline is
`freeze.before2`. If those comparisons really were against `freeze.before`,
each one should have shown the `sqlmodel` line and none did, so the comparisons
were presumably against `freeze.before2` and the 99 rows carry the wrong
filename. Suggestion S-03.

### 3. Keeping the three invalidated S4 rows — right decision, under-labelled

Keeping them is right, and the agent's reasoning is the correct reasoning: a
row that collected nothing looks, in a summary, exactly like a row whose
mutation nothing caught. Deleting them would have hidden the event and left the
budget looking cleanly met. Keeping them, with `-04r`/`-08r`/`-10r` beside
them, is the honest record, and the budget is met by the valid rows alone.

Is the distinction unmissable? **No — and this is the weakest part of the
document's presentation.** The information is in three places, but not in the
one place that matters:

- the S4 census paragraph says the three were invalidated and re-run;
- each `r` row's **Mutation** field explains the first attempt's failure;
- `EK-15` names them.

But the body of `S4-FE-04` itself (lines 4184-4202) carries **no invalidation
marker**. Its `Reddened vs that baseline` field reads `none` and its
`Was it among the reddened?` field reads
`no — expected: the specifier is replaced by vi.mock, so the real module is
never reached` — which is a substantive adjudication, in the same shape as
every legitimate non-reddening row. The only in-row trace is
`0 tests: 0 passed, 0 failed (files 1)`; exit 1 in the step-3 field. A reader
who reaches the row by grep, or who skims the ledger, sees a reasoned "no"
where no measurement exists. That depends on noticing both the `0 tests` and
the `r` suffix elsewhere.

The fix is one phrase in each of the three row bodies. Suggestion S-01 — and I
have made it a suggestion rather than a blocking finding only because the
agent did disclose the invalidation in three other places and did not let the
rows carry the budget.

## ER7 / ER8 — the zero, and whether the positive control earns belief

The parity gate is sound and uses real file counts from `vitest list`, not the
JSON suite field: I measured 188 files / 2503 cases from plain `npx vitest list`
and the document reports 188 / 2503 on both sides with a match verdict and
byte-identical sorted file lists. The +7 case delta against the spec's 2496 is
explained and, as the document says, is the same on both sides, which is what
the gate asks.

The shipped-config answer is correct and precisely stated: "fails the run but
passes the case" — `Tests 2 passed` plus `Errors 2 errors`, exit 1 on both
`npm run test --` and `npx vitest run`. Both invocations and both exit codes are
recorded, and the probe's removal is recorded as verified absence rather than a
`cmp` against a copy that cannot exist. I confirmed
`frontend/src/test/__audit_probe__/` does not exist and
`git status --porcelain -- frontend/src/test/` is empty.

The honoured-config proof is real: the appended recorder was made to throw, the
run reported the error with its source line
(`<scratchpad>/audit-recorder.setup.ts:41:7`), and the throw was then removed
and `cmp`-verified.

**Is the positive control sufficient to believe the zero?** Largely yes. The
control is the right shape — it tests the instrument's two failure modes that
matter, that it writes at all and that it attributes to the correct case, and
it did both, producing two lines each naming the right case and the right
leaked message. Combined with the honoured-config proof (the setup file is
loaded) and the parity gate (the same 188/2503 are collected), the chain from
"a leak happened" to "a line appears in `leaks.jsonl`" is demonstrated
end to end.

One gap keeps this from being airtight, and it is worth a sentence in the
document rather than more work: the control ran the probe **alone**, not inside
the full 188-file run. Vitest's `setupFiles` execute per test file in separate
environments, so the inference carries, but the control does not strictly
exclude a full-run-only suppression — for example a worker whose writes race on
the single append path, which would be invisible precisely when many files leak
at once. Running the probe as the 189th file of an otherwise full instrumented
run would have closed it. Suggestion S-05. I do not treat the zero as
unsupported: it is the best-evidenced zero I have seen in this project's
audits.

## Classification and the deletion logic

All 16 findings carry exactly one class from the closed list of five — F-10 and
F-15 are class 2, the remaining fourteen class 1. No finding uses a class
outside the list, and none rests on slowness, verbosity or age; the document
states that those are never grounds (line 4462).

**Zero deletions proposed is consistent with the findings' own classes.**
Classes 1–4 are the only grounds on which a deletion *may* be offered; they do
not oblige one. Every finding here is an under-assertion — the test claims more
than it asserts — whose remedy is to add or repair the assertion. The two
class-2 findings are the ones that would normally be deletion candidates, and
the document's reasoning for keeping them is correct in both cases: the cases
concerned also hold assertions that are load-bearing, proved by the neighbours
that *did* redden under the same mutation. F-15 is precisely that situation —
the lattice case's other assertions are real; what is misplaced is the
docstring's claim about which test is the alarm. The preamble also draws the
right consequence: because nothing is proposed for deletion, there is no
sole-cover coverage analysis to report.

`Over-pins` lists every member of the S1 threshold subset (19 backend, 21
frontend, 2 config) with a safe-direction verdict each, covers
`test_bcrypt_cost.py` by name with the `BCRYPT_ROUNDS` 13 evidence, and does
not re-describe that module's source anchor or `>= PRODUCTION_FLOOR` ratchet as
defects.

## Tree safety

I mutated and restored five files. All five are byte-identical to their
pristine state, verified by `cmp` plus a `shasum -a 256` pair:

| file | checksum after restore | `cmp` |
|---|---|---|
| `backend/app/core/branding.py` | `d18dbf5c863933cd…` | clean |
| `backend/tests/test_project_report_branding.py` | `6ed8af6f0040578c…` | clean |
| `backend/pytest.ini` | `9a07d9cded340f66…` | clean |
| `backend/app/core/security.py` | `7f9ff25e27959c23…` | clean |

(`backend/pytest.ini` was mutated twice, to 1 and to 100, and restored once from
the single pristine copy.)

Final state:

```
$ git status --porcelain --untracked-files=all -- backend/ frontend/
?? backend/scripts/sync_obras_from_drive.py

$ git diff --cached --name-only
docs/audits/APRAS-111-test-suite-audit.md
```

No production or test file is changed. The index holds exactly the one path it
held when I started; I staged and unstaged nothing. The deliberately
uncommitted `sync_obras_from_drive.py` was not touched.

## Blocking findings

### B-01 — `(files N)` is not a file count, in ~187 ledger fields and in two findings

`docs/audits/APRAS-111-test-suite-audit.md:3077`, `:3078`, `:3080`, `:4645`,
`:5332`, and 187 occurrences of the `(files N)` pattern across the frontend
rows.

Every frontend row's baseline and mutated-run field reports
`N tests: N passed, 0 failed (files M)`. The rows' command is
`npx vitest run --reporter=json`, and `M` is the JSON's `numTotalTestSuites` —
the number of `describe` blocks — not the number of files. Measured:

```
$ npx vitest run --reporter=json src/features/user-administration/__tests__
numTotalTests        = 513
numTotalTestSuites   = 134    <- reported as "files"
len(testResults)     = 51     <- the actual file count

$ npx vitest run src/features/user-administration/__tests__
 Test Files  51 passed (51)
      Tests  513 passed (513)
```

and on a single-spec row (`S4-FE-04`'s baseline `B-80`, recorded as
`4 tests: 4 passed, 0 failed (files 2)`):

```
numTotalTests = 4   numTotalTestSuites = 2   actual files = 1
```

Two consequences, and the second is why this blocks:

1. F-13's prose states "513 cases across 134 files" (line 4645) and FU-10
   repeats "513 cases across 134 files currently miss it" (line 5332). The real
   figure is 51 files. A quantity presented as a measurement is wrong by 2.6x,
   in a finding's evidence, in the document that is to be the reference for
   sixteen follow-up tasks.
2. It breaks the re-executability the spec makes the proof of this deliverable
   ("A reviewer re-running a sampled row must observe the recorded outcome").
   A reviewer re-running `S4-FE-04` sees `Test Files 1 passed (1)` against a
   ledger that says `files 2`, and cannot distinguish a mislabel from a row
   that does not reproduce. I hit this myself on F-13 and had to reverse-engineer
   the JSON to tell which it was.

The case counts are correct everywhere I checked, and no finding's verdict,
class or reddening judgement depends on the file figure — which is why this is
a labelling defect and not a measurement failure. Fix: relabel to `suites`
(or report `len(testResults)` as `files`), and correct the two prose figures at
lines 4645 and 5332 to 51.

## Suggestions

- **S-01** — Give each of the three invalidated S4 rows an in-row marker.
  `docs/audits/APRAS-111-test-suite-audit.md:4184` (`S4-FE-04`), and the
  corresponding `S4-FE-08` and `S4-FE-10` row bodies. Add
  `**INVALIDATED — measured nothing (0 tests collected, exit 1); see -04r**` to
  the row, and replace the reasoned `no — expected: …` in the
  `Was it among the reddened?` field, which currently reads like a real
  adjudication. The agent's own sentence in EK-15 is the argument for this:
  a row that collected nothing looks, in a summary, exactly like a row whose
  mutation nothing caught — and that is true of these three rows read on their
  own, which is how a follow-up will read them.

- **S-02** — Two summary miscounts, both understating the work, with the
  authoritative per-row data correct in each case:
  - line 167: "**96** interim captures (`freeze.i01` … `freeze.i96`)". The
    ledger carries 99, `freeze.i01`…`freeze.i99`, each named exactly once
    against 99 reusing rows. Should read 99 / `i99`.
  - line 731: "the 68 backend mutation rows' modules". Backend rows are
    43 (S1) + 25 (S2) + 22 (S3) = 90; 68 omits S3 backend entirely. 90 + 93
    frontend = 183, which is the figure that reconciles.

- **S-03** — The 99 reuse rows state the interim capture was "compared against
  `freeze.before`", but `freeze.before` is the pre-resync capture containing
  `sqlmodel==0.0.38`. A genuine comparison against it would have shown the
  `sqlmodel` line in all 99 rows, and none did, so the comparisons were against
  `freeze.before2` and the filename in the rows is wrong. Worth correcting
  because the whole point of the capture is to name which set was compared.

- **S-04** — Add one sentence to "The bare load: observed, not assumed" naming
  APRAS-123 and stating that the preexisting `node_modules` symlink and
  `{"type":"module"}` `package.json` dated 2026-10-01 17:02 are the plausible
  explanation of the earlier round's contrary observation. The observation is
  already recorded correctly; this turns it into evidence the sibling task can
  cite without re-deriving the inference.

- **S-05** — Record the one limit of the ER8 positive control: the probe was run
  alone, not as an extra file inside the full instrumented run, so the control
  does not strictly exclude a full-run-only suppression of the recorder (a
  write race on the single append path being the realistic one). `setupFiles`
  run per file, so the inference carries; a sentence stating the limit is
  cheaper than re-running and keeps the zero honest about its own support.

- **S-06** — `frontend/vitest.config.ts`'s `test.coverage.thresholds` is the one
  S1 threshold-subset member with no mutation behind it, excluded because
  expected result 14 forbids editing that file. The document discloses this
  twice (lines 338-340, 5376) and routes it to FU-02 without claiming a
  finding, which is the correct handling of a spec that asks for exhaustive
  bidirectional mutation of config thresholds while also forbidding edits to
  that file. Worth noting that the prohibition was written for the ER8
  instrumented run, and the ordinary protocol — `cp` aside, mutate, run,
  `cp` back, `cmp` — would have applied to it as safely as to `pytest.ini`.
  A future spec should resolve the conflict rather than leave the auditor to.

## What is strong here

Recorded so the revision does not disturb it. The mutation protocol is executed
with real discipline: 183 rows, 84 baselines, every checksum pair matching, two
checksums I recomputed matching the ledger digit for digit, nine enumeration
commands reproducing their printed denominators exactly, and a dependency
fingerprint that matches on a different session hours later. Every claim I chose
to re-run reproduced — including the two that are the whole value of their rows,
F-15's neighbour-only reddening with both halves intact and F-01's 21.0 floor.
The findings are all mutation-backed, the classification is disciplined, and the
decision to propose zero deletions is reasoned rather than timid. The three
disclosures beyond the spec are all judged correctly: the invalidated rows were
kept, the resync was re-based rather than papered over, and the bare config load
was made genuinely bare before being measured.

The blocking finding is one systematic mislabel with a mechanical fix. Nothing
in the document's conclusions is wrong.
