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
    remapped_citations: list[dict[str, str]] | None = None,
    auto_citations: list[str] | None = None,
) -> dict[str, Any]:
    content: dict[str, Any] = {
        "text": text,
        "assumptions": assumptions,
        "evidence_used": evidence_used,
    }
    if dropped_citations:
        content["dropped_citations"] = dropped_citations
    if remapped_citations:
        content["remapped_citations"] = remapped_citations
    if auto_citations:
        content["auto_citations"] = auto_citations
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


def compute_generation_summary_from_sections(
    sections: list[dict[str, Any]],
    *,
    warnings: list[str],
) -> dict[str, Any]:
    """Aggregate generation_summary from a merged section list (§2.8)."""
    generated = failed = awaiting_review = accepted = critic_blocks = 0
    for section in sections:
        if not isinstance(section, dict):
            continue
        status = section.get("generation_status")
        if status == "GENERATED":
            generated += 1
        elif status == "FAILED":
            failed += 1
        elif status == "AWAITING_REVIEW":
            awaiting_review += 1
        elif status == "ACCEPTED":
            accepted += 1
        for flag in section.get("critic_flags") or []:
            if (
                isinstance(flag, dict)
                and flag.get("severity") == "BLOCK"
                and not flag.get("accepted")
            ):
                critic_blocks += 1
    return {
        "total_sections": len(sections),
        "generated": generated,
        "failed": failed,
        "awaiting_review": awaiting_review,
        "accepted": accepted,
        "critic_blocks": critic_blocks,
        "warnings": warnings,
    }


_SKIP_IF_NON_EMPTY_TEXT = frozenset({"GENERATED", "AWAITING_REVIEW", "ACCEPTED"})


def section_needs_synthesis(existing: dict[str, Any] | None) -> bool:
    """True when F1 should call OpenAI for this section (resume: skip completed work)."""
    if existing is None:
        return True
    if existing.get("human_edited") is True:
        return False
    if existing.get("generation_status") == "ACCEPTED":
        return False
    text = str((existing.get("content") or {}).get("text") or "").strip()
    status = existing.get("generation_status")
    if status in _SKIP_IF_NON_EMPTY_TEXT and text:
        return False
    if status == "FAILED":
        return True
    if not text:
        return True
    return False


def merge_synthesis_sections(
    *,
    template_sections: list[dict[str, Any]],
    existing_by_key: dict[str, dict[str, Any]],
    new_results_by_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Walk template order; apply fresh results or carry forward existing sections."""
    merged: list[dict[str, Any]] = []
    for template_section in template_sections:
        key = str(template_section["section_key"])
        if key in new_results_by_key:
            merged.append(new_results_by_key[key])
        elif key in existing_by_key:
            merged.append(existing_by_key[key])
        else:
            label = str(template_section.get("label") or key)
            word_limit = int(template_section.get("word_limit") or 0)
            merged.append(
                build_failed_section(
                    section_key=key,
                    label=label,
                    word_limit=word_limit,
                    failure_reason="NOT_GENERATED",
                )
            )
    return merged


def merge_content_json_after_synthesis(
    existing_content_json: dict[str, Any],
    merged_sections: list[dict[str, Any]],
    *,
    warnings: list[str],
) -> dict[str, Any]:
    """Merge synthesis output into prior content_json; preserve sibling top-level keys."""
    out = dict(existing_content_json or {})
    out["sections"] = merged_sections
    out["generation_summary"] = compute_generation_summary_from_sections(
        merged_sections,
        warnings=warnings,
    )
    return out


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
    return {
        "sections": sections,
        "generation_summary": compute_generation_summary_from_sections(
            sections,
            warnings=warnings,
        ),
    }
