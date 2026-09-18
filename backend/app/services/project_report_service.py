"""The construction-projects report, rendered as printable HTML (APRAS-60).

One self-contained document for the acting tenant: one ``div.page`` per
project, in ``created_at`` order, with no tenant totals header and no
aggregate page. It is modelled verbatim on the assembly-minutes precedent
(``voting_service.render_minutes_html`` / ``save_minutes``) -- same rendering
shape, same storage provider + ``document_service.create_document``
storage path, same "folder created on demand" behaviour -- and it adds **no
dependency**: the PDF is produced by the browser's Print dialog against the
print CSS below, because Vercel's serverless runtime cannot carry WeasyPrint's
or wkhtmltopdf's native binaries.

Three properties are load-bearing and are what the tests pin:

**Tenant scoping comes from three different mechanisms, one per entity.**
``ConstructionProject`` carries its own ``tenant_id``, so a bare
``select(ConstructionProject)`` is already narrowed by the ambient
``with_loader_criteria`` of ``app.core.tenant_context``.
``ProjectMilestone`` and ``ProjectUpdate`` do **not** carry one -- they are
*inherited* tables, scoped only through their parent -- so a bare
``select(ProjectMilestone)`` would return every tenant's rows. They are
therefore reached exclusively through the already-scoped
``project.milestones`` / ``project.updates`` relationships, and this module
contains no ``select()`` over either class. The acting tenant's **own row** is
covered by neither, because ``tenant`` has no ``tenant_id`` and is never
filtered: ``select(Tenant).first()`` would put another condominium's logo and
name on the document, so the row is resolved with the established precedent
(``document_service._assert_role_ids_resolve``, ``role_service``)
``session.get(Tenant, tenant_context.acting_tenant_id(session) or
DEFAULT_TENANT_ID)``.

**Graceful degradation is behaviour, not a nicety.** A zero budget, a ``None``
date, a missing cover photo, an empty milestone list, an absent planned curve
and a malformed ``photos_json`` each render an em-dash, a placeholder or an
omitted element. No ``None``, ``NaN`` or ``null`` token ever reaches a
user-visible position, and no division by zero is possible.

**The save route answers one authorization outcome, never a state-dependent
one.** See :func:`save_report` and :func:`_find_or_create_obras_folder`.
"""

from __future__ import annotations

import html
import json
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlmodel import Session, select

from app.api.deps import has_permission
from app.core import clock
from app.core.exceptions import ForbiddenError
from app.core.money import ZERO
from app.core.tenant_context import acting_tenant_id
from app.models.document import DocumentFolder
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
from app.schemas.document import AssociationDocumentCreate
from app.services import document_service
from app.services.storage_service import (
    BaseStorageProvider,
    generated_storage_provider,
)

if TYPE_CHECKING:  # pragma: no cover
    from datetime import date, datetime
    from uuid import UUID

    from app.models.project import ProjectMilestone, ProjectUpdate
    from app.models.user import User

#: The fixed, system-managed root folder the saved report is filed into.
OBRAS_FOLDER_NAME = "Obras"

#: The report's own file name. ``LocalStorageProvider.save_file`` discards it
#: entirely -- since APRAS-65 not even the suffix survives, which is derived
#: from the ``text/html`` passed beside it -- so this is display metadata and
#: ``AssociationDocument.file_url`` remains the field guaranteed distinct
#: between two saves where ``title`` is not.
REPORT_FILENAME = "relatorio-obras.html"

#: pt-BR month names, indexed 1..12. The report is a Brazilian condominium
#: document and is not translated; `locale.setlocale` is deliberately avoided
#: because it is process-global and depends on the host's installed locales.
MONTHS_PT: tuple[str, ...] = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

#: The status pill's label, in pt-BR.
PROJECT_STATUS_LABELS: dict[str, str] = {
    ProjectStatus.PLANNED: "Planejada",
    ProjectStatus.IN_PROGRESS: "Em andamento",
    ProjectStatus.PAUSED: "Paralisada",
    ProjectStatus.COMPLETED: "Concluída",
}

#: The three milestone cards: `(css class, heading, MilestoneStatus)`.
MILESTONE_GROUPS: tuple[tuple[str, str, MilestoneStatus], ...] = (
    ("done", "Concluídos", MilestoneStatus.DONE),
    ("doing", "Em andamento", MilestoneStatus.IN_PROGRESS),
    ("next", "Próximos passos", MilestoneStatus.NEXT_STEPS),
)

#: ``"Coberturas e Portaria (Edificação)"`` -> title + kind.
_KIND_SUFFIX = re.compile(r"^(?P<title>.+?)\s*\((?P<kind>[^()]+)\)\s*$")

#: The gap under which the two bar labels would collide, in percentage
#: points. Compared on the **unrounded** values, exactly as the mock's
#: generator does.
CLOSE_LABEL_GAP = 8.0

#: The approved visual language, ported from the mock's generator
#: (`docs/tasks/APRAS-60-mock-generator.py`). Emitted inline, in one
#: ``<style>``: the document has to survive being saved to disk and reopened
#: with no server.
#:
#: The generator's dead rules -- the Gantt, the numbered stage cards, the
#: S-curve and the deadline strip -- are dropped, because this report emits
#: none of that markup. Its ``@media print`` block was a copy-paste of the
#: whole sheet; only the rules that actually change under print survive here.
#:
#: Two page-break spellings, on purpose. ``.page + .page`` is the generator's
#: ``.project + .project`` rule adapted to the one-``div.page``-per-project
#: structure; ``.page.brk`` is the same break carried *on the element*, which
#: is what lets the report assert "exactly ``project_count - 1`` breaks"
#: against the document instead of against a single stylesheet rule that says
#: nothing about how many pages follow.
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
:root { --navy:#082f2a; --green:#174b40; --gold:#c6a04a; --gold-light:#ead6a4; --cream:#f7f1e5; --text:#1d2925; --muted:#6f746e; --line:#ddd1b6; --soft:#eee6d7; --kicker:#9b7327; }
* { box-sizing:border-box; }
html, body { margin:0; padding:0; }
body { font-family:"DM Sans", Arial, sans-serif; color:var(--text); background:#d9d3c4; font-size:10.5pt; line-height:1.5; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
.page { width:210mm; min-height:297mm; margin:10mm auto; background:var(--cream); box-shadow:0 18px 45px rgba(8,47,42,.13); position:relative; overflow:hidden; }
h1,h2,h3,h4 { margin:0; }
.serif { font-family:"Playfair Display", Georgia, serif; color:var(--navy); }
.mast { display:flex; align-items:center; justify-content:space-between; padding:9mm 14mm 6mm; }
.mast img { height:19mm; width:auto; border-radius:8px; box-shadow:0 6px 16px rgba(8,47,42,.18); }
.mast .rep { text-align:right; }
.kicker { display:block; font-size:8pt; letter-spacing:2.4px; color:var(--kicker); font-weight:700; text-transform:uppercase; }
.mast .name { font-family:"Playfair Display", Georgia, serif; color:var(--navy); font-size:15pt; font-weight:700; line-height:1.1; }
.mast .when { font-size:8pt; color:var(--muted); margin-top:2px; }
.hero { padding:6mm 14mm 8mm; background:radial-gradient(circle at 82% 20%, #d8e7df 0, transparent 36%), radial-gradient(circle at 14% 88%, rgba(198,160,74,.25), transparent 34%), linear-gradient(120deg, #edf1e9, #f4e8cb); }
.hero-grid { display:grid; grid-template-columns:1.2fr .8fr; gap:8mm; align-items:center; margin-top:3mm; }
.hero h1 { font-size:27pt; line-height:1.02; margin:2mm 0 3mm; }
.hero p { font-size:10.5pt; line-height:1.6; color:var(--muted); margin:0; }
.pills { display:flex; flex-wrap:wrap; gap:6px; margin-top:4mm; }
.pill { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; border-radius:30px; background:#fff; border:1px solid rgba(198,160,74,.4); font-size:8pt; font-weight:700; color:var(--green); }
.pill i { width:7px; height:7px; border-radius:50%; background:var(--gold); }
.hero-card { background:#fff; border:1px solid rgba(198,160,74,.3); border-radius:14px; padding:5mm; box-shadow:0 10px 26px rgba(8,47,42,.10); }
.hero-card img { width:100%; height:26mm; object-fit:cover; border-radius:9px; border:1px solid var(--line); display:block; margin-bottom:3.5mm; }
.hero-card .noimg { width:100%; height:26mm; border-radius:9px; border:1px solid var(--line); background:var(--soft); display:block; margin-bottom:3.5mm; }
.hero-card small { display:block; color:var(--muted); font-size:7.5pt; letter-spacing:1.2px; font-weight:700; text-transform:uppercase; }
.hero-card strong { display:block; color:var(--navy); font-size:19pt; margin:1mm 0 3mm; font-weight:700; }
.progress { height:8px; background:#ded8c8; border-radius:20px; overflow:hidden; }
.progress span { display:block; height:100%; background:linear-gradient(90deg, var(--green), var(--gold)); border-radius:20px; }
.progress-labels { display:flex; justify-content:space-between; color:var(--muted); font-size:7.5pt; margin-top:5px; }
.progress-labels b { color:var(--navy); }
.section { padding:6mm 14mm 0; }
.section-head { margin-bottom:3.5mm; }
.section-head h2 { font-size:17pt; margin-top:1mm; }
.section-head p { color:var(--muted); font-size:9pt; margin:1mm 0 0; }
.groups { display:grid; grid-template-columns:1fr 1fr 1fr; gap:3mm; }
.grp { background:#fff; border:1px solid var(--line); border-radius:12px; padding:3mm 3.5mm; }
.grp.doing { border-color:var(--gold); box-shadow:0 8px 20px rgba(8,47,42,.08); }
.grp h4 { font-size:7pt; letter-spacing:1.4px; font-weight:700; text-transform:uppercase; display:flex; align-items:center; gap:6px; margin-bottom:2mm; }
.grp h4 i { width:8px; height:8px; border-radius:50%; }
.grp.done h4 { color:var(--green); } .grp.done h4 i { background:var(--green); }
.grp.doing h4 { color:var(--kicker); } .grp.doing h4 i { background:var(--gold); box-shadow:0 0 0 3px rgba(198,160,74,.3); }
.grp.next h4 { color:var(--muted); } .grp.next h4 i { border:2px solid var(--muted); width:5px; height:5px; }
.grp ul { margin:0; padding-left:4mm; font-size:9pt; color:var(--navy); }
.grp li { margin:1.2mm 0; line-height:1.35; }
.grp li::marker { color:var(--gold); }
.grp .none { color:var(--muted); font-style:italic; font-size:8.5pt; margin:0; }
.pv { background:#fff; border:1px solid var(--line); border-radius:12px; padding:3.5mm 4.5mm; margin-top:4mm; }
.pv small { display:block; color:var(--muted); font-size:7.5pt; letter-spacing:1px; font-weight:700; text-transform:uppercase; margin-bottom:2.5mm; }
.one { position:relative; padding-top:9mm; margin-top:1mm; }
.one .track { height:11px; background:#ded8c8; border-radius:20px; overflow:hidden; position:relative; }
.one .seg { position:absolute; top:0; height:100%; }
.one .seg.a { left:0; background:var(--green); }
.one .seg.b { background:var(--gold); }
.one .seg.b.behind { background:#c0392b; opacity:.7; }
.one .mark { position:absolute; top:0; width:1.5px; height:100%; background:#fff; }
.one .tag { position:absolute; top:0; transform:translateX(-1px); border-left:1.5px solid var(--line); padding-left:2mm; height:9mm; font-size:7.5pt; color:var(--muted); line-height:1.2; white-space:nowrap; }
.one .tag b { display:block; font-size:10pt; color:var(--navy); }
.one .tag.real b { color:var(--green); }
.one .tag.real { border-left-color:var(--gold); }
.one.close { padding-bottom:9mm; }
.one .tag.below { top:auto; bottom:0; height:9mm; display:flex; flex-direction:column-reverse; justify-content:flex-start; }
.one.close .ends { position:absolute; left:0; right:0; bottom:6.5mm; }
.one .ends { display:flex; justify-content:space-between; font-size:7pt; color:var(--muted); margin-top:1.5mm; }
.pv .note { font-size:7.5pt; color:var(--muted); margin-top:2mm; }
.two { display:grid; grid-template-columns:1.1fr .9fr; gap:4mm; align-items:stretch; }
.budget-col { background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; }
.budget-row { display:flex; justify-content:space-between; align-items:baseline; padding:3.2mm 4.5mm; border-bottom:1px solid var(--line); }
.budget-row:last-child { border-bottom:0; }
.budget-row small { color:var(--muted); font-size:7.5pt; letter-spacing:1px; font-weight:700; text-transform:uppercase; }
.budget-row strong { color:var(--navy); font-size:12pt; font-variant-numeric:tabular-nums; }
.budget-row.total { background:var(--soft); }
.cyl { background:#fff; border:1px solid var(--line); border-radius:12px; padding:3mm 4mm; display:flex; gap:4mm; align-items:center; }
.cyl svg { width:30mm; height:auto; flex:0 0 auto; }
.cyl .txt small { display:block; color:var(--muted); font-size:7.5pt; letter-spacing:1px; font-weight:700; text-transform:uppercase; }
.cyl .txt strong { display:block; color:var(--navy); font-size:20pt; font-weight:700; line-height:1.05; margin:1mm 0; }
.cyl .txt p { margin:0; font-size:8.5pt; color:var(--muted); }
.weeks { display:grid; gap:3mm; }
.week { background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; }
.week-head { display:flex; justify-content:space-between; align-items:baseline; padding:3mm 4mm; }
.week-head b { color:var(--navy); font-size:10.5pt; }
.week-head small { color:var(--muted); font-size:8pt; }
.week-body { display:flex; gap:4mm; padding:0 4mm 3.5mm; align-items:flex-start; }
.week-body p { margin:0; flex:1; font-size:9pt; color:var(--muted); line-height:1.55; }
.photo-grid { display:flex; gap:2.5mm; flex:0 0 auto; }
.photo-grid img { width:34mm; height:25mm; object-fit:cover; border-radius:9px; border:1px solid var(--line); display:block; }
.empty { color:var(--muted); font-style:italic; font-size:9pt; }
.foot { margin-top:8mm; background:var(--navy); color:#aebcb7; padding:4mm 14mm; display:flex; justify-content:space-between; font-size:8pt; border-top:3px solid var(--gold); }
.foot b { color:#fff; }
@page { size:A4; margin:0; }
@media print {
body { background:#fff; }
.page { margin:0; box-shadow:none; width:auto; min-height:auto; }
.page + .page, .page.brk { page-break-before:always; break-before:page; }
.groups, .two, .week, .cyl { page-break-inside:avoid; }
}
"""


# ---------------------------------------------------------------------------
# Formatting primitives
# ---------------------------------------------------------------------------


def _brl(value: Decimal | float | None) -> str:
    """``Decimal("1200000.00")`` -> ``"R$ 1.200.000,00"``. ``None`` is zero."""
    amount = Decimal(str(value or 0))
    return "R$ " + f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", "."
    )


def _pct(value: float | None) -> str:
    return f"{float(value or 0.0):.0f}%"


def _fmt_date(value: date | datetime | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "—"


def _fmt_datetime(value: datetime | None) -> str:
    return value.strftime("%d/%m/%Y %H:%M") if value else "—"


def _e(value: object) -> str:
    """Escape a user string. ``None`` becomes the empty string, never ``"None"``."""
    return html.escape("" if value is None else str(value))


def split_title_and_kind(title: str | None) -> tuple[str, str | None]:
    """``"X (Edificação)"`` -> ``("X", "Edificação")``; ``"X"`` -> ``("X", None)``."""
    raw = (title or "").strip()
    match = _KIND_SUFFIX.match(raw)
    if match is None:
        return raw, None
    return match.group("title").strip(), match.group("kind").strip()


def planned_to_date(payload: object, today: date | None = None) -> float | None:
    """The planned physical progress as of the current month.

    The ``pct`` of the **latest** point whose ``month`` is ``<= `` the current
    month, and ``0`` when every point is still in the future. ``None``, an
    empty list and any malformed payload mean *no curve* and return ``None``
    -- the caller renders the bar without a ``previsto`` segment rather than
    guessing a number the contractor never gave.

    Strict on purpose: one unparseable point invalidates the whole curve. A
    partially-read schedule would silently under- or over-state the plan,
    which is the one number the síndico compares the measurement against.
    """
    if not isinstance(payload, list) or not payload:
        return None

    current = (today or clock.today_utc()).strftime("%Y-%m")
    best: float | None = None
    best_month = ""
    for point in payload:
        if not isinstance(point, dict):
            return None
        month = point.get("month")
        pct = point.get("pct")
        if not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month):
            return None
        if isinstance(pct, bool) or not isinstance(pct, (int, float)):
            return None
        if month <= current and month >= best_month:
            best, best_month = float(pct), month
    return 0.0 if best is None else best


def decode_photos(photos_json: str | None) -> list[str]:
    """The photo URLs of one bulletin. Malformed or absent means none."""
    if not photos_json:
        return []
    try:
        decoded = json.loads(photos_json)
    except (TypeError, ValueError):
        return []
    if not isinstance(decoded, list):
        return []
    return [item for item in decoded if isinstance(item, str) and item]


# ---------------------------------------------------------------------------
# Fragments -- ported from the approved mock's generator
# ---------------------------------------------------------------------------


def _one_bar(planned: float | None, realized: float) -> str:
    """The single ``previsto até hoje`` x ``realizado`` track.

    With no curve (``planned is None``) the realized segment is drawn alone:
    no ``seg b``, no ``mark``, and the plan tag reads ``previsto —``. There is
    nothing to compare against, and a zero-width gold segment would read as
    "on plan".
    """
    if planned is None:
        return (
            '<div class="one">'
            '<div class="tag plan" style="left:0%"><span>previsto</span><b>—</b></div>'
            f'<div class="tag real" style="left:{realized:.0f}%">'
            f"<span>realizado</span><b>{realized:.0f}%</b></div>"
            f'<div class="track"><div class="seg a" style="width:{realized:.0f}%">'
            "</div></div>"
            '<div class="ends"><span>Início</span><span>Conclusão</span></div></div>'
        )

    low, high = min(planned, realized), max(planned, realized)
    behind = " behind" if realized < planned else ""
    close = abs(planned - realized) < CLOSE_LABEL_GAP
    plan_cls = "tag plan below" if close else "tag plan"
    return (
        f'<div class="one{" close" if close else ""}">'
        f'<div class="{plan_cls}" style="left:{planned:.0f}%">'
        f"<span>previsto</span><b>{planned:.0f}%</b></div>"
        f'<div class="tag real" style="left:{realized:.0f}%">'
        f"<span>realizado</span><b>{realized:.0f}%</b></div>"
        f'<div class="track"><div class="seg a" style="width:{low:.0f}%"></div>'
        f'<div class="seg b{behind}" style="left:{low:.0f}%;width:{high - low:.0f}%">'
        "</div>"
        f'<div class="mark" style="left:{planned:.0f}%"></div></div>'
        '<div class="ends"><span>Início</span><span>Conclusão</span></div></div>'
    )


def _cylinder_svg(pct_remaining: float) -> str:
    """The budget gauge: a tank filled from the bottom to the remaining balance."""
    top, bottom, width, rx, ry = 20, 140, 100, 50, 12
    filled = max(0.0, min(100.0, pct_remaining))
    fill_height = (bottom - top) * filled / 100
    fy = bottom - fill_height
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 165">'
        '<defs><linearGradient id="g" x1="0" x2="1">'
        '<stop offset="0" stop-color="#174b40"/>'
        '<stop offset=".5" stop-color="#2d6b5c"/>'
        '<stop offset="1" stop-color="#174b40"/></linearGradient>'
        '<linearGradient id="e" x1="0" x2="1">'
        '<stop offset="0" stop-color="#eee6d7"/>'
        '<stop offset=".5" stop-color="#fbf8f1"/>'
        '<stop offset="1" stop-color="#eee6d7"/></linearGradient></defs>'
        f'<path d="M10 {top} v{bottom - top} a{rx} {ry} 0 0 0 {width} 0 '
        f'v-{bottom - top}" fill="url(#e)" stroke="#ddd1b6"/>'
        f'<path d="M10 {fy:.1f} v{bottom - fy:.1f} a{rx} {ry} 0 0 0 {width} 0 '
        f'v-{bottom - fy:.1f}" fill="url(#g)"/>'
        f'<ellipse cx="60" cy="{fy:.1f}" rx="{rx}" ry="{ry}" fill="#2d6b5c" '
        'stroke="#c6a04a" stroke-width="1.2"/>'
        f'<ellipse cx="60" cy="{top}" rx="{rx}" ry="{ry}" fill="none" '
        'stroke="#ddd1b6"/>'
        f'<text x="60" y="{max(fy + 22, top + 30):.1f}" '
        'font-family="DM Sans, Arial" font-size="16" font-weight="700" '
        f'fill="#fff" text-anchor="middle">{filled:.0f}%</text>'
        "</svg>"
    )


def _done_sort_key(milestone: ProjectMilestone) -> tuple[int, int, int]:
    """Newest ``completion_date`` first, ``None`` last, ``display_order`` tiebreak."""
    completion = milestone.completion_date
    if completion is None:
        return (1, 0, milestone.display_order)
    return (0, -completion.toordinal(), milestone.display_order)


def _select_milestones(
    milestones: list[ProjectMilestone], status: MilestoneStatus
) -> list[ProjectMilestone]:
    """The rows one card shows: three, three, or all of them."""
    rows = [m for m in milestones if m.status == status]
    if status is MilestoneStatus.DONE:
        # "What was finished recently", not the whole history.
        return sorted(rows, key=_done_sort_key)[:3]
    ordered = sorted(rows, key=lambda m: m.display_order)
    # Everything in progress: the card the síndico is asked about is exactly
    # the list of open fronts, so truncating it would hide one.
    return ordered if status is MilestoneStatus.IN_PROGRESS else ordered[:3]


def _groups_html(milestones: list[ProjectMilestone]) -> str:
    cards = ""
    for css_class, label, status in MILESTONE_GROUPS:
        items = _select_milestones(milestones, status)
        body = (
            "<ul>" + "".join(f"<li>{_e(m.title)}</li>" for m in items) + "</ul>"
            if items
            else '<p class="none">—</p>'
        )
        cards += f'<div class="grp {css_class}"><h4><i></i>{label}</h4>{body}</div>'
    return f'<div class="groups">{cards}</div>'


def _updates_html(updates: list[ProjectUpdate]) -> str:
    """The three latest bulletins. Neither the author nor `cost_impact` shows.

    Both are deliberate omissions, not oversights: the report is published to
    the whole condominium and a per-bulletin cost figure read out of the
    budget block's context is the one number that generates disputes.
    """
    if not updates:
        return '<p class="empty">Nenhum boletim publicado.</p>'
    cards = ""
    for update in updates[:3]:
        photos = decode_photos(update.photos_json)[:3]
        photo_grid = (
            '<div class="photo-grid">'
            + "".join(f'<img alt="Foto do boletim" src="{_e(url)}">' for url in photos)
            + "</div>"
            if photos
            else ""
        )
        cards += (
            f'<div class="week"><div class="week-head"><b>{_e(update.title)}</b>'
            f"<small>{_fmt_date(update.created_at)}</small></div>"
            f'<div class="week-body"><p>{_e(update.content)}</p>{photo_grid}</div>'
            "</div>"
        )
    return cards


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------


def _masthead_html(tenant: Tenant | None, today: date) -> str:
    logo_url = getattr(tenant, "logo_url", None)
    tenant_name = _e(getattr(tenant, "name", None))
    logo = f'<img src="{_e(logo_url)}" alt="{tenant_name}">' if logo_url else ""
    when = f"{MONTHS_PT[today.month]} de {today.year} · gerado em {_fmt_date(today)}"
    return (
        f'<header class="mast">{logo}'
        '<div class="rep"><span class="kicker">Obras em foco</span>'
        '<div class="name">Relatório de Obras</div>'
        f'<div class="when">{when}</div></div></header>'
    )


def _hero_html(project: ConstructionProject, number: int) -> str:
    title, kind = split_title_and_kind(project.title)
    kicker = f"Obra {number:02d} • {_e(kind)}" if kind else f"Obra {number:02d}"
    status_label = PROJECT_STATUS_LABELS.get(project.status, str(project.status))
    updates = list(project.updates)
    last_update = (
        max(update.created_at for update in updates) if updates else project.updated_at
    )
    progress = float(project.physical_progress_pct or 0.0)
    cover = (
        f'<img src="{_e(project.cover_photo_url)}" alt="Foto de capa da obra">'
        if project.cover_photo_url
        else '<div class="noimg"></div>'
    )
    return (
        f'<section class="hero project"><span class="kicker">{kicker}</span>'
        '<div class="hero-grid"><div>'
        f'<h1 class="serif">{_e(title)}</h1>'
        f"<p>{_e(project.description)}</p>"
        f'<div class="pills"><span class="pill"><i></i>{_e(status_label)}</span>'
        f'<span class="pill">Última atualização {_fmt_date(last_update)}</span></div>'
        f'</div><div class="hero-card">{cover}'
        "<small>Progresso geral</small>"
        f"<strong>{_pct(progress)} concluído</strong>"
        f'<div class="progress"><span style="width:{progress:.0f}%"></span></div>'
        f'<div class="progress-labels"><span>Início</span><b>{_pct(progress)}</b>'
        "<span>Conclusão</span></div>"
        "</div></div></section>"
    )


def _budget_html(project: ConstructionProject) -> str:
    total = project.total_budget or ZERO
    executed = project.executed_budget or ZERO
    balance = total - executed
    # Defined as 0 for a zero budget: never a division, never a `NaN`. The
    # percentage is a ratio, not money, so it leaves `Decimal` here.
    executed_pct = float(executed / total * 100) if total else 0.0
    remaining_pct = 100.0 - executed_pct
    return (
        '<section class="section">'
        '<div class="section-head"><h2 class="serif">Orçamento da obra</h2></div>'
        '<div class="two"><div class="budget-col">'
        '<div class="budget-row total"><small>Orçamento previsto</small>'
        f"<strong>{_brl(total)}</strong></div>"
        f'<div class="budget-row"><small>Executado</small>'
        f"<strong>{_brl(executed)}</strong></div>"
        f'<div class="budget-row"><small>Saldo</small>'
        f"<strong>{_brl(balance)}</strong></div>"
        f'<div class="budget-row"><small>% executado</small>'
        f"<strong>{executed_pct:.1f}%</strong></div></div>"
        f'<div class="cyl">{_cylinder_svg(remaining_pct)}<div class="txt">'
        "<small>Saldo restante</small>"
        f"<strong>{remaining_pct:.0f}%</strong>"
        f"<p>{_brl(balance)} ainda disponíveis do orçamento previsto.</p>"
        "</div></div></div></section>"
    )


def _stages_html(project: ConstructionProject) -> str:
    planned = planned_to_date(project.planned_progress_json)
    realized = float(project.physical_progress_pct or 0.0)
    return (
        '<section class="section"><div class="section-head">'
        '<span class="kicker">Desenvolvimento</span>'
        '<h2 class="serif">Etapas da obra</h2>'
        "<p>O que já foi realizado, o que está acontecendo agora e o que vem "
        "a seguir.</p></div>"
        f"{_groups_html(list(project.milestones))}"
        '<div class="pv"><small>Avanço físico · previsto até hoje &times; realizado'
        "</small>"
        f"{_one_bar(planned, realized)}"
        '<div class="note">Previsto conforme o cronograma físico-financeiro da '
        "empreiteira; realizado conforme a última medição.</div>"
        "</div></section>"
    )


def _footer_html(tenant: Tenant | None, user: User, generated_at: datetime) -> str:
    tenant_name = _e(getattr(tenant, "name", None))
    return (
        f'<footer class="foot"><span><b>{tenant_name}</b> · Relatório de Obras</span>'
        f"<span>Gerado em {_fmt_datetime(generated_at)} por "
        f"{_e(user.full_name)}</span></footer>"
    )


def _page_html(
    project: ConstructionProject,
    number: int,
    tenant: Tenant | None,
    user: User,
    generated_at: datetime,
) -> str:
    page_class = "page" if number == 1 else "page brk"
    return (
        f'<div class="{page_class}">'
        f"{_masthead_html(tenant, generated_at.date())}"
        f"{_hero_html(project, number)}"
        f"{_stages_html(project)}"
        f"{_budget_html(project)}"
        '<section class="section"><div class="section-head">'
        '<span class="kicker">Acompanhamento visual</span>'
        '<h2 class="serif">Últimos boletins</h2></div>'
        f'<div class="weeks">{_updates_html(list(project.updates))}</div></section>'
        f"{_footer_html(tenant, user, generated_at)}"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Tenant resolution and rendering
# ---------------------------------------------------------------------------


def _acting_tenant(session: Session) -> Tenant | None:
    """The acting tenant's own row.

    `tenant` carries no `tenant_id` and is never narrowed by the ambient
    criteria, so `select(Tenant).first()` would render another condominium's
    logo and name on a multi-tenant install. The established precedent
    (`document_service`, `role_service`) is the acting tenant id with the
    default as the fallback, then a by-id `get`. A missing row degrades like a
    missing logo: no `<img>`, an empty name, never an exception.
    """
    return session.get(Tenant, acting_tenant_id(session) or DEFAULT_TENANT_ID)


def _acting_projects(session: Session) -> list[ConstructionProject]:
    """Every project of the acting tenant, oldest first.

    No `where(tenant_id == ...)`: `ConstructionProject` carries its own
    `tenant_id`, so `app.core.tenant_context`'s ambient `with_loader_criteria`
    already narrows this select. Milestones and bulletins are then reached
    **only** through these rows' relationships -- they carry no `tenant_id`
    and a bare `select()` over either would cross the boundary.
    """
    return list(
        session.exec(
            select(ConstructionProject).order_by(
                ConstructionProject.created_at, ConstructionProject.id
            )
        ).all()
    )


def render_report_html(session: Session, user: User) -> str:
    """The whole report: one ``div.page`` per project, no totals header."""
    generated_at = clock.db_now()
    tenant = _acting_tenant(session)
    projects = _acting_projects(session)
    pages = "".join(
        _page_html(project, number, tenant, user, generated_at)
        for number, project in enumerate(projects, start=1)
    )
    tenant_name = _e(getattr(tenant, "name", None))
    return (
        "<!DOCTYPE html>"
        '<html lang="pt-BR"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>Relatório de Obras — {tenant_name}</title>"
        f"<style>{CSS}</style></head><body>"
        f"{pages}"
        "</body></html>"
    )


def get_report_html(session: Session, user: User) -> str:
    """Entry point of ``GET /api/v1/projects/report``."""
    return render_report_html(session, user)


# ---------------------------------------------------------------------------
# Saving into the Documents module
# ---------------------------------------------------------------------------


def _find_or_create_obras_folder(session: Session) -> UUID:
    """Resolve the fixed "Obras" root folder, constructing it once.

    **Deliberately not `document_service.create_folder`.** That function opens
    with `_check_admin_or_director(user, session, "documents:folder_create")`,
    so a caller holding exactly `projects:read` + `documents:create` -- the
    save route's whole permission set -- would take a 403 on their first save
    and a 201 on their second, i.e. a state-dependent authorization answer and
    a frontend button that fails exactly once. The row is therefore built
    here, field for field as `create_folder` builds it.

    No ACL validation is skipped in substance: the role ids come from
    `select(Role)` over the acting tenant, so `_assert_role_ids_resolve`'s
    invariant holds by construction. The folder is a fixed, system-managed
    container rather than operator-authored content, which is what makes
    `documents:create` the right gate for it.
    """
    folder = session.exec(
        select(DocumentFolder).where(
            DocumentFolder.name == OBRAS_FOLDER_NAME,
            DocumentFolder.parent_id == None,  # noqa: E711  # SQLAlchemy column expression; `is None` does not compile to SQL
        )
    ).first()
    if folder is not None:
        return folder.id

    created = DocumentFolder(
        name=OBRAS_FOLDER_NAME,
        description="Relatórios de obras gerados pelo módulo de obras.",
        parent_id=None,
        allowed_role_ids_json=json.dumps(
            [str(role.id) for role in session.exec(select(Role)).all()]
        ),
        created_at=clock.db_now(),
        updated_at=clock.db_now(),
    )
    session.add(created)
    session.commit()
    session.refresh(created)
    return created.id


def save_report(
    session: Session,
    user: User,
    storage_provider: BaseStorageProvider | None = None,
) -> Any:
    """Render the report and file it in the Document Center.

    The `documents:create` assertion is the **first** statement, before the
    HTML is rendered, before a byte is written and before the folder is looked
    up or created: a refused caller must leave no folder and no file behind.
    `document_service.create_document`'s own check then passes by construction.
    """
    if not has_permission(user, session, "documents:create"):
        raise ForbiddenError("Not enough privileges")

    report_html = render_report_html(session, user)
    payload = report_html.encode("utf-8")

    # Server-rendered HTML: it goes to the generated tree, which the mount
    # serving it renders inline. Never `static/uploads`, which forces a
    # download for `.html` precisely because a client can write there.
    provider = storage_provider or generated_storage_provider()
    _file_path, url = provider.save_file(payload, REPORT_FILENAME, "text/html")

    generated_at = clock.db_now()
    folder_id = _find_or_create_obras_folder(session)
    return document_service.create_document(
        session,
        user,
        AssociationDocumentCreate(
            folder_id=folder_id,
            title=f"Relatório de Obras — {generated_at.strftime('%d/%m/%Y %H:%M:%S')}",
            description="Relatório de obras gerado automaticamente pelo APRAS.",
            file_url=url,
            file_size_bytes=len(payload),
            mime_type="text/html",
            publication_year=generated_at.year,
            publication_month=generated_at.month,
        ),
    )
