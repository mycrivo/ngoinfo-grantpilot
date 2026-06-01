"""Content-based graders for E3 gap/compliance (section + required-item identity)."""

from __future__ import annotations

from typing import Any

from app.reports.gap.logframe_completeness import (
    derive_missing_logframe_actuals,
    logframe_missing_identities,
)
from app.reports.gap.satisfaction import unsatisfied_requirements
from app.reports.gap.template_requirements import enumerate_template_requirements


def _gap_identity(gap: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(gap.get("section_key")),
        str(gap.get("required_item_type")),
        str(gap.get("required_item_ref")),
    )


def grade_gap_compliance(
    gap_analysis: dict[str, Any],
    *,
    template_sections: list[dict[str, Any]],
    knowledge_bank_json: dict[str, Any],
    answer_key: dict[str, Any],
    report_context: dict[str, Any] | None = None,
    format_rules_json: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    ctx = report_context or answer_key.get("report_context") or {"report_type": "annual"}
    requirements = enumerate_template_requirements(template_sections, report_context=ctx)
    expected_missing = answer_key.get("expected_missing") or []
    forbidden = answer_key.get("forbidden_gaps") or []
    max_gaps = answer_key.get("max_gaps")

    gaps = gap_analysis.get("gaps") or []
    if not isinstance(gaps, list):
        return ["gaps must be a list"]

    readiness = gap_analysis.get("readiness_score")
    if readiness is None:
        errors.append("missing readiness_score")
    elif not isinstance(readiness, int) or readiness < 0 or readiness > 100:
        errors.append(f"invalid readiness_score: {readiness!r}")

    expected_identities = {
        (
            item["section_key"],
            item["required_item_type"],
            item["required_item_ref"],
        )
        for item in expected_missing
    }
    gap_identities = {_gap_identity(g) for g in gaps if isinstance(g, dict)}

    for identity in expected_identities:
        if identity not in gap_identities:
            errors.append(f"expected missing gap not surfaced: {identity!r}")

    for identity in forbidden:
        if isinstance(identity, dict):
            trip = (
                identity["section_key"],
                identity["required_item_type"],
                identity["required_item_ref"],
            )
        else:
            trip = tuple(identity)
        if trip in gap_identities:
            errors.append(f"forbidden gap surfaced: {trip!r}")

    if max_gaps is not None and len(gaps) > int(max_gaps):
        errors.append(f"too many gaps: {len(gaps)} > {max_gaps}")

    derived_missing = unsatisfied_requirements(requirements, knowledge_bank_json)
    derived_identities = {req.identity for req in derived_missing}
    logframe_missing = derive_missing_logframe_actuals(
        knowledge_bank_json,
        format_rules_json=format_rules_json,
        report_sections_json=template_sections,
    )
    derived_identities |= logframe_missing_identities(logframe_missing)
    for gap in gaps:
        if not isinstance(gap, dict):
            errors.append("gap entry must be object")
            continue
        gid = _gap_identity(gap)
        if gid not in derived_identities and gid not in expected_identities:
            errors.append(f"gap {gid!r} not derivable as unsatisfied from KB")

    if expected_identities and readiness == 100:
        errors.append("readiness_score 100 with expected missing items")

    if not expected_identities and gaps and max_gaps == 0:
        errors.append(f"complete bank should have no gaps, got {len(gaps)}")

    return errors
