"""APRAS-114: the stage-detail column, its decoder, and the unchanged render.

`ProjectMilestone.detail_json` stores one stage of the contractor's schedule as
`{pct, start, leaves: [{name, pct, start, finish}]}`. Nothing in the
application writes it -- the writer is an operator script deliberately never
committed here -- so what this repository owns is the *contract*, and that is
what this module pins:

* every malformed payload decodes to "no detail", never to a partial read
  (`planned_to_date`'s rule, for its reason: a partially-read stage understates
  the work, and that is the number the síndico holds against the measurement);
* the two shapes that are valid rather than corrupt -- a leaf with null dates,
  and `leaves: []` -- decode;
* a real payload, extracted from the cached contractor schedule and committed
  as `tests/data/obras_stage_detail_fixture.json`, decodes through the **same**
  entry point as the guards above. Without that positive control, "malformed
  yields no detail" is satisfied by a decoder that always refuses;
* the rendered report is byte-identical for the all-NULL state every
  production row is in.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.services import project_report_service as report

DATA = Path(__file__).resolve().parent / "data"

#: The real payload, two stages keyed by milestone title. Derived from the
#: contractor's cached `.mpp` by the untracked operator script's own `read_mpp`
#: + `fronts`, projected to the four leaf keys. The `.mpp` sources and the
#: extraction script are not committed; this JSON is.
FIXTURE = DATA / "obras_stage_detail_fixture.json"

#: The rendered bytes of one page whose every milestone has `detail_json is
#: None`. See :func:`test_the_all_null_page_renders_the_committed_baseline`
#: for what this file does and does not guard, and for the command that
#: regenerates it.
BASELINE = DATA / "report_page_null_detail_baseline.html"

#: The frame of the same all-NULL page **as it stood before APRAS-113**: the
#: page text around the milestone-cards block, plus the milestone titles the
#: old block printed. See
#: :func:`test_the_all_null_frame_survives_the_card_rewrite` for what it
#: proves, why it exists instead of a diff claim, and the command that made it.
PRE113_FRAME = DATA / "report_page_pre113_frame.json"

#: The separator the operator's (never committed) sync tool writes between a
#: stage's parent and its own name. The pre-APRAS-113 card printed the whole
#: title, this glyph included; the post-APRAS-113 card splits on it and prints
#: it nowhere, which is what makes its presence in the artifact proof that the
#: artifact predates the change.
TITLE_SEPARATOR = " · "

GROUPS_OPEN = '<div class="groups">'

HYDRAULICS = "Instalações Hidraulicas — Térreo e Superior"
DEMOLITIONS = "Demolições — Térreo e Superior"

#: One leaf that is valid in every respect, so a case can vary exactly one key.
GOOD_LEAF = {
    "name": "REMOÇÃO DE PISO EXISTENTE",
    "pct": 95.0,
    "start": "2026-10-07",
    "finish": "2026-10-19",
}


def _naive(stamp: str) -> datetime:
    """A naive `datetime` from an ISO string.

    Every datetime column in this database is `TIMESTAMP WITHOUT TIME ZONE`
    and `clock.db_now()` writes naive UTC, so a pinned literal must be naive
    too. `datetime.fromisoformat` says that without the `DTZ001` suppression
    comment a bare `datetime(...)` constructor would need on each of the six
    literals below.
    """
    return datetime.fromisoformat(stamp)


def _payload(**overrides: object) -> dict[str, object]:
    """A valid stage payload with `overrides` applied."""
    return {"pct": 12.5, "start": "2026-10-16", "leaves": [dict(GOOD_LEAF)]} | overrides


# ---------------------------------------------------------------------------
# The positive control (ER4, ER10) -- first, because every rejection case
# below is worthless if the decoder cannot accept anything at all.
# ---------------------------------------------------------------------------


def test_a_valid_payload_decodes_to_typed_values():
    stage = report.decode_stage_detail(_payload())

    assert stage is not None
    assert stage.pct == 12.5
    assert stage.start == date(2026, 10, 16)
    assert len(stage.leaves) == 1
    assert stage.leaves[0].name == "REMOÇÃO DE PISO EXISTENTE"
    assert stage.leaves[0].pct == 95.0
    assert stage.leaves[0].start == date(2026, 10, 7)
    assert stage.leaves[0].finish == date(2026, 10, 19)


@pytest.mark.parametrize("title", [HYDRAULICS, DEMOLITIONS])
def test_the_real_fixture_reaches_the_same_entry_point(title: str):
    """The committed fixture decodes through `decode_stage_detail` itself.

    `json.load` produces a `dict`, exactly as the JSON column does, and the
    decoder takes `object` -- so this control exercises the *same* entry point
    as the rejection cases rather than a string-parsing wrapper beside it
    (ER10).
    """
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))[title]

    assert report.decode_stage_detail(payload) is not None


def test_the_fixture_is_keyed_by_exactly_the_two_real_milestone_titles():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert set(fixture) == {HYDRAULICS, DEMOLITIONS}


def test_the_hydraulics_stage_decodes_to_its_measured_values():
    """The comma-rich stage. Its `pct` is exactly `0.0`, which is why the
    second stage below is also required: `0.0` cannot distinguish a decoded
    value from a default."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))[HYDRAULICS]

    stage = report.decode_stage_detail(payload)

    assert stage is not None
    assert stage.pct == 0.0
    assert stage.start == date(2026, 10, 16)
    assert len(stage.leaves) == 5
    assert [leaf.name for leaf in stage.leaves] == [
        "REALOCAÇÃO DE PONTOS DE ESGOTO PARA NOVO PLANO DE LAYOUT- INCLUSO NOVO BANHEIRO DE USO FEMININO E SALA 4- PAVIMENTO SUPERIOR/ LAVABO MASCULINO, FEMININO- COZINHA, WC E WC PCD- PAVIMENTO TÉRREO",
        "REALOCAÇÃO DE PONTOS DE AGUA FRIA PARA NOVO PLANO DE LAYOUT- INCLUSO NOVO BANHEIRO DE USO FEMININO E SALA 4- PAVIMENTO SUPERIOR/ LAVABO MASCULINO, FEMININO- COZINHA, WC E WC PCD- PAVIMENTO TÉRREO",
        "ESCAVAÇÃO, PREPARAÇÃO DE BASE E FECHAMENTO DE CAIXA DE PASSAGEM DE ESGOTO EM ALVENARIA - INCLUSO TAMPA DE CONCRETO ARMADO- SAIDA COZINHA E SANITARIOS DO PAVIMENTO SUPERIOR E TÉRREO",
        "INSTALAÇÃO DE LOUÇAS E METAIS NAS AREAS MOLHADAS- TORNEIRAS, VASOS, CHUVEIROS, LAVATÓRIOS COM COLUNA, TANQUES E ACESSÓRIOS DE COMPOSIÇÃO",
        "EXECUÇÃO DE INFRA DE ENCAMINHAMENTO DA REDE DE CAPTAÇÃO DE AGUAS PLUVIAIS DAS NOVAS INSTALAÇÕES- TUBULAÇÃO E CAIXAS DE PASSAGEM",
    ]
    # 4 of the 5 names carry a comma, which is what makes the `description`
    # column (leaf names joined with `", "`) unsplittable and is why this
    # payload is stored rather than parsed back out of it.
    assert sum(1 for leaf in stage.leaves if "," in leaf.name) == 4


def test_the_demolitions_stage_decodes_its_non_zero_progress():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))[DEMOLITIONS]

    stage = report.decode_stage_detail(payload)

    assert stage is not None
    assert stage.pct == pytest.approx(49.56, abs=0.01)
    assert stage.start == date(2026, 9, 25)
    assert len(stage.leaves) == 8
    assert [leaf.name for leaf in stage.leaves] == [
        "DEMOLIÇÃO DE PAREDES EM ALVENARIA CONFORME DEMARCAÇÃO DE PROJETO",
        "REMOÇÃO DE PISO EXISTENTE PISO TÉRREO E PISO SUPERIOR AREAS SECAS E AREAS MOLHADAS",
        "REMOÇÃO DE REVESTIMENTO EXISTENTE PISO TÉRREO E PISO SUPERIOR AREAS MOLHADAS",
        "DESMONTAGEM DE LOUÇAS E METAIS EXISTENTES",
        "REMOÇÃO DE ESQUADRIAS EXISTENTES",
        "DESMONTAGEM DE ESTRUTURA EXISTENTE NA LATERAL DA FACHADA (TOLDO METALICO)",
        "REMOÇÃO DE PEDRA DE GRANITO DA ESCADA PRINCIPAL DE ACESSO AO PAVIMENTO SUPERIOR",
        "DESMONTAGEM DE MAQUINAS DE AR CONDICIONADO E INFRAS EXISTENTES",
    ]


# ---------------------------------------------------------------------------
# Rejection (ER3): one named case per unusable input, each "no detail"
# ---------------------------------------------------------------------------


def test_none_is_no_detail():
    assert report.decode_stage_detail(None) is None


def test_an_empty_object_is_no_detail():
    assert report.decode_stage_detail({}) is None


@pytest.mark.parametrize(
    "payload",
    [[], ["pct"], "pct", 12.5, True],
    ids=["empty-list", "list", "string", "number", "bool"],
)
def test_a_non_object_payload_is_no_detail(payload: object):
    assert report.decode_stage_detail(payload) is None


@pytest.mark.parametrize(
    "pct",
    [None, "12.5", "", -0.5, 100.5, [12.5], {}],
    ids=[
        "none",
        "numeric-string",
        "empty-string",
        "negative",
        "over-100",
        "list",
        "dict",
    ],
)
def test_an_unusable_stage_pct_is_no_detail(pct: object):
    assert report.decode_stage_detail(_payload(pct=pct)) is None


def test_a_missing_stage_pct_is_no_detail():
    assert report.decode_stage_detail({"start": "2026-10-16", "leaves": []}) is None


def test_a_boolean_stage_pct_is_no_detail():
    """Pydantic's *lax* mode coerces `True` to `1.0`. `planned_to_date` rejects
    booleans and so must this decoder, which is what `Field(strict=True)` buys
    and what this case guards against a later relaxation."""
    assert report.decode_stage_detail(_payload(pct=True)) is None


def test_an_integer_stage_pct_decodes():
    """`0` and `12` are the ints the producer emits for a whole percentage;
    field-level strictness on a plain `float` accepts them (measured on
    pydantic 2.13.3) and must keep doing so."""
    stage = report.decode_stage_detail(_payload(pct=0))

    assert stage is not None
    assert stage.pct == 0.0


def test_a_missing_stage_start_is_no_detail():
    assert report.decode_stage_detail({"pct": 12.5, "leaves": []}) is None


@pytest.mark.parametrize(
    "start",
    [None, "", "16/10/2026", "2026-13-40", "not-a-date"],
    ids=["none", "empty", "br-format", "impossible", "text"],
)
def test_an_unparseable_stage_start_is_no_detail(start: object):
    assert report.decode_stage_detail(_payload(start=start)) is None


@pytest.mark.parametrize(
    "leaves",
    [None, "leaf", 3, {"name": "x"}],
    ids=["none", "string", "number", "dict"],
)
def test_a_non_list_leaves_is_no_detail(leaves: object):
    assert report.decode_stage_detail(_payload(leaves=leaves)) is None


def test_an_absent_leaves_key_is_no_detail():
    """`leaves` is required, exactly as `pct` and the stage `start` are: the
    producer always emits it, so its absence means the payload did not come
    from the producer. `payload.get("leaves", [])` is the wrong reading."""
    assert report.decode_stage_detail({"pct": 12.5, "start": "2026-10-16"}) is None


@pytest.mark.parametrize(
    "name",
    [None, 3, True, "", ["x"], {"pt": "x"}],
    ids=["none", "number", "bool", "empty", "list", "dict"],
)
def test_a_leaf_with_a_non_string_name_is_no_detail(name: object):
    payload = _payload(leaves=[dict(GOOD_LEAF) | {"name": name}])

    assert report.decode_stage_detail(payload) is None


def test_a_missing_leaf_name_is_no_detail():
    leaf = {k: v for k, v in GOOD_LEAF.items() if k != "name"}

    assert report.decode_stage_detail(_payload(leaves=[leaf])) is None


@pytest.mark.parametrize("field", ["start", "finish"])
@pytest.mark.parametrize(
    "value",
    ["", "07/10/2026", "2026-13-40", "soon"],
    ids=["empty", "br", "impossible", "text"],
)
def test_a_leaf_with_a_present_but_unparseable_date_is_no_detail(
    field: str, value: str
):
    payload = _payload(leaves=[dict(GOOD_LEAF) | {field: value}])

    assert report.decode_stage_detail(payload) is None


@pytest.mark.parametrize(
    "pct",
    [None, "95", True, -1, 101],
    ids=["none", "str", "bool", "negative", "over-100"],
)
def test_a_leaf_with_an_unusable_pct_is_no_detail(pct: object):
    payload = _payload(leaves=[dict(GOOD_LEAF) | {"pct": pct}])

    assert report.decode_stage_detail(payload) is None


def test_one_bad_leaf_invalidates_the_whole_stage_rather_than_being_dropped():
    """No partial read: a stage missing one of its services understates the
    work, and the report would show a number nobody can reconcile."""
    payload = _payload(leaves=[dict(GOOD_LEAF), {"name": 7, "pct": 0.0}])

    assert report.decode_stage_detail(payload) is None


def test_a_non_dict_leaf_is_no_detail():
    assert report.decode_stage_detail(_payload(leaves=["DEMOLIÇÃO"])) is None


# ---------------------------------------------------------------------------
# Accepted edge cases (ER8, ER9). Neither fixture stage carries a null leaf
# date or an empty `leaves` list, so these payloads are hand-written.
# ---------------------------------------------------------------------------


def test_a_leaf_with_null_dates_decodes_with_both_fields_none():
    """The contractor's schedule genuinely lacks dates on some services and
    the producer writes `null` there. Only a *present* unparseable value is
    malformed."""
    leaf = dict(GOOD_LEAF) | {"start": None, "finish": None}

    stage = report.decode_stage_detail(_payload(leaves=[leaf]))

    assert stage is not None
    assert len(stage.leaves) == 1
    assert stage.leaves[0].start is None
    assert stage.leaves[0].finish is None
    assert stage.leaves[0].name == "REMOÇÃO DE PISO EXISTENTE"
    assert stage.leaves[0].pct == 95.0


def test_an_empty_leaves_list_decodes_as_a_stage_with_zero_leaves():
    """A stage that is its own leaf is real; decoding it as "no detail" would
    silently drop it from the report. Note the asymmetry with
    :func:`test_an_absent_leaves_key_is_no_detail`, which is deliberate."""
    stage = report.decode_stage_detail(_payload(leaves=[]))

    assert stage is not None
    assert stage.pct == 12.5
    assert stage.start == date(2026, 10, 16)
    assert stage.leaves == ()


def test_a_leaf_carrying_the_producers_extra_keys_decodes_identically():
    """The producer's leaf dicts also carry `id`, `lvl`, `summary` and `dur`.
    If it dumps them verbatim those keys reach the column, so tolerating them
    is a correctness requirement, not politeness."""
    verbose = dict(GOOD_LEAF) | {"id": 41, "lvl": 5, "summary": False, "dur": 9.0}

    with_extras = report.decode_stage_detail(_payload(leaves=[verbose]))
    without = report.decode_stage_detail(_payload(leaves=[dict(GOOD_LEAF)]))

    assert with_extras is not None
    assert with_extras == without


def test_unknown_keys_on_the_stage_itself_are_ignored():
    """`fronts()` stage dicts also carry `name`, `top` and `finish`, which the
    milestone's own `title` and `due_date` columns already hold."""
    noisy = _payload(name="Demolições", top="Sede Social", finish="2026-10-20")

    decoded = report.decode_stage_detail(noisy)

    # Guarded like its ER9 sibling above: without this, a decoder that refuses
    # everything satisfies the comparison below as `None == None`.
    assert decoded is not None
    assert decoded == report.decode_stage_detail(_payload())


# ---------------------------------------------------------------------------
# The unchanged render (ER6)
# ---------------------------------------------------------------------------

#: Every month is in the past. `planned_to_date` does read the clock, so this
#: is not clock-independence -- it is forward stability: the last past month
#: stays the last past month as time advances, so the bar is fixed from now on.
#: A future-dated month here would reintroduce the drift this avoids.
PLANNED_CURVE = [
    {"month": "2020-01", "pct": 8.0},
    {"month": "2020-02", "pct": 31.5},
    {"month": "2020-03", "pct": 64.0},
]

#: Pinned, not defaulted: `generated_at` reaches the masthead and the footer.
#: Built from an ISO string rather than `datetime(...)` so the literal is
#: naive -- matching the naive `TIMESTAMP WITHOUT TIME ZONE` columns this
#: project uses everywhere -- with no lint suppression on any of the literals.
GENERATED_AT = _naive("2026-09-26T14:30:00")

#: Every title carries the producer's `" · "` separator (APRAS-113), because
#: that is the shape the operator's sync tool writes for a stage under a parent
#: and it is the shape the card now splits. It is also what makes
#: :data:`PRE113_FRAME` falsifiable: a regeneration of that artifact from the
#: *post*-change renderer would drop the glyph from every entry.
MILESTONE_TITLES = (
    "Demolições · Térreo e Superior",
    "Instalações Hidraulicas · Térreo e Superior",
    "Estruturas Metalicas · Alvenaria e Vedações",
    "Acabamentos · Pintura Geral",
)


def null_detail_project() -> ConstructionProject:
    """The page the baseline pins: fully deterministic, every stage NULL.

    Nothing here may fall back to `clock.db_now()`. `updated_at` and every
    bulletin's `created_at` both reach the rendered bytes -- the masthead
    prints `max(update.created_at) or project.updated_at` and each bulletin
    prints its own date -- so an unpinned one makes the baseline pass on the
    day it is written and fail at the next UTC date change.

    The fixture also avoids ties, because two orderings are truncated: the
    bulletins are sorted by `created_at` and cut to three, and the completed
    milestones are sorted by `(completion_date, display_order)` and cut to
    three. Two rows sharing a sort key would order arbitrarily and make the
    byte comparison flaky rather than wrong, so every bulletin has a distinct
    `created_at` and every milestone a distinct `display_order`.
    """
    statuses = (
        MilestoneStatus.DONE,
        MilestoneStatus.IN_PROGRESS,
        MilestoneStatus.IN_PROGRESS,
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
            created_at=_naive("2026-09-01T08:00:00"),
            updated_at=_naive("2026-09-02T08:00:00"),
            detail_json=None,
        )
        for order, (title, status) in enumerate(
            zip(MILESTONE_TITLES, statuses, strict=True), start=1
        )
    ]
    updates = [
        ProjectUpdate(
            title=f"Boletim {n}",
            content=f"Frente {n} em andamento.",
            photos_json=None,
            cost_impact=Decimal("0.00"),
            created_at=_naive(f"2026-09-{20 + n}T09:00:00"),
        )
        for n in (1, 2)
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
        created_at=_naive("2026-09-01T07:00:00"),
        updated_at=_naive("2026-09-05T07:00:00"),
        milestones=milestones,
        updates=updates,
    )


def render_null_detail_page() -> str:
    """The page bytes the baseline holds, rendered by the current module."""
    return report._page_html(null_detail_project(), 1, None, None, GENERATED_AT)


def test_the_all_null_page_renders_the_committed_baseline():
    """`tests/data/report_page_null_detail_baseline.html`, byte for byte.

    **What this file guards:** from the next commit onwards, any change to a
    rendering fragment that alters the all-NULL page fails this test. That is
    its whole job, and it is why APRAS-113 and APRAS-115 inherit a tripwire
    instead of a promise.

    **What it does not guard:** that these bytes were produced by the module
    as it stood *before* APRAS-114. Nothing in the repository can check when a
    human ran a command. What makes the baseline meaningful for APRAS-114 is
    that task's diff-checkable property -- no rendering code path changed, the
    decoder is a pure addition -- not the order in which the file was written.

    The stylesheet is pinned separately and independently by
    `tests/data/report_css_shared_baseline.json`.

    After a deliberate rendering change, regenerate rather than hand-patch,
    from `backend/`, and review the diff:

        uv run python -c "
        from tests.test_project_stage_detail import BASELINE, render_null_detail_page
        BASELINE.write_text(render_null_detail_page(), encoding='utf-8')
        "
    """
    baseline = BASELINE.read_text(encoding="utf-8")

    # Anti-vacuity: this case must not be able to pass by comparing two empty
    # strings, nor by silently exercising the populated state.
    assert baseline
    assert "Etapas da obra" in baseline
    # Both halves, not the whole title: since APRAS-113 the card splits on
    # `TITLE_SEPARATOR` and prints the glyph nowhere.
    for title in MILESTONE_TITLES:
        for half in title.split(TITLE_SEPARATOR):
            assert half in baseline
    project = null_detail_project()
    assert project.milestones
    assert all(m.detail_json is None for m in project.milestones)

    assert render_null_detail_page() == baseline


# ---------------------------------------------------------------------------
# The frame around the rewritten cards (APRAS-113 ER9/ER11)
# ---------------------------------------------------------------------------


def split_div_block(page: str, marker: str) -> tuple[str, str, str]:
    """`(prefix, block, suffix)` around the `<div>` that `marker` opens.

    The block is delimited by matching `<div` openings against `</div>`
    closings from `marker` onwards, so the returned block is the whole element
    however deeply it nests. A naive `split("</div>")` stops at the first inner
    `<div>` -- and once an `<li>` nests a `<div class="ttl">` it stops one level
    earlier still -- which is exactly the string surgery APRAS-113 replaces.

    Raises rather than returning a plausible triple when the element is absent
    or unbalanced: a helper that silently yields `("", "", page)` would make
    every assertion built on it pass over a page with no such element at all.
    """
    start = page.find(marker)
    if start == -1:
        raise AssertionError(f"no {marker} in the rendered page")
    depth = 0
    index = start
    while index < len(page):
        opening = page.find("<div", index)
        closing = page.find("</div>", index)
        if closing == -1:
            break
        if opening != -1 and opening < closing:
            depth += 1
            index = opening + len("<div")
            continue
        depth -= 1
        index = closing + len("</div>")
        if depth == 0:
            return page[:start], page[start:index], page[index:]
    raise AssertionError(f"the element {marker} opens is not closed")


def split_groups_block(page: str) -> tuple[str, str, str]:
    """`(prefix, groups_block, suffix)` around the milestone-cards block."""
    return split_div_block(page, GROUPS_OPEN)


def test_the_all_null_frame_survives_the_card_rewrite():
    """APRAS-113 ER9/ER11: the page around the cards did not move, and the
    all-NULL card lost no row text.

    `tests/data/report_page_null_detail_baseline.html` is a single 4 KiB line
    with no trailing newline, so git renders its regeneration as a whole-file
    replacement: there are no hunks, and "the change is confined to the cards"
    is not a claim that diff can express. This case expresses it instead, out
    of an artifact captured from the **pre**-APRAS-113 renderer and committed
    beside it.

    Two halves:

    (a) the prefix and the suffix are byte-equal to the pre-change ones -- the
        masthead, the hero, the bar, the budget block, the bulletins and the
        footer are untouched;
    (b) every title the old block printed still has *both* halves of its
        `" · "` split inside the new block. Not the whole title: the separator
        is now the boundary between the kicker and the name and is printed
        nowhere, so a whole-title assertion here would be a requirement that
        the change had not happened.

    The artifact is trustworthy only if it predates the renderer change, and
    the assertion that makes that checkable is the `TITLE_SEPARATOR` one: the
    post-change card never emits that glyph, so a regeneration from the new
    renderer would leave `titles` entries without it and fail here. Without
    that line this case is one careless regeneration away from comparing the
    new page to itself.

    It was generated, **before** `project_report_service.py` was edited and
    from the same seed this module's baseline uses, by running from `backend/`:

        uv run python -c "
        import json, re
        from tests.test_project_stage_detail import (
            PRE113_FRAME, render_null_detail_page, split_groups_block)
        prefix, block, suffix = split_groups_block(render_null_detail_page())
        PRE113_FRAME.write_text(json.dumps({
            'prefix': prefix,
            'suffix': suffix,
            'titles': re.findall(r'<li>(.*?)</li>', block),
        }, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        "

    That command is not re-runnable after the change and is not meant to be:
    the new block emits no bare `<li>{title}</li>`, so it would capture an
    empty `titles` list. It is recorded so the artifact's provenance is
    readable, not so it can be refreshed.
    """
    frame = json.loads(PRE113_FRAME.read_text(encoding="utf-8"))

    # Anti-vacuity, and the provenance check: an artifact regenerated from the
    # post-change renderer has no titles at all, and one regenerated from a
    # renderer that had already dropped the glyph would still be caught here.
    assert len(frame["titles"]) == len(MILESTONE_TITLES)
    for title in frame["titles"]:
        assert TITLE_SEPARATOR in title, title

    prefix, block, suffix = split_groups_block(render_null_detail_page())

    assert prefix == frame["prefix"]
    assert suffix == frame["suffix"]
    # The rewritten card must not be able to satisfy (b) by being the old card.
    assert TITLE_SEPARATOR not in block
    for title in frame["titles"]:
        parent, name = title.split(TITLE_SEPARATOR, 1)
        assert parent in block, parent
        assert name in block, name
