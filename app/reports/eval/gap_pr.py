"""Gap precision/recall — identity keyed by section + type + ref (content only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GapPRReport:
    expected_identities: set[tuple[str, str, str]] = field(default_factory=set)
    actual_identities: set[tuple[str, str, str]] = field(default_factory=set)
    missing: set[tuple[str, str, str]] = field(default_factory=set)
    extra: set[tuple[str, str, str]] = field(default_factory=set)

    @property
    def precision(self) -> float:
        if not self.actual_identities:
            return 1.0 if not self.extra else 0.0
        return len(self.actual_identities - self.extra) / len(self.actual_identities)

    @property
    def recall(self) -> float:
        if not self.expected_identities:
            return 1.0
        return len(self.expected_identities - self.missing) / len(self.expected_identities)

    @property
    def passed(self) -> bool:
        return not self.missing and not self.extra

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "gap.expected_count": len(self.expected_identities),
            "gap.actual_count": len(self.actual_identities),
            "gap.missing_count": len(self.missing),
            "gap.extra_count": len(self.extra),
            "gap.precision": round(self.precision, 4),
            "gap.recall": round(self.recall, 4),
            "gap.passed": self.passed,
        }


def gap_identity(gap: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(gap.get("section_key") or ""),
        str(gap.get("required_item_type") or ""),
        str(gap.get("required_item_ref") or ""),
    )


def evaluate_gap_pr(
    gap_analysis: dict[str, Any],
    *,
    expected_identities: set[tuple[str, str, str]],
) -> GapPRReport:
    gaps = gap_analysis.get("gaps") or []
    actual = {
        gap_identity(g)
        for g in gaps
        if isinstance(g, dict)
    }
    missing = expected_identities - actual
    extra = actual - expected_identities
    return GapPRReport(
        expected_identities=expected_identities,
        actual_identities=actual,
        missing=missing,
        extra=extra,
    )
