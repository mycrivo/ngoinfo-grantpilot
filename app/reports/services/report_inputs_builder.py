"""Assemble report_inputs for per-section synthesis (Stage F1).

Section-scoped visibility (Package A) is template-driven and source-routed:
1. SOURCE PIN — a fact carrying a funder source-declared section (``source_section``)
   is visible ONLY to the section that source assigned it to (no cross-section bleed).
2. DECLARED-NEEDS FALLBACK — a fact with no/unknown source signal is visible to a
   section per what the section declares (``fact_namespaces`` + ``required_tables``
   data sources + ``required_indicators`` tokens), over a shared programme floor
   (grant / reporting / objectives), matched by NAMESPACE ROOT so underscore roots
   like ``grant_reference`` match alongside dotted ``grant.x``.
The archetype map is a derivation fallback, not the source of truth.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.proposal import Proposal
from app.reports.gap.gap_answer import GAP_ANSWER_DISPOSITION_ANSWERED
from app.reports.gap.requirement_satisfaction import evaluate_requirement_satisfaction
from app.reports.gap.template_requirements import enumerate_template_requirements
from app.reports.knowledge.confirmed_kb import (
    filter_citable_facts,
    filter_citable_gap_answers,
)
from app.reports.models.donor_report import DonorReport
from app.reports.models.funder_report_template import FunderReportTemplate
from app.services.profile_service import get_profile

logger = logging.getLogger("reports.services.report_inputs_builder")

# Programme-level fact namespace ROOTS any section may reference in narrative.
# Root matching (not dotted startswith) so grant_reference / reporting_period.* match.
_SHARED_FACT_ROOTS: frozenset[str] = frozenset({"grant", "reporting", "objectives"})

# Archetype-driven namespace roots — FALLBACK only (used when a section declares no
# explicit fact_namespaces). Template data is the source of truth; see _fact_namespace_patterns.
_ARCHETYPE_FACT_ROOTS: dict[str, tuple[str, ...]] = {
    "ARCH_EXECUTIVE_REVIEW_SUMMARY": ("indicators", "financials"),
    "ARCH_PERFORMANCE_CONCLUSIONS": ("indicators",),
    "ARCH_OUTPUT_SCORING_TABLE": ("indicators", "financials"),
    "ARCH_EVIDENCE_AND_EVALUATION_REVIEW": ("indicators",),
    "ARCH_RISK_ASSUMPTIONS_AND_CONTROLS": ("indicators", "financials"),
    "ARCH_VALUE_FOR_MONEY_4E": ("indicators", "financials"),
    "ARCH_DELIVERY_COMMERCIAL_FINANCIAL_REVIEW": ("indicators", "financials"),
    "ARCH_RECOMMENDATIONS_ACTION_PLAN": ("indicators",),
}

_TABLE_DATA_SOURCE_ROOTS: dict[str, tuple[str, ...]] = {
    "indicators": ("indicators",),
    "financials": ("financials",),
}

_NAMESPACE_ROOT_RE = re.compile(r"^[a-z]+")

_LINKED_PROPOSAL_SUMMARY_MAX_CHARS = 4000


def _namespace_root(key: str) -> str:
    match = _NAMESPACE_ROOT_RE.match(str(key).lower())
    return match.group(0) if match else ""


def _norm_label(label: str) -> str:
    return re.sub(r"\s+", " ", str(label or "").strip().lower())


def _build_section_label_map(
    report_sections: list[dict[str, Any]] | None,
    section: dict[str, Any],
) -> dict[str, str]:
    """Normalized source-section label -> engine section_key, across the template.

    Falls back to the single section when the full template is unavailable (legacy
    callers); pinning to this section still works, cross-section exclusion does not.
    """
    sections = report_sections if report_sections is not None else [section]
    label_map: dict[str, str] = {}
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        skey = str(sec.get("section_key") or "")
        if not skey:
            continue
        for label in sec.get("source_section_labels") or []:
            norm = _norm_label(label)
            if norm:
                label_map[norm] = skey
    return label_map


def _fact_namespace_patterns(section: dict[str, Any]) -> set[str]:
    """Declared-needs namespace patterns (roots or glob sub-paths) for one section.

    Template data is the source of truth: explicit fact_namespaces + required_tables
    data sources. The archetype map is used ONLY as a fallback when no explicit
    fact_namespaces are declared.
    """
    patterns: set[str] = set()
    declared = section.get("fact_namespaces") or []
    for ns in declared:
        text = str(ns).strip()
        if text:
            patterns.add(text)
    for table in section.get("required_tables") or []:
        if not isinstance(table, dict):
            continue
        data_source = str(table.get("data_source") or "")
        patterns.update(_TABLE_DATA_SOURCE_ROOTS.get(data_source, ()))
    # Archetype roots are a FALLBACK only for legacy sections that declare no
    # fact_namespaces key at all (e.g. FCDO). A section that declares the key (even
    # empty) opts into precise template-driven routing with no archetype widening.
    if "fact_namespaces" not in section:
        archetype = str(section.get("archetype") or "")
        patterns.update(_ARCHETYPE_FACT_ROOTS.get(archetype, ()))
    return patterns


def _key_matches_patterns(key: str, patterns: set[str]) -> bool:
    root = _namespace_root(key)
    for pattern in patterns:
        if "." in pattern or "*" in pattern:
            if fnmatch.fnmatch(key, pattern):
                return True
        elif root == pattern:
            return True
    return False


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


def _linked_proposal_summary(db: Session, report: DonorReport) -> str | None:
    """Truncate winning-proposal prose for synthesis context (background only)."""
    if not report.linked_proposal_id:
        return None
    proposal = db.get(Proposal, report.linked_proposal_id)
    if proposal is None:
        return None
    parts: list[str] = []
    for section in (proposal.content_json or {}).get("sections") or []:
        if not isinstance(section, dict):
            continue
        label = str(section.get("label") or section.get("section_key") or "").strip()
        content = section.get("content") or {}
        text = str(content.get("text") or "").strip() if isinstance(content, dict) else ""
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    if not parts:
        return None
    summary = "\n\n".join(parts)
    if len(summary) > _LINKED_PROPOSAL_SUMMARY_MAX_CHARS:
        return summary[: _LINKED_PROPOSAL_SUMMARY_MAX_CHARS].rstrip() + "…"
    return summary


def _terminology_resolved(template: FunderReportTemplate) -> dict[str, str]:
    mapping = (template.terminology_map_json or {}).get("canonical_to_funder") or {}
    if not isinstance(mapping, dict):
        return {}
    return {str(k): str(v) for k, v in mapping.items() if k and v}


def _narrative_constraints(template: FunderReportTemplate) -> dict[str, Any]:
    rules = template.format_rules_json or {}
    constraints = rules.get("narrative_constraints") or {}
    return constraints if isinstance(constraints, dict) else {}


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


def _indicator_match_tokens(section: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for indicator in section.get("required_indicators") or []:
        for part in str(indicator).lower().replace("-", "_").split("_"):
            if len(part) >= 4:
                tokens.add(part)
    return tokens


def _fact_source_section(value: Any) -> str | None:
    if isinstance(value, dict):
        src = value.get("source_section")
        return str(src) if src else None
    return None


def subset_facts_for_section(
    facts: dict[str, Any],
    section: dict[str, Any],
    *,
    report_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the fact subset visible to one F1 section call.

    Source pin first (a source-declared fact is visible ONLY to its assigned section),
    then a template-driven declared-needs floor for facts with no/unknown source. A
    source label that matches no declared section fails safe to declared-needs (never
    dropped, never misrouted) and is surfaced for observability.
    """
    if not facts:
        return {}
    section_key = str(section.get("section_key") or "")
    label_map = _build_section_label_map(report_sections, section)
    own_labels = {_norm_label(lbl) for lbl in (section.get("source_section_labels") or [])}
    patterns = _fact_namespace_patterns(section)
    # Legacy indicator-token matching is a fallback for sections that declare NO
    # fact_namespaces key (e.g. FCDO archetype-driven). Sections that declare the key
    # (even empty) use precise patterns only — this excludes the accidental broad
    # "indicators" token bleed and the "work"->"workers" financial mismatch.
    tokens = (
        _indicator_match_tokens(section)
        if "fact_namespaces" not in section
        else set()
    )
    unmatched_labels: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in facts.items():
        source_section = _fact_source_section(value)
        if source_section:
            norm = _norm_label(source_section)
            if norm in own_labels:
                out[key] = value  # source pin: this section owns the fact
                continue
            resolved = label_map.get(norm)
            if resolved is not None and resolved != section_key:
                continue  # pinned to another declared section — never bleed here
            # Unknown label: fail safe to declared-needs (surfaced below).
            unmatched_labels.add(source_section)
        root = _namespace_root(key)
        if root in _SHARED_FACT_ROOTS or _key_matches_patterns(key, patterns):
            out[key] = value
            continue
        if tokens and any(token in key.lower() for token in tokens):
            out[key] = value
    if unmatched_labels:
        logger.warning(
            "subset_facts_for_section unmatched source_section labels=%s section=%s "
            "-> declared-needs fallback (check template source_section_labels)",
            sorted(unmatched_labels),
            section_key or "(unknown)",
        )
    return out


def build_knowledge_bank_inputs_for_section(
    knowledge_bank_json: dict[str, Any],
    section: dict[str, Any],
    *,
    report_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Section-scoped KB inputs: citable trimmed facts, all citable answered gaps."""
    kb = knowledge_bank_json or {}
    citable_facts = filter_citable_facts(kb)
    return {
        "facts": subset_facts_for_section(
            citable_facts, section, report_sections=report_sections
        ),
        "gap_answers": filter_citable_gap_answers(kb),
        "conflicts_resolved": _resolved_conflicts(kb.get("conflicts") or []),
        "gate1_confirmed_at": kb.get("gate1_confirmed_at"),
        "gate2_confirmed_at": kb.get("gate2_confirmed_at"),
    }


def section_has_synthesizable_inputs(
    knowledge_bank_json: dict[str, Any],
    section: dict[str, Any],
    *,
    report_context: dict[str, Any] | None = None,
    report_sections: list[dict[str, Any]] | None = None,
) -> bool:
    """True when at least one NGO checklist requirement for this section is satisfied in KB."""
    kb = knowledge_bank_json or {}
    ctx = report_context or {"report_type": "annual"}
    facts = kb.get("facts") or {}
    gap_answers = kb.get("gap_answers") or {}
    gate1_at = kb.get("gate1_confirmed_at")
    requirements = enumerate_template_requirements([section], report_context=ctx)
    for requirement in requirements:
        if requirement.required_item_type == "section":
            continue
        result = evaluate_requirement_satisfaction(
            requirement,
            facts=facts,
            gap_answers=gap_answers,
            gate1_confirmed_at=gate1_at,
            purpose="synthesis",
        )
        if result.satisfied:
            return True
    # The shared programme floor (grant / reporting / objectives) is CONTEXT available to
    # every section, not synthesizable content on its own. A section is synthesizable only
    # when it can see at least one SECTION-SPECIFIC fact (source-pinned or declared-needs),
    # so a section seeing only the shared floor is correctly treated as insufficient.
    section_facts = build_knowledge_bank_inputs_for_section(
        kb, section, report_sections=report_sections
    )["facts"]
    if any(_namespace_root(key) not in _SHARED_FACT_ROOTS for key in section_facts):
        return True
    return False


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
        report_sections=template.report_sections_json or [],
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
            "linked_proposal_summary": _linked_proposal_summary(db, report),
            "terminology_resolved": _terminology_resolved(template),
            "narrative_constraints": _narrative_constraints(template),
        },
    }
