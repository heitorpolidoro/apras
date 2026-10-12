# APRAS-124 — spec review (round 2)

Spec: `docs/tasks/APRAS-124-spec.md` (526 lines)
Round 1: `docs/reviews/APRAS-124-spec-review.md`
Reviewed against the working tree at `master` = `99a3d2d`. Nothing was staged,
committed, edited or written to the Meridian board; no production database or
API was touched. No mock was expected and none is requested.

This is a **findings-only** re-review: round 1's five findings, the sections the
author changed to close them, and the unprompted changes the dispatch lists.
Everything round 1 verified (the `sha256(logo_url)` strong validator, slowapi
0.1.10's `exempt_when`/no `deduct_when`, the `public_projects.py`-scoped AST
sweep, `no-cache` agreeing with the title, no migration, the
APRAS-93/APRAS-110 provenance) was not re-litigated.

## Verdict

`NEEDS_REVISION` — five blocking findings, all of them again inside the
verification apparatus, none of them in the design. The design is unchanged
from round 1 and still sound.

The apparatus did grow correctly in shape: the artifact exists, the test names
are fixed, R2's and R5's unfalsifiable halves are gone, and R4 finally has a
mutation. What it did not get is *arithmetic*. Three of the eight rows' "must
redden" lists are provably wrong against the code and the existing test module
— I executed them rather than read them — and two of the rows whose entire
value is the uniqueness of their target cannot be checked from the artifact the
spec requires. That is this repository's fourth recorded mechanism (an
anti-vacuity apparatus satisfied by a checker that cannot fail) reappearing one
level up: the mutation table is now the checker, and three of its predictions
are unsatisfiable, which means the implementer who runs them honestly will be
forced either to doctor the log or to deviate from the spec.

Still not a `NEEDS_SPLIT` candidate: one route, one classmethod, one handler
branch, one test module.

## Blocking Findings

1. **Mutation 8's "must redden" list is false: the strong-`ETag` case's
   64-character check *passes* under mutation 8 for the fixture URL this module
   produces, so the row as written can never be satisfied.** §"Test criteria"
   fixes every case to the real `LocalStorageProvider` the `uploads` fixture
   installs, and that fixture's `_store` helper
   (`backend/tests/test_public_logo_route.py:98-102`) returns
   `/static/uploads/2026/09/{name}`. For `logo.png` and `logo.jpg` that string
   is **exactly 32 characters**, so
   `logo_url.encode("utf-8").hex()` is **exactly 64 characters, all in
   `[0-9a-f]`** — I computed it:
   `2f7374617469632f75706c6f6164732f323032362f30392f6c6f676f2e706e67`, which
   `re.fullmatch(r'[0-9a-f]{64}', …)` accepts. It is also double-quoted and
   carries no `W/`. Every assertion in
   `test_the_route_sets_no_cache_and_a_strong_etag` therefore stays green under
   mutation 8, and the row's demand that it redden the "(the 64-character
   check)" is unmeetable. Two changes: drop that case from row 8's list, and —
   more importantly — **say in §"Test criteria" that the shape check (`64` chars
   of `[0-9a-f]`) proves nothing about the tag being a digest**, since a
   reversible hex encoding of any 32-byte URL satisfies it. That is the whole
   reason assertion 3 of the opacity case is load-bearing, and finding 3 below
   depends on it.

2. **Mutation 6's "— and nothing else" is false against a test that already
   exists in the module, and the row instructs the implementer to treat that as
   proof the apparatus is broken.** `test_the_route_reads_a_private_object_with_the_applications_own_credential`
   (`test_public_logo_route.py:303-313`) asserts `len(private_store) == 1`, i.e.
   it already counts outbound reads, on an **unconditional** request. Mutation 6
   as the spec defines it — "the handler calls `TenantService.logo_bytes` before
   comparing the tag" — cannot be confined to the `304` path, because the
   handler does not yet know which path it is on; so the `200` path reads twice
   and that existing case goes red too. The row then says "any second failure
   means some other case depends on read ordering and R4 is not the only thing
   pinning the saving", which is the wrong conclusion and will be recorded in
   the log as such. Fix by **scoping the mutation to the matching branch**:
   *the handler compares the tag first and, on a match, calls
   `TenantService.logo_bytes`, discards the result, and still answers `304`*.
   I checked that formulation: the `200` path is untouched, every status, header
   and body in the suite is unchanged, the existing credential case keeps
   counting one read, and the only node id that reddens is
   `test_the_304_performs_no_outbound_read_and_the_200_performs_one` — the
   uniqueness the row needs is true of *that* mutation and only that one.

3. **The three assertions of `test_the_tag_is_a_function_of_the_stored_url_and_not_a_copy_of_it`
   share one `pytest` node id, so rows 1, 4 and 8's per-assertion mapping — and
   the spec's own self-test — cannot be checked from the artifact the spec
   requires.** The artifact records "the failing node id or node ids, copied
   from `pytest`'s own `FAILED …` lines". Mutation 4 is supposed to redden
   assertion 1, mutation 1 assertion 2 and mutation 8 assertion 3, and the row
   for mutation 8 adds the self-test "if it reddens assertion 1 or 2 instead of
   3, the opacity half is still vacuous". All four outcomes produce the
   identical `FAILED …::test_the_tag_is_a_function_of_the_stored_url_and_not_a_copy_of_it`
   line, and the first failing assertion aborts the function, so the log cannot
   distinguish them. "Shown red by running that node id alone" does not help:
   running it alone still yields one node id. This is round 1 finding 4 in a new
   costume — R6 resolving against something that cannot discriminate. Fix by
   **splitting the case into three separately named test functions** (or
   `pytest.mark.parametrize` with explicit `ids=`, one per assertion) and citing
   the three node ids individually in rows 1, 4 and 8. If the author prefers to
   keep one function, the artifact spec must instead require the **full pytest
   failure block** (the `assert` line and its `E` lines) for every mutation, not
   just the `FAILED` line — but separate node ids is the better fix, because
   §"Required mutation proofs" is expressed in node ids throughout.

4. **Rows 1, 3 and 4 under-list their targets, while the section's own
   enforcement sentence applies to all eight rows — so the table contradicts
   itself on three of them.** §"Required mutation proofs" states, without
   restriction: "a mutation that reddens a node id other than the one cited is a
   test measuring something other than what it claims." Traced against the
   specified behaviour:
   - **Mutation 1** (constant tag for every tenant): for `logo_url=None` the
     derivation now returns non-`None`, so the handler no longer takes the
     `404`-on-`None` path and `If-None-Match: *` answers `304`. It therefore
     also reddens `test_a_star_is_404_and_never_304_without_a_representation`
     and `test_the_tag_derivation_refuses_exactly_what_logo_bytes_refuses`,
     neither of which is cited.
   - **Mutation 4** (digest `tenant.slug`): same two extra node ids, for the
     same reason — a tenant with no `logo_url` acquires a tag.
   - **Mutation 3** (`304` whenever `If-None-Match` is present, without
     comparing): the star case sends `*`, so it gets `304` instead of `404` and
     `test_a_star_is_404_and_never_304_without_a_representation` reddens; only
     the non-matching case is cited.
   Either complete the three lists, or scope the enforcement sentence to the two
   rows where target uniqueness is the point (6 and 8) and say that the other
   rows' lists are a minimum rather than an exhaustive set. As written, an
   implementer who runs row 1 honestly records two uncited failures and is told
   by the spec that the tests are wrong.

5. **`test_the_tag_derivation_refuses_exactly_what_logo_bytes_refuses`
   contradicts §"One divergence", is implementable two ways, and is the one
   named case no mutation covers.** `logo_bytes` has **four** refusals
   (`tenant_service.py:596-604`: no stored value, disallowed suffix, an
   unreadable object, a file over the ceiling), of which the derivation must
   mirror only the first two — §"One divergence" *depends* on the derivation
   returning a tag for an object that has become unreadable, since that is what
   produces the accepted `304`-where-a-fresh-client-gets-`404`. But the case's
   name says "refuses exactly what `logo_bytes` refuses" and its description
   says it asserts the derivation "agrees with `logo_bytes`' refusal set". Under
   the literal reading the case must fail on an unreadable object; under the
   enumerated reading (`None`, `.svg`, `.bin`) it passes. Pin it: rename to the
   pre-read refusal set, and have the case **also assert the divergence
   positively** — a `logo_url` whose object is missing or oversized yields a
   non-`None` tag while `logo_bytes` yields `None` — so §"One divergence" gains
   the test it currently lacks. Then add the missing mutation (the derivation
   applies a wider suffix set, e.g. accepts `.svg`) and cite this case plus
   `test_a_star_is_404_and_never_304_without_a_representation` on it; at present
   this is the only one of the ten fixed names the table never mentions, and the
   spec gives no reason why not.

## What I executed, and what it found

**Mutation 8's alphabet argument — the reasoning is right, the prediction is
wrong.** The claim that a reversible encoding is the only non-opacity failure
fitting `[0-9a-f]` holds: base64/base64url and the raw URL all carry characters
outside the alphabet, so they are caught by any shape check, and hex is what
survives it. And assertion 3 does redden under mutation 8 **and not under
something else**: assertion 1 (same `logo_url`, different slugs → same tag) and
assertion 2 (URLs differing only in the object UUID → different tags) are both
*satisfied* by a hex encoding of the URL, as is `test_replacing_the_logo_…`, as
is `test_a_matching_if_none_match_…`. The two things that break are assertion 3
and `test_the_tag_is_the_literal_sha256_of_the_stored_url`. What is false is the
third cited target (finding 1), and what is unverifiable is the self-test
(finding 3) — the self-test is exactly the kind of clause this repository has
shipped vacuous before, because it asserts a distinction the artifact cannot
record.

**Mutation 6 — the named spy case does go red, and so does one more.** With the
extra call on the conditional request, "zero calls recorded since that request
began" fails, so the row's primary purpose is served; the mutation is not
decorative. Its uniqueness is not (finding 2): `private_store`'s
`len(…) == 1` at `:311` is a second call-counting assertion on the `200` path,
which no longer holds once the read is unconditional. I also checked the
narrower reading of mutation 6 (read early, keep the `None` check, reuse the
payload) — it changes no asserted status either, because the divergence it would
alter has no test, which is part of finding 5.

**Finding 5's ordering versus R4's spy — no conflict, and the `raise
HTTPException` claim holds in the only sense that matters.** Deriving the tag
before reading `If-None-Match` introduces no storage access: the derivation
reads `tenant.logo_url` and hashes it, so "conditional evaluated before the
outbound read" is untouched and the spy case still pins the saving. The two
orderings compose as `resolve tenant → derive → 404 on None → compare → 304 |
read → 200`, which is what Approach steps 1-4 now say. On the header claim: all
four refusals in `public_branding.py` are `raise HTTPException(status_code=404,
detail="Logo not found")` with no `headers=`, and FastAPI's handler builds a
fresh `JSONResponse` from the exception, so no handler-set header reaches those
`404`s. The author's "under any implementation" is a shade overbroad —
`HTTPException(..., headers={...})` exists — but the operative conclusion is
correct, and the replacement assertion (status is `404`, not `304`) is
falsifiable: mutation 7 flips it. R2's unfalsifiable absence half is genuinely
gone.

**The ten fixed names — internally consistent, with one gap.** The ten names in
§"Test criteria" are exactly the names used in the table; no name appears in one
place and not the other, and every mutation cites at least one real name. The
gaps are in the other direction: `test_the_tag_derivation_refuses_exactly_what_logo_bytes_refuses`
is cited by no mutation (finding 5), and the node ids of the three opacity
assertions do not exist as distinct ids (finding 3). The names follow the
module's `test_the_…`/`test_a_…` convention and none collides with an existing
function in the file.

**R2 and R5 read cold.** This project's board carries no `expected_results`
field on any task — `APRAS-123` and `APRAS-125`, both `done`, do not have the
key either — so §"Expected Results" in the spec is what a verifier sees, and I
judged that text. R2 ("a non-matching `If-None-Match` answers `200` with the
full bytes, and `If-None-Match: *` answers `404` rather than `304` for a tenant
with no `logo_url` and for one whose suffix is outside the logo allowlist") is
mechanically checkable by someone who has not read the spec: two concrete
requests, two concrete statuses, both of which a wrong implementation gets
wrong. R5 is likewise checkable clause by clause — the literal digest, the
two-tenants equality, the UUID-only inequality and the not-hex/not-base64 — and
nothing in it is an absence that cannot be present. Both are closed on the
vacuity axis. Both now bundle several assertions into one line; see Suggestions.

**The unprompted changes.** §Scope's "what 'do not re-fetch the bytes' means"
paragraph is correct and is the right place for round 1's wording note. R7's
grep is real: `grep -n 'No ``Cache-Control`` and no ``ETag``'` matches
`public_branding.py:123` today, so "must match nothing" after the change can
fail, and the paragraph-naming-APRAS-124 half is a second, independent grep.
The Starlette note is accurate against the installed **1.3.1**:
`responses.py::init_headers:66-79` skips `content-length` when
`status_code in (204, 304)` and appends `content-type` only when
`media_type is not None`, so `Response(status_code=304, headers={…})` with no
`media_type` is bodiless and typeless, and the instruction not to pass a
`media_type` is right. The out-of-band-destroyed-object asymmetry is recorded
under §"One divergence" with the reopening condition, as round 1 suggested. The
`98-156` citation is fixed, but **to `99-149`, and the route block actually
starts at line 98** (`@router.get(` at `:98`, `response_class=Response` at
`:99`); the file is 149 lines, so the end is right. The dispatch says the
citation was corrected "in two places" — it now appears only once, at spec
line 16, which is fine.

## Suggestions

- §"Expected Results" R5 now asserts four separate things in one line (literal
  digest, slug-independence, UUID-sensitivity, not-hex-or-base64), and R7 two
  (the grep and `git diff --name-only`). Each clause is verifiable, so I am not
  blocking on shape — but splitting R5 into the derivation result and the
  opacity result would keep the list at eight while making each line a single
  assertion, which is what the result format is for.
- Correct `public_branding.py:99-149` to `98-149`.
- §"Approach" step 3 is the natural home for one more sentence: that the `ETag`
  on a `304` is set from the same derived value as the `200`, which is what
  `test_a_matching_if_none_match_is_a_bodiless_304`'s last assertion checks.
- Once finding 3 is fixed by splitting the opacity case, the three new names
  are worth stating in §"Files touched" alongside the deletion of
  `test_the_route_sets_no_cache_control_and_no_etag` (`:134-145`, confirmed at
  those lines), so the test module's final shape is fully pinned.
- The log file is a good idea, and §"The artifact" is specified well enough to
  check. One addition would make it self-policing: require the log to state,
  per section, the **full `FAILED` list** rather than only for rows 6 and 8.
  The cost is a few lines; the benefit is that findings like 4 above become
  visible in the artifact instead of in a review.

CHANGES REQUESTED
