"""§4: the `allowed_menus` menu gate is deleted, not translated.

The gate was a **coarse AND** in front of the permission check on 12 handlers
(`endpoints/tasks.py` x8, `endpoints/categories.py` x4). Removing it widens
access for exactly one population, and §4.2 is the argument for why it is not
translated instead:

* folding it into each role's bundle **per role** would strip `tasks:*` from
  all six historically-named rows — they are all seeded `allowed_menus = []`
  by migration `0018` — locking every non-superuser out of Tarefas.
  Catastrophic narrowing;
* folding it **per user** is not expressible: permissions live on roles, and
  the board has ruled out per-user permissions. Manufacturing one
  `(role x menu-profile)` row per combination would create up to 24
  machine-generated rows per tenant and contradict "no system roles";
* the gate's job — "who sees Tarefas" — is now done, and done *finer*, by
  `tasks:read` in a role. Keeping both would be two sources of truth for one
  question, which is the drift this chain exists to remove.

The delta is **invisible to the parity matrix by construction**, and that is
correct rather than convenient: `matrix_world` gave every actor a
menu-granting type precisely so the matrix measured permissions and not menus
(F2 §6.2). The matrix therefore still proves the 1080 authorization outcomes
are unchanged; this module carries the one thing it cannot see.
"""

import ast
import pathlib
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api import deps
from app.core.security import create_access_token, get_password_hash
from app.models import enums
from app.models.category import Category
from app.models.role import Role
from app.models.user import User

APP_ROOT = pathlib.Path(deps.__file__).resolve().parent.parent
ENDPOINTS = APP_ROOT / "api" / "v1" / "endpoints"


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _member(session: Session, name: str, permissions: list[str]) -> User:
    """A user whose only role carries `permissions` and **no** menu keys.

    Before F5 this shape was 403'd on every gated handler no matter what the
    bundle said, because the role's `allowed_menus` was empty.
    """
    role = Role(name=name, permissions=permissions)
    session.add(role)
    session.commit()
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@menugate.example.com",
        full_name="Menu Gate Case",
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
        roles=[role],
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# The gate is gone from the code
# ---------------------------------------------------------------------------


def test_assert_menu_access_no_longer_exists():
    assert not hasattr(deps, "assert_menu_access")


def test_has_admin_capability_no_longer_exists():
    """It lost its only caller and went with it (§4.1).

    F3 §5.1 #3 already recorded that `assert_menu_access` was its sole
    consumer. `is_acting_tenant_admin` stays: `get_effective_permissions`
    still calls it.
    """
    assert not hasattr(deps, "has_admin_capability")
    assert hasattr(deps, "is_acting_tenant_admin")


def test_menu_key_no_longer_exists():
    assert not hasattr(enums, "MenuKey")


def test_role_carries_no_allowed_menus_column():
    assert "allowed_menus" not in Role.model_fields


def test_no_handler_calls_a_menu_gate():
    """An AST walk over every endpoint module, so a re-introduction fails CI."""
    offenders = []
    for path in sorted(ENDPOINTS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(
            f"{path.name}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and "assert_menu_access"
            in {
                getattr(node.func, "attr", None),
                getattr(node.func, "id", None),
            }
        )
    assert not offenders, f"menu-gate calls survived: {offenders}"


# ---------------------------------------------------------------------------
# §4.2 -- the one deliberate behaviour delta, both directions
# ---------------------------------------------------------------------------


def test_a_user_without_the_legacy_menu_key_now_reaches_tasks(
    client: TestClient, session: Session
):
    """The widening, stated so it is not rediscovered as a bug.

    This user holds `tasks:read` and belongs to no role carrying the `tasks`
    menu key. Before F5 the gate answered 403 before the permission was ever
    consulted; now the permission is the whole answer. The operator's
    replacement lever is in `AGENTS.md`: remove `tasks:*` from the role.
    """
    user = _member(session, "Tarefas sem menu", ["tasks:read"])

    response = client.get("/api/v1/tasks/", headers=_auth(user))

    assert response.status_code == 200
    assert response.json() == []


def test_a_user_without_the_legacy_menu_key_now_reaches_categories(
    client: TestClient, session: Session
):
    """The same widening on the other four gated handlers."""
    session.add(Category(name="Geral", color="#808080"))
    session.commit()
    user = _member(session, "Categorias sem menu", ["categories:read"])

    response = client.get("/api/v1/categories/", headers=_auth(user))

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Geral"]


def test_a_user_without_tasks_read_is_still_refused(
    client: TestClient, session: Session
):
    """The narrowing that did **not** happen: the permission still decides.

    Removing the gate widened the population that reaches the handler; it did
    not widen what the handler allows. Since APRAS-51 the listing route
    enforces its mapped `tasks:read` in the dependency tree, so a caller
    without it is refused outright rather than served the empty list this case
    used to assert -- the parity cell `("GUEST", "GET", "/api/v1/tasks/")`
    moving 200 -> 403. A write they cannot make is still a 403.
    """
    user = _member(session, "Sem tarefas", ["categories:read"])

    listing = client.get("/api/v1/tasks/", headers=_auth(user))
    assert listing.status_code == 403
    assert listing.json()["detail"] == "The user doesn't have enough privileges"

    creation = client.post(
        "/api/v1/tasks/",
        headers=_auth(user),
        json={"title": "Nope"},
    )
    assert creation.status_code == 403


def test_a_user_without_categories_create_is_still_refused(
    client: TestClient, session: Session
):
    user = _member(session, "Só leitura", ["categories:read"])

    response = client.post(
        "/api/v1/categories/",
        headers=_auth(user),
        json={"name": "Nope", "color": "#ff0000"},
    )

    assert response.status_code == 403
