"""Knowledge-bank citability and confirmed views (P1-3 moat fence)."""

from app.reports.knowledge.confirmed_kb import (
    ConfirmedKBView,
    build_confirmed_kb_view,
    count_unverified_excluded,
    effective_verification_status,
    filter_citable_facts,
    filter_citable_gap_answers,
    is_evidence_ref_citable,
    is_fact_citable,
    is_gap_answer_citable,
    non_citable_evidence_refs,
)

__all__ = [
    "ConfirmedKBView",
    "build_confirmed_kb_view",
    "count_unverified_excluded",
    "effective_verification_status",
    "filter_citable_facts",
    "filter_citable_gap_answers",
    "is_evidence_ref_citable",
    "is_fact_citable",
    "is_gap_answer_citable",
    "non_citable_evidence_refs",
]
