"""The brand-colour derivation and its contrast guarantee (APRAS-68).

`app/core/branding.py` is the **only** theme derivation in the repository: this
task's `PATCH /api/v1/tenant-profile` and APRAS-74's public `/c/<slug>`
endpoint both call `build_theme`, and the frontend ports the ratio function
alone (pinned from both sides by `tests/data/contrast_fixtures.json`).

Three defect classes are pinned by number here, because each of them fails
**silently**:

* **the double transfer** -- the inverse OKLCH conversion already yields
  linear-light channels, so applying the sRGB->linear transfer a second time
  *inflates* light-on-light ratios (4.29 reads 10.96) and would make an
  illegible palette pass;
* **the naive clip** -- CSS Color 4 §13 has the browser gamut-map an
  out-of-range `oklch()` by chroma reduction at constant L/H, so measuring a
  per-channel clip certifies a colour nobody paints;
* **measuring internal floats** -- every ratio below is measured on the
  emitted, rounded, gamut-snapped `oklch(...)` strings parsed back out of
  `build_theme`'s own output.
"""

import json
import math
import pathlib
import re

import pytest

from app.core.branding import (
    AUTHORED_KEYS,
    EMITTED_KEYS,
    GAMUT_TOLERANCE,
    MEASURED_PAIRS,
    MINIMUM_CONTRAST_RATIO,
    OklchColor,
    audit_contrast,
    build_theme,
    contrast_ratio,
    hex_to_oklch,
    is_in_gamut,
    is_valid_hex_color,
    normalize_hex_color,
    oklch_to_hex,
    oklch_to_linear_srgb,
    parse_oklch,
    relative_luminance,
    snap_to_gamut,
)
from app.core.exceptions import InvalidBrandThemeError

#: The nine inputs every simple-mode claim is made over: the near-white and
#: near-black extremes, a pure grey, a fully saturated blue, and the four real
#: brand colours the spec pins by name.
HOSTILE_INPUTS = (
    "#ffe680",
    "#ffffff",
    "#000000",
    "#808080",
    "#0000ff",
    "#10b981",
    "#857046",
    "#0ea5e9",
    "#7c3aed",
)

#: `oklch(L C H)` with **exactly** two decimals in each component, the
#: precision every value in `frontend/src/index.css` is authored at.
_EMITTED = re.compile(r"^oklch\((\d+\.\d{2}) (\d+\.\d{2}) (\d+\.\d{2})\)$")

_FIXTURE = pathlib.Path(__file__).parent / "data" / "contrast_fixtures.json"

#: The frontend half of the two-sided pin on the ratio function, named in the
#: failure message so a red run points at the file that moves with it.
_FRONTEND_CONTRAST = "frontend/src/lib/contrast.ts"

_GOOD_PALETTE = {
    "background": "#fffdf7",
    "foreground": "#1d1b16",
    "card": "#ffffff",
    "card-foreground": "#1d1b16",
    "primary": "#8a2b2b",
    "primary-foreground": "#fff7f5",
    "secondary": "#1f6f8b",
    "secondary-foreground": "#ffffff",
    "accent": "#e8ddc9",
    "accent-foreground": "#3a3128",
    "muted": "#f1ece4",
    "muted-foreground": "#5c5344",
    "border": "#e2d9c8",
}

#: Black-ish text on a near-black background, a yellow card under near-white
#: text: the palette the mock's "carregar paleta ilegível" button loads.
_BAD_PALETTE = {
    **_GOOD_PALETTE,
    "background": "#2b2b2b",
    "foreground": "#4a4a4a",
    "card": "#ffe680",
    "card-foreground": "#fff1a8",
    "primary": "#ffe680",
    "primary-foreground": "#ffffff",
    "secondary": "#1f6f8b",
    "secondary-foreground": "#3a7fa0",
    "muted-foreground": "#8a8a8a",
}


def simple(primary: str, accent: str) -> dict:
    return {"mode": "simple", "primary": primary, "accent": accent}


def advanced(light: dict, dark: dict | None = None) -> dict:
    return {"mode": "advanced", "light": dict(light), "dark": dark}


def measured(scheme: dict[str, str]) -> dict[str, float]:
    """Every measured pair's ratio, parsed back out of the emitted strings."""
    return {
        f"{fg}/{bg}": contrast_ratio(parse_oklch(scheme[fg]), parse_oklch(scheme[bg]))
        for fg, bg in MEASURED_PAIRS
    }


# ---------------------------------------------------------------------------
# The luminance rule, pinned by number (the double-transfer regression)
# ---------------------------------------------------------------------------


def test_the_shipped_muted_pair_measures_4_29_and_not_10_96():
    """`index.css`'s own `--muted-foreground`/`--muted`, measured.

    Under a second sRGB->linear transfer this reads **10.96**: the bug does
    not halve ratios, it inflates them for light-on-light pairs, which is
    exactly how it would neutralise both the repair loop and the advanced-mode
    refusal without a single red test elsewhere.
    """
    ratio = contrast_ratio(OklchColor(0.55, 0.02, 160.0), OklchColor(0.96, 0.01, 160.0))

    assert ratio == pytest.approx(4.29, abs=0.01)


def test_the_wcag_canonical_grey_on_white_measures_4_54():
    ratio = contrast_ratio(hex_to_oklch("#767676"), hex_to_oklch("#ffffff"))

    assert ratio == pytest.approx(4.54, abs=0.01)


def test_black_on_white_is_the_maximum_21_to_1():
    ratio = contrast_ratio(hex_to_oklch("#000000"), hex_to_oklch("#ffffff"))

    assert ratio == pytest.approx(21.0, abs=0.01)


def test_relative_luminance_runs_on_linear_light_channels():
    """The inverse conversion already yields linear light (BF-7).

    White's luminance is 1.0 exactly; a second transfer would leave it 1.0 too,
    so the discriminating case is mid-grey: `#808080` is 0.2159 linear, and
    0.0513 under a double transfer.
    """
    grey = oklch_to_linear_srgb(hex_to_oklch("#808080"))

    assert relative_luminance(grey) == pytest.approx(0.2159, abs=0.001)


# ---------------------------------------------------------------------------
# Conversion, rounding and the gamut snap
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", HOSTILE_INPUTS)
def test_hex_round_trips_through_oklch_within_one_8_bit_step(value: str):
    returned = oklch_to_hex(hex_to_oklch(value))

    for i in (1, 3, 5):
        original = int(value[i : i + 2], 16)
        assert abs(int(returned[i : i + 2], 16) - original) <= 1, returned


def test_the_pre_snap_triple_measures_above_aa_but_renders_below_it():
    """The round-3 defect, as one direct case (BF-4).

    `oklch(0.52 0.22 210)` is outside sRGB. A per-channel clip measures it at
    **4.52**; the browser's chroma reduction paints **3.74**. `contrast_ratio`
    must report what is painted, and the snap must mean no emitted scheme can
    ever contain the triple.
    """
    surface = OklchColor(0.52, 0.22, 210.0)
    text = OklchColor(0.15, 0.02, 210.0)

    assert not is_in_gamut(surface)
    assert contrast_ratio(surface, text) == pytest.approx(3.74, abs=0.01)

    clipped = [min(1.0, max(0.0, v)) for v in oklch_to_linear_srgb(surface)]
    naive = (relative_luminance(clipped) + 0.05) / (
        relative_luminance(oklch_to_linear_srgb(text)) + 0.05
    )
    assert naive == pytest.approx(4.52, abs=0.01)


def test_the_snap_rounds_to_two_places_then_reduces_chroma_into_gamut():
    snapped = snap_to_gamut(OklchColor(0.523, 0.224, 210.004))

    assert snapped.lightness == 0.52
    assert snapped.hue == 210.0
    assert is_in_gamut(snapped)
    assert snapped.chroma < 0.22
    assert round(snapped.chroma * 100) == snapped.chroma * 100


def test_a_saturated_green_emits_an_in_gamut_primary():
    """`#008a5a` is one of the three real hex inputs the old rule certified
    at 4.5129 while the browser painted 4.498."""
    scheme = build_theme(simple("#008a5a", "#0ea5e9"))["light"]

    assert is_in_gamut(parse_oklch(scheme["primary"]))
    assert measured(scheme)["primary-foreground/primary"] >= MINIMUM_CONTRAST_RATIO


@pytest.mark.parametrize("primary", HOSTILE_INPUTS)
def test_every_emitted_colour_is_in_gamut_and_two_decimals(primary: str):
    theme = build_theme(simple(primary, "#0ea5e9"))

    for scheme in theme.values():
        for name, value in scheme.items():
            assert _EMITTED.fullmatch(value), f"{name}: {value}"
            channels = oklch_to_linear_srgb(parse_oklch(value))
            assert all(
                -GAMUT_TOLERANCE <= channel <= 1 + GAMUT_TOLERANCE
                for channel in channels
            ), f"{name}: {value} -> {channels}"


# ---------------------------------------------------------------------------
# `build_theme`'s contract
# ---------------------------------------------------------------------------


def test_no_branding_derives_no_theme():
    assert build_theme(None) is None


def test_a_theme_is_a_light_and_a_dark_scheme_of_the_seventeen_variables():
    theme = build_theme(simple("#7c3aed", "#0ea5e9"))

    assert set(theme) == {"light", "dark"}
    for scheme in theme.values():
        assert set(scheme) == set(EMITTED_KEYS)
        assert len(scheme) == 17


def test_the_emitted_set_never_touches_a_semantic_token():
    """No `--destructive*`, no status, no priority, no `--radius`."""
    emitted = set(EMITTED_KEYS)

    assert not [key for key in emitted if key.startswith(("destructive", "status-"))]
    assert not [key for key in emitted if key.startswith(("priority-", "radius"))]
    assert set(AUTHORED_KEYS) < emitted
    assert len(AUTHORED_KEYS) == 13
    assert emitted - set(AUTHORED_KEYS) == {
        "popover",
        "popover-foreground",
        "input",
        "ring",
    }


def test_the_four_in_scheme_derivations_follow_their_sources():
    for scheme in build_theme(simple("#7c3aed", "#0ea5e9")).values():
        assert scheme["popover"] == scheme["card"]
        assert scheme["popover-foreground"] == scheme["card-foreground"]
        assert scheme["input"] == scheme["border"]
        assert scheme["ring"] == scheme["primary"]


def test_muted_is_no_longer_a_copy_of_secondary():
    """D-G's consequence: `--secondary` now carries the accent at full chroma,
    so the old `muted <- secondary` relationship is dropped."""
    for scheme in build_theme(simple("#7c3aed", "#0ea5e9")).values():
        assert scheme["muted"] != scheme["secondary"]


# ---------------------------------------------------------------------------
# Simple mode: the guarantee, measured on the emitted strings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("primary", HOSTILE_INPUTS)
def test_simple_mode_clears_every_measured_pair_for_every_hostile_accent(
    primary: str,
):
    """9 x 9 x 2 schemes, 8 pairs each: `audit_contrast` must be empty."""
    for accent in HOSTILE_INPUTS:
        theme = build_theme(simple(primary, accent))
        for name, scheme in theme.items():
            assert audit_contrast(scheme) == [], f"{primary}/{accent} {name}"


def test_857046_light_is_pinned_at_its_exact_emitted_pair():
    """Round 1's pin, unchanged: raw `L = 0.555` rounds to 0.56 and measures
    4.4073, so the loop steps once to 0.55."""
    scheme = build_theme(simple("#857046", "#0ea5e9"))["light"]

    assert scheme["primary"] == "oklch(0.55 0.06 83.88)"
    assert scheme["primary-foreground"] == "oklch(0.98 0.00 0.00)"
    assert measured(scheme)["primary-foreground/primary"] == pytest.approx(
        4.596, abs=0.01
    )


def test_the_accent_lands_on_secondary_at_full_chroma():
    """D-G: `#0ea5e9` is visible as a real surface, not as a 1% tint."""
    scheme = build_theme(simple("#7c3aed", "#0ea5e9"))["light"]

    assert scheme["secondary"] == "oklch(0.68 0.14 237.32)"
    assert scheme["secondary-foreground"] == "oklch(0.15 0.02 237.32)"
    assert oklch_to_hex(parse_oklch(scheme["secondary"])) == "#23a3e3"
    assert measured(scheme)["secondary-foreground/secondary"] >= 6.9


def test_accent_stays_the_pale_hover_tint_of_the_accent_hue():
    """Disclosed in the spec: the light `--accent` band is `#e3f6f5`-ish."""
    scheme = build_theme(simple("#7c3aed", "#0ea5e9"))["light"]
    accent = parse_oklch(scheme["accent"])

    assert accent.lightness >= 0.96
    assert accent.chroma <= 0.02
    assert accent.hue == parse_oklch(scheme["secondary"]).hue


def test_dark_is_derived_from_the_same_single_stored_colour():
    """(c): no second input, its own lightness rule, its own contrast pass."""
    theme = build_theme(simple("#0b3d2e", "#0ea5e9"))
    dark = theme["dark"]

    assert audit_contrast(dark) == []
    assert parse_oklch(dark["primary"]).lightness >= 0.62
    assert parse_oklch(dark["background"]).lightness == 0.14
    assert dark != theme["light"]


# ---------------------------------------------------------------------------
# Which side the repair moves, per pair (BF-1)
# ---------------------------------------------------------------------------


def test_the_muted_foreground_repair_moves_the_text_side_in_both_schemes():
    """`--muted`, `--background` and `--card` cannot move, so the text does.

    Today's default pair measures 4.2913 for **every** hue, so the loop
    engages for every simple-mode theme: light lands darker than 0.55, dark
    lighter than 0.65.
    """
    theme = build_theme(simple("#7c3aed", "#0ea5e9"))

    light = theme["light"]
    assert parse_oklch(light["muted"]) == OklchColor(0.96, 0.01, 293.01)
    assert parse_oklch(light["muted-foreground"]).lightness < 0.55

    # The dark pair starts legible, so the loop does not engage -- what is
    # asserted there is the **direction**: it may only ever move up, never
    # down onto the dark surfaces.
    dark = theme["dark"]
    assert parse_oklch(dark["muted"]) == OklchColor(0.22, 0.02, 293.01)
    assert parse_oklch(dark["muted-foreground"]).lightness >= 0.65

    for scheme in theme.values():
        ratios = measured(scheme)
        for surface in ("muted", "background", "card"):
            assert ratios[f"muted-foreground/{surface}"] >= MINIMUM_CONTRAST_RATIO


def test_the_brand_and_tint_repairs_move_the_non_text_side():
    """`--primary`, `--secondary` and `--accent` move; their foregrounds are
    picked once from two fixed candidates and then held."""
    scheme = build_theme(simple("#857046", "#0ea5e9"))["light"]

    # `#857046` starts at L 0.56 and is stepped down to 0.55 -- the surface
    # moved, while its foreground is still one of the two candidates.
    assert parse_oklch(scheme["primary"]).lightness == 0.55
    assert scheme["primary-foreground"] in {
        "oklch(0.98 0.00 0.00)",
        "oklch(0.15 0.02 83.88)",
    }
    assert scheme["secondary-foreground"] in {
        "oklch(0.98 0.00 0.00)",
        "oklch(0.15 0.02 237.32)",
    }
    # The tint surface, not the brand one: `--accent-foreground` is the fixed
    # `0.20 0.02 AH` constant, so any repair had to happen on `--accent`.
    assert scheme["accent-foreground"] == "oklch(0.20 0.02 237.32)"


@pytest.mark.parametrize("hue", range(0, 360, 30))
def test_the_page_level_pairs_never_repair_for_any_hue(hue: int):
    """`foreground`/`background` and `card-foreground`/`card` are constants on
    both sides and pass by construction, so they must come out untouched."""
    primary = oklch_to_hex(snap_to_gamut(OklchColor(0.55, 0.12, float(hue))))
    theme = build_theme(simple(primary, "#0ea5e9"))

    # Only a repair moves a lightness, so an untouched lightness *is* the
    # claim. The chromas are not asserted: the gamut snap legitimately takes
    # `0.98 0.01 H` down to a chroma of 0 near the top of the scale, and that
    # is the snap doing its job, not a repair.
    assert theme["light"]["background"] == "oklch(0.99 0.00 0.00)"
    assert theme["light"]["card"] == "oklch(1.00 0.00 0.00)"
    assert parse_oklch(theme["light"]["foreground"]).lightness == 0.14
    assert theme["light"]["card-foreground"] == theme["light"]["foreground"]
    assert parse_oklch(theme["dark"]["background"]).lightness == 0.14
    assert parse_oklch(theme["dark"]["card"]).lightness == 0.16
    assert parse_oklch(theme["dark"]["foreground"]).lightness == 0.98
    for scheme in theme.values():
        ratios = measured(scheme)
        assert ratios["foreground/background"] >= MINIMUM_CONTRAST_RATIO
        assert ratios["card-foreground/card"] >= MINIMUM_CONTRAST_RATIO


# ---------------------------------------------------------------------------
# The lattice sweeps: what is emittable, not what a case happened to try
# ---------------------------------------------------------------------------


def test_the_brand_surface_lattice_never_fails_and_never_leaves_the_gamut():
    """`L` x 0.01 x `C` x 0.01 x `H` x 5 degrees, light and dark.

    The rule shared by `--primary` and `--secondary`, over every triple the
    clamp of step 1 can produce. 0 failures and 0 out-of-gamut emissions is
    the whole guarantee; a spot check of nine colours is not.
    """
    worst = math.inf
    failures = 0
    out_of_gamut = 0

    for lightness_step in range(20, 93):
        for chroma_step in range(23):
            for hue_step in range(0, 360, 5):
                for dark in (False, True):
                    lightness = lightness_step / 100
                    surface, text = _brand_surface(
                        max(lightness, 0.62) if dark else lightness,
                        chroma_step / 100,
                        float(hue_step),
                    )
                    ratio = contrast_ratio(surface, text)
                    worst = min(worst, ratio)
                    failures += ratio < MINIMUM_CONTRAST_RATIO
                    out_of_gamut += not (is_in_gamut(surface) and is_in_gamut(text))

    assert failures == 0
    assert out_of_gamut == 0
    assert worst >= MINIMUM_CONTRAST_RATIO


def test_the_neutral_and_tint_lattice_never_fails():
    """Hue x accent chroma: the six pairs the brand surfaces do not cover."""
    worst = math.inf

    for hue_step in range(0, 360, 5):
        for chroma_step in range(23):
            for dark in (False, True):
                scheme = _neutral_scheme(float(hue_step), chroma_step / 100, dark=dark)
                for name, ratio in measured(scheme).items():
                    if name.startswith(("primary", "secondary")):
                        continue
                    worst = min(worst, ratio)

    assert worst >= MINIMUM_CONTRAST_RATIO


def _brand_surface(lightness: float, chroma: float, hue: float):
    """One brand surface and its foreground, as `build_theme` derives them."""
    from app.core.branding import derive_brand_surface

    return derive_brand_surface(OklchColor(lightness, chroma, hue))


def _neutral_scheme(hue: float, accent_chroma: float, *, dark: bool) -> dict[str, str]:
    """A whole scheme at one hue, with the accent chroma the sweep varies.

    Built through `build_theme` so the sweep measures emitted strings and not
    an internal shortcut: the primary is parked at a mid lightness and the
    accent carries the swept chroma at the same hue.
    """
    accent = oklch_to_hex(snap_to_gamut(OklchColor(0.60, accent_chroma, hue)))
    primary = oklch_to_hex(snap_to_gamut(OklchColor(0.55, 0.10, hue)))
    return build_theme(simple(primary, accent))["dark" if dark else "light"]


# ---------------------------------------------------------------------------
# Advanced mode: authored literally, measured, and refused
# ---------------------------------------------------------------------------


def test_advanced_emits_the_authored_colours_literally():
    """Step 1's clamp is a simple-mode **input** rule and is not applied here.

    A clamping implementation emits `oklch(0.54 0.22 293.01)` (`#7945df`) and
    fails this case.

    The criterion is the **exact** pinned string and hex, deliberately, and
    not a general "within one 8-bit step of the authored value": `#7c3aed`
    emits `#7c38ee`, which is *two* steps on green, and 2dp emission rounding
    can deviate by as much as 54 steps over the sweep (`#00e0e0` emits
    `#36dede`). The unrounded conversion round trip is a different claim, is
    exact, and is asserted separately above.
    """
    scheme = build_theme(advanced({**_GOOD_PALETTE, "primary": "#7c3aed"}))["light"]

    assert scheme["primary"] == "oklch(0.54 0.25 293.01)"
    assert oklch_to_hex(parse_oklch(scheme["primary"])) == "#7c38ee"


def test_advanced_accepts_a_readable_palette_and_measures_no_failure():
    theme = build_theme(advanced(_GOOD_PALETTE))

    assert audit_contrast(theme["light"]) == []
    assert audit_contrast(theme["dark"]) == []


def test_advanced_names_every_failing_pair_with_its_measured_ratio():
    failures = audit_contrast(build_theme(advanced(_BAD_PALETTE))["light"])

    named = {failure.pair: failure.ratio for failure in failures}
    assert "foreground/background" in named
    assert "card-foreground/card" in named
    assert "primary-foreground/primary" in named
    assert "secondary-foreground/secondary" in named
    for pair, ratio in named.items():
        assert ratio < MINIMUM_CONTRAST_RATIO, pair
    assert all(failure.minimum == MINIMUM_CONTRAST_RATIO for failure in failures)


def test_advanced_with_a_null_dark_falls_back_to_the_simple_dark_derivation():
    """(c): no per-variable inversion of a hand-authored palette."""
    authored = advanced(_GOOD_PALETTE, dark=None)

    derived = build_theme(authored)["dark"]
    expected = build_theme(simple(_GOOD_PALETTE["primary"], _GOOD_PALETTE["accent"]))[
        "dark"
    ]

    assert derived == expected


def test_advanced_with_a_supplied_dark_palette_is_measured_by_the_same_check():
    theme = build_theme(advanced(_GOOD_PALETTE, dark=_BAD_PALETTE))

    assert audit_contrast(theme["light"]) == []
    assert audit_contrast(theme["dark"]) != []


# ---------------------------------------------------------------------------
# The hex rule: case-insensitive in, lowercase stored
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["#ffe680", "#FFE680", "#FfE680", "#000000"])
def test_a_well_formed_hex_is_accepted_in_either_case(value: str):
    assert is_valid_hex_color(value)
    assert normalize_hex_color(value) == value.lower()


@pytest.mark.parametrize(
    "value",
    ["#GGG", "red", "#abc", "#abcd", "#abcdeff", "abcdef", "", "#ab cdef", "#-12345"],
)
def test_a_malformed_hex_is_refused_rather_than_repaired(value: str):
    assert not is_valid_hex_color(value)
    with pytest.raises(InvalidBrandThemeError):
        normalize_hex_color(value)


def test_build_theme_is_identical_for_the_uppercase_and_lowercase_objects():
    assert build_theme(simple("#FFE680", "#0EA5E9")) == build_theme(
        simple("#ffe680", "#0ea5e9")
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "simple", "primary": "#GGGGGG", "accent": "#0ea5e9"},
        {"mode": "simple", "primary": "red", "accent": "#0ea5e9"},
        {"mode": "simple", "primary": "#abc", "accent": "#0ea5e9"},
        {"mode": "simple", "primary": "#7c3aed"},
        {"mode": "simple", "primary": "#7c3aed", "accent": "#0ea5e9", "x": "#000000"},
        {"mode": "sparkle", "primary": "#7c3aed", "accent": "#0ea5e9"},
        {"primary": "#7c3aed", "accent": "#0ea5e9"},
        {"mode": "advanced", "light": dict.fromkeys(AUTHORED_KEYS[:12], "#123456")},
        {
            "mode": "advanced",
            "light": {
                **dict.fromkeys(AUTHORED_KEYS, "#123456"),
                "radius": "#123456",
            },
        },
        {"mode": "advanced", "light": {**_GOOD_PALETTE, "primary": "#nothex"}},
        {"mode": "advanced"},
    ],
)
def test_an_unusable_brand_theme_is_refused_by_the_single_judge(payload: dict):
    with pytest.raises(InvalidBrandThemeError):
        build_theme(payload)


@pytest.mark.parametrize("payload", ["#7c3aed", ["#7c3aed"], 7, True])
def test_a_brand_theme_that_is_not_an_object_at_all_is_refused(payload: object):
    """The shape is judged before any key is read.

    `None` is the one non-mapping that is *not* an error -- it is "this
    condominium has no colours" -- and it leaves through `build_theme`'s first
    line, never through here.
    """
    with pytest.raises(InvalidBrandThemeError):
        build_theme(payload)


@pytest.mark.parametrize(
    "value", ["#7c3aed", "rgb(1 2 3)", "oklch(0.5 0.1)", "oklch(a b c)", ""]
)
def test_parse_oklch_refuses_anything_that_is_not_an_emitted_string(value: str):
    """`audit_contrast` reads the emitted strings back out, so a value it
    cannot parse has to raise rather than silently measure a default."""
    with pytest.raises(InvalidBrandThemeError):
        parse_oklch(value)


def test_the_authored_key_set_is_exactly_the_thirteen_documented_names():
    assert AUTHORED_KEYS == (
        "background",
        "foreground",
        "card",
        "card-foreground",
        "primary",
        "primary-foreground",
        "secondary",
        "secondary-foreground",
        "accent",
        "accent-foreground",
        "muted",
        "muted-foreground",
        "border",
    )


def test_the_eight_measured_pairs_are_the_documented_ones():
    assert MEASURED_PAIRS == (
        ("foreground", "background"),
        ("card-foreground", "card"),
        ("primary-foreground", "primary"),
        ("secondary-foreground", "secondary"),
        ("accent-foreground", "accent"),
        ("muted-foreground", "muted"),
        ("muted-foreground", "background"),
        ("muted-foreground", "card"),
    )


# ---------------------------------------------------------------------------
# The cross-language fixture
# ---------------------------------------------------------------------------


def test_the_shared_fixture_matches_the_python_helper():
    """The backend half of the pin `frontend/src/lib/contrast.ts` reads.

    The same file is asserted by `contrast.test.ts`, so a TypeScript port that
    clips where Python gamut-maps fails over there on the out-of-gamut cases.
    """
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    assert fixture["minimum"] == MINIMUM_CONTRAST_RATIO
    assert any(not case["in_gamut"][0] for case in fixture["cases"]), (
        f"the fixture must keep an out-of-gamut triple, or {_FRONTEND_CONTRAST} "
        "could clip instead of chroma-reducing and still pass"
    )
    for case in fixture["cases"]:
        colours = [_fixture_colour(side) for side in (case["a"], case["b"])]
        assert contrast_ratio(*colours) == pytest.approx(case["ratio"], abs=0.01), (
            f"{case['name']}: {_FRONTEND_CONTRAST} pins the same number"
        )
        assert [is_in_gamut(colour) for colour in colours] == case["in_gamut"], case[
            "name"
        ]


def _fixture_colour(side: dict) -> OklchColor:
    if "hex" in side:
        return hex_to_oklch(side["hex"])
    return OklchColor(*side["oklch"])
