# APRAS-123 — spec review, round 5 (findings-only)

VERDICT: APPROVED

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-123-spec.md`
Tree: `master` @ `2cb0d48`. Nothing in the repository was modified; all
verification ran from a scratchpad copy of `frontend/src/lib/contrast.ts`
transpiled with the repo's own `typescript` binary (no install).

## Blocking Findings

None.

## 1. Is the round-4 finding resolved, and is the exemption unambiguous?

Result 8's checkable form now reads: grep the test file for each of the 19
rows' `oklch()`/`#rrggbb` pairs; **no pair other than the single sentinel pair
`oklch(0.62 0.15 160)`/`#009f68`** may be found; **one** hit on any other row's
pair is a failure, not only two.

Decidable from the results list alone: yes. The 19 pairs are not needed as
literals in the results — they are read from the deliverable the results
require (`docs/frontend/contrast-provenance.md`, results 7 and 8), and result 8
also enumerates the 19 tokens by name and by block. A QA agent holding only the
results therefore has (a) the file to grep, (b) the source of the pair list,
(c) the exemption, and (d) the quantifier. No reference to §6 or §9 is needed.
The cross-reference inside result 8 ("that result 5 requires the test to
count") also resolves correctly against the current 15-item list: the sentinel
pair is in result 5.

Narrowness: the clause exempts **the pair**, named by value, three times over
("no pair other than the single sentinel pair", "that one pair is exempt", "one
hit on any **other row's** pair is a failure"). It cannot be read as exempting
the whole `:root` block — `:root`/`--destructive`'s
`oklch(0.58 0.24 27)`/`#e60018` is plainly still forbidden. It can be read as
covering both rows that carry the pair, which is unavoidable and harmless: the
two rows are value-identical, so exempting the pair and exempting both rows'
pairs are the same set of strings. The residual reading difference — whether
"a pair hit" means both members on one line or anywhere in the file — cannot
flip a correct implementation (see §2 below), so it is a note, not a finding.

**Collision enumeration (the check that round 4's defect demanded).** I
enumerated every literal the spec requires the test file to contain and
compared each against the 19 rows' values:

- sentinel `oklch(0.62 0.15 160)` + `#009f68` (result 5) — exempt;
- the two sentinel file paths, the five import specifiers, the two regex
  literals, the ignore-marker and ratio-marker forms, the floor numerals
  (100, 8, 17, 5, 4, 19, 4), the three shape regexes — none is a colour value;
- nothing in the results requires the test to hold `#e60018`,
  `oklch(0.58 0.24 27)`, `#00aa6f`, `oklch(0.65 0.15 160)` or any
  `--status-*`/`--priority-*` value. Result 7's three hexes live in the
  **document**, not the test; result 6's ratio operands are parsed from the
  markers, not inlined.

So exactly one collision existed, it is the one now exempted, and the grep
check no longer fails on correct work. Under either reading of "pair hit"
(same-line, or file-wide AND) a conformant test passes, because no non-exempt
row's oklch *or* hex is required anywhere in the file.

## 2. Does the exemption reopen the hole the four rounds closed?

No. The inventory cannot be smuggled back using the exempt pair:

- the document side of the assertion is **parsed**, and the assertion is set
  **equality** of `(block, token, oklch, hex)` 4-tuples against the set derived
  from `index.css` via `isInGamut` + `oklchToHex`;
- a hardcoded document side made of 19 copies of the sentinel tuple fails that
  equality immediately, because `index.css` yields 18 other distinct values
  (verified below);
- the `≥ 19`-on-both-sides floor blocks the empty-equals-empty escape;
- result 12's third proven-to-fail run (one hex of one table row set to
  `#00a166`, must fail **by set inequality, naming the row**) forces the
  document to be the actual input.

The most an implementer can legitimately inline is one pair, plus — if they
choose — the two block/token names that carry it, which are already published
in result 8's own prose and which cannot make a wrong figure pass.

## 3. Independent verification of every mechanically checkable figure

Run against `contrast.ts` and the committed tree (`git ls-files`), with my own
implementation of the three claim shapes, written from §1 without consulting
the spec's numbers first:

| spec claim | my measurement | verdict |
|---|---|---|
| 125 tracked documents in scope, 98 md (96 tasks + 2 frontend) + 27 html | 125 / 98 (96+2) / 27 | exact |
| 17 claims across 8 documents, committed tree | 17 across 8 | exact |
| 0 mismatches on the committed tree | 0 | exact |
| `APRAS-90-mock.html` ≥ 5 shape A | 5 | exact |
| `APRAS-76-mock.html` ≥ 4 shape B | 4 | exact |
| 58 `oklch()` declarations in `index.css`, all parse | 58, all parse | exact |
| 19 out of gamut, 16 light / 3 dark | 19 (16/3) | exact |
| §6 table = `index.css`-derived set | set difference empty both ways | exact |
| four ratios 3.4054 / 1.4117 / 6.4180 / 1.8021 | identical to 4 dp | exact |
| `oklch(0.5 0.15 20)` (`--status-canceled-fg`) in gamut, `oklch(0.5 0.15 70)` out | confirmed | exact |
| `#008a5a → oklch(0.56 0.13 160.15)` round-trips to `#008b5a` | confirmed | exact |
| `oklch(0.68 0.14 237.32)` paints `#23a3e3` | confirmed | exact |
| shape-B example `oklch(0.53 0.02 160)` / `#627068` | confirmed | exact |

Anchored marker emptiness: `grep -rn -E '^[[:space:]]*<!--[[:space:]]*(contrast-guard|ratio)'`
over `docs/tasks`, `docs/frontend` and `docs/reviews` returns nothing, in the
**working** tree — so no untracked sibling document (APRAS-98, -102, -121, -122
and the rest are all present uncommitted) trips result 9's exact-empty-list
assertion either.

The spec is self-passing as a scanned document. It contributes 8 claims of its
own — shape A at lines 50, 51, 455; shape B at 52; shape C at 317, 318, 319,
514 — and all 8 derive correctly, so landing it does not turn its own guard
red. Its §6 table rows contribute **zero** claims, confirming §4's reasoning
that a connector-less pipe row is invisible to the scan.

The two self-referential regex literals are inert as claimed: the source text
`/await\s+import\s*\(/` is not matched by the pattern it expresses (`\s+`
matches whitespace, not a backslash), so the assertion can be written literally
and still pass on a correct file. No concatenation or excision device is
needed, which was round 2's defect and remains closed.

## 4. Convergence — the judgement asked for

My answer: **it has converged, and the shape that produced the four defects is
still present but no longer has anything to bite.**

The four defects were one family. Each was a *negative or self-counting
assertion whose subject includes the artifact making it*: a count of a document
inside that document; a scan of a file for literals that file must contain; a
uniqueness claim made by one of the two copies; a grep-for-absence colliding
with a required literal. That family is collision-prone by construction, and
each round found the next collision by going one level further out — which is
exactly why it took four rounds rather than one: nobody enumerated the required
content exhaustively until the collision was pointed at.

I did that enumeration this round (§1 above) and it closes: there is one
collision, it is exempted, and no other required literal is a colour value.
Every number in the spec that can be checked against the tree checks out
exactly, including four I expected to drift. So I do not believe a sixth defect
of this family is waiting at implementation time.

One fifth instance of the family *did* surface in my pass, and it is the reason
I am recording a structural recommendation rather than a clean bill: §4's
"Expected post-landing measurement, for comparison: 126 documents read, 9
contributing, 20 claims" counts this task's provenance document but **forgets
this spec itself**, which §9 lists as a committed deliverable in
`docs/tasks/` and which contributes 1 document and 8 claims. The real
post-landing figure is ~127 documents, 10 contributing, ~28 claims. This is not
blocking: the binding floors are `≥` and are satisfied, §4 explicitly orders
re-measurement at landing rather than copying, and the error is in the safe
direction (the implementer measures *above* the comparison figure, so §4's
"below these numbers is a defect to investigate" tripwire does not misfire).
But it is the same mistake one more time: a statement about a document set that
forgot it was a member of the set.

**Structural recommendation, for the operator, not a condition of approval.**
Grep-for-absence over a file that must contain some of the same strings cannot
be made safe in general — every new required literal reopens it, which is the
mechanism that burned four rounds. The fix is to remove the need for the
literal rather than to exempt it:

1. Write result 5's sentinel assertion in terms of a pair **parsed from the
   provenance document** ("the pair of row `:root`/`--primary`, as parsed,
   appears at least twice in the claim set") instead of a literal pair. The
   assertion is identical in strength, the test then holds **no** inventory
   value at all, and result 8's grep becomes total again with no exemption and
   no quantifier clause. This is the single change I would make.
2. Treat "the test holds no second copy of the inventory" as a code-review
   property of a single-expression derivation, the way §7 already treats the
   absence of arithmetic literals ("a stated property of the file, checked by
   the reviewer reading it, not by the file reading itself"). §7 reached that
   conclusion for its own needles in round 2; result 8 is the same problem and
   did not inherit the lesson.

Either change is textual in size and structural in effect. Neither is needed
for the spec as written to be implementable, which is why the verdict is
`APPROVED`.

## Suggestions

- Fix §4's expected post-landing comparison figure to account for this spec's
  own entry into the scanned set: ~127 documents read, 10 contributing, ~28
  claims (its 8 claims are at lines 50, 51, 52, 317, 318, 319, 455, 514, all
  correct). As written a future reader could use 20 as a sanity anchor and
  conclude the scan over-matched.
- Apply recommendation 1 above (sentinel parsed from the document rather than
  inlined) in the implementation if the implementer sees a clean way to do it;
  it is strictly stronger than the exemption and costs nothing.
- The internal `result N` cross-references are stale in five places and appear
  to track an earlier numbering: §4's heading says "result 4" (positive control
  is result 5), §5's says "result 2" (ratios are result 6), §6 labels the
  inventory "result 5" (it is result 8), §10 says "result 3" for proven-to-fail
  (result 12), and §8 says "result 11's proven-to-fail edits" and "result 12 is
  written to allow exactly this cap" (proven-to-fail is 12, the three-line cap
  is 13). §6's "the three loose hexes of result 7" and result 8's "result 5" are
  correct. None changes what must be built — each sits next to the full prose
  definition — but a renumbering pass would stop the next reader chasing them.
- The Meridian record for APRAS-123 currently carries no `expected_results`
  field at all. The 15 items I gated are the spec's `## Expected Results`
  section. Since QA sees only the task's array, the `work` skill must write
  those 15 items verbatim on approval; a partial copy would silently drop the
  exemption clause this round exists to add.
- "Pair hit" in result 8 is not scoped to a line. It makes no difference to a
  conformant file (no non-exempt row's oklch or hex is required anywhere in the
  test), so this is cosmetic, but "both members of the pair anywhere in the
  file" would be the stricter and more obviously intended reading to state.
