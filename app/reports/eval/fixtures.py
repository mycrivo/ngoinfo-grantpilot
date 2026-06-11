"""Build six-section FCDO NGO content for section-count gates."""

from __future__ import annotations

import copy
from typing import Any

from app.reports.gap.section_visibility import visible_sections_for_context

_EMPTY_SECTION_CONTENT = {
    "citation_mode": "structured",
    "structured_bind_status": "honest_empty",
    "text": "Not reported in fixture.",
    "claims": [],
    "evidence_used": [],
    "assumptions": [],
    "omitted_claims": [],
}


def pad_fcdo_ngo_sections(
    content_json: dict[str, Any],
    template_sections: list[dict[str, Any]],
    *,
    report_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = report_context or {"report_type": "annual"}
    visible = visible_sections_for_context(
        template_sections,
        report_context=ctx,
        include_funder_owned=False,
    )
    by_key = {
        str(s.get("section_key") or ""): s
        for s in content_json.get("sections") or []
        if isinstance(s, dict)
    }
    sections: list[dict[str, Any]] = []
    for template_section in visible:
        key = str(template_section.get("section_key") or "")
        existing = by_key.get(key)
        if existing:
            sections.append(copy.deepcopy(existing))
            continue
        sections.append(
            {
                "section_key": key,
                "label": template_section.get("label"),
                "generation_status": "GENERATED",
                "content": copy.deepcopy(_EMPTY_SECTION_CONTENT),
            }
        )
    return {"sections": sections}
