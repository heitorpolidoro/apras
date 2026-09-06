"""The rule catalogue and its escalation ladder (APRAS-44 §12.1).

Eight cases. §7.7's two create-time validations live in
``tests/test_infractions.py`` and not here, because they are validations of
``POST /infractions``, not of the catalogue's own routes.
"""


import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.infraction import InfractionRule
from app.models.tenant import Tenant, UserTenantLink
from app.models.user import User
from tests.infraction_helpers import (
    headers as _headers,
)
from tests.infraction_helpers import (
    make_lot,
    make_member,
    make_resident,
)


@pytest.fixture(name="staff")
def staff_fixture(session: Session) -> User:
    """An ADMINISTRATOR-profile superuser: it holds the whole catalogue."""
    return make_member(session, profile="ADMINISTRATOR", seed=1)


RULE_BODY = {
    "article": "art. 12, §2º",
    "origin": "REGIMENTO_INTERNO",
    "description": "Perturbação do sossego após as 22h.",
    "recidivism_window_days": 365,
}


def test_create_and_list_a_rule(client: TestClient, staff: User):
    """201, and the rule reads back with every catalogue field."""
    created = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["article"] == "art. 12, §2º"
    assert body["origin"] == "REGIMENTO_INTERNO"
    assert body["description"] == RULE_BODY["description"]
    assert body["recidivism_window_days"] == 365
    assert body["is_active"] is True
    # A rule is born without a ladder, and that is a legitimate state (§6.5).
    assert body["steps"] == []

    listed = client.get("/api/v1/infraction-rules", headers=_headers(staff))
    assert listed.status_code == 200
    assert [rule["id"] for rule in listed.json()] == [body["id"]]

    fetched = client.get(
        f"/api/v1/infraction-rules/{body['id']}", headers=_headers(staff)
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_duplicate_article_and_origin_is_rejected(
    client: TestClient, session: Session, staff: User
):
    """409 in the same tenant, 201 in another: uniqueness is per tenant."""
    assert (
        client.post(
            "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
        ).status_code
        == 201
    )
    duplicate = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    )
    assert duplicate.status_code == 409
    assert "art. 12, §2º" in duplicate.json()["detail"]

    # The same (origin, article) in a *second* tenant is a different article
    # of a different condominium's regimento.
    other = Tenant(name="Condomínio Vizinho")
    session.add(other)
    session.commit()
    session.refresh(other)
    session.add(UserTenantLink(user_id=staff.id, tenant_id=other.id))
    session.commit()

    elsewhere = client.post(
        "/api/v1/infraction-rules",
        json=RULE_BODY,
        headers=_headers(staff, other.id),
    )
    assert elsewhere.status_code == 201, elsewhere.text


def test_delete_deactivates_and_keeps_the_rule_readable(
    client: TestClient, session: Session, staff: User
):
    """`DELETE` soft-deactivates; a referencing infraction still resolves it."""
    rule_id = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()["id"]

    lot = make_lot(session)
    resident = make_resident(session, lot, seed=20)

    infraction = client.post(
        "/api/v1/infractions",
        json={
            "rule_id": rule_id,
            "lot_id": str(lot.id),
            "responsible_resident_id": str(resident.id),
            "occurred_on": "2026-01-10",
            "description": "Som alto às 23h.",
        },
        headers=_headers(staff),
    )
    assert infraction.status_code == 201, infraction.text

    deleted = client.delete(
        f"/api/v1/infraction-rules/{rule_id}", headers=_headers(staff)
    )
    assert deleted.status_code == 204

    still_there = client.get(
        f"/api/v1/infraction-rules/{rule_id}", headers=_headers(staff)
    )
    assert still_there.status_code == 200
    assert still_there.json()["is_active"] is False

    # ER-4: the lot's history stays whole and navigable.
    resolved = client.get(
        f"/api/v1/infractions/{infraction.json()['id']}", headers=_headers(staff)
    )
    assert resolved.status_code == 200
    assert resolved.json()["rule"]["id"] == rule_id


def test_policy_write_replaces_the_whole_ladder(client: TestClient, staff: User):
    """Three steps then two steps leaves exactly two."""
    rule_id = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()["id"]

    three = client.put(
        f"/api/v1/infraction-rules/{rule_id}/policy",
        json={
            "steps": [
                {"step_order": 1, "action": "AVISO"},
                {
                    "step_order": 2,
                    "action": "NOTIFICACAO",
                    "defense_deadline_days": 30,
                },
                {
                    "step_order": 3,
                    "action": "MULTA",
                    "fine_mode": "FIXED",
                    "fine_fixed_amount": 250.0,
                },
            ]
        },
        headers=_headers(staff),
    )
    assert three.status_code == 200, three.text
    assert [step["step_order"] for step in three.json()["steps"]] == [1, 2, 3]

    two = client.put(
        f"/api/v1/infraction-rules/{rule_id}/policy",
        json={
            "steps": [
                {"step_order": 1, "action": "AVISO"},
                {
                    "step_order": 2,
                    "action": "MULTA",
                    "fine_mode": "MULTIPLE",
                    "fine_fee_multiplier": 2.0,
                },
            ]
        },
        headers=_headers(staff),
    )
    assert two.status_code == 200, two.text
    steps = two.json()["steps"]
    assert len(steps) == 2
    assert [step["action"] for step in steps] == ["AVISO", "MULTA"]


def test_policy_rejects_non_contiguous_step_order(client: TestClient, staff: User):
    """**422**, and the detail names the gap. The spec's `422/400` is 422."""
    rule_id = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()["id"]

    response = client.put(
        f"/api/v1/infraction-rules/{rule_id}/policy",
        json={
            "steps": [
                {"step_order": 1, "action": "AVISO"},
                {"step_order": 3, "action": "AVISO"},
            ]
        },
        headers=_headers(staff),
    )
    assert response.status_code == 422, response.text
    assert "2" in response.json()["detail"]


def test_notificacao_requires_a_deadline(client: TestClient, staff: User):
    rule_id = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()["id"]

    response = client.put(
        f"/api/v1/infraction-rules/{rule_id}/policy",
        json={"steps": [{"step_order": 1, "action": "NOTIFICACAO"}]},
        headers=_headers(staff),
    )
    assert response.status_code == 422
    assert "defense_deadline_days" in response.json()["detail"]


@pytest.mark.parametrize(
    ("step", "fragment"),
    [
        ({"step_order": 1, "action": "MULTA"}, "fine_mode"),
        (
            {"step_order": 1, "action": "MULTA", "fine_mode": "FIXED"},
            "fine_fixed_amount",
        ),
        (
            {"step_order": 1, "action": "MULTA", "fine_mode": "MULTIPLE"},
            "fine_fee_multiplier",
        ),
    ],
)
def test_multa_requires_a_coherent_fine_mode(
    client: TestClient, staff: User, step: dict, fragment: str
):
    """A MULTA with no mode, a FIXED with no amount, a MULTIPLE with no
    multiplier: all three are 422 naming the missing field."""
    rule_id = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()["id"]

    response = client.put(
        f"/api/v1/infraction-rules/{rule_id}/policy",
        json={"steps": [step]},
        headers=_headers(staff),
    )
    assert response.status_code == 422, response.text
    assert fragment in response.json()["detail"]


def test_settings_read_on_an_absent_row_is_200_with_nulls(
    client: TestClient, session: Session, staff: User
):
    """§5: `GET /infraction-settings` never 404s, and `PUT` upserts."""
    absent = client.get("/api/v1/infraction-settings", headers=_headers(staff))
    assert absent.status_code == 200
    assert absent.json() == {
        "condo_fee_amount": None,
        "updated_at": None,
        "updated_by": None,
    }

    written = client.put(
        "/api/v1/infraction-settings",
        json={"condo_fee_amount": 850.5},
        headers=_headers(staff),
    )
    assert written.status_code == 200, written.text
    assert written.json()["condo_fee_amount"] == 850.5
    assert written.json()["updated_by"]["id"] == str(staff.id)

    # The row is materialised lazily, so exactly one exists after one PUT.
    cleared = client.put(
        "/api/v1/infraction-settings",
        json={"condo_fee_amount": None},
        headers=_headers(staff),
    )
    assert cleared.status_code == 200
    assert cleared.json()["condo_fee_amount"] is None
    assert len(session.exec(select(InfractionRule)).all()) == 0


def test_updating_a_rule_into_another_articles_pair_is_rejected(
    client: TestClient, staff: User
):
    """The `(origin, article)` uniqueness is checked on **update** too.

    Without the `exclude_id` half of the check an update that changes nothing
    would collide with the row it is updating; with it, renaming *onto* a
    sibling's pair is still a 409.
    """
    first = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()
    second = client.post(
        "/api/v1/infraction-rules",
        json={**RULE_BODY, "article": "art. 30"},
        headers=_headers(staff),
    ).json()

    # Re-saving the same pair on the same row is not a conflict with itself.
    unchanged = client.put(
        f"/api/v1/infraction-rules/{second['id']}",
        json={"article": "art. 30", "description": "Nova redação."},
        headers=_headers(staff),
    )
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["description"] == "Nova redação."

    collision = client.put(
        f"/api/v1/infraction-rules/{second['id']}",
        json={"article": first["article"]},
        headers=_headers(staff),
    )
    assert collision.status_code == 409
    assert first["article"] in collision.json()["detail"]


def test_policy_rejects_a_duplicated_step_order(client: TestClient, staff: User):
    """Two rungs numbered the same is a different failure from a gap."""
    rule_id = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()["id"]

    response = client.put(
        f"/api/v1/infraction-rules/{rule_id}/policy",
        json={
            "steps": [
                {"step_order": 1, "action": "AVISO"},
                {"step_order": 1, "action": "AVISO"},
            ]
        },
        headers=_headers(staff),
    )
    assert response.status_code == 422, response.text
    assert "unique" in response.json()["detail"]


@pytest.mark.parametrize(
    ("step", "fragment"),
    [
        (
            {"step_order": 1, "action": "AVISO", "defense_deadline_days": 10},
            "defense_deadline_days is only meaningful",
        ),
        (
            {"step_order": 1, "action": "AVISO", "fine_mode": "FIXED"},
            "fine_mode is only meaningful",
        ),
    ],
)
def test_a_field_on_the_wrong_kind_of_step_is_rejected(
    client: TestClient, staff: User, step: dict, fragment: str
):
    """The coherence check runs in both directions.

    A deadline on an AVISO or a fine mode on a NOTIFICACAO would be silently
    ignored at application time, which is worse than a refusal: the síndico
    would believe the ladder says something it does not.
    """
    rule_id = client.post(
        "/api/v1/infraction-rules", json=RULE_BODY, headers=_headers(staff)
    ).json()["id"]

    response = client.put(
        f"/api/v1/infraction-rules/{rule_id}/policy",
        json={"steps": [step]},
        headers=_headers(staff),
    )
    assert response.status_code == 422, response.text
    assert fragment in response.json()["detail"]
