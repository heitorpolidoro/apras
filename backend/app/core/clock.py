"""The one clock (APRAS-54, contract restated by APRAS-120).

**The columns are naive by annotation, not merely by migration history.**
Every datetime field in `app/models/` is declared `pydantic.NaiveDatetime`,
which sqlmodel 0.0.47 resolves to `sa.DateTime(timezone=False)` -- byte for
byte the `TIMESTAMP WITHOUT TIME ZONE` the migrations already create, so the
annotation changed no DDL. A *bare* `datetime` resolves instead to sqlmodel's
`UTCDateTime`, a `TypeDecorator` over `DateTime(timezone=True)` that raises on
a naive bind parameter, so the annotation is what keeps the write path
working. `tests/test_clock.py` asserts it from `SQLModel.metadata`, with a
ledger (`AWARE_COLUMNS`) for columns a future migration deliberately makes
aware.

**One rule for instants: everything stored is UTC.** Both directions, with no
wall-clock column anywhere:

- **Save.** The browser converts the local wall clock to UTC with its own zone
  and sends the instant. The zone *name* never travels. `to_db` lands it in
  the column.
- **Read.** The API returns UTC *carrying the offset*, via `to_api` and
  `app/schemas/base.py`'s `ApiModel`, and the browser renders it in the
  viewer's zone.

So `db_now()` and a client write mean the same thing -- both are UTC instants
in a naive column. `db_now()` is the writer for anything the server stamps.

**`clock` is the only place a timezone is added or dropped.**
`tests/test_lint_hygiene.py` asserts that this is the only module under
`app/**` whose source text contains `tzinfo` or `astimezone(`, and the only
one that reads the clock at all. `app/schemas/base.py` converts by *calling*
`to_api`, which is what lets that rule stay a single-home rule instead of
growing an exception.

Writing naive UTC is not what an *aware* value used to become on its way into
a naive column. PostgreSQL casts an aware value by converting it into the
session's `TimeZone` first, so stored values depended on the connection's zone
(measured: a non-UTC session stored `10:13` where UTC stores `13:13` for one
instant); SQLite, measured on 0.0.47, discards the offset *without*
converting. `to_db` removes both dependences in Python, where they are
visible.

**Offsetless input is read as UTC, deliberately, and never passed to a bare
`astimezone`.** `astimezone` on a naive value assumes the *process's local
zone*, which would make the stored instant depend on where the server runs --
and because CI and production are both UTC, a suite would stay green either
way. Measured: naive `10:00` under `TZ=America/Sao_Paulo` stores `13:00`
unguarded and `10:00` guarded. Rejecting offsetless input with 422 was the
alternative and was declined: no current caller sends one, so it would buy
nothing and break every script and integration that does.

**The calendar-date exception.** `Task.due_date` and
`UserLotLink.start_date`/`.end_date` are *calendar dates* that happen to live
in `DateTime` columns, and their forms are `type="date"`. They take no `to_db`
alias on the way in and no offset on the way out
(`ApiModel.CALENDAR_DATE_FIELDS`), because a timezone conversion moves a date
by a day: `taskUtils.ts` does `startOfDay(new Date(due_date))`, so
`"2026-09-10T00:00:00"` reads as Sep 10 local while
`"2026-09-10T00:00:00+00:00"` reads as **Sep 9** in BRT. Applying the UTC rule
to them would ship a one-day regression.

**Follow-ups this contract deliberately leaves open**, recorded here rather
than rediscovered:

1. *Those three columns are the wrong type.* They should be `Date`. Narrowing
   them is a migration and APRAS-120 took none, so the mismatch stands and the
   exception list is how it is contained. The cost of the list is that a real
   *timestamp* field named `end_date` added later would be silently excluded
   from the offset.
2. *A datetime inside a `dict`- or `Any`-typed response field ships
   offsetless.* `ApiModel`'s serialiser is attached to the model, so a value
   nested in a raw `dict` never passes through it (measured on pydantic
   2.13.3). Audited at APRAS-120: no response does this today -- the only
   loose fields reaching the wire are `TaskHistoryRead.resolved_old_value` and
   `.resolved_new_value`, whose producer returns strings and lists of strings
   by construction. Whoever adds a `dict`- or `Any`-typed response field must
   stringify any datetime they put inside it.
3. *`TaskForm.tsx`'s `new Date(v).toISOString().split("T")[0]`* is off by a day
   for positive offsets. It prefills the edit form from a value this contract
   leaves offsetless, so its behaviour is unchanged and it was left alone.

`db_now()` is UTC with `tzinfo` dropped; the stored instant is the UTC one on
every session, which is what every reader already assumed.
"""

from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import AfterValidator


def utc_now() -> datetime:
    """The current instant, timezone-aware, in UTC. For computation only."""
    return datetime.now(UTC)


def db_now() -> datetime:
    """`utc_now()` with `tzinfo` dropped.

    The same instant, in the shape the naive `TIMESTAMP WITHOUT TIME ZONE`
    columns already hold. Every writer that reaches a column uses this.
    """
    return utc_now().replace(tzinfo=None)


def today_utc() -> date:
    """The calendar date of `utc_now()`.

    Deliberately UTC and not the local calendar: production runs UTC, so this
    makes a developer machine agree with it instead of drifting by a day
    every evening in a negative-offset zone.
    """
    return utc_now().date()


def to_db(value: datetime) -> datetime:
    """A client-supplied instant, in the shape the naive columns hold.

    Aware in -- which is every real request, since the browser sends
    `new Date(v).toISOString()` -- converts to UTC and drops `tzinfo`, so the
    offset is *subtracted* rather than discarded.

    Naive in is read as already being UTC and returned unchanged. The
    `tzinfo is None` guard is the whole point and is not defensive: without
    it, `astimezone(UTC)` would assume the process's local zone and the same
    payload would store a different instant depending on where the server
    runs. The module docstring records the measurement.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def to_api(value: datetime) -> datetime:
    """A stored instant, in the shape a JSON response should carry.

    Naive in is stamped UTC -- the columns hold UTC, so this adds the offset
    the value always had and never moves the instant. Aware in is normalised
    to UTC. Either way the result serialises with a trailing offset, which is
    what lets `new Date(x).toLocaleString()` in the browser render the
    viewer's local time instead of reading UTC digits as local ones.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


#: A client-supplied *timestamp* field, normalised to the naive UTC instant
#: its column holds. Applied to the eight `datetime` inputs in
#: `app/schemas/` that are genuine instants; the three calendar-date fields
#: named in this module's docstring deliberately do not take it.
#:
#: The base is a bare `datetime`, not `NaiveDatetime`, and that is measured
#: rather than stylistic: an `AfterValidator` runs *after* the base type's own
#: validation, so `Annotated[NaiveDatetime, AfterValidator(to_db)]` rejects
#: every aware input with a 422 before `to_db` can convert it -- i.e. it would
#: reject every real request, since the browser always sends an offset.
#: Verified: with the bare base, `+03:00 13:00` validates to naive `10:00`.
DbDatetime = Annotated[datetime, AfterValidator(to_db)]
