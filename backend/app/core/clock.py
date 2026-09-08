"""The one clock (APRAS-54).

Every datetime column in this database is naive: `timezone=True` appears in
none of the 38 migrations, so every `sa.DateTime()` is
`TIMESTAMP WITHOUT TIME ZONE`. Making them aware would be a migration over
every dated table and is deliberately not this task. The consequence is
stated once, here: a value *loaded* from the database is naive, so the value
*written* to it must be naive too, or every `loaded < now` comparison in the
codebase becomes a TypeError.

`db_now()` is UTC with `tzinfo` dropped, and that is not the same as what an
*aware* value used to become on its way into a naive column: PostgreSQL casts
an aware value to `TIMESTAMP WITHOUT TIME ZONE` by converting it into the
session's `TimeZone` first, so the stored field values depended on the
connection's zone (measured: a non-UTC session stored `10:13` where UTC
stores `13:13` for one instant). Writing naive UTC removes that dependence;
the stored instant is the UTC one on every session, which is what every
reader already assumed.

`backend/tests/test_lint_hygiene.py` asserts that this is the only module
under `app/**` whose source text reads the clock, so a second one cannot be
introduced without a red test.
"""

from datetime import UTC, date, datetime


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
