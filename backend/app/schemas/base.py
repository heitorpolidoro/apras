"""The base every API schema inherits, and the one reason it exists.

Until APRAS-120 the API returned stored instants **offsetless**. The columns
hold UTC, so `"2026-06-01T13:00:00"` went out and the 33
`new Date(x).toLocaleString()` call sites in the frontend read it as *local*
time: a space reservation booked at 10:00 BRT was stored correctly as 13:00
UTC and **displayed as 13:00**. That is a defect a resident can see, and it is
independent of sqlmodel.

The fix is one shared base, rather than an `Annotated` alias on each of the
106 response-side `datetime` fields: a newly added read schema inherits the
correct behaviour instead of silently opting out of it.
`tests/test_suite_hygiene.py` asserts that every schema class whose resolved
fields include a `datetime` has `ApiModel` in its MRO, so the next one cannot
opt out by accident either.

**Why a wrapped model serialiser and not `@field_serializer("*")`.** The
wildcard field serialiser was the obvious mechanism and it is wrong here,
measured on this tree: a `"*"` field serialiser **replaces** whatever
serialiser an individual field declared, and `app/core/money.py` declares one
on every monetary field -- `PlainSerializer(float, return_type=float,
when_used="json")`, which is what makes `NUMERIC(12, 2)` reach the wire as
`350.0` rather than as pydantic's default `Decimal` rendering `"350.00"`.
Attaching the wildcard silently reverted that for all 43 money assertions in
the suite. Verified in isolation: with a field typed
`Annotated[Decimal, PlainSerializer(float, ...)]`, the plain model dumps
`350.0` and the same model with a pass-through `"*"` serialiser dumps
`'350.00'`.

`mode="wrap"` avoids that by construction. `handler(self)` performs the
*normal* serialisation -- every per-field serialiser included -- and this
module only rewrites the datetime entries of the result. So the money contract
and the UTC contract compose instead of overriding one another, and a field
that declares its own serialiser later keeps it.

Two things this module deliberately does *not* do:

- **It adds no timezone itself.** The conversion lives in `app/core/clock.py`
  as the named direction `to_api`, and this module only calls it. That is what
  keeps "clock is the only module that adds or drops a timezone" a rule with
  no exceptions, which `tests/test_lint_hygiene.py` enforces on source text --
  including on this sentence, which is why it names neither spelling the scan
  looks for.
- **It does not reach inside containers.** The rewrite reads the model's own
  fields, so a datetime nested in a raw `dict` is not converted (nested models
  and lists of models *are* fine, because they serialise through their own
  `ApiModel`). Audited at APRAS-120: no response returns a datetime that way
  today. `clock`'s docstring records the obligation on whoever adds the first
  one. A `@computed_field` returning a `datetime` is the same blind spot for
  the same reason -- it is not in `model_fields` -- and there is exactly one
  computed field in `app/schemas/` today, returning `str`.

`when_used="json"` is what makes this safe for internal callers:
`model_dump()` in python mode still returns real `datetime` objects, so no
service changes. FastAPI serialises a `response_model` with `mode="json"`, so
the offset reaches the wire.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_serializer
from pydantic_core.core_schema import SerializationInfo, SerializerFunctionWrapHandler

from app.core import clock

#: Field names that hold a **calendar date** in a `DateTime` column and must
#: therefore ship *without* an offset: `Task.due_date` and
#: `UserLotLink.start_date`/`.end_date`, plus the read side of the latter two.
#: Their forms are `type="date"`, and a timezone conversion moves a date by a
#: day -- `taskUtils.ts` does `startOfDay(new Date(due_date))`, so
#: `"2026-09-10T00:00:00+00:00"` renders as **Sep 9** in BRT. Applying the UTC
#: read rule to them would ship a one-day regression; excluding them ships
#: none.
#:
#: The match is by exact name, and it is exact *today* rather than
#: approximate: `app/schemas/` contains exactly six `datetime`-typed fields
#: whose name ends in `_date`, and they are precisely these three names in
#: their write and read schemas. The cost, recorded in `clock`'s docstring, is
#: that a genuine *timestamp* field named `end_date` added later would be
#: silently excluded. The real fix is migrating the three columns to `Date`,
#: which is a migration APRAS-120 did not take.
CALENDAR_DATE_FIELDS: frozenset[str] = frozenset({"due_date", "start_date", "end_date"})


class ApiModel(BaseModel):
    """A pydantic model whose `datetime` fields serialise as UTC with offset."""

    @model_serializer(mode="wrap", when_used="json")
    def _serialise_datetimes_as_utc(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Any:
        """Stamp every `datetime` field with the UTC offset it was stored in.

        `handler(self)` is the normal serialisation, so every per-field
        serialiser -- `app/core/money.py`'s `float` conversion above all --
        has already run and is preserved. Only the datetime entries are
        rewritten afterwards.

        `isinstance(value, datetime)` and not `isinstance(value, date)`: a
        `datetime` *is* a `date` subclass, so testing for `date` would catch
        the instants too, while testing for `datetime` correctly leaves real
        `date` fields alone.
        """
        dumped = handler(self)
        if not isinstance(dumped, dict):
            return dumped

        for name, field in type(self).model_fields.items():
            if name in CALENDAR_DATE_FIELDS:
                continue
            # `by_alias` decides which key the handler wrote, so the lookup has
            # to follow it or the rewrite would quietly miss every aliased
            # field instead of failing loudly.
            key = name
            if info.by_alias:
                key = field.serialization_alias or field.alias or name
            if key not in dumped:
                # Dropped by `exclude`, `exclude_none` or `exclude_unset`.
                continue
            value = getattr(self, name, None)
            if isinstance(value, datetime):
                dumped[key] = clock.to_api(value).isoformat()
        return dumped
