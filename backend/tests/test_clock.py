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

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from app.core import clock
from app.models.asset import Asset
from app.models.purchase import PurchaseRequest
from app.models.task import Task
from app.schemas.asset import AssetCreate
from app.schemas.purchase import PurchaseRequestCreate
from app.schemas.task import TaskCreate
from app.services.asset_service import AssetService
from app.services.purchase_service import PurchaseService
from app.services.task_service import TaskService
from tests.conftest import make_user

if TYPE_CHECKING:
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
