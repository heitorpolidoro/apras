"""§6, the suggestion algorithm, table-driven (APRAS-44 §12.1).

Seventeen cases. Six of them exist because §6.2 says *"six properties, each of
which is a test"*, so each property below names the one that proves it:

1. ``lot_id`` is absent from the predicate — ``test_recidivism_is_per_responsible_not_per_lot``
2. the window is anchored on ``occurred_on`` — ``test_suggestion_is_stable_across_days``
3. the strict ``<`` is symmetric — ``test_same_day_infractions_do_not_count_each_other``
4. a closed cycle is a cutoff, not a deletion — ``test_a_closed_cycle_is_a_cutoff_not_a_deletion``
5. ``InfractionCycleClose.lot_id`` is ignored — ``test_a_cycle_close_ignores_the_lot``
6. an unadvanced prior infraction still counts — ``test_an_unadvanced_prior_infraction_still_counts``
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func
from sqlmodel import select

from app.models.infraction import Infraction, InfractionStage
from tests.infraction_helpers import (
    LADDER_THREE,
    create_infraction,
    create_rule,
    headers,
    make_lot,
    make_member,
    make_resident,
)

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app.models.user import User


# ---------------------------------------------------------------------------
# One clock, computed per call (CR1)
# ---------------------------------------------------------------------------
#
# Every date in this module is an `occurred_on` the test *sends*, so the
# arithmetic is self-consistent whichever clock produces it -- with two
# exceptions that are not: `defense_due_on` is computed by the service with
# `date.today()` (local), so `_local_today()` is the only correct anchor for
# it. What matters everywhere is that the value is captured **per test** and
# not at import: a module-level constant makes a 15-minute suite that starts
# just before midnight compare two different days.
def _local_today() -> date:
    """The date the service computes (`applied_on`, `defense_due_on`)."""
    return date.today()



@pytest.fixture(name="staff")
def staff_fixture(session: Session) -> User:
    return make_member(session, profile="ADMINISTRATOR", seed=1)


@pytest.fixture(name="world")
def world_fixture(client: TestClient, session: Session, staff: User) -> dict:
    lot = make_lot(session)
    resident = make_resident(session, lot, seed=10)
    rule_id = create_rule(client, staff, steps=LADDER_THREE)
    return {"lot": lot, "resident": resident, "rule_id": rule_id}


def _next_step(client: TestClient, staff: User, infraction_id: str) -> dict:
    response = client.get(
        f"/api/v1/infractions/{infraction_id}/next-step", headers=headers(staff)
    )
    assert response.status_code == 200, response.text
    return response.json()


def _advance(
    client: TestClient, staff: User, infraction_id: str, **body
) -> object:
    return client.post(
        f"/api/v1/infractions/{infraction_id}/stages",
        json={"note": "Avanço.", **body},
        headers=headers(staff),
    )


# ---------------------------------------------------------------------------
# The ordinal (§6.1)
# ---------------------------------------------------------------------------


def test_first_infraction_suggests_step_one(
    client: TestClient, staff: User, world: dict
):
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    suggestion = _next_step(client, staff, infraction["id"])
    assert suggestion["recidivism_count"] == 0
    assert suggestion["stages_applied"] == 0
    assert suggestion["ladder_index"] == 1
    assert suggestion["suggested_step_order"] == 1
    assert suggestion["suggested_action"] == "AVISO"
    assert suggestion["reason"] == "SUGGESTED"
    assert suggestion["is_saturated"] is False
    assert suggestion["window_start"] == (
        date.fromisoformat(infraction["occurred_on"]) - timedelta(days=365)
    ).isoformat()


def test_advancing_moves_one_step_within_the_process(
    client: TestClient, staff: User, world: dict
):
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    assert _advance(client, staff, infraction["id"]).status_code == 201
    suggestion = _next_step(client, staff, infraction["id"])
    assert suggestion["stages_applied"] == 1
    assert suggestion["ladder_index"] == 2
    assert suggestion["suggested_action"] == "NOTIFICACAO"
    assert suggestion["defense_deadline_days"] == 30


def test_a_repeat_offender_starts_higher(
    client: TestClient, staff: User, world: dict
):
    """The ladder is not climbed twice from the bottom."""
    create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today() - timedelta(days=10),
    )
    second = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today() - timedelta(days=1),
    )
    suggestion = _next_step(client, staff, second["id"])
    assert suggestion["recidivism_count"] == 1
    assert suggestion["ladder_index"] == 2
    assert suggestion["suggested_action"] == "NOTIFICACAO"


def test_recidivism_is_per_responsible_not_per_lot(
    client: TestClient, session: Session, staff: User, world: dict
):
    """**ER-4's star test.** Same rule, same lot, different responsibles."""
    other = make_resident(session, world["lot"], seed=20)

    first = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today() - timedelta(days=10),
    )
    second = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=other,
        occurred_on=_local_today() - timedelta(days=1),
    )

    assert _next_step(client, staff, first["id"])["recidivism_count"] == 0
    assert _next_step(client, staff, second["id"])["recidivism_count"] == 0

    # ...and the lot's history stays whole and navigable.
    listed = client.get(
        "/api/v1/infractions",
        params={"lot_id": str(world["lot"].id)},
        headers=headers(staff),
    ).json()
    assert {item["id"] for item in listed["items"]} == {first["id"], second["id"]}


def test_outside_the_window_does_not_count(
    client: TestClient, session: Session, staff: User, world: dict
):
    """One day before `window_start` is not counted; one day after is.

    A 30-day window, so both sides of the boundary fit inside one test without
    a second rule.
    """
    narrow = create_rule(
        client, staff, article="art. 70", origin="ESTATUTO", window_days=30
    )
    subject_day = _local_today()
    # `window_start = subject_day - 30`. One day *before* it, and one day after.
    create_infraction(
        client,
        staff,
        rule_id=narrow,
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=subject_day - timedelta(days=31),
    )
    subject = create_infraction(
        client,
        staff,
        rule_id=narrow,
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=subject_day,
    )
    assert _next_step(client, staff, subject["id"])["recidivism_count"] == 0

    create_infraction(
        client,
        staff,
        rule_id=narrow,
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=subject_day - timedelta(days=29),
    )
    assert _next_step(client, staff, subject["id"])["recidivism_count"] == 1


def test_same_day_infractions_do_not_count_each_other(
    client: TestClient, staff: User, world: dict
):
    """§6.2 property 3: the strict `<` is symmetric; neither ordering wins."""
    first = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today(),
    )
    second = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today(),
    )
    assert _next_step(client, staff, first["id"])["recidivism_count"] == 0
    assert _next_step(client, staff, second["id"])["recidivism_count"] == 0


def test_an_unadvanced_prior_infraction_still_counts(
    client: TestClient, session: Session, staff: User, world: dict
):
    """§6.2 property 6: the count reads facts, not staff diligence."""
    create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today() - timedelta(days=5),
    )
    assert session.exec(select(func.count()).select_from(InfractionStage)).one() == 0

    later = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today(),
    )
    assert _next_step(client, staff, later["id"])["recidivism_count"] == 1


# ---------------------------------------------------------------------------
# Cycle closes (§6.2 properties 4 and 5, ER-9)
# ---------------------------------------------------------------------------


def test_a_closed_cycle_is_a_cutoff_not_a_deletion(
    client: TestClient, session: Session, staff: User, world: dict
):
    """B5. The **new** infraction restarts; the **pre-existing** one does not."""
    for offset in (20, 10):
        create_infraction(
            client,
            staff,
            rule_id=world["rule_id"],
            lot=world["lot"],
            resident=world["resident"],
            occurred_on=_local_today() - timedelta(days=offset),
        )
    existing = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today() - timedelta(days=5),
    )
    before = _next_step(client, staff, existing["id"])
    assert before["recidivism_count"] == 2

    rows_before = (
        session.exec(select(func.count()).select_from(Infraction)).one(),
        session.exec(select(func.count()).select_from(InfractionStage)).one(),
    )

    closed = client.post(
        "/api/v1/infractions/cycles/close",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(world["resident"].id),
            "justification": "Mudança de inquilino não refletida no cadastro.",
        },
        headers=headers(staff),
    )
    assert closed.status_code == 201, closed.text

    # The pre-existing process is byte-identical: the close is a cutoff going
    # forward, not a retroactive rewrite.
    assert _next_step(client, staff, existing["id"]) == before
    assert before["cycle_closed_at"] is None

    fresh = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today(),
    )
    after = _next_step(client, staff, fresh["id"])
    assert after["recidivism_count"] == 0
    assert after["ladder_index"] == 1
    assert after["cycle_closed_at"] is not None

    # Nothing was deleted.
    assert rows_before == (
        session.exec(select(func.count()).select_from(Infraction)).one() - 1,
        session.exec(select(func.count()).select_from(InfractionStage)).one(),
    )

    listed = client.get("/api/v1/infractions/cycles", headers=headers(staff))
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [closed.json()["id"]]


def test_a_cycle_close_ignores_the_lot(
    client: TestClient, session: Session, staff: User, world: dict
):
    """§6.2 property 5: a close on lot A still cuts off an infraction on lot B."""
    lot_b = make_lot(session, block="B", number="2")
    # The *same person* is the responsible on both lots -- which is the whole
    # point: recidivism follows the person, so the lot is decoration.
    resident_b = make_resident(session, lot_b, seed=30)

    create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=lot_b,
        resident=resident_b,
        occurred_on=_local_today() - timedelta(days=10),
    )
    closed = client.post(
        "/api/v1/infractions/cycles/close",
        json={
            "rule_id": world["rule_id"],
            "responsible_resident_id": str(resident_b.id),
            "lot_id": str(world["lot"].id),
            "justification": "Observado na portaria do lote A.",
        },
        headers=headers(staff),
    )
    assert closed.status_code == 201, closed.text
    assert closed.json()["lot_id"] == str(world["lot"].id)

    fresh = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=lot_b,
        resident=resident_b,
        occurred_on=_local_today(),
    )
    assert _next_step(client, staff, fresh["id"])["recidivism_count"] == 0


# ---------------------------------------------------------------------------
# Saturation and the empty ladder (§6.1, §6.5)
# ---------------------------------------------------------------------------


def test_the_ladder_saturates_at_the_last_step(
    client: TestClient, staff: User, world: dict
):
    """A three-rung ladder at index 7 suggests rung 3, CLAMPED and saturated."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    client.put(
        "/api/v1/infraction-settings",
        json={"condo_fee_amount": 100.0},
        headers=headers(staff),
    )
    for _ in range(6):
        assert _advance(client, staff, infraction["id"]).status_code == 201

    suggestion = _next_step(client, staff, infraction["id"])
    assert suggestion["ladder_index"] == 7
    assert suggestion["suggested_step_order"] == 3
    assert suggestion["suggested_action"] == "MULTA"
    assert suggestion["is_saturated"] is True
    assert suggestion["reason"] == "CLAMPED"


def test_saturated_is_not_clamped_at_the_last_step(
    client: TestClient, staff: User, world: dict
):
    """They disagree at exactly `ladder_index == n`, and that is the point."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    for _ in range(2):
        assert _advance(client, staff, infraction["id"]).status_code == 201

    suggestion = _next_step(client, staff, infraction["id"])
    assert suggestion["ladder_index"] == 3
    assert suggestion["is_saturated"] is True
    assert suggestion["reason"] == "SUGGESTED"


def test_an_empty_ladder_answers_no_policy(
    client: TestClient, staff: User, world: dict
):
    """B3: 200, not 404 and not 409 -- a read of a legitimate state."""
    bare = create_rule(client, staff, article="art. 99", origin="ESTATUTO")
    infraction = create_infraction(
        client, staff, rule_id=bare, lot=world["lot"], resident=world["resident"]
    )

    suggestion = _next_step(client, staff, infraction["id"])
    assert suggestion["suggested_step_order"] is None
    assert suggestion["suggested_action"] is None
    assert suggestion["reason"] == "NO_POLICY"
    assert suggestion["is_saturated"] is False
    assert suggestion["fine_amount"] is None
    # The fee is not the reason; there is no step to price.
    assert suggestion["fine_amount_unavailable_reason"] is None
    assert suggestion["recidivism_count"] == 0
    assert suggestion["stages_applied"] == 0
    assert suggestion["ladder_index"] == 1
    assert suggestion["window_start"] is not None


def test_accepting_a_suggestion_with_no_policy_is_409(
    client: TestClient, session: Session, staff: User, world: dict
):
    """B3: `action = null` cannot be honoured, and nothing is written."""
    bare = create_rule(client, staff, article="art. 99", origin="ESTATUTO")
    infraction = create_infraction(
        client, staff, rule_id=bare, lot=world["lot"], resident=world["resident"]
    )
    before = session.exec(select(func.count()).select_from(InfractionStage)).one()

    refused = _advance(client, staff, infraction["id"])
    assert refused.status_code == 409
    assert refused.json()["detail"] == "Rule has no escalation policy"
    assert (
        session.exec(select(func.count()).select_from(InfractionStage)).one()
        == before
    )


def test_an_explicit_action_is_accepted_with_no_policy(
    client: TestClient, staff: User, world: dict
):
    """B3: the ladder is a suggestion engine, not a gate on staff judgement."""
    bare = create_rule(client, staff, article="art. 99", origin="ESTATUTO")
    infraction = create_infraction(
        client, staff, rule_id=bare, lot=world["lot"], resident=world["resident"]
    )

    applied = _advance(client, staff, infraction["id"], action="AVISO")
    assert applied.status_code == 201, applied.text
    entry = applied.json()["timeline"][0]
    assert entry["action"] == "AVISO"
    assert entry["policy_step_order"] is None
    assert entry["suggestion_followed"] is False


# ---------------------------------------------------------------------------
# Two rules, two ladders (ER-2)
# ---------------------------------------------------------------------------


def test_two_rules_of_one_tenant_escalate_differently(
    client: TestClient, staff: User, world: dict
):
    """**ER-2's star test.** Rule A = `[MULTA]`; rule B = `[AVISO, AVISO, MULTA]`."""
    rule_a = create_rule(
        client,
        staff,
        article="art. 51",
        origin="CONVENCAO",
        steps=[
            {
                "step_order": 1,
                "action": "MULTA",
                "fine_mode": "FIXED",
                "fine_fixed_amount": 500.0,
            }
        ],
    )
    rule_b = create_rule(
        client,
        staff,
        article="art. 52",
        origin="CONVENCAO",
        steps=[
            {"step_order": 1, "action": "AVISO"},
            {"step_order": 2, "action": "AVISO"},
            {
                "step_order": 3,
                "action": "MULTA",
                "fine_mode": "FIXED",
                "fine_fixed_amount": 500.0,
            },
        ],
    )

    first_a = create_infraction(
        client, staff, rule_id=rule_a, lot=world["lot"], resident=world["resident"]
    )
    first_b = create_infraction(
        client, staff, rule_id=rule_b, lot=world["lot"], resident=world["resident"]
    )

    assert _next_step(client, staff, first_a["id"])["suggested_action"] == "MULTA"
    assert _next_step(client, staff, first_b["id"])["suggested_action"] == "AVISO"


def test_fixed_and_multiple_fine_values(
    client: TestClient, staff: User, world: dict
):
    """FIXED returns the literal; MULTIPLE returns `multiplier * fee`, 2 places."""
    client.put(
        "/api/v1/infraction-settings",
        json={"condo_fee_amount": 333.33},
        headers=headers(staff),
    )
    fixed = create_rule(
        client,
        staff,
        article="art. 61",
        origin="CONVENCAO",
        steps=[
            {
                "step_order": 1,
                "action": "MULTA",
                "fine_mode": "FIXED",
                "fine_fixed_amount": 120.0,
            }
        ],
    )
    multiple = create_rule(
        client,
        staff,
        article="art. 62",
        origin="CONVENCAO",
        steps=[
            {
                "step_order": 1,
                "action": "MULTA",
                "fine_mode": "MULTIPLE",
                "fine_fee_multiplier": 1.5,
            }
        ],
    )

    one = create_infraction(
        client, staff, rule_id=fixed, lot=world["lot"], resident=world["resident"]
    )
    two = create_infraction(
        client, staff, rule_id=multiple, lot=world["lot"], resident=world["resident"]
    )
    assert _next_step(client, staff, one["id"])["fine_amount"] == 120.0
    assert _next_step(client, staff, two["id"])["fine_amount"] == 500.0


def test_suggestion_is_stable_across_days(
    client: TestClient, staff: User, world: dict
):
    """§6.2 property 2: the window is anchored on `occurred_on`, not on today.

    Asserted by *derivation* rather than by freezing the clock: `window_start`
    is a pure function of `occurred_on` and the rule's window, so two reads on
    different days cannot differ.
    """
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
        occurred_on=_local_today() - timedelta(days=100),
    )
    first = _next_step(client, staff, infraction["id"])
    second = _next_step(client, staff, infraction["id"])
    assert first == second
    assert first["window_start"] == (
        _local_today() - timedelta(days=100 + 365)
    ).isoformat()


def test_explicit_action_records_a_deviation(
    client: TestClient, staff: User, world: dict
):
    """ER-4, read literally: **any** explicit action is a deviation on record."""
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )
    applied = _advance(client, staff, infraction["id"], action="NOTIFICACAO")
    assert applied.status_code == 201, applied.text
    entry = applied.json()["timeline"][0]
    assert entry["suggestion_followed"] is False
    # The deadline is borrowed from the ladder's own NOTIFICACAO rung, so an
    # off-ladder application is still priced by policy where policy has an
    # answer (the decision the spec left open).
    assert entry["defense_due_on"] == (_local_today() + timedelta(days=30)).isoformat()


def test_an_off_ladder_action_borrows_the_last_rung_of_its_own_kind(
    client: TestClient, staff: User, world: dict
):
    """S-6: the `max(step_order)` tie-break, with **two** rungs of one action.

    A ladder with two `MULTA` rungs at different prices is the only shape in
    which "last rung of the same action" is a *decision* rather than the single
    available answer. The last one is the right choice: reaching past the
    suggestion for a sanction is an escalation, and borrowing the cheaper early
    rung would quietly under-price one staff chose deliberately.

    The ladder starts with an `AVISO` on purpose. When the explicit action
    **coincides** with the suggestion the service uses the suggested rung
    instead -- the policy's own terms for this position -- so a ladder whose
    first rung is already a `MULTA` never reaches the tie-break at all. (That
    is how the first draft of this test passed for the wrong reason.)
    """
    rule_id = create_rule(
        client,
        staff,
        article="art. 77",
        origin="CONVENCAO",
        steps=[
            {"step_order": 1, "action": "AVISO"},
            {
                "step_order": 2,
                "action": "MULTA",
                "fine_mode": "FIXED",
                "fine_fixed_amount": 100.0,
            },
            {
                "step_order": 3,
                "action": "MULTA",
                "fine_mode": "FIXED",
                "fine_fixed_amount": 900.0,
            },
        ],
    )
    infraction = create_infraction(
        client, staff, rule_id=rule_id, lot=world["lot"], resident=world["resident"]
    )

    # The suggestion is rung 1, an AVISO -- so an explicit MULTA is off-ladder.
    suggestion = _next_step(client, staff, infraction["id"])
    assert suggestion["suggested_action"] == "AVISO"
    assert suggestion["fine_amount"] is None

    applied = _advance(client, staff, infraction["id"], action="MULTA")
    assert applied.status_code == 201, applied.text
    entry = applied.json()["timeline"][0]
    assert entry["fine_amount"] == 900.0
    assert entry["fine_amount_overridden"] is False
    assert entry["suggestion_followed"] is False
    assert entry["policy_step_order"] is None


def test_an_explicit_deadline_is_recorded_as_an_override(
    client: TestClient, staff: User, world: dict
):
    """S-5: `defense_deadline_overridden` mirrors `fine_amount_overridden`.

    Without it the audit trail can say "a human chose this value" for a fine
    and only "a human chose this action" for a deadline, which is a different
    and weaker claim.
    """
    infraction = create_infraction(
        client,
        staff,
        rule_id=world["rule_id"],
        lot=world["lot"],
        resident=world["resident"],
    )

    borrowed = _advance(client, staff, infraction["id"], action="NOTIFICACAO")
    assert borrowed.status_code == 201, borrowed.text
    entry = borrowed.json()["timeline"][0]
    # 30 days, taken from the ladder's own NOTIFICACAO rung.
    assert entry["defense_due_on"] == (
        _local_today() + timedelta(days=30)
    ).isoformat()
    assert entry["defense_deadline_overridden"] is False

    typed = _advance(
        client,
        staff,
        infraction["id"],
        action="NOTIFICACAO",
        defense_deadline_days=5,
    )
    assert typed.status_code == 201, typed.text
    entry = typed.json()["timeline"][1]
    assert entry["defense_due_on"] == (
        _local_today() + timedelta(days=5)
    ).isoformat()
    assert entry["defense_deadline_overridden"] is True


def test_an_explicit_multa_on_an_unpriced_multiple_rung_is_still_409(
    client: TestClient, staff: User, world: dict
):
    """S-7: "an explicit action is always 201" was **wrong** in the PR body.

    An explicit `MULTA` that resolves to a `MULTIPLE` rung with no
    `condo_fee_amount` and no `fine_amount` in the body is a 409 — the same
    §6.3 refusal the accepted suggestion gets, and correctly so: the world has
    no value to record. Staff always have the explicit-`fine_amount` escape,
    which is what keeps §6.4's "the ladder is not a gate on staff judgement"
    true. Asserted here so the sentence cannot drift back.
    """
    rule_id = create_rule(
        client,
        staff,
        article="art. 88",
        origin="CONVENCAO",
        steps=[
            {"step_order": 1, "action": "AVISO"},
            {
                "step_order": 2,
                "action": "MULTA",
                "fine_mode": "MULTIPLE",
                "fine_fee_multiplier": 2.0,
            },
        ],
    )
    infraction = create_infraction(
        client, staff, rule_id=rule_id, lot=world["lot"], resident=world["resident"]
    )
    # The suggestion is the AVISO, so the MULTA below is genuinely off-ladder.
    assert (
        _next_step(client, staff, infraction["id"])["suggested_action"] == "AVISO"
    )

    refused = _advance(client, staff, infraction["id"], action="MULTA")
    assert refused.status_code == 409
    assert refused.json()["detail"] == "The condominium fee reference is not set"

    # The escape, and the only one: name the value.
    escaped = _advance(
        client, staff, infraction["id"], action="MULTA", fine_amount=42.0
    )
    assert escaped.status_code == 201, escaped.text
    assert escaped.json()["timeline"][0]["fine_amount"] == 42.0
