# APRAS-124 — spec review (round 1)

Spec: `docs/tasks/APRAS-124-spec.md`
Reviewed against the working tree at `master` = `99a3d2d`. No file was staged,
committed or edited; no production database or API was touched.

## What this review executed

Every claim listed in the dispatch was checked against the code and the
installed packages rather than accepted. Findings per claim are in
§"Claim-by-claim verification" below. Five of the six hold; the sixth (R5's
opacity assertion) is where the spec's own anti-vacuity apparatus fails.

## Verdict

`NEEDS_REVISION` — five blocking findings. None of them touches the design's
core, which is sound: the `ETag = sha256(logo_url)` derivation is genuinely
strong against this codebase, `no-cache` is the right value, and the task is
one PR-sized deliverable across three files. All five findings are about the
spec's verification apparatus, which is the part this repository has a ten-case
record of shipping vacuous.

This is not a `NEEDS_SPLIT` candidate: one route, one new classmethod, one
handler branch, one test module.

## Blocking Findings

1. **§"Required mutation proofs" tells the implementer to record "the diff and
   the name of the case that failed" for each of the five mutations but names
   no artifact to record them in, so R6's "with the mutation confirmed on disk
   before the suite ran" is not checkable by anyone who did not watch the
   implementer work.** QA sees only the expected results and the tree. Name the
   destination explicitly — the handover note, a `docs/reviews/APRAS-124-*`
   section, or the commit body — and say that each of the five entries carries
   the `git diff` output and the failing `pytest` node id.

2. **No mutation in the table targets R4, which is the only expected result
   that proves the task's reason for existing.** All five listed mutations are
   about status codes, tag derivation and headers; every one of them would be
   caught by a route that reads the bytes on the `304` path and then discards
   them. The ordering ("the conditional is evaluated before the outbound read")
   is the entire saving, and it is pinned by exactly one case with no
   vacuity proof behind it. Add a sixth row: *the handler calls
   `TenantService.logo_bytes` before comparing the tag, then still answers
   `304`* → must redden the spy case **and nothing else**, since that is the
   only mutation whose uniqueness of target is itself the point.

3. **R5's opacity half is vacuous as written, in precisely this repository's
   recorded shape — an absence assertion satisfied by something that cannot be
   present.** The tag is a lowercase hex digest, alphabet `[0-9a-f]`. The
   fixture URL is `/static/uploads/2026/09/logo.png`
   (`test_public_logo_route.py`'s `_store` helper hardcodes that prefix), and a
   Blob URL's store id, `canonical_extension` suffix and `uuid4` object name
   all contain characters outside that alphabet. So "contains neither the store
   id, nor the object name, nor any path segment of that URL" passes for *any*
   hex digest — including a constant one, and including the
   `sha256(tenant.slug)` mutation the table lists. It cannot fail, so it buys
   nothing. Worse, the wording recorded on the board is weaker still —
   "contains no substring of that URL" — which read literally is false for
   every digest, because single characters of `2026/09` are substrings of it.
   Fix both: drop the opacity half and let the literal-digest assertion carry
   R5 alone, or restate it as something that can go red (e.g. two tenants whose
   URLs differ only in the object UUID must produce different tags, and the
   header must not equal the URL nor its hex/base64 encoding) — and bring the
   board's R5 text into line with §"Test criteria", since the two currently say
   different things and QA reads the board.

4. **The mutation table's "Must redden" column names prose labels — "the
   replacement case", "the header case", "the literal-digest case" — and
   §"Test criteria" fixes no test function names, so R6's "reddens a *named*
   case" has nothing to resolve against.** A mutation that reddens some other
   case would satisfy the result as written. Fix the test function names in
   §"Test criteria" (the module already uses long `test_the_…` names) and refer
   to those names in the table, so verifying R6 is `pytest <node id>` and not
   an interpretation.

5. **`If-None-Match: *` against a tenant that has no logo, or whose `logo_url`
   suffix is outside `LOGO_ALLOWED_MIME_TYPES`, is unspecified, and the
   expected result that should cover it cannot fail.** §"Approach" step 3 says
   `*` "matches any existing representation" and §"Decisions" says the
   derivation returns `None` for those two inputs, but no case asserts the
   interaction, and an implementer who evaluates `*` before testing the tag for
   `None` ships a `304` where the route must answer `404` — a bodiless `304` to
   a client that has no copy, on a tenant with no logo at all. R2's second half
   does not catch it: all four refusals are `raise HTTPException`, and FastAPI
   builds a fresh `JSONResponse` for those, so no handler-set header can reach
   a `404` under *any* implementation — "every `404` shape carries neither
   `ETag` nor `Cache-Control`" is unfalsifiable, the same absence shape as
   finding 3. Replace it with the 404-adjacent assertion that *can* fail:
   `If-None-Match: *` and a list containing `*` must answer `404`, not `304`,
   for no `logo_url` and for a `.svg`/`.bin` suffix — and add the matching
   mutation (*the handler honours `*` before checking the derivation for
   `None`*) to the table.

## Claim-by-claim verification

**The `ETag` is `sha256(tenant.logo_url)` and strong — HOLDS, and more
strongly than the spec argues.** `storage_service.py:242` (local) and `:834`
(Blob `_pathname`) both mint the object name from `uuid.uuid4()`, as cited. The
Blob `PUT` at `:508-511` sends `"x-add-random-suffix": "0"` and does not send
`x-allow-overwrite`, with a comment saying the omission is deliberate so a
collision errors; a non-success response raises `StorageUnavailableError`.
`TenantService.set_logo` (`:757-767`) captures `previous`, writes a new URL,
commits, then deletes the old object. I also checked the claim the spec does
*not* make, which is the one that would break it: **nothing else writes
`logo_url`.** A repository-wide grep finds writes only in `set_logo:761` and
`clear_logo:777`; `TenantProfileRead:118` and `PublicTenantBrandingRead:147`
are read schemas, and no update schema carries the field. No path can rewrite
the bytes behind an unchanged URL, so the strong validator is correct and R3 is
sound. (A legacy externally-hosted `logo_url`, which `_delete_stored_logo`'s
APRAS-61 comment implies may exist, would get a derived tag — but
`read_file`/`resolve_own_url` never returns bytes for one, so no client can
ever hold that tag. Harmless.)

**slowapi has `exempt_when` and no `deduct_when` — HOLDS.** Installed version
is **slowapi 0.1.10** (`backend/.venv/lib/python3.13/site-packages/slowapi-0.1.10.dist-info`).
`extension.py` mentions `exempt_when` at `:661, :680, :694, :795, :812, :823,
:834, :853` and `deduct_when` **nowhere**; the cited `:788-830` is the `limit`
signature and docstring region, as described, and `:490`'s
`_exempt_when_takes_request` confirms it is evaluated pre-handler with a request
at most. The "forced, not chosen" reasoning stands and R4's reconciliation needs
no redeciding. `app/core/limiter.py` is `Limiter(key_func=get_remote_address)`
with `headers_enabled` left default-off, so the limiter injects no headers into a
`304` either.

**`test_public_project_report.py:402-408`'s AST sweep — HOLDS, and the spec's
file-path wording is correct where the dispatch suspected drift.** The tree is
`ast.parse(inspect.getsource(public_projects))` (`:390`), and the header half
collects `ast.Constant` nodes whose value is **exactly** `"Cache-Control"` or
`"ETag"`, module-wide within `public_projects.py` only. The logo route lives in
`public_branding.py` (`@router.get("/tenants/{slug}/logo")` at `:99`), which
that test never parses, so **it would not go red for this task** — the
exclusion of the cover route is a genuine scoping decision, not an unaddressed
problem. The exact-equality match also means the cover follow-up really would
have to re-scope it, since a docstring that merely mentions the header does not
trip it but a `headers={"Cache-Control": …}` literal does. The spec's §3 claim
that the logo module has no such entanglement checks out too: the only existing
assertion is `test_the_route_sets_no_cache_control_and_no_etag`
(`test_public_logo_route.py:134-145`), a single behavioural case over this one
route, and `test_public_branding.py:162`'s AST walk over `public_branding.py`
is about colour derivation, not headers.

**The conditional is evaluated before the storage read, and the `304`/`404`
divergence — argument HOLDS; one consequence is unrecorded.** The reasoning is
correct: the object is immutable, so a matching tag means the client's bytes are
the right ones, and a `304` is a better answer than a `404` that trips
APRAS-110's `onError` latch. The ordering is not left to drift, because R4's spy
forces it. What the spec does not record is the observability asymmetry: if the
stored object is destroyed out of band while `logo_url` stands, a *new* visitor
gets `404` and a blank header while every *returning* visitor — the operator
included — gets `304` forever and sees a logo that no longer exists. The person
able to fix it is the one least likely to notice. That is a consequence to file,
not a reason to change the decision. Suggestion, not blocking.

**`Cache-Control: no-cache` with no TTL — HOLDS, and the title and the design do
agree.** `no-cache` means store-and-revalidate, so a repeat page load transfers
**zero** stored-object bytes and the `304` is bodiless: "repeat page loads do not
re-fetch the bytes" is literally achieved. What it does not eliminate is the
round trip — and the cost APRAS-110 priced and accepted was the *outbound Blob
fetch*, not the inbound request, so the design targets exactly the cost the task
exists to remove. §"The `Cache-Control` value" states this in as many words
("each reuse costs one conditional request and **zero** stored-object bytes"),
so the spec already says which reading wins. No finding; one wording suggestion
below.

**No migration — CONFIRMED.** Nothing in §"Files touched" is under
`backend/alembic/`; the derivation reads `tenant.logo_url`, an existing column
(`models/tenant.py:147`), and adds no field, index or dependency.
`pytest.ini:4` is `--cov=app --cov-fail-under=90`, so R8 quotes the real gate.

**Provenance — CONFIRMED, no contradiction with APRAS-93 or APRAS-110.**
APRAS-93's spec at `:1238-1247` contains the sentence the spec quotes verbatim,
including "that question is APRAS-124's and this document neither pre-empts nor
declines it", and `:1507` independently names APRAS-124 as the home for caching
this route. APRAS-110 §"The cost of the logo bytes" (`:91-116`) prices the route
at one request per full document load, records the `no Cache-Control / no ETag`
decision and accepts the cost explicitly. This task reverses that in one
direction only (a validator, not a freshness lifetime), which is consistent with
both documents' binding constraint. `public_projects.py:68-77` does say the real
remedy is "`Cache-Control` plus server-side resizing" and does record the
~1.5 GiB/min worst case, as §"Whether the cover route is in scope" reports.

**Could not check:** nothing. Every claim above was resolvable from the tree and
the venv. No production data was needed and none was accessed.

## One thing I checked that the spec leaves to luck and gets right

A `304` must carry no `Content-Length` and no `Content-Type`. Starlette **1.3.1**
`responses.py::init_headers` skips `content-length` when
`status_code in (204, 304)` and skips `content-type` when `media_type is None`,
so `Response(status_code=304, headers={…})` satisfies §"Approach" step 3 with no
special handling. Worth stating in the spec so the implementer does not invent
a `media_type` and break it.

## Suggestions

- Add the Starlette note above to §"Approach" step 3: the bodiless, typeless
  `304` comes free from `Response(status_code=304, …)` with no `media_type`,
  verified against the installed 1.3.1.
- Record the observability asymmetry of the accepted `304`-over-`404`
  divergence (operator sees the cached logo, new visitors see the blank), and
  the condition that would reopen it.
- Pin R7's "docstrings state the new policy" to something a verifier can grep:
  the phrase "No ``Cache-Control`` and no ``ETag``" no longer appears in
  `public_branding.py`, and a paragraph naming APRAS-124, `no-cache` and the
  strong validator does. As written it is a judgement call on a board card.
- Have the spy case assert both status codes in the same case (a `304` then a
  `200`), so "zero calls" and "exactly one call" are anchored to the outcomes
  they claim to be about rather than to request order.
- `public_branding.py:98-156` is cited twice; the file is 149 lines and the
  handler is `98-149`. Also worth one sentence in §Scope saying that "do not
  re-fetch the bytes" means the body and not the round trip, so a reader of the
  title alone does not expect a `max-age`.
- The follow-up the spec recommends ("Cache the public obras cover-photo route,
  and decide whether to resize on write") is correctly left for the operator to
  file; the AST sweep's exact-string matching, confirmed above, is the detail
  that task will need and is worth carrying over verbatim.

CHANGES REQUESTED
