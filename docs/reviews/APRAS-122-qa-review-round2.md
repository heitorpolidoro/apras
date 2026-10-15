# APRAS-122 — QA verification, round 2

VERDICT: APPROVED

R10, the sole blocking finding of round 1, is **fixed and independently
verified**. Nothing the edit could plausibly have touched is broken. R5 remains
the only outstanding item, pending the operator's push.

---

## What I verified, and what I deliberately did not

The change is confined to one markdown file under `docs/tasks/`. That bounds
what could have regressed. I re-verified:

- **R10** in full, from scratch — census, row set, occurrence counts, verdict,
  and the two corrected claims.
- **R9**, because §5 gained new labelling around the four mutation transcripts
  and the coordinator asked me to judge whether that labelling is honest.
- **R2, R3, R4, R11**, because all four rest on the content of this document.
- **R13, R14**, because they are about tree scope and suite health, which any
  working-tree change can disturb.

I did **not** re-verify R1, R6, R7, R8 or R12. Those rest on
`.github/workflows/*.yml`, `backend/tests/test_workflow_actions.py` and
`AGENTS.md`, none of which is modified — `git status --porcelain -- .github/
AGENTS.md backend/` reports only the long-standing untracked
`backend/scripts/sync_obras_from_drive.py`. I re-ran the guard module anyway as
a cheap regression check: **15 passed**.

---

## Working-tree state — verified, with one correction to the brief

- `git rev-parse --short HEAD` → `04eabec`. No new commit.
- `git diff --cached --numstat` → **empty**. Nothing staged.
- The audit file is modified and unstaged: `399 insertions, 78 deletions`.
- `gh api repos/:owner/:repo/git/ref/heads/...` was not needed; no branch was
  created and nothing was pushed — `origin/master` is still `25e9dc6`.

**Correction to the brief's "one file … nothing else was touched".** `git diff
--numstat` reports **two** modified files:

```
1873	0	docs/suggestions-log.md
 399	78	docs/tasks/APRAS-122-action-audit.md
```

`docs/suggestions-log.md` was already `M` at the start of my round-1 session, so
it is not new — but its mtime is `Oct 10 22:05:32`, **after** the audit file's
`21:58:49`, so it was written during or just after this round, and its diff
contains 14 `APRAS-122` mentions. Inspecting it: it is append-only (1873
insertions, 0 deletions) and is the pipeline's own cross-task suggestions log,
carrying `## [APRAS-84]`, `## [APRAS-122] … (round 2/3/4)` and a process-gap
note about the Meridian schema's `questions` field. It is orchestration
bookkeeping, not product change, and it touches nothing any test or workflow
reads. **Not a finding — but the brief's claim that one file changed is not
literally true, and I was asked to check it myself rather than accept it.**

---

## R10 — the census, re-derived independently

I did not re-run the document's pipeline and compare. I wrote my own scanner
(python, one `uses:` per line, quote-stripping, `./` reusable calls dropped) and
compared its output to the document afterwards.

**Count.** My scanner: **12 distinct third-party refs, 43 occurrences, 10
files, 4 reusable calls excluded.** The document's `sort -u | wc -l` → `12`,
`wc -l` → `43`, `grep -rln | wc -l` → `10`. I then ran the document's own
pipeline verbatim and got the same 12 refs — identical set, not merely the same
cardinality.

**Row-by-row occurrence counts.** Mine, sorted, against the document's table:

| Ref | Mine | Doc |
| --- | --- | --- |
| `actions/checkout@v6` | 9 | 9 |
| `actions/create-github-app-token@29824e6` | 7 | 7 |
| `astral-sh/setup-uv@v8.1.0` | 5 | 5 |
| `google-github-actions/run-gemini-cli@v0` | 5 | 5 |
| `actions/setup-node@v6` | 4 | 4 |
| `actions/github-script@ed597411…` | 4 | 4 |
| `actions/upload-artifact@v7` | 2 | 2 |
| `actions/download-artifact@v8` | 2 | 2 |
| `actions/checkout@v4` | 2 | 2 |
| `actions/github-script@60a0d83…` | 1 | 1 |
| `actions/checkout@8e8c483…` | 1 | 1 |
| `SonarSource/sonarqube-scan-action@v7` | 1 | 1 |

Sum **43**, matching. All six refs I named as missing in round 1 now have rows
(2, 3, 6, 9, 10, 11), and the two `actions/github-script` refs are **two
separate rows** as R10 demands — the requirement is now satisfied rather than
rendered vacuous.

**The `40d40a2` variant.** `git grep` at the pin commit confirms the tree there
was `ci.yml`, `migrate.yml`, `release.yml`; `--exclude=requirements-export.yml`
gives 12 refs / 41 occurrences / 9 files, and `requirements-export.yml`'s only
two `uses:` are `actions/checkout@v6` (99) and `astral-sh/setup-uv@v8.1.0`
(106), both already present. So the ref count is **12, not 13**, and R10's
"fourth `actions/checkout` ref" branch correctly does not apply. I confirmed
there are exactly three `checkout` refs: `@v6`, `@v4`, `@8e8c483`.

**The verdict — zero undeclared inputs — recomputed by me, not read.** I wrote a
second script that parses every step's `with:` block across all 43 occurrences
and diffs the keys against `inputs:` fetched with `gh api
repos/<owner>/<repo>/contents/action.yml?ref=<ref>` for each of the 12 refs:

```
occurrences checked: 43
steps with undeclared inputs: 0
```

Declared-input counts my fetch returned, against the document's: `checkout@v6`
21/21, `checkout@v4` 21/21, `checkout@8e8c483` 20/20, `setup-node@v6` 12/12,
`upload-artifact@v7` 8/8, `download-artifact@v8` 10/10,
`sonarqube-scan-action@v7` 5/5, `create-github-app-token@29824e6` 56/56,
`github-script@ed59741` 9/9, `github-script@60a0d83` 9/9,
`run-gemini-cli@v0` 21/21, `setup-uv@v8.1.0` 24/24. **All twelve match.**

**A trap I fell into, which the document did not.** My first parser flagged four
apparent undeclared inputs — `owner`, `repo`, `per_page`, `issue_number`,
`labels` on `github-script@ed59741` at `gemini-triage.yml:34/130` and
`gemini-scheduled-triage.yml:43/168`. Reading the files, those are JavaScript
object keys **inside a `script: |-` block scalar**, not YAML inputs. My parser
was block-scalar-blind; the document's row 6 records exactly the right keys
(`script` at 43/34; `script` + `github-token` at 168/130). I fixed my parser to
skip block-scalar bodies and the count went to zero. Spot-checking eight
individual occurrences against the table — including
`requirements-export.yml:106` (`checksum`, `enable-cache`, `version`),
`requirements-export.yml:99` (`fetch-depth`, `persist-credentials`, `ref`) and
the three zero-key rows — all eight match. **The document's analysis was more
careful than my first attempt at checking it.**

**The reasoning for completing rather than excluding — I agree with it.** The
exclusion path lands on 7 refs across 4 files, a figure R10 names nowhere, and
it would have made the "two separate `github-script` rows" clause vacuous. That
is the shrinking move I rejected in round 1, reached by a different route. The
developer instead kept the exclusion's *reason* as row context and backed it
with evidence rather than inference: `gh api
'repos/:owner/:repo/contents/.github/workflows?ref=master'` returning only
`ci.yml`, `migrate.yml`, `release.yml`. That is the right shape — the claim
"these never execute on GitHub" is now checkable instead of asserted.

**The withdrawn conclusions are properly withdrawn.** §6 now states that the
`git ls-tree` / `git log --all` evidence "is true but answers a different
question — it proves the files are **not committed**, not that they are **not
there**", and ledger rows 20 and 21 mark both as *reproduces, conclusion
withdrawn*. I re-ran both: `git ls-tree --name-only 2cb0d48 .github/workflows/`
still prints three files; `git log --oneline --all -- '.github/workflows/gemini*'`
still prints nothing. The document no longer draws the wrong inference from
either, and keeps them rather than deleting them — which is the honest move.

**On the quote-stripping claim.** The brief glosses it as "a second,
independent reason [the old scan] was wrong". The document itself does **not**
make that causal claim — §6 says only that the new `sed` "strips the
surrounding quotes the `gemini-*.yml` files put around their `uses:` values",
and ledger row 17 says the old `sed` "also failed to strip" them. That
distinction matters, and the document gets it right: I ran the old pipeline on
the real tree and it prints **16** rows, not 6, splitting quoted and unquoted
refs. So the quoting bug is a genuine *additional* defect in the old command,
but it is not what produced the 6 — pretending the files were absent is. The
document does not confuse the two.

**R10 verdict: met.**

---

## R9 — the four un-re-run mutation transcripts

**Honest enough, and corroborated independently.** §5 now carries, before the
transcripts:

> **These four are dated observations, anchored at the pin commit `40d40a2`**,
> and the `ci.yml:55` / `:160` / `:221` line numbers in them are that commit's
> … Re-running them against today's tree would print 224/285 instead and would
> require editing a workflow file, which is out of this document's scope.

I verified the anchor myself:
`git grep -n 'astral-sh/setup-uv@' 40d40a2 -- .github/workflows/ci.yml` prints
exactly `55`, `160`, `221`, and `git grep -o … | wc -l` over the workflows dir
prints `4`. The cited lines are the real ones at that commit.

More importantly, **R9 does not depend on these four transcripts being
re-executed, because I built my own mutants in round 1** covering all four
classes (`pyproject-file:` re-added, one literal changed, one `version:`
deleted, unknown ref) plus four more, watched each go red, confirmed each
mutation on disk before pytest ran, restored and `cmp`-verified. The committed
outputs' assertion line numbers (`:381`, `:414`, `:401`, `:374`) match the
committed module. So the pasted outputs are corroborated rather than trusted,
and the "dated observation" label is accurate rather than an excuse. **No
re-execution is needed before R9 can stand.**

---

## §9 ledger — spot-checked, not accepted

A ledger of re-runs is exactly the artefact that can look diligent while being
wrong, so I re-executed **all eighteen** rows marked `yes`, including the ones
claiming "reproduces exactly". Every one reproduced.

The sharpest checks, since these are the ones a fabricated ledger would fail:

- **Row 2** quotes three log timestamps to seven decimals. I pulled the three
  job logs and got `2026-10-01T20:47:47.2103370Z` (job `…457`),
  `20:47:46.0495934Z` (`…946`), `20:48:08.8191969Z` (`…967`) — exact, all
  three, including the two the round-1 document never printed.
- **Row 3** claims `grep -c 'Unexpected input'` is 2 per job. Mine: `2, 2, 2`.
- **Row 10** quotes three after-run timestamps. Mine:
  `13:14:10.0552552Z`, `13:14:26.5351168Z`, `13:14:09.4210950Z` — exact.
- **Row 8** quotes the Meridian question. I read `.meridian/tasks.jsonl`
  read-only: `q-1790947582472-122`, `by: "Agent"`, `answer: "yes"`,
  `answered_at: "2026-10-02T13:33:08.907Z"` — exact, including `by`.
- **Row 15** claims dependabot declares only `uv` and `npm`. Mine:
  `26:  - package-ecosystem: "uv"`, `60:  - package-ecosystem: "npm"`, zero
  `github-actions` occurrences — exact line numbers.
- **Row 19**, the corrected one: `grep -rn "uses: *['\"]\?\./" .github/workflows/
  | wc -l` → **4**, at `gemini-dispatch.yml:132/146/160/174`. The round-1
  claim of `0` was indeed false; the correction is right.
- **Rows 16, 17, 18**: `ls -1 … | wc -l` → `10`; old scan → 16 rows; new scan →
  12. All as the ledger states.
- **Rows 5, 6** (§2): `git grep` at `40d40a2` → 55/160/221 + `migrate.yml:17`,
  count 4; current tree → 5 occurrences at 55/224/285/17/106. Both reproduce,
  and §2's `diff` loop showing the `uses:` set is unchanged across
  `ci.yml`/`migrate.yml`/`release.yml` between `40d40a2` and `04eabec` also
  reproduces — which is the load-bearing step that lets §6's current-tree scan
  speak for the landing commit.
- **Row 22**: the five original `action.yml` input counts (21, 12, 8, 10, 5) all
  match my own fetches.

**One ledger wording nit, not a defect.** "Twenty-two blocks" counts *claims*,
including three explicitly labelled `prose:` and two rows that bundle several
commands; the document contains 21 fenced `bash` blocks and 25 `$` prompt lines.
A reader could take "every command block in this document has been re-executed —
twenty-two blocks" as a claim about the document's current block count, which it
is not: the round-2 transcripts (the `ls -1` listing, the `.gitignore` grep,
`gh api contents?ref=master`, the `--exclude` scans, the two `diff`s, the tag
lookup) are new evidence, not re-runs, and are not ledgered. I verified a large
sample of those new blocks directly and every one reproduced, so the substance
is sound.

---

## The two self-found claims — both verified

- **`github-script` input sets.** The spec's claim that the two refs' "declared
  inputs are not the same set" is **false**, and the document is right to say
  so. My `diff` of the two `action.yml` files returns exactly one hunk:
  `39c39 < using: node24 / > using: node20`. Both declare the same nine inputs.
  Keeping them as separate rows anyway is correct — one row per distinct ref.
- **`checkout@8e8c483` drift.** `gh api repos/actions/checkout/git/refs/tags`
  resolves `8e8c483db84b4bee98b60c0593521ed34d9990e8` to **`refs/tags/v6.0.1`**.
  Diffing `@v6` against that sha returns one hunk: the nine added lines
  declaring **`allow-unsafe-pr-checkout`**, so `@v6` has 21 inputs and the sha
  has 20. Nothing in `.github/workflows/` passes it, so not a finding — and the
  document says exactly that, filing it as a measured instance of §7's drift
  follow-up. Correct on every point. (I also confirmed `@v4` and `@v6` differ
  only by `using: node20` vs `node24`, as the rows state.)

---

## Anything the edit could have broken

- **R2** — unaffected. §1 is untouched by the diff (the hunk map starts at line
  85, in §2), and ledger rows 1–3 and 9–10 reproduce. The after-side evidence is
  intact.
- **R3** — strengthened, not weakened. §4 gained four lines explaining that
  `requirements-export.yml` has no job in run `37315213778` because it did not
  exist at `40d40a2`. The job table, ids and attempt-1 conclusions are unchanged
  and re-verified via `gh api …/runs/37315213778/jobs`.
- **R4** — unaffected. §3 is untouched by the diff. I re-confirmed
  `headSha 40d40a2… = the landing sha`, `event workflow_dispatch`, branch
  `tmp-apras-122-uv-pin-gate`, `conclusion success`, and the
  `q-1790947582472-122` answer `yes` (not a refusal, so the first path is still
  the one taken).
- **R11** — still met, and now on a sound basis. §7's "zero findings outside
  `setup-uv`" is no longer a statement about an incomplete census: all twelve
  refs were examined and all 43 occurrences are clean, which I recomputed
  myself. The round-1 caveat is discharged. `.github/workflows/` is unmodified,
  so no action other than `setup-uv` was touched. The follow-ups section now
  carries two entries with titles and one-line scopes.
- **R13** — unaffected. This round's change is one markdown file under
  `docs/tasks/`; `backend/pyproject.toml`, `backend/uv.lock`,
  `backend/requirements.txt`, `test_suite_hygiene.py`,
  `test_requirements_export.py`, `test_docs_agents_md.py` and everything under
  `frontend/` are untouched. The by-this-task reading I applied in round 1 is
  unchanged.
- **R14** — re-run. `uv run pytest tests/test_workflow_actions.py` → **15
  passed**; `test_workflow_actions` + `test_docs_agents_md` +
  `test_suite_hygiene` + `test_requirements_export` together → **77 passed**;
  `uv run ruff check .` → `[]`; `uv run ruff format --check .` → `303 files
  already formatted`.
- **No test reads this file.** `test_workflow_actions.py` restricts `read_text`
  receivers to `path` (under `.github/workflows/`), `AGENTS_MD` and
  `THIS_MODULE`, enforced by AST. Nothing under `backend/` references
  `docs/tasks/APRAS-122-action-audit.md`.

**The pre-existing failure, correctly attributed.** Full suite: `4217 passed, 1
failed, 38 skipped`. The failure is
`tests/test_bcrypt_cost.py::test_passlib_is_not_installed` — `passlib` is
present in the local venv (`importlib.util.find_spec("passlib")` is not None)
while the project deliberately depends on `bcrypt` directly; `passlib` appears
in `backend/pyproject.toml` only inside a comment. This is a local-environment
condition, unreachable by a markdown edit, and I do **not** attribute it to this
round or to APRAS-122. It should be raised separately with the operator.

---

## Blocking Findings

None.

---

## Suggestions

- `_parse_with_block` in `backend/tests/test_workflow_actions.py` is
  block-scalar-blind in the same way my first scanner was: a `with:` key whose
  value is `|`/`|-` would have its body's `key:` lines absorbed as inputs. It is
  harmless today — no `setup-uv` step uses a block scalar, and the four
  anti-vacuity assertions would not be fooled — but if a future step passes
  `script:`-style content the guard would report phantom undeclared inputs. A
  three-line skip on block-scalar bodies would close it. Not blocking; the
  module's scope is `setup-uv` only.
- §9's "Twenty-two blocks" would read more plainly as "twenty-two recorded
  claims (command transcripts and the prose assertions derived from them)",
  since the document's fenced-block count is different and the round-2
  transcripts are new evidence rather than re-runs.
- Row 3 of §6 lists `run-gemini-cli@v0`'s `with:` keys as a "union of 18" across
  five occurrences. The union is correct, but since the verdict is per
  occurrence it would be easier to re-check if the row said which five
  occurrences contribute the four conditional keys, the way row 6 does for
  `github-script`.
- `docs/suggestions-log.md` is accumulating uncommitted across many tasks (1873
  unstaged insertions spanning at least APRAS-84 and APRAS-122). Worth a
  decision from the operator about when it lands; it is not this task's to fix.

---

## Pending the push

- **R5 — the only outstanding result, unchanged from round 1.** `migrate.yml`
  declares only `on: push: branches: [ master ]` and no `workflow_dispatch`, so
  no run of it can exist while local `master` sits twelve commits ahead of
  `origin/master` (`25e9dc6`) with nothing pushed. After the operator pushes it
  needs, recorded in the audit:
  1. the `migrate.yml` run id;
  2. its `Run DB Migrations` job id and `conclusion: success`, from
     `gh api repos/:owner/:repo/actions/runs/<run_id>/jobs --jq '.jobs[] |
     "\(.id) \(.name) \(.conclusion)"'`;
  3. that job's log showing `Successfully installed uv version 0.12.19`, zero
     `Falling back to latest` lines, and `grep -c 'Unexpected input'` at 0.

  Everything else R5 asks for is already in place: §4's sub-section
  "`migrate.yml` is covered, not excluded" states the coverage and the reason
  (it is the only job holding `POSTGRES_URL_NON_POOLING` and the only one
  running `alembic upgrade head` against production), and names the two
  commands to fill in. Only the observed values are missing, and they cannot
  exist before the push.

- R2, R3 and R4 were verified in round 1 and re-confirmed here; they are **not**
  pending. R4 in particular needs no action before the push — the dispatched
  run `37315213778` already satisfies its first path, and the throwaway ref it
  used has been deleted (`gh api …/git/ref/heads/tmp-apras-122-uv-pin-gate` →
  404).

---

VERDICT: APPROVED — R10 fixed and independently re-derived; nothing the edit
could have touched is broken; R5 alone pending the push.
