"""The construction-projects report (APRAS-60).

Every case here is a claim about the *document* or about the *authorization
answer*, never about an intermediate representation: the report's contract is
"what a síndico prints", so the assertions read the emitted HTML.

The isolation case (§2) is the one with a non-obvious fixture order, stated
here because getting it wrong would make the case pass vacuously: the **other**
tenant is the default tenant, seeded first by the autouse fixture, and the
**acting** tenant is tenant B. That is what makes a `select(Tenant).first()`
resolution of the masthead logo and the footer name fail the case instead of
accidentally returning the right row.
"""

from __future__ import annotations

import ast
import itertools
import json
import re
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, select

from app.core import clock
from app.core.exceptions import ForbiddenError
from app.core.security import create_access_token, get_password_hash
from app.core.tenant_context import acting_tenant_scope
from app.models.document import AssociationDocument, DocumentFolder
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.services import project_report_service as report
from app.services.storage_service import LocalStorageProvider
from tests.conftest import make_user

if TYPE_CHECKING:  # pragma: no cover
    from fastapi.testclient import TestClient

REPORT_URL = "/api/v1/projects/report"
SAVE_URL = "/api/v1/projects/report/save"

#: The tokens a rendered document must never contain in a text position.
#: Matched on the *text* of the document rather than on its source, because
#: "financeiro" contains `nan` and a CSS colour could contain any of them --
#: the claim is about what a reader sees, not about the bytes.
FORBIDDEN_TEXT_TOKENS = ("None", "NaN", "nan", "null")


def _cpf(serial: int) -> str:
    """A syntactically valid CPF, generated: `user.cpf` is globally unique and
    a hand-written list runs out the moment a case adds one more caller."""
    base = f"{serial:09d}"
    digits = [int(c) for c in base]
    for weights in (range(10, 1, -1), range(11, 1, -1)):
        total = sum(d * w for d, w in zip(digits, weights, strict=True))
        check = (total * 10) % 11
        digits.append(0 if check == 10 else check)
    return "".join(str(d) for d in digits)


_SERIAL = itertools.count(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(user: User, tenant_id: uuid.UUID | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    if tenant_id is not None:
        headers["X-Tenant-Id"] = str(tenant_id)
    return headers


def _user(
    session: Session,
    *,
    profile: str = "ADMINISTRATOR",
    email: str | None = None,
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    full_name: str = "Heitor Polidoro",
) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=email or f"{uuid.uuid4().hex[:10]}@test.com",
        full_name=full_name,
        hashed_password=get_password_hash("password123"),
        profile=profile,
        tenant_id=tenant_id,
        cpf=_cpf(next(_SERIAL)),
    )
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_id))
    session.commit()
    return user


def _user_with_permissions(
    session: Session, permissions: list[str], *, name: str
) -> User:
    """A caller whose authority is exactly `permissions` and nothing else."""
    role = Role(name=name, permissions=permissions, tenant_id=DEFAULT_TENANT_ID)
    session.add(role)
    session.commit()
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@test.com",
        full_name="Caller",
        hashed_password=get_password_hash("password123"),
        cpf=_cpf(next(_SERIAL)),
        is_superuser=False,
        roles=[role],
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    return user


def _project(
    session: Session,
    *,
    title: str = "Coberturas e Portaria (Edificação)",
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    created_at=None,
    **kwargs,
) -> ConstructionProject:
    project = ConstructionProject(
        title=title,
        tenant_id=tenant_id,
        created_at=created_at or clock.db_now(),
        **kwargs,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _milestone(session: Session, project, **kwargs) -> ProjectMilestone:
    milestone = ProjectMilestone(project_id=project.id, **kwargs)
    session.add(milestone)
    session.commit()
    return milestone


def _update(session: Session, project, author, **kwargs) -> ProjectUpdate:
    kwargs.setdefault("content", "Corpo do boletim.")
    update = ProjectUpdate(project_id=project.id, author_id=author.id, **kwargs)
    session.add(update)
    session.commit()
    return update


def _text_of(document: str) -> str:
    """The document's visible text: tags, `<style>` and `<svg>` removed."""
    stripped = re.sub(r"<style.*?</style>", " ", document, flags=re.DOTALL)
    stripped = re.sub(r"<svg.*?</svg>", " ", stripped, flags=re.DOTALL)
    return re.sub(r"<[^>]+>", " ", stripped)


# ---------------------------------------------------------------------------
# §1 -- the route, the shape, and the absence of a totals header
# ---------------------------------------------------------------------------


def test_report_renders_one_page_per_project_with_no_totals_header(
    client: TestClient, session: Session
):
    admin = _user(session)
    _project(session, title="Obra Um", created_at=clock.db_now())
    _project(
        session,
        title="Obra Dois",
        created_at=clock.db_now() + timedelta(seconds=1),
    )

    response = client.get(REPORT_URL, headers=_auth(admin))

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    body = response.text
    assert "Obra Um" in body
    assert "Obra Dois" in body
    assert body.count('class="page') == 2
    # No aggregate block: the report is a stack of sheets, not a dashboard.
    assert "Total de obras" not in body
    assert "Orçamento total" not in body


def test_pages_are_ordered_by_created_at(client: TestClient, session: Session):
    base = clock.db_now()
    _project(session, title="Terceira", created_at=base + timedelta(seconds=2))
    _project(session, title="Primeira", created_at=base)
    _project(session, title="Segunda", created_at=base + timedelta(seconds=1))
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert body.index("Primeira") < body.index("Segunda") < body.index("Terceira")


# ---------------------------------------------------------------------------
# §2 -- isolation, including the milestones and bulletins of the other tenant
# ---------------------------------------------------------------------------


@pytest.fixture(name="two_tenants")
def two_tenants_fixture(session: Session, tenant_b: Tenant):
    """The other tenant is the **default** one, created first by the autouse
    fixture; the acting tenant is B. `select(Tenant).first()` therefore
    returns the other tenant, which is what makes §2 a real test."""
    other = session.get(Tenant, DEFAULT_TENANT_ID)
    other.logo_url = "https://alheio.example/logo-alheio.png"
    other.name = "Condomínio Alheio"
    tenant_b.logo_url = "https://proprio.example/logo-proprio.png"
    tenant_b.name = "Condomínio Próprio"
    session.add(other)
    session.add(tenant_b)
    session.commit()

    outsider = _user(session, tenant_id=DEFAULT_TENANT_ID)
    alien = _project(session, title="Obra Alheia", tenant_id=DEFAULT_TENANT_ID)
    _milestone(
        session,
        alien,
        title="Marco Alheio",
        status=MilestoneStatus.IN_PROGRESS,
        display_order=1,
    )
    _update(
        session,
        alien,
        outsider,
        title="Boletim Alheio",
        content="Conteúdo Alheio",
        photos_json=json.dumps(["https://alheio.example/foto-alheia.jpg"]),
    )

    _project(session, title="Obra Própria", tenant_id=tenant_b.id)
    insider = _user(session, tenant_id=tenant_b.id)
    return tenant_b, insider


def test_the_report_never_leaks_another_tenants_rows(
    tenant_client: TestClient, session: Session, two_tenants
):
    tenant_b, insider = two_tenants

    body = tenant_client.get(REPORT_URL, headers=_auth(insider, tenant_b.id)).text

    assert "Obra Própria" in body
    assert "Obra Alheia" not in body
    # Milestones and bulletins carry no `tenant_id`: a bare `select()` over
    # either would put these three strings in the document.
    assert "Marco Alheio" not in body
    assert "Boletim Alheio" not in body
    assert "Conteúdo Alheio" not in body
    assert "foto-alheia" not in body
    # The other tenant's project must not shift the numbering.
    assert "Obra 01" in body
    assert "Obra 02" not in body


def test_the_masthead_and_footer_name_the_acting_tenant(
    tenant_client: TestClient, session: Session, two_tenants
):
    tenant_b, insider = two_tenants

    body = tenant_client.get(REPORT_URL, headers=_auth(insider, tenant_b.id)).text

    assert 'src="https://proprio.example/logo-proprio.png"' in body
    assert "logo-alheio" not in body
    assert "Condomínio Próprio" in body
    assert "Condomínio Alheio" not in body


def test_the_service_reaches_milestones_and_updates_only_through_the_parent():
    """A structural guard: the module contains no bare `select()` over either
    inherited class. Prose in a docstring rots; this does not."""
    source = Path(report.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    selects = {
        node.args[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "select"
        and node.args
        and isinstance(node.args[0], ast.Name)
    }
    assert "ProjectMilestone" not in selects
    assert "ProjectUpdate" not in selects
    assert selects == {"ConstructionProject", "DocumentFolder", "Role"}
    assert "project.milestones" in source
    assert "project.updates" in source


# ---------------------------------------------------------------------------
# §3 -- the `Obra NN • <kind>` kicker
# ---------------------------------------------------------------------------


def test_the_kicker_numbers_and_splits_the_title(client: TestClient, session: Session):
    base = clock.db_now()
    _project(session, title="Coberturas e Portaria (Edificação)", created_at=base)
    _project(session, title="Reforma da Quadra", created_at=base + timedelta(seconds=1))
    _project(session, title="Guarita Nova", created_at=base + timedelta(seconds=2))
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert "Obra 01 • Edificação" in body
    assert '<h1 class="serif">Coberturas e Portaria</h1>' in body
    assert '<span class="kicker">Obra 02</span>' in body
    assert '<h1 class="serif">Reforma da Quadra</h1>' in body
    assert '<span class="kicker">Obra 03</span>' in body


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Coberturas e Portaria (Edificação)", ("Coberturas e Portaria", "Edificação")),
        ("Reforma da Quadra", ("Reforma da Quadra", None)),
        ("", ("", None)),
        ("Obra (A) (B)", ("Obra (A)", "B")),
    ],
)
def test_split_title_and_kind(raw, expected):
    assert report.split_title_and_kind(raw) == expected


# ---------------------------------------------------------------------------
# §4 -- milestone selection
# ---------------------------------------------------------------------------


def test_milestone_cards_select_three_all_and_three(
    client: TestClient, session: Session
):
    project = _project(session, title="Obra com marcos")
    for index in range(5):
        _milestone(
            session,
            project,
            title=f"Feito {index}",
            status=MilestoneStatus.DONE,
            completion_date=date(2026, 1, 1) + timedelta(days=index),
            display_order=index,
        )
    for index in range(2):
        _milestone(
            session,
            project,
            title=f"Andando {index}",
            status=MilestoneStatus.IN_PROGRESS,
            display_order=index,
        )
    for index in range(5):
        _milestone(
            session,
            project,
            title=f"Futuro {index}",
            status=MilestoneStatus.NEXT_STEPS,
            display_order=index,
        )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text
    done = body.split('class="grp done"')[1].split("</div>")[0]
    doing = body.split('class="grp doing"')[1].split("</div>")[0]
    nxt = body.split('class="grp next"')[1].split("</div>")[0]

    assert done.count("<li>") == 3
    assert re.findall(r"<li>(.*?)</li>", done) == ["Feito 4", "Feito 3", "Feito 2"]
    assert doing.count("<li>") == 2
    assert nxt.count("<li>") == 3
    assert re.findall(r"<li>(.*?)</li>", nxt) == ["Futuro 0", "Futuro 1", "Futuro 2"]


def test_an_empty_milestone_group_renders_an_em_dash(
    client: TestClient, session: Session
):
    _project(session, title="Obra sem marcos")
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert body.count('<p class="none">—</p>') == 3


def test_a_done_milestone_without_a_completion_date_sorts_last(session: Session):
    project = _project(session, title="Ordenação")
    undated = ProjectMilestone(
        project_id=project.id,
        title="Sem data",
        status=MilestoneStatus.DONE,
        display_order=0,
    )
    dated = ProjectMilestone(
        project_id=project.id,
        title="Com data",
        status=MilestoneStatus.DONE,
        completion_date=date(2026, 3, 1),
        display_order=1,
    )
    session.add(undated)
    session.add(dated)
    session.commit()

    selected = report._select_milestones([undated, dated], MilestoneStatus.DONE)

    assert [m.title for m in selected] == ["Com data", "Sem data"]


# ---------------------------------------------------------------------------
# §5 -- planned to date
# ---------------------------------------------------------------------------


CURVE = [
    {"month": "2026-09", "pct": 13.2},
    {"month": "2026-10", "pct": 44.9},
    {"month": "2027-03", "pct": 100.0},
]


def test_planned_to_date_reads_the_latest_qualifying_point():
    assert report.planned_to_date(CURVE, date(2026, 9, 20)) == 13.2
    assert report.planned_to_date(CURVE, date(2026, 10, 1)) == 44.9
    assert report.planned_to_date(CURVE, date(2027, 6, 1)) == 100.0


def test_planned_to_date_is_zero_when_every_point_is_in_the_future():
    assert report.planned_to_date(CURVE, date(2026, 1, 1)) == 0


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "not a list",
        [{"month": "setembro", "pct": 13.2}],
        [{"month": "2026-09"}],
        [{"month": "2026-09", "pct": "treze"}],
        ["2026-09"],
        {"month": "2026-09", "pct": 1.0},
    ],
)
def test_planned_to_date_treats_an_unusable_payload_as_no_curve(payload):
    assert report.planned_to_date(payload, date(2026, 9, 20)) is None


def test_planned_to_date_defaults_to_the_projects_clock():
    """No `today` argument means `app.core.clock`, never `date.today()`."""
    assert report.planned_to_date([{"month": "1970-01", "pct": 7.0}]) == 7.0


# ---------------------------------------------------------------------------
# §6 -- the avanço físico bar
# ---------------------------------------------------------------------------


def _bar(planned: float | None, realized: float) -> str:
    return report._one_bar(planned, realized)


def test_the_bar_is_gold_when_realized_is_ahead():
    markup = _bar(13.2, 22.0)
    assert 'class="seg b"' in markup
    assert "behind" not in markup
    assert 'class="seg a" style="width:13%"' in markup
    assert 'class="one"' in markup
    assert "below" not in markup


def test_the_bar_is_red_when_realized_is_behind():
    markup = _bar(45.0, 22.0)
    assert 'class="seg b behind"' in markup
    assert 'class="seg a" style="width:22%"' in markup
    assert 'class="mark" style="left:45%"' in markup


@pytest.mark.parametrize(
    ("planned", "realized"), [(20.0, 22.0), (24.0, 22.0), (22.0, 22.0)]
)
def test_close_values_move_the_plan_tag_below_the_bar(planned, realized):
    markup = _bar(planned, realized)
    assert 'class="one close"' in markup
    assert 'class="tag plan below"' in markup
    assert 'class="tag real"' in markup


def test_a_gap_of_eight_or_more_keeps_both_tags_above():
    markup = _bar(13.0, 22.0)
    assert 'class="one"' in markup
    assert "close" not in markup
    assert 'class="tag plan"' in markup


def test_no_curve_renders_the_realized_segment_alone():
    markup = _bar(None, 22.0)
    assert "<b>—</b>" in markup
    assert "previsto" in markup
    assert 'class="seg b' not in markup
    assert 'class="mark"' not in markup
    assert 'class="seg a" style="width:22%"' in markup


def test_a_project_without_a_curve_says_previsto_em_dash(
    client: TestClient, session: Session
):
    _project(session, title="Sem cronograma", physical_progress_pct=22.0)
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert "<span>previsto</span><b>—</b>" in body
    assert (
        "Previsto conforme o cronograma físico-financeiro da empreiteira; "
        "realizado conforme a última medição." in body
    )
    assert "<span>Início</span><span>Conclusão</span>" in body


def test_the_curve_column_drives_the_bar(client: TestClient, session: Session):
    today = clock.today_utc()
    _project(
        session,
        title="Com cronograma",
        physical_progress_pct=22.0,
        planned_progress_json=[{"month": today.strftime("%Y-%m"), "pct": 45.0}],
    )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert 'class="seg b behind"' in body
    assert "<span>previsto</span><b>45%</b>" in body


# ---------------------------------------------------------------------------
# §7 -- the budget block
# ---------------------------------------------------------------------------


def test_the_budget_block_formats_money_and_the_gauge(
    client: TestClient, session: Session
):
    _project(
        session,
        title="Orçada",
        total_budget=1_200_000.0,
        executed_budget=312_000.0,
    )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert "R$ 1.200.000,00" in body
    assert "R$ 312.000,00" in body
    assert "R$ 888.000,00" in body  # saldo
    assert "26.0%" in body  # % executado
    assert "<strong>74%</strong>" in body  # saldo restante, the gauge caption
    assert "R$ 888.000,00 ainda disponíveis do orçamento previsto." in body
    assert 'class="budget-row total"' in body


def test_a_zero_budget_renders_a_zero_gauge_and_never_a_nan(
    client: TestClient, session: Session
):
    _project(session, title="Sem orçamento", total_budget=0.0, executed_budget=0.0)
    admin = _user(session)

    response = client.get(REPORT_URL, headers=_auth(admin))

    assert response.status_code == 200
    assert "0.0%" in response.text
    assert "<strong>100%</strong>" in response.text
    assert "NaN" not in response.text


# ---------------------------------------------------------------------------
# §8 -- the bulletins
# ---------------------------------------------------------------------------


def test_only_the_three_newest_bulletins_render_newest_first(
    client: TestClient, session: Session
):
    project = _project(session, title="Com boletins")
    admin = _user(session)
    base = clock.db_now()
    for index in range(5):
        _update(
            session,
            project,
            admin,
            title=f"Boletim {index}",
            created_at=base + timedelta(minutes=index),
        )

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert body.count('class="week"') == 3
    assert re.findall(r"<b>Boletim \d</b>", body) == [
        "<b>Boletim 4</b>",
        "<b>Boletim 3</b>",
        "<b>Boletim 2</b>",
    ]


def test_a_bulletin_shows_at_most_three_photos(client: TestClient, session: Session):
    project = _project(session, title="Com fotos")
    admin = _user(session)
    _update(
        session,
        project,
        admin,
        title="Cinco fotos",
        photos_json=json.dumps([f"https://cdn.example/f{i}.jpg" for i in range(5)]),
    )

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert body.count('alt="Foto do boletim"') == 3


def test_a_bulletin_without_photos_renders_no_photo_grid(
    client: TestClient, session: Session
):
    project = _project(session, title="Sem fotos")
    admin = _user(session)
    _update(session, project, admin, title="Nenhuma foto", photos_json=None)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert '<div class="photo-grid">' not in body


@pytest.mark.parametrize(
    "payload", [None, "", "{not json", json.dumps({"a": 1}), json.dumps([])]
)
def test_decode_photos_is_total(payload):
    assert report.decode_photos(payload) == []


def test_no_bulletin_renders_the_empty_notice(client: TestClient, session: Session):
    _project(session, title="Recém-criada")
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert '<p class="empty">Nenhum boletim publicado.</p>' in body


def test_neither_the_author_nor_the_cost_impact_appears(
    client: TestClient, session: Session
):
    project = _project(session, title="Com custo")
    author = _user(session, full_name="Engenheiro Confidencial")
    reader = _user(session, full_name="Síndica Leitora")
    _update(
        session,
        project,
        author,
        title="Medição",
        content="Corpo.",
        cost_impact=98765.43,
    )

    body = client.get(REPORT_URL, headers=_auth(reader)).text

    assert "Engenheiro Confidencial" not in body
    assert "98765" not in body
    assert "98.765,43" not in body


# ---------------------------------------------------------------------------
# §9 -- masthead, hero and footer
# ---------------------------------------------------------------------------


def test_the_masthead_omits_the_image_when_the_logo_is_absent(
    client: TestClient, session: Session
):
    _project(session, title="Sem logo")
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert "<img" not in body
    assert '<header class="mast">' in body
    assert "Obras em foco" in body
    assert "Relatório de Obras" in body


def test_the_masthead_renders_the_logo_when_present(
    client: TestClient, session: Session
):
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant.logo_url = "https://cdn.example/logo.png"
    session.add(tenant)
    session.commit()
    _project(session, title="Com logo")
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert 'src="https://cdn.example/logo.png"' in body


def test_the_hero_renders_the_status_pill_cover_and_progress(
    client: TestClient, session: Session
):
    project = _project(
        session,
        title="Obra completa",
        description="Modernização das portarias.",
        status=ProjectStatus.IN_PROGRESS,
        physical_progress_pct=22.0,
        cover_photo_url="https://cdn.example/capa.jpg",
    )
    admin = _user(session)
    _update(
        session,
        project,
        admin,
        title="Boletim",
        created_at=clock.db_now() - timedelta(days=3),
    )

    body = client.get(REPORT_URL, headers=_auth(admin)).text
    expected = (clock.db_now() - timedelta(days=3)).strftime("%d/%m/%Y")

    assert '<span class="pill"><i></i>Em andamento</span>' in body
    assert f"Última atualização {expected}" in body
    assert 'src="https://cdn.example/capa.jpg"' in body
    assert "Modernização das portarias." in body
    assert "<small>Progresso geral</small>" in body
    assert "<strong>22% concluído</strong>" in body
    assert '<div class="progress"><span style="width:22%"></span></div>' in body
    assert "<span>Início</span><b>22%</b><span>Conclusão</span>" in body


def test_the_hero_falls_back_to_updated_at_and_a_placeholder(
    client: TestClient, session: Session
):
    project = _project(session, title="Sem boletins nem capa", cover_photo_url=None)
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert '<div class="noimg"></div>' in body
    assert f"Última atualização {project.updated_at.strftime('%d/%m/%Y')}" in body


def test_the_footer_names_the_tenant_and_the_caller(
    client: TestClient, session: Session
):
    _project(session, title="Obra")
    admin = _user(session, full_name="Heitor Polidoro")

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert "· Relatório de Obras</span>" in body
    assert re.search(
        r"Gerado em \d{2}/\d{2}/\d{4} \d{2}:\d{2} por Heitor Polidoro", body
    )


def test_the_tenant_row_is_resolved_by_id_and_a_missing_one_degrades(
    session: Session,
):
    """The resolution path itself, at unit level.

    With the acting tenant set, the renderer reads the row
    `session.get(Tenant, acting_tenant_id(session))` returns; with no such row
    it renders no `<img>` and an empty tenant name rather than raising.
    """
    admin = _user(session)
    _project(session, title="Obra")
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    tenant.logo_url = "https://cdn.example/by-id.png"
    session.add(tenant)
    session.commit()

    with acting_tenant_scope(session, DEFAULT_TENANT_ID):
        assert report._acting_tenant(session).id == DEFAULT_TENANT_ID
        assert 'src="https://cdn.example/by-id.png"' in report.render_report_html(
            session, admin
        )

    ghost = uuid.uuid4()
    with acting_tenant_scope(session, ghost):
        assert report._acting_tenant(session) is None
        # It degrades rather than raising. The document is empty of pages
        # because the *projects* are scoped to the same missing tenant, so the
        # two fragments that read the row are asserted directly.
        rendered = report.render_report_html(session, admin)

    assert "<img" not in rendered
    assert "<img" not in report._masthead_html(None, clock.today_utc())
    assert "Obras em foco" in report._masthead_html(None, clock.today_utc())
    assert "<b></b> · Relatório de Obras" in report._footer_html(
        None, admin, clock.db_now()
    )


# ---------------------------------------------------------------------------
# §10 -- print behaviour and the ported CSS
# ---------------------------------------------------------------------------


def test_the_document_carries_the_ported_print_css(
    client: TestClient, session: Session
):
    _project(session, title="Obra")
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    for colour in (
        "#082f2a",
        "#174b40",
        "#c6a04a",
        "#f7f1e5",
        "#ddd1b6",
        "#eee6d7",
        "#9b7327",
    ):
        assert colour in body, colour
    assert "fonts.googleapis.com/css2?family=DM+Sans" in body
    assert "Playfair+Display" in body
    assert '"Playfair Display", Georgia, serif' in body
    assert '"DM Sans", Arial, sans-serif' in body
    assert "print-color-adjust:exact" in body
    assert "@page { size:A4; margin:0; }" in body
    assert "@media print" in body
    assert "page-break-before:always" in body


@pytest.mark.parametrize("count", [1, 2, 4])
def test_the_page_break_count_is_one_less_than_the_page_count(
    client: TestClient, session: Session, count
):
    base = clock.db_now()
    for index in range(count):
        _project(
            session, title=f"Obra {index}", created_at=base + timedelta(seconds=index)
        )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert body.count('<div class="page brk">') == count - 1
    assert body.count('<div class="page') == count


def test_the_document_carries_no_gantt_timeline_or_curve(
    client: TestClient, session: Session
):
    _project(session, title="Obra")
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert 'class="gantt"' not in body
    assert 'class="tl"' not in body
    assert 'class="deadline"' not in body
    assert "<script" not in body


# ---------------------------------------------------------------------------
# §11 -- degradation
# ---------------------------------------------------------------------------


def test_the_emptiest_possible_project_still_renders(
    client: TestClient, session: Session
):
    _project(
        session,
        title="Obra vazia",
        description=None,
        total_budget=0.0,
        executed_budget=0.0,
        physical_progress_pct=0.0,
        start_date=None,
        estimated_completion_date=None,
        actual_completion_date=None,
        cover_photo_url=None,
        planned_progress_json=None,
    )
    admin = _user(session)

    response = client.get(REPORT_URL, headers=_auth(admin))

    assert response.status_code == 200
    text = _text_of(response.text)
    for token in FORBIDDEN_TEXT_TOKENS:
        assert not re.search(rf"\b{token}\b", text), token


# ---------------------------------------------------------------------------
# §12-§14 -- saving
# ---------------------------------------------------------------------------


@pytest.fixture(name="storage")
def storage_fixture(tmp_path: Path, monkeypatch):
    """A real `LocalStorageProvider` rooted in `tmp_path`.

    Real, not a fake: §13 asserts that a refused caller writes **no file**,
    and an in-memory double could not tell the difference. APRAS-65 moved
    generated output off the upload tree, so the seam is now the
    `generated_storage_provider` factory rather than the provider class.
    """
    base = tmp_path / "generated"

    def _provider() -> LocalStorageProvider:
        return LocalStorageProvider(base_dir=base, url_prefix="/static/generated")

    monkeypatch.setattr(report, "generated_storage_provider", _provider)
    return base


def test_saving_creates_the_folder_once_and_two_distinct_files(
    client: TestClient, session: Session, storage: Path
):
    _project(session, title="Obra")
    admin = _user(session)

    first = client.post(SAVE_URL, headers=_auth(admin))
    second = client.post(SAVE_URL, headers=_auth(admin))

    assert first.status_code == 201
    assert second.status_code == 201
    folders = session.exec(
        select(DocumentFolder).where(DocumentFolder.name == "Obras")
    ).all()
    assert len(folders) == 1
    assert folders[0].parent_id is None
    assert first.json()["folder_id"] == second.json()["folder_id"] == str(folders[0].id)
    documents = session.exec(select(AssociationDocument)).all()
    assert len(documents) == 2
    assert len({doc.file_url for doc in documents}) == 2
    for doc in documents:
        assert re.fullmatch(
            r"Relatório de Obras — \d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", doc.title
        ), doc.title
        assert doc.mime_type == "text/html"
    assert len(list(storage.rglob("*.html"))) == 2


def test_the_saved_document_holds_the_rendered_report(
    client: TestClient, session: Session, storage: Path
):
    _project(session, title="Obra Salva")
    admin = _user(session)

    client.post(SAVE_URL, headers=_auth(admin))

    written = next(iter(storage.rglob("*.html")))
    assert "Obra Salva" in written.read_text(encoding="utf-8")


def test_the_report_route_refuses_a_caller_without_projects_read(
    client: TestClient, session: Session
):
    caller = _user_with_permissions(session, ["documents:create"], name="Sem leitura")

    response = client.get(REPORT_URL, headers=_auth(caller))

    assert response.status_code == 403


def test_a_refused_save_leaves_no_folder_and_no_file(
    client: TestClient, session: Session, storage: Path
):
    _project(session, title="Obra")
    caller = _user_with_permissions(session, ["projects:read"], name="Só leitura")

    response = client.post(SAVE_URL, headers=_auth(caller))

    assert response.status_code == 403
    assert (
        session.exec(select(DocumentFolder).where(DocumentFolder.name == "Obras")).all()
        == []
    )
    assert session.exec(select(AssociationDocument)).all() == []
    assert not list(storage.rglob("*"))


def test_documents_create_without_folder_create_is_201_on_both_calls(
    client: TestClient, session: Session, storage: Path
):
    """§14: the save route's answer never depends on whether the folder exists.

    This is the whole reason `_find_or_create_obras_folder` does not call
    `document_service.create_folder`.
    """
    _project(session, title="Obra")
    caller = _user_with_permissions(
        session,
        ["projects:read", "documents:create", "documents:read"],
        name="Relatórios",
    )

    first = client.post(SAVE_URL, headers=_auth(caller))
    second = client.post(SAVE_URL, headers=_auth(caller))

    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["folder_id"] == second.json()["folder_id"]


def test_save_report_asserts_before_it_renders(session: Session):
    """The `documents:create` check is the first statement, so a refusal costs
    no render, no file and no folder."""
    _project(session, title="Obra")
    caller = _user_with_permissions(session, ["projects:read"], name="Refusada")

    with pytest.raises(ForbiddenError):
        report.save_report(session, caller)

    assert (
        session.exec(select(DocumentFolder).where(DocumentFolder.name == "Obras")).all()
        == []
    )


# ---------------------------------------------------------------------------
# APRAS-65 -- generated output lives off the hardened upload mount
# ---------------------------------------------------------------------------


def test_the_saved_report_lands_in_the_generated_tree(
    client: TestClient, session: Session, storage: Path
):
    """§D4: `/static/generated/YYYY/MM/<uuid>.html`, and nothing in uploads.

    The report is HTML the server rendered, and the Document Center opens it
    in a tab. `/static/uploads` now forces a download for `.html` because a
    client can write there; the generated tree exists so this file does not
    have to pay for that.
    """
    _project(session, title="Obra")
    admin = _user(session)
    uploads = Path("static/uploads")
    before = set(uploads.rglob("*")) if uploads.exists() else set()

    response = client.post(SAVE_URL, headers=_auth(admin))

    assert response.status_code == 201
    file_url = response.json()["file_url"]
    assert re.fullmatch(
        r"/static/generated/\d{4}/\d{2}/[0-9a-f-]{36}\.html", file_url
    ), file_url
    written = [path for path in storage.rglob("*") if path.is_file()]
    assert len(written) == 1
    assert written[0].suffix == ".html"
    assert re.fullmatch(r"\d{4}", written[0].parent.parent.name)
    assert re.fullmatch(r"\d{2}", written[0].parent.name)
    assert (set(uploads.rglob("*")) if uploads.exists() else set()) == before


def test_regenerating_adds_a_generated_row_and_leaves_a_legacy_row_alone(
    client: TestClient, session: Session, storage: Path
):
    """D5: no migration. The old row keeps its `/static/uploads/…` URL.

    A report saved before this change is indistinguishable from a file a
    director planted, so nothing may rewrite it. Re-generating is the remedy,
    and it must add a row rather than touch the old one.
    """
    _project(session, title="Obra")
    admin = _user(session)
    folder_id = report._find_or_create_obras_folder(session)
    legacy = AssociationDocument(
        folder_id=folder_id,
        title="Relatório de Obras — legado",
        file_url="/static/uploads/2025/01/legacy.html",
        file_size_bytes=10,
        mime_type="text/html",
        uploaded_by_id=admin.id,
        publication_year=2025,
        publication_month=1,
    )
    session.add(legacy)
    session.commit()
    session.refresh(legacy)
    legacy_id, legacy_url, legacy_updated = (
        legacy.id,
        legacy.file_url,
        legacy.updated_at,
    )

    response = client.post(SAVE_URL, headers=_auth(admin))

    assert response.status_code == 201
    assert response.json()["file_url"].startswith("/static/generated/")
    assert response.json()["id"] != str(legacy_id)
    session.expire_all()
    reread = session.get(AssociationDocument, legacy_id)
    assert reread.file_url == legacy_url
    assert reread.updated_at == legacy_updated
