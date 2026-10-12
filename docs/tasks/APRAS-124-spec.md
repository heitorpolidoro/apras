# APRAS-124 — Cache the public tenant logo route so repeat page loads do not re-fetch the bytes

**No migration. No schema change. No new column, no new table, no new
dependency.** Nothing in this task touches `backend/alembic/`, so landing it on
`master` does not put `migrate.yml`'s `alembic upgrade head` against production
in play. Every input the validator needs is already on the `Tenant` row.

**No mockup.** This task ships no UI and poses no visual question; the one
frontend surface that consumes the route (`TenantHeaderLogo`, APRAS-110) is
unchanged and out of scope. There is nothing for an operator to compare, so
there is no `docs/tasks/APRAS-124-mock.html`.

## Where this comes from

`GET /api/v1/public/tenants/{slug}/logo`
(`backend/app/api/v1/endpoints/public_branding.py:98-149`) serves the logo's
bytes, reading the object with the application's own credential because the
Blob store has private access. It carries `@limiter.limit("30/minute")` per IP
and sets **no `Cache-Control` and no `ETag`**, deliberately, citing APRAS-92 D3.
With no validator of any kind a browser's heuristic freshness lifetime is zero,
so **every full document load re-fetches the bytes** — and APRAS-110 put that
`<img>` in the chrome of every authenticated screen, measured its volume as one
request per full document load per user (plus at most one retry), and
**accepted the cost explicitly** in its §"The cost of the logo bytes", naming
this task as the remedy. The operator filed it when answering APRAS-110's
question 3.

APRAS-93 is the governing precedent and this task **builds on it rather than
around it**. Three of its findings are load-bearing here and are not re-derived:

- **The binding constraint** — "a freshly published bulletin must be visible
  immediately; no mechanism that can serve a stale copy is acceptable" — which
  is why a plain positive `max-age` was rejected there.
- **A limiter is not a cache**: it holds no copy, so it cannot serve stale, and
  under several serverless instances it degrades by *allowing more requests*,
  never by publishing something outdated.
- **§1.6 and §3.2 are the argument *for* this task, not against it.** APRAS-93
  rejected an `ETag` over the *report HTML* because the saving arrives after the
  22 ms render has already been spent and does nothing against a sweeper, and it
  states in as many words that its `(logo_url, ETag)` bullet "says nothing
  whatever about caching `GET /api/v1/public/tenants/{slug}/logo` — that
  question is APRAS-124's and this document neither pre-empts nor declines it",
  adding that de-embedding moved ~140 KiB per render onto a route the browser
  fetches once, "which is precisely what makes caching that route worth doing".

**Nothing below contradicts APRAS-93.** The asymmetry that makes the same
mechanism win here and lose there is stated in §"Why a validator pays on this
route": the logo route's dominant cost is an **outbound fetch that has not
happened yet** when the validator is computed, so a `304` skips it entirely.

## Scope

**In scope: one route, `GET /api/v1/public/tenants/{slug}/logo`.** It gains a
strong `ETag`, honours `If-None-Match` with a bodiless `304`, and sets
`Cache-Control: no-cache`. The tag's derivation lands beside the other logo
rules in `TenantService`.

**What "do not re-fetch the bytes" means, so the title is not read as a
promise this task does not keep.** It means the *body* is not transferred and
the *outbound Blob fetch* does not happen — the cost APRAS-110 priced and
accepted. It does **not** mean the round trip disappears: a revalidating
client still sends one conditional request per use. A mechanism that removes
the round trip is a positive `max-age`, and §"The `Cache-Control` value"
rejects it.

**Out of scope, each for a stated reason:**

- **`GET /api/v1/public/tenants/{slug}/projects/{project_id}/cover`** — see
  §"Whether the cover route is in scope", which decides to exclude it and files
  the consequence.
- **`GET /api/v1/public/tenants/{slug}/projects/report`** — APRAS-93's route.
  Its policy is settled (a limiter, no cache, no `ETag`) and
  `test_public_project_report.py` holds it; nothing here reopens it.
- **`GET /api/v1/public/tenants/{slug}/branding`** — a small JSON body with no
  outbound fetch, so the measured cost this task exists to remove is not
  present. Its `30/minute` is untouched.
- **The frontend.** APRAS-110's `<img>`, its `key`, its `onError` latch and its
  60 s retry all keep working unchanged: a `304` is not an `error` event, and a
  browser-served cached image fires `load`. No file under `frontend/` changes.
- **Server-side caching of the bytes, a CDN, or any shared store.** APRAS-93 §2
  and §3.2 reject all three on the per-instance invalidation argument, and
  nothing here needs them: the only copy this task relies on is the one in the
  client that fetched it, validated on every use.
- **`TenantService.LOGO_MAX_FILE_SIZE` and the upload rules.** Unchanged.

## Decisions

### What the `ETag` is derived from

**The tag is a strong validator over a SHA-256 digest of `tenant.logo_url`.**
Exactly: the response header value is a quoted hex digest,
`'"' + sha256(logo_url.encode("utf-8")).hexdigest() + '"'`, with **no `W/`
prefix** — so the recipe is reproducible by a test against a literal, and the
spec does not leave the implementer a choice to drift on.

Why that input is a stable identity for the octets, from the storage code and
not by assumption: both providers mint the object name from `uuid.uuid4()`
(`storage_service.py:242`, `:834`), the Blob provider sends
`x-add-random-suffix: 0` and deliberately does **not** send `x-allow-overwrite`
so that a collision is an error rather than a silent replace, and
`TenantService.set_logo` always writes a **new** URL and then deletes the old
object. One URL therefore names one immutable byte sequence for that object's
whole life, and a replacement always produces a different URL. That is what
makes the validator **strong** rather than weak: equal tag implies
byte-identical representation, not merely an equivalent one.

Three alternatives, rejected by name:

- **A digest of the payload.** The strongest possible tag, and it defeats the
  purpose: computing it requires the outbound read whose elimination is the
  entire saving. Rejected on cost, not on correctness.
- **`tenant.updated_at`.** It is bumped by `set_logo` and `clear_logo`, but also
  by an unrelated rename or address change (`update_profile`), so every profile
  edit would invalidate a logo that did not change — churn with no correctness
  gain. It is also a timestamp, i.e. a coarser identity than the object it
  stands for.
- **The builtin `hash()`.** Forbidden. It is salted per process
  (`PYTHONHASHSEED`), so two serverless instances would answer different tags
  for the same object and a client would revalidate to a `200` roughly half the
  time. The derivation must be deterministic across processes and instances,
  and a test pins it to a literal digest for a fixed URL precisely so a
  non-deterministic derivation cannot pass.

**Why a digest and not the URL itself.** The stored value carries the Blob store
id, the access label, a tenant-id path segment and the object UUID. Echoing it
in a header to an anonymous caller would publish internal storage structure for
no benefit; a digest of the whole URL is one-way and carries none of it. This is
also the answer to "does the `ETag` leak anything about the stored object": it
reveals one bit of equality between two representations an anonymous caller can
already download in full, and nothing else — not the size, not the type, not the
path.

**When there is no stable identity, there is no tag.** The derivation lives as a
classmethod on `TenantService` beside `logo_bytes`, and it returns `None` for
exactly the inputs `logo_bytes` refuses *before reading* — **two** of its
**four** refusals (`tenant_service.py:596-621`): no `logo_url` (`:611-613`) and
a suffix outside `LOGO_ALLOWED_MIME_TYPES` (`:615-617`). The other two —
`read_file` returning nothing, and a file above `LOGO_MAX_FILE_SIZE`
(`:619-621`) — are **post-read** and the derivation must **not** mirror them:
§"One divergence" depends on an unreadable or oversized object still yielding a
tag. It must apply the **same** suffix
check as `logo_bytes`, not a second copy of it, so the `304` gate cannot drift
from the `404` gate. A response that is not a `200` therefore carries no `ETag`
and no `Cache-Control` at all.

**`If-None-Match: *` is subordinate to the derivation, and this ordering is
mandatory.** RFC 9110 gives `*` the meaning "if the target has **any** current
representation" — so a tenant with no `logo_url`, or with a suffix outside
`LOGO_ALLOWED_MIME_TYPES`, has no representation and `*` must **not** match.
The handler must therefore derive the tag **first** and take the `404` path on
`None` **before** it looks at `If-None-Match` at all; only a non-`None` tag may
then be compared, `*` included. An implementation that short-circuits on `*`
answers a bodiless `304` to a client that holds no copy, for a condominium that
has no logo — a blank header with no way for the client to discover why. This
is not a style note: it is R2's second half, it is mutation 7, and the test that
pins it is named below.

### Whether a `304` is reachable through the rate limiter, and what the limit now protects

**It is reachable, it counts against the limit exactly as a `200` does, and the
`30/minute` stays unchanged.**

This is not a preference; it is what the installed limiter can do. `slowapi`
0.1.x deducts in the decorator *before* the handler runs, and the version in
`backend/.venv` exposes `exempt_when` (evaluated pre-handler, with no access to
a response) and **no `deduct_when`** — verified by reading
`slowapi/extension.py:788-830`. Making a `304` free would mean hand-rolling a
post-response deduction path around `app.core.limiter`, i.e. new limiter
machinery on the one route that least needs it.

**So the limit's meaning is stated rather than changed.** After this task the
`30/minute` per IP protects the **inbound request rate**: a tenant lookup plus a
digest per hit, and — only for a request that does not revalidate or whose tag
does not match — one outbound Blob fetch buffering up to 2 MiB. It is no longer
a one-to-one proxy for paid egress, because a revalidating client's request
costs no egress at all. The practical headroom improves rather than tightens:
APRAS-110 sized the volume at one request per full document load, and that
request is now usually a conditional one, so the ceiling of 30 views/minute per
address is unchanged while the bytes behind it mostly are not sent. The
unmitigated case the limit was sized for — a caller sending no `If-None-Match`
— is byte-for-byte as expensive as before, which is the reason not to relax it.

Raising, lowering or exempting the limit is **explicitly not** part of this
task. The condition that would reopen it: evidence that real clients are
spending their 30 on `304`s and being refused, which nothing available locally
can show.

### The `Cache-Control` value

**`Cache-Control: no-cache`, set on the `200` and on the `304`, and on nothing
else.** `no-cache` does not mean "do not store"; it means "store it, and
revalidate before every reuse". That is the whole decision: the client keeps the
bytes, and each reuse costs one conditional request and **zero** stored-object
bytes.

**Justified against how often a logo changes — and the honest version of that
justification is that the frequency cannot be measured here and does not favour
a TTL anyway.** No dispatched agent may read the production database or call the
production API, so there is no change-frequency figure to quote and none is
invented. Reasoning from the upload path instead: a logo is replaced by a human
on `TenantProfilePage` through `PUT /api/v1/tenant-profile/logo`, an onboarding
action that then sits untouched for months — but it can happen at **any**
moment, and because the public URL is slug-stable (`/tenants/{slug}/logo`), any
positive `max-age` is a window in which a condominium that has just changed its
brand is shown the old one in the header of every screen, with no way to
invalidate it. Low change frequency is what makes `no-cache` *cheap* (nearly
every revalidation answers `304`); it is not an argument for a TTL, because the
cost of being wrong does not shrink with the probability of being wrong when the
window cannot be cut short. This is APRAS-92 D3's and APRAS-93's binding
constraint applied unchanged, and it is why the previous decision is reversed in
only one direction: the route gains a validator, not a freshness lifetime.

Decided alongside it, so the implementer has nothing to improvise:

- **No `Last-Modified`.** One validator only. A second, coarser one invites
  `If-Modified-Since` revalidation with one-second granularity against a column
  that moves for unrelated reasons.
- **No `Expires`, no `max-age`, no `s-maxage`, no `stale-while-revalidate`,
  no `immutable`.** The header value is the single token `no-cache`.
- **No `Vary`.** The response depends on no request header the route negotiates.
- **No `private`.** The bytes are public by decision (APRAS-105); marking them
  private would forbid a shared cache from holding a copy it is already
  revalidating on every use.

### What happens on the first request after a replacement

This is R3, and it is the result most easily satisfied vacuously, so the
behaviour is specified step by step and the test is required to drive the **real
upload route** rather than mutate `logo_url` by hand.

`set_logo` stores the new bytes under a fresh UUID name, writes the new URL to
`tenant.logo_url`, commits, and deletes the old object. So, for a client holding
the pre-replacement tag:

1. It sends `If-None-Match: "<old digest>"`.
2. The handler resolves the tenant, finds `logo_url` now naming the new object,
   and derives a **different** digest.
3. The tags do not match, so the conditional fails: the handler reads the bytes
   and answers **`200`**, with the new payload, the new `ETag`, and
   `Cache-Control: no-cache`.
4. The client's stored copy is replaced. The stale window is **zero
   revalidations wide** — there is no interval in which a `304` could be served
   for the old object, because the only tag the route will ever match is the one
   derived from the URL currently in the column.

A logo *removed* through `DELETE /api/v1/tenant-profile/logo` sets `logo_url` to
`None`, so the derivation returns `None`, the route answers its existing `404`,
and that `404` carries neither header. Removal is immediately visible for the
same reason.

**One divergence, decided and accepted.** The conditional is evaluated **before**
`logo_bytes` performs the outbound read — that ordering *is* the saving. So a
client holding a matching tag receives `304` in a case where a fresh client
would receive `404`: when the stored object has become unreadable (a transient
store failure, a refused read, a file above the ceiling). This is accepted. The
object is immutable, so a matching tag means the client's bytes are the correct
ones; answering `304` lets the header keep showing the right logo where a `404`
would trip APRAS-110's `onError` latch and blank it. The alternative — reading
the bytes before deciding — would spend the egress on every request and leave
nothing to this task.

**The consequence of that divergence, filed rather than fixed: the person who
can repair it is the least likely to see it.** If the stored object is
destroyed out of band while `logo_url` still stands in the column, a **new**
visitor gets `404` and a blank header, while every **returning** visitor — the
operator who manages the condominium included, since they load the app daily
and hold the tag — gets `304` forever and keeps seeing a logo that no longer
exists. Nothing in this task detects that state, and nothing in it should: a
detector is a read on the `304` path, which is the saving. What would reopen
it is evidence that out-of-band destruction happens at all (a support report of
a blank logo that the operator cannot reproduce); the remedy then is a
re-upload, or a separate task that reconciles `logo_url` against the store out
of the request path.

### Whether anything becomes more public, and the `304` oracle

**Nothing becomes private, and nothing an unauthenticated caller can learn
changes in kind.** The route answers the bytes in full to anyone, so a caller
who can obtain a `304` could instead obtain a `200` and compare locally; the
`200`/`304` distinction is a function of data the same caller may download. Slug
enumeration is unchanged — the `404`-vs-`200` distinction that publishes
existence predates this task and is APRAS-74 D3's accepted risk — and a `404`
gains no new header, so the enumeration signal is not sharpened. The `ETag`
itself is a one-way digest and carries no store id, tenant id, object name,
size or type. `UNGUARDED_ROUTES` and the permission catalogue are untouched: the
route still authenticates nobody.

### Whether the cover route is in scope

**Excluded.** The code's own comments are right that
`get_public_project_cover` is the worse amplifier — one report view costs one
logo fetch but *N* cover fetches, uncapped in general since `_hero_html` emits
one `<img>` per project — and that is exactly why it is not bundled here:

1. **It is a different, larger deliverable.** A cover's identity is
   `project.cover_photo_url` per project, the fan-out is per report rather than
   per document load, and `public_projects.py:76` names the real remedy as
   "`Cache-Control` plus server-side resizing" at the 5 MiB cap. Resizing is a
   second subsystem.
2. **Its module carries a module-wide invariant owned by another task.**
   `test_public_project_report.py:402-408` asserts, over the parsed AST, that the
   string `"Cache-Control"` and the string `"ETag"` appear **nowhere** in
   `public_projects.py` — both routes. Caching the cover means weakening that
   module-wide assertion to a per-handler one, inside APRAS-93's test file, in
   the same change as a new behaviour. That is how a strengthening gets validated
   by "it still passes".
3. **The logo route has no such entanglement**: its no-cache assertion is a
   single case in `test_public_logo_route.py` about this one route, and
   inverting it is a local, visible act.

**What excluding it leaves open:** the amplifier the code calls worse than the
logo stays uncached, so a report reload still re-fetches every cover from the
store, bounded only by `300/minute` per IP, and the worst case
`public_projects.py:69-75` records (~1.5 GiB/min of paid egress from one
address) is unchanged by this task.

**Yes, a follow-up task should exist** — "Cache the public obras cover-photo
route, and decide whether to resize on write" — and this spec does not file it;
the operator does. It should state up front that it must re-scope
`test_public_project_report.py`'s module-wide header sweep to the report handler,
with that re-scoping mutation-proven in both directions. The detail that task
will need, carried over so it is not re-derived: the sweep parses
`ast.parse(inspect.getsource(public_projects))` and matches `ast.Constant`
nodes whose value is **exactly** `"Cache-Control"` or `"ETag"`, so a docstring
mentioning the header does not trip it but a `headers={"Cache-Control": …}`
literal does.

## Approach

### Behaviour

1. `GET /api/v1/public/tenants/{slug}/logo` resolves the tenant exactly as
   today (unknown slug or inactive condominium → `404`, unchanged detail).
2. It derives the logo's tag through the new `TenantService` classmethod
   **before reading `If-None-Match`**. `None` → the existing `404` path, with no
   `ETag` and no `Cache-Control`, **whatever `If-None-Match` contains, `*`
   included**.
3. Only with a non-`None` tag does it compare against `If-None-Match`, per
   RFC 9110 weak comparison for a `GET`: the header may be a comma-separated
   list; an entry's optional `W/` prefix is stripped before comparing the opaque
   part; `*` matches, because at this point a representation exists. A match
   answers **`304`** with `ETag` and `Cache-Control: no-cache`, **no body** and
   no `Content-Type`, and performs no outbound read. The `ETag` on the `304` is
   the **same derived value** the `200` would carry — one derivation per
   request, used for both the comparison and the header, never recomputed by a
   second path.

   The bodiless, typeless `304` comes **free** and must not be hand-rolled:
   Starlette 1.3.1's `responses.py::init_headers` skips `content-length` when
   `status_code in (204, 304)` and skips `content-type` when `media_type is
   None` (verified against the installed 1.3.1). So
   `Response(status_code=304, headers={…})` — with **no `media_type` argument**
   and no `content` — already satisfies this step. Passing a `media_type` to
   make the `304` "match" the `200` would put a `Content-Type` on a bodiless
   response and break it.
4. Otherwise it reads the bytes as today and answers `200` with the payload, the
   existing `Content-Type`, plus `ETag` and `Cache-Control: no-cache`. A read
   that comes back empty or refused is still a `404`, never a `5xx`.
5. The `30/minute` per-IP limit is unchanged and applies to every outcome above.

### Files touched

- `backend/app/services/tenant_service.py` — one new classmethod beside
  `logo_bytes` returning the opaque tag or `None`, sharing `logo_bytes`' suffix
  check rather than copying it; its docstring states the immutability argument
  and the `hash()` prohibition.
- `backend/app/api/v1/endpoints/public_branding.py` — the logo handler gains the
  conditional branch and the two headers, inside the route block at `:98-149`;
  the module docstring's and the route
  docstring's "No `Cache-Control` and no `ETag`" paragraphs are rewritten to
  state the new policy, cite this task, and say that the branding route beside
  it is deliberately unchanged. Pinned so a verifier does not have to judge
  prose: that phrase stands in the tree today at **`public_branding.py:123`**
  (the route docstring), which is the line this grep is pinned to, so it fails
  before the change and must be empty after it — `grep -F 'No ``Cache-Control`` and no ``ETag``'
  backend/app/api/v1/endpoints/public_branding.py` must match **nothing**, and
  the file must contain a paragraph naming **APRAS-124**, `no-cache` and the
  strong validator over `logo_url`.
- `backend/tests/test_public_logo_route.py` — `test_the_route_sets_no_cache_control_and_no_etag`
  (`:134-145`) is **deleted and replaced** by the twelve named cases below (it
  now asserts the opposite of the truth; leaving it renamed-but-unchanged is not
  an option), and the module docstring's list of carried properties gains the
  validator. The opacity property is three separate functions —
  `test_the_tag_is_the_same_for_two_tenants_sharing_a_logo_url`,
  `test_the_tag_differs_when_only_the_object_uuid_differs` and
  `test_the_tag_is_not_a_reversible_encoding_of_the_stored_url` — not one
  function with three assertions, for the reason §"Required mutation proofs"
  gives. No existing case in the module is renamed or weakened.
- `docs/tasks/APRAS-124-mutation-log.md` — **new**, the recorded artifact for
  §"Required mutation proofs". Nothing else in `docs/` changes.
- No other file under `backend/app`. No file under `frontend/`. No file under
  `backend/alembic/`.

### Test criteria

All in `backend/tests/test_public_logo_route.py` unless stated, all against the
real `LocalStorageProvider` the `uploads` fixture installs, and all driving the
real route through `TestClient`. **The twelve test function names below are
fixed by this spec, not suggested**, because §"Required mutation proofs" cites
them as `pytest` node ids and R6 is unverifiable if they drift. They follow the
module's existing `test_the_…` convention.

**One property per function, because a node id is the only thing the artifact
records.** A `FAILED …` line names a function, not an assertion, and the first
failing assertion aborts the rest — so a mutation that is supposed to redden
"the third assertion of X" cannot be distinguished in the log from one that
reddens X's first. Every property §"Required mutation proofs" maps a mutation to
therefore gets its own function.

- **`test_a_matching_if_none_match_is_a_bodiless_304`** — read the `ETag` from a
  first `200` and replay it in `If-None-Match`; assert `304`,
  `response.content == b""`, no `content-type` and no `content-length` header,
  and that the `ETag` on the `304` equals the one from the `200`.
- **`test_a_non_matching_if_none_match_is_a_200_with_the_full_bytes`** — a
  plausible wrong digest (64 hex characters, not the real one) answers `200`
  with the full bytes. This is the case that catches a route answering `304`
  unconditionally, which is the vacuity shape this task is most exposed to.
- **`test_a_star_a_list_and_a_weak_prefix_all_match`** — parametrised over
  `*`, `"<wrong>", "<right>"` and `W/"<right>"`; each answers `304` against a
  tenant **that has a readable logo**.
- **`test_a_star_is_404_and_never_304_without_a_representation`** — the
  can-fail half of R2, and the case finding 5 of the round-1 review demanded.
  Parametrised over the two inputs the derivation refuses (`logo_url=None`, and
  a `.svg` and a `.bin` suffix) crossed with the two header forms that carry a
  star (`*` and `"d8e8fca2…", *`): every combination must answer **`404`**, and
  the assertion is on the status being `404` rather than on a header's absence,
  because a `404` built by `raise HTTPException` can carry no handler-set header
  under any implementation. It fails loudly against an implementation that
  honours `*` before checking the derivation for `None`.
- **`test_the_route_sets_no_cache_and_a_strong_etag`** — the replacement for the
  deleted case: `Cache-Control` is exactly the single token `no-cache`; the
  `ETag` is double-quoted, does **not** start with `W/`, and its inner value is
  exactly 64 characters from `[0-9a-f]`; `Last-Modified`, `Expires` and `Vary`
  are absent.

  **The shape check proves nothing about the tag being a digest, and must not be
  read as doing so.** `re.fullmatch(r"[0-9a-f]{64}", …)` accepts any 32-byte
  string's hex, and the `_store` fixture's URL
  (`/static/uploads/2026/09/logo.png`, `test_public_logo_route.py:98-102`) is
  **exactly 32 characters**: its hex is
  `2f7374617469632f75706c6f6164732f323032362f30392f6c6f676f2e706e67`, 64
  characters of `[0-9a-f]`, double-quoted and `W/`-free. So this case stays
  **green** under a plain hex echo of the URL (mutation 8), and it is
  deliberately **not** cited by that row. What this case pins is the header
  policy — one token `no-cache`, a strong quoted tag, no second validator. What
  pins digest-ness is `test_the_tag_is_the_literal_sha256_of_the_stored_url`,
  and what pins one-wayness is
  `test_the_tag_is_not_a_reversible_encoding_of_the_stored_url`.
- **`test_replacing_the_logo_changes_the_etag_and_serves_the_new_bytes`** —
  upload a logo through `PUT /api/v1/tenant-profile/logo` with the existing
  authenticated helpers, read the `ETag`, upload **different** bytes through the
  same route, then replay the old `ETag`: assert `200`, assert the body equals
  the new bytes and not the old, and assert the new `ETag` differs from the old.
  All three assertions are required; the status alone would pass against a route
  that ignores `If-None-Match` entirely.
- **`test_the_304_performs_no_outbound_read_and_the_200_performs_one`** — spy on
  the installed provider's `read_file`. Both outcomes are asserted **in this one
  case**, each anchored to the status it belongs to rather than to request
  order: issue the conditional request, assert `304` **and** zero calls
  recorded since that request began; then issue the unconditional request,
  assert `200` **and** exactly one further call. This is the case that proves
  the saving exists rather than asserting a header, and mutation 6 exists
  solely to prove it can go red.
- **`test_the_tag_is_the_literal_sha256_of_the_stored_url`** — assert the
  `ETag` equals `'"' + hashlib.sha256(url.encode("utf-8")).hexdigest() + '"'`
  for a fixed `logo_url`, with the digest computed in the test from the literal
  URL string. Comparing against a literal, not against a second call to the
  route, is deliberate: a self-comparison would pass for a salted or random tag.
- **The opacity property, as three separate cases** (round-1 finding 3: the
  previous "contains no store id, object name or path segment" could not fail,
  since the tag's alphabet is `[0-9a-f]` and those substrings are not). One
  function each, so rows 1, 4 and 8 can cite a node id that resolves:
  - **`test_the_tag_is_the_same_for_two_tenants_sharing_a_logo_url`** — two
    tenants with **different slugs** but the identical `logo_url` string
    produce the **same** tag. Red under a `tenant.slug`-derived tag.
  - **`test_the_tag_differs_when_only_the_object_uuid_differs`** — two tenants
    whose URLs differ **only in the object UUID** produce **different** tags.
    Red under a constant tag.
  - **`test_the_tag_is_not_a_reversible_encoding_of_the_stored_url`** — the
    header's inner value is neither the URL, nor `url.encode("utf-8").hex()`,
    nor its base64 or base64url encoding (padding stripped). A reversible
    encoding is the only non-opacity failure that *fits* the `[0-9a-f]` alphabet
    the shape check allows, and so the only one worth asserting; the others are
    caught by shape. This case is mutation 8's sole opacity target, and
    mutation 8 must leave the two cases above green.

- **`test_the_tag_derivation_refuses_only_the_two_pre_read_refusals`** — a unit
  case over the new classmethod, renamed from "exactly what `logo_bytes`
  refuses" because that name asserted something §"When there is no stable
  identity" and §"One divergence" both contradict: `logo_bytes` has **four**
  refusals and the derivation mirrors the **two pre-read** ones only. Three
  groups of assertions, and the third is the divergence:
  1. a valid PNG URL yields a **non-`None`** tag, so the agreement below is not
     vacuous;
  2. the two pre-read refusals yield `None` — `logo_url=None`, and a `.svg` and
     a `.bin` suffix — matching `logo_bytes`' `None` on the same three inputs;
  3. the two **post-read** refusals yield a **non-`None`** tag while
     `logo_bytes` on the same tenant yields `None`: a `logo_url` whose object is
     **missing from the store**, and one whose object is **above
     `LOGO_MAX_FILE_SIZE`** (built with the existing `uploads`/`_store`
     helpers, as `test_an_unreadable_object_is_404_and_never_a_5xx` and
     `test_an_object_over_the_two_mib_ceiling_is_refused_rather_than_streamed`
     already do). This is the only test of §"One divergence", and it is what
     makes the two readings of the old name distinguishable: an implementation
     that mirrors all four refusals fails group 3, one that mirrors two passes.

  Mutation 9 reddens groups 2 and 3's suffix half. Group 3 alone is **not**
  mutation-covered: the mutation that would redden it — the derivation calling
  `logo_bytes` and returning `None` whenever it does — also reddens
  `test_the_304_performs_no_outbound_read_and_the_200_performs_one`, since the
  derivation then reads on the `304` path, and the table does not grow a row to
  re-prove a saving mutation 6 already proves. Stated here so a verifier is not
  looking in the log for a proof that is deliberately absent.
- `pytest` passes with `pytest.ini`'s `--cov-fail-under=90`.

### Required mutation proofs

This repository's recorded failure mode is the vacuous check — ten shipped so
far, across five mechanisms, including an absence assertion satisfied by
something that could not be present and an anti-vacuity apparatus satisfied by
a checker that returned `true` unconditionally. This section is that apparatus
for this task, so it is itself specified to be checkable rather than trusted.

**The artifact. Every proof is recorded in
`docs/tasks/APRAS-124-mutation-log.md`, a new file this task delivers**, and
nowhere else — not in a commit body, not in the handover message, not in the
implementer's recollection. QA sees only the expected results and the tree, so
a proof that is not in that file did not happen. The file carries **one section
per numbered mutation below**, and each section carries, verbatim and
unedited:

1. the full `git diff` output for the mutation, as pasted from a run against
   the working tree **before** the suite was invoked (this is what "confirmed
   on disk" means: the diff is non-empty and shows exactly that mutation);
2. the exact `pytest` command that was run;
3. **every** `FAILED …` line the run printed, copied verbatim — e.g.
   `FAILED backend/tests/test_public_logo_route.py::test_a_matching_if_none_match_is_a_bodiless_304`
   — plus the `N failed, M passed` summary line. The **full** list for every
   mutation, not only for the rows that claim uniqueness: that is what makes a
   row's list checkable in both directions, and it is the cheap way an
   under-listed row shows up in the artifact instead of in a review.

Each mutation is applied, diffed, run, recorded, then **reverted** before the
next. **A mutation that reddens none of its cited node ids is a missing test,
not a passing suite** — that rule is absolute and applies to all nine rows.

**Uncited failures are a finding on rows 6 and 8 only.** Those two rows exist
*because* their target is unique, so there the cited list is **exhaustive** and
any extra `FAILED` line means the mutation is not isolating what the row
claims. On the other seven rows the list is a **minimum**: each cited id must
redden, and an additional failure is not by itself a defect — several of these
mutations break more than one property, and the rows are deliberately worded to
narrow the mutation rather than to lengthen the list. Where a narrower mutation
makes a list exactly true, the narrower mutation is the one specified (rows 1,
3 and 4 each keep the two pre-read refusals in place for precisely that
reason).

| # | Mutation | Must redden (node ids in `backend/tests/test_public_logo_route.py`) |
|---|---|---|
| 1 | The derivation returns a fixed 64-hex constant tag for every tenant it returns a tag for, **leaving the two pre-read refusals in place** | `test_replacing_the_logo_changes_the_etag_and_serves_the_new_bytes`, `test_the_tag_is_the_literal_sha256_of_the_stored_url`, `test_the_tag_differs_when_only_the_object_uuid_differs` |
| 2 | The handler ignores `If-None-Match` and always answers `200` | `test_a_matching_if_none_match_is_a_bodiless_304`, `test_a_star_a_list_and_a_weak_prefix_all_match`, `test_the_304_performs_no_outbound_read_and_the_200_performs_one` |
| 3 | The **comparison step** answers `304` whenever `If-None-Match` is present at all, without comparing — the derivation and its `404`-on-`None` untouched, so a tenant without a representation still gets `404` | `test_a_non_matching_if_none_match_is_a_200_with_the_full_bytes`, `test_replacing_the_logo_changes_the_etag_and_serves_the_new_bytes` |
| 4 | The derivation digests `tenant.slug` instead of `tenant.logo_url`, **leaving the two pre-read refusals in place** | `test_replacing_the_logo_changes_the_etag_and_serves_the_new_bytes` (a stale `304`), `test_the_tag_is_the_literal_sha256_of_the_stored_url`, `test_the_tag_is_the_same_for_two_tenants_sharing_a_logo_url` |
| 5 | The handler sets no `Cache-Control` | `test_the_route_sets_no_cache_and_a_strong_etag` |
| 6 | **The handler compares the tag first and, on a match, calls `TenantService.logo_bytes`, discards the result, and still answers `304`** — the `200` path untouched, so every status code, header and body in the suite is unchanged | `test_the_304_performs_no_outbound_read_and_the_200_performs_one` — **and nothing else.** The mutation is scoped to the matching branch so that this is true: an unconditional request still performs exactly one read, which is why the existing `test_the_route_reads_a_private_object_with_the_applications_own_credential` (`:303-313`, `len(private_store) == 1`) stays green. Any absence of failure means the spy case is decorative and the task's reason for existing is unproven |
| 7 | The handler honours `If-None-Match: *` before checking the derivation for `None` | `test_a_star_is_404_and_never_304_without_a_representation` |
| 8 | The derivation's final line returns `tenant.logo_url.encode("utf-8").hex()` instead of the digest — a reversible encoding that still fits the `[0-9a-f]` alphabet — **with both pre-read refusals left in place** | `test_the_tag_is_not_a_reversible_encoding_of_the_stored_url` and `test_the_tag_is_the_literal_sha256_of_the_stored_url` — **and nothing else.** The two other opacity cases must stay **green** (a hex echo is slug-independent and UUID-sensitive), and so must `test_the_route_sets_no_cache_and_a_strong_etag`, whose shape check this mutation satisfies for the 32-character fixture URL — see §"Test criteria". If the uniqueness case or the UUID case reddens instead, the opacity property has been tested by something other than one-wayness |
| 9 | The derivation applies a **wider** suffix set than `logo_bytes` — it accepts `.svg` and `.bin` and returns a tag for them | `test_the_tag_derivation_refuses_only_the_two_pre_read_refusals`, `test_a_star_is_404_and_never_304_without_a_representation` (its `.svg` and `.bin` parameters, which now match `*` and answer `304`) |

**Nine mutations, nine recorded sections. No mutation may remain in the tree
when the task is handed over** — `git diff` over `backend/` at handover shows
the implementation and the tests, and no mutation from this table.

## Expected Results

- [ ] `GET /api/v1/public/tenants/{slug}/logo` answers `200` with a strong
      quoted `ETag` and `Cache-Control: no-cache`, and the same request replayed
      with that value in `If-None-Match` answers `304` with an empty body and no
      `Content-Type`.
- [ ] A non-matching `If-None-Match` answers `200` with the full bytes, and
      `If-None-Match: *` answers `404` rather than `304` for a tenant with no
      `logo_url` and for one whose suffix is outside the logo allowlist.
- [ ] Replacing the logo through `PUT /api/v1/tenant-profile/logo` changes the
      `ETag`, so a client replaying the old one receives `200` and the new bytes.
- [ ] The `304` path performs no outbound storage read while the `200` path
      performs exactly one, asserted by a spy on the installed provider.
- [ ] The `ETag` equals the literal SHA-256 digest of a fixed stored URL, is the
      same for two tenants sharing a `logo_url` and different when only the
      object UUID differs, and is not that URL's hex or base64 encoding.
- [ ] `docs/tasks/APRAS-124-mutation-log.md` records all nine mutations of
      §"Required mutation proofs", each with its `git diff`, its `pytest`
      command and the full list of `FAILED` lines that run printed, every cited
      node id appearing among them, and no mutation remains in the tree.
- [ ] `public_branding.py` no longer contains the phrase "No ``Cache-Control``
      and no ``ETag``" and states the new policy naming APRAS-124, while
      `git diff --name-only` shows no file under `backend/alembic/`,
      `frontend/`, or `public_projects.py`.
- [ ] `pytest` passes in `backend/` with `--cov-fail-under=90`.

## Out of Scope

The cover-photo route and its resizing (§"Whether the cover route is in scope",
which recommends a follow-up task), the obras report route's policy (APRAS-93),
the branding JSON route, the `30/minute` limit's value, any server-side or CDN
cache, the frontend, and the logo upload rules.
