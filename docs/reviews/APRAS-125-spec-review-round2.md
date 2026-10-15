# APRAS-125 — spec review, round 2 (findings-only)

Spec: `/Users/heitor/workspace/apras/docs/tasks/APRAS-125-spec.md`, revision 2, 433 lines,
untracked. Tree `/Users/heitor/workspace/apras`, `master` = `4be622b`. Nothing staged or
mutated; probes in
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/specrev125`.

Round-2 scope per the pipeline: verify the four round-1 blocking findings are closed, and
a consistency pass over the sections that changed. I re-implemented §2's reader exactly as
specified and re-ran every figure on **both** Tailwind 4.2.4 (installed) and 4.3.3
(`package-lock.json`, installed into my own scratchpad). I accepted none of the 59/59
claims on trust.

**VERDICT: APPROVED.** All four findings are closed, every re-measured figure reproduces,
and the author's correction to my round-1 report is right — I was wrong about
`dark:bg-[url('/x.png')]` and say why below.

---

## 1. Finding 1 (emission premise / shape-agnostic reader) — closed, re-measured

Implemented §2 steps 1–4 verbatim (comments stripped first; at-rule preludes discarded at
`{` with the parent selector carried through; `&` substituted, descendant combinator when
there is a parent and no `&`; recursion into every body; match on effective selector equal
to `"." + escape(t)` or starting `"." + escape(t) + ":"`; `declarationsDeep` discarding
preludes at `{`).

| measurement | 4.2.4 | 4.3.3 |
|---|---|---|
| tokens matched / extracted | 59 / 59 | 59 / 59 |
| per-token failures | **0** | **0** |
| dark-gated (`.esc(t):is(.dark *)` prefix present) | **59** | **59** |
| R1 exact `.dark\:bg-foreground:is(.dark *)` present | yes | yes |

The effective selectors R1 resolves to differ in count and agree on the asserted string —
4.2.4 yields `['.dark\:bg-foreground', '.dark\:bg-foreground:is(.dark *)']`, 4.3.3 yields
`['.dark\:bg-foreground:is(.dark *)']` — so ER1's exact-string wording survives on both,
as the spec claims, with no nesting shape encoded anywhere. §0 is the right section and
mirrors §8's discipline; the diagnosis of revision 1's error (lockfile entry read while
probing the installed package) matches what I measured.

Also confirmed the depth-blind harvest is *necessary*, not stylistic: my round-1 depth-0
variant of the same reader failed exactly the 8 stacked tokens on 4.2.4 (`@media
(hover: hover)` two levels down), so §2's justification for `declarationsDeep` is
load-bearing and correctly stated.

## 2. Finding 2 (negative controls) — closed, and **my round-1 report was wrong**

§4's four-row table reproduces exactly, on both versions:

```
4.2.4 / 4.3.3, identical outcomes
  dark:bg-foreground        ACCEPT  props=["background-color"]
  dark:text-sm              REJECT (wrong property)  props=["font-size","line-height"]
  dark:bg-[url('/x.png')]   REJECT (wrong property)  props=["background-image"]
  dark:bg-nosuchcolour      REJECT (no rule)         props=[]
```

The correction stands and my round-1 claim that `dark:bg-[url('/x.png')]` "emits no rule"
was an artefact of my own probe, not of Tailwind: my probe's `escape` covered only `:`,
`/` and `.`, so it never matched the emitted
`.dark\:bg-\[url\(\'\/x\.png\'\)\]:is(.dark *)`. With §2's `escape` — which deliberately
adds `[ ] ( ) ' #` — the rule is found and carries `background-image`. **Treat §4's
assignment as authoritative and my round-1 §3 as corrected**: that candidate exercises the
wrong-property branch, and `dark:bg-nosuchcolour` (verified: no rule at all, both versions)
is the missing-rule control. The spec's `escape` definition is thereby doing real work, and
the warning against reusing `escapeClass` is correct.

Asserting `dark:bg-foreground` **accepted** in the same fixture compile as the three
rejections is the right shape: one call site shows the checker discriminating rather than
merely refusing. Together with the empty-list throw, §4 is a genuine answer to "a check
that could not have failed" — a checker returning `true` unconditionally now fails three
cases.

## 3. Finding 3 (candidate accumulation / disjointness) — closed, re-measured

Accumulation reproduced in round 1 on both versions and the spec now states it as the
reason for the contract. The mechanism is explicit ("a fresh `compile()` on every call and
caches nothing", as a commented contract, because the helper is shared) and — the part
that matters — it is *asserted*, not written down: the sentinel `dark:bg-fuchsia-300` is
confirmed absent from the extracted 59 and produces **0 matched rules in the scanned
sheet** on both versions. Caching `compileIndexCss` reddens that case. That is the
mechanical proof round 1 asked for.

The APRAS-110 escape itself is undamaged by the reader becoming shape-agnostic: shape
agnosticism widens how a rule is *located* in the sheet, never where candidates come from.
Re-confirmed `build([])` emits no utility rules and a fresh compiler without the token
emits no `.dark\:bg-foreground`.

## 4. Finding 4 (the seam) — closed

§6's seam is checkable against the file and is accurate: `build()` is at line **409**,
`compiler.build([...candidates])` at **427**, `const parsed = rules(css)` at **428** — so
"lifted out of lines 409–427, seam immediately before `const parsed = rules(css)`" is
exactly right, with no off-by-one. The split of responsibilities is the one I asked for:
`rules`/`declarations` move unchanged (preserving the `@layer`-only flattening and depth-0
semantics that `themeTokenCompile.test.ts` §1i and its last-unqualified-`:root` selection
depend on), and `rulesDeep`/`declarationsDeep`/`escape` are new readers placed beside them,
used only by the new guard. "Pure move" framing withdrawn, `SRC`/`FRONTEND_ROOT` re-derived
one level deeper with the reason stated, `escape` defined, `escapeClass` explicitly ruled
out. "`themeTokenCompile.test.ts` stays green" is now a meaningful proof because nothing it
calls changed.

## 5. The ruling you asked for: dual-version green, with APRAS-127 for reconciliation

**I accept the split.** The reasoning is not "keep the task small" — it is that the
dual-version requirement adds **zero** marginal complexity, which I verified rather than
assumed. My implementation of §2 contains no version check, no branch, no conditional:
one reader resolves effective selectors and both emission shapes collapse to the same
answer (59/59, 0 failures, 59/59 gated, identical control outcomes). The shape-agnostic
machinery is not a concession to two Tailwinds — it is what you must write anyway, because
the stacked tokens nest their declarations inside `@media (hover: hover)` on **both**
versions. A reader that handles that nesting handles the `&:is(.dark *)` nesting for free.

So the complexity does not belong in the reconciliation, because there is no complexity to
move. And the asymmetry favours the split in the other direction too: coupling a
test-only guard to a dependency bump makes the guard hostage to that bump's fallout — and
this very task is the evidence that a Tailwind minor can change emitted CSS. A
version-robust guard keeps working after APRAS-127 *and* after the next bump; a
version-pinned one would need editing both times. APRAS-127 at `high` in the backlog to
close both documented drifts (Tailwind and eslint) is the right home for the reconciliation.

One thing to keep: §0's requirement that the installed version be printed and reported
before any emission figure is quoted. That is what makes a dual-version contract auditable
rather than a loophole, and it must survive into QA's report.

## 6. The eight expected results, as the contract QA sees

All eight are decidable by execution. ER1 verified on both versions; ER2 verified (276
files, no excluded path in any provenance, `dark:bg-foreground`'s provenance contains
`TenantHeaderLogo.tsx`); ER3's sentinel verified absent on both; ER4's gate assertion
verified 59/59 and the four structural floors all hold today with the right margins; ER5's
four control outcomes verified on both; ER6 is a six-step on-disk procedure with a
`2 → 0 → 2` bracket; ER7 is CI's own command against a baseline I measured green in round 1
(198 files / 2594 tests, exit 0) plus named thresholds; ER8 is a `≤` bound, so the
`370/368/2` reading of the stale eslint also satisfies it without contradicting §8.

Eight results is the cap, not over it, and each asserts one thing about one case. The
deliverable is still one PR: one new test file plus one bounded helper extraction. Not a
split candidate.

## 7. YAGNI

Proportionate. The guard's machinery is now ~5 functions (walk, `declarationsDeep`,
`escape`, match, check), and every piece is forced by something measured: the walk by the
`@media` nesting, `declarationsDeep` by the stacked tokens, `escape`'s bracket characters
by the `url()` control, the fresh-compiler contract by the accumulation, the four controls
by this repository's six vacuous checks. Nothing in §2–§5 is there speculatively. The two
things I would have cut in round 1 — the fixture compile and the provenance map — both
earn their keep now that §4's controls ride in the fixture compile and ER2's non-brittle
form rides on the provenance map.

## Suggestions (non-blocking, for the implementer rather than another spec round)

- **Free strengthening, measured.** §2 lets the paint requirement and the gate requirement
  be satisfied by *different* matched rules. Requiring the paint declaration to come from
  the subtree of a rule whose own effective selector carries `:is(.dark *)` is strictly
  sharper and costs one `.filter()`: I measured it at **59/59, 0 failures on both
  versions**, with all four controls unchanged. It closes the (currently theoretical) case
  of a token that emits ungated paint plus an empty gated rule. Worth taking while the
  code is being written.
- ER4 on the board writes the selector as `.<token>:is(.dark *)` unescaped, while §2 is
  explicit that it is `"." + escape(t) + ":is(.dark *)"`. Harmless in the spec, but QA
  reads the board line alone — the escaped form would read less ambiguously there.
- §5's stacked-token floor says "two or more `:` before the utility". Phrased against the
  raw token that is right (8 tokens today); worth a parenthetical that it is counted on the
  unescaped token, since every other selector discussion in the spec is escaped.
- When the implementer reports §0's version line, have them report it **once per command
  whose output is quoted** (the vitest run and the mutation re-run), not once per session —
  the drift this spec exists to survive is exactly a figure quoted from a different tree
  than the one that produced it.

---

VERDICT: APPROVED

Blocking findings: None.
