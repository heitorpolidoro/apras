"""The install-wide plan catalogue service (APRAS-40 §6.2).

In the shape of :class:`~app.services.tenant_service.TenantService`: a
module-level class of ``@staticmethod``s taking ``session=``. All validation
lives **here**, never in a Pydantic ``field_validator`` -- the schema
validates shape, the service validates vocabulary, and a schema-level
rejection would surface as FastAPI's 422 where the ERs pin **400**.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.core.exceptions import (
    CoreModuleNotContractableError,
    InvalidModulePriceError,
    InvalidPlanPriceError,
    PlanAlreadyExistsError,
    PlanNotFoundError,
    UnknownModuleError,
)
from app.core.permissions import CORE_MODULES, MODULES, TOGGLEABLE_MODULES
from app.models.plan import Plan

if TYPE_CHECKING:  # pragma: no cover
    from uuid import UUID

    from app.schemas.plan import PlanCreate, PlanUpdate

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _now() -> datetime:
    return datetime.utcnow()  # noqa: DTZ003


class PlanService:
    """Create, read and update the global plan catalogue. There is no delete."""

    @staticmethod
    def _validate_modules(modules: list[str]) -> list[str]:
        """`modules` deduplicated and sorted, or a 400-shaped domain error.

        A plan may only include **toggleable** modules: a non-catalogue string
        is an :class:`UnknownModuleError` and a core one is a
        :class:`CoreModuleNotContractableError`, because a plan cannot
        "include" what is always on.
        """
        requested = set(modules)
        for module in sorted(requested):
            if module not in MODULES:
                raise UnknownModuleError(module)
        core = requested & CORE_MODULES
        if core:
            raise CoreModuleNotContractableError(sorted(core))
        return sorted(requested & TOGGLEABLE_MODULES)

    @staticmethod
    def _validate_prices(
        prices: dict[str, float], included: list[str]
    ) -> dict[str, float]:
        """Key-sorted prices, every key covered by the plan and every value >= 0."""
        uncovered = set(prices) - set(included)
        if uncovered:
            raise InvalidModulePriceError(sorted(uncovered))
        negative = sorted(module for module, price in prices.items() if price < 0)
        if negative:
            raise InvalidPlanPriceError(
                "Module prices cannot be negative: " + ", ".join(negative)
            )
        return {module: float(prices[module]) for module in sorted(prices)}

    @staticmethod
    def _validate_currency(currency: str) -> str:
        if not _CURRENCY_RE.fullmatch(currency):
            raise InvalidPlanPriceError(
                f"Currency must be three uppercase letters: '{currency}'"
            )
        return currency

    @staticmethod
    def _validate_base_price(base_price: float) -> float:
        if base_price < 0:
            raise InvalidPlanPriceError("The base price cannot be negative")
        return float(base_price)

    @staticmethod
    def list_plans(*, session: Session) -> list[Plan]:
        """Every plan, active and inactive, newest name order.

        Inactive plans are listed on purpose: the operator has to be able to
        see and reactivate one, and a tenant may still be subscribed to it.
        """
        return list(session.exec(select(Plan).order_by(Plan.name)).all())

    @staticmethod
    def get_plan(*, session: Session, plan_id: UUID) -> Plan:
        plan = session.get(Plan, plan_id)
        if plan is None:
            raise PlanNotFoundError(plan_id)
        return plan

    @classmethod
    def create_plan(cls, *, session: Session, plan_in: PlanCreate) -> Plan:
        existing = session.exec(select(Plan).where(Plan.name == plan_in.name)).first()
        if existing is not None:
            raise PlanAlreadyExistsError(plan_in.name)

        included = cls._validate_modules(plan_in.included_modules)
        plan = Plan(
            name=plan_in.name,
            description=plan_in.description,
            included_modules=included,
            base_price=cls._validate_base_price(plan_in.base_price),
            module_prices=cls._validate_prices(plan_in.module_prices, included),
            currency=cls._validate_currency(plan_in.currency),
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)
        return plan

    @classmethod
    def update_plan(
        cls, *, session: Session, plan_id: UUID, plan_in: PlanUpdate
    ) -> Plan:
        """Partial update. Every validation of `create_plan` runs again.

        The plan is resolved **first**, so an unknown id is a 404 even when
        the payload is also invalid, exactly as `TenantService` does.

        **Validation is over the whole resulting plan; the write is only over
        what the body sent.** The two JSON columns are always *checked*
        together -- the prices have to be validated against the resulting
        module set, so a `PATCH` that widens the plan and prices the new
        module is legal and one that narrows it without dropping the price is
        not -- but a field absent from `model_dump(exclude_unset=True)` is not
        assigned.

        **This is readability, not behaviour, and the docstring said otherwise
        until round 2 of review measured it.** The `else` branches below fall
        back to the *stored* value unvalidated, so the omitted assignment was
        writing back what was already there, and SQLAlchemy compares those
        attributes by value on flush -- the emitted statement is
        `UPDATE "plan" SET name=?, updated_at=?` with or without the split. It
        is kept because "assign exactly the fields the body sent" is what
        `exclude_unset` is *for*, and a reader should not have to re-derive
        that the two extra assignments are inert; it is not kept because it
        fixes anything observable.
        """
        plan = cls.get_plan(session=session, plan_id=plan_id)
        data = plan_in.model_dump(exclude_unset=True)

        new_name = data.get("name")
        if new_name is not None and new_name != plan.name:
            collision = session.exec(select(Plan).where(Plan.name == new_name)).first()
            if collision is not None:
                raise PlanAlreadyExistsError(new_name)

        included = (
            cls._validate_modules(data["included_modules"])
            if "included_modules" in data
            else list(plan.included_modules)
        )
        prices = (
            data["module_prices"]
            if "module_prices" in data
            else dict(plan.module_prices)
        )
        # Validated unconditionally, assigned only when sent.
        validated_prices = cls._validate_prices(prices, included)
        if "included_modules" in data:
            data["included_modules"] = included
        if "module_prices" in data:
            data["module_prices"] = validated_prices
        if "base_price" in data:
            data["base_price"] = cls._validate_base_price(data["base_price"])
        if "currency" in data:
            data["currency"] = cls._validate_currency(data["currency"])

        for key, value in data.items():
            setattr(plan, key, value)
        plan.updated_at = _now()

        session.add(plan)
        session.commit()
        session.refresh(plan)
        return plan
