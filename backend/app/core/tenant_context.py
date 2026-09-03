"""Session-level tenant isolation (APRAS-42).

APRAS-41 gave 27 tables a NOT NULL ``tenant_id``; this module is what makes
that column *mean* something at request time. It is deliberately central and
default-on: enforcement lives in two SQLAlchemy session events rather than in
22 service files each remembering to pass a ``tenant_id``.

* ``do_orm_execute`` appends one
  :func:`~sqlalchemy.orm.with_loader_criteria` option per scoped model, so
  SELECTs, ``Session.get()``, aggregates, joins and ORM-enabled
  UPDATE/DELETE are all constrained to the acting tenant.
* ``before_flush`` **overwrites** ``tenant_id`` on every pending scoped
  instance, so a create can neither forget the stamp nor honour a forged
  value from a request body.

A session whose ``info`` carries no acting tenant behaves exactly as it did
before this module existed — which is what keeps ``app/seed.py``, Alembic and
the pre-existing test modules working untouched. To stop "no key = no
filter" from becoming a silent leak on an unclassified route, sessions
created by the request dependency ``app.db.get_session`` are additionally
marked *request scoped*, and a request-scoped session that touches a scoped
model before its scope is resolved raises
:class:`~app.core.exceptions.TenantScopeNotResolvedError`.

This module lives in ``app/core/`` and not in ``app/db.py`` on purpose:
``app/db.py`` is excluded from coverage measurement, and this code must be
covered.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import with_loader_criteria
from sqlmodel import Session, SQLModel

# Importing the models package registers every mapper, which is what makes
# the scoped-model discovery below exhaustive no matter who imports this
# module first. No model imports `app.db` or `app.core`, so there is no
# import cycle.
import app.models  # noqa: F401
from app.core.exceptions import CrossTenantWriteError, TenantScopeNotResolvedError
from app.models.tenant import UserTenantLink

#: ``session.info`` key holding the acting tenant id (``UUID``).
ACTING_TENANT_KEY = "acting_tenant_id"
#: ``session.info`` key marking a session created by the request dependency.
REQUEST_SCOPED_KEY = "request_scoped"
#: ``session.info`` key marking the tenant scope as deliberately resolved,
#: whether to a tenant (scoped route) or to nothing (global route).
SCOPE_RESOLVED_KEY = "tenant_scope_resolved"


def _discover_scoped_models() -> tuple[type[SQLModel], ...]:
    """Return every mapped class carrying its own ``tenant_id`` column.

    Derived rather than hand-written so a table added by a future task is
    filtered the day it gets a ``tenant_id``, with nobody having to remember
    a list. ``UserTenantLink`` is excluded: it is the membership table, not
    a tenant-scoped entity.
    """
    return tuple(
        mapper.class_
        for mapper in SQLModel._sa_registry.mappers  # noqa: SLF001
        if "tenant_id" in mapper.local_table.c and mapper.class_ is not UserTenantLink
    )


#: The 28 directly tenant-scoped models: APRAS-41's 27
#: (`_TENANT_SCOPED_TABLES`) plus APRAS-40's `tenant_subscription`, the first
#: added after migration `0028`. Derived by discovery, never listed, so the
#: count moves with the schema and no constant has to be remembered.
TENANT_SCOPED_MODELS: tuple[type[SQLModel], ...] = _discover_scoped_models()

# Memoised `with_loader_criteria` options per tenant id. Rebuilding the 28
# options on every statement measured ~2x the cost of reusing them, and a
# tenant id set is bounded by the number of condominiums in the install.
_OPTIONS_CACHE: dict[UUID, tuple] = {}


def _options_for(tenant_id: UUID) -> tuple:
    """Return (and memoise) the loader criteria for one acting tenant."""
    options = _OPTIONS_CACHE.get(tenant_id)
    if options is None:
        options = tuple(
            with_loader_criteria(
                model, model.tenant_id == tenant_id, include_aliases=True
            )
            for model in TENANT_SCOPED_MODELS
        )
        _OPTIONS_CACHE[tenant_id] = options
    return options


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def set_acting_tenant(session: Session, tenant_id: UUID) -> None:
    """Make ``tenant_id`` the acting tenant of ``session`` and mark it resolved."""
    session.info[ACTING_TENANT_KEY] = tenant_id
    session.info[SCOPE_RESOLVED_KEY] = True


def use_global_scope(session: Session) -> None:
    """Mark ``session`` resolved with **no** acting tenant.

    Used by the routes whose entire surface is unscoped (``user``,
    ``tenant``, ``user_tenant_link``) so the fail-closed guard does not fire
    on them.
    """
    session.info.pop(ACTING_TENANT_KEY, None)
    session.info[SCOPE_RESOLVED_KEY] = True


def acting_tenant_id(session: Session) -> UUID | None:
    """Return the session's acting tenant id, or ``None`` when unscoped."""
    return session.info.get(ACTING_TENANT_KEY)


@contextmanager
def acting_tenant_scope(session: Session, tenant_id: UUID) -> Iterator[None]:
    """Temporarily act in ``tenant_id``, restoring the previous scope after.

    There is exactly one production caller: seeding a *new* tenant's
    role-linked ``Role`` rows from inside a request that acts in a
    different tenant (``TenantService.create_tenant``). Any second caller
    needs a review comment justifying it.
    """
    had_key = ACTING_TENANT_KEY in session.info
    previous = session.info.get(ACTING_TENANT_KEY)
    was_resolved = session.info.get(SCOPE_RESOLVED_KEY, False)
    set_acting_tenant(session, tenant_id)
    try:
        yield
    finally:
        if had_key:
            session.info[ACTING_TENANT_KEY] = previous
        else:
            session.info.pop(ACTING_TENANT_KEY, None)
        session.info[SCOPE_RESOLVED_KEY] = was_resolved


# ---------------------------------------------------------------------------
# Listeners
# ---------------------------------------------------------------------------


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(state) -> None:
    """Constrain every ORM statement to the session's acting tenant.

    Column loads (refreshes) and relationship (lazy) loads are exempt:
    filtering them would break lazy loading on an already-filtered parent,
    and the parent was itself constrained on the way in.
    """
    if state.is_column_load or state.is_relationship_load:
        return

    session_info = state.session.info
    if session_info.get(REQUEST_SCOPED_KEY) and not session_info.get(
        SCOPE_RESOLVED_KEY
    ):
        for description in state.statement.column_descriptions:
            entity = description.get("entity")
            if entity is not None and entity in TENANT_SCOPED_MODELS:
                raise TenantScopeNotResolvedError(entity.__name__)

    tenant_id = session_info.get(ACTING_TENANT_KEY)
    if tenant_id is not None:
        state.statement = state.statement.options(*_options_for(tenant_id))


@event.listens_for(Session, "before_flush")
def _stamp_tenant_on_write(session, _flush_context, _instances) -> None:
    """Stamp pending scoped rows with the acting tenant, refusing foreign ones."""
    tenant_id = session.info.get(ACTING_TENANT_KEY)
    if tenant_id is None:
        return
    for obj in session.new:
        if isinstance(obj, TENANT_SCOPED_MODELS):
            obj.tenant_id = tenant_id
    for obj in session.dirty:
        if isinstance(obj, TENANT_SCOPED_MODELS) and obj.tenant_id != tenant_id:
            raise CrossTenantWriteError(type(obj).__name__)
