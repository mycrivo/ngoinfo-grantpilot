"""donor_reports.content_json shape helpers — DB contract §2.8."""

from __future__ import annotations

from typing import Any


def build_generated_section(
    *,
    section_key: str,
    label: str,
    archetype: str | None,
    text: str,
    assumptions: list[str],
    evidence_used: list[str],
    word_limit: int,
    word_limit_respected: bool,
    dropped_citations: list[str] | None = None,
) -> dict[str, Any]:
    content: dict[str, Any] = {
        "text": text,
        "assumptions": assumptions,
        "evidence_used": evidence_used,
    }
    if dropped_citations:
        content["dropped_citations"] = dropped_citations
    return {
        "section_key": section_key,
        "label": label,
        "generation_status": "GENERATED",
        "archetype": archetype,
        "content": content,
        "critic_flags": [],
        "failure_reason": None,
        "constraints_applied": {
            "word_limit": word_limit,
            "word_limit_respected": word_limit_respected,
        },
        "human_edited": False,
        "last_edited_at": None,
    }


def build_failed_section(
    *,
    section_key: str,
    label: str,
    word_limit: int,
    failure_reason: str,
) -> dict[str, Any]:
    return {
        "section_key": section_key,
        "label": label,
        "generation_status": "FAILED",
        "archetype": None,
        "content": {
            "text": "",
            "assumptions": [],
            "evidence_used": [],
        },
        "critic_flags": [],
        "failure_reason": failure_reason,
        "constraints_applied": {
            "word_limit": word_limit,
            "word_limit_respected": False,
        },
        "human_edited": False,
        "last_edited_at": None,
    }


def build_generation_summary(
    *,
    total_sections: int,
    generated: int,
    failed: int,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "total_sections": total_sections,
        "generated": generated,
        "failed": failed,
        "awaiting_review": 0,
        "accepted": 0,
        "critic_blocks": 0,
        "warnings": warnings,
    }


def sections_by_key(sections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for section in sections:
        key = section.get("section_key")
        if key:
            out[str(key)] = section
    return out


def assemble_content_json(
    sections: list[dict[str, Any]],
    *,
    warnings: list[str],
) -> dict[str, Any]:
    generated = sum(1 for s in sections if s.get("generation_status") == "GENERATED")
    failed = sum(1 for s in sections if s.get("generation_status") == "FAILED")
    return {
        "sections": sections,
        "generation_summary": build_generation_summary(
            total_sections=len(sections),
            generated=generated,
            failed=failed,
            warnings=warnings,
        ),
    }
