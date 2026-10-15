# APRAS-121 — spec revision, round 3

## State found on disk

The interrupted round-3 attempt had already landed every non-blocking point
except two. Present on arrival:

- `pyproject-file:` described accurately as an **undeclared input** of
  `astral-sh/setup-uv@v8.1.0` (declared inputs: `version`, `version-file`),
  silently ignored with a warning, so every `setup-uv` step in the repository
  already installs floating-latest uv — "not an override being removed".
- Pin test locator narrowed to the `setup-uv` step of the `backend` job in
  `ci.yml`, with `node-version: 24` named as the thing a loose locator would
  wrongly match.
- Guard needle given word boundaries and line scoping: `\buv[ \t]+export\b`,
  with the `setup-uv` + shell `export FOO=…` false positive spelled out.
- `checksum:` on the privileged job's `setup-uv`, justified by `v8.1.0`
  (2026-04-16) predating uv 0.12.19 and `validateChecksum` returning silently
  on a table miss.
- "Who bumps the pin" — nothing automatic, bumped deliberately by editing the
  three literals and the checksum in one commit.

Not present, and added this round: B1, B2, the push refspec, the
`required-version` fail-closed note, and the public-visibility record.

## B1 — second checkout cannot be placed as §2 required

Resolved by **choosing the `git fetch` form outright and rejecting the
second-checkout alternative**, rather than by naming a layout and step order.

Rationale written into §2:

- `actions/checkout`'s `path:` is relative to `$GITHUB_WORKSPACE` and the
  action refuses anything resolving outside it; with the head at the workspace
  root, every legal `path:` is inside the head work tree, so the original
  instruction was unsatisfiable.
- Relocating the head into its own `path:` would move every other path in the
  job — the `cd backend` the shared script does, the push's work tree — for no
  gain.
- Keeping the head at the root makes checkout *order* silently load-bearing,
  because `actions/checkout` runs `git clean -ffdx` on its target and a base
  checkout written first is deleted by the head checkout that follows.

The spec now fixes:

    git fetch --no-tags --depth=1 origin "$BASE_SHA"
    git show "$BASE_SHA":backend/scripts/export_requirements.sh

and records that this works **because the repository is public** — an
unauthenticated fetch-by-sha succeeds despite `persist-credentials: false` —
with a note to revisit the step if visibility ever changes.

### The recurring failure mode

Addressed directly, as its own named requirement rather than a parenthesis.
The job's final step **always** writes one line to `$GITHUB_STEP_SUMMARY`,
naming the base sha and exactly one of `export regenerated; pushed <sha>` or
`export already matches the lock; nothing to push`. A no-op run therefore
still leaves a visible run with a summary line; the absence of any run for the
head sha means the trigger, the gate or the `paths:` filter rejected it. Every
failure path (missing base script, absent secret) fails the job instead of
exiting zero. This became its own expected result (new result 8), because it is
the observable the reviewer said keeps escaping and burying it inside result 7
would have left it unchecked.

Result 7 was rewritten to name the `git fetch` + `git show` pair and to
explicitly exclude a second `actions/checkout`.

## B2 — result 9's outstanding-vs-unmet gate

The pass condition now lives **inside the result text**, in two branches and no
others:

1. the full demonstration evidence is recorded; **or**
2. `gh secret list` contains no `REQUIREMENTS_EXPORT_TOKEN` — today the list is
   `POSTGRES_URL_NON_POOLING`, `SECRET_KEY`, `SONAR_TOKEN`, `VERCEL_TOKEN` —
   and the task records the demonstration as pending that secret.

With the closing sentence: a missing demonstration while the secret *does*
exist is a failure, not an outstanding item. The "Operator prerequisite"
section no longer licenses a pass; it now points at the result's own text, so
QA, which sees only `expected_results`, needs nothing from it.

## Other changes

- **Push refspec**: `git push origin HEAD:refs/heads/"$HEAD_REF"` with
  `$HEAD_REF` from `github.head_ref`, justified by the detached, now-shallow
  head (`fetch-depth: 1` plus `--depth=1`); a bare `git push` has no upstream
  and `git push origin HEAD` targets `refs/heads/HEAD`.
- **`[tool.uv] required-version`**: noted as a residual that fails **closed** —
  a head adding an incompatible `required-version` makes `uv export --frozen`
  refuse, so the job errors and pushes nothing, and with the new summary-line
  observable it surfaces as a failed run rather than silence.
- Files-touched entry for the workflow updated to the fetch form plus the
  always-written summary line.

## Renumbering

Adding the observability result shifted the tail: the demonstration is now
result 9, docs result 10, the `frontend/` guard result 11. All prose references
updated (`Results 1–8, 10 and 11`, "result 9 requires `Backend Tests` to reach
`success`", the prerequisite heading). No merge of results was needed.

## Scope discipline

The repository-wide `pyproject-file:` removal stays out of this spec — it is
APRAS-122. Only `docs/tasks/APRAS-121-spec.md` was modified. Nothing staged,
nothing committed, no workflow run triggered.
