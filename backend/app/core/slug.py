"""The condominium slug: one producer, one judge (APRAS-66 D-A / D-C.4).

A slug is the URL-safe address a condominium is reached by — ``/c/<slug>``,
which APRAS-69 will route. Two things live here and nothing else:

* :func:`slugify` — the **only** producer of a slug string from a name.
* :func:`is_valid_slug` — the **only** judge of a slug a person typed.

They share one 3-64 length rule, so they cannot disagree: ``slugify`` never
returns a value ``is_valid_slug`` would reject, and therefore no row can exist
that fails the rule its own API enforces. The floor is on the *slug* and not
on ``tenant.name``, which keeps ``min_length=1``: ``AB`` is a legitimate
condominium name and the operator's to choose, while the slug is our derived
artefact and ours to constrain.

Neither function ever touches the database. Uniqueness is
``TenantService``'s job (the ``-<n>`` walk of D-B) and the unique index's.

``alembic/versions/0002_tenant_slug.py`` carries a **frozen copy** of this
derivation on purpose — see the comment there. Changing the rules below does
not, and must not, change what that revision replays.
"""

import re
import unicodedata

#: The shortest slug that may be stored, shared by generated and typed values.
#: Below it, :func:`slugify` discards the derivation and uses
#: :data:`SLUG_FALLBACK_BASE` instead of padding, which would invent
#: characters the name does not contain.
SLUG_MIN_LENGTH = 3

#: The width of the ``tenant.slug`` column, and the longest slug a person may
#: type. 60 characters of derived base (:data:`SLUG_MAX_BASE_LENGTH`) plus
#: room for the ``-<n>`` uniqueness suffix.
SLUG_MAX_LENGTH = 64

#: How much of a derived slug survives truncation, leaving four characters of
#: the column for the suffix.
SLUG_MAX_BASE_LENGTH = 60

#: The base used whenever a derivation yields fewer than
#: :data:`SLUG_MIN_LENGTH` characters — an empty result (a name made only of
#: CJK, emoji or punctuation) or a short name such as ``AB``. It is a *base*,
#: not a final slug: the caller still resolves collisions, and
#: ``condominio-<n>`` only ever grows, so this path can neither fall under the
#: floor nor overflow the column.
SLUG_FALLBACK_BASE = "condominio"

#: Lowercase ASCII letters and digits in hyphen-separated groups: no leading,
#: trailing or doubled hyphen, no space, no accent, no uppercase, no
#: underscore. Applied with :func:`re.fullmatch`, never :func:`re.match`, so a
#: trailing newline cannot smuggle a tail past the ``$``.
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

#: Every maximal run of characters outside ``[a-z0-9]`` becomes one ``-``.
#: One rule, not a per-character table: punctuation, spaces, ``&``, ``/`` and
#: whatever did not fold to ASCII are all covered by it.
_SEPARATOR_RUN = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Derive a slug from a condominium name (D-A).

    NFKD-normalise and drop combining marks, fold to ASCII, lowercase,
    collapse every non-``[a-z0-9]`` run into a single ``-``, strip the edges,
    truncate to 60 characters and strip the edge again so a truncated slug
    never ends in a hyphen. A result under the floor is discarded in favour
    of :data:`SLUG_FALLBACK_BASE`.

    The return value always satisfies :func:`is_valid_slug`.
    """
    folded = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(ch for ch in folded if not unicodedata.combining(ch))
    ascii_only = ascii_only.encode("ascii", "ignore").decode("ascii")

    hyphenated = _SEPARATOR_RUN.sub("-", ascii_only.lower()).strip("-")
    truncated = hyphenated[:SLUG_MAX_BASE_LENGTH].strip("-")

    if len(truncated) < SLUG_MIN_LENGTH:
        return SLUG_FALLBACK_BASE
    return truncated


def is_valid_slug(value: str) -> bool:
    """Whether ``value`` is a slug this installation will store (D-C.4).

    The judge of a **typed** slug: a value outside the set is refused with a
    422 rather than quietly folded, because what a person sees accepted must
    be what is stored.
    """
    return (
        SLUG_MIN_LENGTH <= len(value) <= SLUG_MAX_LENGTH
        and SLUG_PATTERN.fullmatch(value) is not None
    )
