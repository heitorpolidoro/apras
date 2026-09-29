# APRAS-104 — Upload an obra cover photo instead of pasting a URL

## Scope

Replace the "URL da Foto de Capa" text field in the internal obra form with a
file picker, store the chosen image through the configured storage provider,
and keep the obras report rendering that image for a public reader.

Covered:

- a tenant-scoped upload route (`PUT /projects/{id}/cover-photo`) and a clear
  route (`DELETE /projects/{id}/cover-photo`) for one project's cover photo;
- the storage write, the validation that precedes it and the removal of the
  object the project pointed at before;
- a public, unauthenticated route that serves the cover photo's **bytes**, and
  one derived read field that tells every renderer which URL to load;
- the internal obra form and the obra card;
- the report hero's `<img>`/placeholder choice.

Not covered: the progress-bulletin photo pipeline (`POST /uploads/photo`,
`ProjectUpdate.photos_json`) is untouched; no image resizing, cropping,
thumbnailing or EXIF stripping; no change to the Blob store's access mode; no
change to the **report** route's rate-limit or cache policy (APRAS-92 D3, whose
revisit **APRAS-93** owns, named at `public_projects.py:41`) — the new cover
route carries a limiter of its own, on the logo route's model and not the report
route's, see §C; no `Cache-Control` or `ETag` on the new route either; no
migration of the cover photos that already exist as third-party URLs; no
gallery — a project still has exactly one cover photo.

## Approach

### A. How the cover photo reaches a public reader (ER2, ER3, ER4, ER5 together)

This is the constraint everything else follows from. The Blob store is
configured with **private** access (`storage_service.BLOB_STORE_ACCESS`), so
no URL the provider returns is fetchable by a browser — not by an anonymous
reader of `/c/<slug>/obras`, and not by a signed-in administrator either,
because an `<img src>` carries no credential of ours in either case.

The answer is APRAS-105's, reused without variation: **the stored column is
storage truth, and a route of ours is the display source.**

- `ConstructionProject.cover_photo_url` stores exactly the URL
  `upload_storage_provider().save_file(...)` returned. ER2 is satisfied
  literally, and nothing in this task writes a different kind of value into
  that column.
- A new unauthenticated route serves the bytes:
  `GET /api/v1/public/tenants/{slug}/projects/{project_id}/cover`. It reads
  the object with the application's own credential through
  `provider.read_file(url, max_bytes=media_service.MAX_FILE_SIZE)` — the
  ceiling is **stated by this caller**, see §C — and answers **only** bytes,
  never the store token and never the upstream Blob URL.
- Every renderer — the report hero and the internal obra card — points at that
  route, never at `cover_photo_url`. For the report the URL must be
  **absolute** (`core/urls.py`), because `PublicObrasReportPage` injects the
  document into an `<iframe srcDoc>` whose relative URLs resolve against the
  frontend's origin.

Two consequences to state rather than gloss:

1. **ER2's wording holds, but `cover_photo_url` is not a display URL.** A
   reviewer checking ER2 should compare the column against what `save_file`
   returned; a reviewer checking ER5 should look at the `<img src>`, which is
   our route. This is the same split `tenant.logo_url` has carried since
   APRAS-105.
2. **Third-party URLs keep working, and that branch is not a migration
   remnant.** Rows whose `cover_photo_url` is a CDN or Drive URL exist today,
   and a provider cannot read them back
   (`resolve_stored_path` answers `None` for a value it did not mint). So the
   display URL is chosen by one rung, in one function: if the provider owns the
   stored value, the display URL is our public route; otherwise it is the
   stored value verbatim, which is what renders today. No open redirect is
   introduced — our route never forwards to a foreign host, it 404s for a value
   it cannot read.

   That second branch is a **live write path, not a tail to be retired**:
   `ProjectUpdateSchema` keeps `cover_photo_url` (§B), and
   `backend/scripts/sync_obras_from_drive.py` writes third-party URLs into the
   column on every run. A future reader weighing the branch's removal has to
   retire that writer first; deleting the branch on the assumption that only
   historical rows reach it would break the Drive sync's obras.

### B. Behavior

**Write.** `PUT /api/v1/projects/{id}/cover-photo`, multipart, one `file`
field, answers the updated `ProjectRead`. Guarded by the existing
`projects:update` permission — the same gate that authorises `PUT
/projects/{id}`, which could already set this column. No new catalogue string,
so no permission-catalogue change; two new `ROUTE_PERMISSIONS` entries.
`DELETE /api/v1/projects/{id}/cover-photo` clears the column and removes the
object, idempotently, under the same permission. The delete route is in scope
because the text field being removed was the only way to blank a cover, and
`ProjectService.update_project` skips `None` values, so `PUT /projects/{id}`
cannot clear the column at all.

**Validation, all of it before any write.** Size, then declared MIME type, then
Pillow decodability, in that order, exactly as `TenantService.set_logo`
sequences them. A refusal writes no object and no column.

**Order of operations on replace.** New object written → column set → commit →
previous object deleted, best effort. See §C.

**Public read.** The new route resolves the tenant by slug, refuses an unknown
or inactive one, establishes `tenant_context.acting_tenant_scope` around the
project lookup — the third caller of that helper, and it needs the review
comment its docstring demands — and answers **404 for everything that is not a
readable cover photo**, in one shape: unknown slug, inactive tenant, project
not in that tenant, no `cover_photo_url`, a suffix outside the accepted image
types, a provider that does not own the value, and a read that comes back
empty. A storage failure is deliberately not a 5xx. It carries
**`@limiter.limit("300/minute")`** — the logo route's decision at the cover
route's fan-out, arithmetic in §C — and no `Cache-Control` and no `ETag`, which
is the one thing it does take from the report route. The path cannot shadow the report route even though both live under
`/tenants/{slug}/projects/…`: `…/projects/report` is two segments after the
slug and `…/projects/{project_id}/cover` is three, so no literal/parameter
ambiguity arises and no declaration-order constraint applies between them
(unlike `GET /projects/{id}` in the internal module, which the new
`/{id}/cover-photo` routes must be declared around).

**Read field.** `ProjectRead` gains one derived, read-only
`cover_photo_display_url: str | None`, built by the rung in §A.2 — the same
shape `TenantProfileRead.theme` has: derived on read, never stored, never
accepted on a write. `ProjectCreate`/`ProjectUpdateSchema` keep
`cover_photo_url` (the Drive sync and existing integrations write it); the UI
simply stops sending it.

**What the detail route answers.** Every `ProjectRead` a route answers carries
the derived URL, the detail route included: `ProjectDetailRead` inherits
`cover_photo_display_url` from `ProjectRead`, but it is constructed inside
`ProjectService.get_project_detail`, which the `_project_read(project, tenant)`
helper in `projects.py` does not pass through. So `get_project_detail` must fill
the field with the same rung, and `GET /api/v1/projects/{id}` answers the same
value the list route does for the same project — not `null`. A test asserts
that explicitly, because inheriting the field is exactly the shape that ships a
permanent `null`.

**UI.** The obra form's URL input is replaced by a cover-photo control: a
preview when there is one, a "Escolher foto" button, a "Remover" action, and an
inline message when the picked file breaks a rule. The picked file is held in
form state and uploaded **after** the project is saved, so an obra can still
get its cover at creation time — which the URL field allowed and a
`PUT /projects/{id}/cover-photo` alone could not, since a project that does not
exist has no id.

**A successful create leaves the modal in edit mode, before the cover step
runs.** This is not cosmetic: if the create succeeded and only the cover upload
failed, a modal still in create mode would answer the operator's natural next
action — press Save again — with a second `POST /projects`, i.e. a duplicate
obra. So the sequence is: `POST /projects` → on 2xx, adopt the returned project
id and switch the modal to editing that project (and refresh the list, so the
new obra is visible behind the modal) → then `PUT /{id}/cover-photo`. If the
cover step fails, the modal stays open on that obra reporting the cover error —
it never silently swallows it — and pressing Save again re-issues a `PUT
/projects/{id}` plus the cover upload, never a second create. Closing the modal
at that point leaves a coverless obra that already exists in the list and whose
cover can be set from its edit screen; nothing is lost and nothing is
duplicated.

Type and size are checked in the browser first, so a refused file never reaches
the network, and the same constants are the server's — see §C.

### C. Decisions

**ER7 — the orphan. Delete the previous object, after the column is
committed.** Reason: a cover photo is replaced from a screen, repeatedly, and
every superseded object would otherwise accumulate in a private store nobody
browses; the logo took the same decision for the same reason and
`_delete_stored_logo` is the code to mirror. The ordering is deliberate and is
the failure mode being chosen: write the new object, set the column, commit,
then delete. If the delete fails, the store keeps one unreferenced object —
cheap, harmless to every reader, and logged by our own helper rather than left
silent (next paragraph). Delete-first would invert that
into a project pointing at an object that no longer exists, which is a broken
image on a public page. `delete_file` already swallows every failure, so a
failed cleanup cannot fail the request. Only a value the provider minted is
deleted: `resolve_stored_path` answers `None` for a pasted third-party URL, and
somebody else's file is left alone (APRAS-61).

**`_delete_stored_cover` logs when `delete_file` answers `False`.** The previous
paragraph's "cheap and invisible" is only acceptable while the orphan is
*recorded somewhere*, and the storage layer does not record it uniformly:
`VercelBlobStorageProvider.delete_file` calls `_log_refusal` on a refusing store
(`storage_service.py:549`), but `LocalStorageProvider.delete_file` is
`except Exception: return False` with **no log at all**
(`storage_service.py:257-264`), and every caller discards the bool. On local
disk a genuine failure is therefore entirely invisible today. The fix belongs in
this task's own helper, not in the shared provider: one `logger.warning` naming
the project id and the undeleted value when `delete_file` returns `False`.
Chosen over "correct the claim and move on" because the swallowed delete is the
whole justification for the write-then-delete ordering, and over "make
`LocalStorageProvider` log" because that changes behaviour shared with the logo
and the bulletin photos, which is a different task's blast radius.

**Size and type limits: reuse `media_service.MAX_FILE_SIZE` (5 MiB) and
`media_service.ALLOWED_MIME_TYPES` (`image/jpeg`, `image/png`, `image/webp`),
and on the frontend the constants that already mirror them in
`src/api/uploads.ts` (`UPLOAD_MAX_FILE_SIZE_BYTES`,
`UPLOAD_ALLOWED_MIME_TYPES`, `UPLOAD_ACCEPT`).** No new number, no new
two-sided pin. It is the logo's 2 MiB cap that is the exception, and its own
comment says why — "the logo is embedded in **every** printed document". A
cover photo is a project photo, governed by the rules that already accept the
bulletin photos rendered in this same report. The refusals reuse
`PhotoFileTooLargeError` and `InvalidPhotoFormatError`, whose messages already
name the rule broken ("excede o limite máximo permitido de 5MB", "Formatos
aceitos: JPEG, PNG, WebP") and which map to **400**, the media pipeline's
published contract. `image/svg+xml` stays out, for APRAS-61 D2's reason: an SVG
is active content embedded in a report a browser renders.

**The read ceiling is stated by the caller: `read_file(url,
max_bytes=media_service.MAX_FILE_SIZE)`.** Accepting 5 MiB on upload and reading
with the provider default would ship a route that returns 200 on upload and 404
forever after: `storage_service.BLOB_MAX_READ_BYTES` is `2 * 1024 * 1024`
(`storage_service.py:387`) and its comment says that default is safe *because*
it equals `TenantService.LOGO_MAX_FILE_SIZE` — an assumption this caller breaks.
A 3 MiB cover would upload fine and then be refused by
`VercelBlobStorageProvider.read_file`, for every reader, silently as a 404.
`TenantService.logo_bytes` passes its ceiling explicitly for exactly this reason
(`tenant_service.py:619`) and this route does the same.

No test can catch this incidentally, which is why ER4 is a named result rather
than a note: `LocalStorageProvider.read_file` has **no implicit ceiling** — its
docstring says so, and with `max_bytes=None` it reads the whole file
(`storage_service.py:318,334`) — so a suite running on the local provider is
green at any cover size, and only production's Blob provider refuses. That is
the same green-suite/production-failure shape APRAS-105 already paid for. The
two ER4 tests are pinned against `MAX_FILE_SIZE` itself, never a retyped
literal: at `MAX_FILE_SIZE` bytes the route still answers 200 with the bytes; at
`MAX_FILE_SIZE + 1` the read is refused and the route answers 404.

**Of those two, the over-ceiling case is the load-bearing one, and it is
load-bearing on the local provider** — which is worth stating because the
opposite was believed at one point in this task's review. `LocalStorageProvider`
does not merely honour a ceiling that is passed; it applies **none** when one is
not. `read_file` branches on `max_bytes is None` and then `return
path.read_bytes()`, the whole file, no bound at all
(`storage_service.py:334-335`, and its docstring says so in a paragraph headed
"No implicit ceiling"). So an implementation that omits the keyword reads the
over-ceiling object in full and serves it **200**, and the test asserting 404
goes red on the local provider, in CI, with no Blob store involved. That test
alone catches the omission this whole decision exists to prevent.

The provider spy ER4 also requires has a **narrower** value than an earlier
draft of this spec claimed, and the narrower claim is the true one. The two size
cases between them catch every wrong *number*, in both directions: a retyped
`2 * 1024 * 1024` makes `read_file` return `None` for the at-ceiling 5 MiB
object, so the route answers 404 and the test asserting **200** goes red; a
too-generous ceiling serves the over-ceiling object and the test asserting
**404** goes red. So the spy catches neither an omitted argument nor a wrong
number.

What it does catch is a retyped-but-**equal** literal — `5 * 1024 * 1024`
written in place of the constant. Its value is therefore **drift protection**:
it pins the *reference*, so a future change to `media_service.MAX_FILE_SIZE`
carries the route's ceiling with it instead of stranding a literal that was
correct on the day it was typed. Worth one line, on that ground and no other.

Write the comparison as `== media_service.MAX_FILE_SIZE`. Never `is`: on an
`int` above 256 that relies on CPython interning a folded constant, which is not
a property to build an assertion on.

**The accepted risk, recorded here because this module's convention is to record it where the code is** (`public_projects.py:41`, `public_branding.py:20-23`). At `300/minute` with twelve covers at the 5 MiB cap, the worst case is ~1.5 GiB/min of paid Blob egress from one IP. That is accepted knowingly. A bandwidth-parity limit would be ~12/minute — one page view a minute — which is not a limit but an outage, and its enforcement would be indistinguishable to a resident from the product being broken. So **this limiter is a fan-out guard, not an egress budget**. The worst case is also not reachable by accident: it needs twelve covers all at the cap and a caller choosing to pull them 300 times a minute. The real answer to that is `Cache-Control` plus server-side resizing, both out of scope here and both belonging with **APRAS-93**'s cache decision, where a cache changes the arithmetic.

**When the tenant is `None`.** `_page_html` takes `tenant: Tenant | None` because `_acting_tenant` can answer `None`, and that function's own docstring sets the policy: a missing row degrades like a missing logo — no `<img>`, an empty name, never an exception. The cover follows it: no tenant means the `noimg` placeholder, never the stored Blob value, and never an `AttributeError`. Both production paths establish a tenant, so this is unreachable today; it is stated because a developer writing `tenant.slug` against a `| None` parameter is the likely first draft.

**Who may upload: `projects:update`.** The write is authenticated,
tenant-scoped and gated by the permission that already governs editing an
obra's fields — a caller who may not edit an obra may not give it a photo, and
a caller who may, could already set this column through `PUT /projects/{id}`.
A test proves the refusal by calling the route as a member holding
`projects:read` only and asserting the status is 403 **and** that the column is
still what it was.

**ER11 — the public cover route carries `@limiter.limit("300/minute")` per IP.**
The right neighbour to argue from is the **logo bytes route**, not the report
route, and the logo route settles the principle before this task starts:
`backend/app/api/v1/endpoints/public_branding.py:103` decorates
`get_public_tenant_logo` with `@limiter.limit("30/minute")`, and its docstring
pre-empts exactly the cheap-versus-expensive comparison an earlier draft of this
spec rested on — "one cheap inbound request buys one outbound request we pay
for. It does not reverse D3, which was about the obras report — a local render
with a different cost profile entirely." The module docstring makes the
asymmetry explicit rather than accidental (`public_branding.py:20-23`): the
report route "carries **no** rate limit … The limiter below is this route's and
is not shared."

So the premise that public bytes routes on this surface are unlimited by design
is simply false. A cover GET has the logo GET's shape exactly — public,
uncached, one outbound Blob fetch we are billed for on every hit — and it is a
**worse** amplifier than the logo: one report view costs one logo fetch but *N*
cover fetches. A route strictly more amplifying than one that is limited cannot
be unlimited on the limited one's reasoning.

**The number, by arithmetic.** The unit that matters to an honest reader is the
*page view*, and the limiter's unit is the *request*, so the two differ by the
fan-out:

- the largest report to plan for carries **12 obras** → 12 cover GETs per view,
  and since this surface sets no `Cache-Control` anywhere, a reload repeats all
  12 rather than hitting a browser cache;
- the worst legitimate load to survive is one NAT'd condominium office or one
  shared connection: take ~10 distinct readers behind a single IP, each loading
  or reloading the report twice a minute → **20 views/minute**;
- 20 × 12 = **240 requests/minute**, and 300 is the next round number above it,
  leaving ~25% headroom and admitting **25 views/minute at 12 obras**.

That is the answer to "why do the two bytes routes carry different numbers".
They carry the *same* policy measured in page views — the logo's 30/minute is 30
views/minute at one fetch per view, and 300/minute is 25 views/minute at twelve
— and they differ tenfold in requests only because the fan-out differs tenfold.
`public_branding.py`'s "The limiter below is this route's and is not shared" is
the standing permission for per-route numbers; this route takes that note at its
word instead of copying 30, which at 12 obras would exhaust on the **third**
page view of the minute.

The earlier draft's honest-reader arithmetic was correct as arithmetic. What it
disproved was **60/minute** — five views a minute — and it would disprove the
logo route's 30/minute just as effectively if the logo carried twelve images. It
never disproved *having a limit*, and the spec was wrong to read it that way.

**What a 429 renders as.** The report HTML comes from the unmetered report
route, so the page itself still renders; a 429 lands on an `<img src>` and the
browser draws its broken-image glyph in that obra's hero. Above 300 requests a
minute from one address that is the intended outcome, and it is the reason the
limit sits well clear of legitimate traffic rather than snug against it.

**Assertion is structural, and names its mechanism.** `conftest.py` sets
`app.state.limiter.enabled = False` suite-wide (`backend/tests/conftest.py:24`),
so a case firing 301 requests and expecting a 429 asserts nothing. The test
reads slowapi's own registry, the way
`test_public_logo_route.py::test_the_route_is_decorated_with_a_thirty_per_minute_limit`
already does: build the key `f"{module.__name__}.{handler.__name__}"`, assert it
is in `limiter._route_limits`, and assert
`[str(item.limit) for item in limiter._route_limits[key]] == ["300 per 1 minute"]`.
A behavioural case is **not** required; if one is written it must re-enable
`app.state.limiter` around itself and `reset()` in a `finally`, as
`test_public_logo_route.py:364-377` does, and 301 requests is a poor trade for
what the registry assertion already fixes.

Out of scope, still: APRAS-92 D3's report-route policy. Adding this limiter does
not touch it, does not reverse it, and does not pre-empt **APRAS-93**, which
`public_projects.py:41` names as the owner of any revisit there.

**The public route is keyed by slug, not by project id alone.** Keying on the
id would need a cross-tenant lookup from an unauthenticated, `GLOBAL_SCOPED`
handler; keying on the slug lets the lookup run inside
`acting_tenant_scope`, which enforces "this project belongs to this
condominium" as a side effect of the scope rather than as a hand-written check.
It is also the shape of the report route the image is embedded in.

### D. Files touched

Backend

- `backend/app/core/urls.py` — a `public_project_cover_url(slug, project_id)`
  builder beside `public_tenant_logo_url`, absolute, slug percent-encoded.
- `backend/app/api/v1/endpoints/public_projects.py` — the new public cover
  route, its one-shape 404 and its `acting_tenant_scope` comment;
  `@limiter.limit("300/minute")` (which forces `from app.core.limiter import
  limiter` and a `request: Request` parameter **by name**, carrying the same
  `# noqa: ARG001` comment `public_branding.py:67` carries, because slowapi
  looks the parameter up by name), and no cache header. The module docstring
  gains a paragraph for the **cover route's own** limit and its number's
  arithmetic; it must **not** claim the cover route shares D3's policy, because
  D3's policy is "no limiter" and `public_branding.py:20-23` already states that
  a bytes route's limiter is its own and not shared — a "shares D3's policy"
  sentence here would contradict that module and misdescribe the code beside it.
  The existing D3 paragraph and its "**APRAS-93** owns any revisit" line stay
  exactly as they are.
- `backend/app/api/v1/endpoints/projects.py` — `PUT`/`DELETE
  /{id}/cover-photo`, declared where they cannot shadow `GET /{id}`, and one
  `_project_read(project, tenant)` helper so every `ProjectRead` in this module
  carries the derived display URL (the `_profile_of` shape).
- `backend/app/services/project_service.py` — `set_cover_photo`,
  `clear_cover_photo`, `cover_photo_bytes` (which passes
  `max_bytes=MAX_FILE_SIZE`), `cover_display_url` and `_delete_stored_cover`
  (which logs a `False` from `delete_file`); `get_project_detail` fills
  `cover_photo_display_url` through the same rung; the module-level provider
  seam tests can patch, as `tenant_service` has.
- `backend/app/schemas/project.py` — `cover_photo_display_url` on
  `ProjectRead`, read-only.
- `backend/app/services/project_report_service.py` — `_hero_html`'s `cover`
  expression asks `cover_display_url` instead of reading the column. Its
  signature grows the tenant it needs to build an absolute URL
  (`_hero_html(project, number, tenant)`), since the current signature
  (`project_report_service.py:813`) has no tenant in scope while its only
  caller, `_page_html`, does.
- `backend/app/core/permissions.py` — two `ROUTE_PERMISSIONS` entries mapping
  to `projects:update`; one `UNGUARDED_ROUTES` entry for the public cover
  route, with the comment the neighbouring entries carry.

Frontend

- `frontend/src/api/projects.ts` — `putProjectCoverPhoto(id, file)` and
  `deleteProjectCoverPhoto(id)`, multipart, paths written exactly as FastAPI
  mounts them.
- `frontend/src/types/project.ts` — `cover_photo_display_url` on
  `ConstructionProject`.
- `frontend/src/features/project-management/components/ProjectFormModal.tsx` —
  the URL input replaced by the picker, preview, remove action and inline
  refusal message; `cover_photo_url` no longer sent.
- `frontend/src/features/project-management/components/ProjectSummaryCard.tsx`
  — the `<img src>` reads `cover_photo_display_url`; the "Sem foto de capa"
  placeholder branch is unchanged.
- `frontend/src/features/project-management/components/ConstructionTrackerPage.tsx`
  — whatever wiring the modal's new upload step needs, and nothing else.
- `frontend/src/i18n/locales/pt.json`, `en.json` — the control's labels and the
  two refusal messages; the now-dead `projects.modals.coverPhotoLabel` removed.

Tests

- `backend/tests/test_projects.py` — the upload, the `DELETE`, the two refusals,
  the authorization refusal, the derived read field on both the list and the
  detail route, the replace/orphan cases, and the `caplog` case for
  `_delete_stored_cover`'s warning.
- `backend/tests/test_public_project_cover_route.py` (new) — the public route's
  200, its five 404s, its two read-ceiling cases, the `max_bytes` spy and the
  structural `300/minute` registry assertion, on `test_public_logo_route.py`'s
  model.
- `backend/tests/test_project_report.py` — the hero's two branches.
- `frontend/src/features/project-management/__tests__/` — the picker's happy
  path, its two local refusals, and the card's two branches.

### E. Test criteria, and what break makes each fail

Every assertion below is **anchored**: it names a value, not a shape. The
numbering is the card's `expected_results` numbering, one bullet per result.

- **ER1** — a test drives the form: picks a `File`, submits, and asserts the
  cover request was issued with that file's bytes for that project id, and that
  the project payload sent carries **no** `cover_photo_url` key. It also
  asserts no textbox labelled with the old URL label exists. A second test
  covers §B's create sequence: with `POST /projects` resolving to a new id and
  the cover request rejected, exactly **one** create request was issued, the
  modal is still open, the cover error is displayed, and pressing Save again
  issues a `PUT /projects/{id}` — never a second `POST`.
  *Fails if:* the URL input is restored, or the form sends `cover_photo_url`,
  or the picked file is dropped on submit, or a failed cover upload lets a
  second create through.
- **ER2** — a backend test uploads through the route with a real
  `LocalStorageProvider` rooted in `tmp_path`, then asserts `cover_photo_url`
  equals **the second element `save_file` returned** (captured from the
  provider, not retyped), and that the file exists under `base_dir`. The same
  test then reads the project back through **both** `GET /api/v1/projects` and
  `GET /api/v1/projects/{id}` and asserts each answers the same non-null
  `cover_photo_display_url`, equal to `public_project_cover_url(slug, id)` — the
  detail route is asserted explicitly because it builds its payload in
  `ProjectService.get_project_detail`, outside `_project_read`, and would
  otherwise inherit the field and answer `null` forever (§B).
  *Fails if:* the column is set to anything the provider did not return, or the
  bytes are not written, or either read route answers `null`.
- **ER3** — the public route, one test per condition, all on a real
  `LocalStorageProvider`. The 200: an unauthenticated client (no auth header at
  all) gets `response.status_code == 200`, `response.content` **equal to the
  bytes that were uploaded**, and a `content-type` header equal to the image
  type those bytes are (`image/png` for a PNG). Then five tests, each asserting
  `status_code == 404` — the literal equality, never `!= 500` — for: an unknown
  slug; a tenant whose `is_active` is `False`; a project belonging to another
  tenant; a project whose `cover_photo_url` is `None`; and a stored value the
  provider owns but cannot read, produced by setting the column to a URL under
  the provider's **own** `url_prefix` naming a file that was never written (no
  fake and no patch needed). The cross-tenant test additionally asserts the
  other tenant's uploaded bytes are **absent from `response.body`**, so the
  result is a 404 and not a 404 over a leaked payload; it resolves the project
  through a **fresh session** (`session.expunge_all()` or a new session from
  the fixture), because `Session.get()` can answer from the identity map
  without emitting a query and would then never exercise `tenant_context`'s
  loader criteria. (The route's rate limit is ER11's, not this result's.)
  *Fails if:* any condition turns into a 500 or a 200, or the route answers the
  stored Blob URL instead of bytes.
- **ER4** — the read ceiling, two size tests plus a spy, all pinned against
  `media_service.MAX_FILE_SIZE` rather than a literal. Store an object of
  exactly `MAX_FILE_SIZE` bytes as a project's cover and assert the public
  route answers 200 with all of those bytes. Store an object of
  `MAX_FILE_SIZE + 1` bytes and assert the route answers **404**. That second
  case is **the load-bearing one**: `LocalStorageProvider.read_file` returns
  `path.read_bytes()` — the whole file, no bound — when `max_bytes is None`
  (`storage_service.py:334-335`), so an implementation that omits the keyword
  serves the oversized object with a **200** and this test goes red on the local
  provider in CI. Then the spy, as a cheap **second** pin on the keyword's
  identity and explicitly **not** the assertion that catches an omitted
  argument: with the service's provider seam replaced by a spy, one public-route
  request records a `read_file` call whose `max_bytes` keyword **is**
  `media_service.MAX_FILE_SIZE` — not `2 * 1024 * 1024` retyped, not some other
  ceiling that would pass every size case in this file while still breaking a
  3 MiB cover in production.
  *Fails if:* `read_file` is called without `max_bytes` (the over-ceiling case
  turns 200), or with the wrong ceiling (the spy fails), or with a ceiling below
  `MAX_FILE_SIZE` — in production that last one means the Blob provider falls
  back to `BLOB_MAX_READ_BYTES` (2 MiB) and every cover between 2 and 5 MiB 404s
  for every resident.
- **ER5** — **one** test, both branches, so a renderer that always emits the
  placeholder cannot pass: project A has a cover stored through the provider,
  project B has none; the rendered report must contain
  `src="<the absolute public cover URL of A>"` **and**
  `<div class="noimg"></div>` for B, and must **not** contain A's raw stored
  URL. A second test keeps the third-party rung honest: a project whose column
  is `https://cdn.example/capa.jpg` renders that value verbatim.
  *Fails if:* the hero emits the stored Blob URL (the reader would get
  nothing), or emits a relative URL, or emits the placeholder unconditionally,
  or stops emitting it for a project with no photo.
- **ER6** — anchored in three steps, in one test per rule: set a cover through
  the route and remember the stored value **and** the on-disk file; attempt the
  bad upload (a `text/plain` file for the type rule, `MAX_FILE_SIZE + 1` bytes
  for the size rule); assert the status is 400 and the response `detail`
  contains the words naming the rule (`5MB` / `JPEG, PNG, WebP`); assert
  `session.get(ConstructionProject, id).cover_photo_url` **equals the
  remembered value** after `expire_all()`; assert the remembered file still
  exists and that no second file was written into `base_dir`.
  *Fails if:* validation moves after the write, or the refusal path deletes the
  previous object, or either check is dropped.
- **ER7** — verified against a **real** `LocalStorageProvider` on `tmp_path`,
  not a fake, exactly as `test_tenant_profile.py`'s `storage` fixture does:
  upload A, capture its path, upload B, then assert A's path no longer exists,
  B's does, and `base_dir` contains **exactly one** file for that project. A
  second test asserts the opposite claim for a value the provider does not own:
  with the column set to `https://cdn.example/capa.jpg`, an upload issues no
  delete (a `forbid_http`-style provider spy, or a `delete_file` that records
  its calls, asserted empty). A **third, listed** test is what actually pins
  §C's ordering, and it is listed rather than parenthetical because the two
  assertions above hold just as well for a delete-first implementation: with the
  commit made to fail (patch `session.commit` to raise once), assert the
  previous object **still exists** on disk afterwards. Delete-first leaves the
  project pointing at a deleted file and fails this test; write-set-commit-delete
  passes it. A **fourth** test covers the warning §C requires, because otherwise
  nothing in the suite notices that line was never written: patch the provider's
  `delete_file` to return `False`, replace a cover, and assert with `caplog` (at
  `WARNING`, on the `project_service` logger) that exactly one warning was
  emitted and that its message contains the project id and the undeleted stored
  value. The request itself must still answer 200 — a failed cleanup does not
  fail the call.
  *Fails if:* the previous object is left behind, or a third-party URL is
  treated as ours, or the delete runs ahead of the commit, or a `False` from
  `delete_file` is swallowed without a log.
- **ER8** — a member holding `projects:read` and not `projects:update` calls
  `PUT /{id}/cover-photo` and `DELETE /{id}/cover-photo`; each answers **403**
  and `cover_photo_url` still equals the value it had before the call, read back
  after `expire_all()`.
  *Fails if:* either route is reachable without `projects:update`, or a refused
  call still touches the column.
- **ER9** — the `DELETE`'s functional behaviour, not just its 403: set a cover
  through the route on a real `LocalStorageProvider`, capture the stored value
  and the on-disk path, call `DELETE /{id}/cover-photo`, then assert the status
  is **200** with a `ProjectRead` body whose `cover_photo_url` and
  `cover_photo_display_url` are both `null` — 200-with-the-read-schema, not 204,
  because that is what `DELETE /api/v1/tenant-profile/logo` already declares
  (`tenant_profile.py:122-131`, returning `TenantProfileRead`) and there is no
  reason for the sibling resource to answer differently. Also assert
  `cover_photo_url` is `None` in the database after `expire_all()`, the captured
  file no longer exists, and the public cover route now answers 404 for that
  project. A second call to the same `DELETE` answers **200** again with the same
  body — idempotent, no 404 and no 500.
  *Fails if:* the column is cleared without removing the object, or the object
  is removed without clearing the column, or the route answers 204, or a second
  delete errors.
- **ER10** — `cd backend && uv run pytest` and `cd frontend && npm run test`
  both green; `uv run ruff check .` clean; `npm run lint` reports **zero**
  errors for the files this task touches and a repo-wide count no higher than
  the pre-existing baseline (~375 across 64 files).
- **ER11** — the rate limit, asserted **structurally, by naming its mechanism**,
  because `backend/tests/conftest.py:24` sets `app.state.limiter.enabled = False`
  for the whole suite and a 301-request case would therefore pass without a
  limiter existing. The test imports `limiter` from `app.core.limiter`, builds
  the key slowapi registers the handler under —
  `f"{public_projects.__name__}.{public_projects.<cover handler>.__name__}"` —
  asserts that key is present in `limiter._route_limits`, and asserts
  `[str(item.limit) for item in limiter._route_limits[key]] == ["300 per 1 minute"]`.
  This is the shape `test_public_logo_route.py::test_the_route_is_decorated_with_a_thirty_per_minute_limit`
  already uses against `public_branding.get_public_tenant_logo`; copy it, do not
  invent a new one. The same test asserts the **report** handler
  (`get_public_projects_report`) is **absent** from `limiter._route_limits`, so
  the new registration is this route's alone and APRAS-92 D3 is provably
  untouched.
  *Fails if:* the decorator is missing, or registers a different number, or the
  number drifts from the arithmetic in §C without that arithmetic changing, or
  the report route acquires a limit as a side effect.

Also asserted, because the registry is the contract: `("PUT",
"/api/v1/projects/{id}/cover-photo")` and its `DELETE` map to
`projects:update` in `ROUTE_PERMISSIONS` and are absent from
`UNGUARDED_ROUTES`; the public cover route is in `UNGUARDED_ROUTES` and absent
from `ROUTE_PERMISSIONS`.

## Expected Results

- [ ] A construction project's cover photo can be set by choosing an image
      file in the internal obra view; the form no longer has a URL field and
      no longer sends cover_photo_url.
- [ ] PUT /api/v1/projects/{id}/cover-photo stores the bytes through
      upload_storage_provider() and sets cover_photo_url to the URL that
      provider returned, asserted against the provider's own return value.
- [ ] GET /api/v1/public/tenants/{slug}/projects/{project_id}/cover answers
      200 to an unauthenticated caller with response.content equal to the
      stored bytes AND an image content-type header. Five conditions each get
      their own test asserting `status_code == 404` -- never `!= 500` -- for
      an unknown slug, an inactive tenant, a project belonging to another
      tenant, a project with no cover, and a stored value the provider owns
      but cannot read (produced by naming a file under the provider's own
      prefix that does not exist; no fake needed). The cross-tenant test also
      asserts the other tenant's bytes are absent from the response body, so
      the 404 is not merely a status code over a leaked payload.
- [ ] The route that serves the cover passes its own read ceiling:
      read_file(url, max_bytes=media_service.MAX_FILE_SIZE), matching the 5
      MiB the upload accepts. Two size tests bracket it and between them catch
      every wrong NUMBER: an object one byte over the ceiling gets 404 (which
      also fails if the argument is omitted, since
      LocalStorageProvider.read_file returns path.read_bytes() whole when
      max_bytes is None, serving the oversized object with a 200; and fails if
      the ceiling is too generous), and an object exactly at the ceiling is
      served in full (which fails if the ceiling is too small, e.g. a retyped
      2 MiB). A third test asserts with a provider spy that the max_bytes
      keyword == media_service.MAX_FILE_SIZE -- use ==, never `is`, which on
      ints above 256 depends on constant interning. Its value is narrow and
      should be stated as such: the size cases already catch every wrong
      number, so the spy catches only a retyped-but-EQUAL literal, i.e. it
      pins the REFERENCE so a future change to media_service.MAX_FILE_SIZE
      carries the route's ceiling with it instead of stranding a literal. Why
      any of this matters: storage_service.BLOB_MAX_READ_BYTES defaults to 2
      MiB (sized to the logo's 2 MiB upload limit) while covers accept 5 MiB,
      so without an explicit ceiling a 3 MiB cover uploads with a 200 and then
      404s for every resident.
- [ ] One report test asserts, on the SAME rendered document, that a project
      with a cover renders <img
      src="...public/tenants/<slug>/projects/<id>/cover"> absolutely AND that
      a project without one renders <div class="noimg"></div>. Both halves in
      one document: a test that only checks the placeholder passes on a
      renderer that always emits the placeholder. A project whose stored value
      is a third-party URL still renders that URL verbatim.
- [ ] A non-image file is refused 400 with a message naming the accepted
      formats, and an oversized file is refused 400 with a message naming the
      5MB limit. In both cases the test must FIRST set a cover photo, then
      attempt the bad upload, then assert cover_photo_url still equals that
      original value by value and the previously stored file still exists --
      otherwise 'unchanged' is satisfied by there never having been anything.
- [ ] Replacing a cover photo leaves exactly one stored object for that
      project: a test on a real LocalStorageProvider asserts the previous file
      no longer exists, the new one does, and the base directory holds exactly
      one file. A project whose previous value was a third-party URL triggers
      no delete. A fourth test asserts the failed-cleanup warning: patch
      delete_file to return False, replace a cover, and assert via caplog at
      WARNING that exactly one record carries the project id and the undeleted
      value -- and that the request still answers 200, since a failed cleanup
      must not fail the call. Without this the log requirement is a line
      nobody notices was never written.
- [ ] A caller holding projects:read but not projects:update is refused 403 by
      both cover-photo routes and the column is unchanged; ROUTE_PERMISSIONS
      maps both to projects:update and the public cover route is in
      UNGUARDED_ROUTES.
- [ ] DELETE /api/v1/projects/{id}/cover-photo removes a cover. This is in
      scope because ProjectService.update_project skips None values, so PUT
      /projects/{id} cannot clear cover_photo_url -- without the delete route,
      removing the URL field would leave no way at all to drop a cover. The
      route answers 200 with ProjectRead (matching DELETE
      /tenant-profile/logo), not 204, and the body carries both
      cover_photo_url and cover_photo_display_url null.
- [ ] Backend pytest and frontend npm test suites pass in full; ruff check is
      clean; npm run lint reports zero errors in the files this task touches
      and the repo-wide count is no higher than the current baseline (~375
      pre-existing errors across 64 files -- 'zero repo-wide' is unsatisfiable
      and must not be used).
- [ ] The public cover route carries @limiter.limit('300/minute'). The number
      is page-view parity with the logo route's 30/minute, not request parity:
      30/min is 30 views/min at one fetch per view; 300/min is 25 views/min at
      twelve covers per view. Arithmetic: 12 obras x 20 views/min (one NAT'd
      office, ~10 readers, two loads each) = 240, rounded up to 300. Copying
      30 would exhaust on the THIRD page view of a 12-obra report. The
      assertion is structural, reading slowapi's registry the way
      test_public_logo_route.py already does: the handler's key is present in
      limiter._route_limits with value ['300 per 1 minute'], AND
      get_public_projects_report is ABSENT from that registry, which makes
      'the public report route is still unlimited' provable rather than
      promised. Structural because conftest.py disables the limiter
      suite-wide.

## Out of Scope

- The bulletin photo pipeline, `POST /uploads/photo` and `ProjectUpdate.photos`.
- Resizing, cropping, thumbnails, EXIF stripping, or any image processing
  beyond Pillow's decodability check.
- Changing the Blob store's access mode, or the **report** route's cache and
  rate-limit policy (APRAS-92 D3) — **APRAS-93** owns that revisit
  (`public_projects.py:41`). The cover route's own `300/minute` limiter (§C,
  ER11) is in scope and leaves the report route's registration untouched.
- Any `Cache-Control` or `ETag` on the new cover route.
- Backfilling or rewriting the third-party `cover_photo_url` values already in
  the database.
- Removing `cover_photo_url` from `ProjectCreate`/`ProjectUpdateSchema`.

## Mockup

`docs/tasks/APRAS-104-mock.html` — the cover-photo control in the obra form, in
its empty state and with a photo, plus the report hero's two branches side by
side.
