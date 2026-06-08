"""Upload format gating — extension/MIME lane validation at the door (P1 / D1).

Validation is lane-based at upload time, independent of later classifier labels.
Monitoring data (indicator_data after classify): `.xlsx`, `.csv`, and `.docx` with
tables (P5 — `.docx` accepted via the text lane at upload; extracted via Docling).
"""

from __future__ import annotations

from pathlib import Path

from app.core.errors import DomainError

TEXT_EXTENSIONS = frozenset({".docx", ".pdf", ".txt"})
SPREADSHEET_EXTENSIONS = frozenset({".xlsx", ".csv"})
PHOTO_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
)
DECK_EXTENSIONS = frozenset({".ppt", ".pptx"})

# Legacy / near-miss types rejected with the spreadsheet lane message.
_SPREADSHEET_REJECT_EXTENSIONS = frozenset({".xls", ".xlsm", ".ods", ".xlsb"})

_DECK_MIME_TYPES = frozenset(
    {
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)

_TEXT_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)

_SPREADSHEET_MIME_TYPES = frozenset(
    {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)

_LANE_MESSAGES: dict[str, str] = {
    "text": (
        "This file is not supported for project documents. "
        "Upload Word (.docx), PDF (.pdf), or plain text (.txt)."
    ),
    "spreadsheet": (
        "This file is not supported for monitoring data. "
        "Upload Excel (.xlsx), CSV (.csv), or Word (.docx) with tables."
    ),
    "photo": (
        "This image format is not supported. "
        "Upload JPEG, PNG, GIF, or WebP."
    ),
    "deck": (
        "This presentation format is not supported. "
        "Upload PowerPoint (.ppt or .pptx)."
    ),
    "unsupported": (
        "This file type is not supported. "
        "Use Word (.docx), PDF (.pdf), or text (.txt) for project documents; "
        "Excel (.xlsx), CSV (.csv), or Word (.docx) with tables for monitoring data; "
        "common images or PowerPoint for supporting files."
    ),
}

_LANE_ACCEPTED: dict[str, list[str]] = {
    "text": sorted(TEXT_EXTENSIONS),
    "spreadsheet": sorted(SPREADSHEET_EXTENSIONS),
    "photo": sorted(PHOTO_EXTENSIONS),
    "deck": sorted(DECK_EXTENSIONS),
}


def _normalized_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix else ""


def _normalized_mime(mime_type: str) -> str:
    return (mime_type or "application/octet-stream").split(";", 1)[0].strip().lower()


def _is_photo_mime(mime: str) -> bool:
    return mime.startswith("image/")


def _reject(lane: str, *, filename: str, extension: str) -> None:
    raise DomainError(
        error_code="UNSUPPORTED_DOCUMENT_FORMAT",
        message=_LANE_MESSAGES[lane],
        status_code=422,
        details={
            "lane": lane,
            "accepted_extensions": _LANE_ACCEPTED.get(lane, []),
            "filename": filename,
            "extension": extension or None,
        },
    )


def validate_upload_format(*, filename: str, mime_type: str) -> None:
    """Raise DomainError when filename/MIME is not accepted for any upload lane."""
    extension = _normalized_extension(filename)
    mime = _normalized_mime(mime_type)

    if extension in TEXT_EXTENSIONS:
        return
    if extension in SPREADSHEET_EXTENSIONS:
        return
    if extension in PHOTO_EXTENSIONS:
        return
    if extension in DECK_EXTENSIONS:
        return

    if extension in _SPREADSHEET_REJECT_EXTENSIONS:
        _reject("spreadsheet", filename=filename, extension=extension)

    if _is_photo_mime(mime):
        return

    if mime in _DECK_MIME_TYPES:
        return

    if mime in _TEXT_MIME_TYPES:
        if extension in {".doc", ".rtf", ".odt", ".docm"}:
            _reject("text", filename=filename, extension=extension)
        if extension and extension not in TEXT_EXTENSIONS:
            _reject("text", filename=filename, extension=extension)
        return

    if mime in _SPREADSHEET_MIME_TYPES:
        _reject("spreadsheet", filename=filename, extension=extension)

    if extension in {".doc", ".rtf", ".odt", ".docm"}:
        _reject("text", filename=filename, extension=extension)

    if extension == ".zip":
        raise DomainError(
            error_code="UNSUPPORTED_DOCUMENT_FORMAT",
            message=(
                "Compressed archives are not supported. "
                "Upload the document inside using Word (.docx), PDF (.pdf), "
                "or plain text (.txt) for project documents, or Excel (.xlsx), "
                "CSV (.csv), or Word (.docx) with tables for monitoring data."
            ),
            status_code=422,
            details={
                "lane": "unsupported",
                "accepted_extensions": [],
                "filename": filename,
                "extension": extension,
            },
        )

    _reject("unsupported", filename=filename, extension=extension)
