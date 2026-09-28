"""The public obras report (APRAS-92).

``GET /api/v1/public/tenants/{slug}/projects/report`` is the second
unauthenticated, tenant-shaped read in the product, and the first that answers
with a whole rendered document. Four properties carry it:

* **No credential of any kind.** No ``Authorization``, no ``X-Tenant-Id``; the
  condominium is named in the path and is the *subject* of the read, exactly as
  on ``/public/tenants/{slug}/branding``.
* **Full parity with the internal report (D2).** The same document
  ``render_report_html`` produces, budget block and gauge included. The two
  bodies are compared field by field here rather than described.
* **Nothing between the caller and the render (D3).** No rate limit, no
  ``Cache-Control``, no ``ETag``: the 31st request inside a minute is a 200,
  and the operator's accepted risk is recorded at the route.
* **Isolation is the ambient scope's, not a ``where`` clause's.** The handler
  enters ``tenant_context.acting_tenant_scope`` around the render and the
  renderer is unchanged, so milestones and bulletins stay on the already
  narrowed relationships.
"""

from __future__ import annotations

import ast
import inspect
import itertools
import json
import re
import uuid
from typing import TYPE_CHECKING

import pytest

from app.api.v1.endpoints import public_projects
from app.core import clock
from app.core.permissions import UNGUARDED_ROUTES
from app.core.security import create_access_token, get_password_hash
from app.models.enums import MilestoneStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from tests.conftest import make_user

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient
    from sqlmodel import Session

#: The route, spelled exactly as FastAPI mounts it.
ROUTE = ("GET", "/api/v1/public/tenants/{slug}/projects/report")

INTERNAL_URL = "/api/v1/projects/report"

#: APRAS-74's limit, which this route deliberately does not carry (D3).
REQUESTS_PAST_THE_DECLINED_LIMIT = 31

_SERIAL = itertools.count(9_500_000)


def _url(slug: str) -> str:
    return f"/api/v1/public/tenants/{slug}/projects/report"


def _cpf(serial: int) -> str:
    base = f"{serial:09d}"
    digits = [int(character) for character in base]
    for weights in (range(10, 1, -1), range(11, 1, -1)):
        total = sum(d * w for d, w in zip(digits, weights, strict=True))
        check = (total * 10) % 11
        digits.append(0 if check == 10 else check)
    return "".join(str(d) for d in digits)


def _user(
    session: Session,
    *,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    full_name: str = "Heitor Polidoro",
):
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@test.com",
        full_name=full_name,
        hashed_password=get_password_hash("password123"),
        profile="ADMINISTRATOR",
        tenant_id=tenant_id,
        cpf=_cpf(next(_SERIAL)),
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_id))
    session.commit()
    return user


def _auth(user, tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


def _project(
    session: Session,
    *,
    title: str = "Coberturas e Portaria (Edificação)",
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    **kwargs,
) -> ConstructionProject:
    kwargs.setdefault("total_budget", 1_200_000)
    kwargs.setdefault("executed_budget", 300_000)
    kwargs.setdefault("physical_progress_pct", 42.0)
    project = ConstructionProject(
        title=title, tenant_id=tenant_id, created_at=clock.db_now(), **kwargs
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _without_timestamps(body: str) -> str:
    """The document with its ``Gerado em ...`` clauses removed.

    What is left is everything the two routes must agree on byte for byte --
    which is the whole document except the footer's author clause, the one
    thing an anonymous render deliberately drops.
    """
    return re.sub(
        r"Gerado em \d{2}/\d{2}/\d{4} \d{2}:\d{2}( por [^<]+)?", "Gerado em", body
    )


def _default_tenant(session: Session) -> Tenant:
    """The default tenant, named so its slug is derived and addressable."""
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant.name = "Condomínio Altos da Serra"
    tenant.slug = "condominio-altos-da-serra"
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


# ---------------------------------------------------------------------------
# §1 -- the 200, and parity with the internal document
# ---------------------------------------------------------------------------


def test_an_anonymous_caller_gets_the_document(client: TestClient, session: Session):
    """ER 1: no credential in the request the client actually made."""
    tenant = _default_tenant(session)
    _project(session, title="Obra Pública")

    response = client.get(_url(tenant.slug))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text.startswith("<!DOCTYPE html>")
    assert "Authorization" not in response.request.headers
    assert "X-Tenant-Id" not in response.request.headers


def test_the_public_body_carries_the_whole_budget_block(
    client: TestClient, session: Session
):
    """ER 2: full parity with the internal report (D2), asserted as an equality
    of the two documents once their timestamps are normalised."""
    tenant = _default_tenant(session)
    _project(session, title="Obra Pública")
    admin = _user(session)

    public = client.get(_url(tenant.slug)).text
    internal = client.get(INTERNAL_URL, headers=_auth(admin)).text

    for marker in (
        "Obra Pública",
        "Orçamento previsto",
        "R$ 1.200.000,00",
        "Executado",
        "R$ 300.000,00",
        "Saldo",
        "R$ 900.000,00",
        "Saldo restante",
        "<svg",
    ):
        assert marker in public, marker
        assert marker in internal, marker

    # The documents differ in exactly one place: the footer's author clause.
    assert _without_timestamps(public) == _without_timestamps(internal)


def test_the_footer_omits_the_author_for_an_anonymous_caller(
    client: TestClient, session: Session
):
    """ER 6: both halves, in one case."""
    tenant = _default_tenant(session)
    _project(session)
    admin = _user(session, full_name="Heitor Polidoro")

    public = client.get(_url(tenant.slug)).text
    internal = client.get(INTERNAL_URL, headers=_auth(admin)).text

    assert re.search(r"Gerado em \d{2}/\d{2}/\d{4} \d{2}:\d{2}</span>", public)
    assert "por Heitor Polidoro" not in public
    assert re.search(
        r"Gerado em \d{2}/\d{2}/\d{4} \d{2}:\d{2} por Heitor Polidoro", internal
    )


def test_a_condominium_with_no_project_still_answers_a_document(
    client: TestClient, session: Session
):
    """Graceful degradation is this renderer's documented behaviour: an empty
    report is a document with no page, never a 404 and never a 500."""
    tenant = _default_tenant(session)

    response = client.get(_url(tenant.slug))

    assert response.status_code == 200
    assert response.text.startswith("<!DOCTYPE html>")
    assert 'class="page' not in response.text


# ---------------------------------------------------------------------------
# §2 -- the 404, for an unknown slug and an inactive condominium alike
# ---------------------------------------------------------------------------


def test_an_unknown_slug_and_an_inactive_condominium_answer_the_same_404(
    client: TestClient, session: Session
):
    """ER 3. Indistinguishable on purpose: an inactive tenant is refused to
    everyone elsewhere, so answering 200 would publish a door nailed shut."""
    tenant = _default_tenant(session)
    _project(session)
    tenant.is_active = False
    session.add(tenant)
    session.commit()

    inactive = client.get(_url(tenant.slug))
    unknown = client.get(_url("nao-existe-este-condominio"))

    assert inactive.status_code == 404
    assert unknown.status_code == 404
    assert inactive.json() == unknown.json()
    assert inactive.json()["detail"] == "Tenant not found"


# ---------------------------------------------------------------------------
# §3 -- isolation
# ---------------------------------------------------------------------------


@pytest.fixture(name="two_tenants")
def two_tenants_fixture(session: Session, tenant_b: Tenant):
    """Tenant B is the one the slug names; the default tenant is the outsider.

    Same fixture order as ``test_project_report.py``'s §2, and for the same
    reason: ``select(Tenant).first()`` returns the **other** tenant, so a
    resolution that ignored the acting scope would fail the case instead of
    accidentally passing it.
    """
    other = session.get(Tenant, DEFAULT_TENANT_ID)
    other.name = "Condomínio Alheio"
    other.slug = "condominio-alheio"
    other.logo_url = "https://alheio.example/logo-alheio.png"
    tenant_b.name = "Condomínio Próprio"
    tenant_b.slug = "condominio-proprio"
    session.add(other)
    session.add(tenant_b)
    session.commit()

    outsider = _user(session, tenant_id=DEFAULT_TENANT_ID)
    alien = _project(session, title="Obra Alheia", tenant_id=DEFAULT_TENANT_ID)
    session.add(
        ProjectMilestone(
            project_id=alien.id,
            title="Marco Alheio",
            status=MilestoneStatus.IN_PROGRESS,
            display_order=1,
        )
    )
    session.add(
        ProjectUpdate(
            project_id=alien.id,
            author_id=outsider.id,
            title="Boletim Alheio",
            content="Conteúdo Alheio",
            photos_json=json.dumps(["https://alheio.example/foto-alheia.jpg"]),
        )
    )
    session.commit()

    _project(session, title="Obra Própria", tenant_id=tenant_b.id)
    session.refresh(tenant_b)
    return tenant_b


def test_the_public_report_never_leaks_another_condominium(
    tenant_client: TestClient, two_tenants: Tenant
):
    """ER 4, including the two tables that carry no ``tenant_id`` at all."""
    body = tenant_client.get(_url(two_tenants.slug)).text

    assert "Obra Própria" in body
    assert "Obra Alheia" not in body
    assert "Marco Alheio" not in body
    assert "Boletim Alheio" not in body
    assert "Conteúdo Alheio" not in body
    assert "foto-alheia" not in body
    assert "Condomínio Próprio" in body
    assert "Condomínio Alheio" not in body
    assert "logo-alheio" not in body
    assert "Obra 01" in body
    assert "Obra 02" not in body


def test_the_anonymous_render_leaves_no_acting_tenant_behind(
    client: TestClient, session: Session, tenant_b: Tenant
):
    """The seam is a *scope*, not an assignment: what the handler establishes
    for the render is restored afterwards, so a session reused by the next
    request is not silently acting in the condominium the last slug named."""
    from app.core.tenant_context import ACTING_TENANT_KEY

    tenant_b.name = "Condomínio Escopo"
    tenant_b.slug = "condominio-escopo"
    session.add(tenant_b)
    session.commit()
    _project(session, title="Obra do Escopo", tenant_id=tenant_b.id)

    assert client.get(_url("condominio-escopo")).status_code == 200
    assert session.info.get(ACTING_TENANT_KEY) is None


# ---------------------------------------------------------------------------
# §4 -- nothing between the caller and the render (D3)
# ---------------------------------------------------------------------------


def test_the_response_carries_no_cache_header_of_any_kind(
    client: TestClient, session: Session
):
    """ER 5's first half. A browser-held copy cannot be invalidated on demand,
    so a freshly published bulletin would stay invisible for the whole TTL."""
    tenant = _default_tenant(session)
    _project(session)

    response = client.get(_url(tenant.slug))

    assert "cache-control" not in response.headers
    assert "etag" not in response.headers
    assert "expires" not in response.headers


def test_the_thirty_first_request_inside_a_minute_is_still_a_200(
    client: TestClient, session: Session
):
    """ER 5's second half: the per-IP limiter APRAS-74 carries was declined
    here, deliberately and twice (D3). APRAS-93 owns any revisit."""
    tenant = _default_tenant(session)
    _project(session)

    statuses = {
        client.get(_url(tenant.slug)).status_code
        for _ in range(REQUESTS_PAST_THE_DECLINED_LIMIT)
    }

    assert statuses == {200}

    # That loop alone proves nothing: `conftest.py` sets
    # `app.state.limiter.enabled = False` for the whole suite, so it would pass
    # unchanged if a `@limiter.limit` were added to this route tomorrow. D3 is
    # an operator decision taken twice, so assert it structurally as well --
    # over the parsed module, not its text, because the docstring above the
    # route *documents* the absence and names all three of `limiter`,
    # `Cache-Control` and `ETag`. A grep would forbid the module explaining
    # itself; the AST sees only what executes.
    tree = ast.parse(inspect.getsource(public_projects))

    decorators = [
        ast.unparse(decorator)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        for decorator in node.decorator_list
    ]
    assert decorators, "no decorated handler found -- the check would be vacuous"
    assert not [d for d in decorators if "limit" in d]

    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "limiter" not in imported

    headers = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        for header in ("Cache-Control", "ETag")
        if node.value == header
    ]
    assert not headers


# ---------------------------------------------------------------------------
# §5 -- the registry, and the internal route's unchanged guard
# ---------------------------------------------------------------------------


def test_the_route_is_on_the_unguarded_allowlist():
    """ER 8: it authenticates nobody, so there is nobody to hold a permission."""
    assert ROUTE in UNGUARDED_ROUTES
    assert len(UNGUARDED_ROUTES) == 30


def test_the_route_is_mounted_globally_scoped():
    """The caller resolves no acting tenant, so ``get_current_tenant`` would
    refuse every request and the fail-closed guard would fire."""
    from app.api.v1 import api as api_module

    mounted = [
        route
        for route in api_module.api_router.routes
        if getattr(route, "path", None) == "/public/tenants/{slug}/projects/report"
    ]
    assert len(mounted) == 1
    assert "public" in mounted[0].tags


def test_the_internal_route_keeps_its_permission_guard(
    client: TestClient, session: Session
):
    """ER 7's first half, asserted here too because this task is what makes a
    caller able to reach the same document with no permission at all."""
    from app.models.role import Role
    from app.models.user import User

    _default_tenant(session)
    _project(session)
    role = Role(
        name="Sem obras", permissions=["documents:read"], tenant_id=DEFAULT_TENANT_ID
    )
    session.add(role)
    session.commit()
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@test.com",
        full_name="Sem Permissão",
        hashed_password=get_password_hash("password123"),
        cpf=_cpf(next(_SERIAL)),
        is_superuser=False,
        roles=[role],
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()

    assert client.get(INTERNAL_URL, headers=_auth(user)).status_code == 403


# ---------------------------------------------------------------------------
# §6 -- the avanço físico bar of a project with no planned curve (APRAS-103)
# ---------------------------------------------------------------------------


def test_a_project_without_a_curve_separates_the_two_labels(
    client: TestClient, session: Session
):
    """APRAS-103: the shape every production project renders today.

    ``planned_progress_json`` unset means ``_one_bar`` takes its no-curve
    branch, which used to stack ``previsto —`` and ``realizado`` in the same
    band. The plan tag now sits below the track, so the public document is
    readable for a condominium that has no schedule on file.
    """
    tenant = _default_tenant(session)
    _project(session, title="Obra sem cronograma", physical_progress_pct=0.0)

    body = client.get(_url(tenant.slug)).text

    assert '<div class="one close">' in body
    assert '<div class="tag plan" style="left:0%">' not in body
    assert (
        '<div class="tag plan below" style="left:0%">'
        "<span>previsto</span><b>—</b></div>" in body
    )
