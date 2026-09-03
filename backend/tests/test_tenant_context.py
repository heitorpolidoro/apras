"""Unit tests for the tenant isolation machinery itself (APRAS-42 §9.3).

These tests never go through HTTP: they exercise
``app/core/tenant_context.py`` directly against real models, so a failure
here points at the mechanism rather than at a route.
"""

import ast
import os
import uuid

import pytest
from sqlalchemy import delete, update
from sqlmodel import Session, func, select

from app.core.exceptions import CrossTenantWriteError, TenantScopeNotResolvedError
from app.core.tenant_context import (
    ACTING_TENANT_KEY,
    REQUEST_SCOPED_KEY,
    SCOPE_RESOLVED_KEY,
    TENANT_SCOPED_MODELS,
    acting_tenant_id,
    acting_tenant_scope,
    set_acting_tenant,
    use_global_scope,
)
from app.models.category import Category
from app.models.task import Task, TaskComment
from app.models.tenant import DEFAULT_TENANT_ID, Tenant
from app.models.user import User

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATION = os.path.join(
    _BACKEND_DIR, "alembic", "versions", "0028_add_tenant_and_membership.py"
)


#: Tables migration `0028` named under a spelling a later migration changed.
#: `0028` is a historical artefact and must keep saying `user_type`; migration
#: `0032` (IAM F5, APRAS-49 §2.3) renamed that table to `role`. Mapping here
#: is what keeps this comparison about *which* tables are scoped rather than
#: about what they were called in 2026-08.
_RENAMED_SINCE_0028: dict[str, str] = {"user_type": "role"}


def _migration_scoped_tables() -> tuple[str, ...]:
    """Read `_TENANT_SCOPED_TABLES` out of migration 0028 with `ast`.

    Names are returned under their **current** spelling (`_RENAMED_SINCE_0028`).
    """
    with open(MIGRATION, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=MIGRATION)
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "_TENANT_SCOPED_TABLES":
                return tuple(
                    _RENAMED_SINCE_0028.get(name, name)
                    for name in ast.literal_eval(node.value)
                )
    raise AssertionError("_TENANT_SCOPED_TABLES not found")


@pytest.fixture(name="tenant_b")
def tenant_b_fixture(session: Session) -> Tenant:
    """A second tenant, created outside any acting scope."""
    tenant = Tenant(name="Condomínio B")
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@pytest.fixture(name="fresh_session")
def fresh_session_fixture(session: Session):
    """A second Session on the same engine, with an empty identity map."""
    with Session(session.get_bind()) as other:
        yield other


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


#: Directly-scoped tables created after migration `0028`, whose frozen
#: `_TENANT_SCOPED_TABLES` literal therefore cannot name them. The same
#: constant, and the same reason, as `tests/test_tenant_models.py`'s:
#: `0028` records history and is not amended. APRAS-40's is the first.
POST_0028_SCOPED_TABLES = {"tenant_subscription"}


def test_registry_matches_the_migrations_scoped_table_list():
    """The derived registry cannot drift from the scoped table list.

    APRAS-41's 27, from migration `0028`'s literal, plus every directly-scoped
    table added since -- which the registry picks up by *discovery* (any
    mapped class with a `tenant_id` column), with no code change of its own.
    """
    assert {m.__tablename__ for m in TENANT_SCOPED_MODELS} == (
        set(_migration_scoped_tables()) | POST_0028_SCOPED_TABLES
    )
    assert len(TENANT_SCOPED_MODELS) == 28


def test_registry_excludes_the_membership_table():
    """`user_tenant_link` carries a tenant_id but is not a scoped entity."""
    assert "user_tenant_link" not in {m.__tablename__ for m in TENANT_SCOPED_MODELS}


# ---------------------------------------------------------------------------
# Read filter
# ---------------------------------------------------------------------------


def _seed_two_categories(session: Session, tenant_b: Tenant) -> tuple[Category, Category]:
    a = Category(name="A-only", color="#111111")
    b = Category(name="B-only", color="#222222", tenant_id=tenant_b.id)
    session.add_all([a, b])
    session.commit()
    session.refresh(a)
    session.refresh(b)
    return a, b


def test_select_is_filtered_by_the_acting_tenant(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """A plain select only returns the acting tenant's rows."""
    _seed_two_categories(session, tenant_b)
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)

    names = {c.name for c in fresh_session.exec(select(Category)).all()}
    assert names == {"A-only"}


def test_column_only_select_is_filtered(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """A column-only select is filtered too."""
    _seed_two_categories(session, tenant_b)
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)

    assert list(fresh_session.exec(select(Category.name)).all()) == ["A-only"]


def test_count_is_filtered(session: Session, tenant_b: Tenant, fresh_session: Session):
    """Aggregates over a scoped entity are filtered."""
    _seed_two_categories(session, tenant_b)
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)

    assert fresh_session.exec(select(func.count(Category.id))).one() == 1
    assert (
        fresh_session.exec(select(func.count()).select_from(Category)).one() == 1
    )


def test_count_over_a_subquery_is_filtered(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """`select(func.count()).select_from(<select>.subquery())` — the paginated
    total form used across the services — is filtered by the listener."""
    _seed_two_categories(session, tenant_b)
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)

    inner = select(Category)
    assert fresh_session.exec(select(func.count()).select_from(inner.subquery())).one() == 1


def test_session_get_is_filtered_on_a_fresh_session(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """`session.get` of another tenant's row returns None."""
    _, b_category = _seed_two_categories(session, tenant_b)
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)

    assert fresh_session.get(Category, b_category.id) is None


def test_orm_update_and_delete_are_filtered(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """ORM-enabled UPDATE/DELETE cannot touch another tenant's rows."""
    _, b_category = _seed_two_categories(session, tenant_b)
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)

    result = fresh_session.exec(
        update(Category).where(Category.id == b_category.id).values(name="hacked")
    )
    assert result.rowcount == 0

    result = fresh_session.exec(delete(Category).where(Category.id == b_category.id))
    assert result.rowcount == 0
    fresh_session.rollback()


def test_join_through_a_scoped_parent_is_filtered(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """A child table joined to its scoped parent inherits the filter."""
    user = User(
        id=uuid.uuid4(),
        email="tc@test.com",
        full_name="TC",
        hashed_password="x",
        cpf="12345678901",
    )
    session.add(user)
    session.commit()
    task_a = Task(title="A task", created_by_id=user.id)
    task_b = Task(title="B task", created_by_id=user.id, tenant_id=tenant_b.id)
    session.add_all([task_a, task_b])
    session.commit()
    session.add_all(
        [
            TaskComment(task_id=task_a.id, created_by_id=user.id, content="a"),
            TaskComment(task_id=task_b.id, created_by_id=user.id, content="b"),
        ]
    )
    session.commit()

    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)
    contents = {
        c.content for c in fresh_session.exec(select(TaskComment).join(Task)).all()
    }
    assert contents == {"a"}


def test_unscoped_session_sees_everything(session: Session, tenant_b: Tenant):
    """A session with no acting tenant behaves exactly as it does today."""
    _seed_two_categories(session, tenant_b)
    with Session(session.get_bind()) as plain:
        assert len(plain.exec(select(Category)).all()) == 2


def test_global_scope_does_not_filter(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """`use_global_scope` marks the scope resolved without filtering."""
    _seed_two_categories(session, tenant_b)
    use_global_scope(fresh_session)

    assert acting_tenant_id(fresh_session) is None
    assert fresh_session.info[SCOPE_RESOLVED_KEY] is True
    assert len(fresh_session.exec(select(Category)).all()) == 2


# ---------------------------------------------------------------------------
# Write stamp
# ---------------------------------------------------------------------------


def test_stamp_overwrites_the_model_default(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """A create that omits tenant_id lands in the acting tenant."""
    set_acting_tenant(fresh_session, tenant_b.id)
    category = Category(name="Stamped", color="#333333")
    fresh_session.add(category)
    fresh_session.commit()

    assert category.tenant_id == tenant_b.id


def test_stamp_overwrites_a_forged_tenant_id(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """An explicitly forged tenant_id is overwritten, never honoured."""
    set_acting_tenant(fresh_session, tenant_b.id)
    category = Category(name="Forged", color="#444444", tenant_id=DEFAULT_TENANT_ID)
    fresh_session.add(category)
    fresh_session.commit()

    assert category.tenant_id == tenant_b.id


def test_dirty_cross_tenant_object_raises(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """Mutating another tenant's already-loaded row is refused at flush."""
    _, b_category = _seed_two_categories(session, tenant_b)

    loaded = fresh_session.get(Category, b_category.id)
    assert loaded is not None
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)
    loaded.name = "hijacked"

    with pytest.raises(CrossTenantWriteError):
        fresh_session.commit()
    fresh_session.rollback()


def test_no_stamp_without_an_acting_tenant(session: Session, tenant_b: Tenant):
    """A direct `Session(engine)` writer keeps the model default."""
    with Session(session.get_bind()) as plain:
        category = Category(name="Plain", color="#555555")
        plain.add(category)
        plain.commit()
        assert category.tenant_id == DEFAULT_TENANT_ID


# ---------------------------------------------------------------------------
# Fail-closed guard
# ---------------------------------------------------------------------------


def test_unresolved_request_session_raises_on_a_scoped_model(session: Session):
    """A request-scoped session that queries a scoped model before its scope
    is resolved fails loudly instead of returning every tenant's rows."""
    with Session(session.get_bind()) as request_session:
        request_session.info[REQUEST_SCOPED_KEY] = True
        with pytest.raises(TenantScopeNotResolvedError):
            request_session.exec(select(Category)).all()


def test_unresolved_request_session_allows_global_models(session: Session):
    """The guard only fires for tenant-scoped entities."""
    with Session(session.get_bind()) as request_session:
        request_session.info[REQUEST_SCOPED_KEY] = True
        assert request_session.exec(select(User)).all() == []
        assert request_session.exec(select(Tenant)).all() != []


def test_resolved_request_session_does_not_raise(session: Session):
    """Once resolved, a request-scoped session queries scoped models freely."""
    with Session(session.get_bind()) as request_session:
        request_session.info[REQUEST_SCOPED_KEY] = True
        set_acting_tenant(request_session, DEFAULT_TENANT_ID)
        assert request_session.exec(select(Category)).all() == []


def test_plain_session_is_never_guarded(session: Session):
    """`Session(engine)` (seed.py, Alembic, existing tests) is untouched."""
    with Session(session.get_bind()) as plain:
        assert REQUEST_SCOPED_KEY not in plain.info
        assert plain.exec(select(Category)).all() == []


# ---------------------------------------------------------------------------
# acting_tenant_scope
# ---------------------------------------------------------------------------


def test_acting_tenant_scope_restores_the_previous_value(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """The context manager swaps and restores the acting tenant."""
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)
    with acting_tenant_scope(fresh_session, tenant_b.id):
        assert acting_tenant_id(fresh_session) == tenant_b.id
    assert acting_tenant_id(fresh_session) == DEFAULT_TENANT_ID


def test_acting_tenant_scope_restores_on_exception(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """It restores even when the body raises."""
    set_acting_tenant(fresh_session, DEFAULT_TENANT_ID)
    with pytest.raises(RuntimeError), acting_tenant_scope(fresh_session, tenant_b.id):
        raise RuntimeError("boom")
    assert acting_tenant_id(fresh_session) == DEFAULT_TENANT_ID


def test_acting_tenant_scope_restores_an_absent_key(
    session: Session, tenant_b: Tenant, fresh_session: Session
):
    """Entering from a session with no acting tenant leaves none behind."""
    with acting_tenant_scope(fresh_session, tenant_b.id):
        assert acting_tenant_id(fresh_session) == tenant_b.id
    assert ACTING_TENANT_KEY not in fresh_session.info


# ---------------------------------------------------------------------------
# Known limitation — pinned, not a bug
# ---------------------------------------------------------------------------


def test_identity_map_limitation_is_known(session: Session, tenant_b: Tenant):
    """`with_loader_criteria` rewrites SQL; it does not evict the identity
    map. A session that already holds a foreign row can still reach it via
    `session.get`. Production never can — each request gets a new Session —
    which is why the isolation suite uses a per-request session harness."""
    _, b_category = _seed_two_categories(session, tenant_b)

    set_acting_tenant(session, DEFAULT_TENANT_ID)
    assert {c.name for c in session.exec(select(Category)).all()} == {"A-only"}
    assert session.get(Category, b_category.id) is not None

    with Session(session.get_bind()) as fresh:
        set_acting_tenant(fresh, DEFAULT_TENANT_ID)
        assert fresh.get(Category, b_category.id) is None
