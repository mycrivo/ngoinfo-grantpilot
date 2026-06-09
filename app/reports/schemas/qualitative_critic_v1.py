"""F2 split critic helpers — qualitative LLM output shapes and flag conversion."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.reports.schemas.fact_safety_critic_v1 import (
    CRITIC_AGENT_NAME,
    CriticFlagSeverity,
    FactSafetySpecificResult,
)

QualitativeVerificationPath = Literal["qualitative_llm", "deterministic_numeric", "p1_3_fence"]


class QualitativeCriticLLMOutput(BaseModel):
    specifics: list[FactSafetySpecificResult] = Field(default_factory=list)
    fact_safety_status: Literal["VERIFIED", "FLAGGED"]


def qualitative_flag_from_specific(item: FactSafetySpecificResult) -> dict[str, Any]:
    return {
        "claim_text": item.text,
        "severity": item.severity or "BLOCK",
        "reason": item.reason or "Qualitative specific not supported by scoped citable KB",
        "source_required": True,
        "accepted": False,
        "accepted_at": None,
        "source_ref": item.source_ref,
        "verification_path": "qualitative_llm",
    }


def fence_flag_dict(*, ref: str, reason: str) -> dict[str, Any]:
    return {
        "claim_text": ref,
        "severity": "BLOCK",
        "reason": reason,
        "source_required": True,
        "accepted": False,
        "accepted_at": None,
        "source_ref": ref,
        "verification_path": "p1_3_fence",
    }


__all__ = [
    "CRITIC_AGENT_NAME",
    "QualitativeCriticLLMOutput",
    "qualitative_flag_from_specific",
    "fence_flag_dict",
]
