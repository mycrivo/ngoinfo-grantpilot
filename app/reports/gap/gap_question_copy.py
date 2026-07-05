"""Deterministic Gate 2 gap question copy — readable English, no LLM."""

from __future__ import annotations

import re

from app.reports.gap.logframe_completeness import is_logframe_row_ref
from app.reports.gap.template_requirements import TemplateRequirement

# Natural question clauses for known checklist refs (lowercase; no trailing punctuation).
_INDICATOR_DATA_CLAUSES: dict[str, str] = {
    "what_worked": "what worked",
    "what_did_not_work": "what did not work",
    "unexpected_findings": "what unexpected findings can you share",
    "learning_useful_to_others": "what learning would be useful to others",
    "planned_changes": "what are your planned changes",
    "support_needed": "what support do you need",
    "changes_made": "what changes have you made",
    "budgeted_total": "what was the budgeted total",
    "actual_spend_total": "what was the actual spend total",
    "revenue_cost_variance": "what was the revenue cost variance",
    "capital_cost_variance": "what was the capital cost variance",
    "beneficiary_numbers": "what are the beneficiary numbers",
    "outcome_indicators_where_available": "what outcome indicators can you report",
    "overall_progress": "what was the overall progress",
    "main_results_achieved": "what were the main results achieved",
    "main_issues": "what were the main issues",
    "key_recommendations": "what are the key recommendations",
}

_INDICATOR_NARRATIVE_CLAUSES: dict[str, str] = {
    "community_participation_examples": "please give examples of community participation",
    "partner_or_local_collaboration_examples": (
        "please give examples of partner or local collaboration"
    ),
    "community_feedback": "what community feedback can you share",
    "staff_or_volunteer_feedback": "what staff or volunteer feedback can you share",
    "overall_project_reflection": "please share your overall project reflection",
    "unshared_evidence_or_learning": "please share any evidence or learning not yet covered",
    "unspent_funds_status": "what is the status of any unspent funds",
}

_TABLE_PHRASES: dict[str, str] = {
    "budget_vs_actual": "your budget vs actual table",
    "outcomes_summary": "your outcomes summary table",
    "output_score_table": "your output score table",
}

_BROKEN_DATA_PATTERN = re.compile(
    r"^What is the (what|how|why|when|who)\b",
    re.IGNORECASE,
)
_BROKEN_ARTICLE_STACK = re.compile(r"\bthe the\b", re.IGNORECASE)


def humanize_ref(ref: str) -> str:
    """Readable words from a snake_case checklist ref."""
    return ref.replace("_", " ").strip()


def is_well_formed_gap_question(question: str) -> bool:
    """Heuristic guardrails for generated Gate 2 question copy."""
    text = question.strip()
    if not text:
        return False
    if _BROKEN_DATA_PATTERN.search(text):
        return False
    if _BROKEN_ARTICLE_STACK.search(text):
        return False
    if not text[0].isupper():
        return False
    return True


def _section_prefix(section_label: str) -> str:
    return f"For {section_label},"


def _clause_for_data_indicator(ref: str) -> str:
    if ref in _INDICATOR_DATA_CLAUSES:
        return _INDICATOR_DATA_CLAUSES[ref]

    words = humanize_ref(ref).lower()
    tokens = words.split()
    if tokens and tokens[0] in ("what", "how", "why", "when", "who"):
        return words
    if words.endswith(("numbers", "examples")):
        return f"what are the {words}"
    if words.endswith(("total", "variance", "amount", "count")):
        return f"what was the {words}"
    if words.endswith(("feedback", "findings", "reflection")):
        return f"what {words} can you share"
    return f"please provide the {words}"


def _clause_for_narrative_indicator(ref: str) -> str:
    if ref in _INDICATOR_NARRATIVE_CLAUSES:
        return _INDICATOR_NARRATIVE_CLAUSES[ref]

    words = humanize_ref(ref).lower()
    if words.endswith("examples"):
        topic = words[: -len("examples")].strip(" _") or words
        return f"please give examples of {topic}"
    return f"please describe {words}"


def _table_phrase(ref: str) -> str:
    if ref in _TABLE_PHRASES:
        return _TABLE_PHRASES[ref]
    label = humanize_ref(ref)
    return f"your {label} table"


def build_logframe_indicator_question(required_item_ref: str) -> str:
    """Logframe row ref question (FCDO-style OP1.1 actuals)."""
    indicator_id = required_item_ref.split(":", 1)[-1].replace("_", ".").upper()
    return (
        f"What was the actual result for indicator {indicator_id} "
        "during this reporting period?"
    )


def build_gap_question(requirement: TemplateRequirement) -> str:
    """Build a readable, deterministic Gate 2 question for one checklist requirement."""
    if is_logframe_row_ref(requirement.required_item_ref):
        return build_logframe_indicator_question(requirement.required_item_ref)

    prefix = _section_prefix(requirement.section_label)

    if requirement.required_item_type == "table":
        return f"{prefix} please confirm or provide {_table_phrase(requirement.required_item_ref)}."

    if requirement.requirement_type == "data":
        clause = _clause_for_data_indicator(requirement.required_item_ref)
        return f"{prefix} {clause}?"

    clause = _clause_for_narrative_indicator(requirement.required_item_ref)
    return f"{prefix} {clause}."
