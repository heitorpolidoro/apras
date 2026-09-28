"""Where this API answers from, as a browser somewhere else would name it.

Everything this module builds is **absolute**, and that is its whole reason to
exist (APRAS-105 §D). The obras report is rendered by the backend
(``apras-back.vercel.app``) while the page a visitor opens belongs to the
frontend (``apras.vercel.app``), and ``PublicObrasReportPage`` injects the
rendered document into an ``<iframe srcDoc>`` -- whose relative URLs resolve
against the *parent* document's base. A relative ``src`` in the masthead
therefore fails silently, with no console error and no broken-image box worth
noticing.

The base is resolved from :data:`app.core.config.settings` alone. This module
imports no ``os`` and reads no environment variable directly: the three rungs
are ``Settings`` fields, which on a ``case_sensitive=True`` ``BaseSettings``
already *are* the variables Vercel injects, and which a test can override with
the same ``monkeypatch.setattr(settings, ...)`` used everywhere else.
"""

from urllib.parse import quote

from app.core.config import settings

#: What ``main.py`` mounts the v1 router under. Restated here rather than
#: imported, because importing ``app.main`` from a core module would invert the
#: dependency (and pull the whole application graph into a URL builder).
#: ``tests/test_public_logo_route.py`` pins the two against each other.
API_V1_PREFIX = "/api/v1"

#: The prefix ``api.py`` mounts the unauthenticated routers under.
PUBLIC_PREFIX = "/public"

#: Where a developer's ``uvicorn`` answers, and the last rung: no Vercel
#: variable, no explicit setting, so this is a local run.
LOCAL_API_BASE_URL = "http://localhost:8000"


def public_api_base_url() -> str:
    """``scheme://host`` for this deployment, with no trailing slash.

    Four rungs, first match wins: the explicit ``PUBLIC_API_BASE_URL``; else
    Vercel's ``VERCEL_PROJECT_PRODUCTION_URL``; else Vercel's ``VERCEL_URL``;
    else localhost. The two Vercel values carry no scheme, so ``https://`` is
    prepended -- every Vercel domain is TLS-only.

    Trailing slashes are stripped so a join can never double one: a
    ``//api/v1`` path is not the same path on every proxy.
    """
    explicit = settings.PUBLIC_API_BASE_URL.strip()
    if explicit:
        return explicit.rstrip("/")
    for injected in (settings.VERCEL_PROJECT_PRODUCTION_URL, settings.VERCEL_URL):
        host = injected.strip().rstrip("/")
        if host:
            return f"https://{host}"
    return LOCAL_API_BASE_URL


def public_tenant_logo_url(slug: str) -> str:
    """The absolute URL of one condominium's public logo route.

    ``slug`` is percent-encoded with no safe characters: it is a validated
    column today, and a builder that trusted it would be one bad write away
    from emitting a path segment nobody meant.
    """
    path = f"{PUBLIC_PREFIX}/tenants/{quote(slug, safe='')}/logo"
    return f"{public_api_base_url()}{API_V1_PREFIX}{path}"
