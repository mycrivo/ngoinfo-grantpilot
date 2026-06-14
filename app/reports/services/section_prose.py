"""Section prose helpers — non-empty body contract (P3-7 F-9)."""

from __future__ import annotations

from typing import Any

from app.reports.schemas.content_json_v1 import build_generated_section
from app.reports.services.ngo_text_redaction import (
    humanize_identifier,
    redact_internal_identifiers,
)

MIN_SECTION_PROSE_CHARS = 40

FAILURE_EMPTY_PROSE = "EMPTY_SECTION_PROSE"
STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA = "insufficient_data"


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


def _humanize_requirement_refs(refs: list[str]) -> str:
    """Plain-English, identifier-free names for required items (colon-paths translated)."""
    readable = [humanize_identifier(ref) for ref in refs if str(ref).strip()]
    readable = [r for r in readable if r]
    if not readable:
        return ""
    if len(readable) == 1:
        return readable[0]
    return ", ".join(readable[:-1]) + f", and {readable[-1]}"


def build_insufficiency_statement(
    *,
    section: dict[str, Any],
    unsatisfied_refs: list[str] | None = None,
) -> str:
    """Deterministic, submittable prose when no citable section inputs exist (P3-8).

    Names the missing requirements in plain language. When the template declares no
    named requirements for the section, the requirement clause is dropped entirely
    rather than emitting a generic placeholder (Package 1, A3).
    """
    label = str(section.get("label") or section.get("section_key") or "this section").strip()
    refs = unsatisfied_refs or list(section.get("required_indicators") or [])
    items_phrase = _humanize_requirement_refs(refs)
    if items_phrase:
        requirement_clause = (
            f"The template requires information on {items_phrase}, but no citable "
            f"source supplied those items for \"{label}\". "
        )
    else:
        requirement_clause = (
            f"No citable source in the uploaded documents or confirmed gap answers "
            f"supplied material for \"{label}\". "
        )
    statement = (
        f"This section could not be drafted from the material available in uploaded "
        f"documents or confirmed gap answers for the reporting period. "
        f"{requirement_clause}"
        f"Accordingly, no narrative is presented here: the organisation has left "
        f"this section blank rather than report anything not supported by the "
        f"available evidence."
    )
    return redact_internal_identifiers(statement)


def build_insufficient_data_section(
    *,
    section: dict[str, Any],
    unsatisfied_refs: list[str] | None = None,
) -> dict[str, Any]:
    """GENERATED section with engine-owned insufficiency prose (P3-8)."""
    section_key = str(section.get("section_key") or "")
    label = str(section.get("label") or section_key)
    word_limit = int(section.get("word_limit") or 0)
    text = build_insufficiency_statement(section=section, unsatisfied_refs=unsatisfied_refs)
    return build_generated_section(
        section_key=section_key,
        label=label,
        archetype=section.get("archetype"),
        text=text,
        assumptions=[],
        evidence_used=[],
        claims=[],
        citation_mode="structured",
        structured_bind_status=STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA,
        word_limit=word_limit,
        word_limit_respected=True,
    )
