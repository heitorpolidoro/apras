# APRAS-124 — spec review (round 3)

Spec: `docs/tasks/APRAS-124-spec.md` (605 lines)
Round 1: `docs/reviews/APRAS-124-spec-review.md`
Round 2: `docs/reviews/APRAS-124-spec-review-round2.md`
Reviewed against the working tree at `master` = `99a3d2d`. Nothing was staged,
committed, reverted or tidied; no file was edited; nothing was written to the
Meridian board; no production database or API was touched; no worktree under
`.claude/worktrees/` was read. No mock was expected and none is requested.

Findings-only re-review, scoped as the dispatch directs: closure of round 2's
five findings, the predictions the author added to close them, and the specific
checks listed below. The design (the `sha256(logo_url)` strong validator,
slowapi 0.1.10 without `deduct_when`, the `public_projects.py`-scoped AST
sweep, `no-cache` agreeing with the title, no migration, the APRAS-93/110
provenance) was confirmed in rounds 1 and 2 and is not re-litigated.

## Verdict

`APPROVED`. All five round-2 findings are closed, and every new prediction the
author added to close them is true when executed against the real test module
and the real service code. The apparatus is now arithmetically correct: the
three rows that were under-listed in round 2 are, after narrowing, *exactly*
true — neither short nor long — and the two rows whose value is target
uniqueness are checkable from the artifact the spec requires.

Not a `NEEDS_SPLIT` candidate: one route, one classmethod, one handler branch,
one test module.

## Blocking Findings

None.

## Round-2 findings — closure

1. **Mutation 8's false target — closed.** `test_the_route_sets_no_cache_and_a_strong_etag`
   is gone from row 8's "must redden" list and now appears in an explicit
   must-stay-green list, with the computed evidence (32-character fixture URL,
   64 hex characters) quoted in §"Test criteria" where the shape check is
   defined. The shape check is now stated, in as many words, to prove nothing
   about digest-ness. **The narrowing of the mutation itself is correct, and
   the author's reason for it is sound:** applied to the whole derivation,
   `tenant.logo_url.encode(...)` raises `AttributeError` for `logo_url=None`,
   which turns `test_a_star_is_404_and_never_304_without_a_representation` into
   a `500` and reddens `test_the_tag_derivation_refuses_only_the_two_pre_read_refusals`
   — two extra failures for a reason that has nothing to do with reversibility,
   on a row whose whole point is exhaustiveness. Confining the mutation to the
   final line, with both pre-read refusals left in place, makes row 8's list and
   its green list simultaneously true.
2. **Mutation 6's uniqueness — closed.** Row 6 is now scoped to the matching
   branch, the `200` path untouched, and it names the existing credential case
   as must-stay-green. The wrong inference ("a second failure means R4 is not
   the only thing pinning the saving") is deleted.
3. **Shared node id — closed.** The opacity property is three separately named
   functions, cited individually by rows 1, 4 and 8. The fixed-name count is
   twelve and is consistent everywhere (checked mechanically, below).
4. **Under-listed rows — closed, by narrowing rather than by listing.** Rows 1,
   3 and 4 are now exactly true (I traced all twelve cases against each; see
   below), and the enforcement sentence is split into an absolute half ("a
   mutation that reddens none of its cited ids is a missing test", all nine
   rows) and an asymmetric half (uncited failures are a finding on rows 6 and 8
   only). The self-contradiction is gone.
5. **The refusal case — closed.** Renamed to the pre-read refusal set,
   rewritten as three groups with group 1 defeating vacuity and group 3
   asserting §"One divergence" positively, and now cited by new mutation 9.
   §"When there is no stable identity" cites `tenant_service.py:596-621` with
   pre-read at `:611-613`/`:615-617` and post-read `:619-621` explicitly not
   mirrored — all four line ranges verified exact in the tree.

## What I executed, and what it found

**Row 8's and row 6's green lists — both true.**
- Row 8: the `_store` helper (`test_public_logo_route.py:98-102`) returns
  `/static/uploads/2026/09/{name}`, which for `logo.png` and `logo.jpg` is
  exactly 32 characters. I computed `len(url) == 32`, the hex
  `2f7374617469632f75706c6f6164732f323032362f30392f6c6f676f2e706e67`
  (64 characters) and `re.fullmatch(r"[0-9a-f]{64}", …) → True`, so the shape
  case stays green under a quoted hex echo, as the row asserts. The two other
  opacity cases also stay green: a hex echo of the URL is slug-independent
  (so the two-tenants case holds) and UUID-sensitive (so the UUID case holds);
  what reddens is `test_the_tag_is_not_a_reversible_encoding_of_the_stored_url`
  and `test_the_tag_is_the_literal_sha256_of_the_stored_url`, and nothing else
  in the twelve or in the existing module.
- Row 6: `test_the_route_reads_a_private_object_with_the_applications_own_credential`
  is at `:303-313` with `assert len(private_store) == 1` at `:312` — the
  citation is exact. The mutation as now written adds a discarded read only on
  the matching branch, and that case issues an **unconditional** request, so it
  keeps counting exactly one read. Walking the rest of the suite: the matching
  case still gets `304` with an empty body, no `content-type`/`content-length`
  and the same `ETag`; the star/list/weak case still gets `304`; the star-`404`
  case never reaches the comparison. Only the spy case reddens. Uniqueness
  holds.

**Row 3's insulation of the star case — holds, and for the stated reason.**
Approach steps 2-3 put the derivation and the `404`-on-`None` strictly before
`If-None-Match` is read, so a mutation confined to the comparison step is
unreachable for a tenant with no representation: `logo_url=None`, `.svg` and
`.bin` all leave the handler on the `404` path before any comparison exists to
mutate. I also checked row 3's two cited ids do redden (the non-matching case
gets `304` instead of `200`; the replacement case gets a stale `304`) and that
nothing else does — the spy case's second request carries no `If-None-Match`,
so it still reads once and answers `200`.

**Rows 1 and 4 — each cited set is exactly the set that reddens.** Traced
against all twelve named cases plus the existing module:
- Row 1 (constant 64-hex tag, pre-read refusals in place): reddens the
  replacement case (old tag matches the new one → stale `304`), the literal
  digest case, and the UUID case. Green: the two-tenants case (same constant),
  the reversibility case (a constant is not the URL's hex or base64), the shape
  case, the non-matching case (a wrong 64-hex literal still mismatches), the
  star-`404` case and the refusal unit case (refusals intact), the matching
  case, the star/list/weak case, the spy case. Three, exactly as cited.
- Row 4 (digest `tenant.slug`, pre-read refusals in place): reddens the
  replacement case (slug unchanged → stale `304`), the literal digest case, and
  the two-tenants case. The UUID case stays green because two tenants
  necessarily carry different slugs, so a slug digest still yields different
  tags; the star-`404` and refusal cases stay green because the refusals are
  intact. Three, exactly as cited.
I also re-checked rows 2, 5, 7 and 9 as minimum rows: each cited id does
redden, and mutation 9's star-`404` citation is right — a wider suffix set
gives the `.svg` and `.bin` parameters a tag, so `*` matches and they answer
`304`, while the existing `test_a_suffix_outside_the_logo_allowlist_is_404`
(`:184`) stays green because `logo_bytes` still refuses on the unconditional
path.

**The asymmetric enforcement rule, against the full-`FAILED`-list artifact — a
verifier can apply it, and the minimum rows keep their force.** The rule
decomposes into two mechanical checks over the log: for all nine rows,
cited ⊆ `FAILED`; for rows 6 and 8 additionally `FAILED` ⊆ cited (row 8's
green list is the same containment stated the other way). Both are decidable
from a verbatim `FAILED` list, which the artifact now requires for every
mutation. The minimum rows retain the only force that matters for this
repository's failure mode — they still fail the task if a cited test cannot go
red — and because the full list is recorded, an under-listed row now surfaces
in the artifact rather than in a review, which is what finding 4 asked for.
Requiring exhaustiveness on all nine would be worse, not better: it would push
the author back toward the arithmetic that was wrong in round 2.

**Group 3's deliberate mutation exemption — sound, and not self-certifying.**
The mutation that would redden group 3 (the derivation delegating to
`logo_bytes` and returning `None` whenever it does) performs the outbound read
inside the derivation, which runs before the comparison, so it also reddens the
spy case — the author's stated reason for not adding a tenth row is accurate.
The reason this is not the apparatus certifying itself is that group 3 cannot
be vacuously green: it asserts a non-`None` tag **and** `logo_bytes → None` on
the same tenant, and the second half pins the fixture. If the object were in
fact present and readable (the way a group-3 fixture would most plausibly be
wrong), `logo_bytes` returns bytes and the case fails loudly. So group 3's
pass carries evidence of its own setup, which is exactly what the missing
mutation would otherwise have had to supply. Stating the absence in the spec so
QA does not hunt for it is the right handling.

**The twelve names — consistent and fully cited.** I extracted every
`test_[a-z0-9_]+` token from the spec and checked it per section: all twelve
new names appear in §"Test criteria"; all twelve are cited by at least one
table row (row 1 → 3 ids, 2 → 3, 3 → 2, 4 → 3, 5 → 1, 6 → 1, 7 → 1, 8 → 2,
9 → 2; union = all twelve); every mutation cites at least one. §"Files touched"
names the three opacity functions and the deleted
`test_the_route_sets_no_cache_control_and_no_etag`, whose `:134-145` citation
is exact. The three existing cases the spec leans on all exist where it says:
`test_an_unreadable_object_is_404_and_never_a_5xx` (`:194`),
`test_an_object_over_the_two_mib_ceiling_is_refused_rather_than_streamed`
(`:216`), the credential case (`:303-313`). No new name collides with an
existing function, and all follow the module's `test_the_…`/`test_a_…`
convention.

**The citations — both correct.** `public_branding.py` is 149 lines and
`@router.get(` for the logo route is at `:98`, so `98-149` is right in both
places it appears (spec `:16` and §"Files touched"). The R7 grep as specified
— `grep -F 'No ``Cache-Control`` and no ``ETag``'` — matches **one** line,
`:123`, and does **not** match the unrelated `Cache-Control` mention at `:22`
("sets no ``Cache-Control``, by an operator decision taken twice"), which
differs in wording. Executed; one match, as the spec claims.

**R5 judged on its merits, with the author's premise discarded.** There is no
eight-result cap, so "the cap is eight" is not a reason to keep R5 as one line,
and I am not accepting it on that ground. On the merits it stands anyway: R5 is
one sentence stating four concrete, mechanically decidable facts about the same
single property — that the header value is the SHA-256 digest of the stored URL
and nothing else. A verifier who has not read the spec can decide each clause
by inspection of one response plus one `hashlib` call (equals the literal
digest; equal across two tenants sharing a `logo_url`; different when only the
UUID differs; not that URL's hex or base64). None of the clauses is an absence
that could not be present, none requires judgement, and none can be satisfied
vacuously. Splitting it into three would be tidier and is now cost-free, but
the line as written is verifiable, so it is a suggestion and not a finding.

## Suggestions

- Pin **where the quotes are added**. §"What the `ETag` is derived from" gives
  the header value as `'"' + sha256(…).hexdigest() + '"'`, while §"Files
  touched" says the classmethod returns "the opaque tag", so an implementer may
  reasonably put the quoting inside the derivation or in the handler. Row 8
  mutates "the derivation's final line": under the first reading, a literal
  application of that mutation also drops the quotes and reddens
  `test_the_route_sets_no_cache_and_a_strong_etag`'s double-quote assertion.
  §"Test criteria" already resolves it by declaring mutation 8's output
  "double-quoted and `W/`-free", which is why this is not a finding — but one
  clause saying the classmethod returns the inner hex and the handler wraps it
  (or that mutation 8 preserves the quoting) removes the reading entirely.
- Row 8's green list is true **for a 32-character fixture URL**. That is stated,
  and `logo.png`/`logo.jpg` are what every other case in the module uses, but
  the spec never requires `test_the_route_sets_no_cache_and_a_strong_etag` to
  use that filename: `_store(uploads, "logo.webp", …)` is 33 characters, whose
  hex is 66, and the shape check would then redden under mutation 8 — an extra
  `FAILED` line on an exhaustive row. One phrase ("this case stores
  `logo.png`") makes the prediction unconditional.
- Splitting R5 into the derivation result and the opacity result would give each
  of the three new test functions a home in the results list, at no cost — the
  eight-line figure is a convention, not a ceiling.
- The mutation log would read better if each section also recorded the
  must-stay-green list it was checked against, not only the `FAILED` lines, so
  rows 6 and 8's green predictions are affirmed in the artifact rather than
  inferred from an absence.

APPROVED
