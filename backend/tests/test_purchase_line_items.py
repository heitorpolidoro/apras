"""The request enumerates the lines and each quote prices them (APRAS-73).

Everything the grid rests on lives here: the exclusive-or between a linked
line and a supplier's own extra line (D3), coverage counted over linked items
only (D5), the total derived from the lines and nothing else (D8), the
wholesale rewrite of both lists (D7), and the ranking restricted to complete
quotes (D10) -- which deliberately **changes** the APRAS-63 contract, where
``is_lowest_price`` was a pure minimum over totals.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import create_access_token
from app.models.purchase import PurchaseQuoteItem, PurchaseRequestItem
from app.models.user import User
from app.schemas.purchase import MAX_QUOTE_ITEMS, MAX_REQUEST_ITEMS
from tests.conftest import make_user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def admin(session: Session) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email="admin_items@test.com",
        full_name="Admin Itens",
        hashed_password="hash",
        profile="ADMINISTRATOR",
        cpf="11111111111",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


THREE_LINES = [
    {"description": "Câmeras IP 4MP", "quantity": 4},
    {"description": "Instalação", "quantity": 1},
    {"description": "Cabo UTP CAT6", "quantity": 2},
]


def _create_request(client: TestClient, user: User, **overrides) -> dict:
    payload: dict = {"title": "Instalação de CFTV"}
    payload.update(overrides)
    res = client.post("/api/v1/purchase-requests", json=payload, headers=_headers(user))
    assert res.status_code == 201, res.text
    return res.json()


def _linked(request_item: dict, unit_price: float, model: str | None = None) -> dict:
    line: dict = {
        "request_item_id": request_item["id"],
        "unit_price": unit_price,
    }
    if model is not None:
        line["model"] = model
    return line


def _extra(description: str, quantity: int, unit_price: float) -> dict:
    return {
        "description": description,
        "quantity": quantity,
        "unit_price": unit_price,
    }


def _add_quote(
    client: TestClient, user: User, request_id: str, supplier: str, items: list[dict]
):
    return client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json={"supplier_name": supplier, "items": items},
        headers=_headers(user),
    )


def _detail(client: TestClient, user: User, request_id: str) -> dict:
    res = client.get(f"/api/v1/purchase-requests/{request_id}", headers=_headers(user))
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------------------
# The request's enumeration (D1, D6, D7)
# ---------------------------------------------------------------------------


def test_a_request_returns_its_lines_in_submitted_order_with_server_positions(
    client: TestClient, admin: User
) -> None:
    created = _create_request(client, admin, items=THREE_LINES)

    assert [item["description"] for item in created["items"]] == [
        "Câmeras IP 4MP",
        "Instalação",
        "Cabo UTP CAT6",
    ]
    assert [item["position"] for item in created["items"]] == [0, 1, 2]
    assert [item["quantity"] for item in created["items"]] == [4, 1, 2]


def test_a_request_with_no_lines_is_valid_and_reads_back_empty(
    client: TestClient, admin: User
) -> None:
    """D6: zero lines is the pre-APRAS-73 world, and what the migration makes."""
    created = _create_request(client, admin)

    assert created["items"] == []
    assert _detail(client, admin, created["id"])["items"] == []


def test_a_line_description_is_stripped_and_a_blank_one_is_422(
    client: TestClient, admin: User
) -> None:
    created = _create_request(
        client, admin, items=[{"description": "  Câmeras  ", "quantity": 1}]
    )
    assert created["items"][0]["description"] == "Câmeras"

    for bad in ("", "   "):
        res = client.post(
            "/api/v1/purchase-requests",
            json={"title": "X", "items": [{"description": bad, "quantity": 1}]},
            headers=_headers(admin),
        )
        assert res.status_code == 422, bad


def test_a_zero_quantity_line_is_422_and_fifty_one_lines_are_422(
    client: TestClient, admin: User
) -> None:
    zero = client.post(
        "/api/v1/purchase-requests",
        json={"title": "X", "items": [{"description": "Item", "quantity": 0}]},
        headers=_headers(admin),
    )
    assert zero.status_code == 422

    too_many = client.post(
        "/api/v1/purchase-requests",
        json={
            "title": "X",
            "items": [
                {"description": f"Item {i}", "quantity": 1}
                for i in range(MAX_REQUEST_ITEMS + 1)
            ],
        },
        headers=_headers(admin),
    )
    assert too_many.status_code == 422

    at_the_cap = client.post(
        "/api/v1/purchase-requests",
        json={
            "title": "X",
            "items": [
                {"description": f"Item {i}", "quantity": 1}
                for i in range(MAX_REQUEST_ITEMS)
            ],
        },
        headers=_headers(admin),
    )
    assert at_the_cap.status_code == 201
    assert len(at_the_cap.json()["items"]) == MAX_REQUEST_ITEMS


def test_updating_the_lines_keeps_the_resubmitted_ids_and_their_quote_cells(
    client: TestClient, admin: User, session: Session
) -> None:
    """D7: a rewrite by identity, not a delete-and-recreate.

    The line the payload resubmits by ``id`` keeps every cell attached to it;
    the line it omits is deleted, and its cells go with it.
    """
    created = _create_request(client, admin, items=THREE_LINES)
    kept, edited, dropped = created["items"]
    quote = _add_quote(
        client,
        admin,
        created["id"],
        "Fornecedor",
        [
            _linked(kept, 1450.0),
            _linked(edited, 1200.0),
            _linked(dropped, 240.0),
        ],
    ).json()
    assert len(quote["items"]) == 3

    res = client.put(
        f"/api/v1/purchase-requests/{created['id']}",
        json={
            "items": [
                {"id": kept["id"], "description": kept["description"], "quantity": 4},
                {
                    "id": edited["id"],
                    "description": "Instalação e testes",
                    "quantity": 2,
                },
                {"description": "Fonte 12 V", "quantity": 1},
            ]
        },
        headers=_headers(admin),
    )
    assert res.status_code == 200, res.text
    items = res.json()["items"]

    assert [item["id"] for item in items[:2]] == [kept["id"], edited["id"]]
    assert items[1]["description"] == "Instalação e testes"
    assert items[1]["quantity"] == 2
    assert items[2]["description"] == "Fonte 12 V"
    assert [item["position"] for item in items] == [0, 1, 2]

    # The dropped line took its cell with it; the two kept ones kept theirs.
    surviving = _detail(client, admin, created["id"])["quotes"][0]["items"]
    assert {item["request_item_id"] for item in surviving} == {
        kept["id"],
        edited["id"],
    }
    assert (
        session.exec(
            select(PurchaseRequestItem).where(
                PurchaseRequestItem.id == uuid.UUID(dropped["id"])
            )
        ).first()
        is None
    )
    assert (
        session.exec(
            select(PurchaseQuoteItem).where(
                PurchaseQuoteItem.request_item_id == uuid.UUID(dropped["id"])
            )
        ).first()
        is None
    )


def test_rewriting_the_lines_of_a_decided_request_is_refused(
    client: TestClient, admin: User
) -> None:
    """The freeze guard, now reached from `update_request` when `items` is
    present -- and **only** then, so a free-text edit keeps its behaviour."""
    created = _create_request(client, admin, items=THREE_LINES)
    quote = _add_quote(
        client,
        admin,
        created["id"],
        "Fornecedor",
        [_linked(item, 10.0) for item in created["items"]],
    ).json()
    client.post(
        f"/api/v1/purchase-requests/{created['id']}/decision",
        json={"quote_id": quote["id"], "justification": "Único fornecedor da praça."},
        headers=_headers(admin),
    )

    frozen = client.put(
        f"/api/v1/purchase-requests/{created['id']}",
        json={"items": [{"description": "Outra coisa", "quantity": 1}]},
        headers=_headers(admin),
    )
    assert frozen.status_code == 409

    # An empty list is a wholesale rewrite to nothing, not an absent key: the
    # guard must refuse it too, which is why the form omits `items` entirely
    # instead of sending `[]` on a free-text edit (D7).
    emptied = client.put(
        f"/api/v1/purchase-requests/{created['id']}",
        json={"title": "Troca das bombas d'agua", "items": []},
        headers=_headers(admin),
    )
    assert emptied.status_code == 409

    free_text = client.put(
        f"/api/v1/purchase-requests/{created['id']}",
        json={"general_notes": "Ata assinada."},
        headers=_headers(admin),
    )
    assert free_text.status_code == 200
    assert len(free_text.json()["items"]) == 3


# ---------------------------------------------------------------------------
# The quote's priced lines (D2, D3, D5, D8)
# ---------------------------------------------------------------------------


def test_a_quote_pricing_two_of_three_lines_echoes_them_and_counts_coverage(
    client: TestClient, admin: User
) -> None:
    """D5: the unpriced line has **no** row -- no zero anywhere in the stack."""
    created = _create_request(client, admin, items=THREE_LINES)
    camera, install, _cable = created["items"]

    body = _add_quote(
        client,
        admin,
        created["id"],
        "SegurMax",
        [
            _linked(camera, 1450.0, model="Intelbras VIP 5432"),
            _linked(install, 1200.0),
        ],
    ).json()

    assert len(body["items"]) == 2
    assert body["items"][0]["description"] == "Câmeras IP 4MP"
    assert body["items"][0]["quantity"] == 4
    assert body["items"][0]["model"] == "Intelbras VIP 5432"
    assert body["items"][0]["line_total"] == 5800.0
    assert body["items"][1]["description"] == "Instalação"
    assert body["items"][1]["quantity"] == 1
    assert body["items"][1]["model"] is None
    assert body["items"][1]["line_total"] == 1200.0
    assert body["total_price"] == 7000.0
    assert body["quoted_item_count"] == 2
    assert body["is_complete"] is False
    assert all(item["line_total"] != 0 for item in body["items"])


def test_a_quote_pricing_every_line_plus_an_extra_is_complete(
    client: TestClient, admin: User
) -> None:
    created = _create_request(client, admin, items=THREE_LINES)

    body = _add_quote(
        client,
        admin,
        created["id"],
        "CFTV Express",
        [
            *[_linked(item, 100.0) for item in created["items"]],
            _extra("Nobreak 1,2 kVA", 1, 890.0),
        ],
    ).json()

    assert len(body["items"]) == 4
    extra = body["items"][3]
    assert extra["request_item_id"] is None
    assert extra["description"] == "Nobreak 1,2 kVA"
    assert extra["quantity"] == 1
    assert extra["line_total"] == 890.0
    assert body["quoted_item_count"] == 3
    assert body["is_complete"] is True
    assert body["total_price"] == 100.0 * 4 + 100.0 + 100.0 * 2 + 890.0


def test_an_extra_line_never_counts_toward_coverage(
    client: TestClient, admin: User
) -> None:
    """The discriminating case: 2 of 3 **plus one extra** is still 2 of 3."""
    created = _create_request(client, admin, items=THREE_LINES)
    camera, _install, cable = created["items"]

    body = _add_quote(
        client,
        admin,
        created["id"],
        "Parcial",
        [
            _linked(camera, 1000.0),
            _linked(cable, 200.0),
            _extra("Suporte de parede", 4, 55.0),
        ],
    ).json()

    assert len(body["items"]) == 3
    assert body["quoted_item_count"] == 2
    assert body["is_complete"] is False


@pytest.mark.parametrize("model", [None, "", "   "])
def test_a_blank_model_reads_back_as_null(
    client: TestClient, admin: User, model: str | None
) -> None:
    created = _create_request(client, admin, items=[THREE_LINES[0]])
    line = {"request_item_id": created["items"][0]["id"], "unit_price": 10.0}
    if model is not None:
        line["model"] = model

    body = _add_quote(client, admin, created["id"], "F", [line]).json()

    assert body["items"][0]["model"] is None


def test_the_total_is_the_sum_of_half_up_line_totals(
    client: TestClient, admin: User
) -> None:
    """D8, and the order the two roundings happen in.

    ``MoneyIn`` has no scale bound, so ``2.675`` is accepted (APRAS-64
    Decision 4) and quantized **half-up on the way in** -- it has to be, the
    column is ``NUMERIC(12, 2)``. The line total is then the product of the
    *stored* price: ``2.68 * 3 == 8.04``, not ``quantize(2.675 * 3) == 8.03``.
    Asserting the storage order rather than the arithmetic order is the
    point: what the supplier sees is what the database holds.
    """
    created = _create_request(client, admin, items=[])

    body = _add_quote(
        client,
        admin,
        created["id"],
        "Centavos",
        [_extra("Parafuso", 3, 2.675), _extra("Bucha", 1, 1.005)],
    ).json()

    assert body["items"][0]["unit_price"] == 2.68
    assert body["items"][0]["line_total"] == 8.04
    assert body["items"][1]["unit_price"] == 1.01
    assert body["items"][1]["line_total"] == 1.01
    assert body["total_price"] == 9.05


# ---------------------------------------------------------------------------
# The refusals (D3, D6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        pytest.param({"unit_price": 1.0}, id="extra-missing-both"),
        pytest.param(
            {"unit_price": 1.0, "description": "Só descrição"}, id="extra-no-quantity"
        ),
        pytest.param({"unit_price": 1.0, "quantity": 2}, id="extra-no-description"),
        pytest.param(
            {"unit_price": 1.0, "description": "   ", "quantity": 2},
            id="extra-blank-description",
        ),
        pytest.param(
            {"unit_price": 1.0, "description": "Item", "quantity": 0},
            id="quantity-zero",
        ),
        pytest.param(
            {"unit_price": -1.0, "description": "Item", "quantity": 1},
            id="negative-price",
        ),
    ],
)
def test_a_malformed_quote_line_is_422(
    client: TestClient, admin: User, line: dict
) -> None:
    created = _create_request(client, admin)

    assert _add_quote(client, admin, created["id"], "F", [line]).status_code == 422


@pytest.mark.parametrize("field", ["description", "quantity"])
def test_a_linked_line_that_also_sends_its_own_text_is_422(
    client: TestClient, admin: User, field: str
) -> None:
    """D3: the exclusive-or, so no fact is stored twice."""
    created = _create_request(client, admin, items=[THREE_LINES[0]])
    line = {
        "request_item_id": created["items"][0]["id"],
        "unit_price": 10.0,
        field: "Câmeras" if field == "description" else 9,
    }

    assert _add_quote(client, admin, created["id"], "F", [line]).status_code == 422


def test_an_empty_or_missing_items_list_is_422_on_create_and_on_update(
    client: TestClient, admin: User
) -> None:
    """D6: an empty list is a refusal, never a way to empty a quote."""
    created = _create_request(client, admin)

    assert _add_quote(client, admin, created["id"], "F", []).status_code == 422
    missing = client.post(
        f"/api/v1/purchase-requests/{created['id']}/quotes",
        json={"supplier_name": "F"},
        headers=_headers(admin),
    )
    assert missing.status_code == 422

    quote = _add_quote(
        client, admin, created["id"], "F", [_extra("Item", 1, 10.0)]
    ).json()
    emptied = client.put(
        f"/api/v1/purchase-requests/{created['id']}/quotes/{quote['id']}",
        json={"items": []},
        headers=_headers(admin),
    )
    assert emptied.status_code == 422


def test_fifty_one_quote_lines_are_422(client: TestClient, admin: User) -> None:
    created = _create_request(client, admin)
    lines = [_extra(f"Item {i}", 1, 1.0) for i in range(MAX_QUOTE_ITEMS + 1)]

    assert _add_quote(client, admin, created["id"], "F", lines).status_code == 422
    assert _add_quote(client, admin, created["id"], "F", lines[:-1]).status_code == 201


def test_two_lines_pricing_the_same_request_line_are_422(
    client: TestClient, admin: User
) -> None:
    created = _create_request(client, admin, items=[THREE_LINES[0]])
    camera = created["items"][0]

    res = _add_quote(
        client,
        admin,
        created["id"],
        "F",
        [_linked(camera, 10.0), _linked(camera, 20.0)],
    )

    assert res.status_code == 422


def test_an_unknown_or_cross_request_line_is_400(
    client: TestClient, admin: User
) -> None:
    """D3: a cross-entity fact the schema cannot see is a 400, not a 422."""
    created = _create_request(client, admin, items=[THREE_LINES[0]])
    other = _create_request(client, admin, title="Outro", items=[THREE_LINES[1]])

    unknown = _add_quote(
        client,
        admin,
        created["id"],
        "F",
        [{"request_item_id": str(uuid.uuid4()), "unit_price": 10.0}],
    )
    assert unknown.status_code == 400
    assert "não pertence a este pedido" in unknown.json()["detail"]

    cross = _add_quote(
        client, admin, created["id"], "F", [_linked(other["items"][0], 10.0)]
    )
    assert cross.status_code == 400


# ---------------------------------------------------------------------------
# Replacement and cascades
# ---------------------------------------------------------------------------


def test_updating_a_quote_replaces_the_whole_list_and_renumbers_positions(
    client: TestClient, admin: User
) -> None:
    created = _create_request(client, admin, items=THREE_LINES)
    camera, install, cable = created["items"]
    quote = _add_quote(
        client,
        admin,
        created["id"],
        "F",
        [_linked(camera, 100.0), _linked(install, 200.0)],
    ).json()
    kept_id = quote["items"][0]["id"]

    res = client.put(
        f"/api/v1/purchase-requests/{created['id']}/quotes/{quote['id']}",
        json={
            "items": [
                _linked(cable, 50.0),
                _linked(camera, 120.0, model="Novo modelo"),
            ]
        },
        headers=_headers(admin),
    )
    assert res.status_code == 200, res.text
    items = res.json()["items"]

    assert [item["position"] for item in items] == [0, 1]
    assert items[0]["request_item_id"] == cable["id"]
    # The linked row survives its own re-pricing, so its id is stable.
    assert items[1]["id"] == kept_id
    assert items[1]["model"] == "Novo modelo"
    assert res.json()["total_price"] == 50.0 * 2 + 120.0 * 4


def test_deleting_a_quote_deletes_its_lines_and_deleting_a_request_both(
    client: TestClient, admin: User, session: Session
) -> None:
    created = _create_request(client, admin, items=THREE_LINES)
    first = _add_quote(
        client,
        admin,
        created["id"],
        "Um",
        [_linked(item, 10.0) for item in created["items"]],
    ).json()
    _add_quote(client, admin, created["id"], "Dois", [_extra("Avulso", 1, 5.0)])

    assert (
        client.delete(
            f"/api/v1/purchase-requests/{created['id']}/quotes/{first['id']}",
            headers=_headers(admin),
        ).status_code
        == 204
    )
    session.expire_all()
    assert (
        session.exec(
            select(PurchaseQuoteItem).where(
                PurchaseQuoteItem.quote_id == uuid.UUID(first["id"])
            )
        ).all()
        == []
    )

    assert (
        client.delete(
            f"/api/v1/purchase-requests/{created['id']}", headers=_headers(admin)
        ).status_code
        == 204
    )
    session.expire_all()
    assert session.exec(select(PurchaseQuoteItem)).all() == []
    assert session.exec(select(PurchaseRequestItem)).all() == []


# ---------------------------------------------------------------------------
# Ranking over complete quotes only (D10) and the money projections
# ---------------------------------------------------------------------------


def test_the_badge_lands_on_the_cheapest_complete_quote_not_the_cheapest_one(
    client: TestClient, admin: User
) -> None:
    """The deliberate change to the APRAS-63 contract.

    The incomplete quote is cheaper *because it delivers less*, so it is
    neither badged nor the baseline the gap is measured from.
    """
    created = _create_request(client, admin, items=THREE_LINES)
    camera, install, cable = created["items"]
    _add_quote(
        client, admin, created["id"], "Incompleto barato", [_linked(camera, 100.0)]
    )
    _add_quote(
        client,
        admin,
        created["id"],
        "Completo médio",
        [_linked(camera, 100.0), _linked(install, 100.0), _linked(cable, 100.0)],
    )
    _add_quote(
        client,
        admin,
        created["id"],
        "Completo caro",
        [_linked(camera, 200.0), _linked(install, 200.0), _linked(cable, 200.0)],
    )

    detail = _detail(client, admin, created["id"])
    by_name = {quote["supplier_name"]: quote for quote in detail["quotes"]}

    assert by_name["Incompleto barato"]["total_price"] == 400.0
    assert by_name["Completo médio"]["total_price"] == 700.0
    assert by_name["Incompleto barato"]["is_lowest_price"] is False
    assert by_name["Completo médio"]["is_lowest_price"] is True
    assert by_name["Completo caro"]["is_lowest_price"] is False
    assert detail["lowest_quote_total"] == 700.0


def test_with_no_complete_quote_nothing_is_badged_and_the_baseline_is_none(
    client: TestClient, admin: User
) -> None:
    created = _create_request(client, admin, items=THREE_LINES)
    camera, install, _cable = created["items"]
    _add_quote(client, admin, created["id"], "A", [_linked(camera, 100.0)])
    _add_quote(client, admin, created["id"], "B", [_linked(install, 50.0)])

    detail = _detail(client, admin, created["id"])

    assert detail["lowest_quote_total"] is None
    assert all(quote["is_lowest_price"] is False for quote in detail["quotes"])
    assert all(quote["is_complete"] is False for quote in detail["quotes"])


def test_on_a_request_with_no_lines_ranking_is_the_plain_minimum(
    client: TestClient, admin: User
) -> None:
    """The migrated world: every quote is trivially complete (D5), so the
    ranking is bit-for-bit what APRAS-63 produced."""
    created = _create_request(client, admin)
    _add_quote(client, admin, created["id"], "Caro", [_extra("Serviço", 1, 900.0)])
    _add_quote(client, admin, created["id"], "Barato", [_extra("Serviço", 1, 100.0)])

    detail = _detail(client, admin, created["id"])

    assert [q["supplier_name"] for q in detail["quotes"]] == ["Barato", "Caro"]
    assert [q["is_complete"] for q in detail["quotes"]] == [True, True]
    assert [q["is_lowest_price"] for q in detail["quotes"]] == [True, False]
    assert detail["lowest_quote_total"] == 100.0


def test_the_money_projections_are_right_over_quotes_of_different_coverage(
    client: TestClient, admin: User
) -> None:
    """`lowest_quote_total`, `selected_quote_total`, `total_selected_value`
    and `PurchaseDecisionRead.quote_total_price`, asserted together over a
    request whose two quotes cover different amounts of it."""
    created = _create_request(client, admin, items=THREE_LINES)
    camera, install, cable = created["items"]
    partial = _add_quote(
        client, admin, created["id"], "Parcial", [_linked(camera, 100.0)]
    ).json()
    complete = _add_quote(
        client,
        admin,
        created["id"],
        "Completo",
        [_linked(camera, 150.0), _linked(install, 150.0), _linked(cable, 150.0)],
    ).json()

    assert partial["total_price"] == 400.0
    assert complete["total_price"] == 1050.0

    decision = client.post(
        f"/api/v1/purchase-requests/{created['id']}/decision",
        json={
            "quote_id": partial["id"],
            "justification": "O restante será comprado em outro pedido.",
        },
        headers=_headers(admin),
    )
    assert decision.status_code == 201, decision.text
    # The decision reports the quote that was chosen, incomplete or not.
    assert decision.json()["quote_total_price"] == 400.0

    detail = _detail(client, admin, created["id"])
    assert detail["lowest_quote_total"] == 1050.0
    assert detail["selected_quote_total"] == 400.0

    summary = client.get(
        "/api/v1/purchase-requests/summary", headers=_headers(admin)
    ).json()
    assert summary["total_selected_value"] == 400.0
    assert complete["id"]
