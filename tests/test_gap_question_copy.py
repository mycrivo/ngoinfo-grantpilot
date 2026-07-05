"""Gate 2 deterministic gap question copy — readability regression tests."""

from __future__ import annotations

import pytest

from app.reports.gap.deterministic_gaps import requirement_to_gap_item
from app.reports.gap.gap_question_copy import (
    build_gap_question,
    build_logframe_indicator_question,
    is_well_formed_gap_question,
)
from app.reports.gap.template_requirements import TemplateRequirement

# Before/after anchors from prod report 7cc6412b (NLCF, broken deterministic copy).
NLCF_LEARNING = "What you learned"
NLCF_CHANGES = "How you are changing what you do"
NLCF_SPEND = "What you spent this year"

NLCF_BEFORE_AFTER: list[tuple[str, str, str, str, str, str, str]] = [
    (
        "learning",
        NLCF_LEARNING,
        "indicator",
        "what_worked",
        "data",
        "What is the what worked for What you learned?",
        "For What you learned, what worked?",
    ),
    (
        "learning",
        NLCF_LEARNING,
        "indicator",
        "what_did_not_work",
        "data",
        "What is the what did not work for What you learned?",
        "For What you learned, what did not work?",
    ),
    (
        "learning",
        NLCF_LEARNING,
        "indicator",
        "unexpected_findings",
        "data",
        "What is the unexpected findings for What you learned?",
        "For What you learned, what unexpected findings can you share?",
    ),
    (
        "learning",
        NLCF_LEARNING,
        "indicator",
        "learning_useful_to_others",
        "data",
        "What is the learning useful to others for What you learned?",
        "For What you learned, what learning would be useful to others?",
    ),
    (
        "changes_and_next_steps",
        NLCF_CHANGES,
        "indicator",
        "planned_changes",
        "data",
        "What is the planned changes for How you are changing what you do?",
        "For How you are changing what you do, what are your planned changes?",
    ),
    (
        "changes_and_next_steps",
        NLCF_CHANGES,
        "indicator",
        "support_needed",
        "data",
        "What is the support needed for How you are changing what you do?",
        "For How you are changing what you do, what support do you need?",
    ),
    (
        "spend_summary",
        NLCF_SPEND,
        "indicator",
        "budgeted_total",
        "data",
        "What is the budgeted total for What you spent this year?",
        "For What you spent this year, what was the budgeted total?",
    ),
    (
        "spend_summary",
        NLCF_SPEND,
        "indicator",
        "actual_spend_total",
        "data",
        "What is the actual spend total for What you spent this year?",
        "For What you spent this year, what was the actual spend total?",
    ),
    (
        "spend_summary",
        NLCF_SPEND,
        "indicator",
        "revenue_cost_variance",
        "data",
        "What is the revenue cost variance for What you spent this year?",
        "For What you spent this year, what was the revenue cost variance?",
    ),
    (
        "spend_summary",
        NLCF_SPEND,
        "indicator",
        "capital_cost_variance",
        "data",
        "What is the capital cost variance for What you spent this year?",
        "For What you spent this year, what was the capital cost variance?",
    ),
    (
        "spend_summary",
        NLCF_SPEND,
        "table",
        "budget_vs_actual",
        "data",
        "Please confirm or provide the data for the budget vs actual table in What you spent this year.",
        "For What you spent this year, please confirm or provide your budget vs actual table.",
    ),
]


def _requirement(
    section_key: str,
    section_label: str,
    item_type: str,
    item_ref: str,
    requirement_type: str,
) -> TemplateRequirement:
    return TemplateRequirement(
        item_key=f"{section_key}:{item_type}:{item_ref}",
        section_key=section_key,
        section_label=section_label,
        required_item_type=item_type,  # type: ignore[arg-type]
        required_item_ref=item_ref,
        requirement_type=requirement_type,  # type: ignore[arg-type]
    )


def _legacy_question(
    section_key: str,
    section_label: str,
    item_type: str,
    item_ref: str,
    requirement_type: str,
) -> str:
    label = item_ref.replace("_", " ").strip()
    if item_type == "table":
        return (
            f"Please confirm or provide the data for the {label} table in {section_label}."
        )
    if requirement_type == "data":
        return f"What is the {label} for {section_label}?"
    return f"Please provide information about {label} for {section_label}."


@pytest.mark.parametrize(
    (
        "section_key",
        "section_label",
        "item_type",
        "item_ref",
        "requirement_type",
        "before",
        "after",
    ),
    NLCF_BEFORE_AFTER,
)
def test_nlcf_prod_before_after(
    section_key: str,
    section_label: str,
    item_type: str,
    item_ref: str,
    requirement_type: str,
    before: str,
    after: str,
) -> None:
    requirement = _requirement(
        section_key, section_label, item_type, item_ref, requirement_type
    )
    assert _legacy_question(
        section_key, section_label, item_type, item_ref, requirement_type
    ) == before
    question = build_gap_question(requirement)
    assert question == after
    assert is_well_formed_gap_question(question)


def test_narrative_indicator_question_shape() -> None:
    requirement = _requirement(
        "community_involvement",
        "How you involved people from your community",
        "indicator",
        "community_participation_examples",
        "narrative",
    )
    question = build_gap_question(requirement)
    assert question == (
        "For How you involved people from your community, "
        "please give examples of community participation."
    )
    assert is_well_formed_gap_question(question)


def test_logframe_indicator_question_unchanged() -> None:
    ref = "logframe_row:op1_1"
    assert build_logframe_indicator_question(ref) == (
        "What was the actual result for indicator OP1.1 during this reporting period?"
    )
    requirement = _requirement(
        "difference_made",
        "Results",
        "indicator",
        ref,
        "data",
    )
    assert build_gap_question(requirement) == build_logframe_indicator_question(ref)


def test_requirement_to_gap_item_uses_readable_question() -> None:
    requirement = _requirement(
        "learning", NLCF_LEARNING, "indicator", "what_worked", "data"
    )
    gap = requirement_to_gap_item(requirement)
    assert gap.question == "For What you learned, what worked?"
    assert gap.required_item_ref == "what_worked"
    assert gap.section_label == NLCF_LEARNING


@pytest.mark.parametrize(
    ("section_key", "section_label", "item_type", "item_ref", "requirement_type", "before", "after"),
    NLCF_BEFORE_AFTER,
)
def test_no_legacy_broken_patterns(
    section_key: str,
    section_label: str,
    item_type: str,
    item_ref: str,
    requirement_type: str,
    before: str,
    after: str,
) -> None:
    _ = before
    question = build_gap_question(
        _requirement(section_key, section_label, item_type, item_ref, requirement_type)
    )
    assert "What is the what " not in question
    assert "What is the how " not in question
    assert question == after
