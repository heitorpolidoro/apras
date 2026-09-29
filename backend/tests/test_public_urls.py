"""Absolute URLs for the surfaces a browser loads from elsewhere (APRAS-105 §D).

The obras report is rendered by `apras-back.vercel.app` and the page a visitor
opens is `apras.vercel.app`: `PublicObrasReportPage` injects the document into
an `<iframe srcDoc>`, whose relative URLs resolve against the *parent*
document's base. So a relative `src` in the masthead silently loads nothing,
and the logo route has to be named absolutely.

Every rung of the base resolution is a `Settings` field, never an `os.environ`
read: `Settings` is a pydantic `BaseSettings` with `case_sensitive=True`, so
declaring `VERCEL_PROJECT_PRODUCTION_URL` and `VERCEL_URL` makes pydantic read
the variables Vercel injects under those exact names -- and keeps each rung
overridable here by the same `monkeypatch.setattr(settings, ...)` the rest of
this suite uses.
"""

import uuid
from pathlib import Path

import pytest

from app.core import urls
from app.core.config import settings


@pytest.fixture(name="no_base")
def no_base_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every rung cleared, so a case sets exactly the one it is about."""
    monkeypatch.setattr(settings, "PUBLIC_API_BASE_URL", "")
    monkeypatch.setattr(settings, "VERCEL_PROJECT_PRODUCTION_URL", "")
    monkeypatch.setattr(settings, "VERCEL_URL", "")


def test_the_explicit_setting_wins_over_every_other_rung(
    monkeypatch: pytest.MonkeyPatch, no_base
):
    """Rung 1: the override for a backend served from a domain of our own."""
    monkeypatch.setattr(settings, "PUBLIC_API_BASE_URL", "https://api.apras.com.br")
    monkeypatch.setattr(settings, "VERCEL_PROJECT_PRODUCTION_URL", "prod.vercel.app")
    monkeypatch.setattr(settings, "VERCEL_URL", "preview.vercel.app")

    assert urls.public_api_base_url() == "https://api.apras.com.br"


def test_the_production_url_vercel_injects_is_the_second_rung(
    monkeypatch: pytest.MonkeyPatch, no_base
):
    """Rung 2: production is correct with no new variable to forget."""
    monkeypatch.setattr(
        settings, "VERCEL_PROJECT_PRODUCTION_URL", "apras-back.vercel.app"
    )
    monkeypatch.setattr(settings, "VERCEL_URL", "preview.vercel.app")

    assert urls.public_api_base_url() == "https://apras-back.vercel.app"


def test_the_deployment_url_is_the_third_rung(monkeypatch: pytest.MonkeyPatch, no_base):
    """Rung 3: a preview deployment names itself, and its report still loads."""
    monkeypatch.setattr(settings, "VERCEL_URL", "apras-back-abc123.vercel.app")

    assert urls.public_api_base_url() == "https://apras-back-abc123.vercel.app"


def test_local_development_is_the_last_rung(no_base):
    """Rung 4: no Vercel, no setting -- the port `uvicorn` is run on here."""
    assert urls.public_api_base_url() == "http://localhost:8000"


@pytest.mark.parametrize(
    "configured",
    [
        pytest.param("https://api.apras.com.br/", id="one-slash"),
        pytest.param("https://api.apras.com.br///", id="several"),
    ],
)
def test_a_trailing_slash_is_normalised_so_the_join_never_doubles_one(
    monkeypatch: pytest.MonkeyPatch, no_base, configured: str
):
    monkeypatch.setattr(settings, "PUBLIC_API_BASE_URL", configured)

    assert urls.public_api_base_url() == "https://api.apras.com.br"
    assert "//api/v1" not in urls.public_tenant_logo_url("altos-da-serra")


def test_the_logo_url_is_absolute_and_names_the_route_as_fastapi_mounts_it(
    monkeypatch: pytest.MonkeyPatch, no_base
):
    monkeypatch.setattr(
        settings, "PUBLIC_API_BASE_URL", "https://apras-back.vercel.app"
    )

    assert urls.public_tenant_logo_url("altos-da-serra") == (
        "https://apras-back.vercel.app/api/v1/public/tenants/altos-da-serra/logo"
    )


def test_a_slug_that_would_break_the_path_is_percent_encoded(
    monkeypatch: pytest.MonkeyPatch, no_base
):
    """`slug` is a validated column, but a URL builder that trusts its input is
    one bad write away from emitting a path segment nobody meant."""
    monkeypatch.setattr(
        settings, "PUBLIC_API_BASE_URL", "https://apras-back.vercel.app"
    )

    assert urls.public_tenant_logo_url("a/b") == (
        "https://apras-back.vercel.app/api/v1/public/tenants/a%2Fb/logo"
    )


def test_the_builder_reads_settings_and_never_the_environment():
    """The three rungs are `Settings` fields, so this module imports no `os`."""
    source = urls.__file__ or ""
    assert source.endswith("urls.py")
    text = Path(source).read_text(encoding="utf-8")
    assert "import os" not in text
    assert "os.environ" not in text
    assert "getenv" not in text


# ---------------------------------------------------------------------------
# The public cover-photo route (APRAS-104 §D)
# ---------------------------------------------------------------------------


def test_the_cover_url_is_absolute_and_names_the_route_as_fastapi_mounts_it(
    monkeypatch: pytest.MonkeyPatch, no_base
):
    """The obras report's hero `<img src>`, which the `<iframe srcDoc>` forces
    to be absolute for exactly the reason the logo's is."""
    monkeypatch.setattr(
        settings, "PUBLIC_API_BASE_URL", "https://apras-back.vercel.app"
    )
    project_id = uuid.UUID("2f1c9d4e-7b3a-4c58-9e10-5d6a7b8c9d01")

    assert urls.public_project_cover_url("altos-da-serra", project_id) == (
        "https://apras-back.vercel.app/api/v1/public/tenants/altos-da-serra"
        f"/projects/{project_id}/cover"
    )


def test_a_cover_urls_slug_that_would_break_the_path_is_percent_encoded(
    monkeypatch: pytest.MonkeyPatch, no_base
):
    monkeypatch.setattr(
        settings, "PUBLIC_API_BASE_URL", "https://apras-back.vercel.app"
    )
    project_id = uuid.UUID("2f1c9d4e-7b3a-4c58-9e10-5d6a7b8c9d01")

    assert urls.public_project_cover_url("a/b", project_id) == (
        "https://apras-back.vercel.app/api/v1/public/tenants/a%2Fb"
        f"/projects/{project_id}/cover"
    )


def test_the_cover_url_never_doubles_a_slash_before_the_api_prefix(
    monkeypatch: pytest.MonkeyPatch, no_base
):
    monkeypatch.setattr(
        settings, "PUBLIC_API_BASE_URL", "https://apras-back.vercel.app///"
    )

    assert "//api/v1" not in urls.public_project_cover_url("altos", uuid.uuid4())
