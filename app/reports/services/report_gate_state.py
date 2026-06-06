"""Derive human-gate lifecycle state for report list/detail responses."""

from __future__ import annotations

from app.reports.models.donor_report import DonorReport


def compute_current_gate(report: DonorReport) -> str:
    kb = report.knowledge_bank_json or {}
    ga = report.gap_analysis_json or {}

    if kb.get("gate3_confirmed_at"):
        return "none"
    if kb.get("gate2_confirmed_at"):
        return "gate3"
    if kb.get("gate1_confirmed_at"):
        if ga.get("gaps") is not None or ga.get("analyzed_at") or ga.get("gap_agent"):
            return "gate2"
        return "none"
    if kb.get("facts") or kb.get("reconciliation_outcome") or kb.get("reconciled_at"):
        return "gate1"
    return "none"
