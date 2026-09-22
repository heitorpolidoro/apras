"""Money is ``Decimal`` everywhere it matters (APRAS-64).

Four claims live here:

1. ``quantize_money`` rounds **half away from zero**, the Brazilian
   commercial convention, not Python's default banker's rounding -- and it is
   the only rounding of money left under ``app/``.
2. The twelve monetary fields are ``Decimal``, never ``float``.
3. **Exhaustively**, no ``Decimal`` field under ``app/models/`` or
   ``app/schemas/`` is left bare: every ``Decimal`` leaf of every field's
   annotation carries ``MONEY_SER`` or ``MONEY_IN_SER`` *by identity* --
   ``MONEY_IN_SER`` on ``*Create``/``*Update`` request schemas, ``MONEY_SER``
   everywhere else.
4. Money reaches the client as a JSON **number**, never a string.

This module deliberately makes **no assertion about precision or scale**.
Precision is verified in exactly one place -- ``test_migrations_postgres.py``,
against the schema the migration really created. Neither the annotation
metadata nor ``Table.columns[...].type`` is a trustworthy oracle here:
SQLModel emits a bare ``NUMERIC`` (no precision) for a *nullable* money
column, and Pydantic nests ``max_digits``/``decimal_places`` at a different
depth depending on nullability.
"""

import ast
import importlib
import inspect
import json
import pathlib
import pkgutil
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, get_args, get_origin

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlmodel import Session

import app.models
import app.schemas
from app.core.money import MONEY_IN_SER, MONEY_SER, quantize_money
from app.core.security import create_access_token
from app.models.asset import Asset
from app.models.enums import AssetCategory, TransactionType
from app.models.finance import FinanceCategory, FinancialTransaction
from app.models.infraction import InfractionSettings
from app.models.project import ConstructionProject
from app.models.purchase import (
    PurchaseQuote,
    PurchaseQuoteItem,
    PurchaseRequest,
)
from app.models.user import User

_APP_DIR = pathlib.Path(__file__).resolve().parent.parent / "app"


# --------------------------------------------------------------------------
# 1. The rounding policy
# --------------------------------------------------------------------------


def test_quantize_money_rounds_half_up_not_half_even():
    # Both are wrong under the old float path: round(2.675, 2) is 2.67 and
    # round(1.005, 2) is 1.0, because the binary literal is just under.
    assert quantize_money(Decimal("2.675")) == Decimal("2.68")
    assert quantize_money(Decimal("1.005")) == Decimal("1.01")


def test_quantize_money_returns_two_decimal_places():
    assert str(quantize_money(Decimal(3))) == "3.00"
    assert str(quantize_money(Decimal("1200.1"))) == "1200.10"


def test_the_two_serializers_are_distinct_objects():
    # Identity is what lets the exhaustive scan tell a request field from a
    # response field, so they must never be the same singleton.
    assert MONEY_SER is not MONEY_IN_SER


#: The modules allowed to call the builtin ``round``, each for a stated
#: reason that is **not** money. The scan below is a blanket ban because a
#: blanket ban needs no judgement at the call site; this set is where the
#: judgement is written down instead, and
#: :func:`test_the_round_exemption_names_no_module_that_handles_money` keeps
#: it honest by refusing any entry whose module mentions ``Decimal``.
#:
#: * ``core/branding.py`` (APRAS-68) rounds an **OKLCH component** -- a
#:   lightness, a chroma, a hue in degrees -- onto the two-decimal grid
#:   ``frontend/src/index.css`` is authored at, so the emitted
#:   ``oklch(L C H)`` string is the precise thing the browser parses and the
#:   contrast measurement runs on exactly the colour that gets painted.
#:   A colour carries no cent and has no commercial rounding convention;
#:   quantizing it as a ``Decimal`` would be the wrong instrument, not a
#:   safer one.
_ROUND_EXEMPT = frozenset({"core/branding.py"})


def test_no_module_under_app_rounds_money_with_the_builtin():
    """``round()`` over a float rounds the *binary* representation.

    Parsed, not grepped, so the word in this module's own prose and in
    ``app/core/money.py``'s docstring is not a finding. The handful of
    modules in :data:`_ROUND_EXEMPT` round something that is not money, and
    say which.
    """
    offenders = []
    for path in sorted(_APP_DIR.rglob("*.py")):
        if str(path.relative_to(_APP_DIR)) in _ROUND_EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(
            f"{path.relative_to(_APP_DIR)}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "round"
        )
    assert offenders == [], f"money must be quantized, not round()ed: {offenders}"


def test_the_round_exemption_names_no_module_that_handles_money():
    """An exemption may not become a hole money can fall through.

    Each exempt module must exist, must actually call ``round`` (a stale
    entry is a silently widened ban), and must contain no ``Decimal`` at
    all -- the moment one does, the exemption has to be re-argued rather
    than inherited.
    """
    for relative in sorted(_ROUND_EXEMPT):
        path = _APP_DIR / relative
        assert path.is_file(), relative

        source = path.read_text(encoding="utf-8")
        assert "Decimal" not in source, relative

        tree = ast.parse(source)
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "round"
            for node in ast.walk(tree)
        ), f"{relative} no longer needs its exemption"


# --------------------------------------------------------------------------
# 2 & 3. The exhaustive annotation walk
# --------------------------------------------------------------------------


def money_kind(field_info) -> str | None:
    """Classify one Pydantic field: ``"out"``, ``"in"``, ``"bare"`` or ``None``.

    ``None`` means the annotation holds no ``Decimal`` at all.

    Both halves of the seed are load-bearing. Measured on the pinned Pydantic
    (2.13.3), ``x: Money`` is *flattened*: the annotation becomes a plain
    ``Decimal`` and the metadata lands on ``FieldInfo.metadata``. But
    ``x: Money | None`` stays ``Optional[Annotated[Decimal, ...]]`` with
    ``FieldInfo.metadata`` empty. A flat check of ``FieldInfo.metadata``
    alone cannot see a nullable money field, and a walk that ignores that
    seed cannot see a non-nullable one.
    """
    kinds: set[str] = set()

    def walk(annotation, metadata: tuple) -> None:
        origin = get_origin(annotation)
        if origin is Annotated:
            args = get_args(annotation)
            walk(args[0], metadata + tuple(args[1:]))
            return
        if origin is not None:
            # Union, list, dict, ... -- every argument but ``None`` counts.
            for arg in get_args(annotation):
                if arg is type(None):
                    continue
                walk(arg, metadata)
            return
        if annotation is Decimal:
            if any(meta is MONEY_SER for meta in metadata):
                kinds.add("out")
            elif any(meta is MONEY_IN_SER for meta in metadata):
                kinds.add("in")
            else:
                kinds.add("bare")

    walk(field_info.annotation, tuple(field_info.metadata))
    if not kinds:
        return None
    for kind in ("bare", "in"):
        if kind in kinds:
            return kind
    return "out"


def test_the_walk_classifies_every_shape():
    """The walk is the scan's only instrument, so it is tested on its own.

    A flat ``FieldInfo.metadata`` check gets the nullable and the nested
    shapes wrong; these nine cases are what proves the recursion earns its
    keep.
    """
    from app.core.money import Money, MoneyIn

    class Shapes(BaseModel):
        plain: Money
        nullable: Money | None = None
        plain_in: MoneyIn
        nullable_in: MoneyIn | None = None
        in_list: list[Money] = []
        in_dict: dict[str, Money] = {}
        bare: Decimal = Decimal(0)
        bare_nullable: Decimal | None = None
        bare_list: list[Decimal] = []
        not_money: str = ""

    kinds = {name: money_kind(field) for name, field in Shapes.model_fields.items()}
    assert kinds == {
        "plain": "out",
        "nullable": "out",
        "plain_in": "in",
        "nullable_in": "in",
        "in_list": "out",
        "in_dict": "out",
        "bare": "bare",
        "bare_nullable": "bare",
        "bare_list": "bare",
        "not_money": None,
    }


def _models_declared_under(package) -> list[type[BaseModel]]:
    """Every ``BaseModel``/``SQLModel`` subclass *defined* in the package."""
    found: dict[str, type[BaseModel]] = {}
    package_path = pathlib.Path(package.__file__).parent
    for info in pkgutil.iter_modules([str(package_path)]):
        module = importlib.import_module(f"{package.__name__}.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseModel)
                and obj.__module__ == module.__name__
                and obj is not BaseModel
            ):
                found[f"{obj.__module__}.{obj.__qualname__}"] = obj
    return [found[key] for key in sorted(found)]


ALL_DECLARED = _models_declared_under(app.models) + _models_declared_under(app.schemas)


def test_the_scan_actually_reaches_the_models_and_the_schemas():
    """A scan over an empty list would pass vacuously."""
    names = {cls.__name__ for cls in ALL_DECLARED}
    assert {"FinancialTransaction", "PurchaseQuote", "BudgetLineCreate"} <= names
    assert len(ALL_DECLARED) > 100


def test_no_decimal_field_anywhere_is_bare():
    bare = [
        f"{cls.__module__}.{cls.__name__}.{name}"
        for cls in ALL_DECLARED
        for name, field in cls.model_fields.items()
        if money_kind(field) == "bare"
    ]
    assert bare == [], f"Decimal fields missing Money/MoneyIn: {bare}"


#: The naming convention for a request body in this repository. `*Write` and
#: `ProjectUpdateSchema` are request bodies too -- `*Create`/`*Update` is the
#: rule, these are the other spellings the tree actually uses. `*In` joined
#: the list with APRAS-73: a payload nested inside both a `*Create` and an
#: `*Update` (`PurchaseQuoteItemIn`, `PurchaseRequestItemIn`) is named for
#: its direction rather than for one of the two verbs, and it is a request
#: body in every sense that matters here -- `AccessLogCheckIn` and
#: `FacialVerificationWebhookIn` were already spelled that way.
_REQUEST_SUFFIXES = ("Create", "Update", "UpdateSchema", "Write", "In")


def _request_side_schemas() -> set[type[BaseModel]]:
    """Request bodies, plus the `*Base` classes they inherit their fields from.

    `ProjectBase` and `AssetBase` carry the money field for both `*Create`
    and `*Read`, so the base is annotated `MoneyIn` (a three-decimal `POST`
    stays accepted, Decision 4) and the `*Read` subclass **redeclares** it as
    `Money`. A class is therefore request-side when it is a request body or
    when a request body inherits from it -- and a `*Read` never is, however it
    inherits.
    """
    bodies = {
        cls
        for cls in ALL_DECLARED
        if cls.__module__.startswith("app.schemas.")
        and cls.__name__.endswith(_REQUEST_SUFFIXES)
    }
    request_side = set(bodies)
    for body in bodies:
        request_side |= {
            base
            for base in body.__mro__
            if base in set(ALL_DECLARED) and not base.__name__.endswith("Read")
        }
    return request_side


def test_request_schemas_use_money_in_and_everything_else_money():
    """`MoneyIn` on the way in, `Money` on the way out -- and on every column.

    A table model is never request-side however it is named:
    `models.project.ProjectUpdate` is a table, not a body.
    """
    request_side = _request_side_schemas()
    wrong = []
    for cls in ALL_DECLARED:
        expected = "in" if cls in request_side else "out"
        for name, field in cls.model_fields.items():
            kind = money_kind(field)
            if kind is not None and kind != expected:
                wrong.append(
                    f"{cls.__module__}.{cls.__name__}.{name}: {kind} != {expected}"
                )
    assert wrong == [], f"wrong money annotation: {wrong}"


def test_the_request_side_set_is_what_it_claims_to_be():
    """The classification itself, pinned -- it is the previous test's oracle."""
    names = {cls.__name__ for cls in _request_side_schemas()}
    assert {
        "PurchaseQuoteCreate",
        "PurchaseQuoteUpdate",
        "PurchaseQuoteItemIn",
        "ProjectBase",
        "ProjectCreate",
        "ProjectUpdateSchema",
        "AssetBase",
        "InfractionPolicyStepWrite",
        "InfractionSettingsWrite",
    } <= names
    # A read schema and a table model are never request-side, whatever their
    # name or their base class.
    assert names.isdisjoint(
        {"ProjectRead", "AssetRead", "InfractionPolicyStepRead", "PurchaseQuote"}
    )


#: The twelve monetary fields of the six models, as ``(model, attribute)``.
#: ``fine_amount`` lives on ``InfractionStage`` -- the column is
#: ``infraction_stage.fine_amount``.
TWELVE_FIELDS = [
    ("app.models.finance", "BudgetLine", "planned_amount"),
    ("app.models.finance", "FinancialTransaction", "amount"),
    ("app.models.infraction", "InfractionPolicyStep", "fine_fixed_amount"),
    ("app.models.infraction", "InfractionPolicyStep", "fine_fee_multiplier"),
    ("app.models.infraction", "InfractionStage", "fine_amount"),
    ("app.models.infraction", "InfractionSettings", "condo_fee_amount"),
    ("app.models.project", "ConstructionProject", "total_budget"),
    ("app.models.project", "ConstructionProject", "executed_budget"),
    ("app.models.project", "ProjectUpdate", "cost_impact"),
    # APRAS-73 D13: the price left `purchase_quote` for its lines.
    ("app.models.purchase", "PurchaseQuoteItem", "unit_price"),
    ("app.models.plan", "Plan", "base_price"),
    ("app.models.asset", "Asset", "acquisition_value"),
]


@pytest.mark.parametrize(("module_name", "class_name", "field_name"), TWELVE_FIELDS)
def test_the_twelve_fields_are_decimal_and_not_float(
    module_name: str, class_name: str, field_name: str
):
    model = getattr(importlib.import_module(module_name), class_name)
    field = model.model_fields[field_name]
    assert money_kind(field) == "out", f"{class_name}.{field_name} is not Money"
    assert float not in get_args(field.annotation)
    assert field.annotation is not float


# --------------------------------------------------------------------------
# 4. JSON numbers, not strings
# --------------------------------------------------------------------------


def _numbers_only(payload: object, path: str = "$") -> list[str]:
    """Every string that parses as a decimal number is a serialisation bug."""
    offenders: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            offenders += _numbers_only(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            offenders += _numbers_only(value, f"{path}[{index}]")
    elif isinstance(payload, str):
        try:
            Decimal(payload)
        except InvalidOperation:
            return offenders
        offenders.append(f"{path}={payload!r}")
    return offenders


@pytest.fixture(name="admin_headers")
def admin_headers_fixture(admin_user: User) -> dict:
    return {
        "Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"
    }


def test_money_is_a_json_number_on_every_affected_domain(
    client: TestClient, session: Session, admin_user: User, admin_headers: dict
):
    category = FinanceCategory(name="Taxa", type=TransactionType.INCOME)
    session.add(category)
    session.commit()
    session.refresh(category)
    session.add(
        FinancialTransaction(
            type=TransactionType.INCOME,
            category_id=category.id,
            description="Taxa de março",
            amount=Decimal("1200.00"),
            transaction_date=date(2026, 3, 1),
            created_by_id=admin_user.id,
        )
    )
    session.add(
        ConstructionProject(
            title="Fachada",
            total_budget=Decimal("50000.00"),
            executed_budget=Decimal("1234.56"),
        )
    )
    session.add(
        Asset(
            name="Bomba",
            category=AssetCategory.MANUTENCAO,
            location="Casa de máquinas",
            acquisition_value=Decimal("999.99"),
        )
    )
    session.add(InfractionSettings(condo_fee_amount=Decimal("1200.01")))
    request = PurchaseRequest(
        title="Bombas",
        description="Duas bombas",
        requested_by_id=admin_user.id,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    # APRAS-73 D13: the quote itself carries no price any more, so the
    # money-reaches-JSON-as-a-number claim keeps its live subject by moving
    # onto one `PurchaseQuoteItem` at exactly the same value.
    quote = PurchaseQuote(
        purchase_request_id=request.id,
        supplier_name="Fornecedor A",
        created_by_id=admin_user.id,
    )
    quote.items = [
        PurchaseQuoteItem(
            request_item_id=None,
            description="Bomba submersa",
            quantity=1,
            unit_price=Decimal("2.68"),
            position=0,
        )
    ]
    session.add(quote)
    session.commit()

    endpoints = [
        "/api/v1/finance/transactions",
        "/api/v1/projects",
        "/api/v1/assets",
        "/api/v1/infraction-settings",
        f"/api/v1/purchase-requests/{request.id}",
    ]
    for url in endpoints:
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200, (url, response.text)
        body = json.loads(response.text)
        assert _numbers_only(body) == [], (url, _numbers_only(body))

    listed = json.loads(client.get(endpoints[0], headers=admin_headers).text)
    rows = listed["items"] if isinstance(listed, dict) else listed
    amounts = [row["amount"] for row in rows]
    assert amounts != []
    assert all(isinstance(value, (int, float)) for value in amounts)


def test_plan_money_is_a_json_number(session: Session, tenant_client: TestClient):
    from tests.subscription_helpers import auth, make_superuser

    superuser = make_superuser(session)
    created = tenant_client.post(
        "/api/v1/plans/",
        json={
            "name": f"Plano {uuid.uuid4().hex[:6]}",
            "included_modules": ["finance"],
            "module_prices": {"finance": 49.0},
            "base_price": 100.0,
        },
        headers=auth(superuser),
    )
    assert created.status_code == 201, created.text
    body = json.loads(created.text)
    assert isinstance(body["base_price"], (int, float))
    assert _numbers_only(body) == []
