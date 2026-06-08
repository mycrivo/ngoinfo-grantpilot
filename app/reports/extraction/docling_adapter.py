from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("reports.extraction.docling")


class DoclingIntakeError(Exception):
    """Docling could not extract text from the document (per-document degrade)."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


def extract_text_from_path(path: Path) -> dict:
    """Extract structured text from a document using Docling."""
    try:
        from docling.document_converter import DocumentConverter
    except OSError as exc:
        raise DoclingIntakeError(
            f"Docling import failed: {exc}",
            cause=exc,
        ) from exc

    try:
        converter = DocumentConverter()
        result = converter.convert(str(path))
    except Exception as exc:
        raise DoclingIntakeError(
            f"Docling conversion failed: {exc}",
            cause=exc,
        ) from exc

    document = result.document
    text = document.export_to_markdown()
    conversion_errors: list[str] = []
    for item in getattr(result, "errors", None) or []:
        message = getattr(item, "error_message", None) or str(item)
        if message:
            conversion_errors.append(message)
    metadata = {
        "source_path": str(path),
        "page_count": len(getattr(document, "pages", []) or []),
    }
    return {
        "text": text,
        "metadata": metadata,
        "conversion_status": result.status.value,
        "conversion_errors": conversion_errors,
    }
