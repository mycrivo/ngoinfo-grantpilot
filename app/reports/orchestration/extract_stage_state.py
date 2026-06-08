"""Extract-stage run state for Table C consecutive-failure fail-closed (P2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.reports.orchestration.systemic_extraction_failure import (
    _PER_DOCUMENT_DEGRADE_STOP_CODES,
    is_systemic_extraction_failure,
)

ExtractStopAction = Literal["hard_fail", "degrade"]


@dataclass
class ExtractStageRunState:
    """Tracks successes and consecutive ambiguous agent stops within one extract stage."""

    any_extract_success: bool = False
    consecutive_ambiguous_agent_stops: int = 0

    def record_extract_success(self) -> None:
        self.any_extract_success = True
        self.consecutive_ambiguous_agent_stops = 0

    def record_ambiguous_agent_stop_degraded(self) -> None:
        self.consecutive_ambiguous_agent_stops += 1

    def resolve_agent_stop_action(self, *, code: str, message: str) -> ExtractStopAction:
        """Table B + Table C via shared systemic classifier."""
        if is_systemic_extraction_failure(code=code, message=message):
            return "hard_fail"
        if code in _PER_DOCUMENT_DEGRADE_STOP_CODES:
            return "degrade"
        if code == "STOP_AGENT_ERROR":
            if self.any_extract_success:
                return "degrade"
            if self.consecutive_ambiguous_agent_stops >= 1:
                return "hard_fail"
            return "degrade"
        return "hard_fail"
