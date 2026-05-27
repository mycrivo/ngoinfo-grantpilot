"""Gate 2 gap_answers resolution — answer-or-skip with human provenance."""

from __future__ import annotations

from typing import Any

HUMAN_GAP_ANSWER_SOURCE = "human_confirmed_gap_answer"
GAP_ANSWER_DISPOSITION_ANSWERED = "answered"
GAP_ANSWER_DISPOSITION_SKIPPED = "skipped"
SKIP_REASONS = frozenset({"not_applicable", "cannot_provide"})


def is_gap_answer_resolved(entry: Any) -> bool:
    """True when the human answered with provenance or explicitly skipped."""
    if not isinstance(entry, dict):
        return False
    disposition = entry.get("disposition")
    if disposition == GAP_ANSWER_DISPOSITION_SKIPPED:
        return entry.get("skip_reason") in SKIP_REASONS
    if disposition == GAP_ANSWER_DISPOSITION_ANSWERED:
        text = entry.get("answer_text")
        if not text or not str(text).strip():
            return False
        provenance = entry.get("provenance")
        if not isinstance(provenance, dict):
            return False
        return provenance.get("source") == HUMAN_GAP_ANSWER_SOURCE and bool(
            str(provenance.get("excerpt") or "").strip()
        )
    if entry.get("answer_text") and str(entry.get("answer_text")).strip():
        return False
    return False
