"""APRAS-117: every string the obras report prints, pinned against injection.

`project_report_service` renders a **public** page -- `/c/<slug>/obras`, no
login -- out of data a third party supplies: the contractor's Microsoft
Project schedule, parsed by `backend/scripts/sync_obras_from_drive.py` and
written to the database with nothing in between sanitising it. The whole
defence is the `_e()` call at each interpolation.

**The code was already correct. Nothing protected it.** Replacing `{_e(name)}`
with `{name}` in `_stage_item_html` left the entire backend suite green, this
one included before this module existed: none of the committed fixture names
carries `<`, `>`, `&` or a quote, so even `assert "<script" not in section`
had no `<` to find either way. The escapes were unpinned, not absent.

Three mechanisms, in the order they run:

1. :func:`test_the_module_escapes_or_provably_cannot_need_to` audits the
   module's **whole interpolation inventory**, derived from its AST by
   :mod:`tests.interpolation_audit`. A hand-written list of the call sites
   that ought to escape goes stale the first time someone adds a field --
   the new field is simply not in the list. This one fails on a new
   interpolation that prints a stored value without `_e()`, whoever adds it,
   and :func:`test_the_audit_catches_a_newly_added_unescaped_field` proves
   that on a synthetic module rather than asserting it in prose.
2. :func:`test_removing_any_single_escape_is_caught` re-runs the audit once
   per `_e()` call in the module -- **20 of them**, enumerated, not listed --
   each time with that one call stripped, and requires the audit to report a
   site it did not report before. This is expected result 1 discharged
   mechanically for every site at once.
3. the runtime cases below push a string carrying `<script>`, `&` and a
   double quote through each renderer and assert the **escaped** form is
   present *and* the raw form is absent. Both halves: an absence-only
   assertion is equally satisfied by a renderer that drops the value, which
   is how a passing test comes to prove nothing.

**Every runtime case names its own marker value, through
:func:`assert_escaped_and_never_raw`, and that is structural rather than
stylistic.** The one case that did not --
:func:`test_the_stage_detail_section_escapes_the_contractors_leaf_name` --
asserted nothing: the hostile *stage title* rendered two lines away answered
all five of its clauses, so replacing `leaf.name` with a constant, the
contractor's field gone from the document entirely, left it green. It was the
thirteenth assert-nothing test in this repository.

That is why the mutation campaign behind this module runs **two** mutations
per site, not one:

* *drop the escape* -- `_e(x)` becomes `x`. Caught statically for all 20
  sites by mechanism 2, and at runtime for 19; the twentieth is the logo URL,
  below.
* *drop the field* -- `_e(x)` becomes `_e("servico")`. **Escape-removal
  structurally cannot see this class of defect**, because the escape is still
  there and the audit stays green by construction; only a runtime case that
  names the field can. All 20 are caught now, the leaf name included.

Every assertion here is phrased for **under**-escaping. The cautionary shape
this repository keeps producing is the case now called
`test_a_real_comma_rich_leaf_name_is_not_over_escaped` in
`test_project_report_stage_detail_section.py`: under its previous name it
read as escaping coverage while guarding over-escaping only, and read as
coverage it stops the next person looking. It is renamed rather than deleted
-- over-escaping is worth a case, it is just not this one's subject. One
assertion here is deliberately *not* about `_e` at all --
:func:`test_the_logo_url_is_percent_encoded_before_it_is_escaped` -- because
that site's real defence is `urls.public_tenant_logo_url`'s `quote()` and
saying otherwise would repeat exactly that mistake.

The audit's own pessimism is pinned too, by three synthetic modules rather
than by prose: two false-`SAFE` shapes shipped past the single synthetic case
this module opened with -- a helper that `yield`s, whose returns were
vacuously safe, and a local shadowing a module-scope name -- so each rule now
has a case that fails when its rule is removed.

`tests/data/obras_stage_detail_fixture.json` is a real extract pinned by
APRAS-114 against literal names and counts, so, following APRAS-115, the
hostile strings live here and never touch it.
"""

from __future__ import annotations

import ast
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from app.core.branding import InvalidBrandThemeError
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.tenant import Tenant
from app.models.user import User
from app.services import project_report_service as report
from tests.interpolation_audit import (
    ESCAPED,
    RAW,
    SAFE,
    audit,
    escape_call_sites,
    escape_calls_at_interpolations,
    without_escape,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

SOURCE = Path(report.__file__).read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

# ---------------------------------------------------------------------------
# The declared exemptions
# ---------------------------------------------------------------------------

#: The interpolations the audit reports as `RAW` **by design**, each with the
#: reason and the test that pins it. The audit asserts this mapping is exact:
#: an entry that no longer matches a real interpolation fails just as loudly
#: as an unescaped new field, so the list cannot rot into a suppression file.
#:
#: All four are the generated `<style>` block. Its values never pass through
#: `_e` and must not: `html.escape` inside `<style>` would be *wrong* -- the
#: browser does not decode entities there, so escaping an `&` would corrupt
#: the declaration rather than defuse it.
#:
#: What defends that block is `app.core.branding`, and on two independent
#: counts rather than one. `normalize_brand_theme` rejects anything that is
#: not a hex colour -- but even if that validation were bypassed, `_emit`
#: rebuilds **every** value through `format_oklch`, which formats three floats
#: under a `:.2f` spec, so no stored byte reaches `<style>` at all. Pinned by
#: :func:`test_a_hostile_brand_theme_never_reaches_the_style_block`.
BRANDING_REASON = (
    "CSS, not HTML: app.core.branding rebuilds every value through "
    "format_oklch under a :.2f spec, so no stored byte survives into <style> "
    "-- and escaping would corrupt the declaration instead of defusing it"
)
DECLARED_WITHOUT_ESCAPE: dict[str, str] = {
    "_stylesheet:name": BRANDING_REASON,
    "_stylesheet:palette[name]": BRANDING_REASON,
    "_stylesheet:declarations": BRANDING_REASON,
    "render_report_html:_stylesheet(getattr(tenant, 'brand_theme', None))": (
        BRANDING_REASON
    ),
}


# ---------------------------------------------------------------------------
# The hostile fixture -- this module's own, never the committed extract
# ---------------------------------------------------------------------------


def hostile(marker: str) -> str:
    """A string carrying all three characters `html.escape` exists for.

    `<` and `>` open a tag, `&` opens an entity, and `" onerror=x` closes an
    attribute and starts a handler -- the shape that matters for the values
    that land inside `src="..."`. The marker makes each field's value
    distinguishable, so a renderer that prints the *wrong* field fails
    rather than passes on a neighbour's value.

    No parentheses: `_KIND_SUFFIX` splits a trailing `(...)` off a project
    title, so a value carrying one would be split rather than printed whole,
    and `alert(1)` would make this fixture test the splitter instead.
    """
    return f'<script>alert</script> & "{marker}" onerror=x'


HOSTILE_STAGE_PARENT = hostile("stage-parent")
HOSTILE_STAGE_NAME = hostile("stage-name")
HOSTILE_NEXT_PARENT = hostile("next-parent")
HOSTILE_NEXT_NAME = hostile("next-name")
HOSTILE_LEAF_NAME = hostile("leaf")
HOSTILE_PROJECT_TITLE = hostile("project-title")
HOSTILE_PROJECT_KIND = hostile("project-kind")
HOSTILE_DESCRIPTION = hostile("description")
HOSTILE_STATUS = hostile("status")
HOSTILE_COVER_URL = f"https://drive.example/{hostile('cover')}"
HOSTILE_PHOTO_URL = f"https://drive.example/{hostile('photo')}"
HOSTILE_UPDATE_TITLE = hostile("update-title")
HOSTILE_UPDATE_CONTENT = hostile("update-content")
HOSTILE_TENANT_NAME = hostile("tenant")
HOSTILE_TENANT_SLUG = hostile("slug")
HOSTILE_USER_NAME = hostile("user")

GENERATED_AT = datetime.fromisoformat("2026-09-26T14:30:00")

#: One decoded stage payload, so the `<details>` section renders too.
HOSTILE_PAYLOAD: dict[str, object] = {
    "pct": 42.0,
    "start": "2026-09-21",
    "leaves": [
        {
            "name": HOSTILE_LEAF_NAME,
            "pct": 40.0,
            "start": "2026-09-23",
            "finish": "2026-09-24",
        }
    ],
}


#: A stage with a date and no serviços: enough for `_next_steps_html` to
#: bucket the row, which is what routes it through `_date_group_html`.
DATED_NEXT_STEP_PAYLOAD: dict[str, object] = {
    "pct": 0.0,
    "start": "2026-11-02",
    "leaves": [],
}


def hostile_project() -> ConstructionProject:
    """One obra whose every stored string is hostile, built fresh per call.

    Three milestone rows, one per card, because the cards select by status and
    a single row would leave two renderers -- `_stage_item_html` and
    `_date_group_html` -- unexercised while the test still passed.
    """
    stage_title = f"{HOSTILE_STAGE_PARENT} · {HOSTILE_STAGE_NAME}"
    next_title = f"{HOSTILE_NEXT_PARENT} · {HOSTILE_NEXT_NAME}"
    milestones = [
        ProjectMilestone(
            title=stage_title,
            description="Serviço A",
            status=MilestoneStatus.DONE,
            display_order=1,
            completion_date=date(2026, 9, 11),
            created_at=datetime.fromisoformat("2026-09-01T08:00:00"),
            updated_at=datetime.fromisoformat("2026-09-02T08:00:00"),
            detail_json=HOSTILE_PAYLOAD,
        ),
        ProjectMilestone(
            title=stage_title,
            description="Serviço B",
            status=MilestoneStatus.IN_PROGRESS,
            display_order=2,
            created_at=datetime.fromisoformat("2026-09-01T08:00:00"),
            updated_at=datetime.fromisoformat("2026-09-02T08:00:00"),
            detail_json=None,
        ),
        ProjectMilestone(
            title=next_title,
            description="Serviço C",
            status=MilestoneStatus.NEXT_STEPS,
            display_order=3,
            created_at=datetime.fromisoformat("2026-09-01T08:00:00"),
            updated_at=datetime.fromisoformat("2026-09-02T08:00:00"),
            # **Datable on purpose.** `_next_steps_html` buckets a row by its
            # decoded `start`; a row with no payload falls through to
            # `_stage_items_html` instead, and with `detail_json=None` here
            # both escapes of `_date_group_html` went unexercised while the
            # case that names them still passed.
            detail_json=DATED_NEXT_STEP_PAYLOAD,
        ),
    ]
    project = ConstructionProject(
        title=f"{HOSTILE_PROJECT_TITLE} ({HOSTILE_PROJECT_KIND})",
        description=HOSTILE_DESCRIPTION,
        status=ProjectStatus.IN_PROGRESS,
        physical_progress_pct=Decimal("42.50"),
        total_budget=Decimal("480000.00"),
        executed_budget=Decimal("204000.00"),
        start_date=date(2026, 9, 25),
        estimated_completion_date=date(2027, 3, 31),
        cover_photo_url=HOSTILE_COVER_URL,
        planned_progress_json=None,
        created_at=datetime.fromisoformat("2026-09-01T07:00:00"),
        updated_at=datetime.fromisoformat("2026-09-05T07:00:00"),
        milestones=milestones,
        updates=[
            ProjectUpdate(
                title=HOSTILE_UPDATE_TITLE,
                content=HOSTILE_UPDATE_CONTENT,
                photos_json=json.dumps([HOSTILE_PHOTO_URL]),
                cost_impact=Decimal("0.00"),
                created_at=datetime.fromisoformat("2026-09-21T09:00:00"),
            )
        ],
    )
    # Assigned after construction on purpose: it is the *unknown* status that
    # reaches the pill, through `PROJECT_STATUS_LABELS.get(..., str(status))`.
    project.status = HOSTILE_STATUS
    return project


def hostile_tenant() -> Tenant:
    """A condominium whose name and slug are hostile and which has a logo."""
    return Tenant(
        name=HOSTILE_TENANT_NAME,
        slug=HOSTILE_TENANT_SLUG,
        logo_url="https://storage.example/logo.png",
    )


def hostile_document() -> str:
    """One whole `div.page`: masthead, hero, stages, budget, bulletins, foot.

    `_page_html` is the last function above `render_report_html` that needs no
    database session, and it reaches every renderer this module audits except
    the `<title>` and the `<style>`, which have their own cases.
    """
    return report._page_html(
        hostile_project(),
        1,
        hostile_tenant(),
        User(full_name=HOSTILE_USER_NAME),
        GENERATED_AT,
    )


def assert_escaped_and_never_raw(
    document: str,
    value: str,
    site: str,
    *,
    transform: Callable[[str], str] | None = None,
) -> None:
    """``value``'s escaped form is present **and** its raw form is absent.

    Both halves, always. The absence alone is satisfied by a renderer that
    dropped the field, and the presence alone by one that prints it twice --
    once escaped, once not.

    **Every runtime case in this module goes through here**, and that is the
    point rather than tidiness: the one case that did not
    (`..._escapes_the_contractors_leaf_name`) never named its own marker
    value, so all five of its assertions were answered by the neighbouring
    renderer's hostile stage title and replacing the leaf name with a
    constant left it green -- the thirteenth assert-nothing test here.

    ``transform`` is the renderer's own pass over the value before it escapes
    it: `_stage_leaf_html` title-cases a leaf name first. It is applied to
    **both** halves, and the absence half is the reason it has to be. A
    title-cased string is not equal to its SHOUTING original, so
    `HOSTILE_LEAF_NAME not in document` stays true even with the escape gone;
    only the cased form can fail.
    """
    rendered = value if transform is None else transform(value)
    assert report._e(rendered) in document, f"{site}: the escaped form is missing"
    assert rendered not in document, f"{site}: the raw string reached the document"
    assert value not in document, f"{site}: the untransformed raw string reached it"


# ---------------------------------------------------------------------------
# 1 -- the inventory audit (ER1, ER3)
# ---------------------------------------------------------------------------


def test_the_audit_sees_the_whole_module_and_not_a_handful():
    """Anti-vacuity for every case below: the enumeration is not empty.

    Each later case is a statement about the set the audit returns, and an
    audit that walked nothing satisfies all of them. This pins the shape of
    the inventory instead: three figures, and one named site of each verdict.

    *Fails if:* the AST walk stops finding f-strings -- a renamed module, a
    renderer moved out of module scope, a parse the audit silently swallows.
    """
    inventory = audit(TREE)
    escaped = [item for item in inventory if item.verdict == ESCAPED]

    assert len(inventory) >= 100, "the report is built from far more f-strings"
    assert len(escaped) >= 15
    # The real relation, both counts derived independently: an `ESCAPED`
    # verdict is exactly an `_e()` that is a `{...}`'s whole expression. The
    # module holds more `_e()` calls than that -- inside a `join`'s generator,
    # or assigned to a local interpolated later -- so `escape_call_sites` is
    # strictly larger, and asserting `16 <= 20` would have claimed nothing.
    assert len(escaped) == len(escape_calls_at_interpolations(TREE))
    assert len(escaped) < len(escape_call_sites(TREE))

    sites = {item.site: item.verdict for item in inventory}
    assert sites["_stage_item_html:_e(name)"] == ESCAPED
    assert sites["_hero_html:_e(project.description)"] == ESCAPED
    assert sites["_updates_html:_e(update.title)"] == ESCAPED


def test_the_module_escapes_or_provably_cannot_need_to():
    """ER3: no interpolation prints a stored string without `_e()`.

    The inventory comes from the AST, so a field added next year is audited
    the moment it is interpolated -- there is no list to forget to update.
    The only `RAW` verdicts allowed are :data:`DECLARED_WITHOUT_ESCAPE`, and
    the mapping is checked **exactly**: a declaration whose interpolation no
    longer exists fails too, so the exemptions cannot outlive their reasons.

    *Fails if:* any `_e()` is dropped, or a new interpolation prints a value
    the audit cannot prove is non-text.
    """
    raw = {item.site: item for item in audit(TREE) if item.verdict == RAW}

    unexpected = [
        str(item) for site, item in raw.items() if site not in DECLARED_WITHOUT_ESCAPE
    ]
    assert not unexpected, "unescaped interpolation of a stored value:\n" + "\n".join(
        unexpected
    )
    stale = set(DECLARED_WITHOUT_ESCAPE) - set(raw)
    assert not stale, f"declared exemptions that no longer match anything: {stale}"


def test_the_audit_catches_a_newly_added_unescaped_field():
    """ER3/ER7, shape 1 of 3: a plain attribute read.

    A synthetic module in the shape of the real one -- an escaper, a private
    renderer, a field read off a model. The audit must call the unescaped
    field `RAW` and the escaped one `ESCAPED`; without this, "the audit
    reports nothing" and "there is nothing to report" are indistinguishable.

    One shape per case, because this one alone proved nothing about the
    audit's pessimism as a class: two false-`SAFE` shapes shipped past it,
    and each now has its own case below.
    """
    source = """
import html


def _e(value):
    return html.escape("" if value is None else str(value))


def _render(project):
    return f'<h1>{_e(project.title)}</h1><p>{project.description}</p>'
"""
    verdicts = {item.expression: item.verdict for item in audit(ast.parse(source))}

    assert verdicts["_e(project.title)"] == ESCAPED
    assert verdicts["project.description"] == RAW


def test_the_audit_does_not_trust_a_helper_that_yields():
    """ER7(a), shape 2 of 3: a generator's returns are vacuously safe.

    A function that `yield`s carries no `ast.Return` with the values it
    produces, so `all(...)` over its return list is true of nothing --
    and the verdict `SAFE` claims "every return is provably not storage
    text". This exact module audited `SAFE` before `_returns_hold` demoted
    generators, and it is a shape this repository already writes: three of
    the report module's helpers are `Sequence`-walking joins.

    *Fails if:* the `Yield`/`YieldFrom` check leaves `_returns_hold`.
    """
    source = '''
import html


def _e(value):
    return html.escape("" if value is None else str(value))


def _titles(milestones):
    """A generator, not a list: no `return` node carries `title`."""
    for milestone in milestones:
        yield milestone.title


def _render(milestones):
    return f'<p>{", ".join(_titles(milestones))}</p>'
'''
    verdicts = {item.expression: item.verdict for item in audit(ast.parse(source))}

    assert verdicts["', '.join(_titles(milestones))"] == RAW


def test_the_audit_resolves_a_local_before_the_module_name_it_shadows():
    """ER7(b), shape 3 of 3: a local shadowing a module-scope name.

    `_name_safe` used to answer from `module_names` first, so a local called
    `html`, `json`, `date`, `re`, `clock` -- or any of the module's 45
    function names -- read as safe whatever it held. Python resolves the
    local; so must the audit.

    Both directions in one module, deliberately: the genuine module-scope
    constant must stay `SAFE`, or the fix would be "call everything `RAW`",
    which passes the first assertion and destroys the audit's usefulness.

    *Fails if:* `_name_safe` tests `module_names` or `functions` before the
    function's own parameters and bindings.
    """
    source = """
import html

PREFIX = "Obra"


def _e(value):
    return html.escape("" if value is None else str(value))


def _render(project):
    html = project.description
    return f'<h2>{PREFIX}</h2><p>{html}</p>'
"""
    verdicts = {item.expression: item.verdict for item in audit(ast.parse(source))}

    assert verdicts["html"] == RAW
    assert verdicts["PREFIX"] == SAFE


@pytest.mark.parametrize("index", range(len(escape_call_sites(TREE))))
def test_removing_any_single_escape_is_caught(index: int):
    """ER1, for every `_e()` in the module, one case each.

    The parametrisation is the enumeration: `range(len(...))` over the calls
    the AST holds, so a new escape is covered the moment it is written and a
    removed one changes the case count rather than passing silently.

    Each case strips exactly that one call -- `_e(x)` becomes `x` -- and
    requires the audit to report a site it did not report on the unmutated
    module. "At least one new finding" rather than "one specific finding":
    stripping an escape usually taints the enclosing fragment and everything
    that interpolates it, and pinning the exact fan-out would pin the call
    graph rather than the escaping.

    *Fails if:* an escape's removal is invisible to the audit -- which is the
    state the whole suite was in before this module.
    """
    before = {item.site for item in audit(TREE) if item.verdict == RAW}
    after = {
        item.site for item in audit(without_escape(TREE, index)) if item.verdict == RAW
    }

    line = escape_call_sites(TREE)[index]
    assert after - before, (
        f"removing the _e() on line {line} of {report.__file__} "
        "left the audit reporting nothing new"
    )


# ---------------------------------------------------------------------------
# 2 -- the renderers, with hostile data (ER2, ER4)
# ---------------------------------------------------------------------------


def test_the_whole_page_carries_no_tag_and_no_handler_from_stored_data():
    """ER2: the document-level absence, anchored on a document that rendered.

    The three absence assertions are the ones that would pass on an empty
    string, so the length and the two present-and-escaped fragments come
    first.
    """
    document = hostile_document()

    assert len(document) > 2000, "nothing rendered"
    assert "&lt;script&gt;alert&lt;/script&gt;" in document
    assert "&amp;" in document
    assert "<script" not in document.lower()
    # The attribute breakout, raw. Escaped it reads `&quot; onerror=x`, so
    # this clause is what fails for a value printed inside `src="..."`.
    assert '" onerror=' not in document


def test_the_milestone_card_escapes_both_halves_of_a_stage_title():
    """ER2: `_stage_item_html` -- the renderer whose escape was measured
    unprotected. The parent and the name are two separate `_e()` calls.

    *Fails if:* `_e` is dropped from `{_e(parent)}` or `{_e(name)}` in
    `report._stage_item_html`.
    """
    cards = report._groups_html(list(hostile_project().milestones))

    assert_escaped_and_never_raw(cards, HOSTILE_STAGE_PARENT, "card kicker")
    assert_escaped_and_never_raw(cards, HOSTILE_STAGE_NAME, "card name")


def test_the_next_steps_card_escapes_the_shared_kicker_and_the_name_list():
    """ER2: `_date_group_html`'s two escapes, and `_stage_items_html` below it.

    The row carries a payload with a `start`, so it buckets into a date group
    rather than falling through to `_stage_items_html`; the hoisted kicker
    needs every row in the bucket to share a parent, which one row does.

    *Fails if:* `_e` is dropped from `{_e(shared)}` or from the `", ".join`
    of `_e(...)` names in `report._date_group_html`.
    """
    cards = report._groups_html(list(hostile_project().milestones))

    # The date bucket has to have rendered, or both assertions below are
    # answered by `_stage_items_html` -- which is the *other* card's renderer
    # and is pinned by its own case.
    assert '<div class="dgrp">' in cards, "the row did not reach a date group"
    assert_escaped_and_never_raw(cards, HOSTILE_NEXT_PARENT, "próximos passos kicker")
    assert_escaped_and_never_raw(cards, HOSTILE_NEXT_NAME, "próximos passos name")


def test_the_stage_detail_section_escapes_the_contractors_leaf_name():
    """ER2/ER6: `_stage_leaf_html`, the **leaf name** -- the field that comes
    out of the contractor's `.mpp` with nothing upstream sanitising it.

    This case asserted nothing. Its five original assertions named no value
    of their own, and the hostile *stage title* two lines away in
    `_stage_detail_block_html` -- which has its own case here and in
    `test_project_report_stage_detail_section.py` -- answered every one of
    them: replacing `leaf.name` with a constant, so the contractor's field was
    gone from the document entirely, left it green. Stripping `_e` at the same
    line did redden it, which is why 20 escape mutations never found this.

    So it now names `HOSTILE_LEAF_NAME` and nothing else, through the shared
    helper, with `report.title_case` as the renderer's own pre-escape pass.

    *Fails if:* `_e` is dropped from `{_e(title_case(leaf.name))}`, **or**
    `leaf.name` stops reaching that interpolation at all.
    """
    section = report._stage_detail_html(list(hostile_project().milestones))

    assert section, "no stage-detail section rendered"
    assert_escaped_and_never_raw(
        section, HOSTILE_LEAF_NAME, "serviço leaf name", transform=report.title_case
    )
    assert "<script" not in section.lower()
    assert '" onerror=' not in section


def test_the_hero_escapes_the_title_the_kind_and_the_description():
    """ER2: `_hero_html`'s four stored strings, one assertion each.

    The status pill takes the `str(project.status)` fallback, which is the
    branch a stored value actually reaches; the kind is the `(...)` suffix
    `split_title_and_kind` peels off the title.

    *Fails if:* `_e` is dropped from `{_e(title)}`, `{_e(kind)}`,
    `{_e(project.description)}` or `{_e(status_label)}`.
    """
    hero = report._hero_html(hostile_project(), 1, hostile_tenant())

    assert_escaped_and_never_raw(hero, HOSTILE_PROJECT_TITLE, "hero title")
    assert_escaped_and_never_raw(hero, HOSTILE_PROJECT_KIND, "hero kicker kind")
    assert_escaped_and_never_raw(hero, HOSTILE_DESCRIPTION, "hero description")
    assert_escaped_and_never_raw(hero, HOSTILE_STATUS, "status pill")


def test_the_cover_photo_url_is_escaped_inside_its_src_attribute():
    """ER2: `cover_photo_url` reaches the hero **verbatim** for a Drive URL --
    `ProjectService.cover_display_url` says so, and the sync script writes
    more of those on every run. The value lands inside `src="..."`, so the
    double quote is the character that matters, not only the angle bracket.

    *Fails if:* `_e` is dropped from `{_e(cover_url)}`.
    """
    hero = report._hero_html(hostile_project(), 1, hostile_tenant())

    assert_escaped_and_never_raw(hero, HOSTILE_COVER_URL, "cover src")
    assert '"><script' not in hero


def test_the_bulletins_escape_the_title_the_content_and_every_photo_url():
    """ER2: `_updates_html`'s three escapes.

    *Fails if:* `_e` is dropped from `{_e(update.title)}`,
    `{_e(update.content)}` or `{_e(url)}`.
    """
    updates = report._updates_html(list(hostile_project().updates))

    assert_escaped_and_never_raw(updates, HOSTILE_UPDATE_TITLE, "bulletin title")
    assert_escaped_and_never_raw(updates, HOSTILE_UPDATE_CONTENT, "bulletin body")
    assert_escaped_and_never_raw(updates, HOSTILE_PHOTO_URL, "bulletin photo src")


def test_the_masthead_and_the_footer_escape_the_condominium_name():
    """ER2: the tenant name, rendered twice -- `alt` in the masthead, `<b>` in
    the footer -- by two independent `_e()` calls, plus the author's name.

    A tenant name is administrator-entered rather than contractor-supplied,
    which makes this a coverage gap and not a live defect. It is pinned
    anyway: it is the same public document, and "administrator-entered" is a
    property of today's callers, not of the renderer.

    *Fails if:* `_e` is dropped from either `tenant_name` assignment or from
    `{_e(user.full_name)}`.
    """
    masthead = report._masthead_html(hostile_tenant(), GENERATED_AT.date())
    footer = report._footer_html(
        hostile_tenant(), User(full_name=HOSTILE_USER_NAME), GENERATED_AT
    )

    assert_escaped_and_never_raw(masthead, HOSTILE_TENANT_NAME, "logo alt")
    assert_escaped_and_never_raw(footer, HOSTILE_TENANT_NAME, "footer name")
    assert_escaped_and_never_raw(footer, HOSTILE_USER_NAME, "footer author")


def test_the_document_title_escapes_the_condominium_name(monkeypatch):
    """ER2: `render_report_html`'s `<title>`, the last escape in the module.

    `_page_html` reaches every other renderer without a database; this one
    sits above it, so the two resolvers and the clock are substituted and the
    **whole document** is rendered -- `<!DOCTYPE html>` through `</html>`.

    *Fails if:* `_e` is dropped from the `tenant_name` assignment in
    `report.render_report_html`.
    """
    monkeypatch.setattr(report, "_acting_tenant", lambda _session: hostile_tenant())
    monkeypatch.setattr(
        report, "_acting_projects", lambda _session: [hostile_project()]
    )
    monkeypatch.setattr(report.clock, "db_now", lambda: GENERATED_AT)

    document = report.render_report_html(None, None)

    assert document.startswith("<!DOCTYPE html>")
    assert (
        f"<title>Relatório de Obras — {report._e(HOSTILE_TENANT_NAME)}</title>"
        in document
    )
    assert HOSTILE_TENANT_NAME not in document
    assert "<script" not in document.lower()


def test_the_logo_url_is_percent_encoded_before_it_is_escaped():
    """ER4: the one site whose real defence is **not** `_e`.

    `urls.public_tenant_logo_url` percent-encodes the slug with no safe
    characters, so by the time the escape sees the URL there is no `<`, `&`
    or quote left in it and `_e` is a no-op there. Naming that escape as this
    site's protection would be the same mistake the module docstring warns
    about, so what is asserted is the encoding -- and the audit still pins
    the escape statically.

    **The `safe=""` is not this case's to claim**, and the first version of
    this docstring claimed it anyway: `quote` encodes `<` whether or not
    `safe=""` is passed, so removing it from both builders in
    `app/core/urls.py` left every assertion here green. What `safe=""` buys is
    the `/` -- the character that would otherwise split the path into another
    segment -- so that is what this asserts, and the property is owned by
    `tests/test_public_urls.py::test_a_slug_that_would_break_the_path_is_percent_encoded`.

    *Fails if:* the builder interpolates the slug raw (`%3C`), or `safe=""` is
    dropped so a `/` survives into the path (`%2F`).
    """
    masthead = report._masthead_html(hostile_tenant(), GENERATED_AT.date())

    assert "%3C" in masthead, "the slug was not percent-encoded"
    # `HOSTILE_TENANT_SLUG` carries a `/` -- it closes `</script>` -- so this
    # clause sees `safe=""` leaving the builder, which `%3C` alone cannot.
    assert "/" in HOSTILE_TENANT_SLUG
    assert "%2F" in masthead, "the slug's / was left as a path separator"
    assert HOSTILE_TENANT_SLUG not in masthead
    assert "<script" not in masthead.lower()


def test_a_hostile_brand_theme_never_reaches_the_style_block():
    """ER2/ER3: what the four declared exemptions rest on.

    `<style>` is not an HTML text node -- the browser does not decode
    entities inside it -- so `html.escape` there would corrupt a declaration
    rather than defuse it. The palette is defended one layer up instead:
    `normalize_brand_theme` refuses anything that is not a hex colour, and a
    valid theme can only emit `oklch(...)` built from floats.

    Both halves. A theme that raises proves nothing on its own -- a renderer
    that refused *every* theme would pass that alone -- so the valid theme is
    rendered too and every emitted declaration is matched against `oklch`.

    *Fails if:* the palette stops being validated, or `_stylesheet` starts
    interpolating a stored string that is not a colour.
    """
    with pytest.raises(InvalidBrandThemeError):
        report._stylesheet(
            {"mode": "simple", "primary": "</style><script>", "accent": "#123456"}
        )

    sheet = report._stylesheet(
        {"mode": "simple", "primary": "#1b4332", "accent": "#d4a24c"}
    )
    declarations = re.findall(r"--[\w-]+:([^;]+);", sheet)

    assert len(declarations) >= 19, "the :root block did not render"
    assert all(value.strip().startswith("oklch(") for value in declarations), (
        "a :root value is not an oklch() triple"
    )
    assert "</style" not in sheet.lower()
