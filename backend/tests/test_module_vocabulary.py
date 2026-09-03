"""The module vocabulary derived from the permission catalogue (APRAS-39 §2).

`MODULES` is not a hand-written list: it is exactly the set of `<module>`
segments the catalogue already spells, so a module introduced by a future task
is toggleable (and active) the day its first permission exists, with nobody
having to remember a second list. These cases are what keeps that derivation
honest and what catches a typo in `CORE_MODULES`.
"""

from app.core.permissions import (
    CORE_MODULES,
    MODULES,
    PERMISSIONS,
    TOGGLEABLE_MODULES,
    filter_by_modules,
    module_of,
)


def test_modules_are_derived_from_the_catalogue():
    """`MODULES` is the catalogue's own module set, nothing added or dropped."""
    assert {module_of(permission) for permission in PERMISSIONS} == MODULES
    assert len(MODULES) == 26


def test_core_modules_are_three_and_real():
    """Identity, membership and the authorization vocabulary itself.

    Disabling any of them would make the tenant unadministrable from inside —
    no user list, no role editor, no tenant switcher — and would strip the
    very permissions an operator needs to turn it back on from the tenant
    side. Post-F5 the identity module is `roles`, not `user_types`; the
    subset assertion is what catches a stale name.
    """
    assert {"tenants", "users", "roles"} == CORE_MODULES
    assert CORE_MODULES <= MODULES


def test_toggleable_modules_partition_the_catalogue():
    """The 23 billable features and the 3 core ones tile `MODULES` exactly."""
    assert TOGGLEABLE_MODULES | CORE_MODULES == MODULES
    assert not (TOGGLEABLE_MODULES & CORE_MODULES)
    assert len(TOGGLEABLE_MODULES) == 23


def test_filter_by_modules_removes_exactly_one_module():
    """Disabling `finance` drops the 11 `finance:*` strings and nothing else."""
    kept = filter_by_modules(PERMISSIONS, {"finance"})
    dropped = PERMISSIONS - kept

    assert dropped == {p for p in PERMISSIONS if module_of(p) == "finance"}
    assert len(dropped) == 11
    assert kept == PERMISSIONS - dropped


def test_filter_by_modules_keeps_uncatalogued_strings():
    """A hand-edited row's unknown string survives a filter that is not about it.

    `get_effective_permissions` documents "unknown strings are kept as is";
    the filter removes only what an operator explicitly turned off, which is
    what preserves that property.
    """
    kept = filter_by_modules({"legacy:thing", "finance:read"}, {"finance"})

    assert kept == {"legacy:thing"}


def test_filter_by_modules_on_an_empty_disabled_set_is_the_identity():
    """`[]` is the all-on state, so the strip is a no-op there."""
    assert filter_by_modules(PERMISSIONS, frozenset()) == PERMISSIONS


def test_every_permission_belongs_to_a_declared_module():
    """No catalogue string can name a module the vocabulary does not know."""
    assert {module_of(p) for p in PERMISSIONS} <= MODULES
    assert len(PERMISSIONS) == 159


#: The 26 module names, spelled out. Deliberately a literal and not a
#: derivation: it is the **other half** of the i18n pin
#: (`frontend/src/i18n/__tests__/index.test.ts`), which compares the label
#: files against the same 26 names from its own local constant. Neither side
#: can derive from the other across the language boundary, so a catalogue
#: module added without a label has to fail *here* — with a message naming the
#: file to edit — rather than ship an unlabelled checkbox.
EXPECTED_MODULE_NAMES = frozenset(
    {
        "access_control",
        "announcements",
        "assemblies",
        "assets",
        "authorizations",
        "categories",
        "documents",
        "feedback",
        "finance",
        "gate",
        "inventory",
        "lots",
        "occurrences",
        "packages",
        "projects",
        "purchases",
        "reservations",
        "residents",
        "roles",
        "spaces",
        "tasks",
        "tenants",
        "uploads",
        "users",
        "visitors",
        "votes",
    }
)


def test_the_catalogue_modules_are_the_ones_the_ui_labels():
    """A new catalogue module must be labelled in pt **and** en before it ships.

    The frontend asserts `modules.names` carries exactly these 26 keys in both
    languages. This is the backend end of the same pin: adding a permission in
    a 27th module turns this red first, and the failure says where to go.
    """
    assert MODULES == EXPECTED_MODULE_NAMES, (
        "the catalogue's modules changed. Update EXPECTED_MODULE_NAMES here, "
        "the MODULES constant in frontend/src/i18n/__tests__/index.test.ts, "
        "`modules.names.*` in BOTH frontend/src/i18n/locales/{en,pt}.json, and "
        "the MODULE_GROUPS clusters in TenantModulesPage.tsx. "
        f"added={sorted(MODULES - EXPECTED_MODULE_NAMES)} "
        f"removed={sorted(EXPECTED_MODULE_NAMES - MODULES)}"
    )
