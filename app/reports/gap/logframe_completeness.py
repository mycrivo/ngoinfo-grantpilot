"""Deterministic logframe row completeness — proposal targets vs indicator-data actuals."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.reports.gap.template_requirements import TemplateRequirement, _item_key
from app.reports.schemas.gap_compliance_v1 import GapComplianceGapItem

_INDICATOR_ID_RE = re.compile(r"op(\d+)_(\d+)", re.IGNORECASE)
_LOGFRAME_ROW_REF_PREFIX = "logframe_row:"


@dataclass(frozen=True)
class MissingLogframeActual:
    indicator_id: str
    indicator_label: str
    proposal_target_value: str | None
    missing_facet: str
    section_key: str
    section_label: str
    required_item_ref: str
    item_key: str


def normalize_indicator_id(text: str) -> str | None:
    """Extract canonical opN_N id from a fact key or semantic label."""
    normalized = text.lower().replace(".", "_")
    match = _INDICATOR_ID_RE.search(normalized)
    if not match:
        return None
    return f"op{match.group(1)}_{match.group(2)}"


def logframe_row_ref(indicator_id: str) -> str:
    return f"{_LOGFRAME_ROW_REF_PREFIX}{indicator_id}"


def is_logframe_row_ref(required_item_ref: str) -> bool:
    return required_item_ref.startswith(_LOGFRAME_ROW_REF_PREFIX)


def logframe_indicator_id_from_ref(required_item_ref: str) -> str | None:
    if not is_logframe_row_ref(required_item_ref):
        return None
    raw = required_item_ref.removeprefix(_LOGFRAME_ROW_REF_PREFIX)
    return normalize_indicator_id(raw) or raw.lower()


def is_logframe_enabled(format_rules_json: dict[str, Any] | None) -> bool:
    logframe = (format_rules_json or {}).get("logframe") or {}
    return bool(logframe.get("enabled"))


def resolve_logframe_output_section(
    report_sections_json: list[dict[str, Any]],
) -> tuple[str, str]:
    """Section that owns indicator-sourced output scoring (data-driven)."""
    for section in report_sections_json:
        section_key = section.get("section_key")
        if not section_key:
            continue
        for table in section.get("required_tables") or []:
            if table.get("data_source") == "indicators":
                return str(section_key), str(section.get("label") or section_key)
    return "detailed_output_scoring", "Detailed Output Scoring"


def _is_indicator_data_source(fact: dict[str, Any]) -> bool:
    provenance = fact.get("provenance") or {}
    if provenance.get("cell_ref"):
        return True
    source_label = str(fact.get("source_label") or "").lower()
    return any(
        token in source_label
        for token in (".xlsx", ".xls", "indicator_data", "spreadsheet", "logframe")
    )


def _is_target_facet(fact_key: str) -> bool:
    lower = fact_key.lower()
    return any(
        token in lower
        for token in (
            ".target",
            ".proposal_target",
            "ar1_target",
            ".milestone",
            "_milestone_target",
        )
    )


def _is_actual_facet(fact_key: str) -> bool:
    lower = fact_key.lower()
    if ".target" in lower or "proposal_target" in lower or "ar1_target" in lower:
        return False
    return any(token in lower for token in (".actual", "ar1_actual", "_actual"))


def _is_proposal_target_fact(fact_key: str, fact: dict[str, Any]) -> bool:
    if not _is_target_facet(fact_key):
        return False
    if _is_indicator_data_source(fact):
        return False
    return bool(fact.get("source_document_id"))


def _is_indicator_data_actual_fact(fact_key: str, fact: dict[str, Any]) -> bool:
    if not _is_actual_facet(fact_key):
        return False
    return _is_indicator_data_source(fact)


def derive_missing_logframe_actuals(
    knowledge_bank_json: dict[str, Any],
    *,
    format_rules_json: dict[str, Any] | None,
    report_sections_json: list[dict[str, Any]] | None = None,
) -> list[MissingLogframeActual]:
    """Proposal-sourced targets without indicator-data AR1 actuals."""
    if not is_logframe_enabled(format_rules_json):
        return []

    facts = knowledge_bank_json.get("facts") or {}
    if not isinstance(facts, dict):
        return []

    section_key, section_label = resolve_logframe_output_section(
        report_sections_json or []
    )

    proposal_targets: dict[str, tuple[str, str | None]] = {}
    indicator_data_actuals: set[str] = set()

    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        indicator_id = normalize_indicator_id(str(fact_key))
        if indicator_id is None:
            indicator_id = normalize_indicator_id(str(fact.get("semantic_label") or ""))
        if indicator_id is None:
            continue

        if _is_proposal_target_fact(str(fact_key), fact):
            label = str(fact.get("semantic_label") or indicator_id)
            value = fact.get("value")
            proposal_targets[indicator_id] = (
                label,
                str(value) if value is not None else None,
            )
        if _is_indicator_data_actual_fact(str(fact_key), fact):
            indicator_data_actuals.add(indicator_id)

    missing: list[MissingLogframeActual] = []
    for indicator_id in sorted(proposal_targets):
        if indicator_id in indicator_data_actuals:
            continue
        label, target_value = proposal_targets[indicator_id]
        ref = logframe_row_ref(indicator_id)
        missing.append(
            MissingLogframeActual(
                indicator_id=indicator_id,
                indicator_label=label,
                proposal_target_value=target_value,
                missing_facet="ar1_actual",
                section_key=section_key,
                section_label=section_label,
                required_item_ref=ref,
                item_key=_item_key(section_key, "indicator", ref),
            )
        )
    return missing


def missing_to_template_requirements(
    missing: list[MissingLogframeActual],
) -> list[TemplateRequirement]:
    return [
        TemplateRequirement(
            item_key=entry.item_key,
            section_key=entry.section_key,
            section_label=entry.section_label,
            required_item_type="indicator",
            required_item_ref=entry.required_item_ref,
        )
        for entry in missing
    ]


def _default_question(entry: MissingLogframeActual) -> str:
    display_id = entry.indicator_id.replace("_", ".").upper()
    if display_id.startswith("OP"):
        display_id = display_id.replace("OP", "OP", 1)
    return (
        f"Please provide the Annual Review actual result for {display_id} "
        f"({entry.indicator_label}) and explain any variance from the proposal target."
    )


def _default_rationale(entry: MissingLogframeActual) -> str:
    target_part = (
        f" Proposal target: {entry.proposal_target_value}."
        if entry.proposal_target_value is not None
        else ""
    )
    return (
        f"{entry.indicator_id.upper()} appears in the proposal logframe but no "
        f"indicator-data actual was found in submitted monitoring records."
        f"{target_part}"
    )


def missing_to_gap_items(
    missing: list[MissingLogframeActual],
) -> list[GapComplianceGapItem]:
    return [
        GapComplianceGapItem(
            item_key=entry.item_key,
            section_key=entry.section_key,
            section_label=entry.section_label,
            required_item_type="indicator",
            required_item_ref=entry.required_item_ref,
            severity="required",
            question=_default_question(entry),
            rationale=_default_rationale(entry),
        )
        for entry in missing
    ]


def has_indicator_data_actual_for_id(
    facts: dict[str, Any],
    indicator_id: str,
) -> bool:
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if not _is_indicator_data_actual_fact(str(fact_key), fact):
            continue
        fact_indicator = normalize_indicator_id(str(fact_key))
        if fact_indicator is None:
            fact_indicator = normalize_indicator_id(str(fact.get("semantic_label") or ""))
        if fact_indicator == indicator_id:
            return True
    return False


def is_proposal_target_fact(fact_key: str, fact: dict[str, Any]) -> bool:
    return _is_proposal_target_fact(fact_key, fact)


def is_indicator_data_actual_fact(fact_key: str, fact: dict[str, Any]) -> bool:
    return _is_indicator_data_actual_fact(fact_key, fact)


def logframe_missing_identities(
    missing: list[MissingLogframeActual],
) -> set[tuple[str, str, str]]:
    return {
        (entry.section_key, "indicator", entry.required_item_ref) for entry in missing
    }
