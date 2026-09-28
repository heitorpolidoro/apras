# APRAS-108 — Cut bcrypt cost in tests without weakening it in production

## Scope

The backend suite spends roughly 60% of its wall clock hashing passwords at
bcrypt's default cost. This task lowers the cost **for the test process only**
and makes lowering it in production impossible to ship by accident.

Measured, do not re-measure:

- `backend/app/core/security.py:12` builds `CryptContext(schemes=["bcrypt"],
  deprecated="auto")` with no cost parameter anywhere in the codebase, so
  passlib applies its default `rounds=12`: **253.3 ms per hash**.
- The suite performs **1770** hash calls.
- A full run with `rounds=4` went from **771.07 s to 311.18 s**: 3795 passed,
  coverage identical at **94.13%**.
- Two independent routes agree within 2.6%: 1770 × 253.3 ms predicts 448.3 s of
  hashing, 459.9 s was observed.

Recorded so nobody re-opens them — measured and rejected as second-order:
coverage instrumentation costs 135.8 s (+21.4%) and is the price of the
`--cov-fail-under=90` gate, not waste; there is no hot spot to attack (the 40
slowest phases are 8.8% of total, while fixture setup alone is 58.1%); and
excluding `tests/` from coverage saves nothing, because `--cov=app` already
does not measure it.

Not covered: no change to authentication behaviour, to any endpoint, to any
model, or to how passwords are hashed and verified in production — the same
`app.core.security` functions run in both configurations. Reducing the *number*
of hash calls (session-scoped user fixtures, a shared pre-computed hash) is a
separate, larger task and is out of scope. Frontend, CI workflow files and
`pytest.ini` are untouched. `app/seed.py` and `app/seed_demo.py` call
`get_password_hash` at runtime and need **no change**: whenever the suite
exercises either, they go through the same `pwd_context` the `conftest.py`
override mutates, and so are covered by it automatically; outside the suite they
use the production floor, which is the intended behaviour.

## Approach

### D1 — Where the cost factor lives: a module constant in `security.py`, and nowhere else

Three placements were available, and the choice follows directly from the
danger this task exists to contain. A production bcrypt at `rounds=4` is a
severe, silent defect: every hash still verifies, no test fails, nothing logs.

- **A `Settings` field** (`BCRYPT_ROUNDS: int = 12`). Rejected. `config.py:109`
  is `SettingsConfigDict(env_file=".env", case_sensitive=True)`, and the
  model's resolved `extra` is **`forbid`** (verified with
  `Settings.model_config["extra"]`; an earlier draft of this paragraph said
  `ignore`, which was wrong about the mechanism though not about the
  conclusion). Either way an undeclared `BCRYPT_ROUNDS` never reaches the
  code today: **declaring the field is
  precisely what creates the deploy-time override**. From that moment a
  `BCRYPT_ROUNDS=4` row in the Vercel project's environment, or a line in
  `backend/.env.production` — which **exists on disk**, so this is a concrete
  route and not a hypothetical one — silently weakens production with no code
  change, no diff and no review. The
  field would buy nothing in return — the test process does not need an
  environment variable to configure itself, it has `conftest.py`.
- **Reading `os.environ` in `security.py`.** Rejected for the same reason, and
  it additionally bypasses the one place this project centralises
  configuration.
- **Chosen: a literal module constant plus a test-only override applied from
  `tests/conftest.py`.** Production has *no knob at all*. The only way to lower
  the production cost is to edit `app/core/security.py`, which is a reviewable
  diff, and §D2's tests fail on it.

Concretely:

- `app/core/security.py` gains a documented module constant — name it
  `BCRYPT_ROUNDS`, value `12`, and pass it as `bcrypt__rounds=BCRYPT_ROUNDS`
  when constructing `pwd_context`. Making 12 explicit changes nothing
  operationally (it is already passlib's default) and gives the floor a single
  addressable name.
- The constant is documented with `#` comment lines immediately above it —
  **not** a docstring or a `#:` -style string literal — stating that it is the
  production floor, that it is deliberately not configurable by environment,
  and that the test suite lowers the *context* rather than this constant. That
  comment is free to spell `rounds`, `BCRYPT_ROUNDS` and `bcrypt__rounds` as
  many times as it needs to: §D2's source check strips comments before counting
  (see the rule stated there), so the mandated explanation can never trip it.
  This is the same problem `tests/test_lint_hygiene.py` solves by excluding
  itself from its own scan; here the exclusion is comment-stripping, because
  the file under scan is `security.py`, not the test.
- `tests/conftest.py` lowers the cost at import time, before any test module is
  collected, with passlib's own public API on the existing object:
  `pwd_context.update(bcrypt__rounds=4)`. It must **mutate** the context, not
  rebind `security.pwd_context`, so that any current or future
  `from app.core.security import pwd_context` alias sees the same setting. It
  must be a module-level statement, not a fixture: `4` has to be in force for
  hashes computed during collection and in session-scoped fixtures. A comment
  gives the reason and the measured numbers.
- `verify_password` / `get_password_hash` are not modified; they read the
  module global and therefore pick the mutation up unchanged.

Verified against passlib 1.7.4 / bcrypt 4.0.1, the pinned versions:
`CryptContext.update(bcrypt__rounds=4)` yields `to_dict()["bcrypt__rounds"] ==
4`, and a hash then takes **1.1 ms** instead of 253.3 ms.

### D2 — The production floor, and what "reach production" means for a test

The test process is by definition not production, so "assert production uses
12" has to be decomposed into claims a test *can* decide. There are exactly two
routes by which a value below 12 could reach production, and each gets a test:

1. **By deploy-time configuration** (an environment variable or `.env` entry).
   A test asserts this route does not exist, by spawning a subprocess whose
   environment sets every plausible name — at minimum `BCRYPT_ROUNDS`,
   `BCRYPT_TEST_ROUNDS`, `PASSLIB_BCRYPT_ROUNDS` — to `4`, importing
   `app.core.security` fresh in that subprocess (so `conftest.py` is not
   loaded), and printing `pwd_context.to_dict()["bcrypt__rounds"]`. The
   assertion is `12`. This is the strongest statement available from inside a
   test process, and it is a real one: it proves the deploy-time route is
   inert, not merely that a default is 12.
2. **By a code change.** A test asserts `security.BCRYPT_ROUNDS >= 12`. The
   `>=` is deliberate and is the whole rule: the floor test is a **ratchet**,
   and `12` is only today's value. A future task that raises the production cost
   to 13 or 14 satisfies this spec unchanged and must not be read as violating
   it; only a value *below* 12 is a defect. (Expected Result 1 pins the literal
   `12` because that is what this task lands; the test does not.)

   So the constant cannot become decorative while the context is built from
   something else, a **static source check on `app/core/security.py`**, stated
   exactly so the implementation and QA cannot diverge:

   - Read the file's source and **strip comments first**: drop, from every
     line, the `#` and everything after it. The module has no docstring
     mentioning these tokens and §D1 forbids documenting the constant as one,
     so comment-stripping is the whole normalisation — no AST walk needed.
   - On the stripped text, count **occurrences, not lines**, and
     **case-sensitively**:
     - lowercase `rounds` occurs **exactly once** — the `bcrypt__rounds=`
       keyword argument. (`BCRYPT_ROUNDS` does not match: the check is
       case-sensitive, so its uppercase `ROUNDS` is invisible to this count.)
     - `BCRYPT_ROUNDS` occurs **exactly twice** — the assignment's left-hand
       side and the keyword argument's value.
   - The stripped text contains neither `os.environ` nor `getenv`.

   Two companion static checks:

   - `app/core/config.py` declares no field whose name contains `BCRYPT` or
     `ROUNDS`, which keeps route 1 closed against a future edit rather than only
     today.
   - Neither `needs_update` nor `verify_and_update` appears **anywhere under
     `app/`** — a ratchet in the same shape `tests/test_lint_hygiene.py` uses
     for the clock, scanning every `*.py` under `app/`. §D3 leans on the absence
     of these two names, and prose cannot enforce it. The stake is concrete:
     `needs_update` on a cost-12 hash returns `True` under a cost-4 context
     (measured), so one future caller plus one production misconfiguration would
     silently *downgrade* real users' stored hashes at login. It is inert today
     only because no caller exists; this check is what keeps it that way. The
     scan root is `app/`, so the test module may name both tokens freely and
     needs no self-exclusion.

   `tests/test_lint_hygiene.py` is the precedent for enforcing a source-level
   rule from the suite.

What remains uncovered, stated plainly: nothing prevents someone editing
`security.py` to set the constant to 4 *and* deleting these tests in the same
commit. That is not a gap a test can close, and it is acceptable — it is an
unmistakable diff, which is exactly the property the design was chosen for,
whereas the `Settings`-field design would have allowed the same outcome with no
diff at all.

### D3 — Existing hashes keep verifying

bcrypt encodes its cost in the modular-crypt prefix, and passlib's `verify`
dispatches on the hash's own parameters, not on the context's. Confirmed
empirically against the pinned versions: a `$2b$12$…` hash verifies `True`
under a context configured with `bcrypt__rounds=4`, and a wrong password
against the same hash returns `False`. Nothing in `app/` calls `needs_update`
or `verify_and_update` (checked), so no code path can decide a production hash
is stale and rewrite it — and §D2's third static check now *enforces* that
absence instead of leaving it to prose, because `needs_update` on a cost-12 hash
does return `True` under a cost-4 context. A regression test pins this with a
checked-in
12-round hash literal, so production hashes are provably not invalidated.

A usable fixture value — generated for this spec at rounds 12, password
`prod-era-password`:

```
$2b$12$N7D1OMxeQ7i0SlTfVHsOBeqdzlUkVcv5iuFRBxtccYZ23TS2Ui5cq
```

The reverse direction is tested too: `get_password_hash("…")` produced inside
the suite must start with `$2b$04$`. Without it, a silent revert to cost 12
would cost 460 s per run and no test would notice.

### Files touched

- `backend/app/core/security.py` — add the `BCRYPT_ROUNDS = 12` constant with
  its comment; pass `bcrypt__rounds=BCRYPT_ROUNDS` to the existing
  `CryptContext`. No function body changes.
- `backend/tests/conftest.py` — one module-level `pwd_context.update(
  bcrypt__rounds=4)` with a comment carrying the measured figures. **Append
  only**: this file sits beside APRAS-105's staged work; do not revert or
  restage anything in the tree, and stage only explicit paths.
- `backend/tests/test_bcrypt_cost.py` — new. The §D2 and §D3 tests.
- `docs/tasks/APRAS-108-spec.md` — this file.

### Allowed paths (complete)

```
backend/app/core/security.py
backend/tests/conftest.py
backend/tests/test_bcrypt_cost.py
docs/tasks/APRAS-108-spec.md
```

Any other path — `backend/app/core/config.py`, `pytest.ini`, CI workflows, the
27 paths APRAS-105 has staged, `docs/suggestions-log.md`, the untracked
`docs/tasks/APRAS-82-mock.html`, `APRAS-91-spec.md`, `APRAS-93-spec.md`,
`APRAS-106-*` — is off limits: do not edit, stage or revert it. Never
`git stash` in this repository, and never `git add -A`, `git add .`,
`git add docs/` or `git add backend/`; stage the four paths above explicitly.

### Test criteria

- The new tests in `test_bcrypt_cost.py` pass: the subprocess env-override test,
  the constant-and-source floor test (`>= 12` plus the comment-stripped token
  counts), the `config.py` no-such-field test, the
  no-`needs_update`/`verify_and_update`-under-`app/` test, the 12-round-hash
  verification test, and the `$2b$04$` test.
- The whole existing suite passes unchanged, authentication end-to-end tests
  (register → login, password reset, invitation acceptance) included, with no
  test file other than `conftest.py` and the new module modified.
- `--cov-fail-under=90` still satisfied; coverage does not regress from 94.13%.
- Both timings measured the same way (see the expected result below).

## Expected Results

- [ ] `backend/app/core/security.py` defines a module constant `BCRYPT_ROUNDS =
      12` and passes it to the `CryptContext` as `bcrypt__rounds=BCRYPT_ROUNDS`.
      In that file's source **with comments stripped** (every `#` and everything
      after it on the line removed), counting **occurrences case-sensitively**:
      lowercase `rounds` occurs exactly once, `BCRYPT_ROUNDS` occurs exactly
      twice, and neither `os.environ` nor `getenv` occurs at all. The `#`
      comment documenting the constant **may** name `rounds`, `BCRYPT_ROUNDS` or
      `bcrypt__rounds` as often as it likes — comments are stripped before
      counting and are never counted.
- [ ] Running `cd backend && uv run python -c "from app.core.security import
      pwd_context; print(pwd_context.to_dict()['bcrypt__rounds'])"` in a shell
      where `BCRYPT_ROUNDS=4`, `BCRYPT_TEST_ROUNDS=4` and
      `PASSLIB_BCRYPT_ROUNDS=4` are exported prints `12`;
      `backend/app/core/config.py` declares no settings field whose name
      contains `BCRYPT` or `ROUNDS`; and neither `needs_update` nor
      `verify_and_update` appears in any `*.py` file under `backend/app/`. Tests
      in `backend/tests/test_bcrypt_cost.py` assert all three and fail if any
      breaks.
- [ ] A test in `backend/tests/test_bcrypt_cost.py` asserts that the checked-in
      cost-12 hash `$2b$12$N7D1OMxeQ7i0SlTfVHsOBeqdzlUkVcv5iuFRBxtccYZ23TS2Ui5cq`
      still returns `True` from `app.core.security.verify_password` for password
      `prod-era-password` and `False` for a wrong password, while a hash created
      inside the suite by `app.core.security.get_password_hash` starts with
      `$2b$04$`.
- [ ] `cd backend && uv run pytest` passes with no failures and no errors, at
      least 3795 tests passed, and the `--cov-fail-under=90` gate green with
      total coverage ≥ 94.13% — with no test file changed other than
      `backend/tests/conftest.py` and the new `backend/tests/test_bcrypt_cost.py`.
- [ ] The final report states two wall-clock timings for `cd backend && uv run
      pytest` (full suite, default `addopts`, no `--lf`/`-k`/`-x`, coverage on),
      both taken on the same machine back-to-back in the same session, differing
      only in the one `conftest.py` line: "before" with the
      `pwd_context.update(bcrypt__rounds=4)` line commented out, "after" as
      committed. Each figure must name the command and be a single full run — no
      averaged, warm/cold or partial-run numbers. The report must additionally
      state **which of the two runs was executed first**, and must assert that
      **no other pytest run or comparable CPU load shared the machine during
      either run** — bcrypt is CPU-bound and other agents run this same suite on
      this machine, so a contended "before" against an idle "after" (or the
      reverse) would satisfy every other property here while proving nothing.
      The "after" figure must be at least 40% lower than the "before" figure;
      the measured expectation is **~60%** (771.07 s → 311.18 s), so a result
      near the 40% bar is a signal to investigate contention or a missed
      override, not a clean pass. The passed-test count and coverage percentage
      of both runs must be reported. The coverage percentage must be
      identical. The passed-test count must be identical **except for the
      single guard test that asserts a suite-created hash starts with
      `$2b$04$`**: that test necessarily fails in the "before" run, because
      the "before" run is defined as the one with the override removed, and
      that guard exists precisely to detect a missing override. So the
      "before" run is expected to report exactly one failure, that one, and
      the same total collected count as the "after" run. A "before" run with
      zero failures, or with more than that one, is a signal that the two
      runs were not the pair they claim to be.

## Out of Scope

- Reducing the number of hash calls (session-scoped or module-scoped user
  fixtures, one shared pre-computed hash for the whole suite).
- Coverage instrumentation cost (measured at 135.8 s / +21.4%; it is the price
  of the existing gate).
- Any parallelisation of the suite (`pytest-xdist`), CI workflow edits, or
  `pytest.ini` changes.
- Rotating or re-hashing any existing production password.
