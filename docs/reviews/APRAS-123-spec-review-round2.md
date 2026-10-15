# APRAS-123 — spec review, round 2 (findings-only)

Spec: `/Users/heitor/workspace/apras/docs/tasks/APRAS-123-spec.md`
Tree: `master` at `2cb0d48`, working tree dirty with other tasks' untracked work.
Mode: findings-only re-review of round 1's five blocking findings (B1–B5),
plus a consistency pass over the sections that changed to fix them.

VERDICT: NEEDS_REVISION — one blocking finding, in §6 / expected result 8.

## Method

I re-derived everything load-bearing rather than reading the spec's claims.
Node 24's native type stripping let me import `frontend/src/lib/contrast.ts`
directly from throwaway scripts in the session scratchpad
(`/private/tmp/claude-501/.../scratchpad/`); nothing under `frontend/` was
modified, nothing was staged, `git status --porcelain frontend/` is clean.

Scripts written (scratchpad only):

- `g.mts` — walks `frontend/src/index.css` per declaration, counts `oklch()`
  occurrences, runs `parseOklch` / `isInGamut` / `oklchToHex` / `contrastRatio`.
- `scan.mts` / `scan2.mts` / `scan4.mts` — an independent implementation of the
  three claim shapes (A declaration-plus-gloss either order, B tuple row, C
  connector across line breaks on tag/emphasis/pipe-stripped text) over the
  committed scanned set and over the working tree, printing every claim and
  every mismatch.

## Previous blocking findings — status

### B1 (19, not 20) — RESOLVED, and the inventory is verified exact

My derivation from `index.css` with `isInGamut`:

- 58 `oklch()` occurrences in the file, **all 58 parse**, every one on a line
  that also carries a `--token:` declaration, none inside a gradient,
  `color-mix()` or shorthand. §6's parse claim is true as written.
- **19** out-of-gamut declarations, **16 `:root` + 3 `.dark`**.
- My table is **row-for-row and hex-for-hex identical** to §6's, including
  `#fff0d1`, `#7e5d00`, `#ceedff`, `#004d7d`, `#ffebd2`, `#8b5600`, `#b3ffd6`,
  `#005931`, `#ffe7e6`, `#004d58`, `#ffdfda`, `#00aa6f`.
- Result 8's enumeration adds up and is correct: 3 + five `--status-*-bg` +
  four `--status-*-fg` + 4 priority = 16 light, 3 dark.
- The asymmetry explanation holds: `isInGamut(oklch(0.5 0.15 20))` is `true`,
  `isInGamut(oklch(0.5 0.15 70))` is `false`.
- The four ratios are exact to 4 dp as published: `:root --ring` on `--card`
  **3.4054**, on `--destructive` **1.4117**; `.dark --ring` on `--card`
  **6.4180**, on `--destructive` **1.8021**.

### B2 (self-reading needle scan) — RESOLVED; the import pin traced

The needle self-scan is gone. §7 now states the literal absence as a property
checked by a human reader, which is honest, and pins provenance by imports.

Tracing the `^\s*import` anchor against the array-literal self-match hazard
that killed the needle version:

- A multi-line expected-set literal yields lines like `  "node:fs",` — not
  matched. ✓
- The regex literal itself, however formatted (`const IMPORT_RE = /^\s*import…`
  or broken so the line starts with `/`), never starts with `import`. ✓
- So the specific self-reference that made B2 unpassable is genuinely absent.
  A literal implementation is green on arrival.

Evasion surface, stated for the record:

- `import * as C from "colorjs.io"` → caught.
- `import type { X } from "colorjs.io"` → caught (`import\b` matches
  `import type`); `import type … from "../lib/contrast"` is in the allowed set,
  so no false failure.
- `import { createRequire } from "node:module"` → caught, so `require` is
  reachable only through a rejected specifier.
- `const C = await import("colorjs.io")` → **not** caught. A bare
  side-effect `import "colorjs.io";` is also not caught by a `from`-requiring
  regex, but yields no bindings and so cannot carry arithmetic.
- Multi-line `import { … }\nfrom "../lib/contrast";` would defeat the
  required-member half of the pin. Checked whether that is a live hazard here:
  **this repository has no Prettier config** (`frontend/` has no
  `.prettierrc`, `package.json` names no prettier), and existing source carries
  single-line imports up to 388 characters. So the project's actual formatting
  keeps every import on one line and the pin is safe in practice; the failure,
  if an implementer wrapped it, is immediate and loud rather than silent.

So §7's "strictly stronger than the needle list" is right in substance but
overstated in one word: a dynamic `await import()` is a fourth dependency the
pin does not reject. Non-blocking — see suggestions.

**Is a closed set the right instrument?** Yes, on balance. The objection — it
fails on a legitimate future `node:assert` — is real but the remedy is a
one-line edit to the allowed array *in the same diff as the new import*, which
is exactly the visibility the task wants: the pin is a review tripwire, not a
prohibition. A prefix allowance (`node:*` plus `vitest` plus `../lib/contrast`)
would be laxer for no gain, since the threat is a colour library, not a node
builtin. The subset-plus-required-member shape (rather than exact equality)
already removes the brittleness that matters. Keep it.

### B3 / B4 (ignore escape falsified by the spec; unparsable markers) — RESOLVED

Verified mechanically on the whole of `docs/`:

```
grep -rnE '^[[:space:]]*<!--[[:space:]]*contrast-guard:[[:space:]]*ignore.*-->[[:space:]]*$' docs/
→ (no output)
```

Every `contrast-guard` occurrence in `docs/` is either inside backticks with
prose on the line (`APRAS-123-spec.md:107`, `:112`, `:445`) or in
`docs/reviews/` (excluded anyway). The line-anchored rule therefore makes the
spec's own documentation inert, which is what B3 asked for. The same holds for
the ratio template: `:125` splits it across a line break, `:193` and `:419`
wrap it in backticks with trailing prose, so no occurrence is anchored.

The unparsable-marker half of B3 is addressed head-on in §2: a parse failure in
an anchored marker is a test failure naming file and line, never a skip, and the
`NaN` mechanism is named as the reason.

**Two normalisation rules in one module — hazard?** Acceptable. §2 states the
difference explicitly and gives the reason ("runs on the **raw** line: no HTML
tags, backticks, emphasis or pipes are stripped (unlike shape C)"), so the
divergence is specified, not emergent. The residual risk is an implementer
reusing the shape-C stripper for markers; that produces a *failing* test the
moment it meets this spec or the provenance document's template, not a silent
hole, so it self-corrects during implementation.

**"Documentation may never place a marker alone on a line" — tripwire aimed at
whom?** At the documenter, not the abuser, which is a fair criticism. But the
alternative (a stripping rule for markers) is strictly worse, since it is
precisely what B3 falsified. The constraint is cheap to honour (wrap in
backticks, or add any prose), loud when violated, and the spec requires the
provenance document to repeat it. Good enough.

**Result 9's exact-empty-list over a live repository — stable?** Yes, and this
is the *most* stable form available, not the least. An exact-empty assertion
only breaks when someone places a bare `contrast-guard: ignore` line in
`docs/tasks/` or `docs/frontend/` — and that is the one event the assertion
exists to catch, so a failure there is a true positive by construction. The
marker is a syntax this task invents; no concurrent task can emit it by
accident. Contrast this with the §4 floors, which *are* sensitive to concurrent
edits and are correctly written as `≥`.

### B5 (§8 vs result 12) — RESOLVED, with one wording tension

§8 and result 12 are now coherent with each other: §8 permits repairing a
figure landed by a concurrent task, capped at three lines, each listed in the
report, zero expected at the measured baseline, a fourth meaning stop; result 12
is written to allow "exactly this cap and nothing more". The
"no value in `frontend/src/index.css` changed at all" clause is about
`index.css`, a different file from the `docs/tasks/` repair, so there is no
contradiction between the two halves of result 12, and the no-exceptions-JSON
decision is untouched by either.

**Does "zero expected" survive APRAS-100 or APRAS-102 landing first?** I
checked rather than reasoned: both mocks and specs are already in the working
tree, and my three-shape scan over the **whole working tree** (141 documents,
including `APRAS-100-*`, `APRAS-102-*`, `APRAS-118-*`, `APRAS-119-*`,
`APRAS-121/122/123-*` and the untracked APRAS-98 pair) reports **35 claims
across 11 documents, 0 mismatches**. Neither APRAS-100's nor APRAS-102's mock
contributes a single claim. So if either lands before this task, the repair
count is still zero and the figure stays true. And the clause is anchored
("at the 0 mismatches measured at `2cb0d48`"), so a future nonzero measurement
does not falsify the result — it triggers the ≤3-line path, whose verifiable
content is the report listing. Sound.

## Floors, re-measured at `2cb0d48`

Independent implementation of the three shapes over the **committed** scanned
set (`git ls-files 'docs/tasks/*' 'docs/frontend/*'`, `.md`/`.html`):

| §4 figure | spec | measured |
|---|---|---|
| documents in scanned set | 125 | **125** (96 `docs/tasks/*.md`, 2 `docs/frontend/*.md`, 27 `.html`) |
| claims | 17 | **17** |
| contributing documents | 8 | **8** |
| mismatches | 0 | **0** |

Contributing documents: `APRAS-68-mock.html`, `APRAS-68-spec.md`,
`APRAS-76-mock.html`, `APRAS-76-spec.md`, `APRAS-87-mock.html`,
`APRAS-87-spec.md`, `APRAS-88-spec.md`, `APRAS-90-mock.html`.

Sentinels:

- `APRAS-90-mock.html` → **exactly 5** shape-A claims (lines 14, 15, 16, 17, 19);
  floor `≥ 5` holds at the measurement, as §4 admits.
- `APRAS-76-mock.html` → **exactly 4** shape-B claims (177, 178, 188, 189);
  floor `≥ 4` holds at the measurement.
- `oklch(0.62 0.15 160)` / `#009f68` as a claim pair → **3** occurrences
  (`APRAS-87-mock.html:13`, `APRAS-87-spec.md:23`, `APRAS-90-mock.html:16`);
  floor `≥ 2` holds with headroom.

The three excluded-false-positive cases in result 3 all check out:
`APRAS-68-mock.html:93–94` is a genuine cross-line `≈` claim whose hex is
`#23a3e3` (derived correctly) and not the brand input `#0ea5e9` on the same
line; `APRAS-68-spec.md:235` is hex-first and excluded by ordering;
`APRAS-68-spec.md:477` and `APRAS-92-spec.md:717` produce no claim under
connector anchoring. `APRAS-87-spec.md:23` is a Markdown-table shape-C claim
and is matched only after pipe/backtick stripping, confirming why §1 requires it.

**Hard-coded figures invalidated by the task's own new file:** none. Every
count in §4 and result 5 is a floor (`≥`), §4 instructs re-measurement at
landing, and the two exact-set assertions (the 19 index.css rows; the empty
anchored-ignore-marker set) are both immune to a new document being added —
provided the provenance document honours the marker-never-alone rule, which
result 9 restates. The defect shape that bit this task twice is absent here.

One overstatement, non-blocking: §4 says the provenance document "enters the
scanned set carrying the inventory's 19 derived hexes and four ratio markers,
so the real counts at landing are well above these figures." The inventory
table, written as Markdown pipes with no connector, yields **zero** claims — I
confirmed this on the identical table already present in this spec, which
contributes no claims at all from its 19 rows. The landing increase is therefore
much smaller than §4 implies. It cannot break anything, but it leads directly to
the blocking finding below.

## Blocking Findings

- **§6 / expected result 8 — the provenance document's own 19 hexes are
  published without any test that can contradict them, which refutes the
  spec's stated thesis.** Scope line 17 promises "the only way to write a
  colour figure into this repository is to let `contrast.ts` produce it, and
  that a figure disagreeing with `contrast.ts` fails a test." The inventory
  table that §6 puts into `docs/frontend/contrast-provenance.md` is matched by
  **none** of the three claim shapes: its rows are `| :root | --primary |
  oklch(0.62 0.15 160) | #009f68 |`, which after shape C's pipe/backtick
  stripping has no connector between the `oklch()` and the hex, is not a
  declaration (shape A needs `--token: oklch(…)`), and is not a JS tuple
  (shape B). I verified this empirically: the byte-identical table already in
  `docs/tasks/APRAS-123-spec.md` contributes **0** claims to my scan of all
  three shapes. The same holds for the three loose hexes result 7 requires
  (`#009f68`, `#e60018`, `#00aa6f`). The out-of-gamut assertion does not close
  the gap: it compares `index.css` against *the test's* inline list, never
  against the document, so §6's stated consequence — "a token added or moved out
  of gamut later fails until **the document** is updated" — does not follow from
  the mechanism described. Only the test's array must be updated; the document
  may silently drift, for example being left with `#00a166` in one row after a
  future edit. Nothing fails. This matters more here than anywhere else in the
  tree, because `AGENTS.md` will point every future author at this document as
  *the only permitted source for a colour figure*, so a stale row propagates
  into tasks indefinitely — the exact APRAS-98 failure mode the task exists to
  close, relocated into the task's own deliverable. It is also an ambiguity:
  result 8's "the same 19-row list appears in
  `docs/frontend/contrast-provenance.md`" reads either as a test assertion or as
  a documentation requirement checked by eye, and the two produce materially
  different guards. The spec must pick one and say which — the cheap option is
  to make the document's table itself the authority: parse its rows from
  `docs/frontend/contrast-provenance.md` and assert that the parsed
  `(block, token, oklch, hex)` set equals the set derived from `index.css` with
  `isInGamut` and `oklchToHex`, replacing the test's inline duplicate so there
  is exactly one copy of the figure; alternatively require the table to carry
  each row in a connector form (`oklch(0.62 0.15 160) → #009f68`) so shape C
  catches all 19 as ordinary claims. Either closes it; leaving the choice open
  does not.

## Suggestions

- **§7 — soften or close the dynamic-import hole.** "It is strictly stronger
  than the needle list" is not quite true: `const C = await
  import("colorjs.io")` is a fourth dependency that the `^\s*import` anchor does
  not reject, and a bare `import "x";` with no `from` clause escapes a
  `from`-requiring regex. Either add `await import(`, `require(` and the bare
  `import "<specifier>";` form to what the pin rejects, or say "stronger in the
  cases that matter, and static-import-only" and record the residual risk as §5
  does for prose ratios. The threat model here is an honest agent, so the hole
  is theoretical — but this spec's subject is criteria that overclaim.
- **§7 — pin the formatting assumption in one clause.** The line anchor depends
  on each `import` statement sitting on a single line. That is this
  repository's actual style (no Prettier config; imports up to 388 characters),
  but the four-name `../lib/contrast` import is 83 characters and any future
  formatter would wrap it and break the required-member half of the pin. One
  sentence — "each import is written on a single line, which the anchor
  requires" — removes the trap.
- **Result 11 vs result 12 — one word.** Result 12 says "the **only** permitted
  edit to an existing `docs/tasks/` document is §8's repair", while result 11
  requires a temporary edit to `docs/tasks/APRAS-90-mock.html` for the
  proven-to-fail run. Both implementers would do the same thing, so this is not
  blocking, but "the only permitted **committed** edit" removes a literal
  contradiction of the same family as round 1's B5.
- **§4's "well above these figures" is wrong as written.** Per the blocking
  finding, the inventory table contributes no claims, so the landing counts rise
  by roughly one document and whatever claims the provenance document's prose
  happens to carry. The instruction to re-measure rather than copy is right and
  should stay; the justification should be corrected (and will change anyway if
  the table becomes machine-checked).
- **§10's quoted line.** `docs/tasks/APRAS-90-mock.html:16` is
  `--primary: #009f68;       /* oklch(0.62 0.15 160) */` with run-in
  whitespace; the spec quotes it with single spaces. Harmless, since only the
  hex is replaced, but the shape-A matcher must tolerate multiple spaces before
  the comment — worth noting since that is how the real sentinel is written.
- **Positive note, no action.** My independent three-shape implementation
  reproduced §4 and §8 exactly — 17 claims, 8 documents, 125 documents, 0
  mismatches committed; 0 mismatches over the whole working tree — and the 19-row
  inventory, the four ratios and the gamut asymmetry are all exact. Apart from
  the finding above, this spec's figures are the best-substantiated of the chain.
