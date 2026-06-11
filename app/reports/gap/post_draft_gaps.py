"""Post-draft residual gap analysis — gaps after F1 draft synthesis (Phase 2b)."""

from __future__ import annotations

from typing import Any

from app.reports.gap.deterministic_gaps import build_deterministic_gap_compliance_output
from app.reports.gap.logframe_completeness import (
    derive_missing_logframe_actuals,
    missing_to_gap_items,
    missing_to_template_requirements,
)
from app.reports.gap.template_requirements import (
    enumerate_template_requirements,
    merge_template_requirements,
    ngo_data_gap_denominator,
)
from app.reports.schemas.gap_compliance_v1 import GapComplianceGapItem, GapComplianceOutput


def _draft_hole_gaps(content_json: dict[str, Any]) -> list[GapComplianceGapItem]:
    gaps: list[GapComplianceGapItem] = []
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_key = str(section.get("section_key") or "")
        section_label = str(section.get("label") or section_key)
        bind_status = section.get("structured_bind_status")
        if bind_status == "MISSING_STRUCTURED_CLAIMS":
            item_key = f"{section_key}:section:draft_hole"
            gaps.append(
                GapComplianceGapItem(
                    item_key=item_key,
                    section_key=section_key,
                    section_label=section_label,
                    required_item_type="section",
                    required_item_ref=section_key,
                    severity="required",
                    question=f"We could not draft {section_label} with the evidence on file — can you add or confirm missing inputs?",
                    rationale="Draft synthesis flagged missing structured claims for this section.",
                    owner="ngo",
                    requirement_type="data",
                    suggested_action="provide",
                )
            )
            continue
        for assumption in section.get("assumptions") or []:
            if not isinstance(assumption, str) or not assumption.strip():
                continue
            ref_token = assumption.strip().lower().replace(" ", "_")[:40]
            item_key = f"{section_key}:indicator:draft_assumption:{ref_token}"
            gaps.append(
                GapComplianceGapItem(
                    item_key=item_key,
                    section_key=section_key,
                    section_label=section_label,
                    required_item_type="indicator",
                    required_item_ref=f"draft_assumption_{ref_token}",
                    severity="required",
                    question=assumption.strip(),
                    rationale="The draft noted this assumption because supporting evidence was incomplete.",
                    owner="ngo",
                    requirement_type="data",
                    suggested_action="provide",
                )
            )
        for omitted in (section.get("content") or {}).get("omitted_claims") or []:
            if not isinstance(omitted, str) or not omitted.strip():
                continue
            ref_token = omitted.strip().lower().replace(" ", "_")[:40]
            item_key = f"{section_key}:indicator:draft_omitted:{ref_token}"
            gaps.append(
                GapComplianceGapItem(
                    item_key=item_key,
                    section_key=section_key,
                    section_label=section_label,
                    required_item_type="indicator",
                    required_item_ref=f"draft_omitted_{ref_token}",
                    severity="required",
                    question=f"Can you confirm or provide evidence for: {omitted.strip()}?",
                    rationale="This claim was omitted from the draft because it could not be bound to the knowledge bank.",
                    owner="ngo",
                    requirement_type="data",
                    suggested_action="provide",
                )
            )
    return gaps


def run_post_draft_gap_analysis(
    *,
    content_json: dict[str, Any],
    knowledge_bank_json: dict[str, Any],
    template_payload: dict[str, Any],
    report_context: dict[str, Any] | None = None,
) -> GapComplianceOutput:
    """Emit residual gaps from draft sections + confirmed KB."""
    ctx = report_context or {"report_type": "annual"}
    sections = template_payload.get("report_sections_json") or []
    format_rules = template_payload.get("format_rules_json") or {}
    base_requirements = enumerate_template_requirements(sections, report_context=ctx)
    logframe_missing = derive_missing_logframe_actuals(
        knowledge_bank_json,
        format_rules_json=format_rules,
        report_sections_json=sections,
    )
    requirements = merge_template_requirements(
        base_requirements,
        missing_to_template_requirements(logframe_missing),
    )
    logframe_gaps = missing_to_gap_items(logframe_missing)
    baseline = build_deterministic_gap_compliance_output(
        requirements=requirements,
        knowledge_bank_json=knowledge_bank_json,
        logframe_gaps=logframe_gaps,
        checklist_non_section_count=ngo_data_gap_denominator(requirements),
        readiness_basis="post_draft",
    )
    draft_gaps = _draft_hole_gaps(content_json)
    by_key = {gap.item_key: gap for gap in baseline.gaps}
    for gap in draft_gaps:
        by_key.setdefault(gap.item_key, gap)
    merged = list(by_key.values())
    denominator = max(ngo_data_gap_denominator(requirements), len(merged), 1)
    if not merged:
        return GapComplianceOutput(
            open_items_count=0,
            ready_for_gate2=True,
            gaps=[],
            readiness_basis="post_draft",
        )
    data_gaps = [g for g in merged if (g.requirement_type or "data") == "data"]
    return GapComplianceOutput(
        open_items_count=len(data_gaps),
        ready_for_gate2=False,
        gaps=merged,
        readiness_basis="post_draft",
    )
