"""One traversal of the live route table, for every test that audits it.

Why this module exists
----------------------
Until fastapi 0.141, ``include_router`` *flattened* a sub-router's routes into
the parent's ``routes`` list, so ``[r for r in app.routes if isinstance(r,
APIRoute)]`` saw every route in the application. Sixteen test modules relied on
that, each with its own copy of the walk.

fastapi 0.141 stopped flattening. ``include_router`` now appends a single
``fastapi.routing._IncludedRouter`` node that *holds* the sub-router, and
resolves the effective path, tags and dependencies lazily at match time. The
difference, measured on this application:

======================  ===================  ==========================================
fastapi                 ``len(app.routes)``  types
======================  ===================  ==========================================
0.136.3                 248                  ``APIRoute`` 242, ``Route`` 4, ``Mount`` 2
0.141.1                 8                    ``_IncludedRouter`` 1, ``APIRoute`` 1,
                                             ``Route`` 4, ``Mount`` 2
======================  ===================  ==========================================

The application is **not** broken by that: routing works and ``app.openapi()``
still reports all 170 paths. Only the introspection surface moved. But the
permission and tenant-scope audits in this suite *are* introspection, so a
naive walk silently shrinks them from 242 routes to 1 -- an audit that passes
while auditing almost nothing. These helpers are what keep those audits whole.

On the API this uses
--------------------
``fastapi.routing.iter_route_contexts`` is the traversal fastapi's own
``fastapi.openapi.utils.get_openapi`` uses to enumerate routes, which is why
``app.openapi()`` still sees everything. It is not underscore-private and
neither is the ``RouteContext`` it yields.

It is, however, **not** formally exported: ``fastapi.routing`` declares no
``__all__`` and ``fastapi/__init__.py`` re-exports neither name. So it is
public by naming convention and by fastapi's own use of it from a documented
public function, rather than by an explicit API guarantee. That is the most
public route-enumeration API 0.141 offers -- the alternatives on the
``_IncludedRouter`` node itself (``original_router``,
``effective_route_contexts``, ``effective_low_priority_routes``) are either
underscore-private or hang off an underscore-private class. Centralising the
import here is the point: if a later release moves it, one module changes.

``RouteContext`` is the right view for an audit rather than the raw
``APIRoute``, because it carries the route's **effective** state -- the path
with its prefixes applied, and the tags and ``dependant`` merged with every
``include_router(..., tags=..., dependencies=...)`` along the way. That is
exactly what a flattened ``APIRoute`` carried under 0.136, so the audits read
the same values they always read.
"""

from collections.abc import Sequence
from typing import Any

from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from app.main import app

try:  # fastapi >= 0.141
    from fastapi.routing import iter_route_contexts
except ImportError:  # pragma: no cover - fastapi < 0.141 flattens already
    iter_route_contexts = None

#: What the helpers below hand back: a bare ``APIRoute`` under fastapi 0.136,
#: a ``fastapi.routing.RouteContext`` wrapping one under 0.141+. Deliberately
#: not a union of the two: ``RouteContext`` does not exist on 0.136, so naming
#: it in an annotation would make this module fail to import there -- and the
#: whole point of the alias is that callers read ``path``/``methods``/``tags``/
#: ``dependant`` off either shape without caring which they hold.
RouteView = Any


def route_views(routes: Sequence[BaseRoute] | None = None) -> list[RouteView]:
    """Every route reachable from ``routes``, flattened, newest fastapi or old.

    Defaults to the live ``app.main.app`` route table. Pass a router's
    ``.routes`` to walk that router instead, in which case the paths returned
    are relative to it, exactly as they were under 0.136.

    The returned objects are ``APIRoute``/``Mount``/``Route`` under fastapi
    0.136 and ``RouteContext`` views of the same under 0.141+. Both expose
    ``path``, ``methods``, ``name``, ``tags`` and ``dependant``, so callers do
    not branch on the version.
    """
    source = app.routes if routes is None else routes
    if iter_route_contexts is None:
        return list(source)
    return list(iter_route_contexts(list(source)))


def underlying_route(view: RouteView) -> BaseRoute:
    """The real route object behind a view, for ``isinstance`` checks.

    Under 0.141 a ``RouteContext`` is never itself an ``APIRoute``, so the
    class test has to happen on what it wraps.
    """
    return getattr(view, "original_route", view)


def api_routes(routes: Sequence[BaseRoute] | None = None) -> list[RouteView]:
    """Every ``APIRoute``, flattened, as an effective-state view.

    The direct replacement for the ``[route for route in app.routes if
    isinstance(route, APIRoute)]`` idiom this suite used in five places.
    """
    return [
        view
        for view in route_views(routes)
        if isinstance(underlying_route(view), APIRoute)
    ]


def route_paths(routes: Sequence[BaseRoute] | None = None) -> set[str]:
    """Every path in the table, including non-API ``Route`` and ``Mount``."""
    return {view.path for view in route_views(routes) if getattr(view, "path", None)}


def route_names(routes: Sequence[BaseRoute] | None = None) -> set[str | None]:
    """Every route ``name`` in the table, mounts included."""
    return {getattr(view, "name", None) for view in route_views(routes)}
