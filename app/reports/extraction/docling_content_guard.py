"""Post-Docling intake guard — fail loud on unreadable input, do not pass junk to LLMs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

UNREADABLE_DOCUMENT_LOW_CONTENT = "UNREADABLE_DOCUMENT_LOW_CONTENT"
MIN_USABLE_CONTENT_CHARS = 200

_FAILURE_STATUSES = frozenset({"failure", "skipped"})

UnreadableReason = Literal["conversion_failure", "low_content"]


@dataclass(frozen=True)
class UnreadableAssessment:
    reason: UnreadableReason
    conversion_status: str | None
    content_chars: int


def assess_docling_usable(extracted: dict) -> UnreadableAssessment | None:
    """Return an assessment when Docling output must not reach an LLM extractor."""
    status = (extracted.get("conversion_status") or "").lower()
    text = extracted.get("text") or ""
    normalized = text.strip()
    content_chars = len(normalized)

    if status in _FAILURE_STATUSES:
        return UnreadableAssessment(
            reason="conversion_failure",
            conversion_status=status or None,
            content_chars=content_chars,
        )
    if content_chars < MIN_USABLE_CONTENT_CHARS:
        return UnreadableAssessment(
            reason="low_content",
            conversion_status=status or None,
            content_chars=content_chars,
        )
    return None
