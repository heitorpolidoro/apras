"""The stored instant did not move when the writers stopped being aware.

APRAS-54 §4.4 rows 6, 8 and 9: `Task`, `Asset` and `PurchaseRequest` were the
three subsystems writing a **tz-aware** `datetime.now(UTC)` into a **naive**
`TIMESTAMP WITHOUT TIME ZONE` column, relying on the database to coerce it on
every write. They now write `clock.db_now()`, which performs that same
coercion one step earlier, in Python, where it is visible.

One read-back per model, because a green suite elsewhere only proves the
values are *close enough* to whatever the assertions happened to allow. What
these three prove is the two properties the switch could have broken: the
value comes back **naive**, and it is still **now**.
"""

from __future__ import annotations

import importlib
import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from sqlmodel import SQLModel, select
from sqlmodel.sql.sqltypes import UTCDateTime

from app.core import clock, money
from app.core.security import get_password_hash
from app.models.asset import Asset
from app.models.lot import UserLotLink
from app.models.purchase import PurchaseRequest
from app.models.reservation import ReservableSpace, SpaceReservation
from app.models.task import Task
from app.models.visitor import VisitorAuthorization
from app.schemas.asset import AssetCreate
from app.schemas.base import ApiModel
from app.schemas.lot import LotCreate
from app.schemas.purchase import PurchaseRequestCreate
from app.schemas.task import TaskCreate
from app.schemas.visitor import VisitorCreate
from app.services.asset_service import AssetService
from app.services.lot_service import LotService
from app.services.purchase_service import PurchaseService
from app.services.task_service import TaskService
from app.services.visitor_service import VisitorService
from tests.conftest import make_user

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app.models.user import User

#: How far a stored stamp may sit from "now" -- the spec's one second. The
#: write and the read-back are adjacent statements, so anything outside this
#: means the instant genuinely moved rather than that the machine was busy.
TOLERANCE_SECONDS = 1


@pytest.fixture(name="author")
def author_fixture(session: Session) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="clock@test.com",
        full_name="Clock Author",
        hashed_password="hash",
        profile="ADMINISTRATOR",
        cpf="12345678909",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _assert_naive_and_recent(value: datetime, label: str) -> None:
    assert value.tzinfo is None, (
        f"{label} came back tz-aware; the column is TIMESTAMP WITHOUT TIME "
        "ZONE and every reader compares it to a naive value"
    )
    delta = abs((datetime.now(UTC).replace(tzinfo=None) - value).total_seconds())
    assert delta < TOLERANCE_SECONDS, (
        f"{label} is {delta:.1f}s from now -- the stored instant moved"
    )


#: Columns deliberately migrated to `timestamp with time zone`, as
#: `"table.column"`. **Empty today**, and that is the whole point: APRAS-54
#: deferred route 2 -- the migration that would make some of these columns
#: genuinely aware -- rather than ruling it out, so the naive assertion below
#: must not become the second wall in front of it. A route-2 task adds its
#: columns here in the same commit as its migration and its rewrite of
#: `clock`'s contract, and the suite passes; an *accidental* aware column is
#: not in this ledger and still reddens.
#:
#: This is the shape the two bcrypt-cost tests should have had and did not:
#: they pinned a security floor so rigidly that legitimately *raising* it
#: failed CI. So the ledger is checked in both directions -- a name listed
#: here whose column is naive reddens too, which stops it rotting into a list
#: of excuses nobody revisits.
AWARE_COLUMNS: frozenset[str] = frozenset()

#: The vacuity floor for the metadata scan. 108 columns qualify today; the
#: floor sits under that so a legitimately deleted dated field does not redden
#: a test about column *types*, while any broken selector -- one that unwraps
#: nothing, or resolves nothing -- falls far below it and cannot pass.
DATED_COLUMN_FLOOR = 100


def _dated_columns() -> dict[str, sa.types.TypeEngine]:
    """Every `datetime`-ish column in the metadata, by `"table.column"`.

    The unwrapping is load-bearing, not defensive. Measured on sqlmodel
    0.0.47 + SQLAlchemy 2.0.49: a bare `datetime` annotation resolves to
    `UTCDateTime`, which is a `TypeDecorator`, so **both** obvious selectors
    skip such a column in silence -- `isinstance(column.type, sa.DateTime)`
    is `False`, and `column.type.python_type` *raises* `NotImplementedError`.
    A scan written either way passes the very mutation it exists to catch.
    Selecting on the decorator's `impl_instance` as well is what makes the
    reverted column visible so the assertion can reject it.

    `sa.Date` is deliberately not matched: it is not a `sa.DateTime` subclass,
    and the 12 calendar-`date` fields in `app/models/` are not this test's
    subject.
    """
    # Imported for its side effect -- registering every mapper -- so the
    # metadata is exhaustive. `importlib` rather than a bare `import
    # app.models`, because the latter is an unused binding that would need a
    # per-line F401 suppression, and this task does not raise the cap
    # `test_lint_hygiene.py` keeps on those.
    importlib.import_module("app.models")

    found: dict[str, sa.types.TypeEngine] = {}
    for table in SQLModel.metadata.sorted_tables:
        for column in table.columns:
            unwrapped = getattr(column.type, "impl_instance", None)
            if isinstance(column.type, sa.DateTime) or isinstance(
                unwrapped, sa.DateTime
            ):
                found[f"{table.name}.{column.name}"] = column.type
    return found


def test_every_datetime_column_is_naive_unless_the_ledger_says_otherwise() -> None:
    """The columns are naive by *annotation*, not merely by migration history.

    This is the only assertion in the suite that names an offending column
    from `SQLModel.metadata` alone, with no database involved. Reverting one
    model field to a bare `datetime` reddens some 1,800 nodes across 20
    modules, because the write itself raises -- but every one of those names a
    `StatementError` at a call site, and this one names
    `task.created_at: UTCDateTime()`.
    """
    columns = _dated_columns()
    assert len(columns) >= DATED_COLUMN_FLOOR, (
        f"the metadata scan found only {len(columns)} dated columns, under the "
        f"floor of {DATED_COLUMN_FLOOR}; the selector is broken, not the "
        "schema -- a scan that unwraps no `TypeDecorator` and resolves no "
        "mapper finds far fewer than the 108 that exist"
    )

    offenders: list[str] = []
    for name, type_ in sorted(columns.items()):
        is_naive = (
            type(type_) is sa.DateTime
            and not isinstance(type_, UTCDateTime)
            and type_.timezone is False
        )
        if name in AWARE_COLUMNS and is_naive:
            offenders.append(
                f"{name}: {type_!r} is naive, but AWARE_COLUMNS claims it was "
                "deliberately migrated to `timestamp with time zone` -- "
                "remove the stale entry"
            )
        elif name not in AWARE_COLUMNS and not is_naive:
            offenders.append(f"{name}: {type_!r}")

    assert not offenders, (
        "every datetime column must be exactly `sa.DateTime` with `timezone` "
        "false -- annotate the model field `NaiveDatetime`, since a bare "
        "`datetime` resolves to sqlmodel's `UTCDateTime` and emits "
        "`TIMESTAMP WITH TIME ZONE`, which no migration in this repository "
        "creates:\n" + "\n".join(offenders)
    )


def test_clock_helpers_agree_on_one_instant() -> None:
    """`db_now` is `utc_now` without `tzinfo`, and `today_utc` its date."""
    assert clock.utc_now().tzinfo is UTC
    assert clock.db_now().tzinfo is None
    _assert_naive_and_recent(clock.db_now(), "clock.db_now()")
    assert clock.today_utc() == clock.utc_now().date()


def test_task_created_at_is_stored_naive(session: Session, author: User) -> None:
    """`Task` -- §4.4 row 6, the deleted `models.task.get_utc_now`."""
    created = TaskService.create_task(
        session,
        TaskCreate(title="Clock read-back"),
        created_by_id=author.id,
        current_user=author,
    )

    # Drop the identity map: without this `get` can hand back the very
    # object that was just written, and the assertion would never reach
    # the column it is about.
    session.expire_all()
    stored = session.get(Task, created.id)
    assert stored is not None
    _assert_naive_and_recent(stored.created_at, "Task.created_at")
    _assert_naive_and_recent(stored.updated_at, "Task.updated_at")


def test_asset_created_at_is_stored_naive(session: Session, author: User) -> None:
    """`Asset` -- §4.4 rows 8 and 9, `models/asset.py` + `asset_service.py`."""
    read = AssetService.create_asset(
        session,
        author,
        AssetCreate(
            name="Cortador de Grama",
            category="FERRAMENTAS",
            location="Almoxarifado Central",
        ),
    )

    # Drop the identity map: without this `get` can hand back the very
    # object that was just written, and the assertion would never reach
    # the column it is about.
    session.expire_all()
    stored = session.get(Asset, read.id)
    assert stored is not None
    _assert_naive_and_recent(stored.created_at, "Asset.created_at")
    _assert_naive_and_recent(stored.updated_at, "Asset.updated_at")


def test_purchase_request_created_at_is_stored_naive(
    session: Session, author: User
) -> None:
    """`PurchaseRequest` -- §4.4 rows 8 and 9, the purchase subsystem."""
    read = PurchaseService.create_request(
        session,
        author,
        PurchaseRequestCreate(title="Troca das bombas"),
    )

    # Drop the identity map: without this `get` can hand back the very
    # object that was just written, and the assertion would never reach
    # the column it is about.
    session.expire_all()
    stored = session.get(PurchaseRequest, read.id)
    assert stored is not None
    _assert_naive_and_recent(stored.created_at, "PurchaseRequest.created_at")
    _assert_naive_and_recent(stored.updated_at, "PurchaseRequest.updated_at")


# ---------------------------------------------------------------------------
# One rule for instants: everything stored is UTC (APRAS-120 parts 4 and 6)
# ---------------------------------------------------------------------------

#: Naive wall-clock literals, built with `fromisoformat` rather than the
#: `datetime(...)` constructor. The constructor form is a `DTZ001` finding and
#: would need a per-line suppression each; `fromisoformat` of an offsetless
#: string is the same naive value with no directive, and APRAS-120 does not
#: raise the cap `test_lint_hygiene.py` keeps on those.
JUNE_1_AT_10 = datetime.fromisoformat("2026-06-01T10:00:00")
JUNE_1_AT_11 = datetime.fromisoformat("2026-06-01T11:00:00")
JUNE_1_AT_13 = datetime.fromisoformat("2026-06-01T13:00:00")
JUNE_1_AT_14 = datetime.fromisoformat("2026-06-01T14:00:00")

#: `America/Sao_Paulo` has been a flat -03:00 since Brazil abolished DST in
#: 2019, so this is a constant rather than a date-dependent lookup.
SAO_PAULO_OFFSET = timedelta(hours=-3)


def _token(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(name="admin_headers")
def admin_headers_fixture(client: TestClient, admin_user: User) -> dict[str, str]:
    """Bearer headers for the shared ADMINISTRATOR fixture."""
    assert admin_user is not None
    return {"Authorization": f"Bearer {_token(client, 'admin', 'test_admin_password')}"}


@pytest.fixture(name="sao_paulo_process_zone")
def sao_paulo_process_zone_fixture() -> Iterator[None]:
    """Force the *process* zone to `America/Sao_Paulo` for one test.

    This fixture is a test criterion, not a convenience. `to_db` must treat an
    offsetless value as already-UTC, and the way to get that wrong is to pass
    it to a bare `astimezone(UTC)`, which assumes the **process's local zone**.
    Both CI and production run UTC, where that mistake is invisible: the
    unguarded and the guarded implementation store the same value, so a suite
    without this fixture stays green on either. Running one test somewhere
    other than UTC is what makes the guard observable.

    The `utcoffset()` assertion is the premise, checked before any property
    depends on it: `tzset()` is a libc call, and a machine where it did nothing
    -- or a container with no zone database -- would otherwise let this test
    pass while proving nothing at all. `datetime.now(UTC).astimezone()` rather
    than `datetime.now()` for the reading, because the latter is a `DTZ005`
    finding; converting an aware instant into the local zone reports the same
    offset.
    """
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "America/Sao_Paulo"
    time.tzset()
    try:
        assert datetime.now(UTC).astimezone().utcoffset() == SAO_PAULO_OFFSET, (
            "the process zone did not become America/Sao_Paulo, so this test "
            "would run in UTC and pass whether or not `to_db` guards a naive "
            "value -- check that the machine has a zone database and that "
            "time.tzset() is supported here"
        )
        yield
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


def test_to_db_reads_an_offsetless_value_as_utc_in_any_process_zone() -> None:
    """`to_db` of a naive value does not depend on where the server runs.

    The unit half of the zone-independence property. An unguarded
    `astimezone(UTC)` turns naive `10:00` into `13:00` under
    `America/Sao_Paulo` and leaves it at `10:00` under UTC, so the stored
    instant would be a function of the deployment's zone. Both zones are
    exercised in one test, so the comparison is between two *results* rather
    than between one result and a hardcoded expectation.
    """
    results: dict[str, datetime] = {}
    previous = os.environ.get("TZ")
    try:
        for zone in ("UTC", "America/Sao_Paulo"):
            os.environ["TZ"] = zone
            time.tzset()
            results[zone] = clock.to_db(JUNE_1_AT_10)
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()

    assert results["UTC"] == results["America/Sao_Paulo"], (
        f"to_db moved a naive value by the process's local offset: {results}. "
        "A naive value is already UTC by this contract and must be returned "
        "unchanged, never passed to a bare astimezone()"
    )
    assert results["UTC"] == JUNE_1_AT_10


def test_to_db_subtracts_the_offset_of_an_aware_value() -> None:
    """The other branch: an aware value converts, so the instant is preserved."""
    assert clock.to_db(datetime.fromisoformat("2026-06-01T13:00:00+03:00")) == (
        JUNE_1_AT_10
    )
    assert clock.to_db(datetime.fromisoformat("2026-06-01T10:00:00Z")) == JUNE_1_AT_10


def test_to_api_stamps_a_stored_instant_utc_without_moving_it() -> None:
    """`to_api` adds the offset the stored value always had."""
    stamped = clock.to_api(JUNE_1_AT_13)
    assert stamped.utcoffset() == timedelta(0)
    assert stamped.replace(tzinfo=None) == JUNE_1_AT_13
    # Aware in is normalised rather than rejected or counted twice.
    assert clock.to_api(datetime.fromisoformat("2026-06-01T16:00:00+03:00")) == (
        JUNE_1_AT_13.replace(tzinfo=UTC)
    )


def test_authorization_valid_from_with_an_offset_is_stored_as_naive_utc(
    client: TestClient, session: Session, admin_headers: dict[str, str]
) -> None:
    """T3: an offset in a request body is accepted, and *subtracted*.

    The status code is the uninteresting half. Without `to_db`'s alias on
    `VisitorAuthorizationCreate.valid_from` this request still answers 201 and
    still commits: SQLModel skips Pydantic validation on `table=True` models,
    so an aware value in a `NaiveDatetime` field is written, and on SQLite the
    offset is **discarded without being converted** -- `+03:00 13:00` would
    store `13:00`. So the assertion that matters is on the stored column, read
    after `expire_all()` so it comes from the database rather than from the
    identity map.
    """
    lot = LotService.create_lot(session, LotCreate(block="Z", lot_number="99"))
    visitor = VisitorService.create_visitor(
        session, VisitorCreate(full_name="Offset Visitor")
    )

    response = client.post(
        f"/api/v1/lots/{lot.id}/authorizations",
        headers=admin_headers,
        json={
            "visitor_id": str(visitor.id),
            "auth_type": "SINGLE",
            "valid_from": "2026-06-01T13:00:00+03:00",
        },
    )
    assert response.status_code == 201, response.text

    session.expire_all()
    stored = session.exec(select(VisitorAuthorization)).one()
    assert stored.valid_from == JUNE_1_AT_10, (
        "valid_from arrived as 13:00+03:00, which is 10:00 UTC, and the column "
        "holds naive UTC -- storing 13:00 means the offset was dropped instead "
        f"of subtracted (got {stored.valid_from!r})"
    )
    assert stored.valid_from is not None
    assert stored.valid_from.tzinfo is None


@pytest.mark.usefixtures("sao_paulo_process_zone")
def test_reservation_start_time_stores_the_same_utc_instant_in_any_zone(
    client: TestClient, session: Session
) -> None:
    """T7: `Z` and offsetless store the same value, outside UTC.

    Two payloads differing only in the trailing `Z`. The first is what every
    real client sends (`new Date(v).toISOString()`); the second is the
    "offsetless means UTC" decision, and it is the one that reddens if `to_db`
    loses its `tzinfo is None` guard -- but *only* when the process zone is not
    UTC, which `sao_paulo_process_zone` is for.
    """
    space = ReservableSpace(name="Salão")
    session.add(space)
    session.commit()
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="tz@test.com",
        full_name="Zone Resident",
        hashed_password=get_password_hash("pass"),
        profile="RESIDENT",
        cpf="88289649000",
    )
    session.add(user)
    session.commit()
    headers = {"Authorization": f"Bearer {_token(client, 'tz', 'pass')}"}

    for index, start in enumerate(
        ("2026-06-01T10:00:00Z", "2026-06-01T10:00:00"),
    ):
        # A fresh day per iteration so the second request is not a conflict
        # with the first; the *time of day* is what this test is about.
        day = 1 + index
        response = client.post(
            "/api/v1/space-reservations/",
            headers=headers,
            json={
                "space_id": str(space.id),
                "start_time": start.replace("06-01", f"06-0{day}"),
                "end_time": start.replace("06-01", f"06-0{day}").replace(
                    "10:00", "11:00"
                ),
            },
        )
        assert response.status_code == 201, (start, response.text)

        session.expire_all()
        stored = session.exec(
            select(SpaceReservation).where(SpaceReservation.start_time >= JUNE_1_AT_10)
        ).all()
        match = [row for row in stored if row.start_time.day == day]
        assert len(match) == 1, (start, stored)
        assert match[0].start_time == JUNE_1_AT_10.replace(day=day), (
            f"{start!r} stored {match[0].start_time!r}; under "
            "America/Sao_Paulo an unguarded astimezone(UTC) on the offsetless "
            "value yields 13:00, which is the defect this test exists for"
        )


def test_response_datetimes_carry_utc_and_calendar_dates_do_not(
    client: TestClient,
    session: Session,
    admin_user: User,
    admin_headers: dict[str, str],
) -> None:
    """T8: the display defect, end to end, and the calendar-date exception.

    The timestamp half is asserted on the *parsed* offset rather than on string
    equality, so it fails when the offset is **absent** instead of merely
    passing when some string is present. Offsetless is exactly today's
    production behaviour, and it is why a reservation booked at 10:00 BRT reads
    back as 13:00 in the browser.

    The calendar half is the other direction: `due_date`, `start_date` and
    `end_date` hold calendar dates in `DateTime` columns, and stamping them UTC
    would move the day backwards in every negative-offset zone.
    """
    space = ReservableSpace(name="Quadra")
    session.add(space)
    reservation = SpaceReservation(
        space_id=space.id,
        reserved_by_id=admin_user.id,
        start_time=JUNE_1_AT_13,
        end_time=JUNE_1_AT_14,
    )
    session.add(reservation)
    task = Task(
        title="Dated task",
        created_by_id=admin_user.id,
        due_date=datetime.fromisoformat("2026-09-10"),
    )
    session.add(task)
    lot = LotService.create_lot(session, LotCreate(block="Y", lot_number="7"))
    session.add(
        UserLotLink(
            user_id=admin_user.id,
            lot_id=lot.id,
            start_date=datetime.fromisoformat("2026-09-10"),
            end_date=datetime.fromisoformat("2026-12-31"),
        )
    )
    session.commit()

    listed = client.get("/api/v1/space-reservations/", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    payload = rows["items"] if isinstance(rows, dict) else rows
    start_time = payload[0]["start_time"]

    parsed = datetime.fromisoformat(start_time)
    assert parsed.tzinfo is not None, (
        f"start_time came back as {start_time!r}, with no offset. The column "
        "holds UTC and the browser does new Date(x).toLocaleString(), which "
        "reads an offsetless string as *local* time -- this is the three-hour "
        "display defect ApiModel exists to fix"
    )
    assert parsed.utcoffset() == timedelta(0)
    assert parsed == JUNE_1_AT_13.replace(tzinfo=UTC)

    # `GET /tasks/` is the task read path; the router exposes no
    # `/tasks/{task_id}`, so this is the response a client actually sees.
    fetched = client.get("/api/v1/tasks/", headers=admin_headers)
    assert fetched.status_code == 200, fetched.text
    body = fetched.json()
    tasks = body["items"] if isinstance(body, dict) else body
    dated = [row for row in tasks if row["id"] == str(task.id)]
    assert len(dated) == 1, tasks
    due_date = dated[0]["due_date"]
    assert due_date is not None, "the task was created with a due_date"
    assert datetime.fromisoformat(due_date).tzinfo is None, (
        f"due_date came back as {due_date!r}, carrying an offset. It is a "
        "calendar date in a DateTime column, and taskUtils.ts does "
        "startOfDay(new Date(due_date)): with +00:00 the badge reads Sep 9 in "
        "BRT instead of the Sep 10 the user picked"
    )

    lot_detail = client.get(f"/api/v1/lots/{lot.id}", headers=admin_headers)
    assert lot_detail.status_code == 200, lot_detail.text
    links = lot_detail.json()["users"]
    assert len(links) == 1, (
        f"expected the one seeded user link, got {links}; a loop over an empty "
        "list below would assert nothing at all"
    )
    for field in ("start_date", "end_date"):
        value = links[0][field]
        assert value is not None, (
            f"UserLotLink.{field} was seeded non-null, so a null here means "
            "the assertion below never looks at a date"
        )
        assert datetime.fromisoformat(value).tzinfo is None, (
            f"UserLotLink.{field} came back as {value!r}, carrying an offset; "
            'it is a calendar date whose form is type="date", so stamping it '
            "UTC moves the day backwards in every negative-offset zone"
        )


def test_api_model_preserves_the_money_serialiser_it_wraps() -> None:
    """`ApiModel` composes with `app/core/money.py` instead of overriding it.

    This test exists because the obvious implementation of the UTC read rule
    breaks the money contract, silently, in a way no money test names. A
    `@field_serializer("*")` **replaces** whatever serialiser an individual
    field declared, and every monetary field declares one --
    `PlainSerializer(float, return_type=float, when_used="json")` -- which is
    what makes `NUMERIC(12, 2)` reach the wire as `350.0` instead of
    pydantic's default `Decimal` rendering `"350.00"`. Attaching the wildcard
    reverted that for 43 assertions across the finance, purchase and plan
    suites, all of them reading `assert data["amount"] == 350.0`.

    `ApiModel` therefore wraps (`mode="wrap"`): `handler(self)` runs the normal
    serialisation, per-field serialisers included, and only the datetime
    entries are rewritten. Asserting both halves *in one model* is the point --
    a datetime that gained its offset and a `Decimal` that stayed a JSON number
    are the two properties that have to hold simultaneously, and the earlier
    implementation satisfied only the first.
    """

    class Mixed(ApiModel):
        amount: money.Money
        at: datetime

    dumped = Mixed(amount=Decimal("350.00"), at=JUNE_1_AT_13).model_dump(mode="json")

    assert dumped["amount"] == 350.0, (
        f"money serialised as {dumped['amount']!r}; a `Decimal` reaching the "
        "wire as a *string* means ApiModel overrode money.MONEY_SER rather "
        "than wrapping it"
    )
    assert not isinstance(dumped["amount"], str)
    assert dumped["at"] == "2026-06-01T13:00:00+00:00"
