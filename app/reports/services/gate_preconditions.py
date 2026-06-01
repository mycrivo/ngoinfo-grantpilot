"""Pipeline stage preconditions — server-enforced gates (no model calls)."""

from __future__ import annotations

from typing import Any

from app.core.errors import DomainError


def require_gate1_confirmed(knowledge_bank_json: dict | None) -> None:
    """E3 gap-check must not run until Gate 1 human confirmation is stamped."""
    kb = knowledge_bank_json or {}
    if not kb.get("gate1_confirmed_at"):
        raise DomainError(
            error_code="GATE1_NOT_CONFIRMED",
            message="Gate 1 human confirmation is required before gap-check",
            status_code=409,
        )


def require_gap_analysis(gap_analysis_json: dict | None) -> list[dict[str, Any]]:
    """Gate 2 requires E3 gap/compliance output before intake."""
    ga = gap_analysis_json or {}
    if not ga:
        raise DomainError(
            error_code="GAP_ANALYSIS_MISSING",
            message="Gap analysis must be completed before Gate 2 gap-answer intake",
            status_code=409,
        )
    if not ga.get("gap_agent") and not ga.get("analyzed_at"):
        raise DomainError(
            error_code="GAP_ANALYSIS_MISSING",
            message="Gap analysis must be completed before Gate 2 gap-answer intake",
            status_code=409,
        )
    gaps = ga.get("gaps")
    if gaps is None:
        raise DomainError(
            error_code="GAP_ANALYSIS_MISSING",
            message="Gap analysis is missing the gaps list",
            status_code=409,
        )
    if not isinstance(gaps, list):
        raise DomainError(
            error_code="GAP_ANALYSIS_INVALID",
            message="Gap analysis gaps must be a list",
            status_code=422,
        )
    return [g for g in gaps if isinstance(g, dict)]


def require_gate2_confirmed(knowledge_bank_json: dict | None) -> None:
    """F1 synthesis must not run until Gate 2 gap-answer intake is complete."""
    kb = knowledge_bank_json or {}
    if not kb.get("gate2_confirmed_at"):
        raise DomainError(
            error_code="GATE2_NOT_CONFIRMED",
            message="Gate 2 gap-answer confirmation is required before synthesis",
            status_code=409,
        )


def require_gate3_confirmed(knowledge_bank_json: dict | None) -> None:
    """Stage H export must not run until Gate 3 human review is complete."""
    kb = knowledge_bank_json or {}
    if not kb.get("gate3_confirmed_at"):
        raise DomainError(
            error_code="GATE3_NOT_CONFIRMED",
            message="Gate 3 human confirmation is required before export",
            status_code=409,
        )
