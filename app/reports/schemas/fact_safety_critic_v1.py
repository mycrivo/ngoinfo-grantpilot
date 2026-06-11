"""F2 fact-safety critic — LLM output and persisted flag shapes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CRITIC_AGENT_NAME = "fact_safety_critic"

FactSafetyStatus = Literal["VERIFIED", "FLAGGED", "UNVERIFIED", "SKIPPED"]
CriticFlagSeverity = Literal["BLOCK", "WARN"]


class FactSafetySpecificResult(BaseModel):
    text: str = Field(min_length=1)
    status: Literal["VERIFIED", "FLAGGED"]
    source_ref: str | None = None
    severity: CriticFlagSeverity | None = None
    reason: str | None = None


class FactSafetyCriticLLMOutput(BaseModel):
    specifics: list[FactSafetySpecificResult] = Field(default_factory=list)
    fact_safety_status: FactSafetyStatus


class FactSafetyCriticTrace(BaseModel):
    model_used: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated: bool | None = None
    cost_usd: float | None = None


class CriticFlagEntry(BaseModel):
    """Persisted shape for content_json sections[].critic_flags[]."""

    claim_text: str
    severity: CriticFlagSeverity
    reason: str
    source_required: bool = True
    accepted: bool = False
    accepted_at: str | None = None


def critic_flag_from_specific(item: FactSafetySpecificResult) -> dict[str, Any]:
    return CriticFlagEntry(
        claim_text=item.text,
        severity=item.severity or "BLOCK",
        reason=item.reason or "Specific not supported by cited knowledge-bank sources",
        source_required=True,
        accepted=False,
        accepted_at=None,
    ).model_dump(mode="json")


def unverified_section_flag(*, reason: str) -> dict[str, Any]:
    return {
        "claim_text": "[section unverified]",
        "severity": "BLOCK",
        "reason": reason,
        "source_required": True,
        "accepted": False,
        "accepted_at": None,
        "source_ref": None,
        "verification_path": "qualitative_llm",
    }
