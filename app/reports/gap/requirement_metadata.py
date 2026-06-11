"""Resolve owner and requirement_type for template checklist items (schema v1.2.0)."""

from __future__ import annotations

from typing import Any, Literal

RequirementOwner = Literal["ngo", "funder"]
RequirementType = Literal["data", "narrative", "funder_supplied"]

FUNDER_SUPPLIED_INDICATORS = frozenset(
    {
        "output_scores",
        "impact_weightings",
        "risk_ratings",
        "economy",
        "efficiency",
        "effectiveness",
        "equity",
        "vfm_measures",
        "commercial_improvement_where_relevant",
        "FCDO_management_actions",
    }
)

NARRATIVE_INDICATORS = frozenset(
    {
        "overall_progress",
        "main_results_achieved",
        "main_issues",
        "key_recommendations",
        "major_deviations",
        "new_evidence",
        "evaluation_progress",
        "evidence_base_strength",
        "data_quality_limitations",
        "new_risks",
        "realised_assumptions",
        "funds_not_used_as_intended_risk",
        "climate_environment_risk",
        "safeguarding_risk_where_relevant",
        "partner_performance",
        "supplier_or_consultant_performance",
        "commercial_or_procurement_issues",
        "recommendations_from_current_review",
        "updates_on_previous_recommendations",
        "priorities_for_next_period",
        "recommendations_action_plan",
        "gender_age_or_vulnerable_group_disaggregation_where_relevant",
        "community_participation_examples",
        "partner_or_local_collaboration_examples",
        "community_feedback",
        "staff_or_volunteer_feedback",
        "overall_project_reflection",
        "unshared_evidence_or_learning",
        "unspent_funds_status",
    }
)

FUNDER_OWNED_SECTIONS = frozenset({"detailed_output_scoring", "value_for_money"})

FUNDER_SUPPLIED_TABLES = frozenset({"output_score_table", "vfm_measures"})


def _indicator_meta(section: dict[str, Any], indicator_key: str) -> dict[str, Any]:
    meta_map = section.get("indicator_requirements") or {}
    entry = meta_map.get(indicator_key)
    return entry if isinstance(entry, dict) else {}


def _table_meta(section: dict[str, Any], table_key: str) -> dict[str, Any]:
    meta_map = section.get("table_requirements") or {}
    entry = meta_map.get(table_key)
    return entry if isinstance(entry, dict) else {}


def _fallback_requirement_type(
    *,
    section_key: str,
    item_ref: str,
    item_type: str,
) -> RequirementType:
    if item_type == "table" and item_ref in FUNDER_SUPPLIED_TABLES:
        return "funder_supplied"
    if item_ref in FUNDER_SUPPLIED_INDICATORS:
        return "funder_supplied"
    if item_ref in NARRATIVE_INDICATORS:
        return "narrative"
    if section_key in FUNDER_OWNED_SECTIONS and item_ref in FUNDER_SUPPLIED_INDICATORS:
        return "funder_supplied"
    return "data"


def resolve_owner(
    section: dict[str, Any],
    *,
    item_ref: str | None = None,
    item_type: str = "indicator",
) -> RequirementOwner:
    section_owner = section.get("owner")
    if item_ref and item_type == "indicator":
        override = _indicator_meta(section, item_ref).get("owner")
        if override in ("ngo", "funder"):
            return override
    if item_ref and item_type == "table":
        override = _table_meta(section, item_ref).get("owner")
        if override in ("ngo", "funder"):
            return override
    if section_owner in ("ngo", "funder"):
        return section_owner
    section_key = str(section.get("section_key") or "")
    if section_key in FUNDER_OWNED_SECTIONS:
        if item_ref and item_ref in FUNDER_SUPPLIED_INDICATORS:
            return "funder"
        if item_type == "table" and item_ref in FUNDER_SUPPLIED_TABLES:
            return "funder"
    if item_ref in FUNDER_SUPPLIED_INDICATORS:
        return "funder"
    if item_type == "table" and item_ref in FUNDER_SUPPLIED_TABLES:
        return "funder"
    return "ngo"


def resolve_requirement_type(
    section: dict[str, Any],
    *,
    item_ref: str,
    item_type: str,
) -> RequirementType:
    section_default = section.get("requirement_type_default")
    if item_type == "indicator":
        override = _indicator_meta(section, item_ref).get("requirement_type")
        if override in ("data", "narrative", "funder_supplied"):
            return override
    if item_type == "table":
        override = _table_meta(section, item_ref).get("requirement_type")
        if override in ("data", "narrative", "funder_supplied"):
            return override
    if section_default in ("data", "narrative", "funder_supplied"):
        return section_default
    section_key = str(section.get("section_key") or "")
    return _fallback_requirement_type(
        section_key=section_key,
        item_ref=item_ref,
        item_type=item_type,
    )


def is_ngo_checklist_item(owner: RequirementOwner, requirement_type: RequirementType) -> bool:
    """NGO-facing Gate 2 checklist excludes funder-owned and funder_supplied items."""
    if owner == "funder":
        return False
    if requirement_type == "funder_supplied":
        return False
    return True


def is_ngo_data_gap_item(requirement_type: RequirementType) -> bool:
    """Readiness denominator counts only NGO-answerable data gaps."""
    return requirement_type == "data"
