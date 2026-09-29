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
import inspect
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
from app.core.urls import public_project_cover_url, public_tenant_logo_url
from app.models.document import AssociationDocument, DocumentFolder
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.services import project_report_service as report
from app.services import project_service as project_service_module
from app.services.storage_service import LocalStorageProvider
from tests.conftest import make_user
from tests.test_project_report_bar_geometry import parse_css
from tests.test_project_stage_detail import split_div_block, split_groups_block

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


def _card(document: str, css_class: str) -> str:
    """The whole markup of one milestone card, nesting included.

    Shared by every §4 case (APRAS-113 ER11). The extraction this replaced --
    `body.split('class="grp done"')[1].split("</div>")[0]` -- cut the card at
    its first `</div>`, which since an item's `<li>` nests a
    `<div class="ttl">` now falls *inside* the first row.
    """
    return split_div_block(document, f'<div class="grp {css_class}">')[1]


def _names(markup: str) -> list[str]:
    """The stage names `markup` prints as items, in document order."""
    return re.findall(r'<span class="nm">(.*?)</span>', markup)


def _kickers(markup: str) -> list[str]:
    """The parent kickers `markup` prints, in document order."""
    return re.findall(r'<span class="top">(.*?)</span>', markup)


def _percentages(markup: str) -> list[str]:
    """The per-item percentages `markup` prints, in document order."""
    return re.findall(r'<span class="pc">(.*?)</span>', markup)


#: The two real stage payloads APRAS-114 committed, keyed by milestone title.
STAGE_FIXTURE: dict[str, dict] = json.loads(
    (
        Path(__file__).resolve().parent / "data" / "obras_stage_detail_fixture.json"
    ).read_text(encoding="utf-8")
)

#: The comma-rich real stage, used wherever a case needs a payload that is not
#: hand-written: its `pct` is 49.5588, which `_pct` renders `50%`.
DEMOLITIONS_PAYLOAD = STAGE_FIXTURE["Demolições — Térreo e Superior"]


def _real_payload(**overrides: object) -> dict:
    """The real Demolições payload with `overrides` applied.

    Cases override `pct` and `start` only; `leaves` stays as the contractor
    wrote it, so nothing here can pass against a payload shape the producer
    does not emit.
    """
    return dict(DEMOLITIONS_PAYLOAD) | overrides


def _leaf_payload(pct: float, start: str) -> dict:
    """A minimal one-leaf payload, for cases that must control every string in
    it -- the `description` guard asserts tokens are absent from the *page*, so
    a fixture leaf name could only muddy the claim."""
    return {
        "pct": pct,
        "start": start,
        "leaves": [
            {"name": "ETAPA UNICA", "pct": pct, "start": start, "finish": start}
        ],
    }


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

    # The masthead links the acting tenant's own logo route, never the stored
    # URL and never another condominium's (APRAS-105 §E).
    assert f'src="{public_tenant_logo_url(tenant_b.slug)}"' in body
    assert "proprio.example" not in body
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
    """Rewritten for APRAS-113, not patched: the old body asserted `<li>` counts
    and sliced each card with `split("</div>")[0]`, and both of those describe
    the pre-113 markup rather than the selection this case is about.

    The selection itself is unchanged in two of the three cards and only
    *relaxed* in the third: three most-recent DONE, every IN_PROGRESS, and --
    since `_select_milestones` lost its `[:3]` -- every NEXT_STEPS row, of which
    the card still renders three, now through the 3-slot cap. These milestones
    carry no `detail_json`, which is every production row today, so the next
    card's three rows arrive as plain items and the remaining two as the
    remainder line.
    """
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

    assert _names(_card(body, "done")) == ["Feito 4", "Feito 3", "Feito 2"]
    assert _names(_card(body, "doing")) == ["Andando 0", "Andando 1"]
    nxt = _card(body, "next")
    assert _names(nxt) == ["Futuro 0", "Futuro 1", "Futuro 2"]
    assert '<p class="rest">e mais 2 frentes sem data prevista</p>' in nxt


def test_next_steps_selection_orders_by_display_order_then_title(session: Session):
    """The sort key is `(display_order, title)` and never `display_order` alone.

    `ConstructionProject.milestones` is ordered by `display_order` only, so rows
    sharing one value fall back to whatever the database returns -- not stable
    across plans or after an update. APRAS-114 hit exactly this with bulletins.
    """
    rows = [
        ProjectMilestone(
            title=title,
            status=MilestoneStatus.NEXT_STEPS,
            display_order=order,
        )
        for title, order in (("Zebra", 1), ("Alfa", 1), ("Meio", 0))
    ]

    selected = report._select_milestones(rows, MilestoneStatus.NEXT_STEPS)

    assert [m.title for m in selected] == ["Meio", "Alfa", "Zebra"]


def test_next_steps_selection_is_no_longer_capped_at_three(session: Session):
    """The cap moved from the selector to the card's 3 *slots*, so the selector
    must hand every row over -- the remainder line's `N` counts rows it never
    saw otherwise."""
    rows = [
        ProjectMilestone(
            title=f"Frente {index}",
            status=MilestoneStatus.NEXT_STEPS,
            display_order=index,
        )
        for index in range(7)
    ]

    assert len(report._select_milestones(rows, MilestoneStatus.NEXT_STEPS)) == 7


# ---------------------------------------------------------------------------
# §4b -- the card bodies APRAS-113 renders (the approved mock)
# ---------------------------------------------------------------------------


def test_each_done_and_doing_item_prints_its_own_percentage(
    client: TestClient, session: Session
):
    """ER1: the mock's Portarias figures, 100% / 63% / 50%.

    `50%` is the real Demolições payload's own 49.5588 through `_pct`, which is
    what makes this case able to fail on a truncating formatter (49%) and on a
    percentage read from `project.physical_progress_pct` (which is 22 here).
    """
    project = _project(
        session, title="Obra com percentuais", physical_progress_pct=22.0
    )
    _milestone(
        session,
        project,
        title="Mobilização de Canteiro e Instalações Provisórias",
        status=MilestoneStatus.DONE,
        completion_date=date(2026, 1, 1),
        display_order=0,
        detail_json=_real_payload(pct=100.0),
    )
    _milestone(
        session,
        project,
        title="Serviços Preliminares",
        status=MilestoneStatus.IN_PROGRESS,
        display_order=0,
        detail_json=_real_payload(pct=63.0),
    )
    _milestone(
        session,
        project,
        title="Fundações · Locação de Estacas",
        status=MilestoneStatus.IN_PROGRESS,
        display_order=1,
        detail_json=_real_payload(),
    )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert _percentages(_card(body, "done")) == ["100%"]
    doing = _card(body, "doing")
    assert _percentages(doing) == ["63%", "50%"]
    assert _names(doing) == ["Serviços Preliminares", "Locação de Estacas"]
    assert _kickers(doing) == ["Fundações"]
    # The percentage is a *sibling* of the title block, not a child of it: `.pc`
    # is the flex row's right-hand cell, so nesting it inside `.ttl` would move
    # the figure under the name.
    assert '</div><span class="pc">50%</span></li>' in doing


def test_a_milestone_without_a_payload_prints_no_percentage_element(
    client: TestClient, session: Session
):
    """ER1b/ER9: no detail means no `pc` element at all -- never `0%`, which
    would state a measurement nobody made."""
    project = _project(session, title="Obra sem payloads")
    _milestone(
        session,
        project,
        title="Mobilização de Canteiro",
        status=MilestoneStatus.DONE,
        completion_date=date(2026, 1, 1),
        display_order=0,
        detail_json=None,
    )
    _milestone(
        session,
        project,
        title="Fundações · Locação de Estacas",
        status=MilestoneStatus.IN_PROGRESS,
        display_order=0,
        detail_json=None,
    )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    done = _card(body, "done")
    doing = _card(body, "doing")
    assert _names(done) == ["Mobilização de Canteiro"]
    assert _names(doing) == ["Locação de Estacas"]
    assert _kickers(doing) == ["Fundações"]
    assert 'class="pc"' not in done
    assert 'class="pc"' not in doing
    assert "0%" not in _text_of(done)
    assert "0%" not in _text_of(doing)


def test_an_empty_milestone_group_renders_an_em_dash(
    client: TestClient, session: Session
):
    _project(session, title="Obra sem marcos")
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert body.count('<p class="none">—</p>') == 3


def _next_steps(
    session: Session,
    project,
    sizes: tuple[int, ...],
    *,
    undated: int = 0,
    parent: str | None = "Fundações",
    base: date = date(2026, 9, 25),
) -> None:
    """Seed NEXT_STEPS rows: `sizes[k]` of them starting on `base + k` days.

    `undated` further rows carry `detail_json=None`, which is what every
    production row carries today. `display_order` runs with the seeding order,
    so a group's items are already in `(display_order, title)`.
    """
    order = 0
    for index, size in enumerate(sizes):
        start = base + timedelta(days=index)
        for slot in range(size):
            kicker = f"{parent} · " if parent else ""
            _milestone(
                session,
                project,
                title=f"{kicker}Frente {index}-{slot}",
                status=MilestoneStatus.NEXT_STEPS,
                display_order=order,
                detail_json=_leaf_payload(0.0, start.isoformat()),
            )
            order += 1
    for slot in range(undated):
        _milestone(
            session,
            project,
            title=f"Sem data · Frente {slot}",
            status=MilestoneStatus.NEXT_STEPS,
            display_order=order,
            detail_json=None,
        )
        order += 1


def test_next_steps_are_grouped_by_start_date_with_a_count_and_a_kicker(
    client: TestClient, session: Session
):
    """ER2: the mock's 5/4/1 split, its date heads, counts, kicker and flow.

    The group whose items share a parent hoists it into one `dsub`; the group
    whose parents differ emits none. The item with the *lowest* `display_order`
    sits in the *latest* group, so ordering the groups by `display_order`
    reverses the rendered order and fails here.
    """
    project = _project(session, title="Obra agrupada")
    first = date(2026, 9, 25)
    second = date(2026, 10, 20)
    third = date(2027, 1, 6)
    shared = [
        "Entrada de Caminhões",
        "Saida de Veiculos e Caminhões",
        "Entrada de Veiculos e Pórtico de Entrada",
        "Totem",
        "Pergolado",
    ]
    for index, name in enumerate(shared, start=10):
        _milestone(
            session,
            project,
            title=f"Fundações · {name}",
            status=MilestoneStatus.NEXT_STEPS,
            display_order=index,
            detail_json=_leaf_payload(0.0, first.isoformat()),
        )
    mixed = [
        ("Estruturas Metalicas", "Cobertura de Entrada de Caminhões"),
        ("Estruturas Metalicas", "Cobertura de Saida de Veiculos"),
        ("Fechamentos", "Cobertura de Entrada de Visitantes"),
        ("Coberturas", "Pergolado Metalico"),
    ]
    for index, (top, name) in enumerate(mixed, start=20):
        _milestone(
            session,
            project,
            title=f"{top} · {name}",
            status=MilestoneStatus.NEXT_STEPS,
            display_order=index,
            detail_json=_leaf_payload(0.0, second.isoformat()),
        )
    _milestone(
        session,
        project,
        title="Totem Final",
        status=MilestoneStatus.NEXT_STEPS,
        display_order=0,
        detail_json=_leaf_payload(0.0, third.isoformat()),
    )
    admin = _user(session)

    card = _card(client.get(REPORT_URL, headers=_auth(admin)).text, "next")

    assert card.count('<div class="dgrp">') == 3
    assert re.findall(r"a partir de <b>(.*?)</b>", card) == [
        "25/09/2026",
        "20/10/2026",
        "06/01/2027",
    ]
    assert re.findall(r'<span class="cnt">(.*?)</span>', card) == ["5", "4", "1"]
    # One hoisted kicker, for the one group whose parents agree.
    assert card.count('class="dsub"') == 1
    assert '<div class="dsub">Fundações</div>' in card
    flows = re.findall(r'<p class="flow">(.*?)</p>', card)
    assert flows[0] == ", ".join(shared)
    assert flows[1] == ", ".join(name for _, name in mixed)
    assert flows[2] == "Totem Final"
    # A grouped item is a name in the inline list, never its own bullet.
    assert "<li>" not in card
    assert 'class="rest"' not in card


def test_the_remainder_line_counts_the_omitted_rows_and_their_dates(
    client: TestClient, session: Session
):
    """ER3, the mock's Portarias shape: 23 rows over 10 dates, 3 groups shown
    (5+4+1), so 13 names and 7 dates are missing."""
    project = _project(session, title="Obra Portarias")
    _next_steps(session, project, (5, 4, 1, 2, 2, 2, 2, 2, 2, 1))
    admin = _user(session)

    card = _card(client.get(REPORT_URL, headers=_auth(admin)).text, "next")

    assert card.endswith('<p class="rest">e mais 13 frentes em 7 datas</p></div>')


def test_the_all_null_card_says_sem_data_prevista_rather_than_em_zero_datas(
    client: TestClient, session: Session
):
    """ER9: 23 rows with no payload -- today's live state. Three render as plain
    items and the line must not claim "em 0 datas", which would be false."""
    project = _project(session, title="Obra sem payload")
    _next_steps(session, project, (), undated=23)
    admin = _user(session)

    card = _card(client.get(REPORT_URL, headers=_auth(admin)).text, "next")

    assert len(_names(card)) == 3
    assert _names(card) == ["Frente 0", "Frente 1", "Frente 2"]
    assert _kickers(card) == ["Sem data"] * 3
    assert 'class="dgrp"' not in card
    assert card.endswith(
        '<p class="rest">e mais 20 frentes sem data prevista</p></div>'
    )
    assert "em 0 datas" not in card


def test_no_remainder_line_when_the_groups_cover_every_row(
    client: TestClient, session: Session
):
    """ER3: `N == 0` emits nothing at all, not "e mais 0 frentes"."""
    project = _project(session, title="Obra completa em três grupos")
    _next_steps(session, project, (5, 4, 1))
    admin = _user(session)

    card = _card(client.get(REPORT_URL, headers=_auth(admin)).text, "next")

    assert card.count('<div class="dgrp">') == 3
    assert 'class="rest"' not in card


def test_the_remainder_counts_undated_rows_in_n_but_not_in_m(
    client: TestClient, session: Session
):
    """ER3, the mixed case: 5 date groups (5, 4, 1, 4, 3) plus 2 undated rows.

    Three groups consume the three slots, so two groups (7 rows) and both
    undated rows are omitted: `N = 9` names missing, `M = 2` dates missing. The
    two figures are deliberately not counts of the same set -- `N` counts every
    unprinted row, `M` only the distinct dates among the *datable* ones.
    """
    project = _project(session, title="Obra mista")
    _next_steps(session, project, (5, 4, 1, 4, 3), undated=2)
    admin = _user(session)

    card = _card(client.get(REPORT_URL, headers=_auth(admin)).text, "next")

    assert card.count('<div class="dgrp">') == 3
    # No slot is left, so neither undated row is rendered as an item.
    assert "<li>" not in card
    assert card.endswith('<p class="rest">e mais 9 frentes em 2 datas</p></div>')


def test_the_three_cards_are_distinguished_and_only_doing_carries_a_border(
    client: TestClient, session: Session
):
    """ER4: the distinction, in the document and in the stylesheet.

    Asserting `.grp.doing` declares `border-color` is not enough on its own --
    adding the same declaration to the other two cards would keep it green while
    destroying the distinction -- so the absence on `.done` and `.next` is
    asserted beside it.
    """
    project = _project(session, title="Obra distinguida")
    _milestone(
        session,
        project,
        title="Serviços Preliminares",
        status=MilestoneStatus.IN_PROGRESS,
        display_order=0,
    )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert body.count('class="grp doing"') == 1
    classes = re.findall(r'<div class="(grp [a-z]+)">', split_groups_block(body)[1])
    assert classes == ["grp done", "grp doing", "grp next"]
    assert len(set(classes)) == 3

    rules = parse_css(report.CSS_BODY).rules
    declaring = {
        rule.selector for rule in rules if "border-color:" in rule.declarations
    }
    assert ".grp.doing" in declaring
    assert declaring.isdisjoint({".grp.done", ".grp.next"})


def _past_curve(final_pct: float) -> list[dict[str, object]]:
    """A planned curve whose every month is elapsed, ending on `final_pct`.

    `planned_to_date` reads the clock, so a page-level pin on the bar has to be
    date-independent: with all three months already past, the last one stays
    the last one as time advances and the planned figure is fixed from now on.
    """
    return [
        {"month": "2020-01", "pct": 4.0},
        {"month": "2020-02", "pct": 8.0},
        {"month": "2020-03", "pct": final_pct},
    ]


def test_the_page_emits_the_pinned_bar_markup_byte_for_byte(
    client: TestClient, session: Session
):
    """ER5: the far pair (13.2/22.0) and the close pair (20.0/22.0), verbatim.

    `test_the_two_value_branch_is_pinned_byte_for_byte` pins `_one_bar` itself
    and must not move a byte; this case checks the same two strings through the
    real page, because APRAS-113 edits the module that renders it.
    """
    for title, planned in (("Obra Longe", 13.2), ("Obra Perto", 20.0)):
        project = _project(
            session,
            title=title,
            physical_progress_pct=22.0,
            planned_progress_json=_past_curve(planned),
        )
        _milestone(
            session,
            project,
            title="Fundações · Locação de Estacas",
            status=MilestoneStatus.IN_PROGRESS,
            display_order=0,
            detail_json=_real_payload(),
        )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    # Containment alone would survive the bar being *wrapped* in new markup, so
    # each pin is asserted with the bytes on both sides of it: the `.pv` label
    # it follows and the note it precedes.
    for key in ((13.2, 22.0), (20.0, 22.0)):
        assert _TWO_VALUE_MARKUP[key] in body
        assert (
            "</small>" + _TWO_VALUE_MARKUP[key] + '<div class="note">Previsto conforme'
        ) in body


def test_a_project_with_no_milestones_renders_three_empty_cards(
    client: TestClient, session: Session
):
    """ER6: three cards, each an em dash, and no list machinery anywhere."""
    _project(session, title="Obra vazia")
    admin = _user(session)

    response = client.get(REPORT_URL, headers=_auth(admin))

    assert response.status_code == 200
    block = split_groups_block(response.text)[1]
    for css_class in ("done", "doing", "next"):
        assert _card(response.text, css_class).count('<p class="none">—</p>') == 1
    assert "<ul" not in block
    assert "dgrp" not in block
    assert 'class="rest"' not in block


def test_a_project_whose_every_milestone_is_complete_renders_only_the_done_card(
    client: TestClient, session: Session
):
    """ER6/ER7: three DONE items with their percentages, two em dashes, and no
    `description` token in the page."""
    project = _project(session, title="Obra concluída")
    for index in range(3):
        _milestone(
            session,
            project,
            title=f"Fundações · Frente {index}",
            status=MilestoneStatus.DONE,
            completion_date=date(2026, 1, 1) + timedelta(days=index),
            display_order=index,
            description="Piso, Parede, Teto",
            # `_leaf_payload` and not `_real_payload`, for the reason that
            # helper's docstring already gives: this case asserts the three
            # tokens are absent from the **page**, and since APRAS-115 the
            # stage-detail section legitimately prints the payload's leaf
            # names title-cased -- the real Demolições leaves contain
            # "PISO" and "PAREDES", so the claim would be ambiguous rather
            # than false.
            detail_json=_leaf_payload(100.0, "2026-01-01"),
        )
    admin = _user(session)

    response = client.get(REPORT_URL, headers=_auth(admin))

    assert response.status_code == 200
    body = response.text
    done = _card(body, "done")
    assert _names(done) == ["Frente 2", "Frente 1", "Frente 0"]
    assert _percentages(done) == ["100%"] * 3
    assert _card(body, "doing").count('<p class="none">—</p>') == 1
    assert _card(body, "next").count('<p class="none">—</p>') == 1
    for token in ("Piso", "Parede", "Teto"):
        assert token not in body


def test_the_description_column_is_never_split_into_items(
    client: TestClient, session: Session
):
    """ER7: the inline list and the count come from the payload, never from
    `description.split(", ")`.

    48 of the 152 real serviço names carry a comma, so that split is wrong at
    the source. If anyone reintroduces it the badge reads `5` instead of `1` and
    the five tokens reach the document.
    """
    tokens = ("Piso", "Parede", "Teto", "Rodapé", "Soleira")
    description = ", ".join(tokens)
    project = _project(session, title="Obra com descrição")
    _milestone(
        session,
        project,
        title="Acabamentos · Revestimento Interno",
        status=MilestoneStatus.NEXT_STEPS,
        display_order=0,
        description=description,
        detail_json=_leaf_payload(0.0, "2026-10-20"),
    )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text
    card = _card(body, "next")

    assert re.findall(r'<span class="cnt">(.*?)</span>', card) == ["1"]
    assert re.findall(r'<p class="flow">(.*?)</p>', card) == ["Revestimento Interno"]
    assert description not in body
    for token in tokens:
        assert token not in body


# ---------------------------------------------------------------------------
# §4c -- the title split (ER8) and the palette contract
# ---------------------------------------------------------------------------


def test_the_title_split_names_its_uncommitted_producer():
    """ER8: the coupling is discoverable from the renderer.

    `ProjectMilestone` has no parent column; the parent reaches this repository
    only inside `title`, in a format an operator script that is deliberately
    never committed here defines. Nothing in this repository can explain why the
    separator matters, so the helper has to name the script.
    """
    source = inspect.getsource(report._split_stage_title)

    assert "sync_obras_from_drive.py" in source


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Totem", (None, "Totem")),
        ("Fundações · Totem", ("Fundações", "Totem")),
        # A shape the producer does not emit: `top` is exactly one level and the
        # only separator it substitutes inside a name is `"- "` -> `" — "`. Kept
        # because `maxsplit=1` has to degrade safely -- an unpack would raise
        # and a plain `split` would silently drop `Bloco A`.
        ("Fundações · Bloco A · Totem", ("Fundações", "Bloco A · Totem")),
        ("", (None, "")),
        (None, (None, "")),
    ],
)
def test_the_title_split_takes_the_first_separator_only(title, expected):
    assert report._split_stage_title(title) == expected


def test_the_three_title_shapes_render_kicker_and_name(
    client: TestClient, session: Session
):
    """ER8, through the document: no separator means **no** kicker element, not
    an empty one."""
    project = _project(session, title="Obra com títulos")
    for index, title in enumerate(
        ("Totem", "Fundações · Totem", "Fundações · Bloco A · Totem")
    ):
        _milestone(
            session,
            project,
            title=title,
            status=MilestoneStatus.NEXT_STEPS,
            display_order=index,
            detail_json=None,
        )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text
    card = _card(body, "next")
    items = re.findall(r"<li>.*?</li>", card)

    assert len(items) == 3
    assert 'class="nm">Totem<' in items[0]
    assert 'class="top"' not in items[0]
    assert _kickers(items[1]) == ["Fundações"]
    assert _names(items[1]) == ["Totem"]
    assert _kickers(items[2]) == ["Fundações"]
    assert _names(items[2]) == ["Bloco A · Totem"]
    # Never an empty kicker, anywhere on the page.
    assert 'class="top"></span>' not in body
    assert 'class="top"> <' not in body


#: The class tokens APRAS-113 introduced into `CSS_BODY`. A rule is "new" when
#: its selector mentions one of them, which is how the scoping assertion below
#: can catch an *unscoped* `.pc { … }` -- selecting the new rules by their
#: `.grp ` prefix instead would make "every new selector starts with `.grp`"
#: true by construction, which is a vacuous test.
_NEW_CARD_CLASSES = frozenset(
    {"fr", "ttl", "top", "nm", "pc", "dgrp", "dhead", "cnt", "dsub", "flow", "rest"}
)

#: Every selector APRAS-113 adds, as an exact ordered list: an added rule that
#: nobody reviewed fails here, and so does a dropped one.
_NEW_CARD_SELECTORS = (
    ".grp ul.fr",
    ".grp ul.fr li",
    ".grp ul.fr li:last-child",
    ".grp .ttl",
    ".grp .top",
    ".grp .nm",
    ".grp .pc",
    ".grp .dgrp",
    ".grp .dgrp:last-of-type",
    ".grp .dhead",
    ".grp .dhead b",
    ".grp .dhead .cnt",
    ".grp .dsub",
    ".grp .flow",
    ".grp .rest",
)


def _new_card_rules():
    """The `CSS_BODY` rules whose selector mentions a class APRAS-113 added.

    `details`-prefixed selectors are excluded, and that exclusion is narrow on
    purpose. APRAS-115's stage-detail section reuses three of these class tokens
    -- `.ttl`, `.top`, `.nm` -- under its own `details.ph` scope, which is
    exactly the scoping this pin asks for, just not under `.grp`. Nothing is
    lost: an *unscoped* `.nm { … }` still carries no `details` prefix and still
    fails the case below, and every section rule is pinned as an exact ordered
    list by `tests/test_project_report_stage_detail_section.py`.
    """
    sheet = parse_css(report.CSS_BODY)
    return [
        rule
        for rule in sheet.rules + sheet.nested_rules
        if not rule.selector.startswith("details")
        and _NEW_CARD_CLASSES
        & {
            token.lstrip(".")
            for token in re.findall(r"\.[A-Za-z][\w-]*", rule.selector)
        }
    ]


def test_the_new_card_rules_are_exactly_the_reviewed_scoped_set():
    """Decision 8, made mechanical: every new selector is scoped under `.grp`.

    The mock leaves `.ttl`, `.nm`, `.top` and `.pc` unscoped and its
    `<details class="all">` subtree reuses two of them, so shipping them
    unscoped would publish a styling hook for APRAS-115 -- which this task's
    Out of Scope forbids.
    """
    selectors = [rule.selector for rule in _new_card_rules()]

    assert selectors == list(_NEW_CARD_SELECTORS)
    for selector in selectors:
        assert selector.startswith(".grp ")


def test_the_new_card_rules_carry_no_colour_literal_and_only_known_variables():
    """The palette contract (ER13), in the order that makes it non-vacuous.

    (a) is checked first and is what gives (b) its force: "every `var()` names a
    known role" passes *vacuously* over `rgba(221,209,182,.45)`, the literal the
    mock hard-codes for its row separator, because a literal is not a `var()`.
    (c) is the collision the mock cannot express: its `--brand` equals both
    production `--brand` and `--brand-text`, and `("brand", "card")` is absent
    from `REPORT_TEXT_PAIRS` and already recorded below 3:1, so a text use of
    `var(--brand)` on a card ships a real contrast regression with a green
    suite.
    """
    rules = _new_card_rules()

    # Anti-vacuity: an empty rule list satisfies every loop below.
    assert len(rules) == len(_NEW_CARD_SELECTORS)

    for rule in rules:
        declarations = rule.declarations
        for literal in ("#", "rgb(", "rgba(", "hsl("):
            assert literal not in declarations, f"{rule.selector}: {declarations}"
        for name in re.findall(r"var\(--([\w-]+)\)", declarations):
            assert name in report.REPORT_ROLE_SOURCES, f"{rule.selector}: --{name}"
        for declaration in declarations.split(";"):
            prop, _, value = declaration.partition(":")
            if prop.strip() == "color":
                assert value.strip() != "var(--brand)", rule.selector


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
    assert '<div class="ends"><span>Início</span><span>Conclusão</span></div>' in markup


def test_no_curve_puts_the_plan_tag_in_the_band_below_the_track():
    """APRAS-103: the two labels used to overprint each other.

    The plan tag is a constant ``—`` pinned at ``left:0%``; the realized tag
    starts at ``left:0%`` too, so above the track they collide. The no-curve
    branch now borrows the two-value branch's own vocabulary -- ``one close``
    on the wrapper, ``tag plan below`` on the plan tag -- which the stylesheet
    already supports.
    """
    markup = _bar(None, 0.0)

    assert markup.startswith('<div class="one close">')
    assert (
        '<div class="tag plan below" style="left:0%">'
        "<span>previsto</span><b>—</b></div>" in markup
    )
    assert '<div class="tag plan" style="left:0%">' not in markup


@pytest.mark.parametrize("realized", [0.0, 37.0, 80.0])
def test_no_curve_separates_the_labels_at_every_realized_value(realized):
    """There is no threshold here, on purpose.

    A conditional would key the layout off ``realized`` alone -- a quantity
    that does not describe the plan tag at all -- and would silently change
    one project's report structure between two consecutive monthly issues of
    a document the síndico compares side by side.
    """
    markup = _bar(None, realized)

    assert 'class="one close"' in markup
    assert 'class="tag plan below" style="left:0%"' in markup
    assert f'class="tag real" style="left:{realized:.0f}%"' in markup


#: The two-value branch, byte for byte, in the three shapes that between them
#: exercise every conditional it has: a pair far from ``CLOSE_LABEL_GAP``
#: (gap 8.8, both tags above the track), a pair inside it (gap 2.0, ``close``
#: wrapper and ``below`` plan tag) and a behind-schedule pair (gap 23.0,
#: ``seg b behind`` plus the ``mark``). Hand-tuned against the approved mock;
#: APRAS-103 must not move a single byte of it.
_TWO_VALUE_MARKUP = {
    (13.2, 22.0): (
        '<div class="one">'
        '<div class="tag plan" style="left:13%"><span>previsto</span>'
        "<b>13%</b></div>"
        '<div class="tag real" style="left:22%"><span>realizado</span>'
        "<b>22%</b></div>"
        '<div class="track"><div class="seg a" style="width:13%"></div>'
        '<div class="seg b" style="left:13%;width:9%"></div>'
        '<div class="mark" style="left:13%"></div></div>'
        '<div class="ends"><span>Início</span><span>Conclusão</span></div></div>'
    ),
    (20.0, 22.0): (
        '<div class="one close">'
        '<div class="tag plan below" style="left:20%"><span>previsto</span>'
        "<b>20%</b></div>"
        '<div class="tag real" style="left:22%"><span>realizado</span>'
        "<b>22%</b></div>"
        '<div class="track"><div class="seg a" style="width:20%"></div>'
        '<div class="seg b" style="left:20%;width:2%"></div>'
        '<div class="mark" style="left:20%"></div></div>'
        '<div class="ends"><span>Início</span><span>Conclusão</span></div></div>'
    ),
    (45.0, 22.0): (
        '<div class="one">'
        '<div class="tag plan" style="left:45%"><span>previsto</span>'
        "<b>45%</b></div>"
        '<div class="tag real" style="left:22%"><span>realizado</span>'
        "<b>22%</b></div>"
        '<div class="track"><div class="seg a" style="width:22%"></div>'
        '<div class="seg b behind" style="left:22%;width:23%"></div>'
        '<div class="mark" style="left:45%"></div></div>'
        '<div class="ends"><span>Início</span><span>Conclusão</span></div></div>'
    ),
}


@pytest.mark.parametrize(("planned", "realized"), sorted(_TWO_VALUE_MARKUP))
def test_the_two_value_branch_is_pinned_byte_for_byte(planned, realized):
    assert _bar(planned, realized) == _TWO_VALUE_MARKUP[(planned, realized)]


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

    assert f'src="{public_tenant_logo_url(tenant.slug)}"' in body
    assert "cdn.example" not in body


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
        assert f'src="{public_tenant_logo_url(tenant.slug)}"' in (
            report.render_report_html(session, admin)
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


def test_the_flat_list_rules_reset_what_they_inherit_from_the_older_ones():
    """`.grp ul { padding-left:4mm }`, `.grp li { margin:1.2mm 0 }` and
    `.grp li::marker` all predate APRAS-113 and all still apply to the new rows.

    So the new rules have to both out-specify them -- `.grp ul.fr` (0,2,1) over
    `.grp ul` (0,1,1), `.grp ul.fr li` (0,2,2) over `.grp li` (0,1,1) -- and
    *reset* what they inherit. Without the reset every row keeps its bullet and
    a 4mm indent: a visible drift from the approved mock that the selector list
    and the palette contract both pass over.
    """
    declarations = {rule.selector: rule.declarations for rule in _new_card_rules()}

    assert "list-style:none;" in declarations[".grp ul.fr"]
    assert "padding:0;" in declarations[".grp ul.fr"]
    assert "margin:0;" in declarations[".grp ul.fr"]
    # `.grp li`'s vertical margin and the marker indent are replaced, not added
    # to: the row is a flex line with its own padding.
    assert "margin:0;" in declarations[".grp ul.fr li"]
    assert "padding:1.8mm 0;" in declarations[".grp ul.fr li"]


def test_the_card_applies_no_case_transform_to_either_half_of_the_title(
    client: TestClient, session: Session
):
    """ER12: `title` is printed verbatim, both halves of it.

    The sync tool already title-cased what it stored, and the Portuguese-aware
    title-caser lowercases before capitalising -- so running it here would flatten
    an all-caps suffix like `PCD`. Wiring one in is a defect, not a no-op. Leaf
    names are a different matter and belong to APRAS-115, which prints them.
    """
    project = _project(session, title="Obra com siglas")
    _milestone(
        session,
        project,
        title="Instalações Hidraulicas · Lavabo WC PCD",
        status=MilestoneStatus.IN_PROGRESS,
        display_order=0,
    )
    admin = _user(session)

    doing = _card(client.get(REPORT_URL, headers=_auth(admin)).text, "doing")

    assert _kickers(doing) == ["Instalações Hidraulicas"]
    assert _names(doing) == ["Lavabo WC PCD"]


# ---------------------------------------------------------------------------
# The hero's cover photo, served by a route of ours (APRAS-104 ER5)
# ---------------------------------------------------------------------------


@pytest.fixture(name="cover_storage")
def cover_storage_fixture(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """A real `LocalStorageProvider` rooted in `tmp_path`, on the seam
    `project_service` exposes: the rung under test is "does the provider own
    this value", and only a real provider answers it the production way."""
    provider = LocalStorageProvider(tmp_path / "uploads")
    monkeypatch.setattr(project_service_module, "_storage_provider", provider)
    return provider


def _store_cover(provider: LocalStorageProvider, name: str = "capa.png") -> str:
    target = provider.base_dir / "2026" / "09" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\x89PNG\r\n\x1a\ncapa")
    return f"/static/uploads/2026/09/{name}"


def test_the_hero_names_our_cover_route_absolutely_and_still_places_the_placeholder(
    client: TestClient, session: Session, cover_storage: LocalStorageProvider
):
    """ER5, deliberately **one** test over **one** rendered document.

    Both halves in the same document because a test that only checks the
    placeholder passes on a renderer that emits the placeholder
    unconditionally, and a test that only checks the `<img>` passes on one that
    never emits a placeholder at all. Here project A must get the `<img>` *and*
    project B must get the placeholder, out of a single render.

    The URL is asserted **absolute**, from `public_project_cover_url`, because
    `PublicObrasReportPage` injects this document into an `<iframe srcDoc>`
    whose relative URLs resolve against the frontend's origin -- a relative
    `src` fails silently, with no console error.

    And A's raw stored value is asserted **absent**: the Blob store is private,
    so emitting it would hand every reader a URL that cannot be fetched.
    """
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    stored = _store_cover(cover_storage)
    with_cover = _project(session, title="Com capa", cover_photo_url=stored)
    without_cover = _project(session, title="Sem capa", cover_photo_url=None)
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    expected = public_project_cover_url(tenant.slug, with_cover.id)
    assert expected.startswith("http")
    assert f'src="{expected}"' in body
    assert '<div class="noimg"></div>' in body
    assert f'src="{stored}"' not in body
    # The placeholder belongs to B and the `<img>` to A, not the other way
    # round: the hero order follows `created_at`, so A's fragment comes first.
    hero_a = body.index(f'src="{expected}"')
    hero_b = body.index('<div class="noimg"></div>')
    assert hero_a < hero_b
    assert str(without_cover.id) not in expected


def test_a_third_party_cover_value_is_rendered_verbatim(
    client: TestClient, session: Session, cover_storage: LocalStorageProvider
):
    """The second rung of §A.2, and a live write path rather than a tail:
    `backend/scripts/sync_obras_from_drive.py` writes values of this shape on
    every run, and a provider cannot read them back."""
    _project(
        session, title="Capa do Drive", cover_photo_url="https://cdn.example/capa.jpg"
    )
    admin = _user(session)

    body = client.get(REPORT_URL, headers=_auth(admin)).text

    assert 'src="https://cdn.example/capa.jpg"' in body


def test_a_missing_tenant_row_degrades_the_cover_to_the_placeholder(
    session: Session, cover_storage: LocalStorageProvider
):
    """`_page_html` takes `tenant: Tenant | None` and `_acting_tenant` can
    answer `None`; that function's policy is that a missing row degrades like a
    missing logo -- no `<img>`, never an exception. The cover follows it, and in
    particular never falls back to the unfetchable stored value.

    Unreachable in production, where both paths establish a tenant. Asserted
    because a developer writing `tenant.slug` against a `| None` parameter is
    the likely first draft.
    """
    project = _project(
        session, title="Com capa", cover_photo_url=_store_cover(cover_storage)
    )

    fragment = report._hero_html(project, 1, None)

    assert '<div class="noimg"></div>' in fragment
    assert "<img" not in fragment
    assert project.cover_photo_url not in fragment
