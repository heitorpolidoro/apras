"""Assembly minutes rendering and Document Center filing (APRAS-33).

Covers backend test 12 of `docs/tasks/APRAS-33-spec.md` §Testing and the
"GET /{id}/minutes antes do fechamento devolve 400" complement.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.exceptions import (
    AssemblyNotClosedError,
    DelinquentLotError,
    ForbiddenError,
)
from app.models.document import AssociationDocument, DocumentFolder
from app.services import voting_service
from app.services.storage_service import BaseStorageProvider, LocalStorageProvider
from tests.voting_helpers import (
    auth_headers,
    link_user_to_lot,
    make_assembly,
    make_lot,
    make_user,
    make_vote,
    option_id,
)


class FakeStorageProvider(BaseStorageProvider):
    """In-memory storage so minutes tests never touch the filesystem."""

    def __init__(self) -> None:
        self.saved: list[tuple[bytes, str, str]] = []

    def save_file(self, file_bytes, filename, content_type):
        self.saved.append((file_bytes, filename, content_type))
        return f"memory://{filename}", f"/static/uploads/{filename}"

    def delete_file(self, file_path):
        return True


def _cast(session, user, vote, label, lot=None):
    return voting_service.cast_ballot(
        session,
        user,
        vote,
        lot_id=lot.id if lot else None,
        selected_option_ids=[option_id(vote, label)],
    )


def _closed_assembly_with_delinquent_lot(session: Session):
    admin = make_user(session, "ADMINISTRATOR")
    owner = make_user(session, "RESIDENT")
    debtor = make_user(session, "RESIDENT")
    lot = make_lot(session, "A", "1")
    delinquent_lot = make_lot(session, "B", "12", is_delinquent=True)
    link_user_to_lot(session, owner, lot)
    link_user_to_lot(session, debtor, delinquent_lot)

    assembly = make_assembly(session, admin)
    budget = make_vote(session, admin, assembly=assembly, title="Orçamento 2026")
    _cast(session, owner, budget, "Sim", lot)

    with pytest.raises(DelinquentLotError):
        _cast(session, debtor, budget, "Sim", delinquent_lot)

    voting_service.close_assembly(session, admin, assembly)
    return admin, assembly


def test_minutes_before_closing_are_refused(session: Session):
    admin = make_user(session, "ADMINISTRATOR")
    assembly = make_assembly(session, admin)

    with pytest.raises(AssemblyNotClosedError):
        voting_service.render_minutes_html(session, assembly)


def test_minutes_endpoint_before_closing_returns_400(
    client: TestClient, session: Session
):
    admin = make_user(session, "ADMINISTRATOR")
    assembly = make_assembly(session, admin)

    response = client.get(
        f"/api/v1/assemblies/{assembly.id}/minutes",
        headers=auth_headers(client, admin),
    )
    assert response.status_code == 400


def test_minutes_contain_results_attribution_denominator_and_barred_lots(
    session: Session,
):
    _admin, assembly = _closed_assembly_with_delinquent_lot(session)

    minutes = voting_service.render_minutes_html(session, assembly)

    assert "Minuta de Ata" in minutes
    assert "Assembleia Geral Ordinária (AGO)" in minutes
    assert "Orçamento 2026" in minutes
    # result per option
    assert "<td>Sim</td><td>1</td>" in minutes
    # attribution by Bloco/Lote
    assert "<td>A/1</td>" in minutes
    # denominator over active lots
    assert "Denominador: 2 lotes ativos · 1 votaram · 1 não votaram." in minutes
    # delinquency-barred lots, mandatory section
    assert "Lotes impedidos por inadimplência" in minutes
    assert "<li>B/12</li>" in minutes
    # footer disclaimer
    assert "não substitui a ata registrada" in minutes


def test_minutes_report_no_barred_lots_when_there_were_none(session: Session):
    admin = make_user(session, "ADMINISTRATOR")
    assembly = make_assembly(session, admin)
    make_vote(session, admin, assembly=assembly)
    voting_service.close_assembly(session, admin, assembly)

    minutes = voting_service.render_minutes_html(session, assembly)
    assert "Nenhum lote foi impedido de votar por inadimplência." in minutes


def test_minutes_escape_user_supplied_text(session: Session):
    admin = make_user(session, "ADMINISTRATOR")
    assembly = make_assembly(session, admin, title="<script>alert(1)</script>")
    make_vote(session, admin, assembly=assembly, title="<b>Pauta</b>")
    voting_service.close_assembly(session, admin, assembly)

    minutes = voting_service.render_minutes_html(session, assembly)
    assert "<script>alert(1)</script>" not in minutes
    assert "&lt;script&gt;" in minutes
    assert "&lt;b&gt;Pauta&lt;/b&gt;" in minutes


def test_saving_minutes_creates_the_folder_once_and_files_the_document(
    session: Session,
):
    admin, assembly = _closed_assembly_with_delinquent_lot(session)
    storage = FakeStorageProvider()

    document = voting_service.save_minutes(session, admin, assembly, storage)

    assert document.mime_type == "text/html"
    assert document.file_size_bytes == len(storage.saved[0][0])
    folders = session.exec(
        select(DocumentFolder).where(DocumentFolder.name == "Atas de Assembleia")
    ).all()
    assert len(folders) == 1
    assert folders[0].parent_id is None
    assert document.folder_id == folders[0].id

    voting_service.save_minutes(session, admin, assembly, storage)
    folders_again = session.exec(
        select(DocumentFolder).where(DocumentFolder.name == "Atas de Assembleia")
    ).all()
    assert len(folders_again) == 1
    assert len(session.exec(select(AssociationDocument)).all()) == 2


def test_saving_minutes_is_board_only(session: Session):
    assembly = _closed_assembly_with_delinquent_lot(session)[1]
    manager = make_user(session, "MANAGER")

    with pytest.raises(ForbiddenError):
        voting_service.save_minutes(session, manager, assembly, FakeStorageProvider())

    with pytest.raises(ForbiddenError):
        voting_service.get_minutes_html(session, manager, assembly)


def test_minutes_endpoints_end_to_end(
    client: TestClient, session: Session, monkeypatch
):
    admin, assembly = _closed_assembly_with_delinquent_lot(session)
    monkeypatch.setattr(
        voting_service, "generated_storage_provider", FakeStorageProvider
    )
    headers = auth_headers(client, admin)

    rendered = client.get(f"/api/v1/assemblies/{assembly.id}/minutes", headers=headers)
    assert rendered.status_code == 200
    assert rendered.headers["content-type"].startswith("text/html")
    assert "<li>B/12</li>" in rendered.text

    saved = client.post(
        f"/api/v1/assemblies/{assembly.id}/minutes/save", headers=headers
    )
    assert saved.status_code == 201
    assert saved.json()["mime_type"] == "text/html"
    assert saved.json()["folder_name"] == "Atas de Assembleia"


def test_saved_minutes_land_in_the_generated_tree(session: Session, tmp_path):
    """APRAS-65 §D4: `/static/generated/YYYY/MM/<uuid>.html`, never uploads.

    A real provider, because the claim is about where bytes land on disk.
    """
    admin, assembly = _closed_assembly_with_delinquent_lot(session)
    provider = LocalStorageProvider(
        base_dir=tmp_path / "generated", url_prefix="/static/generated"
    )
    uploads = Path("static/uploads")
    before = set(uploads.rglob("*")) if uploads.exists() else set()

    document = voting_service.save_minutes(session, admin, assembly, provider)

    assert re.fullmatch(
        r"/static/generated/\d{4}/\d{2}/[0-9a-f-]{36}\.html", document.file_url
    ), document.file_url
    written = [path for path in (tmp_path / "generated").rglob("*") if path.is_file()]
    assert len(written) == 1
    assert written[0].suffix == ".html"
    assert re.fullmatch(r"\d{4}", written[0].parent.parent.name)
    assert re.fullmatch(r"\d{2}", written[0].parent.name)
    assert (set(uploads.rglob("*")) if uploads.exists() else set()) == before


def test_the_default_minutes_provider_is_the_generated_one(session: Session):
    """No caller passes a provider in production; the default has to be right."""
    assert voting_service.generated_storage_provider().url_prefix == "/static/generated"
