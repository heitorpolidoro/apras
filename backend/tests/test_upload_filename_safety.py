"""The on-disk name of an upload, and what the two static mounts do with it.

Until APRAS-65 ``LocalStorageProvider.save_file`` built the stored name as
``f"{uuid4()}{Path(filename).suffix.lower()}"``: the extension came from the
*client's* file name. ``/static/uploads`` is mounted unauthenticated and
``StaticFiles`` guesses the content type from that extension, so valid PNG
bytes posted as ``payload.svg`` were stored -- and served -- as
``image/svg+xml``, which browsers execute. Stored XSS.

APRAS-63 fixed one call site (the purchase quote attachment) by sanitising the
name before it reached the provider. This module covers the general fix: the
suffix is derived inside ``save_file`` from the already-validated
``content_type``, so every call site is fixed at once, and the mount is
hardened for files an attacker already planted.
"""

import ast
import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.uploads import (
    CONTENT_TYPE_EXTENSIONS,
    INLINE_SAFE_EXTENSIONS,
    canonical_extension,
    sanitise_upload_filename,
)
from app.models.document import AssociationDocument, DocumentFolder
from app.models.tenant import DEFAULT_TENANT_ID
from app.services.announcement_service import ALLOWED_MEDIA_MIME_TYPES
from app.services.finance_service import ALLOWED_INVOICE_MIME_TYPE
from app.services.media_service import ALLOWED_MIME_TYPES as MEDIA_MIME_TYPES
from app.services.purchase_service import PurchaseService
from app.services.storage_service import (
    LocalStorageProvider,
    generated_storage_provider,
)
from app.services.tenant_service import TenantService

#: Every ``content_type`` any caller can hand ``save_file``: the four service
#: allowlists plus the ``text/html`` the two generators pass. Read from the
#: services themselves so that widening an allowlist without extending the map
#: fails here rather than silently falling back to ``.bin``.
EVERY_ACCEPTED_CONTENT_TYPE = frozenset(
    {
        *MEDIA_MIME_TYPES,
        *ALLOWED_MEDIA_MIME_TYPES,
        ALLOWED_INVOICE_MIME_TYPE,
        *TenantService.LOGO_ALLOWED_MIME_TYPES,
        *PurchaseService.ATTACHMENT_ALLOWED_MIME_TYPES,
        "text/html",
    }
)


# --------------------------------------------------------------------------- #
# canonical_extension
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("content_type", sorted(EVERY_ACCEPTED_CONTENT_TYPE))
def test_every_accepted_content_type_is_mapped(content_type: str) -> None:
    """A type a service accepts but the map misses would land as ``.bin``."""
    assert content_type in CONTENT_TYPE_EXTENSIONS
    assert canonical_extension(content_type).startswith(".")


def test_an_unknown_content_type_falls_back_to_bin() -> None:
    assert canonical_extension("image/svg+xml") == ".bin"
    assert canonical_extension("") == ".bin"


def test_the_content_type_is_normalised_before_the_lookup() -> None:
    """Browsers send parameters and mixed case; neither may defeat the map."""
    assert canonical_extension("TEXT/HTML") == ".html"
    assert canonical_extension("text/html; charset=utf-8") == ".html"
    assert canonical_extension(" image/png ") == ".png"


def test_no_mapped_extension_is_svg_or_otherwise_active() -> None:
    assert ".svg" not in set(CONTENT_TYPE_EXTENSIONS.values())
    assert ".svg" not in INLINE_SAFE_EXTENSIONS
    assert ".html" not in INLINE_SAFE_EXTENSIONS


# --------------------------------------------------------------------------- #
# sanitise_upload_filename
# --------------------------------------------------------------------------- #


def _sanitise(filename: str, content_type: str = "application/pdf") -> str:
    return sanitise_upload_filename(
        filename, content_type, max_length=128, fallback_stem="documento"
    )


def test_a_posix_path_is_reduced_to_its_basename() -> None:
    assert _sanitise("../../etc/orcamento acme.pdf") == "orcamento acme.pdf"


def test_a_windows_path_is_reduced_to_its_basename() -> None:
    assert _sanitise(r"C:\Users\acme\Desktop\orcamento.pdf") == "orcamento.pdf"


def test_control_characters_are_dropped() -> None:
    assert _sanitise("or\ncamento\x00\tacme.pdf") == "orcamentoacme.pdf"


def test_the_extension_comes_from_the_content_type_not_the_name() -> None:
    assert _sanitise("payload.svg", "image/png") == "payload.png"
    assert _sanitise("payload.html", "image/jpeg") == "payload.jpg"


def test_a_long_stem_is_truncated_with_the_extension_kept() -> None:
    result = sanitise_upload_filename(
        f"{'a' * 300}.pdf", "application/pdf", max_length=32, fallback_stem="documento"
    )

    assert len(result) == 32
    assert result.endswith(".pdf")


def test_an_empty_stem_falls_back() -> None:
    assert _sanitise("...") == "documento.pdf"
    assert _sanitise("") == "documento.pdf"
    assert _sanitise("   ") == "documento.pdf"


# --------------------------------------------------------------------------- #
# save_file
# --------------------------------------------------------------------------- #


def test_save_file_ignores_the_submitted_extension(tmp_path: Path) -> None:
    provider = LocalStorageProvider(base_dir=tmp_path)

    path, url = provider.save_file(b"\x89PNG", "payload.svg", "image/png")

    assert Path(path).suffix == ".png"
    assert url.endswith(".png")
    assert Path(path).exists()


def test_save_file_uses_bin_for_a_type_it_does_not_know(tmp_path: Path) -> None:
    provider = LocalStorageProvider(base_dir=tmp_path)

    path, url = provider.save_file(b"x", "payload.html", "application/x-shockwave")

    assert Path(path).suffix == ".bin"
    assert url.endswith(".bin")


def test_save_file_keeps_the_default_upload_url_prefix(tmp_path: Path) -> None:
    provider = LocalStorageProvider(base_dir=tmp_path)

    _path, url = provider.save_file(b"x", "a.png", "image/png")

    assert url.startswith("/static/uploads/")


def test_the_url_prefix_is_paired_with_the_base_dir(tmp_path: Path) -> None:
    provider = LocalStorageProvider(base_dir=tmp_path, url_prefix="/static/generated")

    path, url = provider.save_file(b"<html>", "r.html", "text/html")

    assert url.startswith("/static/generated/")
    assert url.endswith(".html")
    assert Path(path).is_relative_to(tmp_path)


def test_the_generated_provider_is_rooted_off_the_upload_tree() -> None:
    provider = generated_storage_provider()

    assert provider.base_dir == Path("static/generated")
    assert provider.url_prefix == "/static/generated"


def test_the_stored_name_is_a_uuid_and_never_the_submitted_one(
    tmp_path: Path,
) -> None:
    provider = LocalStorageProvider(base_dir=tmp_path)

    path, _url = provider.save_file(b"x", "orcamento.png", "image/png")

    assert uuid.UUID(Path(path).stem)


# --------------------------------------------------------------------------- #
# The two mounts
# --------------------------------------------------------------------------- #

UPLOADS_DIR = Path("static/uploads")
GENERATED_DIR = Path("static/generated")


@pytest.fixture(name="plant")
def plant_fixture():
    """Write a file under one of the real mounted trees and remove it after.

    The mounts are built at import time from paths relative to the working
    directory, so the file has to be planted there rather than in `tmp_path`.
    """
    planted: list[Path] = []

    def _plant(directory: Path, name: str, payload: bytes) -> str:
        target = directory / "apras65" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        planted.append(target.parent)
        return f"/{directory.as_posix()}/apras65/{name}"

    yield _plant

    for directory in planted:
        shutil.rmtree(directory, ignore_errors=True)


def test_an_image_on_the_upload_mount_is_served_inline_with_nosniff(
    client: TestClient, plant
) -> None:
    url = plant(UPLOADS_DIR, "photo.png", b"\x89PNG\r\n\x1a\n")

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-disposition" not in response.headers


def test_a_planted_svg_on_the_upload_mount_is_forced_to_download(
    client: TestClient, plant
) -> None:
    """The legacy case: a file already on disk with an attacker's extension."""
    url = plant(UPLOADS_DIR, "payload.svg", b"<svg onload=alert(1)></svg>")

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == "attachment"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_a_planted_html_on_the_upload_mount_is_forced_to_download(
    client: TestClient, plant
) -> None:
    """D5: a pre-existing generated report is indistinguishable from this."""
    url = plant(UPLOADS_DIR, "relatorio.html", b"<h1>obras</h1>")

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == "attachment"


def test_a_pdf_on_the_upload_mount_stays_inline(client: TestClient, plant) -> None:
    url = plant(UPLOADS_DIR, "nota.pdf", b"%PDF-1.4")

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "content-disposition" not in response.headers


def test_html_on_the_generated_mount_is_served_inline_with_nosniff(
    client: TestClient, plant
) -> None:
    url = plant(GENERATED_DIR, "relatorio.html", b"<h1>obras</h1>")

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-disposition" not in response.headers


def test_both_mounts_are_present_under_their_names() -> None:
    from app.main import app as main_app

    names = {getattr(route, "name", None) for route in main_app.routes}

    assert {"uploads", "generated"} <= names


# --------------------------------------------------------------------------- #
# D5 -- nothing is migrated
# --------------------------------------------------------------------------- #

APP_DIR = Path("app")
SCRIPTS_DIR = Path("scripts")

#: The two modules allowed to name the generated tree: the mount and the
#: factory. Every generator reaches it through `generated_storage_provider()`,
#: so this pair is the complete answer to "what can write next to
#: inline-rendered HTML".
GENERATED_LITERAL_OWNERS = {
    Path("app/main.py"),
    Path("app/services/storage_service.py"),
}


def _string_constants(module: Path) -> list[str]:
    """Every string literal in ``module`` except the docstrings.

    Comments never reach the AST, so parsing is exactly the "outside comments
    and docstrings" filter the criterion asks for.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(
            node,
            ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def _python_sources() -> list[Path]:
    return sorted(
        [*APP_DIR.rglob("*.py"), *SCRIPTS_DIR.rglob("*.py")],
    )


def test_only_the_mount_and_the_factory_name_the_generated_tree() -> None:
    offenders = {
        module
        for module in _python_sources()
        if any("static/generated" in value for value in _string_constants(module))
    }

    assert offenders == GENERATED_LITERAL_OWNERS, sorted(map(str, offenders))


def test_no_module_moves_a_file_between_the_two_trees() -> None:
    """D5: an automatic mover is unsafe, so none may exist.

    ``mime_type`` and ``file_url`` on a document row are free-form client
    strings, so every selector a migration could use is forgeable by the very
    role the threat model is about. A mover would take an attacker-planted
    file off the mount that forces a download and put it on the one that
    renders inline -- re-opening this vulnerability.
    """
    movers = ("shutil.move", "shutil.copy", "os.rename", "os.replace", ".rename(")
    offenders = {
        (module, mover)
        for module in _python_sources()
        for mover in movers
        if mover in module.read_text(encoding="utf-8")
    }

    assert offenders == set(), sorted((str(path), mover) for path, mover in offenders)


def test_a_legacy_generated_row_is_untouched_and_downloads(
    client: TestClient, session, admin_user, plant
) -> None:
    """D5, end to end: the row keeps its URL and the file stops rendering.

    This is a report saved before APRAS-65 -- and it is byte-identical to a
    file a director planted, which is the whole reason nothing moves it.
    """
    url = plant(UPLOADS_DIR, "relatorio-legado.html", b"<h1>obras</h1>")
    folder = DocumentFolder(name="Obras", tenant_id=DEFAULT_TENANT_ID)
    session.add(folder)
    session.commit()
    session.refresh(folder)
    document = AssociationDocument(
        folder_id=folder.id,
        title="Relatório de Obras — legado",
        file_url=url,
        file_size_bytes=14,
        mime_type="text/html",
        uploaded_by_id=admin_user.id,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    before = document.model_dump()

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == "attachment"
    assert Path(UPLOADS_DIR / "apras65" / "relatorio-legado.html").exists()
    session.expire_all()
    assert session.get(AssociationDocument, document.id).model_dump() == before
