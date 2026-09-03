"""Schemas for the install-wide plan catalogue (APRAS-40 §5.4).

Every validation of *vocabulary* lives in `PlanService`, never in a Pydantic
``field_validator``: the schema validates **shape**, the service validates
**meaning**, and a schema-level rejection would surface as FastAPI's 422 where
the ERs pin **400** (APRAS-39 §6.3's rule).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlanCreate(BaseModel):
    """A new plan. Every price field is INERT (§1.2)."""

    name: str
    description: str | None = None
    included_modules: list[str] = []
    base_price: float = 0.0
    module_prices: dict[str, float] = {}
    currency: str = "BRL"


class PlanUpdate(BaseModel):
    """A partial plan edit. Every field optional, including `is_active`.

    ``PATCH`` and not ``PUT``: unlike the module and courtesy sets, a plan is
    an ordinary editable record with no "complete desired state" semantics,
    and `is_active` is the deactivation lever (there is no DELETE route).
    """

    name: str | None = None
    description: str | None = None
    included_modules: list[str] | None = None
    base_price: float | None = None
    module_prices: dict[str, float] | None = None
    currency: str | None = None
    is_active: bool | None = None


class PlanRead(BaseModel):
    """One plan as the API returns it, and as `SubscriptionRead` embeds it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    included_modules: list[str]
    base_price: float
    module_prices: dict[str, float]
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
