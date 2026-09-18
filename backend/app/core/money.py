"""The one definition of money in this codebase (APRAS-64).

Money is ``decimal.Decimal`` backed by ``NUMERIC(12, 2)``, never ``float``.
The defect this fixes is rounding on **multiplication**: ``round()`` over a
binary float rounds the binary representation, so ``round(2.675, 2)`` is
``2.67`` and ``round(1.005, 2)`` is ``1.0``. A fine is a legal document a
resident recomputes by hand; the cent has to be the one they get.

Two annotated types, never a bare ``Decimal``:

``Money``
    Response fields, derived totals and table-model columns. Carries
    ``max_digits=12, decimal_places=2``, which is what makes SQLModel emit
    ``NUMERIC(12, 2)``.

``MoneyIn``
    ``*Create`` / ``*Update`` request bodies only. It has **no scale bound**
    on purpose: ``decimal_places=2`` would make Pydantic reject ``2.675``
    with a 422, and that value is accepted by the API today. The service
    quantizes it half-up instead, so no input accepted today starts failing
    (the screen limits entry to two decimals in front of this, but curl, an
    integration and an older client still reach it).

Both carry a ``PlainSerializer`` to ``float`` for JSON: measured on the
pinned Pydantic (2.13.3), a bare ``Decimal`` field serialises to the
**string** ``"1200.00"``, which would break the frontend in silence.
``return_type=float`` keeps the OpenAPI schema a ``number``. The two
serializers are **distinct module-level singletons** although they behave
identically: identity is what lets ``tests/test_money_typing.py`` tell a
request field from a response field while walking annotations.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

#: The scale every amount is quantized to: two decimal places, in reais.
CENTS = Decimal("0.01")

#: The additive identity, already at scale. A ``sum()`` over money seeds with
#: this so an empty sequence yields ``Decimal("0.00")`` and never ``int`` 0.
ZERO = Decimal("0.00")

#: The rounding policy, in one place. Python's ``Decimal`` default is
#: ``ROUND_HALF_EVEN`` (banker's rounding); the Brazilian commercial
#: convention -- and the one a resident checks a fine against with a pocket
#: calculator -- is half away from zero. Confirmed by the operator (Q1,
#: 2026-09-18). If the association's regimento ever says otherwise, this
#: constant is the only line that changes.
MONEY_ROUNDING = ROUND_HALF_UP

#: Serializer for response/table money. A named singleton, not an inline
#: call, so the exhaustive scan can recognise it by identity.
MONEY_SER = PlainSerializer(float, return_type=float, when_used="json")

#: The request-side twin. A *second, distinct* instance with identical
#: behaviour -- being a separate object is the whole point.
MONEY_IN_SER = PlainSerializer(float, return_type=float, when_used="json")

#: Money on the way out and in the database: ``NUMERIC(12, 2)``, never
#: negative.
Money = Annotated[Decimal, Field(max_digits=12, decimal_places=2, ge=0), MONEY_SER]

#: Money on the way in: no scale bound (see the module docstring).
MoneyIn = Annotated[Decimal, Field(ge=0), MONEY_IN_SER]

#: Derived money that may legitimately be **negative**: a cash balance, a
#: monthly net, a budget variance, a cost impact that is a credit. Same
#: column type and same serializer as :data:`Money`; it just drops ``ge=0``,
#: because a response model validates and a negative balance must not become
#: a 500.
SignedMoney = Annotated[Decimal, Field(max_digits=12, decimal_places=2), MONEY_SER]

#: The request-side twin of :data:`SignedMoney`.
SignedMoneyIn = Annotated[Decimal, MONEY_IN_SER]

#: A ratio, not an amount: ``fine_fee_multiplier`` is ``NUMERIC(8, 4)`` so a
#: bylaw can say 12,5% of the condo fee (``0.125``) instead of being
#: truncated to whole percents. It carries the money serializer, so it still
#: reaches the frontend as a number, but its own precision (operator Q2).
Ratio = Annotated[Decimal, Field(max_digits=8, decimal_places=4, ge=0), MONEY_SER]

#: The request-side twin of ``Ratio``.
RatioIn = Annotated[Decimal, Field(ge=0), MONEY_IN_SER]

#: :data:`Ratio`'s scale, four decimal places.
RATIO_SCALE = Decimal("0.0001")


def quantize_money(value: Decimal) -> Decimal:
    """Round ``value`` to two decimal places, half away from zero.

    The only ``ROUND_HALF_UP`` call in the codebase. Rounding is explicit in
    the service and never delegated to the column scale: SQLite's ``Numeric``
    processor and PostgreSQL's ``NUMERIC(12, 2)`` disagree on a third decimal
    (``Decimal("2.675")`` stores as ``2.67`` on SQLite and ``2.68`` on
    PostgreSQL), so a value must already be quantized before it is assigned.
    """
    return value.quantize(CENTS, rounding=MONEY_ROUNDING)


def quantize_ratio(value: Decimal) -> Decimal:
    """Round a ratio to four decimal places, half away from zero.

    Same policy as :func:`quantize_money`, at ``NUMERIC(8, 4)``'s scale, so a
    multiplier is stored at exactly the precision the column holds instead of
    being rounded by whichever database happens to be underneath.
    """
    return value.quantize(RATIO_SCALE, rounding=MONEY_ROUNDING)
