"""The obras report's own identity: its palette and its logo (APRAS-92 §A/§B).

Two claims, and every case here is a claim about the **emitted document**
rather than about an intermediate value:

**§A -- the palette is the tenant's, or today's.** ``render_report_html``
generates its ``:root`` block from ``app.core.branding.build_theme``, through
the two module tables
``project_report_service.REPORT_ROLE_SOURCES`` (variable -> theme key) and
``FALLBACK_PALETTE`` (variable -> the literal a tenant with no brand keeps).
``build_theme(None) is None``, so an unbranded condominium's report is
byte-identical to what APRAS-60 shipped -- which is why
``tests/test_project_report.py`` is left **unmodified** as the authenticated
half of that claim. No colour is derived here: every ratio below is measured
with ``branding.contrast_ratio`` on the ``oklch()`` strings the document
actually carries, and the graphical pairs that sit below 3:1 are asserted at
their figures rather than skipped, so a change that makes one worse fails.

**§B -- the logo is bytes, not a URL, whenever it can be read locally.** Three
rungs, in order: a ``data:`` URI when the storage provider can read its own
object back, today's ``<img src>`` for an absolute ``http(s)`` value, and no
``<img>`` at all otherwise. **No outbound HTTP request is made while
rendering** -- ``test_rendering_makes_no_outbound_request`` blocks the socket
layer and the three clients and still expects a 200.
"""

from __future__ import annotations

import base64
import itertools
import re
import urllib.request
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from app.core import clock
from app.core.branding import build_theme, contrast_ratio, parse_oklch
from app.core.security import create_access_token, get_password_hash
from app.core.urls import public_tenant_logo_url
from app.models.project import ConstructionProject
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.services import project_report_service as report
from app.services import tenant_service as tenant_service_module
from app.services.storage_service import LocalStorageProvider
from app.services.tenant_service import TenantService
from tests.conftest import make_user

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient
    from sqlmodel import Session

REPORT_URL = "/api/v1/projects/report"


def _public_url(slug: str) -> str:
    return f"/api/v1/public/tenants/{slug}/projects/report"


#: The five brands this repository already types as cases (APRAS-68/88).
BRANDS = ("#059669", "#dc2626", "#2563eb", "#7c3aed", "#facc15")

#: The nine literals an unbranded condominium's report keeps (ER 12). The
#: seven ``test_project_report.py`` already pins, plus the gauge's two sheen
#: stops -- the two that would otherwise have been re-derived.
FALLBACK_HEXES = (
    "#082f2a",
    "#174b40",
    "#2d6b5c",
    "#c6a04a",
    "#f7f1e5",
    "#ddd1b6",
    "#eee6d7",
    "#fbf8f1",
    "#9b7327",
)

#: Every text-on-surface pair the report produces, as *variable names* and not
#: as restated figures: 16 pairs, all of which must measure >= 4.5 for each of
#: :data:`BRANDS`. Enumerated once, here, because the claim is about the
#: document and not about the mapping table -- a variable that stops carrying
#: text is a change to this list and therefore reviewable.
REPORT_TEXT_PAIRS: tuple[tuple[str, str], ...] = (
    *(
        (ink, surface)
        for ink in ("ink", "muted", "brand-text")
        for surface in ("surface", "card", "soft", "hero")
    ),
    ("kicker", "card"),
    ("kicker", "hero"),
    ("foot-ink", "foot"),
    ("brand-ink", "brand"),
)

#: WCAG 2.1 AA for normal text, and the 1.4.11 floor for a meaningful graphic.
TEXT_FLOOR = 4.5
GRAPHIC_FLOOR = 3.0

#: The graphical pairs §A deliberately leaves below 3:1, with the figures two
#: independent implementations reproduced. Asserted, never skipped: the
#: accepted risk is only accepted while it is *this* big.
#: ``(brand hex, accent hex, foreground, background, ratio)``.
GRAPHICAL_PAIRS_BELOW_THREE: tuple[tuple[str, str, str, str, float], ...] = (
    ("#059669", "#059669", "brand", "line", 2.9478),
    ("#facc15", "#facc15", "brand", "line", 1.2111),
    ("#facc15", "#facc15", "brand", "card", 1.5338),
    ("#facc15", "#facc15", "brand-alt", "card", 1.5338),
    ("#facc15", "#facc15", "brand-alt", "line", 1.2111),
    # A tenant whose two typed colours differ: the two bar segments part
    # company, and `--brand-alt` stops being visible on a card.
    ("#059669", "#c6a04a", "brand-alt", "card", 2.4952),
    ("#059669", "#c6a04a", "brand", "brand-alt", 1.4911),
    ("#2563eb", "#facc15", "brand-alt", "card", 1.5338),
    # One hex typed for both: the two segments are indistinguishable, which
    # the printed `previsto`/`realizado` labels are what makes survivable.
    ("#059669", "#059669", "brand", "brand-alt", 1.0),
)

_SERIAL = itertools.count(9_000_000)

_ROOT_BLOCK = re.compile(r":root \{(?P<body>[^}]*)\}")


def _cpf(serial: int) -> str:
    """A syntactically valid, unique CPF (`user.cpf` is globally unique)."""
    base = f"{serial:09d}"
    digits = [int(character) for character in base]
    for weights in (range(10, 1, -1), range(11, 1, -1)):
        total = sum(d * w for d, w in zip(digits, weights, strict=True))
        check = (total * 10) % 11
        digits.append(0 if check == 10 else check)
    return "".join(str(d) for d in digits)


def _admin(session: Session, tenant_id: uuid.UUID = DEFAULT_TENANT_ID):
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@test.com",
        full_name="Heitor Polidoro",
        hashed_password=get_password_hash("password123"),
        profile="ADMINISTRATOR",
        tenant_id=tenant_id,
        cpf=_cpf(next(_SERIAL)),
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_id))
    session.commit()
    return user


def _auth(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _project(session: Session, *, title: str = "Obra Branded") -> ConstructionProject:
    project = ConstructionProject(
        title=title,
        tenant_id=DEFAULT_TENANT_ID,
        created_at=clock.db_now(),
        total_budget=1_200_000,
        executed_budget=300_000,
        physical_progress_pct=42.0,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _brand(session: Session, theme: dict | None) -> Tenant:
    """Store ``theme`` on the default tenant and hand the row back."""
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant.brand_theme = theme
    tenant.name = "Condomínio Padrão"
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


def _simple(primary: str, accent: str | None = None) -> dict[str, str]:
    return {"mode": "simple", "primary": primary, "accent": accent or primary}


def _bodies(client: TestClient, session: Session, theme: dict | None) -> list[str]:
    """The same document off both routes: authenticated, then anonymous."""
    tenant = _brand(session, theme)
    _project(session)
    admin = _admin(session)

    internal = client.get(REPORT_URL, headers=_auth(admin))
    public = client.get(_public_url(tenant.slug))

    assert internal.status_code == 200, internal.text[:200]
    assert public.status_code == 200, public.text[:200]
    return [internal.text, public.text]


def _root_values(document: str) -> dict[str, str]:
    """The ``:root`` block, read back as ``variable name -> emitted value``."""
    match = _ROOT_BLOCK.search(document)
    assert match is not None, "the document carries no :root block"
    values: dict[str, str] = {}
    for declaration in match.group("body").split(";"):
        if not declaration.strip():
            continue
        name, _, value = declaration.partition(":")
        values[name.strip().removeprefix("--")] = value.strip()
    return values


def _rendered(session: Session, theme: dict | None) -> str:
    """One document, rendered off the service with no route in the way."""
    _brand(session, theme)
    _project(session)
    admin = _admin(session)
    return report.render_report_html(session, admin)


def _measured(theme: dict[str, str]) -> dict[str, str]:
    """Each report variable's emitted value, for a stored simple-mode theme."""
    light = build_theme(theme)["light"]
    return {name: light[key] for name, key in report.REPORT_ROLE_SOURCES.items()}


def _ratio(values: dict[str, str], foreground: str, background: str) -> float:
    return contrast_ratio(
        parse_oklch(values[foreground]), parse_oklch(values[background])
    )


# ---------------------------------------------------------------------------
# §A.1 -- the two tables, and the fallback
# ---------------------------------------------------------------------------


def test_the_two_role_tables_name_exactly_the_same_variables():
    """ER 15's premise: one set of names, two sources of values."""
    assert set(report.REPORT_ROLE_SOURCES) == set(report.FALLBACK_PALETTE)
    assert len(report.REPORT_ROLE_SOURCES) == 19


def test_every_named_variable_is_actually_referenced_by_the_document(
    session: Session,
):
    """A dead variable cannot be added -- which is how ``--gold-light`` survived.

    Read off the rendered document rather than off the stylesheet constant, so
    the gauge's own variables (``--brand-sheen``, ``--soft-sheen``,
    ``--brand-ink``) count where they are actually used.
    """
    document = _rendered(session, None)
    body = _ROOT_BLOCK.sub(" ", document)

    missing = [
        name for name in report.REPORT_ROLE_SOURCES if f"var(--{name})" not in body
    ]
    assert not missing, f"declared but never referenced: {missing}"


def test_an_unbranded_condominium_keeps_todays_palette(
    client: TestClient, session: Session
):
    """ER 12, on both routes: nine literals, and not one ``oklch()``."""
    for body in _bodies(client, session, None):
        for hex_value in FALLBACK_HEXES:
            assert hex_value in body, hex_value
        assert "oklch(" not in body
        assert set(_root_values(body)) == set(report.FALLBACK_PALETTE)
        assert _root_values(body) == report.FALLBACK_PALETTE


def test_the_fallback_hero_keeps_its_designed_gradient(session: Session):
    """The hero's whole ``background`` **value** rides the variable, which is
    what lets the three-layer gradient survive verbatim."""
    document = _rendered(session, None)

    assert "radial-gradient(circle at 82% 20%" in document
    assert "linear-gradient(120deg, #edf1e9, #f4e8cb)" in document
    assert ".hero { padding:6mm 14mm 8mm; background:var(--hero); }" in document


def test_a_branded_condominium_emits_the_theme_and_no_fallback_literal(
    client: TestClient, session: Session
):
    """ER 13, on both routes."""
    for body in _bodies(client, session, _simple("#dc2626")):
        assert "oklch(0.58 0.22 27.33)" in body
        for gone in ("#174b40", "#c6a04a", "#9b7327", "#f7f1e5"):
            assert gone not in body, gone


def test_each_variable_carries_the_value_its_theme_key_emits(session: Session):
    """The mapping, asserted by *reading* ``REPORT_ROLE_SOURCES``.

    Restating the table here would only assert that two copies of it agree.
    """
    theme = _simple("#7c3aed", "#059669")
    document = _rendered(session, theme)

    emitted = _root_values(document)
    light = build_theme(theme)["light"]
    for name, key in report.REPORT_ROLE_SOURCES.items():
        assert emitted[name] == light[key], name
    for literal in report.FALLBACK_PALETTE.values():
        assert literal not in ";".join(emitted.values())


def test_a_branded_report_still_renders_its_project_budget_and_gauge(
    session: Session,
):
    """The palette change breaks no markup."""
    document = _rendered(session, _simple("#2563eb"))

    assert "Obra Branded" in document
    assert "R$ 1.200.000,00" in document
    assert "R$ 300.000,00" in document
    assert "R$ 900.000,00" in document
    assert '<div class="cyl">' in document
    assert "<svg" in document


# ---------------------------------------------------------------------------
# §A.2 -- the gauge: three stops, flat under a theme, sheened under the fallback
# ---------------------------------------------------------------------------


def _gradient_stops(document: str, gradient_id: str) -> list[str]:
    match = re.search(
        rf'<linearGradient id="{gradient_id}"[^>]*>(?P<body>.*?)</linearGradient>',
        document,
        flags=re.DOTALL,
    )
    assert match is not None, gradient_id
    return re.findall(r'stop-color="([^"]+)"', match.group("body"))


@pytest.mark.parametrize("gradient_id", ["g", "e"])
def test_the_gauge_keeps_two_three_stop_gradients(session: Session, gradient_id):
    """Today's markup, unchanged: the values moved, the elements did not."""
    for theme in (None, _simple("#dc2626")):
        document = _rendered(session, theme)
        assert len(_gradient_stops(document, gradient_id)) == 3


def test_under_a_theme_each_gauge_gradient_resolves_to_a_flat_fill(
    session: Session,
):
    """ER 14: ``--brand``/``--brand-sheen`` and ``--soft``/``--soft-sheen``
    each collapse onto one ``oklch()`` string, so both tanks render flat."""
    document = _rendered(session, _simple("#7c3aed"))
    values = _root_values(document)

    for gradient_id in ("g", "e"):
        resolved = {
            values[stop.removeprefix("var(--").removesuffix(")")]
            for stop in _gradient_stops(document, gradient_id)
        }
        assert len(resolved) == 1, (gradient_id, resolved)

    assert values["brand"] == values["brand-sheen"]
    assert values["soft"] == values["soft-sheen"]
    # The meniscus is distinguished from the flat tank by its outline alone,
    # which it already had.
    assert 'stroke="var(--brand-alt)" stroke-width="1.2"' in document


def test_under_the_fallback_the_gauge_keeps_its_two_sheen_stops(session: Session):
    """The designed sheen survives byte for byte for an unbranded condominium."""
    document = _rendered(session, None)
    values = _root_values(document)

    assert values["brand-sheen"] == "#2d6b5c"
    assert values["soft-sheen"] == "#fbf8f1"
    assert values["brand"] != values["brand-sheen"]
    assert values["soft"] != values["soft-sheen"]


# ---------------------------------------------------------------------------
# §A.3 -- the measurement
# ---------------------------------------------------------------------------


def test_the_text_pair_list_is_the_sixteen_the_spec_enumerates():
    assert len(REPORT_TEXT_PAIRS) == 16
    assert len(set(REPORT_TEXT_PAIRS)) == 16
    named = {name for pair in REPORT_TEXT_PAIRS for name in pair}
    assert named <= set(report.REPORT_ROLE_SOURCES)


@pytest.mark.parametrize("brand", BRANDS)
def test_every_text_pair_clears_aa_for_every_brand(session: Session, brand: str):
    """ER 15: 16 pairs x 5 brands = 80 figures, all >= 4.5.

    Measured on the strings the **document** carries, read back out of its
    ``:root`` block, so nothing here can pass against a value the browser
    never receives.
    """
    values = _root_values(_rendered(session, _simple(brand)))

    for foreground, background in REPORT_TEXT_PAIRS:
        ratio = _ratio(values, foreground, background)
        assert ratio >= TEXT_FLOOR, f"{foreground}/{background} = {ratio:.4f}"


def test_the_thinnest_text_cushion_is_the_one_the_spec_records(session: Session):
    """The worst of the 80: ``--muted`` on ``--soft`` for ``#facc15``.

    Pinned at 4dp because a derivation that moves must fail loudly here rather
    than degrade silently: the cushion over the 4.5 floor is 0.0028.
    """
    worst = min(
        (
            _ratio(_measured(_simple(brand)), foreground, background),
            brand,
            foreground,
            background,
        )
        for brand in BRANDS
        for foreground, background in REPORT_TEXT_PAIRS
    )
    ratio, brand, foreground, background = worst

    assert (brand, foreground, background) == ("#facc15", "muted", "soft")
    assert round(ratio, 4) == 4.5028

    values = _root_values(_rendered(session, _simple("#facc15")))
    assert round(_ratio(values, "muted", "soft"), 4) == 4.5028


@pytest.mark.parametrize(
    ("primary", "accent", "foreground", "background", "expected"),
    GRAPHICAL_PAIRS_BELOW_THREE,
)
def test_the_graphical_pairs_below_three_are_asserted_not_skipped(
    primary, accent, foreground, background, expected
):
    """ER 17. §A repairs none of these, by decision -- repairing one would be
    a second colour derivation, which ``branding.py`` owns and forbids here.
    Every quantity these graphics encode is printed as text beside them, so
    WCAG 1.4.1 holds where 1.4.11 misses."""
    values = _measured(_simple(primary, accent))
    ratio = _ratio(values, foreground, background)

    assert round(ratio, 4) == expected
    assert ratio < GRAPHIC_FLOOR


def test_the_renderer_records_the_failing_graphical_pairs_at_the_code():
    """ER 18: the accepted risk is readable where the palette is emitted."""
    source = Path(report.__file__).read_text(encoding="utf-8")

    for figure in ("2.9478", "1.2111", "1.5338", "2.4952", "1.4911"):
        assert figure in source, figure
    assert "1.4.11" in source


def test_the_renderer_derives_no_colour_of_its_own():
    """``branding.py`` is the only colour derivation in the repository."""
    source = Path(report.__file__).read_text(encoding="utf-8")

    for forbidden in ("hex_to_oklch", "OklchColor", "relative_luminance", "gamut_map"):
        assert forbidden not in source, forbidden


# ---------------------------------------------------------------------------
# §B -- the logo: three rungs
# ---------------------------------------------------------------------------

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH"
    "/q842iQAAAABJRU5ErkJggg=="
)


@pytest.fixture(name="uploads")
def uploads_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The logo provider, rooted in ``tmp_path`` instead of ``static/uploads``.

    A real ``LocalStorageProvider``, so ``resolve_own_url``'s prefix rule and
    its containment check are the production ones.
    """
    provider = LocalStorageProvider(base_dir=tmp_path)
    monkeypatch.setattr(tenant_service_module, "_storage_provider", provider)
    return tmp_path


def _store_logo(uploads: Path, name: str, payload: bytes) -> str:
    target = uploads / "2026" / "09" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return f"/static/uploads/2026/09/{name}"


def _masthead(document: str) -> str:
    match = re.search(r'<header class="mast">.*?</header>', document, flags=re.DOTALL)
    assert match is not None
    return match.group(0)


def test_a_stored_logo_is_referenced_by_the_public_route_absolutely(
    client: TestClient, session: Session, uploads: Path
):
    """APRAS-105 §E: the bytes leave the document and a URL replaces them.

    The URL is **absolute** and that is load-bearing: this document is injected
    into an ``<iframe srcDoc>`` on the frontend's origin, so a relative ``src``
    would resolve against the wrong base and load nothing at all.
    """
    url = _store_logo(uploads, "logo.png", PNG_BYTES)
    tenant = _brand(session, None)
    tenant.logo_url = url
    session.add(tenant)
    session.commit()
    _project(session)
    admin = _admin(session)
    expected = public_tenant_logo_url(tenant.slug)

    for body in (
        client.get(REPORT_URL, headers=_auth(admin)).text,
        client.get(_public_url(tenant.slug)).text,
    ):
        assert f'<img src="{expected}"' in _masthead(body)
        assert expected.startswith("http://")
        assert "data:image" not in body
        assert "base64," not in body
        # The storage URL is no longer a display source: it is storage truth
        # and nothing else.
        assert url not in body


def test_the_masthead_reads_no_storage_at_all(
    session: Session, uploads: Path, monkeypatch: pytest.MonkeyPatch
):
    """The read moved behind the route, where the browser makes it once.

    Rendering used to hit the provider on every request of an uncached public
    route; now it touches nothing.
    """

    def explode(*_args, **_kwargs):
        raise AssertionError("the renderer read storage")

    monkeypatch.setattr(
        tenant_service_module._storage_provider.__class__, "read_file", explode
    )
    tenant = _brand(session, None)
    tenant.logo_url = _store_logo(uploads, "logo.png", PNG_BYTES)
    session.add(tenant)
    session.commit()
    _project(session)
    admin = _admin(session)

    document = report.render_report_html(session, admin)

    assert public_tenant_logo_url(tenant.slug) in _masthead(document)


def test_a_report_with_a_logo_and_one_without_differ_by_under_two_kib(
    session: Session, uploads: Path
):
    """APRAS-93's measurement, now bounded.

    The embedded logo was ~140 KiB of base64 and about 89% of a
    single-project report's bytes. What is left is one URL.
    """
    tenant = _brand(session, None)
    tenant.logo_url = None
    session.add(tenant)
    session.commit()
    _project(session)
    admin = _admin(session)

    without = report.render_report_html(session, admin)

    tenant.logo_url = _store_logo(uploads, "logo.png", PNG_BYTES * 200)
    session.add(tenant)
    session.commit()

    with_logo = report.render_report_html(session, admin)

    assert abs(len(with_logo) - len(without)) < 2 * 1024


def test_a_null_logo_url_renders_the_no_logo_masthead(
    client: TestClient, session: Session, uploads: Path
):
    """ER: no logo, no broken image element -- no ``<img>`` at all."""
    tenant = _brand(session, None)
    tenant.logo_url = None
    session.add(tenant)
    session.commit()
    _project(session)
    admin = _admin(session)

    for body in (
        client.get(REPORT_URL, headers=_auth(admin)).text,
        client.get(_public_url(tenant.slug)).text,
    ):
        assert "<img" not in _masthead(body)
        assert '<div class="name">Relatório de Obras</div>' in body

    # The same refusal at the unit that owns it: a condominium with nothing
    # stored has no logo to serve, and asking for one is not an error.
    assert TenantService.logo_bytes(tenant) is None
    assert TenantService.logo_bytes(None) is None


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>"),
        ("logo.bin", PNG_BYTES),
        ("logo.png", b"x" * (TenantService.LOGO_MAX_FILE_SIZE + 1)),
    ],
)
def test_a_logo_the_product_would_not_accept_is_never_served(
    session: Session, uploads: Path, name: str, payload: bytes
):
    """An untyped suffix, active content, and a file swapped past the ceiling.

    The unit that owns the logo rules refuses all three, so the public route
    answers 404 for each -- the report's masthead links a URL that serves
    nothing rather than publishing an SVG's active content.
    """
    url = _store_logo(uploads, name, payload)
    tenant = _brand(session, None)
    tenant.logo_url = url
    session.add(tenant)
    session.commit()

    assert TenantService.logo_bytes(tenant) is None


def test_a_value_escaping_the_uploads_directory_reads_nothing(
    session: Session, uploads: Path
):
    """ER 20: the containment check, at the unit the route reads through.

    Not reachable today -- ``logo_url`` is written only by the validated
    upload path -- but a read primitive invoked from an anonymous route must
    not depend on who wrote the value it is handed.
    """
    provider = tenant_service_module._storage_provider
    assert provider.resolve_own_url("/static/uploads/../../../etc/passwd") is None
    assert provider.read_file("/static/uploads/../../../etc/passwd") is None

    tenant = _brand(session, None)
    tenant.logo_url = "/static/uploads/../../../etc/passwd"

    assert TenantService.logo_bytes(tenant) is None


def test_rendering_makes_no_outbound_request(
    client: TestClient, session: Session, uploads: Path, monkeypatch
):
    """The socket layer and all three clients are made to raise.

    ``httpx.Client.send`` itself is deliberately **not** patched -- the test
    client is an ``httpx.Client`` over an in-process ASGI transport, so
    patching it would block the request under test rather than the network.
    What is blocked is every path that reaches a real socket:
    ``HTTPTransport.handle_request``, ``httpx``'s module-level helpers,
    ``urllib.request.urlopen``, and ``socket.socket.connect`` underneath all of
    them. ``requests`` is not a dependency of this backend, so it is patched
    only where it is importable -- and the socket block covers it regardless.
    """

    def explode(*_args, **_kwargs):
        raise AssertionError("the renderer made an outbound request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", explode)
    for helper in ("request", "get", "post", "stream"):
        monkeypatch.setattr(httpx, helper, explode)
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    monkeypatch.setattr("socket.socket.connect", explode)
    try:
        import requests

        monkeypatch.setattr(requests, "request", explode)
    except ImportError:
        pass

    tenant = _brand(session, _simple("#059669"))
    tenant.logo_url = "https://cdn.example/remoto.png"
    session.add(tenant)
    session.commit()
    _project(session)
    admin = _admin(session)

    internal = client.get(REPORT_URL, headers=_auth(admin))
    public = client.get(_public_url(tenant.slug))

    assert internal.status_code == 200
    assert public.status_code == 200
    for body in (internal.text, public.text):
        assert public_tenant_logo_url(tenant.slug) in _masthead(body)
        # The stored URL is never the `src`, not even when it is absolute.
        assert "cdn.example" not in body


# ---------------------------------------------------------------------------
# The absent user -- the footer's only use of one
# ---------------------------------------------------------------------------


def test_the_footer_drops_the_author_clause_for_an_anonymous_render(
    session: Session,
):
    _brand(session, None)
    _project(session)

    document = report.render_report_html(session, None)

    assert re.search(r"Gerado em \d{2}/\d{2}/\d{4} \d{2}:\d{2}</span>", document)
    assert " por " not in document
