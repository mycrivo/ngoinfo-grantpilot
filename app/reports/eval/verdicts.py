"""Assertion verdict vocabulary for the P0 five-layer harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssertionClass(str, Enum):
    INVARIANT = "INVARIANT"
    BASELINED = "BASELINED"
    ADVISORY = "ADVISORY"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PASS_BY_STARVATION = "PASS-BY-STARVATION"
    REVIEW_REQUIRED = "REVIEW-REQUIRED"
    ADVISORY = "ADVISORY"
    NOT_APPLICABLE = "NOT-APPLICABLE"


@dataclass
class AssertionResult:
    assertion_id: str
    layer: int
    name: str
    assertion_class: AssertionClass
    verdict: Verdict
    detail: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def counts_as_demonstrated_safety(self) -> bool:
        """PASS-BY-STARVATION is excluded from demonstrated safety properties (D-067)."""
        return self.verdict == Verdict.PASS and self.assertion_class == AssertionClass.INVARIANT

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "layer": self.layer,
            "name": self.name,
            "class": self.assertion_class.value,
            "verdict": self.verdict.value,
            "detail": self.detail,
            "metrics": self.metrics,
        }
