"""Load uploaded document content for classify / extract stages."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Callable

from app.reports.extraction.docling_adapter import DoclingIntakeError, extract_text_from_path
from app.reports.extraction.docling_content_guard import assess_docling_usable
from app.reports.extraction.pdf_ocr_fallback import try_ocr_pdf
from app.reports.extraction.spreadsheet_input import (
    parse_spreadsheet_from_path,
    spreadsheet_to_json_text,
)
from app.reports.models.enums import DocumentClassification
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.services.document_storage_service import DocumentStorageService

TextLoader = Callable[[UploadedDocument], str]
SpreadsheetLoader = Callable[[UploadedDocument], tuple[str, str | None]]
ExtractionLoader = Callable[[UploadedDocument], dict]

_PHOTO_MIME_PREFIXES = ("image/",)
_DECK_MIME_TYPES = frozenset(
    {
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)
_PDF_MIME_TYPES = frozenset({"application/pdf"})


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


def _is_pdf_document(document: UploadedDocument, path: Path) -> bool:
    if document.mime_type.lower() in _PDF_MIME_TYPES:
        return True
    return path.suffix.lower() == ".pdf"


def extract_text_with_fallback(path: Path, *, is_pdf: bool) -> dict:
    """Docling first; OCR fallback for PDFs when output is unusable."""
    try:
        extracted = extract_text_from_path(path)
    except DoclingIntakeError as exc:
        if is_pdf:
            ocr = try_ocr_pdf(path)
            if ocr is not None:
                return ocr
        raise

    if is_pdf and assess_docling_usable(extracted) is not None:
        ocr = try_ocr_pdf(path)
        if ocr is not None and assess_docling_usable(ocr) is None:
            return ocr
    return extracted


def load_document_extraction(
    document: UploadedDocument,
    *,
    storage: DocumentStorageService | None = None,
    loader_override: ExtractionLoader | None = None,
) -> dict:
    """Load full Docling/OCR extraction dict for classify intake."""
    if loader_override is not None:
        return loader_override(document)
    store = storage or _default_storage()
    data = store.fetch_bytes(document.storage_ref)
    path = _write_temp_file(document, data)
    try:
        is_pdf = _is_pdf_document(document, path)
        return extract_text_with_fallback(path, is_pdf=is_pdf)
    finally:
        path.unlink(missing_ok=True)


def load_document_text(
    document: UploadedDocument,
    *,
    storage: DocumentStorageService | None = None,
    loader_override: TextLoader | None = None,
) -> str:
    if loader_override is not None:
        return loader_override(document)
    extracted = load_document_extraction(document, storage=storage)
    return extracted.get("text", "")


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
