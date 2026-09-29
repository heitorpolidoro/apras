# APRAS-116 — Clear the open Dependabot vulnerabilities in both lock files

## Scope

Raise every vulnerable dependency in `backend/` and `frontend/` to a patched
version inside its current major, regenerate both lock files so the manifest and
the lock agree, and add a `.github/dependabot.yml` so the two ecosystems get
scheduled update PRs instead of accumulating alerts.

Covered: `backend/pyproject.toml`, `backend/uv.lock`, `backend/requirements.txt`,
`frontend/package.json`, `frontend/package-lock.json`, `.github/dependabot.yml`.

Not covered: no application source file changes, no test changes, no CI workflow
changes, no major-version upgrades, and no `overrides` block (§4 shows none is
needed). The pre-existing `~375` `npm run lint` errors are not this task's to
fix.

## Findings from the investigation

These four findings are the deliverable as much as the diff is. Three of them
correct or qualify a premise on the card; none of them blocks implementation.

### F1 — Dependabot *is* opening PRs; the alerts accumulated because the PRs were not merged

The card says "nothing opens update PRs". That is not what the repository shows.
`dependabot_security_updates` is **enabled** in
`gh api repos/heitorpolidoro/apras` → `security_and_analysis`, and
`gh pr list --author app/dependabot --state all` returns six PRs, two of them
**open right now** and both inside this task's scope:

- **#29** `chore(deps-dev): bump vite from 8.0.10 to 8.0.16 in /frontend` —
  touches `frontend/package.json` + `frontend/package-lock.json`.
- **#30** `chore(deps): bump python-multipart from 0.0.27 to 0.0.31 in /backend`
  — touches `backend/pyproject.toml` + `backend/requirements.txt` +
  `backend/uv.lock`.

`.github/dependabot.yml` has never existed
(`git log --all --diff-filter=ADM -- .github/dependabot.yml` is empty); security
updates need no config file, which is why those PRs exist anyway. So the config
this task adds buys **scheduled version updates, grouping and a PR ceiling** —
not the difference between "PRs" and "no PRs". Expected result 7 is satisfied
either way; its stated rationale is what changes.

Consequence for the implementer: do not merge or rebase #29/#30 into this work.
Once this task lands on `master`, Dependabot supersedes and auto-closes a PR
whose dependency already meets the target; if either is still open a day after
merge, close it manually with a comment naming APRAS-116.

### F2 — `backend/requirements.txt` is stale beyond the security bumps

It is a generated export (`uv export --format requirements-txt --no-hashes -o
requirements.txt`, per its own header) and it predates two dependencies that are
in `pyproject.toml` and `uv.lock` today: `pillow` and `qrcode` (and `qrcode`'s
own tree). Regenerating it — which this task must do anyway — will therefore add
rows unrelated to any advisory. That widening is expected and correct, not scope
creep; the reviewer should not read it as one. Nothing consumes
`requirements.txt` (no workflow, no Dockerfile, no README reference — CI runs
`uv sync --all-groups`), so its staleness has had no runtime effect; it exists as
the artifact Dependabot parses, which is exactly why it is alerting separately.

### F3 — `pydantic-settings` 2.14.0 → 2.14.2 does not touch `extra` resolution or `model_fields`

Verified against the upstream release notes for both intervening releases:

- **2.14.1** — dependency bumps plus one fix, "field named `cls` conflicting with
  classmethod parameter".
- **2.14.2** — a security patch release, one functional commit: prevent
  `NestedSecretsSettingsSource` from following symlinks outside `secrets_dir`
  (GHSA-4xgf-cpjx-pc3j, affected `>=2.12.0, <2.14.2`).

Neither release touches `SettingsConfigDict`'s default `extra`, the resolution of
`extra` from `model_config`, or `model_fields` construction. `Settings`
(`backend/app/core/config.py:109`) declares
`SettingsConfigDict(env_file=".env", case_sensitive=True)` and uses no
`secrets_dir` and no `NestedSecretsSettingsSource`, so the advisory is not even
reachable in this codebase — the bump is a clean floor raise. Both APRAS-108
assertions therefore stand unchanged, and `backend/tests/test_bcrypt_cost.py`
(including `test_config_declares_no_cost_field`, which reads
`Settings.model_fields`) must pass untouched. If it does not, that is a finding
to report, not a test to relax.

### F4 — a sixteenth vulnerable package that Dependabot auto-dismissed

`npm audit` in `frontend/` reports **15 vulnerable packages** (2 low, 3
moderate, 10 high) — **baseline measured on 2026-09-29 at base commit
`06333cf`**; record both, because the advisory registry moves and a reader in two
weeks will not reproduce those counts. One of them — `nanoid` (`<=3.3.17`, high) — is absent
from the 57 open alerts because its two alerts are `auto_dismissed`. It clears
for free: `postcss` 8.5.28 requires `nanoid: ^3.3.18`, so updating `postcss`
lifts it to 3.3.19. It matters only because the pre-merge gate below is
`npm audit`, and `nanoid` must be zero there too.

Also note `npm audit`'s ranges are *wider* than the card's snapshot for two
packages: `brace-expansion` needs `>1.1.17` and `>5.0.8` (card said 1.1.16 /
5.0.7), `js-yaml` needs `>4.3.1`. Both remain reachable (§4). Target the audit's
ranges, not the card's numbers.

**Note on the `0 vulnerabilities` criterion.** It is deliberately absolute, and
it will therefore fail if an advisory published *after* 2026-09-29 lands on a
package in this tree. That is the intended design: a newly disclosed
vulnerability is a real failure, not a flaw in the gate. §8 says what to do when
such an advisory has no in-major fix — drop to the lowest passing in-range
version, and if none exists, stop and report that package rather than widening
scope into a major upgrade. Card result 11 ("target the LIVE advisory ranges")
is an instruction, not an outcome: it is subsumed by the `npm audit` → 0 gate
plus the explicit floors in §4, and should be read as context for them.

## Approach

### 1. Backend order of operations (`uv` owns both files)

`requirements.txt` and `uv.lock` must agree, so never hand-edit either. Raise the
floors in `pyproject.toml` first, then let `uv` produce both files:

1. `backend/pyproject.toml` — raise two direct pins: `python-multipart>=0.0.31`,
   `pydantic-settings>=2.14.2`. Leave every other pin alone, including
   `bcrypt<4.1.0` and the deliberate `ruff==0.16.5`.
2. `anyio` is **not** a direct dependency — it arrives via `httpx` and
   `starlette`, neither of which caps it. Move it with
   `uv lock --upgrade-package anyio`, in the same `uv lock` invocation as the two
   above. Do **not** add `anyio` to `pyproject.toml`: that would declare a direct
   dependency on a package no module imports. Its only guards are that `uv lock`
   resolves upward and that Dependabot watches the lock — which is precisely what
   §3 institutionalises.
3. `backend/requirements.txt` — regenerate with the exact command in its header,
   never by hand. Expect the F2 additions in the diff.
4. Prove the export happened, because a careful hand-edit and a real export
   produce indistinguishable files. Run the export a **second** time from the
   committed tree: `git diff --exit-code backend/requirements.txt` must be empty
   (exit 0). Then check the two files agree on *versions*, not merely on floors:
   `anyio`, `python-multipart` and `pydantic-settings` must each resolve to the
   **same** version string in `uv.lock` and in `requirements.txt`.

### 2. Frontend order of operations (keep the lock diff scoped)

1. `frontend/package.json` — four direct ranges: `axios` `^1.18.0`,
   `react-router-dom` `^7.18.2`, `vite` `^8.0.16`, `vitest` `^4.1.11`.
2. `npm install` to re-resolve those four and the children they pin exactly
   (`react-router`, `@vitest/mocker` — see §4).
3. Targeted `npm update` for the transitives whose parents' existing ranges
   already admit a patched version but whose lock entry is stale: `undici`,
   `brace-expansion`, `browserslist`, `baseline-browser-mapping`, `form-data`,
   `js-yaml`, `postcss`, `@babel/core`, `nanoid`, `@vitest/coverage-v8`. Name
   them; do **not** run a bare `npm update`, which would also lift every
   unrelated caret (`react`, `tailwindcss`, `eslint`, `jsdom`, …) and bury the
   security diff in a few hundred incidental lines.

   "Use a named update" is a process instruction and leaves no artefact, so the
   **checkable proxy** is the lock diff itself: no package outside the four
   directs of step 1 and the twelve transitive *lock entries* of §4 (eleven
   distinct names, `brace-expansion` appearing twice) plus `@vitest/coverage-v8`
   may change `version` in `frontend/package-lock.json`. The permitted set of
   names is therefore exactly: `axios`, `react-router-dom`, `vite`, `vitest`,
   `react-router`, `@vitest/mocker`, `@vitest/coverage-v8`, `postcss`, `nanoid`,
   `form-data`, `undici`, `browserslist`, `baseline-browser-mapping`, `js-yaml`,
   `brace-expansion`, `@babel/core`. Verify by diffing the set of changed
   `version` fields against those sixteen; `react`, `react-dom`, `tailwindcss`,
   `eslint`, `jsdom`, `typescript` and `@tanstack/react-query` in particular must
   be untouched. Any extra name in that set is a finding.
4. `@vitest/coverage-v8` stays at `^4.1.5` in `package.json` but must resolve to
   `4.1.11` in the lock, matching `vitest` exactly. A lock where the two disagree
   is a finding. It is listed in the permitted diff set above.
5. `npm ci` from the updated lock before testing — CI installs that way, so a
   lock that is not self-consistent with `package.json` fails there rather than
   locally.

### 3. `.github/dependabot.yml`

Two entries, `version: 2`:

- `package-ecosystem: "uv"`, `directory: "/backend"`. **Not `pip`**: `pip` would
  drive `requirements.txt`, the generated export, and leave `uv.lock`
  untouched — manufacturing exactly the two-files-disagree state the card warns
  about. `uv` is the right key and is already in use: the open PR #30's branch is
  `dependabot/uv/backend/uv-26f8b248e5` and it updates `pyproject.toml`,
  `uv.lock` and `requirements.txt` together.
- `package-ecosystem: "npm"`, `directory: "/frontend"`.

Both on `schedule: {interval: "weekly"}`. Weekly, not daily: one maintainer, and
the failure mode this task exists to prevent is a queue nobody reads. No `day`
key — the shape is fixed by the expected results, and a specific weekday is a
preference nothing can fail on.

The shape is exact, so it can be failed rather than merely preferred. Per
ecosystem, all four required:

- `open-pull-requests-limit: 3`;
- exactly one group with `applies-to: version-updates`, `patterns: ["*"]`,
  `update-types: ["minor", "patch"]` — one PR per ecosystem per week;
- exactly one group with `applies-to: security-updates`, `patterns: ["*"]` —
  security fixes stay batched instead of arriving one per advisory, which is how
  57 alerts became unreadable;
- majors deliberately left ungrouped, so each arrives as its own reviewable PR.

Exclude `ruff` from the backend version-update group (`exclude-patterns`):
`pyproject.toml` states that bumping it must be a deliberate one-line PR that
re-runs the lint harness (APRAS-54 §4.1), and grouping it defeats that. Do not
add an `ignore` rule for it — `ignore` would suppress its security updates too.

No `github-actions` entry: out of scope here, and its security updates already
work without config (PR #8).

### 4. Do the transitive alerts clear from the direct bumps alone? Yes — every one of them

Parents read out of `frontend/package-lock.json`; maximum in-range versions read
from the npm registry. No transitive needs an `overrides` entry, and none is
unreachable.

| alerting package | reached via | parent's range | needs | max in range |
|---|---|---|---|---|
| `react-router` | `react-router-dom` | **exact** `7.15.0` | 7.18.2 | 7.18.4 (`react-router-dom` 7.18.4 pins `react-router` 7.18.4) |
| `@vitest/mocker` | `vitest` | **exact** `4.1.5` | 4.1.11 | 4.1.11 |
| `postcss` | `vite` | `^8.5.10` | **8.5.28** (not 8.5.23 — see below) | 8.5.28 |
| `nanoid` | `postcss` | `^3.3.18` (in 8.5.28) | 3.3.18 | 3.3.19 |
| `form-data` | `axios` | `^4.0.5` | 4.0.6 | 4.0.6 |
| `undici` | `jsdom` | `^7.25.0` | 7.29.0 | 7.30.0 |
| `browserslist` | `@babel/helper-compilation-targets`, `update-browserslist-db` | `^4.24.0`, `>=4.21.0` | 4.28.7 | 4.29.2 |
| `baseline-browser-mapping` | `browserslist` | `^2.10.12` | 2.11.0 | 2.11.26 |
| `js-yaml` | `@eslint/eslintrc` | `^4.1.1` | 4.3.2 | 4.3.2 |
| `brace-expansion` (1.x) | `minimatch` 3.1.5 | `^1.1.7` | >1.1.17 | 1.1.21 |
| `brace-expansion` (5.x) | `@typescript-eslint/typescript-estree/minimatch` 10.2.5 | `^5.0.5` | >5.0.8 | 5.0.12 |
| `@babel/core` | `@vitejs/plugin-react`, `eslint-plugin-react-hooks` | `^7.24.4`, `^7.0.0` | 7.29.6 | 7.29.7 |

The `postcss` floor is **8.5.28**, not 8.5.23. `nanoid: ^3.3.18` first appears in
8.5.28, so a resolution at 8.5.23 would satisfy a `postcss` advisory clause while
leaving `nanoid` on a vulnerable 3.3.x — and `nanoid` is exactly the package the
GitHub alert list does not show (F4). 8.5.23 is a finding, not a pass.

Two of these (`react-router`, `@vitest/mocker`) are pinned exactly by a parent
and move **only** because the card's direct bumps move that parent — they are the
reason `react-router-dom` and `vitest` must be bumped in `package.json` rather
than merely re-resolved. The other ten sit under caret ranges that already admit
a patched version, so they are stale-lock artefacts and §2 step 3 lifts them.
`npm audit --json` corroborates: `fixAvailable` is `true` for all 15 packages and
`isSemVerMajor` is set on none, so `npm audit fix` without `--force` would
suffice — the explicit route above is preferred only because it keeps the diff
legible.

**Conclusion: no `overrides` block. If one appears in the diff, it is a finding.**

### 5. Does anything cross a major? No

Backend: `anyio` 4.13.0 → 4.x (latest 4.15.1); `python-multipart` 0.0.27 → 0.0.31
or 0.0.32 (patch inside `0.0`); `pydantic-settings` 2.14.0 → 2.14.2 (2.15.0 also
exists and is in-major, but the floor is 2.14.2 and `uv` will resolve upward —
either is acceptable, both are 2.x).

Frontend: every target in the §4 table is in the same major as the locked
version, checked against each package's registry metadata. The traps to watch,
because their `latest` is a major ahead, are `react-router` (latest 8.4.0),
`vite` (8.3.1 is in-major, but `undici` latest is 8.11.2), `@babel/core` (8.0.6),
`js-yaml` (5.4.2) and `brace-expansion` (5.0.12 for the entry that must stay on
1.1.x). All are constrained by their parents' caret ranges, so a correct
resolution cannot reach them — which makes a major appearing in the lock diff a
sign of a mis-run command, and a finding.

### 6. Build-time versus runtime, and what the tests would miss

`vite`, `@babel/core`, `browserslist`, `baseline-browser-mapping`, `postcss` and
`nanoid` are all toolchain, not shipped source. `vite` 8.0.10 → 8.0.16 and
`postcss` are patch-level; the real output risk is the babel/browserslist pair,
because `browserslist` decides transpilation targets and `@babel/core` performs
the JSX transform — a patch there can in principle change emitted code. No
application source changes, so `npm run build` (`tsc -b && vite build`) is the
only gate that would catch a regression; the unit tests run under `vitest`'s own
transform and would not. `undici` and `jsdom` are test-environment only.
Runtime-facing bumps are just `axios` and `react-router-dom`/`react-router`,
both patch/minor inside their major.

### 7. How the result is verified — before merge and after

Honest split, because alerts are computed per branch:

**Before merge (local, and what CI proves):** `npm audit --audit-level=low` in
`frontend/` reports **0 vulnerabilities** (baseline 15 packages, measured
2026-09-29 at base commit `06333cf`). Backend has no
audit tool in the dependency set, so the check is that `uv.lock` and
`requirements.txt` both show `anyio>=4.14.2`, `python-multipart>=0.0.31`,
`pydantic-settings>=2.14.2`, and that the suites pass.

**After merge only:** the alert count itself. Dependabot alerts are evaluated
against the **default branch** (`master`), so
`gh api repos/heitorpolidoro/apras/dependabot/alerts --paginate` will keep
reporting 57 open on a feature branch no matter how correct the fix is. Re-run it
after the merge to `master`; expect 0 open, and if any survives, record the
package and the reason. Do not treat a non-zero count before merge as a failure,
and do not chase it with further bumps. The **pre-merge gate on the branch** is
instead: `git log` shows neither #29 nor #30 merged into it, i.e. no commit whose
subject matches `bump vite from 8.0.10` or `bump python-multipart from 0.0.27`
and no `dependabot/**` merge commit. That is checkable at review time; the alert
count is not.

### 8. What to do when a bump breaks something

The general rule, covering every package and not just `pydantic-settings` (F3)
or the alert count (§7): **do not edit application source, tests or CI to make a
bump pass.** Those files are out of scope by construction, which is what forbids
"relax the failing test" as a response.

When a target version breaks `npm run build`, `npm run test:coverage` or
`pytest`:

1. Drop to the **lowest version inside the current major** that still clears the
   advisory (i.e. still satisfies the `needs` column of §4, or the backend floor
   in §1) and makes the failing check pass. The §4 `needs`/`max in range` columns
   bound that search.
2. If no such version exists — every in-range version either fails the check or
   fails the advisory — **stop and report that package** by name, with the check
   it breaks and the versions tried. Leave it unfixed and say so; a major upgrade
   to escape the corner is a separate task (see Out of Scope).

A source, test or CI file in the diff is a finding regardless of the
justification offered for it.

## Files touched

- `backend/pyproject.toml` — raise the `python-multipart` and `pydantic-settings`
  floors.
- `backend/uv.lock` — regenerated; `anyio`, `python-multipart`,
  `pydantic-settings` move.
- `backend/requirements.txt` — regenerated by `uv export`; includes the F2 rows.
- `frontend/package.json` — four direct ranges raised.
- `frontend/package-lock.json` — regenerated; the four directs plus the twelve
  entries in §4.
- `.github/dependabot.yml` — new; two ecosystems, weekly, grouped.

## Test criteria

- `cd backend && uv sync --all-groups && uv run pytest tests/` — whole suite
  green, `tests/test_bcrypt_cost.py` in particular untouched and passing.
- `cd backend && uv run ruff check . && uv run ruff format --check .` — clean.
- `cd frontend && npm ci && npm run build` — succeeds.
- `cd frontend && npm run test:coverage` — whole suite green.
- `cd frontend && npm audit --audit-level=low` — 0 vulnerabilities.
- `cd backend && uv export --format requirements-txt --no-hashes -o
  requirements.txt && git diff --exit-code requirements.txt` — exits 0, proving
  the committed file is an export; and `anyio`, `python-multipart`,
  `pydantic-settings` resolve to the same version in `uv.lock` and
  `requirements.txt`.
- The set of packages whose `version` changes in `frontend/package-lock.json` is
  a subset of the sixteen names listed in §2 step 3; `postcss` is at 8.5.28+ and
  `@vitest/coverage-v8` equals `vitest` at 4.1.11.
- `cd frontend && npm run lint` — error count no worse than the base commit's
  (~375 errors across 64 files, repo-wide and pre-existing). Capture the base
  count before the change; "zero" is not the bar.
- `.github/dependabot.yml` parses: after merge, the repository's Dependabot
  configuration reports no error for either ecosystem entry.
- `git log` on the branch shows neither PR #29 nor #30 merged into it.
- After merge to `master`: the `gh api` alert query reports 0 open, or each
  survivor is recorded with its reason. This is a post-merge follow-up and must
  not fail the task at review time.

## Expected Results

Verbatim from the task card at `.meridian/tasks/APRAS-116.json` — QA sees only
this list, so it is the contract and the spec above is the map.

- [ ] POST-MERGE FOLLOW-UP, not a review-time gate: re-running `gh api
      repos/heitorpolidoro/apras/dependabot/alerts --paginate` after this lands on
      master reports zero open alerts, or each survivor is recorded with the
      reason. Alerts are computed on the DEFAULT BRANCH, so the count stays 57
      until merge -- QA must NOT fail this task for the count being unchanged
      pre-merge. The pre-merge gate is `npm audit` (ER10) plus the lock floors.
- [ ] Backend: anyio moves from 4.13.0 to >=4.14.2 (the only CRITICAL alert),
      python-multipart from 0.0.27 to >=0.0.31, and pydantic-settings from 2.14.0
      to >=2.14.2. Both backend/requirements.txt and backend/uv.lock are updated
      together and agree -- Dependabot flags them separately and a fix to one
      alone leaves the other alerting. The agreement between the two files is
      PROVED, not asserted: re-running `uv export --format requirements-txt
      --no-hashes -o requirements.txt` leaves `git diff --exit-code
      backend/requirements.txt` empty (so it was exported, not hand-edited), and
      anyio, python-multipart and pydantic-settings resolve to the SAME version in
      both files, not merely above their floors. Order: raise the floors in
      pyproject.toml, `uv lock --upgrade-package <name>`, then export.
- [ ] Frontend: the four DIRECT dependencies move -- axios to ^1.18.0,
      react-router-dom to ^7.18.2, vite to ^8.0.16, vitest to ^4.1.11 -- and the
      transitive alerts (undici, brace-expansion, browserslist, form-data,
      js-yaml, postcss, @babel/core, baseline-browser-mapping, @vitest/mocker,
      react-router) are cleared by the resulting lock resolution rather than by
      pinning overrides. If an override is unavoidable, the task states which and
      why.
- [ ] No dependency crosses a major version. Every bump listed above is within the
      same major, so a major-version jump appearing in the diff is a finding, not
      a fix.
- [ ] The whole backend test suite passes, and the whole frontend test suite
      passes. `ruff check` is clean.
- [ ] pydantic-settings is called out specifically: APRAS-108 relies on Settings
      resolving `extra` to `forbid` and on no BCRYPT/ROUNDS field being
      declarable, and tests/test_bcrypt_cost.py asserts both. Those tests must
      still pass after the bump, and if the library changed that resolution the
      task reports it rather than relaxing the test.
- [ ] .github/dependabot.yml is added with exactly this shape, so it can be failed
      rather than merely preferred: two ecosystems -- `uv` at /backend and `npm`
      at /frontend (NOT `pip`: PR #30's branch is dependabot/uv/backend/..., and
      pip would drive only the generated requirements.txt and leave uv.lock
      behind, manufacturing the split this task exists to avoid);
      `schedule.interval: weekly`; `open-pull-requests-limit: 3` per ecosystem;
      one group with `applies-to: version-updates` limited to minor and patch; one
      group with `applies-to: security-updates`; and `ruff` in the backend
      version-update group's `exclude-patterns`, with a comment citing APRAS-54
      for why that pin is held. Context, not a requirement: Dependabot security
      updates are already enabled and PRs already open (#29, #30 are open now) --
      the 57 accumulated because PRs went unmerged, so this file is for
      scheduling, grouping and a PR ceiling, not for turning anything on.
- [ ] The frontend build still succeeds (npm run build), since vite and the
      babel/browserslist chain are among the bumps and a broken build would not be
      caught by the unit tests alone.
- [ ] No `overrides` block is added to frontend/package.json -- every transitive
      alert is reachable from the direct bumps. The update is NAMED (`npm update
      <pkgs>`), never bare, and the mechanical proof is that NO package outside
      the four directs and the twelve transitives listed in the spec changes
      version in frontend/package-lock.json. react, react-dom, tailwindcss,
      eslint, jsdom, typescript and @tanstack/react-query in particular must be
      untouched. A bare `npm update` lifts every unrelated caret and buries the
      security diff, and nothing else in the repository afterwards would
      distinguish the two.
- [ ] `npm audit` reports zero vulnerabilities, against a baseline of 15 packages
      (2 low, 3 moderate, 10 high). This is the PRE-MERGE gate and it catches one
      package the 57 alerts do not: nanoid (<=3.3.17, high) is auto-dismissed on
      GitHub but real, and clears free via postcss 8.5.28. The alert count itself
      can only be checked AFTER merge, since alerts are computed on master.
- [ ] Target the LIVE advisory ranges, not the numbers written on this card:
      brace-expansion now needs >1.1.17 and >5.0.8 (this card said 1.1.16 / 5.0.7)
      and js-yaml needs >4.3.1. Advisory ranges widen between the day a task is
      written and the day it is done.
- [ ] No application source, test or CI file is modified by this task. It changes
      dependency manifests and lock files only. This is what forbids 'relax the
      failing test' as a response to a breaking bump, generally -- not only for
      test_bcrypt_cost.py. If a target version breaks `npm run build`,
      `test:coverage` or pytest: do NOT edit source or tests. Drop to the lowest
      in-range version that still clears the advisory and passes; if none exists,
      stop and report that package.
- [ ] `npm run lint` reports no more errors than the current baseline of ~375
      across 64 files. 'Zero repo-wide' is unsatisfiable and must not be used.
- [ ] Two floors the spec's own table implies but an earlier draft of this card
      understated: postcss must reach 8.5.28+, not 8.5.23 -- `nanoid: ^3.3.18`
      first appears in 8.5.28, so 8.5.23 would satisfy a postcss clause while
      leaving nanoid vulnerable. And @vitest/coverage-v8 must resolve to 4.1.11 in
      the lock, matching vitest: a lock where the two disagree is a finding.

## Out of Scope

- Any major-version upgrade (`react-router` 8, `@babel/core` 8, `vite` 8.3,
  `undici` 8, `js-yaml` 5, `vitest` 5) — each needs its own task.
- The stale `@types/react-router-dom ^5.3.3` devDependency, obsolete since
  `react-router-dom` 7 ships its own types. Unrelated to any advisory.
- A `github-actions` Dependabot entry, and any new CI audit gate.
- The ~375 pre-existing `npm run lint` errors.
- `secret_scanning`, which is disabled on the repository.
