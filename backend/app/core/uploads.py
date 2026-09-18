"""What an uploaded file may be called on disk, and what may be served inline.

Every upload in APRAS reaches disk through
:meth:`app.services.storage_service.LocalStorageProvider.save_file`, which
writes into ``static/uploads`` -- a tree an unauthenticated ``StaticFiles``
mount serves with the content type *guessed from the file extension*. Letting
the client's own file name choose that extension is stored XSS: valid PNG
bytes posted as ``payload.svg`` were written as ``.svg`` and served back as
``image/svg+xml``, which browsers execute in the application's origin.

So the submitted name never decides the extension. It is derived here from the
``content_type`` the calling service has already validated against its own
allowlist, and the submitted name survives only as display metadata --
sanitised by :func:`sanitise_upload_filename` where a service persists it.
"""

from pathlib import Path

#: The one extension each accepted ``content_type`` may ever have on disk.
#:
#: This map is the whole defence, so it must cover **every** type any caller
#: can pass: the media, announcement, finance, tenant-logo and quote-attachment
#: allowlists, plus the ``text/html`` the assembly-minutes and works-report
#: generators write. ``tests/test_upload_filename_safety.py`` reads those
#: allowlists back out of the services and fails if one of them grows a type
#: this map does not name -- the alternative being a silent fall to
#: :data:`FALLBACK_EXTENSION`, which would be a hole rather than an error.
CONTENT_TYPE_EXTENSIONS: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "text/html": ".html",
}

#: The suffix an unmapped ``content_type`` gets. Inert by construction: it is
#: outside :data:`INLINE_SAFE_EXTENSIONS`, so the hardened mount serves it as
#: ``application/octet-stream`` with ``Content-Disposition: attachment``.
FALLBACK_EXTENSION = ".bin"

#: The extensions ``/static/uploads`` may still serve with their guessed type.
#: Everything else -- including ``.svg`` and ``.html``, the two active-content
#: cases -- is forced to download. Deliberately not a function of the MIME
#: map: this set governs files **already on disk**, whose suffix predates the
#: fix and was chosen by whoever uploaded them.
INLINE_SAFE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".pdf"})


def _normalise(content_type: str) -> str:
    """Lower-case, parameters dropped: ``text/html; charset=utf-8`` is HTML."""
    return content_type.split(";", 1)[0].strip().lower()


def canonical_extension(content_type: str) -> str:
    """The only suffix a file of ``content_type`` may carry on disk."""
    return CONTENT_TYPE_EXTENSIONS.get(_normalise(content_type), FALLBACK_EXTENSION)


def sanitise_upload_filename(
    filename: str,
    content_type: str,
    *,
    max_length: int,
    fallback_stem: str,
) -> str:
    """The client's name, reduced to something safe to store and to show.

    Four steps, in this order: take the basename (POSIX *and* Windows
    separators, since the browser sends whatever the client OS gave it), drop
    every non-printable character, force the extension from the
    already-validated ``content_type``, then truncate the stem so the whole
    name fits ``max_length`` with its extension intact. A name that reduces to
    nothing gets ``fallback_stem``.

    This is display metadata only -- the on-disk name is a UUID -- but a value
    a service persists and a browser renders still must not carry a path or a
    type the bytes are not.
    """
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    printable = "".join(character for character in basename if character.isprintable())
    stem = Path(printable.strip().strip(".").strip()).stem.strip()
    extension = canonical_extension(content_type)
    stem = stem[: max_length - len(extension)].strip()
    return f"{stem or fallback_stem}{extension}"
