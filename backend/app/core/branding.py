"""The condominium's brand colours: one derivation, one measurement (APRAS-68).

This module owns every colour decision in the product:

* ``build_theme`` -- the **only** theme derivation in the repository. This
  task's ``GET``/``PATCH /api/v1/tenant-profile`` and APRAS-74's public
  ``/c/<slug>`` endpoint both call it; the frontend ports the ratio function
  alone and cannot produce a theme.
* ``audit_contrast`` -- the single WCAG 2.1 measurement, used both by the
  simple-mode repair loop and by the advanced-mode refusal.
* ``is_valid_hex_color`` / ``normalize_hex_color`` -- the single judge of a
  typed colour, mirrored (never duplicated) by the frontend's
  ``HEX_COLOR_PATTERN``, exactly as ``app/core/slug.py`` is.

Three rules carry the correctness of everything below, and each of them
closes a defect whose failure mode is silent:

1. **Luminance runs on linear light.** ``oklch_to_linear_srgb`` already
   returns linear-light channels, so the sRGB transfer must **not** be applied
   again. A double transfer does not halve ratios -- it *inflates* them for
   light-on-light pairs (the shipped ``--muted-foreground``/``--muted`` pair
   reads 4.29 correctly and 10.96 under the bug), which would make illegible
   palettes pass and neutralise both the repair loop and the 422.
2. **Round to 2dp, then snap into the sRGB gamut, and only then measure.**
   CSS Color 4 §13 requires a browser to gamut-map an out-of-range ``oklch()``
   by chroma reduction at constant ``L``/``H``, never by per-channel clipping,
   so an unsnapped string is painted as a colour nobody measured.
3. **Input is never trusted for a foreground.** The two brand foregrounds are
   picked from two fixed candidates; every other foreground is a constant.

The module deliberately imports nothing but :mod:`app.core.exceptions`: it has
to stay usable from a script, from a test with no database, and from the
public endpoint APRAS-74 adds.
"""

import math
import re
from collections.abc import Mapping
from typing import Any, NamedTuple

from app.core.exceptions import InvalidBrandThemeError

# ---------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------

#: ``#`` plus exactly six hex digits, **case-insensitive**. Brand guides
#: conventionally write hex uppercase, so refusing case would be a validation
#: error the síndico cannot act on; the value is lowercased before storage
#: instead. Mirrored by ``HEX_COLOR_PATTERN`` in
#: ``frontend/src/api/tenantProfile.ts``, which pre-validates and never
#: lowercases -- the server is the single normalisation point.
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

#: WCAG 2.1 AA for normal text. The 3:1 non-text minimum is out of scope:
#: ``border``, ``input`` and ``ring`` are not measured at all.
MINIMUM_CONTRAST_RATIO = 4.5

#: How far outside ``[0, 1]`` a linear channel may sit and still count as
#: inside the sRGB gamut -- floating-point slack, not a colour allowance.
GAMUT_TOLERANCE = 1e-4

#: The 13 colours advanced mode asks for, per scheme.
AUTHORED_KEYS = (
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

#: ``target -> source`` for the four variables that are a **copy** of another
#: colour in the same scheme. With :data:`BRAND_TEXT_KEY`, which is computed
#: rather than copied, they take 13 authored colours to 18 emitted ones.
DERIVED_FROM = {
    "popover": "card",
    "popover-foreground": "card-foreground",
    "input": "border",
    "ring": "primary",
}

#: The brand as **characters** (APRAS-88). ``--primary`` is a surface colour
#: and fails AA as normal text on every light surface -- 3.0427 on
#: ``--accent``, 3.4054 on ``--card``, 3.3091 on ``--background`` in the
#: default theme -- so the mapping table routes brand *text* here instead.
#: Derived, never authored: ``AUTHORED_KEYS`` stays at 13, so no stored
#: advanced palette breaks and no API request shape changes.
BRAND_TEXT_KEY = "primary-text"

#: The four surfaces brand text is rendered on, and the ones
#: :func:`derive_brand_text` must clear all of. ``--border`` is **not** one of
#: them: it carries no text (``--primary-text`` measures 4.1271 on it).
TEXT_SURFACE_KEYS = ("card", "background", "muted", "accent")

#: The 18 custom properties a theme emits per scheme -- the shadcn core of
#: ``:root``/``.dark`` plus ``--primary-text``, and nothing else.
#: ``--destructive*``, the 10 status tokens, the 8 priority tokens and
#: ``--radius`` are semantic and identical in every condominium, so they are
#: never overridden.
EMITTED_KEYS = (*AUTHORED_KEYS, *DERIVED_FROM, BRAND_TEXT_KEY)

#: The eight text/surface pairs ``audit_contrast`` measures, as
#: ``(foreground, background)``. ``--muted-foreground`` appears three times:
#: one token carries text over three surfaces, and none of the three can move.
#:
#: ``--primary-text`` is deliberately **absent** (APRAS-88). This tuple is the
#: 422 refusal contract, mirrored in ``frontend/src/lib/contrast.ts`` and
#: pinned by ``backend/tests/data/contrast_fixtures.json``; adding its four
#: pairs would start refusing advanced palettes that are stored and working
#: today. Its guard is :func:`derive_brand_text`'s non-convergence rule
#: instead, which can never emit a value that is worse than what the product
#: renders now.
MEASURED_PAIRS = (
    ("foreground", "background"),
    ("card-foreground", "card"),
    ("primary-foreground", "primary"),
    ("secondary-foreground", "secondary"),
    ("accent-foreground", "accent"),
    ("muted-foreground", "muted"),
    ("muted-foreground", "background"),
    ("muted-foreground", "card"),
)

SIMPLE_MODE = "simple"
ADVANCED_MODE = "advanced"

# -- the emittable grid ------------------------------------------------------

#: Every emitted component is rounded to this many decimals, the precision
#: every value in ``frontend/src/index.css`` is authored at.
_DECIMALS = 2
#: One step of the emittable grid, for both the chroma snap and every repair.
_STEP = 0.01
#: A hard bound on both loops. The repair always converges long before it
#: (lightness 0 against white and 1 against black both reach 21:1); the bound
#: exists so a future change cannot turn a mis-derivation into a hang.
_MAX_STEPS = 100

# -- the simple-mode input clamp (step 1) ------------------------------------
#
# Applied to the **two input colours only**, so that an extreme input still
# yields a usable hue. It is never applied to an authored advanced-mode
# colour: clamping there would turn an authored white into 0.92 and
# desaturate an authored purple.
_INPUT_MIN_LIGHTNESS = 0.20
_INPUT_MAX_LIGHTNESS = 0.92
_INPUT_MAX_CHROMA = 0.22

# -- the two fixed foreground candidates for a brand surface -----------------
_NEAR_WHITE = (0.98, 0.0, 0.0)
_NEAR_BLACK = (0.15, 0.02)

# -- the neutral family, per scheme (the table in the spec) ------------------
_LIGHT_BACKGROUND = (0.99, 0.0, 0.0)
_LIGHT_CARD = (1.0, 0.0, 0.0)
_LIGHT_FOREGROUND = (0.14, 0.01)
_LIGHT_MUTED = (0.96, 0.01)
_LIGHT_MUTED_FOREGROUND = (0.55, 0.02)
_LIGHT_BORDER = (0.92, 0.01)
_LIGHT_ACCENT_LIGHTNESS = 0.96
_LIGHT_ACCENT_CHROMA_SHARE = 0.1
_LIGHT_ACCENT_MIN_CHROMA = 0.01
_LIGHT_ACCENT_FOREGROUND = (0.20, 0.02)

_DARK_BACKGROUND = (0.14, 0.01)
_DARK_CARD = (0.16, 0.01)
_DARK_FOREGROUND = (0.98, 0.01)
_DARK_MUTED = (0.22, 0.02)
_DARK_MUTED_FOREGROUND = (0.65, 0.02)
_DARK_BORDER = (0.25, 0.02)
_DARK_ACCENT_LIGHTNESS = 0.22
_DARK_ACCENT_CHROMA_SHARE = 0.2
_DARK_ACCENT_MIN_CHROMA = 0.02
_DARK_ACCENT_FOREGROUND = (0.98, 0.01)
#: A brand surface in the dark scheme starts no darker than this, whatever the
#: tenant typed: the same colour that reads on white is unreadable on 0.14.
_DARK_BRAND_MIN_LIGHTNESS = 0.62

# -- conversion constants ----------------------------------------------------
_SRGB_KNEE = 0.04045
_LINEAR_KNEE = 0.0031308
_MAX_CHANNEL = 255
_FULL_TURN = 360.0
_LUMINANCE_OFFSET = 0.05
_WCAG_WEIGHTS = (0.2126, 0.7152, 0.0722)
#: The just-noticeable difference CSS Color 4 §13 allows a gamut-mapped
#: colour to keep from the requested one, in OKLab units.
_JND = 0.02
_BISECTION_EPSILON = 1e-5

_OKLCH_STRING = re.compile(
    r"^oklch\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)$"
)


class OklchColor(NamedTuple):
    """One colour in OKLCH: ``lightness`` 0-1, ``chroma`` >= 0, ``hue`` degrees."""

    lightness: float
    chroma: float
    hue: float


class ContrastFailure(NamedTuple):
    """One measured pair that does not reach :data:`MINIMUM_CONTRAST_RATIO`."""

    pair: str
    ratio: float
    minimum: float = MINIMUM_CONTRAST_RATIO


# ---------------------------------------------------------------------------
# The hex rule
# ---------------------------------------------------------------------------


def is_valid_hex_color(value: object) -> bool:
    """Whether ``value`` is ``#rrggbb``, in either case (never folded)."""
    return isinstance(value, str) and HEX_COLOR_PATTERN.fullmatch(value) is not None


def normalize_hex_color(value: object) -> str:
    """Validate a typed colour and return it lowercased, or raise.

    The single normalisation point: ``#FFE680`` is stored -- and returned by
    every read -- as ``#ffe680``.
    """
    if not is_valid_hex_color(value):
        raise InvalidBrandThemeError(f"'{value}' não é uma cor #rrggbb válida.")
    return str(value).lower()


# ---------------------------------------------------------------------------
# Colour conversion. Every function here returns **linear-light** channels.
# ---------------------------------------------------------------------------


def _srgb_to_linear(channel: float) -> float:
    if channel <= _SRGB_KNEE:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(channel: float) -> float:
    if channel <= _LINEAR_KNEE:
        return 12.92 * channel
    return 1.055 * channel ** (1 / 2.4) - 0.055


def _linear_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    red, green, blue = rgb
    long_ = math.cbrt(0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue)
    medium = math.cbrt(0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue)
    short = math.cbrt(0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue)
    return (
        0.2104542553 * long_ + 0.7936177850 * medium - 0.0040720468 * short,
        1.9779984951 * long_ - 2.4285922050 * medium + 0.4505937099 * short,
        0.0259040371 * long_ + 0.7827717662 * medium - 0.8086757660 * short,
    )


def oklch_to_linear_srgb(colour: OklchColor) -> tuple[float, float, float]:
    """OKLCH to **linear-light** sRGB, possibly outside ``[0, 1]``.

    The result is what :func:`relative_luminance` consumes directly: applying
    the sRGB transfer to it is the double-gamma bug rule 1 above names.
    """
    radians = math.radians(colour.hue)
    axis_a = colour.chroma * math.cos(radians)
    axis_b = colour.chroma * math.sin(radians)
    long_ = (colour.lightness + 0.3963377774 * axis_a + 0.2158037573 * axis_b) ** 3
    medium = (colour.lightness - 0.1055613458 * axis_a - 0.0638541728 * axis_b) ** 3
    short = (colour.lightness - 0.0894841775 * axis_a - 1.2914855480 * axis_b) ** 3
    return (
        4.0767416621 * long_ - 3.3077115913 * medium + 0.2309699292 * short,
        -1.2684380046 * long_ + 2.6097574011 * medium - 0.3413193965 * short,
        -0.0041960863 * long_ - 0.7034186147 * medium + 1.7076147010 * short,
    )


def hex_to_oklch(value: str) -> OklchColor:
    """Parse ``#rrggbb`` (either case) into OKLCH."""
    digits = normalize_hex_color(value)[1:]
    srgb = tuple(int(digits[i : i + 2], 16) / _MAX_CHANNEL for i in (0, 2, 4))
    lightness, axis_a, axis_b = _linear_to_oklab(
        tuple(_srgb_to_linear(channel) for channel in srgb)
    )
    return OklchColor(
        lightness,
        math.hypot(axis_a, axis_b),
        math.degrees(math.atan2(axis_b, axis_a)) % _FULL_TURN,
    )


def is_in_gamut(colour: OklchColor) -> bool:
    """Whether all three linear channels sit inside ``[0, 1] ± 1e-4``."""
    return all(
        -GAMUT_TOLERANCE <= channel <= 1 + GAMUT_TOLERANCE
        for channel in oklch_to_linear_srgb(colour)
    )


def _clip(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(min(1.0, max(0.0, channel)) for channel in rgb)


def gamut_map(colour: OklchColor) -> tuple[float, float, float]:
    """The linear-light colour a browser actually **paints** (CSS Color 4 §13).

    Chroma is bisected at constant lightness and hue until the result is
    inside sRGB, clipping only once the remaining error is under the JND --
    never a naive per-channel clip, which is a different colour: measured over
    the emittable lattice, the clip certifies 1,791 pairs at 4.5 or better
    that render below it.
    """
    if colour.lightness >= 1:
        return (1.0, 1.0, 1.0)
    if colour.lightness <= 0:
        return (0.0, 0.0, 0.0)
    if is_in_gamut(colour):
        return _clip(oklch_to_linear_srgb(colour))

    low, high = 0.0, colour.chroma
    radians = math.radians(colour.hue)
    while high - low > _BISECTION_EPSILON:
        middle = (low + high) / 2
        candidate = OklchColor(colour.lightness, middle, colour.hue)
        if is_in_gamut(candidate):
            low = middle
            continue
        clipped = _clip(oklch_to_linear_srgb(candidate))
        lightness, axis_a, axis_b = _linear_to_oklab(clipped)
        error = math.dist(
            (colour.lightness, middle * math.cos(radians), middle * math.sin(radians)),
            (lightness, axis_a, axis_b),
        )
        if error < _JND:
            return clipped
        high = middle
    # Reached only if the bisection closes without any out-of-gamut candidate
    # ever landing within the JND, which the geometry makes unreachable: a
    # candidate just above the boundary clips to an arbitrarily small error,
    # so the early return above always fires first. Kept anyway, because
    # `frontend/src/lib/contrast.ts` carries the same line and the two are
    # read side by side -- a missing fallback there would read as an omission
    # rather than as a proof.
    return _clip(  # pragma: no cover
        oklch_to_linear_srgb(OklchColor(colour.lightness, low, colour.hue))
    )


def oklch_to_hex(colour: OklchColor) -> str:
    """The ``#rrggbb`` a browser paints for ``colour`` -- for previews only."""
    channels = (
        round(min(1.0, max(0.0, _linear_to_srgb(channel))) * _MAX_CHANNEL)
        for channel in gamut_map(colour)
    )
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def relative_luminance(linear_rgb: tuple[float, float, float]) -> float:
    """WCAG 2.1 relative luminance of already-**linear** channels (rule 1)."""
    return sum(
        weight * channel
        for weight, channel in zip(_WCAG_WEIGHTS, linear_rgb, strict=True)
    )


def contrast_ratio(first: OklchColor, second: OklchColor) -> float:
    """The WCAG 2.1 ratio between two colours **as the browser paints them**."""
    luminances = sorted(
        relative_luminance(gamut_map(colour)) for colour in (first, second)
    )
    return (luminances[1] + _LUMINANCE_OFFSET) / (luminances[0] + _LUMINANCE_OFFSET)


# ---------------------------------------------------------------------------
# The emittable grid: round to 2dp, then snap into the gamut (rule 2)
# ---------------------------------------------------------------------------


def format_oklch(colour: OklchColor) -> str:
    """The CSS string that is emitted -- and the thing that gets measured."""
    return (
        f"oklch({colour.lightness:.{_DECIMALS}f} "
        f"{colour.chroma:.{_DECIMALS}f} {colour.hue:.{_DECIMALS}f})"
    )


def parse_oklch(value: str) -> OklchColor:
    """Read an emitted ``oklch(L C H)`` string back into a colour."""
    match = _OKLCH_STRING.fullmatch(value.strip())
    if match is None:
        raise InvalidBrandThemeError(f"'{value}' não é um valor oklch() emitido.")
    return OklchColor(*(float(group) for group in match.groups()))


def snap_to_gamut(colour: OklchColor) -> OklchColor:
    """Round every component to 2dp, then reduce chroma until it renders.

    Both halves happen **before** any measurement, and the repair loops
    re-apply this after every step, so the measured colour and the painted one
    are the same colour.
    """
    lightness = round(colour.lightness, _DECIMALS)
    chroma = round(colour.chroma, _DECIMALS)
    hue = round(colour.hue, _DECIMALS)
    snapped = OklchColor(lightness, chroma, hue)
    steps = 0
    while snapped.chroma > 0 and not is_in_gamut(snapped) and steps < _MAX_STEPS:
        snapped = OklchColor(lightness, round(snapped.chroma - _STEP, _DECIMALS), hue)
        steps += 1
    return snapped


def _at(pair: tuple[float, float], hue: float) -> OklchColor:
    """One ``(lightness, chroma)`` constant of the table, placed at ``hue``."""
    return snap_to_gamut(OklchColor(pair[0], pair[1], hue))


# ---------------------------------------------------------------------------
# The derivation (simple mode)
# ---------------------------------------------------------------------------


def _clamp_input(colour: OklchColor) -> tuple[float, float]:
    """Step 1's clamp -- **simple-mode inputs only**, never authored colours."""
    return (
        min(_INPUT_MAX_LIGHTNESS, max(_INPUT_MIN_LIGHTNESS, colour.lightness)),
        min(_INPUT_MAX_CHROMA, colour.chroma),
    )


def _pick_foreground(surface: OklchColor) -> OklchColor:
    """The better of near-white and near-black **for this surface**.

    Only the two brand surfaces use this rule. Taken as a blanket rule it
    would make ``--muted-foreground`` near-black and delete muted text from
    the product, which is why every other foreground is a listed constant.
    """
    white = OklchColor(*_NEAR_WHITE)
    black = _at(_NEAR_BLACK, surface.hue)
    return (
        white
        if contrast_ratio(surface, white) >= contrast_ratio(surface, black)
        else black
    )


def _repair_surface(surface: OklchColor, text: OklchColor) -> OklchColor:
    """Move the **non-text** side away from its foreground until it clears AA."""
    away = -_STEP if text.lightness > surface.lightness else _STEP
    current = surface
    for _ in range(_MAX_STEPS):
        if contrast_ratio(current, text) >= MINIMUM_CONTRAST_RATIO:
            break
        current = snap_to_gamut(
            OklchColor(current.lightness + away, current.chroma, current.hue)
        )
    return current


def _repair_text(
    text: OklchColor, surfaces: tuple[OklchColor, ...], *, down: bool
) -> OklchColor:
    """Move the **text** side until it clears AA against *every* surface.

    ``--muted-foreground`` is measured against ``--muted``, ``--background``
    and ``--card``, and none of the three may move: two are page-level and the
    third is a neutral the tenant did not choose.
    """
    step = -_STEP if down else _STEP
    current = text
    for _ in range(_MAX_STEPS):
        if all(
            contrast_ratio(current, surface) >= MINIMUM_CONTRAST_RATIO
            for surface in surfaces
        ):
            break
        current = snap_to_gamut(
            OklchColor(current.lightness + step, current.chroma, current.hue)
        )
    return current


def _clears_every_surface(text: OklchColor, surfaces: tuple[OklchColor, ...]) -> bool:
    return all(
        contrast_ratio(text, surface) >= MINIMUM_CONTRAST_RATIO for surface in surfaces
    )


def _walk_to_legible_text(
    text: OklchColor, surfaces: tuple[OklchColor, ...], *, step: float
) -> OklchColor | None:
    """One **bounded** lightness walk, or ``None`` if it never clears AA.

    Every candidate is re-snapped, so the value tested is the value emitted,
    and no step may leave ``[0.00, 1.00]``: an unbounded loop emits
    ``oklch(-0.38 0.00 160.00)`` on the palette ``test_branding`` pins, a
    negative lightness that ``parseOklch`` accepts downstream.

    **The budget has zero slack.** Crossing the whole 0.01 grid takes exactly
    ``_MAX_STEPS`` steps, so ``_MAX_STEPS + 1`` values have to be *tested* --
    the value the walk lands on included. One test fewer and the claim
    :func:`derive_brand_text` rests on, that the two walks jointly visit every
    emittable lightness, would be false at one end.
    """
    current = text
    for _ in range(_MAX_STEPS + 1):
        if _clears_every_surface(current, surfaces):
            return current
        lightness = round(current.lightness + step, _DECIMALS)
        if not 0.0 <= lightness <= 1.0:
            return None
        current = snap_to_gamut(OklchColor(lightness, current.chroma, current.hue))
    # Unreachable: a walk that has not converged runs into a bound first, at
    # the latest on the test above. Kept as the hard stop `_MAX_STEPS` is
    # documented to be, so a future change to `_STEP` cannot turn a
    # mis-derivation into a hang.
    return None  # pragma: no cover


def derive_brand_text(
    primary: OklchColor, surfaces: tuple[OklchColor, ...]
) -> OklchColor:
    """``--primary-text``: the brand, moved on the grid until it reads as text.

    Only lightness moves, so the tenant's hue and (gamut-snapped) chroma
    survive; the result must clear :data:`MINIMUM_CONTRAST_RATIO` against
    **all** of :data:`TEXT_SURFACE_KEYS`. Three rules, in order:

    1. two bounded walks are attempted, one **down** and one **up**;
    2. exactly one converging wins; both converging prefers **down**, a
       deterministic tie-break which is also the one that leaves every
       simple-mode value where it is;
    3. neither converging emits ``--primary`` **unchanged**.

    The direction is part of the rule and cannot be inherited: this function
    is called once per authored scheme and takes no ``dark`` flag, and a
    single walk "away from the surfaces" is simply wrong whenever the brand
    starts *between* them. Because the two walks between them visit every
    lightness on the emittable grid at this hue and chroma -- down covers
    ``[0.00, L]``, up covers ``[L, 1.00]`` -- rule 3 fires **iff** no legible
    value exists at all, and what it then emits is exactly what the product
    renders today.

    **There is no cushion in simple mode.** Over the emittable lattice the
    worst case is exactly 4.500005 in light (brand ``oklch(0.92 0.04 255)``)
    and 4.502344 in dark (brand ``oklch(0.00 0.22 300)``): that is the loop
    stopping at the first passing step, not margin. A change to ``_STEP``, to
    ``_LIGHT_MUTED`` or to ``_LIGHT_ACCENT_LIGHTNESS`` would land under AA
    silently, so both are pinned to the float in ``tests/test_branding.py``.

    Advanced mode carries **no** AA guarantee: a tenant authoring all 13
    colours can ask for a white card and a near-black accent, and no single
    colour clears both.
    """
    down = _walk_to_legible_text(primary, surfaces, step=-_STEP)
    if down is not None:
        return down
    up = _walk_to_legible_text(primary, surfaces, step=_STEP)
    if up is not None:
        return up
    return primary


def derive_brand_surface(start: OklchColor) -> tuple[OklchColor, OklchColor]:
    """One brand surface and its foreground: snap, pick once, repair.

    Shared by ``--primary`` and ``--secondary`` in both schemes, and the rule
    the lattice sweep in ``tests/test_branding.py`` exercises directly.
    """
    surface = snap_to_gamut(start)
    text = _pick_foreground(surface)
    return _repair_surface(surface, text), text


def _neutral_family(hue: float, accent_hue: float, accent_chroma: float, *, dark: bool):
    """The constants of one scheme's neutral + tint family, placed at the hues."""
    if dark:
        return {
            "background": _at(_DARK_BACKGROUND, hue),
            "card": _at(_DARK_CARD, hue),
            "foreground": _at(_DARK_FOREGROUND, hue),
            "muted": _at(_DARK_MUTED, hue),
            "muted-foreground": _at(_DARK_MUTED_FOREGROUND, hue),
            "border": _at(_DARK_BORDER, hue),
            "accent": snap_to_gamut(
                OklchColor(
                    _DARK_ACCENT_LIGHTNESS,
                    max(
                        _DARK_ACCENT_MIN_CHROMA,
                        round(accent_chroma * _DARK_ACCENT_CHROMA_SHARE, _DECIMALS),
                    ),
                    accent_hue,
                )
            ),
            "accent-foreground": _at(_DARK_ACCENT_FOREGROUND, accent_hue),
        }
    return {
        "background": snap_to_gamut(OklchColor(*_LIGHT_BACKGROUND)),
        "card": snap_to_gamut(OklchColor(*_LIGHT_CARD)),
        "foreground": _at(_LIGHT_FOREGROUND, hue),
        "muted": _at(_LIGHT_MUTED, hue),
        "muted-foreground": _at(_LIGHT_MUTED_FOREGROUND, hue),
        "border": _at(_LIGHT_BORDER, hue),
        "accent": snap_to_gamut(
            OklchColor(
                _LIGHT_ACCENT_LIGHTNESS,
                max(
                    _LIGHT_ACCENT_MIN_CHROMA,
                    round(accent_chroma * _LIGHT_ACCENT_CHROMA_SHARE, _DECIMALS),
                ),
                accent_hue,
            )
        ),
        "accent-foreground": _at(_LIGHT_ACCENT_FOREGROUND, accent_hue),
    }


def _simple_scheme(
    primary_input: OklchColor, accent_input: OklchColor, *, dark: bool
) -> dict[str, OklchColor]:
    """One scheme derived from the two stored colours and nothing else."""
    primary_lightness, primary_chroma = _clamp_input(primary_input)
    accent_lightness, accent_chroma = _clamp_input(accent_input)
    hue = round(primary_input.hue, _DECIMALS)
    accent_hue = round(accent_input.hue, _DECIMALS)

    family = _neutral_family(hue, accent_hue, accent_chroma, dark=dark)
    if dark:
        primary_lightness = max(primary_lightness, _DARK_BRAND_MIN_LIGHTNESS)
        accent_lightness = max(accent_lightness, _DARK_BRAND_MIN_LIGHTNESS)

    primary, primary_text = derive_brand_surface(
        OklchColor(primary_lightness, primary_chroma, hue)
    )
    secondary, secondary_text = derive_brand_surface(
        OklchColor(accent_lightness, accent_chroma, accent_hue)
    )

    scheme = {
        "background": family["background"],
        "foreground": family["foreground"],
        "card": family["card"],
        "card-foreground": family["foreground"],
        "primary": primary,
        "primary-foreground": primary_text,
        "secondary": secondary,
        "secondary-foreground": secondary_text,
        "accent": _repair_surface(family["accent"], family["accent-foreground"]),
        "accent-foreground": family["accent-foreground"],
        "muted": family["muted"],
        "muted-foreground": _repair_text(
            family["muted-foreground"],
            (family["muted"], family["background"], family["card"]),
            down=not dark,
        ),
        "border": family["border"],
    }
    return _with_derived(scheme)


def _advanced_scheme(palette: Mapping[str, str]) -> dict[str, OklchColor]:
    """The 13 authored colours, emitted literally (only 2dp + the gamut snap).

    Step 1's clamp is **not** applied: an authored ``#7c3aed`` emits
    ``oklch(0.54 0.25 293.01)``, not the clamped ``oklch(0.54 0.22 293.01)``.
    """
    scheme = {key: snap_to_gamut(hex_to_oklch(palette[key])) for key in AUTHORED_KEYS}
    return _with_derived(scheme)


def _with_derived(scheme: dict[str, OklchColor]) -> dict[str, OklchColor]:
    """The five in-scheme derivations, for **both** modes.

    ``_simple_scheme`` and ``_advanced_scheme`` end here and nowhere else, so
    ``--primary-text`` is derived once, by the same rule, for a brand the
    síndico typed and for a palette a tenant authored.
    """
    for target, source in DERIVED_FROM.items():
        scheme[target] = scheme[source]
    scheme[BRAND_TEXT_KEY] = derive_brand_text(
        scheme["primary"], tuple(scheme[key] for key in TEXT_SURFACE_KEYS)
    )
    return scheme


def _emit(scheme: Mapping[str, OklchColor]) -> dict[str, str]:
    return {key: format_oklch(scheme[key]) for key in EMITTED_KEYS}


# ---------------------------------------------------------------------------
# The measurement
# ---------------------------------------------------------------------------


def audit_contrast(scheme: Mapping[str, str]) -> list[ContrastFailure]:
    """Measure the 8 pairs of one **emitted** scheme, in document order.

    It parses the emitted ``oklch(...)`` strings back out rather than reading
    any internal float, so what is asserted is what the browser receives.
    """
    failures = []
    for foreground, background in MEASURED_PAIRS:
        ratio = contrast_ratio(
            parse_oklch(scheme[foreground]), parse_oklch(scheme[background])
        )
        if ratio < MINIMUM_CONTRAST_RATIO:
            failures.append(
                ContrastFailure(f"{foreground}/{background}", round(ratio, _DECIMALS))
            )
    return failures


# ---------------------------------------------------------------------------
# Validation and the entry point
# ---------------------------------------------------------------------------


def _normalized_palette(palette: object) -> dict[str, str]:
    if not isinstance(palette, Mapping) or set(palette) != set(AUTHORED_KEYS):
        raise InvalidBrandThemeError(
            "A paleta avançada precisa de exatamente estas 13 chaves: "
            + ", ".join(AUTHORED_KEYS)
        )
    return {key: normalize_hex_color(palette[key]) for key in AUTHORED_KEYS}


def normalize_brand_theme(raw: object) -> dict[str, Any]:
    """Validate a stored or submitted branding object and lowercase it.

    The single judge: a malformed hex, a missing or unknown key and an unknown
    ``mode`` all leave here as :class:`InvalidBrandThemeError`, which the
    handler maps to 422.
    """
    if not isinstance(raw, Mapping):
        raise InvalidBrandThemeError("As cores da marca precisam ser um objeto.")

    mode = raw.get("mode")
    if mode == SIMPLE_MODE:
        if set(raw) != {"mode", "primary", "accent"}:
            raise InvalidBrandThemeError(
                "O modo simples aceita exatamente 'primary' e 'accent'."
            )
        return {
            "mode": SIMPLE_MODE,
            "primary": normalize_hex_color(raw["primary"]),
            "accent": normalize_hex_color(raw["accent"]),
        }
    if mode == ADVANCED_MODE:
        if not set(raw) <= {"mode", "light", "dark"} or "light" not in raw:
            raise InvalidBrandThemeError(
                "O modo avançado aceita 'light' e, opcionalmente, 'dark'."
            )
        dark = raw.get("dark")
        return {
            "mode": ADVANCED_MODE,
            "light": _normalized_palette(raw["light"]),
            "dark": None if dark is None else _normalized_palette(dark),
        }
    raise InvalidBrandThemeError(f"Modo de cores desconhecido: '{mode}'.")


def build_theme(brand_theme: object) -> dict[str, dict[str, str]] | None:
    """The tenant's whole branding object in, the two emitted schemes out.

    ``build_theme(None) is None`` -- a tenant with no branding gets no theme
    and the client injects no element at all. Otherwise the return is
    ``{"light": {...}, "dark": {...}}``, keys being CSS variable names without
    the leading ``--`` and values ``oklch(L C H)`` strings at 2dp.

    This is the function APRAS-74's public endpoint calls: one positional
    argument, one return shape, one derivation in the repository.
    """
    if brand_theme is None:
        return None

    theme = normalize_brand_theme(brand_theme)
    if theme["mode"] == SIMPLE_MODE:
        primary = hex_to_oklch(theme["primary"])
        accent = hex_to_oklch(theme["accent"])
        return {
            "light": _emit(_simple_scheme(primary, accent, dark=False)),
            "dark": _emit(_simple_scheme(primary, accent, dark=True)),
        }

    light = theme["light"]
    dark = theme["dark"]
    if dark is None:
        # No per-variable inversion of a hand-authored palette can preserve
        # either the tenant's intent or its contrast, so the one derivation
        # this task proves correct is the fallback.
        #
        # **The second argument is the authored ``accent``, not the authored
        # ``secondary``**, and that is a decision rather than an oversight.
        # The spec's expected result requires this scheme to be *byte-identical*
        # to ``_simple_scheme`` fed with the authored primary and accent, and a
        # test asserts exactly that -- so the key is fixed by the contract. It
        # is also the conservative reading: in advanced mode ``accent`` is the
        # pale hover tint, so the derived dark ``--secondary`` comes out near
        # the tint's lightness rather than at the brand's full chroma. Nothing
        # renders it today (``.dark`` is declared and never applied), and the
        # alternative -- feeding ``secondary`` -- would silently produce a dark
        # palette the tenant never authored *and* break the stated equality.
        # Revisit when a dark-mode toggle ships, with the expected result.
        dark_scheme = _simple_scheme(
            hex_to_oklch(light["primary"]), hex_to_oklch(light["accent"]), dark=True
        )
    else:
        dark_scheme = _advanced_scheme(dark)
    return {"light": _emit(_advanced_scheme(light)), "dark": _emit(dark_scheme)}
