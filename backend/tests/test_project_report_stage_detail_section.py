"""APRAS-115: the JavaScript-free stage-detail section of the obras report.

`PublicObrasReportPage.tsx` injects the rendered document into an
`<iframe srcDoc sandbox="">`. An empty `sandbox` turns *every* restriction on,
`allow-scripts` included, so **no JavaScript in that document can ever run**.
A `<script>` accordion is impossible rather than merely unwanted, and so is an
inline `onclick`; `<details>`/`<summary>` is the only collapsible mechanism the
renderer has. That is also why `CSS_BODY`'s new `@media print` block forces the
collapsed contents visible on paper: nobody can expand a printed page.

Three of this module's cases have a shape this repository has already shipped
nine times -- a test that asserts nothing -- so each carries an explicit
anti-vacuity anchor and each says, in its docstring, which source change makes
it fail:

* :func:`extract_section` **raises** instead of returning `""`. Every count in
  ER1/ER3 is taken over its result, and an empty string satisfies all of them
  as `0 == 0`;
* the no-`<script>` case proves the section present and non-empty *before* it
  asserts an absence, and the inline-handler regex is anchored inside a tag --
  48 of the 152 real serviço names carry a comma and several an em dash or a
  `/`, so a bare `on[a-z]+=` scan over section text false-positives;
* the "no payload renders no section" case renders **two independently built**
  projects and asserts the populated one *does* carry the section, because the
  negative half alone passes on a renderer that never emits it.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.services import project_report_service as report
from tests.test_project_report_bar_geometry import parse_css

DATA = Path(__file__).resolve().parent / "data"

#: The real payload APRAS-114 committed: two stages keyed by milestone title,
#: extracted from the contractor's cached `.mpp`. Used here so the section is
#: proven against a payload of the real *shape* -- comma-rich SHOUTING names,
#: an unrounded stage `pct`, an eight-leaf stage -- and not only against dicts
#: written to suit the renderer.
FIXTURE = DATA / "obras_stage_detail_fixture.json"

DEMOLITIONS_KEY = "Demolições — Térreo e Superior"
HYDRAULICS_KEY = "Instalações Hidraulicas — Térreo e Superior"

#: The leaf name the title-caser is pinned against. A naive `str.title()`
#: renders `"Cozinha, Wc e Wc Pcd"`; the port must keep `WC` and `PCD` upper
#: and `e` lower. The real fixture contains it verbatim, twice.
RAW_WC_TAIL = "COZINHA, WC E WC PCD- PAVIMENTO TÉRREO"
CASED_WC_TAIL = "Cozinha, WC e WC PCD- Pavimento Térreo"

SECTION_OPEN = '<details class="all">'
STAGE_OPEN = '<details class="ph"'
SUMMARY_LABEL = "Mostrar detalhes"

#: U+2013 EN DASH, the range separator the approved mock spells. Named
#: because ruff reports the glyph as confusable with a hyphen-minus at
#: every literal use, and a `noqa` per use says less than this does.
EN_DASH = "\u2013"

#: An inline event-handler attribute, **anchored inside a tag**. See the module
#: docstring for why the unanchored form cannot be used on this content.
INLINE_HANDLER = re.compile(r"<[^>]*\son[a-z]+\s*=", re.IGNORECASE)


class SectionNotFoundError(AssertionError):
    """:func:`extract_section` found no balanced `<details class="all">`."""


def extract_section(document: str) -> str:
    """The section's substring: `<details class="all">` to its **matching** close.

    Walks the `<details` / `</details>` tokens with a depth counter, because the
    per-stage `<details class="ph">` nest inside the outer one and a naive
    `find("</details>")` would stop at the first inner close.

    **Raises rather than returning `""`.** Every count and every absence
    assertion in this module is taken over this substring, and an empty string
    satisfies each of them vacuously -- `0 == 0` for the cross-check,
    `"<script" not in ""` for ER3. Raising turns an absent section into a loud
    failure at the one place three results depend on.
    """
    start = document.find(SECTION_OPEN)
    if start == -1:
        raise SectionNotFoundError(
            f"no {SECTION_OPEN} in a {len(document)}-char document"
        )
    depth = 0
    for match in re.finditer(r"</?details\b", document[start:]):
        depth += -1 if match.group().startswith("</") else 1
        if depth == 0:
            close = document.find(">", start + match.end())
            if close == -1:
                raise SectionNotFoundError("the matching </details> is unterminated")
            return document[start : close + 1]
    raise SectionNotFoundError("the <details> walk never returned to depth 0")


# ---------------------------------------------------------------------------
# The shared fixture: the mixed rollout state, which is the normal one
# ---------------------------------------------------------------------------

#: Determinism exactly as APRAS-114 pinned it: literal `generated_at`, literal
#: `updated_at`, `tenant=None`, `user=None`, a past-only planned curve and
#: bulletins with literal `created_at`. Nothing here may reach `clock.db_now()`.
GENERATED_AT = datetime.fromisoformat("2026-09-26T14:30:00")
PLANNED_CURVE = [
    {"month": "2020-01", "pct": 8.0},
    {"month": "2020-02", "pct": 31.5},
    {"month": "2020-03", "pct": 64.0},
]

#: A leaf name carrying all three characters `html.escape` exists for -- `<`,
#: `&` and `"`. Leaf names come out of the contractor's `.mpp` file and land in
#: a **public** report with nothing upstream sanitising them, so the escape in
#: :func:`report._stage_leaf_html` is the only thing between the two. None of
#: the 13 committed names contains any of the three, which is why dropping the
#: `_e` call used to leave this module green: the `"<script" not in section`
#: clause of the ER3 case had no `<` to find either way.
HOSTILE_LEAF_NAME = 'ANDAIME <script>alert("xss")</script> & LONA'

#: What the renderer must emit for :data:`HOSTILE_LEAF_NAME`. The caser runs
#: **before** the escape, and it capitalises the opening tag's first letter, so
#: the fragments are compared case-insensitively at the use site.
ESCAPED_HOSTILE_FRAGMENTS = (
    "&lt;script&gt;",
    "alert(&quot;xss&quot;)",
    "&lt;/script&gt;",
    "&amp; lona",
)

#: The same fragments unescaped. Each must be absent from the rendered section;
#: together they are what fails when `_e` is dropped from the leaf renderer.
RAW_HOSTILE_FRAGMENTS = (
    "<script",
    'alert("xss")',
    "</script",
    "& lona",
)

#: A hand-written stage with a known leaf count and the three leaf states the
#: mock shows (`d`/`w`/`n`), plus both dateless shapes: one leaf with neither
#: date and one with only a `start`, and the hostile name above.
PRELIMINARY_PAYLOAD: dict[str, object] = {
    "pct": 63.0,
    "start": "2026-09-21",
    "leaves": [
        {
            "name": "DESMONTAGEM DE ESTRUTURAS EXISTENTES",
            "pct": 100.0,
            "start": "2026-09-21",
            "finish": "2026-09-22",
        },
        {
            "name": "ENTRADA DE CAMINHÕES",
            "pct": 90.0,
            "start": None,
            "finish": None,
        },
        {
            "name": "SAIDA DE VEICULOS GERAL",
            "pct": 0.0,
            "start": "2026-09-25",
            "finish": None,
        },
        {
            "name": HOSTILE_LEAF_NAME,
            "pct": 40.0,
            "start": "2026-09-23",
            "finish": "2026-09-24",
        },
    ],
}

#: A decoded stage that is its own leaf: valid per APRAS-114 ER8, one frente
#: and zero serviços, and the reason ER3's anchor is a disjunction.
EMPTY_STAGE_PAYLOAD: dict[str, object] = {
    "pct": 0.0,
    "start": "2026-11-02",
    "leaves": [],
}

#: `(title, status, payload)`, in `display_order` order. Three real-shaped or
#: hand-written payloads, one stage with no leaves and one milestone whose
#: `detail_json` is `None` -- so the **mixed** state is the default fixture and
#: not a special case. The titles carry the producer's `" · "` separator except
#: `"Serviços Preliminares"`, which is the no-parent case ER2 needs.
#: The two stage *names* are deliberately distinct even though the committed
#: fixture keys both end `"— Térreo e Superior"`: :func:`block_for` locates a
#: block by the name its summary prints, and two identical names would make it
#: ambiguous rather than wrong.
MILESTONE_TITLES = (
    "Demolições · Térreo e Superior",
    "Instalações Hidraulicas · Térreo e Pavimento Superior",
    "Serviços Preliminares",
    "Estruturas Metalicas · Alvenaria e Vedações",
    "Acabamentos · Pintura Geral",
)

DEMOLITIONS_TITLE, HYDRAULICS_TITLE, PRELIMINARY_TITLE = MILESTONE_TITLES[:3]
EMPTY_STAGE_TITLE, NO_PAYLOAD_TITLE = MILESTONE_TITLES[3:]


def real_payload(key: str) -> dict[str, object]:
    """One stage of the committed fixture, as a fresh mutable dict."""
    return copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8"))[key])


def payloads() -> dict[str, dict[str, object] | None]:
    """Each milestone title mapped to the payload it carries, freshly built."""
    return {
        DEMOLITIONS_TITLE: real_payload(DEMOLITIONS_KEY),
        HYDRAULICS_TITLE: real_payload(HYDRAULICS_KEY),
        PRELIMINARY_TITLE: copy.deepcopy(PRELIMINARY_PAYLOAD),
        EMPTY_STAGE_TITLE: copy.deepcopy(EMPTY_STAGE_PAYLOAD),
        NO_PAYLOAD_TITLE: None,
    }


def detail_project(
    overrides: dict[str, dict[str, object] | None] | None = None,
) -> ConstructionProject:
    """A fresh project in the mixed state, built from scratch on every call.

    Built rather than cached, and never mutated in place by a caller, because
    ER4 and ER5 each need **two independent instances** -- one populated, one
    all-NULL. "Null the payloads on the instance, then render both" is the
    classic way those cases pass while asserting nothing about the populated
    one.
    """
    detail = payloads() | (overrides or {})
    statuses = (
        MilestoneStatus.DONE,
        MilestoneStatus.IN_PROGRESS,
        MilestoneStatus.IN_PROGRESS,
        MilestoneStatus.NEXT_STEPS,
        MilestoneStatus.NEXT_STEPS,
    )
    milestones = [
        ProjectMilestone(
            title=title,
            description="Serviço A, Serviço B",
            status=status,
            display_order=order,
            due_date=date(2026, 10, 10 + order),
            completion_date=(
                date(2026, 9, 10 + order) if status is MilestoneStatus.DONE else None
            ),
            created_at=datetime.fromisoformat("2026-09-01T08:00:00"),
            updated_at=datetime.fromisoformat("2026-09-02T08:00:00"),
            detail_json=detail[title],
        )
        for order, (title, status) in enumerate(
            zip(MILESTONE_TITLES, statuses, strict=True), start=1
        )
    ]
    return ConstructionProject(
        title="Sede Social — Reforma (Edificação)",
        description="Reforma integral do térreo e do pavimento superior.",
        status=ProjectStatus.IN_PROGRESS,
        physical_progress_pct=Decimal("42.50"),
        total_budget=Decimal("480000.00"),
        executed_budget=Decimal("204000.00"),
        start_date=date(2026, 9, 25),
        estimated_completion_date=date(2027, 3, 31),
        cover_photo_url=None,
        planned_progress_json=PLANNED_CURVE,
        created_at=datetime.fromisoformat("2026-09-01T07:00:00"),
        updated_at=datetime.fromisoformat("2026-09-05T07:00:00"),
        milestones=milestones,
        updates=[
            ProjectUpdate(
                title="Boletim 1",
                content="Frente 1 em andamento.",
                photos_json=None,
                cost_impact=Decimal("0.00"),
                created_at=datetime.fromisoformat("2026-09-21T09:00:00"),
            )
        ],
    )


def null_detail_project() -> ConstructionProject:
    """The same milestone rows with every `detail_json` NULL -- production's
    live state, and the instance ER4/ER5 compare against."""
    return detail_project(dict.fromkeys(MILESTONE_TITLES))


def expected_totals(
    project: ConstructionProject | None = None,
) -> tuple[int, int]:
    """`(frentes, serviços)` computed from the fixture payloads themselves.

    Derived here for the same reason the renderer derives them: a literal pair
    would keep passing after the renderer stopped counting what it shows.
    """
    rows = (project or detail_project()).milestones
    stages = [
        stage
        for row in rows
        if (stage := report.decode_stage_detail(row.detail_json)) is not None
    ]
    return len(stages), sum(len(stage.leaves) for stage in stages)


def stage_blocks(section: str) -> list[str]:
    """The section split into one string per `<details class="ph">` block."""
    parts = section.split(STAGE_OPEN)
    return [STAGE_OPEN + part for part in parts[1:]]


def block_for(section: str, title: str) -> str:
    """The one stage block whose summary carries `title`'s own name."""
    name = report._split_stage_title(title)[1]
    matches = [block for block in stage_blocks(section) if f">{name}<" in block]
    assert len(matches) == 1, f"{name}: {len(matches)} blocks"
    return matches[0]


# ---------------------------------------------------------------------------
# ER1 -- the totals are derived, proved by cross-check and not by a literal
# ---------------------------------------------------------------------------


def test_the_summary_totals_match_what_the_section_actually_renders():
    """ER1: frentes == emitted `<details class="ph">`, serviços == emitted `<li>`.

    The cross-check is the whole point: a hard-coded `26 frentes, 82 serviços`
    survives every assertion that reads the summary, and only a comparison
    against the section's own content refuses it. Both counts are taken over
    `extract_section`, never the document -- the stage cards emit bare `<li>`
    too, so a document-wide count over-reports.

    *Fails if:* the totals are literals, or count all milestones rather than
    the decoded ones, or count leaves the section does not render.
    """
    frentes, servicos = expected_totals()
    section = extract_section(report._stages_html(detail_project()))

    assert f"{SUMMARY_LABEL} <em>— {frentes} frentes, {servicos} serviços</em>" in (
        section
    )
    assert section.count(STAGE_OPEN) == frentes
    assert section.count("<li") == servicos
    # Anti-vacuity: a zero-for-zero agreement is not evidence of anything.
    assert frentes > 1
    assert servicos > 1


def test_one_more_leaf_moves_the_servicos_total_but_not_the_frentes_total():
    """ER1: the second number tracks the leaf lists, the first does not."""
    base_frentes, base_servicos = expected_totals()

    grown = copy.deepcopy(PRELIMINARY_PAYLOAD)
    leaves = list(grown["leaves"])  # type: ignore[arg-type]
    leaves.append(
        {
            "name": "SERVIÇO ADICIONAL DE TESTE",
            "pct": 10.0,
            "start": "2026-09-26",
            "finish": "2026-09-27",
        }
    )
    grown["leaves"] = leaves
    project = detail_project({PRELIMINARY_TITLE: grown})

    frentes, servicos = expected_totals(project)
    section = extract_section(report._stages_html(project))

    assert (frentes, servicos) == (base_frentes, base_servicos + 1)
    assert section.count(STAGE_OPEN) == frentes
    assert section.count("<li") == servicos


def test_one_more_decoded_stage_moves_both_totals():
    """ER1: giving the NULL milestone a payload moves frentes *and* serviços."""
    base_frentes, base_servicos = expected_totals()
    project = detail_project(
        {NO_PAYLOAD_TITLE: copy.deepcopy(PRELIMINARY_PAYLOAD)},
    )

    frentes, servicos = expected_totals(project)
    section = extract_section(report._stages_html(project))

    assert frentes == base_frentes + 1
    assert servicos == base_servicos + len(PRELIMINARY_PAYLOAD["leaves"])  # type: ignore[arg-type]
    assert section.count(STAGE_OPEN) == frentes
    assert section.count("<li") == servicos


def test_a_milestone_without_a_payload_is_counted_in_neither_total():
    """ER1: the mixed state -- a NULL milestone is rendered nowhere.

    A summary promising 26 frentes and revealing 9 is worse than one promising
    9, so both numbers count only what the section shows.
    """
    section = extract_section(report._stages_html(detail_project()))
    absent = report._split_stage_title(NO_PAYLOAD_TITLE)[1]

    assert section.count(STAGE_OPEN) == len(MILESTONE_TITLES) - 1
    assert absent not in section


def test_the_singular_forms_are_spelled_not_derived():
    """ER1: `1 frente` / `1 serviço`, never `1 frentes` or a glued-on `s`."""
    single = {
        "pct": 100.0,
        "start": "2026-09-21",
        "leaves": [
            {
                "name": "INSTALAÇÃO DE CONTAINERS",
                "pct": 100.0,
                "start": "2026-09-14",
                "finish": "2026-09-15",
            }
        ],
    }
    project = detail_project(
        dict.fromkeys(MILESTONE_TITLES) | {PRELIMINARY_TITLE: single},
    )

    section = extract_section(report._stages_html(project))

    assert expected_totals(project) == (1, 1)
    assert f"{SUMMARY_LABEL} <em>— 1 frente, 1 serviço</em>" in section
    assert "1 frentes" not in section
    assert "1 serviços" not in section


# ---------------------------------------------------------------------------
# ER2 -- the content of one stage block
# ---------------------------------------------------------------------------


def test_a_stage_block_carries_its_title_percentage_leaves_and_dates():
    """ER2: the whole contract of one hand-written stage, leaf by leaf.

    *Fails if:* a leaf percentage or its dates are dropped, or the stage
    percentage is taken from the milestone instead of from the payload.
    """
    section = extract_section(report._stages_html(detail_project()))
    block = block_for(section, PRELIMINARY_TITLE)

    assert f'<span class="nm">{PRELIMINARY_TITLE}</span>' in block
    assert '<span class="pp">63%</span>' in block
    assert (
        '<li class="d">Desmontagem de Estruturas Existentes<b>100%</b>'
        f"<i>21/09{EN_DASH}22/09</i></li>"
    ) in block
    assert '<li class="w">Entrada de Caminhões<b>90%</b></li>' in block
    assert '<li class="n">Saida de Veiculos Geral<b>0%</b><i>25/09</i></li>' in block


def test_the_stage_percentage_comes_from_the_payload_and_not_the_milestone():
    """ER2: the real fixture's unrounded 49.5588... renders as `50%`.

    No milestone column carries that number, so a block showing it can only
    have read `detail.pct`.
    """
    section = extract_section(report._stages_html(detail_project()))
    block = block_for(section, DEMOLITIONS_TITLE)

    assert report._pct(real_payload(DEMOLITIONS_KEY)["pct"]) == "50%"  # type: ignore[arg-type]
    assert '<span class="pp">50%</span>' in block


def test_the_parent_kicker_appears_only_when_the_title_carries_one():
    """ER2: `<span class="top">` for a `" · "` title, omitted for a bare one.

    The cards split on the producer's `" · "` separator since APRAS-113, so the
    section reads the same vocabulary rather than the `(kind)` suffix
    `split_title_and_kind` handles -- which no milestone title carries.
    """
    section = extract_section(report._stages_html(detail_project()))

    with_parent = block_for(section, DEMOLITIONS_TITLE)
    without_parent = block_for(section, PRELIMINARY_TITLE)

    assert '<span class="top">Demolições</span>' in with_parent
    assert '<span class="top">' not in without_parent
    assert '<span class="nm">Térreo e Superior</span>' in with_parent


def test_the_stage_title_is_rendered_as_stored_and_never_title_cased():
    """ER2: only leaf names go through the caser -- it lowercases first.

    APRAS-113 pins the same property on the cards. Running the stored title
    through the helper would flatten an all-caps suffix, which is a defect and
    not a no-op.
    """
    shouting = "REFORMA DA FACHADA · WC PCD E ACESSO"
    project = detail_project()
    project.milestones[2].title = shouting

    section = extract_section(report._stages_html(project))

    assert '<span class="top">REFORMA DA FACHADA</span>' in section
    assert '<span class="nm">WC PCD E ACESSO</span>' in section


def test_the_stage_title_reaches_the_summary_escaped_on_both_halves():
    """ER2: `_e` on the stage `<summary>`, both the parent and the name.

    The leaf names are the hostile surface -- they come out of the
    contractor's `.mpp` with nothing upstream sanitising them -- and their
    escaping is pinned. `milestone.title` is admin-entered rather than
    contractor-supplied, so this is a **coverage gap and not a live defect**:
    the code is already correct. It is pinned anyway rather than argued away,
    on three counts. It is the same public-report surface, rendered into the
    same document by the same function, one line from the leaf renderer. The
    hostile-name machinery already exists in this module, so the case costs a
    fixture-free test and no new concepts. And "admin-entered" is a property
    of today's callers, not of the renderer: it is exactly the kind of premise
    that stops holding without anyone revisiting the escape it justified.

    The two halves are asserted separately because they are two `_e` calls:
    dropping either one alone left the whole report suite green.

    *Fails if:* `_e` is dropped from `{_e(parent)}` or from `{_e(name)}` in
    :func:`report._stage_detail_block_html`.
    """
    parent = 'FACHADA <b>"A"</b> & B'
    name = 'ANDAIME <script>alert("stage")</script> & LONA'
    project = detail_project()
    project.milestones[2].title = f"{parent} · {name}"

    section = extract_section(report._stages_html(project))

    # Present in escaped form -- an absence-only assertion is also satisfied
    # by a renderer that drops the title entirely.
    assert f'<span class="top">{report._e(parent)}</span>' in section
    assert f'<span class="nm">{report._e(name)}</span>' in section
    # ...and absent in raw form, which is the half that fails without `_e`.
    assert parent not in section
    assert name not in section
    assert "<script" not in section.lower()
    # `<b>` alone is the serviço percentage element, so the raw fragment has
    # to carry its own text to mean anything here.
    assert '<b>"a"</b>' not in section.lower()


def test_a_real_comma_rich_leaf_name_is_not_over_escaped():
    """ER2: the committed fixture's name, title-cased and otherwise verbatim.

    **Named for its direction** (APRAS-117). This case guards *over*-escaping
    only -- that `_e` does not mangle an innocent name on the way past -- and
    it says nothing at all about *under*-escaping, which is the direction that
    carries the risk. Its previous name, `..._survives_apart_from_its_casing`,
    read as escaping coverage and is exactly the shape that stops the next
    person looking: every escape in the report module was unpinned while it
    passed. The under-escaping direction is
    :func:`test_the_section_is_present_non_empty_and_carries_no_script_or_handler`
    step 4 here, and `tests/test_project_report_escaping.py` for the module
    as a whole.

    *Fails if:* escaping mangles the name, the names ship SHOUTING, or a naive
    `.title()` renders `Wc`, `Pcd` and `De`.
    """
    raw = [
        leaf["name"]
        for leaf in real_payload(HYDRAULICS_KEY)["leaves"]  # type: ignore[index]
        if RAW_WC_TAIL in leaf["name"]
    ]
    assert raw, "the fixture no longer carries the pinned WC/PCD name"

    section = extract_section(report._stages_html(detail_project()))

    assert CASED_WC_TAIL in section
    assert RAW_WC_TAIL not in section
    assert "Wc" not in section
    assert "Pcd" not in section
    # The comma and the rest of the punctuation reach the document untouched.
    assert "Realocação de Pontos de Esgoto" in section
    assert "Cozinha," in section


def test_the_dot_state_class_follows_the_stage_percentage():
    """ER2: `dot d` above 0%, `dot n` at 0%, as the mock renders them."""
    section = extract_section(report._stages_html(detail_project()))

    assert '<span class="dot d"></span>' in block_for(section, DEMOLITIONS_TITLE)
    assert '<span class="dot n"></span>' in block_for(section, HYDRAULICS_TITLE)


# ---------------------------------------------------------------------------
# ER2b -- the dateless serviço and the stage with no leaves
# ---------------------------------------------------------------------------


def test_a_leaf_with_neither_date_omits_the_element_entirely():
    """ER2b: no `<i></i>`, no bare dash -- the grid row would reserve space.

    *Fails if:* a null date raises, renders `None`, or renders a dangling dash.
    """
    section = extract_section(report._stages_html(detail_project()))
    block = block_for(section, PRELIMINARY_TITLE)
    row = next(line for line in block.split("<li") if "Entrada de Caminhões" in line)

    assert "<i>" not in row
    assert "None" not in row
    assert EN_DASH not in row


def test_a_leaf_with_only_a_start_renders_that_date_with_no_dash():
    """ER2b: `<i>25/09</i>`, not `<i>25/09</i>` with a trailing dash."""
    section = extract_section(report._stages_html(detail_project()))
    block = block_for(section, PRELIMINARY_TITLE)
    row = next(line for line in block.split("<li") if "Saida de Veiculos" in line)

    assert "<i>25/09</i>" in row
    assert EN_DASH not in row


def test_a_stage_with_no_leaves_renders_its_summary_and_the_none_line():
    """ER2b: one frente, zero serviços, visible rather than silently dropped."""
    section = extract_section(report._stages_html(detail_project()))
    block = block_for(section, EMPTY_STAGE_TITLE)

    assert '<span class="nm">Alvenaria e Vedações</span>' in block
    assert '<p class="none">—</p>' in block
    assert "<li" not in block


def test_a_project_whose_only_decoded_stage_has_no_leaves_says_zero_servicos():
    """ER2b: `1 frente, 0 serviços` -- the count is of what is rendered."""
    project = detail_project(
        dict.fromkeys(MILESTONE_TITLES)
        | {EMPTY_STAGE_TITLE: copy.deepcopy(EMPTY_STAGE_PAYLOAD)},
    )

    section = extract_section(report._stages_html(project))

    assert expected_totals(project) == (1, 0)
    assert f"{SUMMARY_LABEL} <em>— 1 frente, 0 serviços</em>" in section
    assert section.count("<li") == 0


# ---------------------------------------------------------------------------
# ER2c -- the sort key is total, so two renders of one payload cannot differ
# ---------------------------------------------------------------------------


def test_two_stages_sharing_a_display_order_and_a_title_order_by_id():
    """ER2c: the `id` tiebreak, which nothing else in this module can see.

    Nothing forbids two milestone rows carrying the same `display_order`
    **and** the same `title`. Without a unique third key they order by
    whatever sequence the caller happened to hold them in, and the section
    reorders between two renders of identical data -- flaky, not wrong, which
    is the harder kind to chase.

    The two rows are appended in **descending** `id` order on purpose.
    `sorted` is stable, so a key that stops at `(display_order, title)` would
    return them in that same descending order and this case would fail;
    nothing weaker than constructing the list against the expected result
    distinguishes the two keys.

    *Fails if:* `milestone.id` is dropped from
    :func:`report._stage_detail_sort_key`, or an `or 0` fallback is added --
    that would raise `TypeError` comparing a `UUID` with an `int`.
    """
    twins = sorted(
        (
            ProjectMilestone(
                title="Fundações · Bloco Único",
                description="",
                status=MilestoneStatus.IN_PROGRESS,
                display_order=1,
                created_at=datetime.fromisoformat("2026-09-01T08:00:00"),
                updated_at=datetime.fromisoformat("2026-09-02T08:00:00"),
                detail_json={
                    "pct": 10.0,
                    "start": "2026-09-21",
                    "leaves": [
                        {
                            "name": name,
                            "pct": 10.0,
                            "start": None,
                            "finish": None,
                        }
                    ],
                },
            )
            for name in ("GEMEA ALFA", "GEMEA BETA")
        ),
        key=lambda row: row.id,
        reverse=True,
    )
    # Anti-vacuity: the twins really are indistinguishable but for their ids.
    assert twins[0].display_order == twins[1].display_order
    assert twins[0].title == twins[1].title
    assert twins[0].id > twins[1].id

    project = detail_project()
    project.milestones = twins

    section = extract_section(report._stages_html(project))
    first, second = (
        report.title_case(twins[index].detail_json["leaves"][0]["name"])
        for index in (1, 0)
    )

    assert section.index(first) < section.index(second)


def test_the_servicos_of_one_stage_render_in_payload_order():
    """ER2c: `_stage_detail_html`'s docstring says serviços are *never*
    re-sorted -- this is the test that makes that sentence a contract.

    The guarantee was documented and unpinned: wrapping `detail.leaves` in
    `sorted(key=lambda leaf: leaf.name)` left the whole report suite green,
    because every other case asserts that a name is *present* and none asserts
    where. Payload order is the contractor's schedule order, it is meaningful
    to the síndico reading the frente top to bottom, and a name sort would
    destroy it silently.

    :data:`PRELIMINARY_PAYLOAD` is what makes the assertion able to fail: its
    leaves are written in schedule order, and the hostile `ANDAIME...` name it
    carries last sorts **first** alphabetically, so payload order and name
    order disagree on this stage rather than coinciding by luck.

    *Fails if:* the renderer sorts, reverses or otherwise reorders
    `detail.leaves`.
    """
    names = [
        leaf["name"]
        for leaf in PRELIMINARY_PAYLOAD["leaves"]  # type: ignore[index]
    ]
    # Anti-vacuity: with fewer than two leaves nothing below has an order, and
    # if payload order happened to *be* name order a sort would be invisible.
    assert len(names) > 1
    assert names != sorted(names)

    block = block_for(
        extract_section(report._stages_html(detail_project())), PRELIMINARY_TITLE
    )
    positions = [block.index(report._e(report.title_case(name))) for name in names]

    assert positions == sorted(positions), names


def test_neither_details_level_carries_the_open_attribute():
    """ER2c: both levels ship closed, which is the whole cost argument.

    `_stage_detail_html`'s docstring promises *neither* level carries `open`.
    The outer level was already well pinned -- adding `open` there kills 19
    cases through the byte-identical and markup assertions -- but the inner
    `<details class="ph">` was not: adding `open` to it left the suite green,
    and an inner level that opens by default expands every frente of every
    stage the moment the report is opened, which is about a page per obra and
    exactly what the nesting exists to avoid.

    The regex scans **tag interiors only**, for the same reason
    :data:`INLINE_HANDLER` does: serviço names are punctuation-rich and a bare
    `open` scan over section text would false-positive on a name.

    *Fails if:* `open` is added to either level, at any point.
    """
    section = extract_section(report._stages_html(detail_project()))

    # Anti-vacuity: both levels are actually present in what is being scanned.
    assert SECTION_OPEN in section
    assert section.count(STAGE_OPEN) == expected_totals()[0]

    opened = re.findall(r"<details[^>]*\bopen\b[^>]*>", section, re.IGNORECASE)
    assert opened == [], opened


# ---------------------------------------------------------------------------
# ER10 -- the title-caser's mechanism, not an allowlist of two names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The pinned fixture tail: the mechanism, end to end.
        (RAW_WC_TAIL, CASED_WC_TAIL),
        # The preposition rule, which is why `str.title()` will not do.
        ("ENTRADA DE CAMINHÕES", "Entrada de Caminhões"),
        ("DEMOLIÇÃO DE PAREDES EM ALVENARIA", "Demolição de Paredes em Alvenaria"),
        # A MINOR word in *initial* position is still capitalised.
        ("DE ACORDO COM O PROJETO", "De Acordo com o Projeto"),
        # (a) no vowel -> verbatim, with no list naming any of these.
        ("INSTALAÇÃO DE PVC", "Instalação de PVC"),
        ("QUADRO QDG", "Quadro QDG"),
        ("SISTEMA CFTV", "Sistema CFTV"),
        # (b) a digit, or a slash between alphanumerics, passes unchanged --
        # and rule (b) is an `or` of two operands, each of which needs a row
        # that *reaches* it. A token gets to line 639 only after surviving the
        # vowel test, so a vowel-less token proves nothing about (b):
        # `30` and `M2` both return at rule (a) and never reach the digit
        # clause at all. This row is a rule (a) row wearing a (b) comment, and
        # it stays only because it is the shape the real data has.
        ("AREA DE 30 M2", "Area de 30 M2"),
        # The digit operand, reached: `TIPO2` carries a vowel *and* a digit, so
        # (a) passes it on and only the digit clause keeps it upper. Deleting
        # that clause renders `Laje Tipo2`.
        ("LAJE TIPO2", "Laje TIPO2"),
        # `AC/60` is the same trap one operand over: `bare` keeps its digits,
        # so this row is satisfied by the *digit* clause and survives deleting
        # the slash one.
        ("CABO AC/60", "Cabo AC/60"),
        # The slash operand, reached: a vowel, an internal slash and no digit
        # anywhere, so this is the only row that fails when the slash clause
        # goes. Without it the caser renders `Area de Circulacao/acesso`.
        ("AREA DE CIRCULACAO/ACESSO", "Area de CIRCULACAO/ACESSO"),
        # ...and the narrowing that makes rule (b) *internal* rather than
        # "contains a slash". Both forms satisfy `AC/60` above, so only this
        # row pins the distinction. The committed fixture carries
        # `"SUPERIOR/ LAVABO"` twice, and the contains-form ships
        # `Pavimento SUPERIOR/ Lavabo` -- SHOUTING mid-sentence.
        ("PAVIMENTO SUPERIOR/ LAVABO", "Pavimento Superior/ Lavabo"),
        # The first *letter* is capitalised, not the first character: the
        # committed fixture really carries "(TOLDO METALICO)", and the
        # operator script's own `part[:1].upper()` renders it "(toldo".
        ("FACHADA (TOLDO METALICO)", "Fachada (Toldo Metalico)"),
        ("- REMOÇÃO DE PISO", "- Remoção de Piso"),
        # (c) the named residue: vowel-bearing acronyms the data carries.
        ("RAMPA PNE", "Rampa PNE"),
        ("EMISSAO DE ART", "Emissao de ART"),
    ],
)
def test_the_title_caser_mechanism(raw: str, expected: str):
    """ER10: a vowel-less token survives *because it has no vowel*.

    The assertion is over the mechanism and not over the two names `WC` and
    `PCD`: an allowlist alone only moves the defect to the next acronym nobody
    listed, and the usual "already uppercase" signal is unavailable because the
    input is uniformly SHOUTING.

    *Fails if:* the port is `str.title()`, or drops the preposition rule, or
    keeps acronyms only by naming them one at a time.
    """
    assert report.title_case(raw) == expected


def test_the_acronym_residue_is_a_named_constant_and_not_a_hidden_list():
    """ER10 (c): the next acronym is a data edit, not a code change.

    The vowel-less names the real data holds must be absent from it -- if they
    had to be listed, rule (a) is not doing its job.
    """
    residue = report.TITLE_CASE_ACRONYMS

    assert residue, "the residue exists and is reachable by name"
    assert {"WC", "PCD", "PVC", "QDG", "CFTV"}.isdisjoint(residue)
    assert all(token == token.upper() for token in residue)


def test_a_vowel_less_token_absent_from_the_residue_still_survives():
    """ER10 (a), isolated: rule (a) and not the allowlist is what keeps `WC`."""
    invented = "XPTQ"

    assert invented not in report.TITLE_CASE_ACRONYMS
    assert report.title_case(f"PAINEL {invented} NOVO") == f"Painel {invented} Novo"


# ---------------------------------------------------------------------------
# ER3 -- no script, no inline handler, anchored so it cannot pass empty
# ---------------------------------------------------------------------------


def test_the_section_is_present_non_empty_and_carries_no_script_or_handler():
    """ER3, in the order that makes the absence assertions mean something.

    Steps 1-2 prove the section exists and has content; only then does step 3
    assert an absence, and over `extract_section` rather than the document. The
    anchor is a **disjunction** -- each stage block carries at least one `<li`
    *or* one `<p class="none"` -- because the `leaves: []` fixture stage renders
    the latter and no `<li>` by design; the section-wide `<li>` clause and the
    count equality are what stop the disjunction passing on an empty section.

    Step 4 is the **under**-escaping half, and it is the reason
    :data:`HOSTILE_LEAF_NAME` is in the shared fixture at all. Asserting only
    that no `<script` appears proves nothing when no input contains a `<`:
    with every committed name innocent, dropping `_e` from the leaf renderer
    left this whole module green. The escaped fragments must be *present* --
    an absence-only assertion is also satisfied by a renderer that drops the
    name entirely.

    *Fails if:* a `<script>` or an `onclick` toggle is reached for, or the
    leaf name reaches the document unescaped, or the section stops being
    emitted at all.
    """
    document = report._stages_html(detail_project())
    frentes, _ = expected_totals()

    # 1. present
    assert SECTION_OPEN in document
    assert SUMMARY_LABEL in document
    section = extract_section(document)

    # 2. non-empty, in the form the `leaves: []` stage can actually satisfy
    blocks = stage_blocks(section)
    assert len(blocks) == frentes
    for block in blocks:
        assert "<li" in block or '<p class="none"' in block, block[:120]
    assert "<li" in section

    # 3. only now, the absences
    assert "<script" not in section.lower()
    assert INLINE_HANDLER.search(section) is None
    assert "javascript:" not in section.lower()

    # 4. and the hostile leaf name is *present*, in its escaped form only
    lowered = section.lower()
    for fragment in ESCAPED_HOSTILE_FRAGMENTS:
        assert fragment in lowered, fragment
    for fragment in RAW_HOSTILE_FRAGMENTS:
        assert fragment not in lowered, fragment


def test_the_inline_handler_regex_is_able_to_fail():
    """ER3: the anchored regex catches a handler *and* spares a serviço name.

    Without this control the step-3 assertion above is one whose checker has
    never been shown to fire, and the unanchored `on[a-z]+=` form would
    false-positive on the punctuation-rich real names.
    """
    assert INLINE_HANDLER.search('<summary onclick="x()">') is not None
    assert INLINE_HANDLER.search('<details OnToggle="x()">') is not None
    assert INLINE_HANDLER.search("<li>Pintura on=off, com demão dupla</li>") is None


# ---------------------------------------------------------------------------
# ER4 -- no payload, no section, anchored against the positive case
# ---------------------------------------------------------------------------


def test_no_decoded_stage_renders_no_section_and_a_payload_renders_one():
    """ER4: both halves in one case, from two independently built projects.

    The negative half alone passes on a renderer that never emits the section,
    so the positive anchor is asserted here rather than only elsewhere. The two
    instances come from two calls to the fixture builder -- never from nulling
    the payloads in place and rendering the same object twice.

    *Fails if:* the section is emitted unconditionally, or as an empty
    `<div class="inner">`, or with a "nenhum detalhe" placeholder.
    """
    populated = report._stages_html(detail_project())
    empty = report._stages_html(null_detail_project())

    assert SECTION_OPEN in populated
    assert extract_section(populated)

    for token in ("<details", "<summary", SUMMARY_LABEL, 'class="inner"'):
        assert token not in empty, token
    with pytest.raises(SectionNotFoundError):
        extract_section(empty)


def test_the_extractor_refuses_an_absent_or_unbalanced_section():
    """The helper three results depend on raises instead of returning `""`.

    An empty return satisfies every count in this module as `0 == 0`, which is
    the shape this repository has already shipped nine times.
    """
    with pytest.raises(SectionNotFoundError):
        extract_section("<section>no section here</section>")
    with pytest.raises(SectionNotFoundError):
        extract_section(f'{SECTION_OPEN}<details class="ph"></details>')


def test_the_document_level_render_emits_one_section_per_decoded_project():
    """ER1/ER4 at document level: `render_report_html` emits one `div.page` per
    project, so the per-project extraction is applied per page."""
    pages = [
        report._page_html(detail_project(), 1, None, None, GENERATED_AT),
        report._page_html(null_detail_project(), 2, None, None, GENERATED_AT),
    ]
    document = "".join(pages)

    assert document.count(SECTION_OPEN) == 1
    assert extract_section(document).count(STAGE_OPEN) == expected_totals()[0]


# ---------------------------------------------------------------------------
# ER5 -- the cards above the section are byte-identical
# ---------------------------------------------------------------------------


def test_the_section_is_appended_last_and_the_cards_are_byte_identical():
    """ER5: a property of the output, since no "before" capture can exist.

    **The spec's own formulation does not survive contact with APRAS-113.** It
    asked for `_stages_html(all-NULL)` minus its `</section>` to be a byte
    prefix of `_stages_html(populated)`. That is false by construction now: the
    APRAS-113 cards *themselves* read `detail_json` -- `_stage_item_html` emits
    a `<span class="pc">` only when the payload decodes, and Próximos passos
    buckets rows by their stage `start` -- so the two renders differ **above**
    the section, by APRAS-113's design and not by anything this task did.

    What is provable, and is what ER5 actually asks, is checked in four parts:

    1. the section is the **last** child of the `<section>`, appended verbatim;
    2. nothing above it is a `<details>` block, so it cannot have been inserted
       between the cards and the `.pv` bar;
    3. the three cards are byte-identical to what APRAS-113's own
       `_groups_html` produces for the same rows -- called independently here,
       so a reworded card or a section spliced inside the groups block fails;
    4. the head above the cards and the whole `.pv` bar block are byte-identical
       to the all-NULL render's, which is the region no payload can reach.

    The second, independent guard costs nothing:
    `test_the_all_null_page_renders_the_committed_baseline` already pins the
    all-NULL page against committed bytes, and this task does not regenerate
    that file.
    """
    project = detail_project()
    full_html = report._stages_html(project)
    section = report._stage_detail_html(list(project.milestones))
    null_html = report._stages_html(null_detail_project())

    # 1. appended last, verbatim.
    assert section
    assert full_html.endswith(section + "</section>")
    prefix = full_html.removesuffix(section + "</section>")

    # Anti-vacuity: `prefix` is a real stages block and not the empty string.
    assert prefix.startswith('<section class="section">')
    assert "Etapas da obra" in prefix

    # 2. nowhere but last.
    assert "<details" not in prefix

    # 3. the cards, byte for byte, as the preceding task's fragment builds them.
    cards = report._groups_html(list(project.milestones))
    assert cards.startswith('<div class="groups">')
    for title in MILESTONE_TITLES:
        assert report._split_stage_title(title)[1] in cards
    assert cards in prefix

    # 4. the head and the bar: the region no payload reaches, byte-identical.
    head = null_html[: null_html.index('<div class="groups">')]
    bar = null_html[null_html.index('<div class="pv">') :].removesuffix("</section>")
    assert head
    assert bar
    assert full_html.startswith(head)
    assert prefix.endswith(bar)


# ---------------------------------------------------------------------------
# ER6 -- the stylesheet's own two-way colour case
# ---------------------------------------------------------------------------

#: Every selector this task appends to `CSS_BODY`, as an exact ordered list: an
#: added rule nobody reviewed fails here, and so does a dropped one. Selected
#: by name rather than by a `details`/`.dot` prefix, because selecting them by
#: the property under test would make the test true by construction.
SECTION_SELECTORS = (
    "details.all",
    "details.all>summary",
    "details.all>summary em",
    "summary::-webkit-details-marker",
    "details.all>summary::before",
    "details.all[open]>summary::before",
    "details.all[open]>summary",
    ".inner",
    "details.ph",
    "details.ph:last-child",
    "details.ph>summary",
    "details.ph>summary::before",
    "details.ph[open]>summary::before",
    "details.ph .ttl",
    "details.ph .top",
    "details.ph .nm",
    "details.ph .none",
    ".dot",
    ".dot.d",
    ".dot.w",
    ".dot.n",
    ".pp",
    "details.ph ul",
    "details.ph li",
    "details.ph li:last-child",
    "details.ph li::before",
    "details.ph li.d::before",
    "details.ph li.w::before",
    "details.ph li b",
    "details.ph li i",
    # The new `@media print` block's own rules.
    "details.all, details.ph",
    (
        "details.all:not([open])>.inner, details.ph:not([open])>ul,"
        " details.ph:not([open])>.none"
    ),
    "details.all>summary::before, details.ph>summary::before",
)


def section_rules():
    """The `CSS_BODY` rules this task appends, top-level and nested alike."""
    sheet = parse_css(report.CSS_BODY)
    wanted = set(SECTION_SELECTORS)
    return [
        rule for rule in sheet.rules + sheet.nested_rules if rule.selector in wanted
    ]


def test_the_appended_rules_are_exactly_the_reviewed_set():
    """ER6/ER7: the selector list is pinned, so the colour case cannot be
    silently narrowed by a rule that escapes the filter."""
    selectors = [rule.selector for rule in section_rules()]

    assert selectors == list(SECTION_SELECTORS)


def test_the_appended_rules_carry_no_colour_literal_and_only_known_variables():
    """ER6: both halves, because either alone is empty.

    Half 2 -- "every `var()` names a `REPORT_ROLE_SOURCES` key" -- passes
    **vacuously** over the mock's hard-coded `rgba(221,209,182,.4)` separator,
    because a literal is not a `var()`. Half 1 alone permits `var(--gold)`.

    Half 2 is also a direction the existing suite never runs:
    `test_every_named_variable_is_actually_referenced_by_the_document` iterates
    the declared names and looks each one up in the body, so a reference to an
    *undefined* property is invisible to the whole suite -- which is the silent
    failure this case closes.

    *Fails if:* `--gold`, `--bg` or any other undefined property is ported, or
    the mock's `rgba()` separator is kept.
    """
    rules = section_rules()

    # Anti-vacuity: an empty rule list satisfies every loop below.
    assert len(rules) == len(SECTION_SELECTORS)

    offenders: list[str] = []
    for rule in rules:
        declarations = rule.declarations
        for literal in ("#", "rgb(", "rgba(", "hsl("):
            assert literal not in declarations, f"{rule.selector}: {declarations}"
        offenders.extend(
            f"{rule.selector}: --{name}"
            for name in re.findall(r"var\(--([\w-]+)\)", declarations)
            if name not in report.REPORT_ROLE_SOURCES
        )

    assert not offenders, offenders


def test_every_text_colour_in_the_appended_rules_avoids_bare_brand():
    """ER6 (c): the collision the mock cannot express.

    `FALLBACK_PALETTE` holds the same `#174b40` for `brand` and `brand-text`,
    so the mock renders identically either way. They diverge for a branded
    tenant, and `("brand", "card")` is absent from `REPORT_TEXT_PAIRS` while
    already recorded in `GRAPHICAL_PAIRS_BELOW_THREE` at 1.5338 and 1.2111 --
    so a verbatim port of `details.all>summary{color:var(--brand)}` ships
    summary text at ~1.2:1 with the whole suite green. Fills may keep `--brand`.
    """
    rules = section_rules()
    assert len(rules) == len(SECTION_SELECTORS)

    coloured = 0
    for rule in rules:
        for declaration in rule.declarations.split(";"):
            prop, _, value = declaration.partition(":")
            if prop.strip() == "color":
                coloured += 1
                assert value.strip() != "var(--brand)", rule.selector

    # Anti-vacuity: the loop above must actually have inspected some `color`.
    assert coloured >= 4
    declarations = {rule.selector: rule.declarations for rule in rules}
    assert "color:var(--brand-text)" in declarations["details.all>summary"].replace(
        " ", ""
    )


def test_the_summary_colour_pair_is_one_the_contrast_suite_measures():
    """ER6 (c), stated as the pair rather than as the excluded value.

    `details.all` paints `var(--card)` and its summary text `var(--brand-text)`,
    and `("brand-text", "card")` *is* in `REPORT_TEXT_PAIRS` -- so this use is
    measured rather than unmeasured, which is the point of the substitution.
    """
    declarations = {rule.selector: rule.declarations for rule in section_rules()}

    assert "background:var(--card)" in declarations["details.all"].replace(" ", "")
    assert "color:var(--brand-text)" in declarations["details.all>summary"].replace(
        " ", ""
    )


def test_the_new_print_rules_arrive_as_a_new_at_rule_block():
    """ER7: `shared_rule_pairs` emits one pair per at-rule as
    `[prelude, whole body]`, so editing the existing `@media print` block
    rewords a pinned pair and breaks additions-only. A brand-new block appends
    a new pair instead."""
    sheet = parse_css(report.CSS_BODY)
    print_blocks = [node for node in sheet.nodes if getattr(node, "prelude", None)]
    preludes = [node.prelude for node in print_blocks]

    assert preludes.count("@media print") == 2
    assert "details" not in print_blocks[preludes.index("@media print")].body


def test_the_card_scoped_none_rule_is_extended_rather_than_edited():
    """ER11: `.grp .none` is card-scoped, so inside the section the line would
    render as unstyled body text. The coverage arrives as an appended rule,
    because editing the existing one rewords a `shared_rule_pairs` pair."""
    declarations = {
        rule.selector: rule.declarations for rule in parse_css(report.CSS_BODY).rules
    }

    assert declarations[".grp .none"] == (
        "color:var(--muted); font-style:italic; font-size:8.5pt; margin:0;"
    )
    assert "font-style:italic" in declarations["details.ph .none"]
    assert "color:var(--muted)" in declarations["details.ph .none"]
