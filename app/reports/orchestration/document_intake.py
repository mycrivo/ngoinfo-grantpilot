"""Load uploaded document content for classify / extract stages."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Callable

from app.reports.extraction.docling_adapter import extract_text_from_path
from app.reports.extraction.spreadsheet_input import (
    parse_spreadsheet_from_path,
    spreadsheet_to_json_text,
)
from app.reports.models.enums import DocumentClassification
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.services.document_storage_service import DocumentStorageService

TextLoader = Callable[[UploadedDocument], str]
SpreadsheetLoader = Callable[[UploadedDocument], tuple[str, str | None]]

_PHOTO_MIME_PREFIXES = ("image/",)
_DECK_MIME_TYPES = frozenset(
    {
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)


def classification_from_mime(mime_type: str) -> str | None:
    """Upstream routing for non-text uploads (photo/deck)."""
    lowered = mime_type.lower()
    if lowered.startswith(_PHOTO_MIME_PREFIXES):
        return DocumentClassification.PHOTO.value
    if lowered in _DECK_MIME_TYPES:
        return DocumentClassification.DECK.value
    return None


def _default_storage() -> DocumentStorageService:
    return DocumentStorageService()


def _write_temp_file(document: UploadedDocument, data: bytes) -> Path:
    suffix = Path(document.original_filename).suffix or ".bin"
    path = Path(tempfile.gettempdir()) / f"me-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return path


def load_document_text(
    document: UploadedDocument,
    *,
    storage: DocumentStorageService | None = None,
    loader_override: TextLoader | None = None,
) -> str:
    if loader_override is not None:
        return loader_override(document)
    store = storage or _default_storage()
    data = store.fetch_bytes(document.storage_ref)
    path = _write_temp_file(document, data)
    try:
        extracted = extract_text_from_path(path)
        return extracted.get("text", "")
    finally:
        path.unlink(missing_ok=True)


def load_spreadsheet_json(
    document: UploadedDocument,
    *,
    storage: DocumentStorageService | None = None,
    loader_override: SpreadsheetLoader | None = None,
) -> tuple[str, str | None]:
    if loader_override is not None:
        return loader_override(document)
    store = storage or _default_storage()
    data = store.fetch_bytes(document.storage_ref)
    path = _write_temp_file(document, data)
    try:
        parsed = parse_spreadsheet_from_path(path)
        text, _truncated = spreadsheet_to_json_text(parsed)
        from app.reports.extraction.spreadsheet_input import compute_spreadsheet_hash

        return text, compute_spreadsheet_hash(parsed)
    finally:
        path.unlink(missing_ok=True)
