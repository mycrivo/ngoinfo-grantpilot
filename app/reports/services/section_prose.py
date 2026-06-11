"""Section prose helpers — non-empty body contract (P3-7 F-9)."""

from __future__ import annotations

from typing import Any

MIN_SECTION_PROSE_CHARS = 40

FAILURE_EMPTY_PROSE = "EMPTY_SECTION_PROSE"


def section_prose_text(section: dict[str, Any]) -> str:
    content = section.get("content") or {}
    return str(content.get("text") or "")


def has_non_empty_prose(section: dict[str, Any]) -> bool:
    return bool(section_prose_text(section).strip())


def assemble_prose_from_bound_claims(claims: list[dict[str, Any]]) -> str:
    """Join bound claim clauses when the model omitted generated_content.text."""
    parts: list[str] = []
    for claim in claims or []:
        if not isinstance(claim, dict):
            continue
        if claim.get("bind_status") not in ("bound", "omitted_numeric"):
            continue
        text = str(claim.get("text") or "").strip()
        if text and (not parts or parts[-1] != text):
            parts.append(text)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return "\n\n".join(parts)


def section_meets_minimum_substance(section: dict[str, Any]) -> bool:
    status = section.get("generation_status")
    if status in ("FAILED", None):
        return False
    if status not in ("GENERATED", "AWAITING_REVIEW", "ACCEPTED"):
        return False
    return len(section_prose_text(section).strip()) >= MIN_SECTION_PROSE_CHARS
