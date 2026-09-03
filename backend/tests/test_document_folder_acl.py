"""§6: the document-folder ACL, keyed on role ids.

`DocumentFolder.allowed_roles_json` stored a JSON list of `UserRole` value
strings. It is a per-object, data-driven ACL and it was the one place the enum
leaked into **user data**, which is why F5 has to rewrite it rather than
delete it.

It becomes a list of role **ids**, and the column is renamed to
`allowed_role_ids_json`. Renaming rather than reusing the name is deliberate:
the *content type* changes, and a reader that was not updated must fail loudly
instead of silently matching nothing.

Two consequences this module pins:

* both defaults become `'[]'` — neither the Python-side `default=` nor the
  column's `server_default` can name four role ids, because a `server_default`
  is a constant expression and role ids differ per tenant and per install — so
  `DocumentFolderCreate.allowed_role_ids` is **required**: a folder created
  without an explicit ACL would otherwise be invisible to everyone;
* the ACL can now name **any** role, not only the six legacy ones, which is a
  straight improvement the enum made impossible.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.document import DocumentFolder
from app.models.role import Role
from app.models.user import User
from app.schemas.document import (
    DocumentFolderCreate,
    DocumentFolderRead,
    DocumentFolderUpdate,
)
from tests.conftest import profile_role


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _user(session: Session, name: str, roles: list[Role]) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@folders.example.com",
        full_name=name,
        hashed_password=get_password_hash("password"),
        cpf=str(uuid.uuid4().int)[:11],
        roles=roles,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="world")
def world_fixture(session: Session):
    reader = Role(name="Leitura", permissions=["documents:read", "documents:folder_read"])
    other = Role(name="Outro", permissions=["documents:read", "documents:folder_read"])
    author = Role(
        name="Autoria",
        permissions=[
            "documents:read",
            "documents:folder_read",
            "documents:folder_create",
            "documents:folder_update",
        ],
    )
    session.add_all([reader, other, author])
    session.commit()

    scoped = DocumentFolder(
        name="Escopada", allowed_role_ids_json=json.dumps([str(reader.id)])
    )
    empty = DocumentFolder(name="Sem ACL", allowed_role_ids_json="[]")
    session.add_all([scoped, empty])
    session.commit()
    session.refresh(scoped)
    session.refresh(empty)

    return {
        "reader": reader,
        "other": other,
        "author": author,
        "member": _user(session, "Membro", [reader]),
        "stranger": _user(session, "Estranho", [other]),
        "staff": _user(session, "Autor", [author]),
        "scoped": scoped,
        "empty": empty,
    }


def _folder_names(client: TestClient, user: User) -> set[str]:
    response = client.get("/api/v1/documents/folders", headers=_auth(user))
    assert response.status_code == 200
    return {row["name"] for row in response.json()}


def test_folder_access_intersects_allowed_role_ids_with_the_callers_roles(
    client: TestClient, world
):
    assert _folder_names(client, world["member"]) == {"Escopada"}
    assert _folder_names(client, world["stranger"]) == set()


def test_documents_folder_create_still_bypasses(client: TestClient, world):
    """The all-folders staff bypass is kept verbatim (§6)."""
    assert _folder_names(client, world["staff"]) == {"Escopada", "Sem ACL"}


def test_a_folder_scoped_to_a_non_legacy_role_admits_its_members(
    client: TestClient, session: Session, world
):
    """The improvement the enum made impossible.

    `Conselho Fiscal` is an ordinary, operator-created role: it never had a
    `UserRole` value, so before F5 no folder could name it at all.
    """
    council = Role(
        name="Conselho Fiscal",
        permissions=["documents:read", "documents:folder_read"],
    )
    session.add(council)
    session.commit()
    member = _user(session, "Conselheiro", [council])
    session.add(
        DocumentFolder(
            name="Prestação de contas",
            allowed_role_ids_json=json.dumps([str(council.id)]),
        )
    )
    session.commit()

    assert _folder_names(client, member) == {"Prestação de contas"}
    assert "Prestação de contas" not in _folder_names(client, world["member"])


def test_allowed_role_ids_is_required_on_create(client: TestClient, world):
    """A folder created without an explicit ACL would be invisible to everyone."""
    missing = client.post(
        "/api/v1/documents/folders",
        headers=_auth(world["staff"]),
        json={"name": "Sem ACL declarada"},
    )
    assert missing.status_code == 422

    explicit = client.post(
        "/api/v1/documents/folders",
        headers=_auth(world["staff"]),
        json={
            "name": "Com ACL declarada",
            "allowed_role_ids": [str(world["reader"].id)],
        },
    )
    assert explicit.status_code == 201
    assert explicit.json()["allowed_role_ids"] == [str(world["reader"].id)]
    assert _folder_names(client, world["member"]) == {"Escopada", "Com ACL declarada"}


def test_an_unresolvable_allowed_role_id_is_a_422_on_create(
    client: TestClient, world
):
    """The mistake the required-field decision worries about, caught early.

    Now that the ACL's content type is an id rather than a name, a typo, a
    stale id copied from another install, or a role deleted between the form
    load and the save all produce the same silent outcome: a folder nobody
    can see. The ids are cheap to resolve at write time, so an unresolvable
    one is refused instead of stored -- the same call the sibling
    `role_ids` validation makes in `endpoints/users.py::_assign_roles`.
    """
    unknown = str(uuid.uuid4())
    response = client.post(
        "/api/v1/documents/folders",
        headers=_auth(world["staff"]),
        json={
            "name": "Fantasma",
            "allowed_role_ids": [str(world["reader"].id), unknown],
        },
    )

    assert response.status_code == 422
    # Naming the offender is the point: "422" alone leaves the operator
    # bisecting their own payload.
    assert unknown in response.json()["detail"]
    assert "Fantasma" not in _folder_names(client, world["staff"])


def test_a_non_uuid_allowed_role_id_is_a_422_rather_than_a_dead_acl(
    client: TestClient, world
):
    """The field is `list[str]`, so garbage reaches the service intact.

    `'ADMINISTRATOR'` is the exact garbage this slice makes possible: it is
    what the column held *before* F5, so a client that was not migrated
    keeps sending it. Matching nothing forever is the failure mode the
    column rename exists to prevent, and it is only prevented if the write
    is refused.
    """
    response = client.post(
        "/api/v1/documents/folders",
        headers=_auth(world["staff"]),
        json={"name": "Legado", "allowed_role_ids": ["ADMINISTRATOR"]},
    )

    assert response.status_code == 422
    assert "ADMINISTRATOR" in response.json()["detail"]


def test_a_role_of_another_tenant_cannot_be_named_in_an_acl(
    client: TestClient, session: Session, world
):
    """Existence is not enough: the id must resolve *in the acting tenant*.

    Ambient tenant filtering does not cover this by itself -- the id is read
    from a request payload, not from a relationship -- so the lookup is
    narrowed explicitly, exactly as `_assign_roles` narrows its own.
    """
    foreign = Role(
        name="Sindico do outro condominio",
        permissions=["documents:read"],
        tenant_id=uuid.uuid4(),
    )
    session.add(foreign)
    session.commit()
    session.refresh(foreign)

    response = client.post(
        "/api/v1/documents/folders",
        headers=_auth(world["staff"]),
        json={"name": "Vizinha", "allowed_role_ids": [str(foreign.id)]},
    )

    assert response.status_code == 422
    assert str(foreign.id) in response.json()["detail"]


def test_an_unresolvable_allowed_role_id_is_a_422_on_update(
    client: TestClient, world
):
    """And the stored ACL survives the refusal untouched."""
    unknown = str(uuid.uuid4())
    response = client.put(
        f"/api/v1/documents/folders/{world['scoped'].id}",
        headers=_auth(world["staff"]),
        json={"allowed_role_ids": [unknown]},
    )

    assert response.status_code == 422
    assert unknown in response.json()["detail"]
    assert _folder_names(client, world["member"]) == {"Escopada"}


def test_the_empty_acl_stays_legal(client: TestClient, world):
    """Validation refuses *unresolvable* ids, never the deliberate `[]`.

    An empty list is how an author says "staff only" -- the folder is still
    reachable through the `documents:folder_create` bypass -- and the
    required-field rule already forces that choice to be explicit.
    """
    response = client.post(
        "/api/v1/documents/folders",
        headers=_auth(world["staff"]),
        json={"name": "So equipe", "allowed_role_ids": []},
    )

    assert response.status_code == 201
    assert response.json()["allowed_role_ids"] == []


def test_update_replaces_the_acl(client: TestClient, world):
    response = client.put(
        f"/api/v1/documents/folders/{world['scoped'].id}",
        headers=_auth(world["staff"]),
        json={"allowed_role_ids": [str(world["other"].id)]},
    )

    assert response.status_code == 200
    assert response.json()["allowed_role_ids"] == [str(world["other"].id)]
    assert _folder_names(client, world["member"]) == set()
    assert _folder_names(client, world["stranger"]) == {"Escopada"}


def test_both_defaults_are_the_empty_list(session: Session):
    """The Python-side `default=` and the schema's read default (§6).

    The column's `server_default` is asserted against real Postgres by
    `tests/test_migrations_postgres.py`; here is the ORM half, which is what
    `SQLModel.metadata.create_all()` builds for the test suite.
    """
    folder = DocumentFolder(name="Padrão")
    session.add(folder)
    session.commit()
    session.refresh(folder)

    assert folder.allowed_role_ids_json == "[]"
    assert DocumentFolderRead.model_fields["allowed_role_ids"].default == []


def test_the_schemas_carry_only_the_renamed_field():
    """A reader that was not updated must fail loudly, not match nothing."""
    for schema in (DocumentFolderCreate, DocumentFolderUpdate, DocumentFolderRead):
        assert "allowed_roles" not in schema.model_fields
        assert "allowed_role_ids" in schema.model_fields
    assert DocumentFolderCreate.model_fields["allowed_role_ids"].is_required()


def test_a_malformed_acl_denies_rather_than_raises(
    client: TestClient, session: Session, world
):
    """A hand-edited row must not take the endpoint down."""
    session.add(
        DocumentFolder(name="Corrompida", allowed_role_ids_json="NOT JSON")
    )
    session.commit()

    assert "Corrompida" not in _folder_names(client, world["member"])
    assert "Corrompida" in _folder_names(client, world["staff"])


def test_the_acl_is_never_matched_by_role_name(
    client: TestClient, session: Session, world
):
    """The name-vs-id mistake §6 exists to prevent, made unreachable.

    The legacy rows' `name` is the pt-BR label (`"Diretor (papel)"`), never a
    `UserRole` value, so a name join would have matched nothing forward and
    denied every non-staff user backward — silently, both times. Storing the
    *label* here must therefore grant nobody anything.
    """
    # `world["member"]` holds `Leitura`, which carries no
    # `documents:folder_create`, so the staff bypass cannot mask the result.
    session.add(
        DocumentFolder(
            name="Por nome",
            allowed_role_ids_json=json.dumps([world["reader"].name]),
        )
    )
    # And the same for a historically-named row, whose label is the shape the
    # mistake would actually take.
    director = profile_role(session, "DIRECTOR")
    session.add(
        DocumentFolder(
            name="Por rótulo legado",
            allowed_role_ids_json=json.dumps([director.name]),
        )
    )
    session.commit()

    visible = _folder_names(client, world["member"])
    assert "Por nome" not in visible
    assert "Por rótulo legado" not in visible
