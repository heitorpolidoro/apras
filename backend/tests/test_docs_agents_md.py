"""ER-5: `AGENTS.md` describes the model that exists.

Three sections were **wrong** after IAM F5 and were rewritten rather than
patched — *UserRole (RBAC)*, *UserType*, and the `allowed_menus` sentences
inside *Tenant* and *User*. A doc that still presents the retired model as
current is worse than no doc, because it is the thing an agent reads first.

The rule this module enforces is deliberately narrow and mechanical: the five
retired terms may appear **only** where the document is explicitly talking
about what was removed (`### What is gone`) or telling an operator how to move
an existing install off it (`### Migrating an existing install`). Anywhere
else they are a claim about the present, and the present does not have them.
"""

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
AGENTS_MD = REPO_ROOT / "AGENTS.md"

#: The five terms §13 names. `user_role_link` and `UserRoleLink` are the
#: *current* names of the link table (§2.1's naming table mandates them), so
#: the `UserRole` pattern excludes them explicitly rather than by luck.
RETIRED_TERMS: dict[str, re.Pattern[str]] = {
    "UserRole": re.compile(r"\bUserRole\b(?!Link)"),
    "allowed_menus": re.compile(r"\ballowed_menus\b"),
    "MenuKey": re.compile(r"\bMenuKey\b"),
    "user_type": re.compile(r"\buser_type\b"),
    "UserType": re.compile(r"\bUserType\b"),
    "menu gate": re.compile(r"\bmenu gate\b", re.IGNORECASE),
}

#: The two headings under which a retired term is a *historical* statement.
PERMITTED_SECTIONS = ("### What is gone", "### Migrating an existing install")


def _sections() -> list[tuple[str, int, list[str]]]:
    """`(heading, first line number, lines)` for every `###` section."""
    lines = AGENTS_MD.read_text(encoding="utf-8").splitlines()
    out: list[tuple[str, int, list[str]]] = []
    heading, start, body = "<preamble>", 1, []
    for index, line in enumerate(lines, start=1):
        if line.startswith(("### ", "## ")):
            out.append((heading, start, body))
            heading, start, body = line.strip(), index, []
        else:
            body.append(line)
    out.append((heading, start, body))
    return out


def test_agents_md_exists():
    assert AGENTS_MD.exists(), AGENTS_MD


def test_agents_md_does_not_describe_the_retired_model():
    """The ER-bearing case: no retired term outside the two permitted sections."""
    offenders: list[str] = []
    for heading, start, body in _sections():
        if heading in PERMITTED_SECTIONS:
            continue
        for offset, line in enumerate(body):
            for term, pattern in RETIRED_TERMS.items():
                if pattern.search(line):
                    offenders.append(
                        f"{heading} (line {start + offset + 1}): {term} -- {line.strip()}"
                    )
    assert not offenders, "AGENTS.md still describes the retired model:\n" + "\n".join(
        offenders
    )


def test_the_what_is_gone_section_exists_and_names_every_retired_term():
    """A section that lists four of five would be the worst possible outcome."""
    section = next(
        body for heading, _start, body in _sections() if heading == "### What is gone"
    )
    text = "\n".join(section)
    for term in ("UserRole", "allowed_menus", "menu gate", "LEGACY_ROLE_PERMISSIONS"):
        assert term in text, f"`### What is gone` does not mention {term}"


def test_the_document_states_the_model_that_exists():
    """The five claims ER-5 requires, each pinned by a phrase that carries it.

    Whitespace is collapsed first, so re-wrapping a paragraph cannot turn a
    true claim into a red test — the assertion is about what the document
    says, not about where its lines break.
    """
    text = re.sub(r"\s+", " ", AGENTS_MD.read_text(encoding="utf-8"))
    for claim in (
        # permissions in code. The two counts moved with the catalogue:
        # APRAS-40 minted `billing:read`/`billing:manage` and APRAS-44 the
        # thirteen `infractions:*`, taking 159/26 to **174/28**. The document
        # was stale at 159/26 -- neither of the two intervening slices moved
        # it -- and APRAS-44 corrects it rather than making it wronger.
        "174",
        "28",
        "ROUTE_PERMISSIONS",
        "UNGUARDED_ROUTES",
        # roles as data
        "### Roles are data",
        "no per-user permissions",
        "there are no system roles",
        # the flag and its one surface
        "PATCH /api/v1/users/{user_id}/superuser",
        "is_tenant_admin",
        # the object-level permissions that replaced the tiers
        "tasks:read_all",
        "tasks:update_any",
        "occurrences:read_assigned",
        # the journal and both refusals
        "f5_backfill_journal",
        "one-way door",
        "refuses to run",
    ):
        assert claim in text, f"AGENTS.md does not state: {claim!r}"


def test_the_endpoint_table_names_roles_and_permissions():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "`/api/v1/roles`" in text
    assert "`/api/v1/permissions`" in text
    assert "/api/v1/user-types" not in text


def test_the_route_map_names_the_role_admin_screens():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "/admin/roles" in text
    assert "RolesAdminPage" in text
    assert "RoleDetailPage" in text
    assert "/admin/groups" not in text


def test_the_runbook_is_present_and_runnable_shaped():
    """§9.3, verbatim enough that an operator can paste it."""
    section = next(
        body
        for heading, _start, body in _sections()
        if heading == "### Migrating an existing install"
    )
    text = "\n".join(section)
    assert "pg_dump" in text
    assert "alembic upgrade head" in text
    assert "python -m app.seed" in text
    assert "alembic downgrade -1" in text
