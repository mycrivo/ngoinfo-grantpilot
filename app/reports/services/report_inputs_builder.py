"""Assemble report_inputs for per-section synthesis (Stage F1)."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.reports.gap.gap_answer import GAP_ANSWER_DISPOSITION_ANSWERED
from app.reports.knowledge.confirmed_kb import (
    filter_citable_facts,
    filter_citable_gap_answers,
)
from app.reports.models.donor_report import DonorReport
from app.reports.models.funder_report_template import FunderReportTemplate
from app.services.profile_service import get_profile

# Programme-level fact namespaces any section may reference in narrative.
_SHARED_FACT_PREFIXES: tuple[str, ...] = ("grant.", "reporting.", "objectives.")

# Generous archetype-driven fact namespaces (template report_sections_json[].archetype).
_ARCHETYPE_FACT_PREFIXES: dict[str, tuple[str, ...]] = {
    "ARCH_EXECUTIVE_REVIEW_SUMMARY": ("indicators.", "financials."),
    "ARCH_PERFORMANCE_CONCLUSIONS": ("indicators.",),
    "ARCH_OUTPUT_SCORING_TABLE": ("indicators.", "financials."),
    "ARCH_EVIDENCE_AND_EVALUATION_REVIEW": ("indicators.",),
    "ARCH_RISK_ASSUMPTIONS_AND_CONTROLS": ("indicators.", "financials."),
    "ARCH_VALUE_FOR_MONEY_4E": ("indicators.", "financials."),
    "ARCH_DELIVERY_COMMERCIAL_FINANCIAL_REVIEW": ("indicators.", "financials."),
    "ARCH_RECOMMENDATIONS_ACTION_PLAN": ("indicators.",),
}

_TABLE_DATA_SOURCE_PREFIXES: dict[str, tuple[str, ...]] = {
    "indicators": ("indicators.",),
    "financials": ("financials.",),
}


def _answered_gap_answers(gap_answers: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, entry in (gap_answers or {}).items():
        if isinstance(entry, dict) and entry.get("disposition") == GAP_ANSWER_DISPOSITION_ANSWERED:
            out[key] = entry
    return out


def _resolved_conflicts(conflicts: list[Any]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for item in conflicts or []:
        if isinstance(item, dict) and item.get("resolved_value") is not None:
            resolved.append(item)
    return resolved


def _format_period_label(start: date | None, end: date | None) -> str | None:
    if start is None or end is None:
        return None
    return f"{start.isoformat()} to {end.isoformat()}"


def _ngo_payload(db: Session, user_id) -> dict[str, Any]:
    try:
        profile = get_profile(db, user_id)
    except NotFoundError:
        return {}
    except Exception:
        return {}
    return {
        "organization_name": profile.organization_name,
        "mission_statement": profile.mission_statement,
        "focus_sectors": profile.focus_sectors or [],
        "geographic_areas_of_work": profile.geographic_areas_of_work or [],
        "target_groups": profile.target_groups or [],
        "past_projects": profile.past_projects or [],
    }


def build_knowledge_bank_inputs(knowledge_bank_json: dict[str, Any]) -> dict[str, Any]:
    kb = knowledge_bank_json or {}
    return {
        "facts": filter_citable_facts(kb),
        "gap_answers": filter_citable_gap_answers(kb),
        "conflicts_resolved": _resolved_conflicts(kb.get("conflicts") or []),
        "gate1_confirmed_at": kb.get("gate1_confirmed_at"),
        "gate2_confirmed_at": kb.get("gate2_confirmed_at"),
    }


def _fact_prefixes_for_section(section: dict[str, Any]) -> set[str]:
    prefixes = set(_SHARED_FACT_PREFIXES)
    archetype = str(section.get("archetype") or "")
    prefixes.update(_ARCHETYPE_FACT_PREFIXES.get(archetype, ()))
    for table in section.get("required_tables") or []:
        if not isinstance(table, dict):
            continue
        data_source = str(table.get("data_source") or "")
        prefixes.update(_TABLE_DATA_SOURCE_PREFIXES.get(data_source, ()))
    return prefixes


def _indicator_match_tokens(section: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for indicator in section.get("required_indicators") or []:
        for part in str(indicator).lower().replace("-", "_").split("_"):
            if len(part) >= 4:
                tokens.add(part)
    return tokens


def subset_facts_for_section(
    facts: dict[str, Any],
    section: dict[str, Any],
) -> dict[str, Any]:
    """Return the fact subset for one F1 section call — generous, template-driven trim."""
    if not facts:
        return {}
    prefixes = _fact_prefixes_for_section(section)
    tokens = _indicator_match_tokens(section)
    out: dict[str, Any] = {}
    for key, value in facts.items():
        if any(key.startswith(prefix) for prefix in prefixes):
            out[key] = value
            continue
        if tokens and any(token in key.lower() for token in tokens):
            out[key] = value
    return out


def build_knowledge_bank_inputs_for_section(
    knowledge_bank_json: dict[str, Any],
    section: dict[str, Any],
) -> dict[str, Any]:
    """Section-scoped KB inputs: citable trimmed facts, all citable answered gaps."""
    kb = knowledge_bank_json or {}
    citable_facts = filter_citable_facts(kb)
    return {
        "facts": subset_facts_for_section(citable_facts, section),
        "gap_answers": filter_citable_gap_answers(kb),
        "conflicts_resolved": _resolved_conflicts(kb.get("conflicts") or []),
        "gate1_confirmed_at": kb.get("gate1_confirmed_at"),
        "gate2_confirmed_at": kb.get("gate2_confirmed_at"),
    }


def build_report_inputs_for_section(
    db: Session,
    *,
    report: DonorReport,
    template: FunderReportTemplate,
    section: dict[str, Any],
) -> dict[str, Any]:
    """Build report_inputs for one synthesis invocation."""
    kb_inputs = build_knowledge_bank_inputs_for_section(
        report.knowledge_bank_json or {},
        section,
    )
    return {
        "ngo": _ngo_payload(db, report.user_id),
        "template": {
            "funder_name": template.funder_name,
            "template_name": template.template_name,
            "format_rules_json": template.format_rules_json or {},
            "terminology_map_json": template.terminology_map_json or {},
        },
        "report": {
            "report_id": str(report.id),
            "reporting_period_start": (
                report.reporting_period_start.isoformat()
                if report.reporting_period_start
                else None
            ),
            "reporting_period_end": (
                report.reporting_period_end.isoformat()
                if report.reporting_period_end
                else None
            ),
            "status": report.status,
        },
        "knowledge_bank": kb_inputs,
        "section": section,
        "derived": {
            "reporting_period_label": _format_period_label(
                report.reporting_period_start,
                report.reporting_period_end,
            ),
            "funder_display_name": f"{template.funder_name} — {template.template_name}",
        },
    }
