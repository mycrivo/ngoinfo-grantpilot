from __future__ import annotations

from pathlib import Path


def extract_text_from_path(path: Path) -> dict:
    """Extract structured text from a document using Docling."""
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(path))
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
