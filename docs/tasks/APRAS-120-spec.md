# APRAS-120 — Decide how the naive datetime columns survive sqlmodel 0.0.47

## The decision

**Route 1: annotate every model datetime field with Pydantic's `NaiveDatetime`,
raise the floor to `sqlmodel>=0.0.47`, and touch no migration.**

The operator's preference is also the correct call, and the reason is narrower
than "it is cheap". Measured in sqlmodel 0.0.47's own source
(`sqlmodel/main.py:757-760`):

```
datetime            -> UTCDateTime()            # TypeDecorator over DateTime(timezone=True)
NaiveDatetime       -> DateTime(timezone=False) # byte-identical to today's sa.DateTime()
```

So the annotation changes **no DDL**: the column sqlmodel emits for
`NaiveDatetime` is the same `TIMESTAMP WITHOUT TIME ZONE` the 38 migrations
already created. Route 2 (migrate 110 columns to `timezone=True`) remains the
eventual end state and remains deferred on APRAS-54's measurement; it is a
migration over every dated table against production Neon and is not this task.
Route 3 (pin below 0.0.47) is **not an outcome**: it freezes the ORM forever to
avoid a type annotation.

**What route 1 costs, stated honestly.** `NaiveDatetime` is a Pydantic
constraint, and SQLModel skips Pydantic validation on `table=True` models —
verified directly on 0.0.47: constructing a model with an **aware** value in a
`NaiveDatetime` field is allowed and commits without error. So the annotation
buys a *naive column*, not a *naive-only writer*. Half of the "prose claim
becomes executable" promise therefore has to be bought separately, and §4 buys
it. Route 1 also forecloses nothing: when route 2 is eventually taken, the
annotations are the exact list of fields it must revisit, which is strictly
better than today's 108 unmarked `datetime`s.

## Scope

One deliverable, in seven parts. Parts 4 and 5 are in scope because the
expected results require them, and because part 5 is the reason part 1's failure
took 22 database-free test modules down with it. Part 6 is the read half of the
same UTC rule part 4 states, and it is where the user-visible defect is.

1. **Raise the floor and relock.** `backend/pyproject.toml`:
   `sqlmodel>=0.0.38` → `sqlmodel>=0.0.47`; `backend/uv.lock` relocked. The
   suite must be run against that lock, not reasoned about.
2. **Annotate the model fields.** All **108** `datetime`-annotated field
   declarations across the **22** files in `backend/app/models/` become
   `NaiveDatetime` (`from pydantic import NaiveDatetime`), including the
   `| None` ones. 108 is the declaration count, measured by applying the
   rewrite mechanically (`^\s+<name>: datetime` → `NaiveDatetime`, 108 hits in
   22 files); the 130 an earlier draft carried was the count of *lines
   mentioning* `datetime`, i.e. those 108 plus 22 `from datetime import …`
   lines. After the sweep `SQLModel.metadata` holds exactly **108**
   `datetime` columns, so the declaration count and the column count agree. Use Pydantic's name directly, with no project alias: it is
   what sqlmodel's own error message and its shipped skill document name, so a
   developer who hits the error finds the repository already spelling the
   answer. `date`-typed fields are untouched (`Date` is unaffected).
3. **State the contract.** `app/core/clock.py`'s module docstring says what is
   now enforced and by what: the columns are naive by *annotation*, not merely
   by migration history; `db_now()` is the writer; and `clock` is the only
   place a timezone is added or dropped.
4. **One rule for instants: everything stored is UTC.** The operator's decision,
   and it replaces an earlier draft's "naive in → stored unchanged":

   - **Save.** The browser converts the local wall clock to UTC with its own
     zone and sends the instant. The zone *name* never travels.
   - **Read.** The backend returns UTC **carrying the offset**, and the browser
     renders it in the viewer's zone.

   `db_now()` writes and client writes therefore mean the same thing — both are
   UTC instants in a naive column — which the previous draft did not achieve and
   wrongly called acceptable. There is no wall-clock column.

   **The client already does the save half.** Measured in the frontend, not
   inferred from fixtures: `SpaceBookingPage.tsx:73-74`,
   `AssemblyVotingPage.tsx:117`, `AuthorizationFormModal.tsx:102-103` and
   `UserLotAssignmentModal.tsx:54` all send `new Date(value).toISOString()`, and
   `TaskForm.tsx:125-126` sends a `Date` object, which `JSON.stringify` renders
   the same way. Every one emits a trailing `Z`. So **every client-supplied
   datetime already arrives aware**, and an earlier draft's naive branch was
   protecting a caller that does not exist: it cited
   `tests/test_space_reservations.py` and `tests/test_projects.py:358`, which are
   test fixtures. Correcting that premise is what changed this part.

   **`clock` gains `to_db(value)`, applied as an `Annotated` alias to the eight
   client-supplied *timestamp* fields** in `app/schemas/`:
   `SpaceReservationCreate.start_time`/`.end_time`,
   `VisitorAuthorizationCreate.valid_from`/`.valid_until`,
   `VoteCreate.opens_at`/`.closes_at`, `VoteUpdate.opens_at`/`.closes_at`.
   `to_db` is `astimezone(UTC)` then `tzinfo` dropped — one branch for aware
   input, which is every real request.

   The alias is needed even though part 2 annotates the columns: measured on
   0.0.47, writing an **aware** value through a `NaiveDatetime` field commits
   silently and the offset is *discarded without conversion* on SQLite
   (`+03:00 13:00` stores `13:00`, not `10:00`), while Postgres converts through
   the session zone. `to_db` is what makes the stored instant the same on both.
   It also fixes a live latent defect: `visitor_service.py:391` compares
   `clock.db_now()` (naive) with `auth.valid_from`, which is the aware Python
   object while the row is still in the identity map, i.e. a `TypeError`. Under
   one UTC rule that comparison is naive-to-naive and the fix is the alias
   itself, with no code in the service.

   **Offsetless input is interpreted as UTC, explicitly — not rejected.** The
   UTC rule makes an offsetless string ambiguous, so `to_db` resolves the
   ambiguity in the one direction consistent with the columns: a value whose
   `tzinfo` is `None` is *read as already being UTC* and returned unchanged. It
   is never passed to a bare `astimezone`, which would assume the process's
   local zone and make the stored value depend on where the server runs
   (measured: naive `10:00` under `TZ=America/Sao_Paulo` becomes `13:00`
   unguarded, `10:00` guarded). 422 was the alternative and is rejected: no
   current caller sends offsetless values, so a 422 buys nothing and breaks
   every script and integration that does.

   Interpret-as-UTC leaves the existing payloads *mechanically* green — the
   stored value is identical — but makes them lie about their intent, so they
   change as part of the work, counted here rather than discovered mid-
   implementation: **18 offsetless strings in 9 payloads in
   `tests/test_space_reservations.py`** (lines 834-835, 854-855, 870-871,
   898-899, 923-924, 950-951, 1032-1033, 1060-1061, 1090-1091) gain a `Z`.
   `tests/test_projects.py:358` does **not** change: it posts
   `"due_date": "2026-09-10"` to `ProjectMilestone.due_date`, which is a
   `date` column on a different model and was never one of the twelve — the
   earlier draft's citation of it was simply wrong.

   **Four of the twelve are calendar dates and leave the coercion list.** A
   calendar date has no timezone and converting one moves it by a day. Measured
   column types in `app/models/`, not reasoned from names:

   | Field | Column | Verdict |
   |---|---|---|
   | `TaskBase.due_date`, `TaskUpdate.due_date` | `Task.due_date: datetime` (`task.py:63`), UI `type="date"` (`TaskForm.tsx:280`) | **calendar date** in a `DateTime` column |
   | `UserLotLinkCreate.start_date`/`.end_date` | `UserLotLink.start_date`/`.end_date: datetime` (`lot.py:37-38`), UI `type="date"` (`UserLotAssignmentModal.tsx:165,175`) | **calendar date** in a `DateTime` column |
   | the other eight | `DateTime`, UI `type="datetime-local"` | timestamps, UTC rule applies |

   These four get **no alias, no conversion, and no offset on the way out**
   (part 6 excludes them). Their columns stay as they are — migrating them to
   `Date` is a schema change and part 1 takes no migration; the mismatch is
   recorded in `clock`'s docstring as the follow-up. The reason to leave them
   alone is measured, not stylistic: `taskUtils.ts:108` does
   `startOfDay(new Date(due_date))`, so today's offsetless `"2026-09-10T00:00:00"`
   parses as local midnight and the badge reads Sep 10, while
   `"2026-09-10T00:00:00+00:00"` parses as Sep 9 21:00 in BRT and the badge
   would read **Sep 9**. Applying the UTC read rule to these fields would ship a
   one-day regression; excluding them ships none.

   `TaskForm.tsx:59`'s `new Date(v).toISOString().split("T")[0]` — safe for
   negative offsets, off by a day for positive ones — is **out of scope**: it
   only prefills the edit form from a value the backend already serialises
   offsetless, so under this task's rules its behaviour does not change. It is
   noted in `clock`'s docstring with the column-type follow-up, not fixed here.
5. **Narrow the autouse fixture.** Move the default-tenant seed **into**
   `session_fixture` in `backend/tests/conftest.py`, immediately after
   `create_all`, and delete `autouse=True` from `default_tenant_fixture`,
   which becomes a plain non-autouse lookup of the seeded row. No test
   references the fixture *by name* today (checked), so nothing else moves.
   This is a strict improvement, not a weakening: "every test database
   contains the default tenant" becomes a property of the database rather than
   of fixture ordering, and the **22** test modules that mention neither
   `session` nor `client` stop building a SQLite engine and committing a row
   they never read.

6. **Fix the live three-hour display defect: the read path carries the offset.**
   This is the most valuable thing in the task and it is a defect a resident can
   see today, independent of sqlmodel. Measured on pydantic 2.13.3: a naive
   `datetime` serialises as `"2026-06-01T13:00:00"`, an aware one as
   `"2026-06-01T13:00:00Z"`. The columns hold UTC, the API drops the offset, and
   `SpaceBookingPage.tsx:174` renders with
   `new Date(res.start_time).toLocaleString()` — which reads an offsetless string
   as **local** time. A reservation booked at 10:00 BRT is stored correctly as
   13:00 UTC and **displayed as 13:00**.

   **How**: a single shared base class, `ApiModel`, in a new
   `backend/app/schemas/base.py`, carrying
   `@field_serializer("*", when_used="json")`. The serialiser itself touches no
   `tzinfo`: the conversion lives in `clock` as a second named direction,
   `to_api(value) -> datetime` (naive in → the same instant stamped UTC; aware in
   → `astimezone(UTC)`), and `base.py` only calls
   `clock.to_api(v).isoformat()` for `datetime` values and returns every other
   value untouched. Keeping the conversion in `clock` is what lets T2 stay the
   single-home rule it is today instead of growing an exception.
   `app/schemas/*.py` holds **239** classes, of which **203** name `BaseModel`
   directly and 36 inherit a sibling in the same file; the sweep rewrites those
   **203** bases to `ApiModel` and the other 36 inherit it, so the change is
   mechanical and complete. The alternative of a
   per-field `Annotated` alias on the 106 response-side `datetime` fields is
   rejected: it is more churn and a newly added read schema would silently opt
   out. `json_encoders` is rejected because pydantic v2 deprecates it.
   Chosen behaviour, measured:

   - `when_used="json"` leaves `model_dump()` in python mode returning real
     `datetime` objects, so no internal caller changes;
   - FastAPI serialises a `response_model` with `mode="json"`, so the offset
     reaches the wire (verified: `model_dump(mode="json")` →
     `"2026-06-01T13:00:00+00:00"`);
   - `date` fields, `UUID`s, nested models and lists of models are unaffected
     (verified on a nested fixture).

   The **33 `toLocaleString` call sites** across the frontend then render
   correctly with **no frontend change**, and no backend test asserts a response
   datetime string today (checked: the only such assertion,
   `tests/test_infractions.py:246`, is on a `date` field).

   **The four calendar-date fields of part 4 are excluded**, for the one-day
   regression measured there. The exclusion is by name, in one module-level
   constant beside the serialiser — `CALENDAR_DATE_FIELDS: frozenset[str]` of
   field names (`"due_date"`, `"start_date"`, `"end_date"`) — so the list is
   readable and testable rather than scattered, and the serialiser reads
   `info.field_name` off `FieldSerializationInfo` (verified to be populated for a
   `"*"` serialiser). The name match is **exact today, not approximate**:
   measured, `app/schemas/` contains exactly six `datetime`-typed fields whose
   name ends in `_date` — `task.py:19,37` and `lot.py:75-76,85-86` — i.e. the
   write side of part 4's four plus `UserLotLinkRead`'s two, and nothing else.
   Its cost is still stated: a *timestamp* field named `end_date` added later
   would be silently excluded, which `clock`'s docstring records as the price of
   not migrating the columns.

   **Known limit, and the audit that says nothing falls through it today.** The
   serialiser is attached to the model, so a value inside a raw `dict` never
   passes through it: verified on 2.13.3, a model with `blob: dict` holding a
   datetime serialises that datetime **offsetless** while sibling fields, nested
   models and lists of models all carry `+00:00`. If a response returned a
   datetime that way, the three-hour defect would survive there. **Nothing does,
   measured three ways on this tree:**

   1. Every declared response model was walked transitively (`app.main`'s 242
      `APIRoute`s → `response_model` → `model_fields`, recursing into nested
      models, unions and `list` args), collecting every field whose resolved
      annotation is loose — `dict`, `Any`, `Mapping` or `object`. The walk
      returns exactly **two** fields, both on the same route:
      `TaskHistoryRead.resolved_old_value` and `.resolved_new_value`
      (`dict | None`, `GET /api/v1/tasks/{task_id}/history`). Their only
      producer is `task_service.py:_resolve_user`, which returns
      `{"name": str, "roles": list[str]}` — no datetime, by construction.
   2. Every other loose-looking schema field is a *typed* mapping that cannot
      hold a datetime: `module_prices: dict[str, float]` (`plan.py`),
      `AdvancedBrandTheme.light`/`.dark` and the two `theme` fields
      (`dict[str, str]` / `dict[str, dict[str, str]]`, `tenant.py`).
   3. The `JSON` columns are not the hole either. `SQLModel.metadata` holds 11
      `JSON` columns; the two with `Any` in their payload type —
      `ConstructionProject.planned_progress_json: list[dict[str, Any]]` and
      `ProjectMilestone.detail_json: dict[str, Any]` — appear in **no** schema
      and **no** endpoint (grep over `app/schemas/` and `app/api/`), so they
      never reach a response. `Tenant.brand_theme` reaches responses only
      through the typed `BrandTheme` model.

   The 29 routes with no `response_model` are all `DELETE`s returning 204 or
   handlers returning `Response`/`HTMLResponse` (file bytes, QR code, HTML
   reports); none emits a JSON datetime.

   So the limit is real and currently unreached. It is **out of scope** rather
   than covered: closing it would mean recursing into arbitrary containers in the
   serialiser, which costs more than it buys while the loose surface is two
   fields of strings. Recorded here, and in `clock`'s docstring, so that whoever
   adds a `dict`-typed or `Any`-typed response field knows a datetime placed
   inside it will ship offsetless and must be stringified by its producer.

7. **Remove the Dependabot exclusion this task was the reason for.**
   `.github/dependabot.yml`'s `backend-version-updates` group excludes
   `sqlmodel` (added by `fa8fe27`, whose message reads "until APRAS-120
   lands"). Parts 1-5 remove the reason, so this commit removes the
   exclusion: `exclude-patterns` goes back to `["ruff"]` and the explanatory
   comment block goes with it. It belongs here and not in a follow-up because
   the two halves are one fact -- the exclusion exists *because* 0.0.47 broke
   the suite, and nothing but this task makes that false. Left for later it
   becomes a permanent exclusion justified by a condition that has already
   been met, which is how a package stops being updated and nobody notices.

## Behavior

- Writing `clock.db_now()` through any model commits and reads back naive, on
  SQLite and on Postgres, under sqlmodel 0.0.47.
- No column type, nullability or default changes anywhere in the live schema.
- An offset-bearing datetime in a request body is accepted (not 422) and stored
  as the equivalent naive **UTC** instant, with the offset subtracted.
- An offsetless datetime in a request body is interpreted as UTC and stored
  unchanged, identically on a machine in any timezone.
- Every `datetime` in a JSON response carries `+00:00`, so
  `new Date(x).toLocaleString()` in the browser renders the viewer's local time.
  A reservation booked at 10:00 BRT reads back as 10:00 BRT.
- `Task.due_date` and `UserLotLink.start_date`/`.end_date` are unchanged in both
  directions: no offset out, no conversion in, and the task's due-date badge
  still names the day the user picked.
- A test module that touches no database builds no database.

## Files touched

- `backend/pyproject.toml` — sqlmodel floor to `>=0.0.47`.
- `backend/uv.lock` — relocked.
- `backend/app/models/*.py` (22 files) — `datetime` → `NaiveDatetime` on field
  annotations; the now-unused `from datetime import datetime` dropped where
  ruff reports it.
- `backend/app/core/clock.py` — docstring restates the contract (one UTC rule
  both directions, the calendar-date exception, the `Task.due_date` /
  `UserLotLink.*_date` column-type follow-up, and the `dict`/`Any`-field limit of
  part 6); adds `to_db`, `to_api` and the
  schema alias.
- `backend/app/schemas/base.py` — **new**: `ApiModel` with the `"*"` json field
  serialiser and `CALENDAR_DATE_FIELDS`.
- `backend/app/schemas/*.py` (28 files) — the 203 direct `BaseModel` bases
  become `ApiModel` (the other 36 classes inherit it through a sibling); the **eight** timestamp input fields take `to_db`'s alias; the
  four calendar-date fields are left alone.
- `backend/tests/test_space_reservations.py` — 18 offsetless datetime strings in
  9 payloads gain a `Z`.
- `backend/tests/conftest.py` — seed moves into `session_fixture`;
  `autouse=True` removed.
- `backend/tests/test_clock.py` — the `AWARE_COLUMNS` ledger constant, T1, T3,
  T7, T8 and T9; the existing three round-trips kept.
- `backend/tests/test_lint_hygiene.py` — the `tzinfo`/`astimezone` scan,
  unchanged in shape: `clock` stays the only home, because `base.py` calls
  `clock.to_api` rather than converting.
- `backend/tests/test_suite_hygiene.py` — the autouse-fixture rule, plus the
  T9 scan: "every schema class whose resolved `model_fields` include a
  `datetime` — inherited ones counted — subclasses `ApiModel`".
- `backend/tests/test_migrations_postgres.py` — the real-Postgres agreement
  test.
- **No file under `backend/alembic/versions/`.** The 38 migrations are left
  untouched, deliberately and for the reason given above: `NaiveDatetime`
  resolves to the column type they already create. Recorded here so it is not
  rediscovered as an omission in review.
- **No frontend file.** The 33 `toLocaleString` sites become correct because the
  payload changed, which is the point of part 6.

## Test criteria

Nine assertions, each with the mutation that proves it load-bearing. The
mutations matter: this repository has shipped nineteen tests that no mutation
of the source could redden.

| # | Assertion | Home | Mutation that must redden it |
|---|---|---|---|
| T1 | Every `datetime` column in `SQLModel.metadata` (after `import app.models`) is a plain `sa.DateTime` with `timezone` false and is **not** a `sqlmodel.UTCDateTime`, unless its `"table.column"` name is in the `AWARE_COLUMNS` ledger (see below, empty today); the inspected set holds at least 100 columns (108 today), so the test cannot pass vacuously. **The column selector must unwrap `TypeDecorator`** — see "How T1 must select columns" | `tests/test_clock.py` | `app/models/task.py`: `Task.created_at: NaiveDatetime` → `datetime`. Measured: T1 reddens with `AssertionError: ['task.created_at: UTCDateTime()']`, and it is the only test in the suite that names the offending column from metadata alone, with no database |
| T2 | `app/core/clock.py` is the only module under `app/**` whose source contains `tzinfo` or `astimezone(` — the existing rule-3 scan extended, so timezone coercion keeps exactly one home | `tests/test_lint_hygiene.py` | add `.replace(tzinfo=None)` to any service; T2 reddens naming that file |
| T3 | `POST .../lots/{lot_id}/authorizations` with `valid_from` carrying a `+03:00` offset answers **201**, and the stored column value is the naive UTC instant (**offset subtracted**, i.e. three hours earlier than the digits sent), read back after `session.expire_all()` | `tests/test_clock.py` | remove the alias from `VisitorAuthorizationCreate.valid_from`; T3 reddens on the stored value, not on the status code. Measured why this mutation is not vacuous: without the alias the write **succeeds silently** on SQLite and stores the unconverted digits (verified on 0.0.47 — an aware value in a `NaiveDatetime` field commits and the offset is discarded, not converted) |
| T4 | The three existing `test_clock.py` round-trips still pass — under 0.0.47 they now additionally prove the bind parameter does not raise | `tests/test_clock.py` | revert any of the three models' annotations; the write raises `StatementError (builtins.ValueError) Datetime values must have timezone information`. For `Task.created_at` this is `test_task_created_at_is_stored_naive` plus ~1,800 other nodes — the same mutation T1 proves, seen from the write side |
| T5 | On a **real Postgres**, every dated column in the migrated schema outside `AWARE_COLUMNS` is `timestamp without time zone` (`information_schema.columns.data_type`), the live set and the live `timezone` flag **agree column for column with `SQLModel.metadata`**, and one `clock.db_now()` write round-trips naive | `tests/test_migrations_postgres.py` | the T1 mutation **also reddens T5**, measured on `postgres:16-alpine`: the agreement half fails with `AssertionError: {('task', 'created_at'): True}` (metadata aware, live naive) and the round-trip half raises the same `StatementError`, while all 36 existing tests in the module stay green because they compare only column *names* and *nullability* |
| T6 | No `autouse` fixture declared in `tests/conftest.py` requests the `session` fixture (AST scan), and `pytest tests/test_lint_hygiene.py` passes 4/4 | `tests/test_suite_hygiene.py` | restore `autouse=True` on `default_tenant_fixture`; T6 reddens |
| T7 | **With the process zone forced to `America/Sao_Paulo`**, `POST /api/v1/space-reservations/` with `"start_time": "2026-06-01T10:00:00Z"` answers 201 and the stored column reads back `datetime(2026, 6, 1, 10, 0)`; **and** the same payload with the `Z` removed stores the identical value, which is the "offsetless means UTC" decision; plus a unit half calling `to_db` on the naive value under `TZ=UTC` and `TZ=America/Sao_Paulo` and requiring the two results equal. The zone is set in-process by a fixture: `os.environ["TZ"] = "America/Sao_Paulo"; time.tzset()`, restoring the previous value and calling `tzset()` again on teardown — **no subprocess needed**, measured working under this suite's `client`/`session` fixtures. The fixture asserts `datetime.now().astimezone().utcoffset()` is `-3:00` first, so T7 cannot pass by failing to change the zone | `tests/test_clock.py` | drop the `value.tzinfo is None` guard from `to_db`. **Measured end to end**, prototyping `to_db` plus the alias on `SpaceReservationCreate` on the current tree: guarded → `1 passed`; unguarded → `AssertionError: assert datetime.datetime(2026, 6, 1, 13, 0) == datetime.datetime(2026, 6, 1, 10, 0)` on the offsetless half, and the unit half fails on the two zones disagreeing. Without the TZ fixture **the same mutation stays green**, which is why the fixture is part of the criterion and not a convenience |
| T8 | **The display defect, end to end and zone-independent.** `GET /api/v1/space-reservations/` for a reservation whose stored column is `datetime(2026, 6, 1, 13, 0)` returns `start_time` **ending in an offset** — asserted as "parsing it with `datetime.fromisoformat` yields `tzinfo is not None` and `utcoffset() == timedelta(0)` and the instant equals `2026-06-01T13:00:00+00:00`" — and the **four** calendar-date fields are asserted **offsetless** in the same test: a `GET` of a task with `due_date` set and a `GET` of a lot's user links return strings that `fromisoformat` parses to `tzinfo is None` | `tests/test_clock.py` | remove `ApiModel` from `SpaceReservationRead` (or revert `to_api` to return the value unchanged): the timestamp half reddens with `tzinfo is None`, which is exactly today's production behaviour. Separately, **adding** `"due_date"`-style coercion to the calendar fields reddens the second half. The assertion is written on the parsed offset, not on string equality, so it **fails when the offset is absent** rather than merely passing when some string is present |
| T9 | **No read schema can opt out by accident.** The scan is **import-based, not AST**: it imports the 27 modules in `app/schemas/`, and for every pydantic model class *defined* in one of them it resolves `model_fields` and recurses through `Annotated`, union and `list`/`dict` arguments; every class whose resolved fields include a `datetime` must have `ApiModel` in its MRO. Measured on this tree: **74** of the 239 classes qualify, and the vacuity floor is **at least 70**. See "Why T9 counts 74" below | `tests/test_suite_hygiene.py` | change any one of the 203 bases back to `BaseModel`; T9 reddens naming the class. This is the test that makes part 6 survive the next read schema somebody adds |

### Why T9 counts 74, and why the floor is 70

The scan and the number were chosen in that order, and both were counted on this
tree rather than estimated:

- **Declaration-only scan** (AST over `AnnAssign` nodes in `app/schemas/*.py`):
  **63** classes.
- **Resolved-fields scan** (import the 27 modules, walk `model_fields`):
  **74** classes.

T9 uses the second, because it is the stronger guarantee: the 11 extra classes
declare no `datetime` of their own and inherit one from a sibling in the same
file, and every one of them is a response schema — `AccessDeviceKeyRead`,
`AnnouncementDetailRead`, `AssetDetailRead`, `DocumentFolderTreeRead`,
`LotDetailRead`, `OccurrenceDetailRead`, `ProjectDetailRead`,
`PurchaseRequestDetailRead`, `ResidentDetailRead`, `MyBallotRead`, plus
`TaskCreate`. Those are exactly the classes part 6 must not miss, and exactly
the ones a declaration-only scan cannot see. The reverse set is empty: every
declaring class is also a resolving one, so the resolved scan is a superset.

The floor is **70**, one notch under today's 74, and the reason is stated here so
the next person who adds or removes a schema knows what to do with it: 74 is a
census, not a target, and a test about *inheritance* must not redden merely
because somebody legitimately deleted a dated field. 70 is still far above what
any broken scan produces — a scan that fails to resolve inheritance yields 63
and a scan that resolves nothing yields 0, so neither can pass. If the count
ever drops below 70, the scan is to be re-measured and the floor re-stated with
the new census; it is never to be lowered to whatever the run produced.

### How T1 must select columns

Measured on sqlmodel 0.0.47 + SQLAlchemy 2.0.49: `UTCDateTime` is a
`TypeDecorator`, so for a reverted column **both** obvious selectors skip it
silently — `isinstance(column.type, sa.DateTime)` is `False`, and
`column.type.python_type` *raises* `NotImplementedError`. A T1 written either
way passes the mutation (verified: it did). T1 must therefore treat a column as
dated when `isinstance(type_, sa.DateTime)` **or** its unwrapped
`impl_instance` is an `sa.DateTime`, and then require the outer type to be
exactly `sa.DateTime` with `timezone` false. Without this, T1 asserts nothing.

### The `AWARE_COLUMNS` ledger, and why it is not a wall

T1 and T5 pin ~108 columns naive, and route 2 — the migration APRAS-54
**deferred**, not ruled out — would deliberately make some of them aware. A
flat "every column is naive" would make this task the second wall in front of
that move, which is the mistake this repository already shipped with the two
tests that pinned the bcrypt cost floor so rigidly that *raising* it failed CI.

So both tests read one module-level constant,
`AWARE_COLUMNS: frozenset[str]` in `tests/test_clock.py`, holding
`"table.column"` names deliberately migrated to `timestamp with time zone`.
It is **empty today**. A route-2 task adds its columns to it in the same commit
as its migration and its rewrite of `clock`'s contract, and the suite passes;
an *accidental* aware column is not in the ledger and still reddens. Measured
on the reverted `Task.created_at`: empty ledger → T1 fails naming
`task.created_at: UTCDateTime()`; `AWARE_COLUMNS = {"task.created_at"}` → T1
passes. T1 also fails for a name **in** the ledger whose column is naive, so
the ledger cannot rot into a list of excuses.

### The mutation, measured in full

`Task.created_at: NaiveDatetime` → `datetime` on the annotated tree under
0.0.47 reddens **1,800 test nodes** across 20 modules (`64 failed, 1,747
errors` in a full run, less 11 failures that are artifacts of running from a
copy without the repo root's `AGENTS.md` and `ci.yml`). Essentially every test
that writes a `Task` fails, because the write itself raises. "Its neighbours
stay green", which an earlier draft of expected result 2 claimed, is false, and
the discrimination is a different one: of those 1,800 nodes, **T1 is the only
one that names `task.created_at` from `SQLModel.metadata` with no database
involved**; every other local failure is a write-time `StatementError`, and the
CI-only T5 names the same column as a live-schema disagreement. That is what
expected result 2 asserts.

**T5 is CI-only.** `ci.yml`'s `backend-migrations` job provides a throwaway
`postgres:16-alpine` UTF-8 service and `TEST_POSTGRES_URL`; the module
self-skips wherever that variable is unset, and `scripts/assert_no_skips.py`
fails the job on any skip. A developer without Docker cannot verify T5 locally
except through the `initdb` recipe in `AGENTS.md`, so the criterion is written
to be checked from a CI run on the branch
(`gh workflow run ci.yml --ref <branch>`), not from a local pytest.

## Measured before any work starts (the blast-radius expected result)

Reproduced on this working tree, not reasoned about:

```
$ cd backend && uv run --with 'sqlmodel==0.0.47' --isolated pytest tests/test_lint_hygiene.py -q
4 errors   # all four from default_tenant_fixture's commit, in setup
```

`tests/test_lint_hygiene.py` reads source files and touches no database, and
still cannot run. Then, with **only** `app/models/tenant.py`'s three fields
annotated `NaiveDatetime` and nothing else changed:

```
4 passed in 0.30s
```

The blast radius is one fixture, and the fix is the annotation. `tenant.py` was
restored immediately; the working tree is unchanged.

## Out of scope

- **Route 2.** No migration, no `timezone=True`, no data step. The eventual
  move stays deferred, and the annotations added here are the worklist for it.
- **Migrating the three calendar-date columns to `Date`.** `Task.due_date` and
  `UserLotLink.start_date`/`.end_date` are calendar dates living in `DateTime`
  columns. Part 4 leaves them untouched in both directions and `clock`'s
  docstring records the mismatch; narrowing the columns is a migration and part
  1 takes none.
- **`TaskForm.tsx:59`.** `new Date(v).toISOString().split("T")[0]` is off by a
  day for positive offsets. It prefills the edit form from a value this task
  leaves offsetless, so nothing here changes its behaviour and nothing here
  fixes it.
- **Rejecting offsetless input with 422.** Considered and decided against in
  part 4; interpret-as-UTC is the rule.
- **Datetimes nested inside `dict`/`Any` response fields.** The `"*"` serialiser
  cannot reach them (measured). Audited in part 6: no response returns a datetime
  that way today, so there is nothing to fix; the limit is documented in `clock`
  rather than engineered around.
- **Frontend changes.** Part 6 is deliberately a payload change so the 33
  existing `toLocaleString` sites become correct without being edited. Frontend
  test fixtures that still contain offsetless strings become unrepresentative of
  the API but no frontend test reddens; refreshing them is its own chore.
- PR #36 / PR #42 and the alembic 1.20.0 bump. The Dependabot `sqlmodel`
  exclusion is **no longer** out of scope -- see part 6.
- `NOQA_CAP` is not raised. If the diff needs a `noqa`, that is a review
  question, not a silent bump.
