# APRAS-96 — Let the Blob provider read its own objects back, so reports can embed the logo

## Why this exists

APRAS-94 (`f24db3f`) made uploads work in production by storing them in Vercel
Blob, but `VercelBlobStorageProvider` is **write-only**: it can `save_file` and
`delete_file` and nothing else. APRAS-92 renders the obras report and wants the
tenant's logo **embedded as a `data:` URI** rather than linked — the operator's
condition was explicit: *"Se possível o logo e as cores virem do sistema e não
chumbados nem de urls públicas."* Its logo ladder (APRAS-92 §B) has three rungs,
and rung 2 — today's plain `<img src="{logo_url}">` — is taken whenever the
provider cannot read its own bytes back. With Blob storage and no read
primitive, rung 2 becomes the path for essentially **every** tenant,
permanently. This task closes it by giving the Blob provider the read side.

## Scope

In scope: a bounded, never-raising read primitive on
`backend/app/services/storage_service.py`'s Blob provider —
`resolve_own_url` (which URLs this store owns) and `read_file` (their bytes,
or `None`) — over the same Vercel Blob REST contract APRAS-94 established, with
`httpx` and no new dependency.

Out of scope, explicitly:

- **Any caller.** `TenantService.logo_data_uri`, the masthead's three rungs and
  the report route are APRAS-92's, and this task adds, changes or removes none
  of them. It only makes rung 1 reachable for a Blob-stored logo.
- **`LocalStorageProvider.read_file` / `resolve_own_url`.** Those are APRAS-92
  §B's. See "Landing order" — whichever task lands second must not restate the
  other's work.
- **Caching, `ETag`/`If-None-Match`, conditional reads, rate limiting.** §5.
- **`resolve_stored_path` and the write/delete paths.** Untouched, byte for
  byte; `tests/test_storage_blob.py`'s existing cases must keep passing
  unmodified.
- **Private or signed Blob access, and reading objects of any other store.**
- **Listing, `head`, `copy`, multipart** and every other SDK verb.

### Landing order (APRAS-92 is not a dependency, in either direction)

APRAS-96 is blocked only by APRAS-94. APRAS-92 is **not yet implemented** and
does not depend on this task, so either may land first. The one shared artefact
is the concrete, `None`-returning `BaseStorageProvider.read_file` default that
APRAS-92 §B describes. Rule: **this task owns that default if it is not already
present, and leaves it exactly as it is if it is.** One deliberate exception to
"leaves it exactly as it is": if APRAS-92 landed the default as
`read_file(url)`, **widening its signature to
`read_file(url, *, max_bytes: int | None = None)` is permitted and preferred**,
because otherwise this task's override is wider than the base it overrides.
Widening a base with a keyword-only defaulted parameter breaks no existing
caller. Nothing in CI would catch the mismatch — there is no `mypy` and no
`pyright` in the backend workflow — so it has to be decided here rather than
discovered. Same for `BaseStorageProvider.resolve_own_url`. Nothing here edits
`project_report_service.py` or `tenant_service.py`.

**Amended during code review:** this originally also said nothing here edits a
`LocalStorageProvider` method. It does, and it has to. Widening the base
`read_file` to `(url, *, max_bytes=None)` without widening the local override
leaves that override **narrower than the base it implements**, so
`local.read_file(url, max_bytes=N)` raises `TypeError` on any deployment
configured for local disk — and nothing in CI would catch it, which is the same
reason the widening was decided here rather than discovered. The override
therefore takes the keyword and **honours** it, because accepting a limit and
ignoring it tells the caller a falsehood. It imposes no default ceiling: with
no keyword it reads the whole file exactly as before, since giving local disk
the Blob provider's 2 MiB bound would be a behaviour change nobody asked for.

## The read contract, and how it was established

Read out of the same compiled `@vercel/blob` 2.6.1 client APRAS-94 read the
write contract from
(`/Users/heitor/workspace/repertoire_hero/node_modules/@vercel/blob/dist`,
strictly read-only), function `get` in `index.js`, plus `constructBlobUrl` in
`chunk-CIIQSN42.js`. The findings, each checkable in that source:

- **A read is a plain `GET` on the object URL itself**, not an API call: `get`
  builds `blobUrl` and calls `fetch(blobUrl, {method: "GET"})`. There is no
  `getApiUrl` on this path, unlike `put` (`/?pathname=`) and `del`
  (`/delete`). So the request goes to the CDN host, **not** to
  `vercel.com/api/blob`, and `x-api-version` / `x-vercel-blob-store-id` have no
  role in it: `BLOB_API_VERSION` is not part of this contract and a read cannot
  be the thing that signals a version bump.
- **The object host is `{storeId}.{access}.blob.vercel-storage.com`**
  (`constructBlobUrl`), with `access` being `public` for everything this
  application writes (`x-vercel-blob-access: public`).
- **`get` validates the hostname suffix `.blob.vercel-storage.com` before
  fetching** and refuses anything else — the same predicate
  `resolve_stored_path` already applies. §3 tightens it.
- **Status handling:** `404` → `null`; any other non-ok → error; `200` →
  the body stream, with `content-length` read from the response header.
- **`get` sends an `authorization: Bearer` header unconditionally**; that it
  *exists for private access* is an **inference**, not something the source
  states — the SDK does not branch on access. What is not an inference is that
  a `public` object is readable with no credential, which is what the decision
  below rests on.

**Decision: fetch the object URL directly, with no `Authorization` header and
no API call.** Direct because that is what the SDK does and because an API
round trip buys nothing for a public object. Credential-free because the
request leaves for a host matched by pattern, and a pattern is a weaker
guarantee than a constant: not sending `BLOB_READ_WRITE_TOKEN` means that even
a future bug in the host check could not leak the write token to whatever host
it let through. Recorded consequence: this provider can only ever read
`public`-access objects, which is all it writes.

## Approach

### 1. Behaviour

`VercelBlobStorageProvider` gains two methods, and the base class gains the
`None`-returning defaults they override (unless APRAS-92 already added them):

- `resolve_own_url(url: str | None) -> str | Path | None` — the URL itself when
  this store minted it, `None` otherwise. Never performs I/O of any kind.
- `read_file(url: str | None, *, max_bytes: int | None = None) -> bytes | None`
  — the object's bytes, or `None`. **Never raises, for any input.**

The keyword is keyword-only with a default, so APRAS-92's ladder keeps calling
`read_file(url)` with one argument exactly as its §B specifies, while a caller
that owns a stricter limit can supply it.

### 2. The bound

Both mechanisms, because either alone is insufficient:

1. The request is issued **streaming** (`httpx.Client.stream`), and
   `Content-Length`, when the response carries one, is compared with the
   ceiling **before a single body byte is read**. Over the ceiling ⇒ the
   response is abandoned and `None` returned.
2. The body is then accumulated from `iter_bytes()` and the read is
   **abandoned the moment the accumulated length exceeds the ceiling** ⇒
   `None`. This is the one that actually holds: `Content-Length` is absent on a
   chunked response and is in any case a claim by the remote, not a fact.
   There is a second reason it is the one that holds: `Content-Length` is the
   **encoded** length, while `iter_bytes()` yields **decoded** bytes, so on a
   `content-encoding: gzip` response the two checks measure different
   quantities and only the streamed one bounds what is actually buffered.

The ceiling is `max_bytes` when supplied, otherwise a module constant
`BLOB_MAX_READ_BYTES = 2 * 1024 * 1024`. 2 MiB because the only consumer is the
logo and `TenantService.LOGO_MAX_FILE_SIZE` is exactly that, so **no logo the
product ever accepted is refused by the default**. The constant's comment must
state the consequence APRAS-92 §B states: base64 inflates by 4/3, so a
worst-case embed adds ≈2.7 MiB to a render of an uncached public route. The
provider does not own that policy — it owns only a safe default and the
honouring of a caller's tighter one.

`BLOB_TIMEOUT` is reused unchanged: a read must be as bounded in time as a
write.

### 3. `resolve_own_url`, and why a hostname suffix is not enough

`resolve_stored_path` tests `host.endswith(BLOB_HOST_SUFFIX)`, which is
sufficient *for delete* — a delete is authenticated with our own token, so
another store's object is unreachable anyway, and APRAS-94's tests pin that
behaviour. It is **not** sufficient for a read reachable anonymously: every
Vercel Blob customer's store shares that suffix, so a crafted value would still
make the server fetch a third party's object. A second reason leaving
`resolve_stored_path` loose is safe: its only caller is `delete_file`, which
takes the pathname it returns and `POST`s to `BLOB_API_BASE_URL` with **our
own** token, so a foreign URL yields at worst a failed delete against our own
store — never an outbound request to a host the attacker named. So
`resolve_own_url` is a separate, strictly tighter predicate and
`resolve_stored_path` is left alone:

- the scheme must be `https`;
- the host is decomposed label by label —
  `labels = (urlparse(url).hostname or "").split(".")` — and **all four** of
  these must hold:
  1. `len(labels) == 5`;
  2. `labels[0] == self._store_id().casefold()` (`urlparse().hostname` is
     already lower-cased, and `tests/test_storage_blob.py` already models the
     URL host as `STORE_ID.lower()`);
  3. `labels[1] in {"public", "private"}` — the access label, neither
     hard-coded to one value nor left free;
  4. `"." + ".".join(labels[2:]) == BLOB_HOST_SUFFIX`, i.e. labels 2..4 are
     exactly `blob.vercel-storage.com`.

  Spelled out this way because the looser phrasings each admit something they
  should not: "the first label is the store id and the rest is the suffix" is
  literally false for the real host (strip `str01dabcdef` from
  `str01dabcdef.public.blob.vercel-storage.com` and the remainder is
  `.public.blob.vercel-storage.com`, not `BLOB_HOST_SUFFIX`), and dropping
  clause 3 or 1 admits `{store}.evil.blob.vercel-storage.com` and
  `{store}.a.b.blob.vercel-storage.com`. The four clauses together make the
  reachable host set a single name per access value;
- the store id comes from `self._store_id()`, whose `StorageUnavailableError`
  for an absent, malformed or non-ASCII token is caught and turned into `None`:
  with no usable token there is no store to own anything;
- no `userinfo`, no port and no credentials in the URL;
- anything else — `None`, **with no HTTP request attempted**.

### 4. SSRF, stated plainly

This primitive is reachable from a public, unauthenticated route (APRAS-92's
obras report), so a value in the database must never be able to make the server
talk to a host of the attacker's choosing. Four things stop it:

1. **`read_file` calls `resolve_own_url` first and returns `None` immediately
   when it rejects.** The set of reachable hosts is therefore a *single* host,
   fixed by the deployment's own token: `{store_id}.*.blob.vercel-storage.com`.
   Not a suffix, not an allowlist — one name.
2. **Redirects are not followed.** The client is built with
   `follow_redirects=False` (also httpx's default, but stated at the call site
   so it is a decision and not an inherited accident). A `3xx` is not a success
   status, so it takes the ordinary non-2xx path and returns `None`. The
   redirect question therefore has no "why it is safe to follow" to answer: the
   server never issues the second request.
3. **No credential leaves the process**, per §"The read contract".
4. **The primitive is not a proxy and not an oracle.** It returns bytes only to
   a caller that will embed them for an object of our own store; every failure
   shape collapses to the same `None`, so a caller cannot distinguish a 404
   from a 403 from a transport error. Residual, recorded rather than implied:
   response *timing* still differs between a rejected URL (no request at all)
   and a fetched one, which is an existence signal for objects of our own
   store whose URLs are already unguessable.

Also on the record: `logo_url` is not client-writable — the only writer is the
validated upload path — so this is defence in depth, exactly as APRAS-92 §B
says of its own containment check.

### 5. Caching — nothing here, and what APRAS-93 should weigh

Every render of APRAS-92's route re-fetches the logo, because D3 declined both
a cache and a rate limit. **At the measured sizes this does not matter enough
to act on here**: real logos are tens of kilobytes, the ceiling is 2 MiB, the
hop is to Vercel's own CDN from a Vercel function, and it is one request
against a render that already performs a `select` over `ConstructionProject`
plus a lazy load of milestones and bulletins per project. The one honest cost
is that it is **synchronous and therefore blocks the event loop**, exactly as
APRAS-94's write does and for the same reason (a synchronous service function
cannot await an offload); the same cheap upgrade applies — `run_in_threadpool`
at the route boundary — and is not done here.

Handed to **APRAS-93**, adopted by neither task:

- the logo read is a second *serial* network hop per render, so a per-tenant
  render cache removes it wholesale rather than needing a cache of its own;
- if only the logo is to be cached, the natural key is `(logo_url, ETag)` and
  the natural mechanism is the conditional `If-None-Match` this task
  deliberately omits — but on Vercel any in-process store is per-instance, the
  same objection D3 already raised;
- APRAS-92 §B's 512 KiB lower embed ceiling is a one-constant alternative that
  needs no store at all, and with this task it is a `max_bytes` argument at the
  call site rather than a provider change.

### 6. Failure behaviour — the enumeration

`read_file` returns `bytes | None` and **never raises**, because a report that
cannot read a logo must render without one; an escaping exception would reach
`ServerErrorMiddleware`, outside `CORSMiddleware`, and reproduce the bodiless,
header-less 500 APRAS-94 §6 exists to prevent — this time on a *public* route.
In the manner of APRAS-94's ER 12, every input and its result:

| input | result |
| --- | --- |
| `None`, `""`, a filesystem path, a relative `/static/uploads/...` value | `None`, no HTTP request |
| a `http://` (non-TLS) blob-shaped URL | `None`, no HTTP request |
| a URL on `cdn.example.com` | `None`, no HTTP request |
| a URL on **another store's** `other.public.blob.vercel-storage.com` | `None`, no HTTP request |
| token absent, malformed or non-ASCII | `None`, no HTTP request |
| `404`, `403`, `500`, or any other non-2xx | `None` |
| a `3xx` redirect | `None` (not followed) |
| `httpx` transport error or timeout | `None` |
| `Content-Length` greater than the ceiling | `None`, **body never read** |
| no `Content-Length`, body exceeding the ceiling mid-stream | `None`, read abandoned |
| `200` with an empty body | `None` (nothing embeddable) |
| `200`, within the ceiling | the bytes |

Every **failure** row above — every row whose result is `None` — is preceded by
a single `logger.warning`
(`logging.getLogger(__name__)`, as `resident_service`/`visitor_service` do)
naming the reason and, where there is one, the status code and the host —
**never the token, and never the URL's query string**. A `None` no one can
diagnose is worse than a linked logo. The success row logs **nothing**: the
only consumer is an uncached public route, and a line per render is noise.

The catch is narrow for the named shapes (`StorageUnavailableError`,
`httpx.HTTPError`) and then closed by one final best-effort
`except Exception:  # noqa: BLE001  # ...` in the shape
`LocalStorageProvider.delete_file` already carries, because "never raises" is a
promise made to an anonymous route and must not depend on having enumerated
every exception `httpx` can produce.

**Measured headroom, so the cap is almost certainly not touched.** Counting
with `tests/test_lint_hygiene.py`'s own regex (`#\s*noqa`) over `app/` +
`tests/`, excluding the module itself exactly as its `_py_files` does, the
count today is **69** and `NOQA_CAP` is **70**. The assertion is
`total <= NOQA_CAP`, so adding this one `BLE001` directive lands on 70 and
still passes. (A plain line-grep reports 70, one of which is
`storage_service.py:162`'s docstring prose "``noqa``" — the regex does not
match it.) So: **do not raise the cap**. Only if the implementation ends up
with enough directives that the measured count actually exceeds `NOQA_CAP` is
the cap raised, by the minimum needed, with the comment paragraph that
module's docstring requires.

### 7. What APRAS-92's ladder needs from this task, and nothing more

Rung 1 becomes reachable for a Blob logo with **no change to APRAS-92's own
plan**: it calls `read_file(url)`, gets bytes, and derives the MIME type from
the stored suffix through its `app.core.uploads` inverse map — which works
unchanged on a Blob URL, because the Blob pathname is
`{uuid4}{canonical_extension(content_type)}` and so ends in exactly the same
`.jpg`/`.png`/`.webp`. Rung 2 stays as the fallback for a genuinely
externally hosted logo. One interface note, advisory to APRAS-92 and not a
requirement of this task: that inverse map must take the suffix from the URL's
*path* rather than from the whole string, since a Blob URL can legitimately
carry a query (`?download=1`).

### Files touched

- `backend/app/services/storage_service.py` — `BLOB_MAX_READ_BYTES`; a module
  logger; `BaseStorageProvider.read_file` and `resolve_own_url` as concrete
  `None`-returning defaults (only if not already present, see "Landing order");
  `VercelBlobStorageProvider.resolve_own_url` and `.read_file`, plus the
  streaming request helper they share. The module docstring gains one paragraph:
  the store was write-only, and why the read side is bounded and silent.
- `backend/tests/test_storage_blob.py` — new cases for the table in §6, with a
  **new** `httpx.Client.stream` fixture (see "Test criteria" for the gating
  rule it must not inherit). No existing case is modified.
- `backend/tests/test_lint_hygiene.py` — **expected untouched**; see §6's
  measured 69/70 headroom. Edited only if the suite actually fails without it.

### Test criteria

Every case patches `httpx` — `httpx.Client.stream` for the read path, as the
module already patches `httpx.Client.request` for the write path and as
`tests/test_mail.py` patches `httpx.AsyncClient.post`. **No test reaches the
network**, and every "no HTTP request" case asserts the patch was never called.

**The `stream` fixture must not be copied from the write fixtures.** The
existing `http` / `forbid_http` fixtures gate on
`url.startswith(BLOB_API_BASE_URL)` and *pass every other URL through to the
real transport*, so that `TestClient` can still reach the ASGI app. A read URL
is a CDN object URL and never starts with `BLOB_API_BASE_URL`, so a fixture
copied verbatim would let the read escape to the live CDN. The new fixture
therefore gates on **`BLOB_HOST_SUFFIX`**: any URL whose host ends with that
suffix is answered from the fake, and a fake that is reached by any *other*
URL fails the test outright rather than passing it through.

- Each row of §6's table, as its own case.
- The oversize cases twice: once with a truthful `Content-Length` (asserting the
  body was never iterated) and once with the header absent and a body that
  overruns (asserting the iteration stopped early rather than buffering it all).
- `max_bytes` smaller than the default refuses a body the default would accept;
  a body one byte under the ceiling is returned in full and compares equal to
  what was served.
- The host check, clause by clause: our own store's URL is read;
  `other.public.blob.vercel-storage.com`, `cdn.example.com`, `http://`, a
  store-id prefix match that is merely a prefix (`{store_id}x.public...`), a
  wrong access label (`{store_id}.evil.blob.vercel-storage.com`) and an extra
  label (`{store_id}.public.a.blob.vercel-storage.com`) are all refused with no
  request.
- The token cases include a **non-ASCII** token (e.g.
  `"vercel_blob_rw_Str01dAbCdÉf_s3cr3t"`), the shape APRAS-94's `_store_id()`
  `isascii()` guard exists for and the one that would otherwise surface as a
  `UnicodeEncodeError` from inside the transport rather than as `None`.
- A `302` to `http://169.254.169.254/latest/meta-data/` returns `None` and the
  second URL is never requested.
- No request carries an `authorization` header.
- The existing APRAS-94 cases pass untouched; backend lint and coverage gates
  stay green.

## Expected Results

Three of the results below compare against **this task's own changed-file
list** — the *APRAS-96 file list*, derived from commit subjects and restated in
full inside each result that uses it, so each is executable on its own:

```sh
git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-96\):' \
  | cut -d' ' -f1 | xargs -r -n1 git show --pretty=format: --name-only | sort -u

  The `-r` is load-bearing, not decoration: GNU `xargs` (Ubuntu, and so CI)
  runs the command **once with no arguments** when its input is empty, and a
  bare `git show --pretty=format: --name-only` then prints HEAD's file list —
  so a grep that matched nothing would silently measure the wrong commit and
  the result would pass or fail for the wrong reason. BSD `xargs` (macOS) does
  not run on empty input but accepts `-r`, so the flag is correct on both.
```

Never `git merge-base HEAD origin/master` and never a bare `git diff --stat`,
which has no comparison base and passes vacuously once the work is committed.

- [ ] `VercelBlobStorageProvider` in
      `backend/app/services/storage_service.py` has a
      `read_file(url, *, max_bytes=None) -> bytes | None` method and a
      `resolve_own_url(url) -> str | Path | None` method, and
      `BaseStorageProvider` declares both as concrete defaults that return
      `None` (no `NotImplementedError`:
      `grep -n "NotImplementedError" backend/app/services/storage_service.py`
      returns nothing).
- [ ] With a fake token `vercel_blob_rw_Str01dAbCdEf_s3cr3trandom` and a patched
      `httpx` returning `200` with body `b"PNGBYTES"`, `read_file` of
      `https://str01dabcdef.public.blob.vercel-storage.com/uploads/x.png`
      returns exactly `b"PNGBYTES"`, and the single request made is a `GET` to
      that same URL — **not** to `vercel.com/api/blob` — carrying **no**
      `authorization` header.
- [ ] `read_file` returns `None`, and the patched `httpx` records **zero
      requests**, for each of: `None`; `""`; `"static/uploads/2026/09/x.png"`;
      `"/static/uploads/2026/09/x.png"`; `"http://str01dabcdef.public.blob.vercel-storage.com/x.png"`;
      `"https://cdn.example.com/x.png"`;
      `"https://other.public.blob.vercel-storage.com/x.png"`;
      `"https://str01dabcdefx.public.blob.vercel-storage.com/x.png"`;
      `"https://str01dabcdef.evil.blob.vercel-storage.com/x.png"`;
      `"https://str01dabcdef.public.a.blob.vercel-storage.com/x.png"`; and the
      same valid URL when the provider's token is `None`, `""`,
      `"vercel_blob_rw"` or the non-ASCII
      `"vercel_blob_rw_Str01dAbCdÉf_s3cr3t"`.
- [ ] `read_file` returns `None` and raises nothing for each of: a `404`; a
      `403`; a `500`; a `200` with a zero-length body; and an `httpx.ConnectError`
      / `httpx.ReadTimeout` raised by the patched client. A test asserts no
      exception type whatsoever escapes — including `StorageUnavailableError`,
      `httpx.HTTPError`, `ValueError` and `KeyError` — for every one of these.
- [ ] Redirects are not followed: with the patched client answering `302` and
      `location: http://169.254.169.254/latest/meta-data/`, `read_file` returns
      `None` and the patched client is called exactly **once**, with the blob
      URL and never with the redirect target.
- [ ] `backend/app/services/storage_service.py` defines
      `BLOB_MAX_READ_BYTES = 2 * 1024 * 1024`, equal to
      `TenantService.LOGO_MAX_FILE_SIZE`, asserted by a test that compares the
      two constants.
- [ ] A response whose `Content-Length` header exceeds the ceiling yields `None`
      **without the body being read**: the test's fake response counts
      `iter_bytes()` invocations and asserts the count is zero.
- [ ] A response with **no** `Content-Length` whose body streams more than the
      ceiling yields `None`, and the test asserts the read was abandoned early —
      the fake body yields chunks from a generator that records how many were
      consumed, and fewer than all of them are.
- [ ] A body of exactly `BLOB_MAX_READ_BYTES` bytes is returned in full and
      compares equal to what was served; a body of `BLOB_MAX_READ_BYTES + 1`
      bytes yields `None`; with `max_bytes=1024`, a 2048-byte body yields `None`
      while the same body is returned when the argument is omitted.
- [ ] `read_file(url)` is callable with exactly one positional argument (the
      signature APRAS-92 §B's ladder uses), proven by a test that calls it that
      way.
- [ ] No new runtime dependency: `backend/pyproject.toml` and `backend/uv.lock`
      are **absent from the *APRAS-96 file list* — the output of `git log --format='%H %s' | grep -E
      '^[0-9a-f]{40} [a-z]+\(APRAS-96\):' | cut -d' ' -f1 | xargs -r -n1 git show
      --pretty=format: --name-only | sort -u`, never `git merge-base` and never a
      bare `git diff --stat`** — and the read path uses `httpx`.
- [ ] No test in `backend/tests` performs a real request to
      `blob.vercel-storage.com` or `vercel.com`; every new case patches `httpx`.
- [ ] The write and delete paths are unchanged: `save_file`, `delete_file` and
      `resolve_stored_path` behave exactly as before. Verified by taking the
      *APRAS-96 file list* — the output of `git log --format='%H %s' | grep -E
      '^[0-9a-f]{40} [a-z]+\(APRAS-96\):' | cut -d' ' -f1 | xargs -r -n1 git show
      --pretty=format: --name-only | sort -u`, never `git merge-base` and never
      a bare `git diff --stat` — then diffing
      `backend/app/services/storage_service.py`
      across exactly those commits, and confirming no hunk touches the bodies of
      those three methods; and by confirming every pre-existing test in
      `backend/tests/test_storage_blob.py` passes with its assertions
      unmodified (the diff of that file over the same commits adds cases only).
- [ ] `backend/app/services/project_report_service.py` and
      `backend/app/services/tenant_service.py` are **not** modified by this
      task: neither path appears in the *APRAS-96 file list* — the output of `git log --format='%H %s' | grep -E
      '^[0-9a-f]{40} [a-z]+\(APRAS-96\):' | cut -d' ' -f1 | xargs -r -n1 git show
      --pretty=format: --name-only | sort -u`, never `git merge-base` and never a
      bare `git diff --stat`.
- [ ] `cd backend && uv run pytest` passes and `uv run ruff check .` reports no
      findings. `NOQA_CAP` in `backend/tests/test_lint_hygiene.py` is expected
      to be **unchanged at 70**: the pre-task count measured with that module's
      own `#\s*noqa` regex over `app/` + `tests/` (excluding the module itself)
      is 69, so the one `# noqa: BLE001` this task adds lands on 70 and the
      `total <= NOQA_CAP` assertion still holds. The cap may be raised **only
      if** `test_lint_hygiene.py` actually fails without the raise, and then by
      the minimum needed, with a comment naming APRAS-96 and the reason. A
      changed `NOQA_CAP` accompanied by a suite that also passes with the
      original value fails this result.

## Out of Scope

- `TenantService.logo_data_uri`, the masthead ladder, the public report route
  and any frontend change — all APRAS-92's.
- `LocalStorageProvider.read_file` / `resolve_own_url` — APRAS-92 §B's.
- Caching, `ETag`/`If-None-Match`, rate limiting (APRAS-93's question).
- Private or signed Blob access; reading any other store's objects; `head`,
  `list`, `copy`, `rename`, multipart.
- Changing `resolve_stored_path`, the write path, or the S3/Cloudinary stubs.
