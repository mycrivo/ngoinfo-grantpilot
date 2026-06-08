"""Optional OCR fallback for image-only PDFs when Docling yields low content."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("reports.extraction.pdf_ocr")

_PDF_SUFFIXES = frozenset({".pdf"})


def try_ocr_pdf(path: Path) -> dict | None:
    """
    Attempt Tesseract OCR on a PDF. Returns extracted dict or None if OCR unavailable.

    Requires system packages: tesseract-ocr, poppler-utils (pdf2image).
    """
    if path.suffix.lower() not in _PDF_SUFFIXES:
        return None
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        logger.debug("OCR dependencies not installed — skipping pdf_ocr_fallback")
        return None

    try:
        images = convert_from_path(str(path), dpi=200)
    except Exception as exc:
        logger.warning("pdf2image failed for %s: %s", path, exc)
        return None

    chunks: list[str] = []
    for index, image in enumerate(images, start=1):
        try:
            page_text = pytesseract.image_to_string(image)
        except Exception as exc:
            logger.warning("tesseract failed page %s of %s: %s", index, path, exc)
            continue
        if page_text.strip():
            chunks.append(page_text.strip())

    text = "\n\n".join(chunks)
    if not text.strip():
        return None

    return {
        "text": text,
        "metadata": {
            "source_path": str(path),
            "page_count": len(images),
            "intake_method": "ocr_fallback",
        },
        "conversion_status": "success",
        "conversion_errors": [],
    }
