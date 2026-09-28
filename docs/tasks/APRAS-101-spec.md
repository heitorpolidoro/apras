# APRAS-101 — Log why Vercel Blob refused an upload, not just the status code

## Scope

`VercelBlobStorageProvider` records the *status* of a Blob API refusal and
throws the body away. In production that leaves the logo upload failure
undiagnosable:

```
λ PUT /api/v1/tenant-profile/logo
HTTP Request: PUT https://vercel.com/api/blob/?pathname=uploads%2F0531b5c6-…%2F2026%2F09%2Fd73b0a2f-….png "HTTP/1.1 400 Bad Request"
```

The Blob API puts the reason in the response body. `_describe()` reads it only
when it is JSON shaped exactly `{"error": {"code", "message"}}`; any other
shape — a bare `{"message": …}`, a plain-text line, an intermediary's HTML
page — is reduced to the bare status, and nothing is written to the log at all
because `app.core.exception_handlers` does not log (it maps
`StorageUnavailableError` to 503 silently).

This task adds **one server-side WARNING record per refused Blob request**,
carrying the raw response body, bounded and credential-scrubbed. It is a
diagnostic change only: one deploy that turns a `400` into a sentence.

It covers `backend/app/services/storage_service.py` and
`backend/tests/test_storage_blob.py`. It does not cover the route, the
exception handlers, the frontend, or the 400 itself.

## Approach

### Behavior

1. **One record per refused Blob request.** Every point in
   `VercelBlobStorageProvider` that decides a Blob API response is unusable
   emits exactly one `logger.warning` (the module logger already bound at
   `storage_service.logger`) before it raises or returns:
   - `save_file` — `not response.is_success` on the `PUT`;
   - `save_file` via `_url_of` — a 2xx whose body carries no usable `url`
     (today's message says the contract "may have changed" and shows nothing);
   - `delete_file` — `not response.is_success` on the `POST /delete`, which is
     silent today and swallowed into `False`.

   One shared private helper does the emitting, so the format is identical at
   all three sites and there is one place a test asserts against. A transport
   failure (`httpx.HTTPError` inside `_request`) already surfaces its own text
   through `StorageUnavailableError` and gains no record here — there is no
   response to log. Known gap, deliberately out of scope: `delete_file`
   swallows `StorageUnavailableError` into `False`
   (`storage_service.py:487-488`), so a transport-level *delete* failure stays
   completely silent even after this task; only a delete that got an HTTP
   response gains a record.

2. **What the record contains.** The HTTP method, the request URL, the status
   code, an allowlisted set of *response* headers — `x-vercel-error`,
   `x-vercel-error-code`, `x-vercel-id`, `content-type` and `retry-after`,
   each included only when present; all five are diagnostic (the error-code and
   `retry-after` pair identifies a `400` produced by an intermediary rather
   than by the Blob API) and none of them can contain a credential of ours —
   and the response body. Message text in Portuguese, per
   the module's precedent (`LocalStorageProvider.read_file`'s
   `"Disco local: leitura recusada, …"`); the docstrings and comments in
   English, per the repository convention.

3. **The body is bounded — and scrubbed before it is bounded.** A new module
   constant `BLOB_LOG_BODY_MAX_BYTES = 512` bounds the logged body. The order
   of the two operations is **fixed and not left to the implementer**: the
   credential scrub of item 4 runs first, over the **entire** body, and the
   truncation runs on the already-scrubbed result. The reverse order is a leak:
   truncating first can cut an echoed token mid-string, and a usable prefix of
   the read-write credential (say `vercel_blob_rw_Store_s3cr`) then no longer
   matches the full-token pattern, survives the scrub, and reaches Vercel's
   durable log stream. The bound is applied as a byte slice (over the scrubbed
   bytes, not `response.text`, so the bound is exact regardless of encoding),
   decoded with `errors="replace"`. When the body was longer, the logged value
   ends with a truncation marker (` …(truncado)`). 512 bytes comfortably holds
   a Blob API error JSON and stops an intermediary's HTML error page from being
   copied into Vercel's log stream.

4. **The record can never carry a credential.** Only the *response* is logged;
   request headers are never logged, because `_auth_headers` builds
   `authorization: Bearer <BLOB_READ_WRITE_TOKEN>` and that token is the
   store's read-write credential — once in Vercel's log stream it is there
   permanently. As defence in depth, the helper replaces every occurrence of
   the provider's configured token (when set and non-empty) with `***` in the
   body text and in the logged header values *before* the values reach
   `logger.warning`, so an API that echoes a header back cannot leak it.
   Lazy `%s` formatting is preserved: the scrub happens to the argument, not
   to a pre-formatted string. As stated in item 3, the scrub sees the whole
   body; truncation happens only after it.

5. **Nothing a caller observes changes.** The record is emitted **before**
   `_describe()` is called, so a `_describe()` that ever raises cannot suppress
   the diagnostic — the ordering must not depend on the fact that `_payload`
   happens to swallow `ValueError` today. `_describe()` keeps its current
   output, so `StorageUnavailableError.message` is byte-for-byte what it is
   today and the route still answers `503` with the same JSON body and the
   same CORS headers. The raw body goes to the log only — it is not promoted
   into the client-visible error, which also keeps Vercel's internal error
   text out of a browser response.

6. **A success stays silent.** A 2xx upload with a usable `url` emits no new
   WARNING or ERROR record.

### Files touched

- `backend/app/services/storage_service.py` — `BLOB_LOG_BODY_MAX_BYTES`; one
  private refusal-logging helper on `VercelBlobStorageProvider` (plus the
  token-scrub and body-truncation it owns); calls to it at the three refusal
  points in `save_file`, `_url_of` and `delete_file`. `_describe`, `_payload`,
  `_auth_headers`, `_store_id`, `_pathname`, `_request`, the URL and the header
  set are all **unchanged**.
- `backend/tests/test_storage_blob.py` — new cases for the criteria below,
  reusing the existing `http` fixture. No existing case is modified.
- `docs/tasks/APRAS-101-spec.md` — this spec.

`backend/tests/test_lint_hygiene.py` is **expected untouched**: the change
needs no new `# noqa`, and `NOQA_CAP` stays at `70`. If a lint finding appears,
narrow the code rather than raise the cap (the precedent that set this rule).

**Allowed paths (complete set).** Only the three files above may change. In
particular: no change to `backend/app/core/exception_handlers.py`,
`backend/app/core/exceptions.py`, any file under `backend/app/api/`,
`backend/tests/test_lint_hygiene.py`, `backend/alembic/`, anything under
`frontend/`, or any other `docs/` file. The uncommitted work already in the
tree (`docs/suggestions-log.md`, `docs/tasks/APRAS-82-mock.html`,
`APRAS-91-spec.md`, `APRAS-93-spec.md`) belongs to other tasks and is neither
staged nor reverted.

### Test criteria

Every case patches `httpx.Client.request` through the existing `http` fixture;
no test reaches the network.

- A canned `400` whose body is `{"error": {"code": "bad_request", "message":
  "pathname is required"}}` produces exactly one record, at WARNING, from
  `storage_service.__name__`, whose message contains `400`, `PUT`, and the
  body's own text.
- A canned `400` whose body is **not** the `{"error": {...}}` shape (plain
  text, and a `{"message": …}` dict) still puts that body text in the record —
  this is the shape `_describe` drops and the reason the task exists.
- A canned `400` whose response headers include `x-vercel-error: …`,
  `x-vercel-error-code: …` and `retry-after: …` puts all three values in the
  record; a refusal carrying none of the allowlisted headers still produces a
  record, with no placeholder for the absent ones.
- **Credential safety**, driven with a token-shaped secret: the provider is
  built with `vercel_blob_rw_Str01dAbCdEf_s3cr3tv4lu3` and the canned refusal
  body echoes that exact token back. No captured record contains the token
  string, nor its `s3cr3tv4lu3` secret segment; no record contains
  `Bearer`/`authorization`.
- **Credential safety across the truncation boundary** — the case that proves
  the ordering of item 3 rather than merely asserting it: the canned body is
  built so the echoed token *straddles* `BLOB_LOG_BODY_MAX_BYTES`, i.e. padded
  so the token starts before byte 512 and ends after it. **The offset is pinned
  numerically at byte 498** (`STRADDLE_OFFSET` in the test module) rather than
  left as "a few bytes before the bound": without a concrete number an
  implementer can write a technically-conforming case that discriminates
  nothing between the two orderings, which is the whole point of this one. The
  record must contain neither the full token, nor its `s3cr3tv4lu3` segment,
  nor any prefix of the token longer than `vercel_blob_rw_` (in particular no
  `vercel_blob_rw_Str` fragment). At offset 498 only 14 bytes of the token fall
  inside the bound, so what truncate-then-scrub leaks there is exactly
  `vercel_blob_rw` — a fragment shorter than `vercel_blob_rw_Str`. The case
  therefore asserts the absence of **every** prefix of the token from
  `vercel_blob_rw` up, which is strictly stronger than the list above and is
  what makes truncate-then-scrub fail at this offset while it passes the case
  before it.
- **Bound, measured in bytes**: a canned refusal whose body is 10 KiB produces
  a record whose message is shorter than the body and carries the truncation
  marker; the logged body portion is at most `BLOB_LOG_BODY_MAX_BYTES`
  **bytes** — `len(kept.encode("utf-8"))`, never a character count. The spec
  slices bytes and decodes with `errors="replace"`, so a character-count
  assertion would wave through a body that overruns the byte bound whenever it
  contains multibyte text. The case is parametrised over an ASCII filler and a
  multibyte one (`"é"`, where 512 characters are 1024 bytes) so the two
  measures cannot be confused.
- **Silence on success**: a 2xx upload under
  `caplog.at_level("WARNING", logger=storage_service.__name__)` leaves
  `caplog.records == []` (same assertion style as the existing
  `test_every_failure_is_logged_once_and_a_success_is_silent`).
- **A failed delete is no longer silent**: a canned `404` on the delete
  endpoint still returns `False` *and* emits one record naming the status.
- **Unchanged contract**: the existing
  `test_save_file_puts_the_bytes_with_every_documented_header`,
  `test_a_non_2xx_raises_with_the_apis_own_code_and_message` and
  `test_a_non_2xx_whose_body_is_not_json_still_raises_the_mapped_error`,
  `test_a_storage_failure_answers_503_with_a_body_and_the_cors_header`
  (`backend/tests/test_storage_blob.py:554`) and
  `test_delete_file_never_raises_and_reports_failure` pass unmodified, proving
  the header set, the URL, the client-visible message and the 503-with-CORS
  response did not move. These five are the contract; this task may edit the
  file they live in, so they are named in the expected results as
  must-pass-unmodified.
- `cd backend && uv run pytest` passes; `uv run ruff check .` and
  `uv run ruff format --check .` report zero findings.

### The hypotheses this log line exists to confirm or kill (next task's work)

Our implementation was compared against the official `@vercel/blob` **2.6.1**
compiled client (`repertoire_hero/node_modules/@vercel/blob/dist/chunk-CIIQSN42.js`).
Matching already: the base URL (`https://vercel.com/api/blob`, requested as
`/?<params>`), `BLOB_API_VERSION = 12`, the store-id derivation
(`token.split("_")[3]`), and all three of our put headers
(`x-vercel-blob-access`, `x-content-type`, `x-add-random-suffix`) exist in the
official `putOptionHeaderMap`.

The official client sends **three headers we do not**, and these are the
leading suspects for the `400`, recorded here as hypotheses and deliberately
**not changed** by this task:

1. `x-content-length` — sent conditionally by the SDK (upload-progress
   callback, or `shouldUseXContentLength()`);
2. `x-api-blob-request-id`;
3. `x-api-blob-request-attempt`.

The SDK also knows `x-allow-overwrite`, `x-cache-control-max-age` and
`x-if-match`, which we intentionally do not send.

Why the log, and not a local experiment: `vercel env pull` returns
`[SENSITIVE]` for Secret-typed variables, so the real `BLOB_READ_WRITE_TOKEN`
cannot be read locally and the refusal cannot be reproduced off-production.
Logging on the server is the only route to the reason.

## Expected Results

- [ ] A refused Vercel Blob upload emits exactly one WARNING record from the
      `app.services.storage_service` logger containing the HTTP status, the
      method and the Blob API's response body; a test in
      `backend/tests/test_storage_blob.py` canning a `400` with body
      `{"error":{"code":"bad_request","message":"pathname is required"}}`
      asserts all three appear in that single record.
- [ ] A refusal body that is **not** `{"error": {...}}` JSON (plain text, or a
      `{"message": …}` dict) still reaches the log record in its entirety up to
      the 512-byte bound, proven by a test — this is the shape the current code
      reduces to a bare status.
- [ ] No log record can carry the store credential: a test builds the provider
      with token `vercel_blob_rw_Str01dAbCdEf_s3cr3tv4lu3`, cans a refusal
      whose body echoes that token, and asserts neither the token string nor
      its `s3cr3tv4lu3` segment appears in any captured record, and that no
      record contains `authorization` or `Bearer`.
- [ ] The credential cannot survive truncation: a second test cans a refusal
      body padded so the echoed token `vercel_blob_rw_Str01dAbCdEf_s3cr3tv4lu3`
      starts at **byte 498** of the body and so straddles byte 512, and asserts
      no captured record contains the token, its `s3cr3tv4lu3` segment, the
      fragment `vercel_blob_rw_Str`, or any other prefix of the token from
      `vercel_blob_rw` up — proving the scrub ran over the full body before
      truncation rather than after it.
- [ ] The logged body is bounded at 512 bytes by a named module constant
      (`BLOB_LOG_BODY_MAX_BYTES = 512` in
      `backend/app/services/storage_service.py`): a test cans a 10 KiB refusal
      body and asserts the record carries a truncation marker and at most that
      many **bytes** of body, measured as `len(kept.encode("utf-8"))` and
      parametrised over an ASCII and a multibyte filler so a character count
      cannot pass in its place.
- [ ] A successful upload emits no new records: a test performs a 2xx
      `save_file` under `caplog.at_level("WARNING", logger=storage_service.__name__)`
      and asserts `caplog.records == []`.
- [ ] A failed Blob delete still returns `False` and now also emits one WARNING
      record naming the status, proven by a test canning a `404` on
      `/delete`.
- [ ] Nothing a caller observes changed: the Blob `PUT` URL, the store-id
      derivation and the exact header set
      (`authorization`, `x-api-version`, `x-vercel-blob-store-id`,
      `x-vercel-blob-access`, `x-content-type`, `x-add-random-suffix`) are
      untouched, and the pre-existing tests
      `test_save_file_puts_the_bytes_with_every_documented_header`,
      `test_a_non_2xx_raises_with_the_apis_own_code_and_message`,
      `test_a_non_2xx_whose_body_is_not_json_still_raises_the_mapped_error`,
      `test_a_storage_failure_answers_503_with_a_body_and_the_cors_header`
      (`backend/tests/test_storage_blob.py:554` — the one that actually
      exercises what a caller observes: the 503, its body and its CORS header)
      and `test_delete_file_never_raises_and_reports_failure` (the delete
      contract) all pass **unmodified**: `git diff` shows no change to any of
      those five test functions.
- [ ] `cd backend && uv run pytest` passes, `uv run ruff check .` and
      `uv run ruff format --check .` report zero findings, and
      `backend/tests/test_lint_hygiene.py` still declares `NOQA_CAP = 70`
      (unchanged file).
- [ ] The task's own commit (or, before committing, its own staged diff —
      `git diff --stat` restricted to the paths it staged) touches exactly
      three paths: `backend/app/services/storage_service.py`,
      `backend/tests/test_storage_blob.py` and
      `docs/tasks/APRAS-101-spec.md`. The worktree additionally carries
      pre-existing uncommitted work belonging to other tasks — modified
      `docs/suggestions-log.md` and untracked `docs/tasks/APRAS-82-mock.html`,
      `docs/tasks/APRAS-91-spec.md`, `docs/tasks/APRAS-93-spec.md` — which are
      **expected to be present and untouched** by this task and must not be
      counted as violations by a verifier reading `git status`.

## Out of Scope

- **Fixing the 400. Explicitly not attempted here.** No request header is
  added, removed or renamed — in particular not `x-content-length`,
  `x-api-blob-request-id` or `x-api-blob-request-attempt`. The request URL,
  the `x-api-version` value and the store-id derivation are unchanged. Any of
  those would be a guess; this task exists so the follow-up does not have to
  guess.
- Changing the client-visible response: the route keeps its `503`, its JSON
  body and its CORS headers, and `_describe()`'s message is unchanged.
- Adding logging to `app.core.exception_handlers`, to routes, or to any other
  provider or service.
- Switching to the `@vercel/blob` SDK, adding a dependency, or making the
  upload asynchronous.
- Any production access: no production API call with credentials and no
  production database read or write while implementing this.
