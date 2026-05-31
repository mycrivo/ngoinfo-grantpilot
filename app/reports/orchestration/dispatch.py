"""Uniform dispatch wrapper for orchestrator agent stages."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, TypeVar

from app.reports.agents.classifier import ClassifierError
from app.reports.agents.gap_compliance_agent import GapComplianceAgentError
from app.reports.agents.grant_terms_extractor import GrantTermsExtractorError
from app.reports.agents.indicator_data_extractor import IndicatorDataExtractorError
from app.reports.agents.knowledge_bank_reconciler import KnowledgeBankReconcilerError
from app.reports.agents.proposal_extractor import ProposalExtractorError

logger = logging.getLogger("reports.orchestration.dispatch")

T = TypeVar("T")

_STOP_ERRORS = (
    ClassifierError,
    GapComplianceAgentError,
    ProposalExtractorError,
    GrantTermsExtractorError,
    IndicatorDataExtractorError,
    KnowledgeBankReconcilerError,
)


class StageFailure(Exception):
    """Hard stage failure — orchestrator marks job failed."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message


@dataclass(frozen=True)
class DispatchOutcome:
    """Normalized agent result for the orchestrator."""

    result: Any
    degraded: bool = False


def is_degraded_result(result: Any) -> bool:
    envelope = getattr(result, "envelope", None)
    if envelope is None:
        return False
    structured = getattr(envelope, "structured", None)
    if structured is None:
        return False
    extraction_outcome = getattr(structured, "extraction_outcome", None)
    if extraction_outcome == "degraded":
        return True
    reconciliation_outcome = getattr(structured, "reconciliation_outcome", None)
    return reconciliation_outcome == "degraded"


async def dispatch_stage(
    coro: Any,
    *,
    stage: str,
    per_call_timeout_seconds: float | None = None,
) -> DispatchOutcome:
    """Run one agent call; normalize raises, timeouts, and degraded returns."""
    try:
        if per_call_timeout_seconds is not None:
            result = await asyncio.wait_for(coro, timeout=per_call_timeout_seconds)
        else:
            result = await coro
    except asyncio.TimeoutError as exc:
        raise StageFailure(
            stage,
            f"{stage} agent call exceeded timeout",
        ) from exc
    except _STOP_ERRORS as exc:
        raise StageFailure(stage, exc.message) from exc
    except StageFailure:
        raise
    except Exception as exc:
        raise StageFailure(stage, str(exc)) from exc

    degraded = is_degraded_result(result)
    if degraded:
        logger.warning("%s returned degraded envelope — walk continues", stage)
    return DispatchOutcome(result=result, degraded=degraded)
