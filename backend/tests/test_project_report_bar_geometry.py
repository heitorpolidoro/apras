"""APRAS-112: the vertical geometry of the report's `avanço físico` bar.

`.one.close .ends { position:absolute; left:0; right:0; bottom:6.5mm; }` took
the `Início`/`Conclusão` row out of normal flow and dropped it into the 9mm
band `.one.close`'s `padding-bottom` reserves for the `previsto` label, so in
the two layout cases that put that label below the track the row sat across
both the track and the label. This module measures the bands arithmetically
out of the shipped stylesheet and asserts they are disjoint.

Why arithmetic and not a browser: jsdom has no layout engine --
`getBoundingClientRect()` returns zeroes there, so a non-overlap assertion
under jsdom passes for every stylesheet, broken or not. Playwright would
measure real layout but the repository carries no browser dependency. Every
length in the `.one` family is a literal `mm`, `pt` or `px` and every box
involved is either a declared `height` or a single line box, so the bands are
computable exactly. `docs/tasks/APRAS-112-mock.html` measures the same bands in
a real engine, and `HEAD_ONE_FAMILY` below pins this model to those numbers.

Two properties make the measurement trustworthy rather than decorative, and
both are asserted here:

* **No defaults.** Every declaration the model needs is read out of the
  stylesheet and raises when absent or unparseable. It is never assumed, never
  substituted with a CSS initial value, never zero. A parser that reads
  nothing must explode, not return plausible geometry.
* **One code path.** `measure_bar` is the single entry point. The calibration
  control feeds it the pre-fix `.one` family and asserts it reports the two
  intersections a real browser reported, which is what proves the checker is
  able to fail at all. The case tests call the same function with `CSS_BODY`.

Recorded limitations, all of them things this module cannot see rather than
things it chooses not to check:

* The model computes single line boxes, so a label wrapping to a second line
  is outside what it detects.
* `_DECLARATION`'s value class stops at the first `;`, so a semicolon inside a
  quoted value or a `url()` would split one declaration into two. Unlike the
  brace case -- which breaks the tokenizer loudly -- this one is silent, since
  the reassembly check compares the raw captured text, which such a value
  leaves unchanged. `CSS_BODY` carries no such value today.
* `parse_css` collects an at-rule's nested rules through `Stylesheet.rules`,
  which keeps `Rule`s only, so an at-rule nested inside another
  (`@media print { @supports … { … } }`) would hide its inner rules from
  `nested_rules` and from the close-layout pin. No such shape exists today.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.services.project_report_service import CSS_BODY

#: The ordered, byte-for-byte text of every `CSS_BODY` rule whose selector
#: mentions neither `close` nor `below`, captured from HEAD before the fix
#: (ER4). Order and text are both compared, so a reordering or a whitespace
#: change in a rule the far-apart layout consumes fails the suite.
#:
#: The file is generated, and this is the command that generates it. After a
#: deliberate edit to a shared rule, run from `backend/` and review the diff
#: rather than hand-patching 354 lines of JSON:
#:
#:     uv run python -c "import json
#:     from app.services.project_report_service import CSS_BODY
#:     from tests.test_project_report_bar_geometry import parse_css, shared_rule_pairs
#:     print(json.dumps(shared_rule_pairs(parse_css(CSS_BODY)), indent=2, ensure_ascii=False))
#:     " > tests/data/report_css_shared_baseline.json
SHARED_BASELINE = (
    Path(__file__).resolve().parent / "data" / "report_css_shared_baseline.json"
)

#: CSS absolute length conversions, at the 96dpi reference pixel.
PX_PER_MM = 96 / 25.4
PX_PER_PT = 96 / 72

#: The three layout cases of `_one_bar`. `no_curve` (APRAS-103) emits the same
#: `one close` / `tag plan below` pairing the close branch does, so it shares
#: its geometry; it is measured separately because it reaches that layout
#: unconditionally rather than through `CLOSE_LABEL_GAP`.
CASES = ("far", "close", "no_curve")

#: The complete `.one` family exactly as it stood before this fix, plus the
#: top-level `body` rule that supplies the `line-height:1.5` the ends row's
#: height is computed from. This is the calibration control's whole input: with
#: the no-defaults rule above, a partial stylesheet raises instead of
#: producing geometry, so the control cannot be reduced to the three rules the
#: bug involves.
HEAD_ONE_FAMILY = """
body { font-family:"DM Sans", Arial, sans-serif; color:var(--text); background:var(--desk); font-size:10.5pt; line-height:1.5; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
.one { position:relative; padding-top:9mm; margin-top:1mm; }
.one .track { height:11px; background:var(--line); border-radius:20px; overflow:hidden; position:relative; }
.one .seg { position:absolute; top:0; height:100%; }
.one .seg.a { left:0; background:var(--brand); }
.one .seg.b { background:var(--brand-alt); }
.one .seg.b.behind { background:#c0392b; opacity:.7; }
.one .mark { position:absolute; top:0; width:1.5px; height:100%; background:var(--card); }
.one .tag { position:absolute; top:0; transform:translateX(-1px); border-left:1.5px solid var(--line); padding-left:2mm; height:9mm; font-size:7.5pt; color:var(--muted); line-height:1.2; white-space:nowrap; }
.one .tag b { display:block; font-size:10pt; color:var(--ink); }
.one .tag.real b { color:var(--brand-text); }
.one .tag.real { border-left-color:var(--brand-alt); }
.one.close { padding-bottom:9mm; }
.one .tag.below { top:auto; bottom:0; height:9mm; display:flex; flex-direction:column-reverse; justify-content:flex-start; }
.one.close .ends { position:absolute; left:0; right:0; bottom:6.5mm; }
.one .ends { display:flex; justify-content:space-between; font-size:7pt; color:var(--muted); margin-top:1.5mm; }
"""

#: The bands a real browser reported for the close case against the live
#: document, relative to the top of `.one`, and the two intersections among
#: them. Quoted from the card and reproduced by
#: `docs/tasks/APRAS-112-mock.html`'s measurement panel.
BROWSER_BANDS = {
    "track": (34.0, 45.0),
    "ends": (40.0, 54.0),
    "label_below": (45.0, 79.0),
}
BROWSER_INTERSECTIONS = (("ends", "label_below"), ("ends", "track"))

#: How much taller the close-case bar is allowed to get (behaviour item 3).
#: Deleting the offending rule costs +5.204mm, which fits. This is a growth
#: guard and *not* a proof the page fits A4: one obra already measures ~356mm
#: against a 297mm sheet, which is a separate task.
MAX_GROWTH_MM = 6.0

#: Every box of the `.one` family whose height `measure_bar` takes from a
#: declaration, in source order. Pinned so that a height added to or removed
#: from a `.one` selector shows up as a missing content check rather than as
#: nothing at all.
DECLARED_HEIGHT_BOXES = (".one .track", ".one .tag", ".one .tag.below")

#: Every `CSS_BODY` rule whose selector names the close layout, pinned as an
#: exact set (ER3). Equality, not containment: a fourth close-scoped rule --
#: an absolute reposition of `.ends` under another name, say -- fails here
#: instead of slipping past.
CLOSE_LAYOUT_RULES = (
    (".one.close", "padding-bottom:9mm;"),
    (
        ".one .tag.below",
        (
            "top:auto; bottom:0; height:9mm; display:flex; "
            "flex-direction:column-reverse; justify-content:flex-start;"
        ),
    ),
)


class StylesheetError(Exception):
    """The stylesheet cannot be parsed, or lacks a declaration the model needs."""


# --------------------------------------------------------------------------
# The parser
# --------------------------------------------------------------------------
#
# `CSS_BODY` is not one rule per line and a line-splitting parser is wrong
# here in three distinct ways, each of which this parser handles explicitly:
#
# 1. Three lines carry two rules each (`.grp.done h4 { … } .grp.done h4 i
#    { … }`, and the same shape for `.doing` and `.next`), so tokenization is
#    by brace matching over the whole string.
# 2. `body` and `.page` are each declared twice, once at the top level and
#    once inside `@media print`. A parser keyed on selector alone overwrites
#    the top-level `body` with the print block's `{ background:#fff; }` and
#    loses the `line-height:1.5` the ends row's height depends on -- so
#    at-rule contents live in their own namespace and are never merged into
#    the screen cascade, and a selector repeated within one namespace
#    accumulates its declarations in source order.
# 3. `@page` and `@media print` are at-rule blocks, one carrying
#    declarations and the other nested rules. An at-rule nested inside another
#    is unsupported: `Stylesheet.rules` keeps `Rule`s only, so the inner
#    block's rules would not reach `nested_rules`. `CSS_BODY` has no such
#    shape.


@dataclass(frozen=True)
class Rule:
    """One `selector { declarations }` block, with its source span."""

    selector: str
    declarations: str
    start: int
    end: int

    def render(self) -> str:
        """The rule rebuilt from its parsed fields, for the reassembly check."""
        return f"{self.selector} {{ {self.declarations} }}"


@dataclass(frozen=True)
class AtRule:
    """One `@prelude { body }` block, with the rules nested inside it."""

    prelude: str
    body: str
    rules: tuple[Rule, ...]
    start: int
    end: int

    def render(self) -> str:
        """The block rebuilt from its parsed fields, for the reassembly check."""
        return f"{self.prelude} {{{self.body}}}"


@dataclass(frozen=True)
class Stylesheet:
    """Every node of a stylesheet, in source order, in two namespaces."""

    nodes: tuple[Rule | AtRule, ...]

    @property
    def rules(self) -> tuple[Rule, ...]:
        """The screen cascade: top-level rules only, never the print block."""
        return tuple(node for node in self.nodes if isinstance(node, Rule))

    @property
    def at_rules(self) -> tuple[AtRule, ...]:
        """The at-rule blocks, in source order."""
        return tuple(node for node in self.nodes if isinstance(node, AtRule))

    @property
    def nested_rules(self) -> tuple[Rule, ...]:
        """Every rule nested inside an at-rule -- the print namespace."""
        return tuple(rule for block in self.at_rules for rule in block.rules)


def _closing_brace(css: str, opening: int) -> int:
    """The index of the `}` that closes the `{` at `opening`."""
    depth = 0
    for index in range(opening, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise StylesheetError(f"unbalanced brace opened at offset {opening}")


def parse_css(css: str, base: int = 0) -> Stylesheet:
    """Tokenize `css` by brace matching, keeping every node's source span.

    `base` offsets the recorded spans, so the rules nested in an at-rule carry
    positions in the enclosing document rather than in the block's body.
    """
    nodes: list[Rule | AtRule] = []
    index = 0
    while index < len(css):
        while index < len(css) and css[index].isspace():
            index += 1
        if index >= len(css):
            break
        opening = css.find("{", index)
        if opening == -1:
            raise StylesheetError(f"text with no block at offset {base + index}")
        closing = _closing_brace(css, opening)
        prelude = css[index:opening].strip()
        body = css[opening + 1 : closing]
        span = (base + index, base + closing + 1)
        if prelude.startswith("@"):
            nested = parse_css(body, base + opening + 1).rules if "{" in body else ()
            nodes.append(AtRule(prelude, body, nested, *span))
        else:
            nodes.append(Rule(prelude, body.strip(), *span))
        index = closing + 1
    return Stylesheet(tuple(nodes))


# --------------------------------------------------------------------------
# Reading declarations out of the screen cascade
# --------------------------------------------------------------------------

_DECLARATION = re.compile(r"([-a-zA-Z]+)\s*:\s*([^;]+)")
_LENGTH = re.compile(r"^(-?\d+(?:\.\d+)?)(mm|pt|px)$")
_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


def _selector_parts(selector: str) -> tuple[str, ...]:
    """A selector list split into its members (`html, body` names both)."""
    return tuple(part.strip() for part in selector.split(","))


def maybe_value(sheet: Stylesheet, selector: str, prop: str) -> str | None:
    """`prop`'s last declared value for `selector` in the screen cascade.

    Matching is on the selector text, not on CSS specificity: the model only
    ever asks for selectors that exist verbatim in the sheet. Declarations
    accumulate in source order across every rule naming `selector`, so a
    duplicated selector loses nothing and the later declaration wins.
    """
    text = " ".join(
        rule.declarations
        for rule in sheet.rules
        if selector in _selector_parts(rule.selector)
    )
    found = [
        match.group(2).strip()
        for match in _DECLARATION.finditer(text)
        if match.group(1) == prop
    ]
    return found[-1] if found else None


def value(sheet: Stylesheet, selector: str, prop: str) -> str:
    """`maybe_value`, but a missing declaration is an error, never a default."""
    found = maybe_value(sheet, selector, prop)
    if found is None:
        raise StylesheetError(f"no `{prop}` declared for `{selector}`")
    return found


def to_px(raw: str) -> float:
    """An absolute CSS length in px. Anything else -- `auto`, `%` -- raises."""
    if raw == "0":
        return 0.0
    match = _LENGTH.match(raw)
    if match is None:
        raise StylesheetError(f"not an absolute length: {raw!r}")
    amount = float(match.group(1))
    if match.group(2) == "mm":
        return amount * PX_PER_MM
    if match.group(2) == "pt":
        return amount * PX_PER_PT
    return amount


def to_number(raw: str) -> float:
    """A unitless number, as `line-height` takes."""
    if _NUMBER.match(raw) is None:
        raise StylesheetError(f"not a unitless number: {raw!r}")
    return float(raw)


_SIMPLE = re.compile(r"[.#]?[-\w]+")


def _simple_selectors(compound: str) -> frozenset[str]:
    """The simple selectors of one compound (`.one.close` -> `.one`, `.close`)."""
    return frozenset(_SIMPLE.findall(compound))


def _ancestor_distance(candidate: str, target: str) -> int | None:
    """How many levels above `target`'s element the element `candidate` names.

    `0` means `candidate` also matches `target`'s own element -- `.one .tag`
    matches `.one .tag.below`, one element carrying both classes -- `1` its
    parent, and so on. `None` means the two are unrelated, or name a shape this
    comparison does not model: a combinator other than the descendant space, or
    a compound with no simple selector in it.

    `body` is the one ancestor no selector text here expresses: `.one` is a
    descendant of `body` in the emitted document, not in the stylesheet, so it
    is placed above every selector by hand. This is what lets the model read
    `line-height:1.5` off `body` while a nearer declaration still wins.
    """
    target_parts = target.split()
    if candidate == "body":
        return len(target_parts)
    candidate_parts = candidate.split()
    if len(candidate_parts) > len(target_parts):
        return None
    # `strict=False` on purpose: a shorter candidate is an ancestor, which is
    # the whole point of the comparison.
    for mine, theirs in zip(candidate_parts, target_parts, strict=False):
        simple, other = _simple_selectors(mine), _simple_selectors(theirs)
        if not simple or not other or not simple <= other:
            return None
    return len(target_parts) - len(candidate_parts)


def inherited(sheet: Stylesheet, selector: str, prop: str) -> str:
    """`prop` for `selector`'s element, resolved through CSS inheritance.

    The nearest declaration wins -- self before parent, parent before `body` --
    and among declarations at the same distance the later one in source order
    wins, the same rule `maybe_value` follows. Specificity is not modelled; the
    `.one` family has no two selectors at one distance that disagree.

    A property no ancestor declares raises, for the same reason `value` does: a
    content height computed from an assumed font size proves nothing.
    """
    best: tuple[int, int, str] | None = None
    for index, rule in enumerate(sheet.rules):
        declared = [
            match.group(2).strip()
            for match in _DECLARATION.finditer(rule.declarations)
            if match.group(1) == prop
        ]
        if not declared:
            continue
        distances = [
            distance
            for part in _selector_parts(rule.selector)
            if (distance := _ancestor_distance(part, selector)) is not None
        ]
        if not distances:
            continue
        # Nearer wins outright; at equal distance the later rule wins, and
        # `index` only grows, so an equal distance always replaces.
        candidate = (min(distances), index, declared[-1])
        if best is None or candidate[0] <= best[0]:
            best = candidate
    if best is None:
        raise StylesheetError(f"no `{prop}` declared for `{selector}` or any ancestor")
    return best[2]


def _line_box_height(sheet: Stylesheet, selector: str) -> float:
    """One line box of `selector`: its font size times its line height."""
    return to_px(inherited(sheet, selector, "font-size")) * to_number(
        inherited(sheet, selector, "line-height")
    )


# --------------------------------------------------------------------------
# The band model
# --------------------------------------------------------------------------


#: What each declared-height box of the `.one` family holds, as the selectors
#: of the line boxes stacked inside it -- a box's own text line is named by its
#: own selector, and every `display:block` child adds another. Content height
#: is a function of the markup, which no stylesheet expresses, so this is the
#: one place the model is told about the emitted DOM. `()` means the box holds
#: no text of its own: `.one .track` contains only absolutely positioned
#: segments and marks.
#:
#: `measure_bar` raises for any box whose height it discovers and this table
#: does not describe, which is what makes the content-fit guarantee general: a
#: fourth declared-height box added to `CSS_BODY` cannot slip past the check by
#: nobody remembering to extend it.
BOX_CONTENTS: dict[str, tuple[str, ...]] = {
    ".one .track": (),
    ".one .tag": (".one .tag", ".one .tag b"),
    ".one .tag.below": (".one .tag", ".one .tag b"),
}


@dataclass(frozen=True)
class DeclaredBox:
    """A box whose height the model reads, beside the content it has to hold.

    A box positioned from its declared height -- `.one .tag.below`, placed at
    `total_height - bottom - height` -- overflows *upward* in a real browser
    when its content does not fit, into whatever sits above it, while the band
    arithmetic stays green. That is why fitting is asserted per box and not
    only for the one box whose overflow is easiest to imagine.
    """

    selector: str
    declared_height: float
    content_height: float


def declared_height_boxes(sheet: Stylesheet) -> tuple[DeclaredBox, ...]:
    """Every `.one`-family box whose height comes from a declaration.

    Discovery is by scanning the sheet, not by naming the boxes, so a height
    declared on a new `.one` selector is found without anyone editing this
    function. A `height` that is not an absolute length -- `.one .seg` and
    `.one .mark` are `100%` -- is not a height the model takes a band or a box
    from, and is skipped; a height it *does* take with no entry in
    `BOX_CONTENTS` raises.
    """
    boxes: list[DeclaredBox] = []
    seen: set[str] = set()
    for rule in sheet.rules:
        for selector in _selector_parts(rule.selector):
            if not selector.startswith(".one") or selector in seen:
                continue
            raw = maybe_value(sheet, selector, "height")
            if raw is None:
                continue
            try:
                declared = to_px(raw)
            except StylesheetError:
                continue
            seen.add(selector)
            if selector not in BOX_CONTENTS:
                raise StylesheetError(
                    f"`{selector}` declares a height but no content model "
                    f"describes it; add it to BOX_CONTENTS"
                )
            boxes.append(
                DeclaredBox(
                    selector,
                    declared,
                    sum(
                        _line_box_height(sheet, line) for line in BOX_CONTENTS[selector]
                    ),
                )
            )
    return tuple(boxes)


@dataclass(frozen=True)
class Band:
    """One vertical band of the bar, in px relative to the top of `.one`."""

    name: str
    top: float
    bottom: float
    elements: tuple[str, ...]

    def intersects(self, other: "Band") -> bool:
        """Strict intersection: bands that merely touch do not intersect.

        The fixed layout is flush at two boundaries -- the track's top is the
        above-label band's bottom, and the below band's top is the ends row's
        bottom with 0.0px of clearance -- so inclusive semantics would fail a
        correct layout. No minimum clearance is demanded.
        """
        return self.top < other.bottom and other.top < self.bottom


@dataclass(frozen=True)
class BarModel:
    """The measured bar: its bands, its height and what it read to get them."""

    case: str
    bands: tuple[Band, ...]
    total_height: float | None
    ends_in_flow: bool
    ends_bottom: float | None
    boxes: tuple[DeclaredBox, ...]

    def box(self, selector: str) -> DeclaredBox:
        """The declared-height box named by `selector`."""
        for box in self.boxes:
            if box.selector == selector:
                return box
        raise StylesheetError(f"no declared-height box for {selector!r}")

    def band(self, name: str) -> Band:
        """The band called `name`."""
        for band in self.bands:
            if band.name == name:
                return band
        raise StylesheetError(f"no band called {name!r} in the {self.case} case")

    def intersections(self) -> tuple[tuple[str, str], ...]:
        """Every intersecting pair of bands, each pair sorted, sorted."""
        found = {
            tuple(sorted((first.name, second.name)))
            for index, first in enumerate(self.bands)
            for second in self.bands[index + 1 :]
            if first.intersects(second)
        }
        return tuple(sorted(found))


def measure_bar(css: str, case: str) -> BarModel:
    """The vertical bands of `.one` in `case`, computed from `css` alone.

    The single entry point: the case tests pass `CSS_BODY`, the calibration
    control passes the pre-fix `.one` family, and both get the same parser,
    the same cascade resolution and the same intersection predicate.

    The two above-track labels share one band. In the far-apart case both
    `previsto` and `realizado` sit at `top:0`, separated horizontally -- that
    separation is the whole reason `CLOSE_LABEL_GAP` exists -- so they are one
    band rather than a pair the model would report as overlapping.
    """
    if case not in CASES:
        raise StylesheetError(f"unknown layout case {case!r}")
    sheet = parse_css(css)

    padding_top = to_px(value(sheet, ".one", "padding-top"))
    track_height = to_px(value(sheet, ".one .track", "height"))
    tag_top = to_px(value(sheet, ".one .tag", "top"))
    tag_height = to_px(value(sheet, ".one .tag", "height"))
    ends_margin_top = to_px(value(sheet, ".one .ends", "margin-top"))
    ends_font = to_px(value(sheet, ".one .ends", "font-size"))
    ends_height = ends_font * to_number(value(sheet, "body", "line-height"))

    closed = case in ("close", "no_curve")
    # `position` and `bottom` on `.one.close .ends` are the one pair whose
    # absence is meaningful rather than an error: absent `position` is the
    # in-flow layout this task restores. A `position` that is there without a
    # `bottom`, or that is not `absolute`, is geometry this model cannot
    # place, so it raises rather than guessing.
    ends_position = (
        maybe_value(sheet, ".one.close .ends", "position") if closed else None
    )
    ends_offset: float | None = None
    if ends_position is not None:
        if ends_position != "absolute":
            raise StylesheetError(f"`.one.close .ends` position:{ends_position}")
        offset = maybe_value(sheet, ".one.close .ends", "bottom")
        if offset is None:
            raise StylesheetError("`.one.close .ends` is absolute with no `bottom`")
        ends_offset = to_px(offset)

    in_flow = ends_position is None
    flow_height = track_height + (ends_margin_top + ends_height if in_flow else 0.0)

    bands = [
        Band(
            "labels_above",
            tag_top,
            tag_top + tag_height,
            ("previsto", "realizado") if case == "far" else ("realizado",),
        ),
        Band("track", padding_top, padding_top + track_height, ("track",)),
    ]

    total_height: float | None = None
    if closed:
        padding_bottom = to_px(value(sheet, ".one.close", "padding-bottom"))
        total_height = padding_top + flow_height + padding_bottom
        below_height = to_px(value(sheet, ".one .tag.below", "height"))
        below_top = (
            total_height
            - to_px(value(sheet, ".one .tag.below", "bottom"))
            - below_height
        )
        bands.append(
            Band("label_below", below_top, below_top + below_height, ("previsto",))
        )

    if in_flow:
        ends_top = padding_top + track_height + ends_margin_top
    else:
        # Absolutely positioned against `.one`'s padding box, which is its
        # border box: the bar declares no border.
        ends_top = total_height - ends_offset - ends_height
    bands.append(
        Band("ends", ends_top, ends_top + ends_height, ("Início", "Conclusão"))
    )

    return BarModel(
        case=case,
        bands=tuple(bands),
        total_height=total_height,
        ends_in_flow=in_flow,
        ends_bottom=ends_offset,
        # Every case reports every declared-height box, including the `below`
        # box the far-apart markup does not emit: an overflowing box is a
        # stylesheet defect wherever it is used.
        boxes=declared_height_boxes(sheet),
    )


# --------------------------------------------------------------------------
# ER1, ER2 -- the bands are disjoint in all three layout cases
# --------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_no_two_bands_of_the_bar_intersect(case):
    """The ends row clears the track and both labels, in every layout case."""
    assert measure_bar(CSS_BODY, case).intersections() == ()


@pytest.mark.parametrize("case", ["close", "no_curve"])
def test_the_ends_row_is_laid_out_in_normal_flow_after_the_track(case):
    """Behaviour item 1: no case positions the ends row absolutely."""
    model = measure_bar(CSS_BODY, case)
    assert model.ends_in_flow
    assert model.ends_bottom is None
    assert model.band("ends").top >= model.band("track").bottom


@pytest.mark.parametrize("case", ["close", "no_curve"])
def test_the_below_label_band_begins_at_or_after_the_ends_row(case):
    """Behaviour item 1, second half: the reserved band starts below the row."""
    model = measure_bar(CSS_BODY, case)
    assert model.band("label_below").top >= model.band("ends").bottom


def test_the_far_apart_case_has_no_below_label_band():
    """Both labels sit above the track when the values are far apart."""
    model = measure_bar(CSS_BODY, "far")
    assert model.band("labels_above").elements == ("previsto", "realizado")
    assert [band.name for band in model.bands] == ["labels_above", "track", "ends"]


# --------------------------------------------------------------------------
# ER6 -- the calibration control: proof the checker can fail
# --------------------------------------------------------------------------


@pytest.mark.parametrize("case", ["close", "no_curve"])
def test_the_pre_fix_stylesheet_reproduces_the_browser_measurement(case):
    """The positive control, through the same entry point the cases use.

    Feeding `measure_bar` the complete pre-fix `.one` family must reproduce
    the bands a real browser reported against the live document and report
    both intersections. Restoring `.one.close .ends { position:absolute; …;
    bottom:6.5mm; }` in `CSS_BODY` therefore turns the case tests above red;
    without this test, "no intersection" could mean the model measured
    nothing.
    """
    model = measure_bar(HEAD_ONE_FAMILY, case)

    assert not model.ends_in_flow
    for name, (top, bottom) in BROWSER_BANDS.items():
        assert model.band(name).top == pytest.approx(top, abs=1.0)
        assert model.band(name).bottom == pytest.approx(bottom, abs=1.0)
    assert model.intersections() == BROWSER_INTERSECTIONS


def test_the_calibration_input_carries_the_whole_one_family():
    """Three rules are not enough input, and the control does not use three.

    The bands depend on `.one{padding-top}`, `.one .track{height}`,
    `.one .tag{height,font-size,line-height,top}`, `.one .tag b{font-size}`,
    `.one .ends{margin-top,font-size}`, `.one .tag.below{bottom,height}`,
    `.one.close{padding-bottom}` and `body{line-height}`. This pins the
    control's input to the shipped text of every `.one` rule, so the control
    cannot quietly shrink to a stylesheet that begs the question.
    """
    shipped = {
        (rule.selector, rule.declarations)
        for rule in parse_css(CSS_BODY).rules
        if rule.selector.startswith(".one")
    }
    control = {
        (rule.selector, rule.declarations)
        for rule in parse_css(HEAD_ONE_FAMILY).rules
        if rule.selector.startswith(".one")
    }
    # The control keeps the one rule this task deletes, and nothing else differs.
    assert control - shipped == {
        (".one.close .ends", "position:absolute; left:0; right:0; bottom:6.5mm;")
    }
    assert shipped - control == set()
    assert maybe_value(parse_css(HEAD_ONE_FAMILY), "body", "line-height") == "1.5"


# --------------------------------------------------------------------------
# ER7 -- the parser accounts for the whole stylesheet
# --------------------------------------------------------------------------


def _gaps_and_reassembly(css: str, sheet: Stylesheet) -> tuple[str, str]:
    """Everything between the parsed nodes, and the sheet rebuilt from them."""
    gaps: list[str] = []
    rebuilt: list[str] = []
    cursor = 0
    for node in sheet.nodes:
        gaps.append(css[cursor : node.start])
        rebuilt.append(css[cursor : node.start])
        rebuilt.append(node.render())
        cursor = node.end
    gaps.append(css[cursor:])
    rebuilt.append(css[cursor:])
    return "".join(gaps), "".join(rebuilt)


def test_the_parser_accounts_for_every_line_of_css_body():
    """Nothing in `CSS_BODY` is invisible to the parser.

    Two assertions, because either alone has a hole: the text between nodes
    must be whitespace only (so no rule is skipped), and every non-blank line
    must fall inside some node's span (so no line is half-read).
    """
    sheet = parse_css(CSS_BODY)
    gaps, _ = _gaps_and_reassembly(CSS_BODY, sheet)
    assert gaps.strip() == ""

    covered: set[int] = set()
    for node in sheet.nodes:
        first = CSS_BODY.count("\n", 0, node.start)
        last = CSS_BODY.count("\n", 0, node.end - 1)
        covered.update(range(first, last + 1))
    non_blank = {
        number for number, line in enumerate(CSS_BODY.split("\n")) if line.strip()
    }
    assert covered == non_blank


def test_css_body_reassembles_byte_for_byte_from_what_was_parsed():
    """Rebuilding each node from its parsed fields reproduces `CSS_BODY`.

    The node text comes from `selector`/`declarations`/`body`, not from the
    source span, so a declaration the parser garbled shows up here.
    """
    _, rebuilt = _gaps_and_reassembly(CSS_BODY, parse_css(CSS_BODY))
    assert rebuilt == CSS_BODY


@pytest.mark.parametrize("group", ["done", "doing", "next"])
def test_the_lines_carrying_two_rules_yield_two_rules(group):
    """`.grp.done h4 { … } .grp.done h4 i { … }` and its two siblings.

    A line-keyed parser drops or garbles one rule of each pair, which would
    also corrupt the shared baseline ER4 compares against.
    """
    sheet = parse_css(CSS_BODY)
    line = next(
        number
        for number, text in enumerate(CSS_BODY.split("\n"))
        if text.startswith(f".grp.{group} h4 {{")
    )
    on_that_line = [
        rule.selector
        for rule in sheet.rules
        if CSS_BODY.count("\n", 0, rule.start) == line
    ]
    assert on_that_line == [f".grp.{group} h4", f".grp.{group} h4 i"]


@pytest.mark.parametrize("selector", ["body", ".page"])
def test_the_duplicated_selectors_are_kept_in_two_namespaces(selector):
    """`body` and `.page` are declared at the top level and in `@media print`.

    Keyed on selector alone, the print block's `body { background:#fff; }`
    overwrites the top-level rule and `line-height:1.5` disappears -- and the
    ends row's height, computed from it, silently becomes unmeasurable.
    """
    sheet = parse_css(CSS_BODY)
    screen = [
        rule for rule in sheet.rules if selector in _selector_parts(rule.selector)
    ]
    printed = [
        rule
        for rule in sheet.nested_rules
        if selector in _selector_parts(rule.selector)
    ]
    assert len(screen) >= 1
    assert len(printed) == 1
    assert maybe_value(sheet, "body", "line-height") == "1.5"


def test_the_at_rules_are_parsed_as_blocks():
    """`@page` carries declarations, `@media print` carries nested rules."""
    blocks = parse_css(CSS_BODY).at_rules
    assert [block.prelude for block in blocks] == ["@page", "@media print"]
    assert blocks[0].rules == ()
    assert blocks[0].body.strip() == "size:A4; margin:0;"
    assert [rule.selector for rule in blocks[1].rules] == [
        "body",
        ".page",
        ".page + .page, .page.brk",
        ".groups, .two, .week, .cyl",
    ]


# --------------------------------------------------------------------------
# The model reads, and never assumes
# --------------------------------------------------------------------------

_MINIMAL = HEAD_ONE_FAMILY.replace(
    ".one.close .ends { position:absolute; left:0; right:0; bottom:6.5mm; }\n", ""
)


@pytest.mark.parametrize(
    "rule",
    [
        ".one { position:relative; padding-top:9mm; margin-top:1mm; }",
        ".one.close { padding-bottom:9mm; }",
        ".one .ends { display:flex; justify-content:space-between; font-size:7pt; color:var(--muted); margin-top:1.5mm; }",
        'body { font-family:"DM Sans", Arial, sans-serif; color:var(--text); background:var(--desk); font-size:10.5pt; line-height:1.5; -webkit-print-color-adjust:exact; print-color-adjust:exact; }',
    ],
)
def test_a_missing_rule_raises_instead_of_being_defaulted(rule):
    """Drop any rule the model needs and it explodes rather than guessing."""
    with pytest.raises(StylesheetError):
        measure_bar(_MINIMAL.replace(rule + "\n", ""), "close")


def test_a_length_the_model_cannot_convert_raises():
    """`padding-top:2em` is not a length this model can place."""
    with pytest.raises(StylesheetError, match="not an absolute length"):
        measure_bar(_MINIMAL.replace("padding-top:9mm", "padding-top:2em"), "close")


def test_a_line_height_that_is_not_a_number_raises():
    """`line-height:normal` leaves the ends row's height undetermined."""
    with pytest.raises(StylesheetError, match="not a unitless number"):
        measure_bar(_MINIMAL.replace("line-height:1.5", "line-height:normal"), "close")


def test_an_absolute_ends_row_without_a_bottom_raises():
    """Absent `position` means in-flow; `position:absolute` needs a `bottom`."""
    css = _MINIMAL + ".one.close .ends { position:absolute; left:0; right:0; }\n"
    with pytest.raises(StylesheetError, match="absolute with no `bottom`"):
        measure_bar(css, "close")


def test_an_ends_row_position_the_model_cannot_place_raises():
    """Only `absolute` is geometry this model knows how to resolve."""
    css = _MINIMAL + ".one.close .ends { position:fixed; bottom:6.5mm; }\n"
    with pytest.raises(StylesheetError, match="position:fixed"):
        measure_bar(css, "close")


def test_an_unknown_layout_case_raises():
    """The bar has exactly three layout cases."""
    with pytest.raises(StylesheetError, match="unknown layout case"):
        measure_bar(CSS_BODY, "sideways")


def test_asking_for_a_declared_height_box_that_does_not_exist_raises():
    """`.one .ends` takes its height from its font, not from a declaration."""
    with pytest.raises(StylesheetError, match="no declared-height box"):
        measure_bar(CSS_BODY, "close").box(".one .ends")


def test_asking_for_a_band_the_case_does_not_have_raises():
    """The far-apart case has no below-label band, and says so."""
    with pytest.raises(StylesheetError, match="no band called"):
        measure_bar(CSS_BODY, "far").band("label_below")


@pytest.mark.parametrize(
    "css",
    [".one { padding-top:9mm;", ".one"],
)
def test_a_malformed_stylesheet_raises(css):
    """An unclosed block and a selector with no block are both errors."""
    with pytest.raises(StylesheetError):
        parse_css(css)


@pytest.mark.parametrize("case", CASES)
def test_every_declared_height_box_fits_the_text_inside_it(case):
    """A declared height must hold its content, or a browser overflows it.

    Every box, not a chosen one: `.one .tag.below` is placed at
    `total_height - bottom - height`, so content that does not fit grows the
    box *upward* into the ends row for a real reader while the band arithmetic
    stays green -- exactly the collision this task exists to end. Both label
    boxes hold the same pair of line boxes, ``7.5pt x 1.2 + 10pt x 1.2 =
    28px``, inside a declared `9mm = 34.02px`.

    The set of boxes is asserted too, so neither the scan nor `BOX_CONTENTS`
    can quietly lose one. The model sees single line boxes only, so a wrapped
    label stays out of its reach.
    """
    model = measure_bar(CSS_BODY, case)

    assert [box.selector for box in model.boxes] == list(DECLARED_HEIGHT_BOXES)
    for box in model.boxes:
        assert box.content_height <= box.declared_height, box.selector
    for selector in (".one .tag", ".one .tag.below"):
        assert model.box(selector).content_height == pytest.approx(28.0, abs=0.1)
        assert model.box(selector).declared_height == pytest.approx(34.02, abs=0.1)


def test_a_declared_height_box_with_no_content_model_raises():
    """A fourth declared-height box must be described, not silently skipped.

    This is what makes the guarantee general rather than two special cases: the
    developer who adds a height to a new `.one` selector is stopped here
    instead of getting a content check that quietly covers only the boxes
    somebody thought of in 2026.
    """
    with pytest.raises(StylesheetError, match="no content model"):
        measure_bar(_MINIMAL + ".one .badge { height:4mm; }\n", "close")


def test_the_bold_line_takes_its_line_height_from_the_tag_not_the_body():
    """The content heights stand on inheritance, so pin what it resolves to.

    `.one .tag b` declares a `font-size` and no `line-height`: the nearest
    ancestor declaring one is `.one .tag` at `1.2`, not `body` at `1.5`. Were
    `body` to win, the bold line would measure 20px instead of 16px and the
    28px content height would be wrong in the direction that hides overflow.
    """
    sheet = parse_css(CSS_BODY)
    assert inherited(sheet, ".one .tag b", "line-height") == "1.2"
    assert inherited(sheet, ".one .tag b", "font-size") == "10pt"
    assert inherited(sheet, ".one .tag.below", "font-size") == "7.5pt"
    assert inherited(sheet, ".one", "line-height") == "1.5"


def test_an_inherited_property_no_ancestor_declares_raises():
    """No defaults in the content model either."""
    with pytest.raises(StylesheetError, match="or any ancestor"):
        inherited(parse_css(".one .tag { height:9mm; }"), ".one .tag", "font-size")


@pytest.mark.parametrize(
    ("candidate", "target", "distance"),
    [
        (".one .tag", ".one .tag.below", 0),
        (".one", ".one .tag.below", 1),
        ("body", ".one .tag.below", 2),
        (".one .tag", ".one .tag b", 1),
        (".one .tag b", ".one .tag", None),
        (".one .seg.a", ".one .tag", None),
        (".one.close .ends", ".one .tag", None),
        (".grp li", ".one .tag", None),
        (".one + .tag", ".one .tag .x", None),
    ],
)
def test_what_the_inheritance_walk_counts_as_an_ancestor(candidate, target, distance):
    """Which selector inherits to which, since the content heights rest on it.

    `.one .tag` and `.one .tag.below` are one element, so the distance is `0`;
    a descendant never inherits upward; a sibling branch is unrelated. The last
    row is a recorded boundary: a combinator other than the descendant space
    leaves a compound with no simple selector in it, and the comparison
    declines the relation instead of guessing one.
    """
    assert _ancestor_distance(candidate, target) == distance


# --------------------------------------------------------------------------
# ER8 -- the fix does not cost materially more vertical space
# --------------------------------------------------------------------------


def test_the_close_case_bar_grows_by_at_most_six_millimetres():
    """The height guard, measured with the same model as everything else."""
    before = measure_bar(HEAD_ONE_FAMILY, "close").total_height
    after = measure_bar(CSS_BODY, "close").total_height
    # `total_height` is `None` outside the close cases -- both operands here are
    # close-case, and saying so keeps the subtraction below honest.
    assert before is not None
    assert after is not None
    assert after - before <= MAX_GROWTH_MM * PX_PER_MM


# --------------------------------------------------------------------------
# ER3, ER4 -- the stylesheet pins
# --------------------------------------------------------------------------


def test_the_close_layout_rules_are_pinned_as_an_exact_set():
    """Every close-scoped rule of `CSS_BODY`, byte for byte, and no others."""
    sheet = parse_css(CSS_BODY)
    scoped = tuple(
        (rule.selector, rule.declarations)
        for rule in sheet.rules + sheet.nested_rules
        if "close" in rule.selector or "below" in rule.selector
    )
    assert scoped == CLOSE_LAYOUT_RULES


def shared_rule_pairs(sheet: Stylesheet) -> list[list[str]]:
    """Every node whose selector mentions neither `close` nor `below`.

    An at-rule block contributes one pair -- its prelude and its whole raw
    body -- so a change anywhere inside `@media print` fails the comparison
    too.
    """
    pairs: list[list[str]] = []
    for node in sheet.nodes:
        if isinstance(node, AtRule):
            pairs.append([node.prelude, node.body])
        elif "close" not in node.selector and "below" not in node.selector:
            pairs.append([node.selector, node.declarations])
    return pairs


def test_every_shared_rule_is_byte_identical_to_the_head_baseline():
    """ER4: the far-apart layout consumes no rule this task changed."""
    expected = json.loads(SHARED_BASELINE.read_text(encoding="utf-8"))
    assert shared_rule_pairs(parse_css(CSS_BODY)) == expected
