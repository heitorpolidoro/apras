"""The slug derivation and its validation rule (APRAS-66 D-A, D-C.4).

One producer, `slugify`, and one judge, `is_valid_slug`, sharing a single
3-64 length rule. The invariant the whole task leans on is asserted here
directly: `slugify` never returns a value `is_valid_slug` would reject, so no
row can exist that fails the rule its own API enforces.
"""

import pytest

from app.core.slug import (
    SLUG_FALLBACK_BASE,
    SLUG_MAX_LENGTH,
    SLUG_MIN_LENGTH,
    SLUG_PATTERN,
    is_valid_slug,
    slugify,
)

#: `(name, expected slug)`, the table D-A is specified by. Every entry is
#: also fed through the `is_valid_slug(slugify(name))` invariant below.
DERIVATIONS = (
    # Accents fold, never drop the letter (NFKD + combining-mark removal).
    ("Condomínio Padrão", "condominio-padrao"),
    ("Condomínio Solar da Serra", "condominio-solar-da-serra"),
    ("Associação", "associacao"),
    # A maximal run of anything outside [a-z0-9] collapses into one hyphen.
    ("Res.  Altos da Serra VI!", "res-altos-da-serra-vi"),
    ("Jardim & Flores / Bloco 2", "jardim-flores-bloco-2"),
    ("  ---Altos da Serra---  ", "altos-da-serra"),
    ("Bloco  2", "bloco-2"),
    # An already-valid slug survives untouched.
    ("altos-da-serra", "altos-da-serra"),
    # Under the floor, so the `condominio` base replaces it entirely.
    ("AB", SLUG_FALLBACK_BASE),
    ("Ré", SLUG_FALLBACK_BASE),
    ("A!", SLUG_FALLBACK_BASE),
    ("!!!", SLUG_FALLBACK_BASE),
    ("", SLUG_FALLBACK_BASE),
    ("   ", SLUG_FALLBACK_BASE),
    # Nothing folds to ASCII: CJK and emoji both reduce to nothing.
    ("東京", SLUG_FALLBACK_BASE),
    ("🏢🏢", SLUG_FALLBACK_BASE),
    # Exactly at the floor, so it is kept. `A. B` is deliberately spelled out:
    # the spec's D-A test criteria list it among the "fewer than 3 characters"
    # cases, but D-A's own steps make the separator run a hyphen the floor
    # counts, so it derives `a-b` — three characters, valid, kept. The rule is
    # mechanical and the parenthetical example was the thing that was wrong.
    ("abc", "abc"),
    ("A-B-C", "a-b-c"),
    ("A. B", "a-b"),
)


@pytest.mark.parametrize(("name", "expected"), DERIVATIONS)
def test_slugify_derives_the_specified_slug(name: str, expected: str):
    assert slugify(name) == expected


@pytest.mark.parametrize(("name", "_expected"), DERIVATIONS)
def test_every_derived_slug_satisfies_the_validation_rule(name: str, _expected: str):
    """The invariant, stated directly: the producer never beats the judge."""
    assert is_valid_slug(slugify(name))


def test_a_long_name_is_truncated_to_sixty_and_never_ends_in_a_hyphen():
    """60 characters of base leaves room in `VARCHAR(64)` for `-<n>`."""
    name = "Condomínio Residencial Jardim das Acácias Fase II Bloco Central Norte"
    derived = slugify(name)

    assert len(derived) <= 60
    assert not derived.endswith("-")
    assert derived == "condominio-residencial-jardim-das-acacias-fase-ii-bloco-cent"


def test_truncation_that_lands_on_a_hyphen_strips_it():
    """The 61st character being a separator must not leave a trailing `-`."""
    # 59 `x`, a separator, then more: the 60th character of the base is the
    # hyphen, so truncation alone would leave `xxx...x-`.
    derived = slugify(("x" * 59) + " yz")

    assert derived == "x" * 59
    assert is_valid_slug(derived)
    # And the case where the cut lands mid-group, which keeps all 60.
    assert slugify(("x" * 60) + " y") == "x" * 60


def test_the_fallback_base_is_itself_valid_and_inside_the_column():
    """`condominio` is 10 characters, so `condominio-<n>` can never overflow."""
    assert is_valid_slug(SLUG_FALLBACK_BASE)
    assert len(SLUG_FALLBACK_BASE) < SLUG_MAX_LENGTH
    assert SLUG_MIN_LENGTH == 3
    assert SLUG_MAX_LENGTH == 64


@pytest.mark.parametrize(
    "value",
    [
        "altos-da-serra",
        "bloco-2",
        "abc",
        "a-b-c",
        "2026",
        "condominio-padrao",
        "a" * 64,
    ],
)
def test_is_valid_slug_accepts(value: str):
    assert is_valid_slug(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ab",  # under the 3-character floor
        "a" * 65,  # over the 64-character column
        "Altos",  # uppercase
        "altos da serra",  # space
        "altos--da-serra",  # doubled hyphen
        "-altos",  # leading hyphen
        "altos-",  # trailing hyphen
        "altos_da_serra",  # underscore
        "condomínio",  # accent
        "altos.da.serra",  # dot
        "altos/serra",  # slash
        "altos serra ",  # trailing space
    ],
)
def test_is_valid_slug_rejects(value: str):
    assert not is_valid_slug(value)


def test_the_pattern_is_anchored_so_a_newline_cannot_smuggle_a_tail():
    """`re.match` alone would accept `"abc\\nAltos"`; the rule must not."""
    assert SLUG_PATTERN.pattern.startswith("^")
    assert SLUG_PATTERN.pattern.endswith("$")
    assert not is_valid_slug("abc\nAltos")
    # `re.match` with a `$` would also accept a bare trailing newline.
    assert not is_valid_slug("abc\n")


# ---------------------------------------------------------------------------
# The model's construction-time fallback (APRAS-66 Approach)
# ---------------------------------------------------------------------------


def test_constructing_a_tenant_without_a_slug_derives_one_from_the_name():
    """The twelve direct `Tenant(name=...)` constructions in `tests/` and
    `seed_demo.py` keep working: the fallback never consults the database."""
    from app.models.tenant import Tenant

    assert Tenant(name="Condomínio Padrão").slug == "condominio-padrao"
    assert Tenant(name="AB").slug == SLUG_FALLBACK_BASE


def test_an_explicit_slug_wins_over_the_derivation():
    from app.models.tenant import Tenant

    assert Tenant(name="Condomínio Padrão", slug="outro-slug").slug == "outro-slug"


def test_the_column_is_sixty_four_wide_unique_and_indexed():
    """`VARCHAR(64)`: 60 of base plus room for the `-<n>` suffix."""
    from app.models.tenant import Tenant

    column = Tenant.__table__.columns["slug"]

    assert column.type.length == SLUG_MAX_LENGTH
    assert column.nullable is False
    assert column.unique is True
    assert column.index is True


# ---------------------------------------------------------------------------
# Collision resolution when the **system** chooses (APRAS-66 D-B)
# ---------------------------------------------------------------------------


def _create(session, name: str):
    from app.schemas.tenant import TenantCreate
    from app.services.tenant_service import TenantService

    return TenantService.create_tenant(session, TenantCreate(name=name))


def test_three_tenants_sharing_a_base_get_x_then_x2_then_x3(session):
    """The smallest free integer from 2 up, not a counter and not a hash."""
    first = _create(session, "Altos da Serra")
    second = _create(session, "Altos  da  Serra!")
    third = _create(session, "altos da serra.")

    assert [first.slug, second.slug, third.slug] == [
        "altos-da-serra",
        "altos-da-serra-2",
        "altos-da-serra-3",
    ]


def test_the_smallest_free_integer_is_reused_after_a_gap(session):
    """`-2` freed by an edit is taken again, which a counter would skip."""
    first = _create(session, "Altos da Serra")
    second = _create(session, "Altos  da  Serra!")
    third = _create(session, "altos da serra.")

    second.slug = "outro-endereco"
    session.add(second)
    session.commit()

    fourth = _create(session, "ALTOS DA SERRA")

    assert fourth.slug == "altos-da-serra-2"
    assert third.slug == "altos-da-serra-3"
    assert first.slug == "altos-da-serra"


def test_two_tenants_can_never_share_a_slug(session):
    """The unique index is the arbiter, asserted against the database itself
    and not only through the service."""
    from sqlalchemy.exc import IntegrityError

    from app.models.tenant import Tenant

    first = _create(session, "Altos da Serra")

    session.add(Tenant(name="Um Nome Totalmente Outro", slug=first.slug))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_a_short_name_is_created_with_the_fallback_base_then_suffixed(session):
    """A tenant named `AB` gets `condominio`, never a two-character slug."""
    first = _create(session, "AB")
    second = _create(session, "CD")

    assert first.slug == SLUG_FALLBACK_BASE
    assert second.slug == f"{SLUG_FALLBACK_BASE}-2"
    assert is_valid_slug(first.slug)
    assert is_valid_slug(second.slug)


def test_a_suffix_never_pushes_the_slug_past_the_column(session):
    """A 60-character base plus `-<n>` stays inside `VARCHAR(64)`."""
    from app.services.tenant_service import TenantService

    base = "x" * 60
    # Every `-2` .. `-999` taken, so the walk has to reach a four-digit
    # suffix, which no longer fits beside 60 characters of base.
    taken = {base} | {f"{base}-{n}" for n in range(2, 1000)}

    candidate = TenantService.first_free_slug(base, taken)

    assert candidate == ("x" * 59) + "-1000"
    assert len(candidate) <= SLUG_MAX_LENGTH
    assert is_valid_slug(candidate)


def test_a_duplicate_name_is_still_409_before_any_slug_is_computed(session):
    from app.core.exceptions import TenantAlreadyExistsError

    _create(session, "Altos da Serra")

    with pytest.raises(TenantAlreadyExistsError):
        _create(session, "Altos da Serra")


# ---------------------------------------------------------------------------
# The unique index has the last word (APRAS-66 D-B, D-C.3)
# ---------------------------------------------------------------------------


def test_a_candidate_lost_to_a_race_is_recomputed_and_the_create_succeeds(
    session, monkeypatch
):
    """The index, not the read, is the arbiter: an `IntegrityError` on insert
    is retried with a recomputed suffix rather than surfaced."""
    from app.services.tenant_service import TenantService

    _create(session, "Altos da Serra")

    answers = iter(["altos-da-serra", "altos-da-serra-2"])
    monkeypatch.setattr(
        TenantService,
        "generated_slug",
        classmethod(lambda *_args, **_kwargs: next(answers)),
    )

    created = _create(session, "Outro Nome Qualquer")

    assert created.slug == "altos-da-serra-2"


def test_a_create_that_cannot_settle_fails_loudly_instead_of_looping(
    session, monkeypatch
):
    """Bounded retries: after `SLUG_INSERT_ATTEMPTS` the create raises."""
    from app.core.exceptions import SlugAlreadyTakenError
    from app.services.tenant_service import TenantService

    _create(session, "Altos da Serra")
    monkeypatch.setattr(
        TenantService,
        "generated_slug",
        classmethod(lambda *_args, **_kwargs: "altos-da-serra"),
    )

    with pytest.raises(SlugAlreadyTakenError):
        _create(session, "Outro Nome Qualquer")


def test_a_typed_slug_lost_to_a_race_surfaces_as_the_same_409(session):
    """Never a suffix walk on the typed path, not even under a race: the
    `IntegrityError` becomes the very `SlugAlreadyTakenError` the pre-check
    would have raised a moment earlier."""
    from app.core.exceptions import SlugAlreadyTakenError
    from app.services.tenant_service import TenantService

    holder = _create(session, "Altos da Serra")
    mover = _create(session, "Outro Nome Qualquer")
    before = mover.slug

    # Straight into the writer, which is exactly the state a racing insert
    # leaves: validation passed, the value is gone by the time we commit.
    with pytest.raises(SlugAlreadyTakenError):
        TenantService._write_slug(session, mover, holder.slug)

    session.rollback()
    session.expire_all()
    assert session.get(type(mover), mover.id).slug == before
