"""Proposal extraction schema v1.0.0 — stable contract for D2 and downstream E1/E3/F1.

Maps to uploaded_documents.extracted_json.structured when classification=proposal.
Aligned with FCDO logframe columns: indicator, baseline, milestone, target.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

PROPOSAL_EXTRACTION_SCHEMA_VERSION = "1.0.0"

LogframeLevel = Literal["impact", "outcome", "output"]
ExtractionItemStatus = Literal["extracted", "failed", "skipped"]
ExtractionOutcome = Literal["complete", "partial", "failed", "degraded", "unreadable"]


class SourceProvenance(BaseModel):
    excerpt: str = Field(min_length=1)
    section_label: str | None = None
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None


class TargetValue(BaseModel):
    """Numeric or textual target from the proposal only — never inferred."""

    value: str | float | int | None = None
    unit: str | None = None
    absent: bool = False

    @model_validator(mode="after")
    def absent_implies_no_value(self) -> TargetValue:
        if self.absent and self.value is not None:
            raise ValueError("target.absent=true requires value=null")
        return self


class BaselineMilestoneEndline(BaseModel):
    baseline: str | float | int | None = None
    milestone: str | float | int | None = None
    endline_target: str | float | int | None = None


class ExtractedObjective(BaseModel):
    objective_key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    level: LogframeLevel
    status: ExtractionItemStatus = "extracted"
    provenance: SourceProvenance
    error_message: str | None = None


class ExtractedActivity(BaseModel):
    activity_key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: ExtractionItemStatus = "extracted"
    provenance: SourceProvenance
    linked_objective_keys: list[str] = Field(default_factory=list)
    error_message: str | None = None


class ExtractedIndicator(BaseModel):
    indicator_key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    level: LogframeLevel | None = None
    baseline: str | float | int | None = None
    milestone: str | float | int | None = None
    target: TargetValue
    status: ExtractionItemStatus = "extracted"
    provenance: SourceProvenance
    error_message: str | None = None


class ProposalExtractionSummary(BaseModel):
    total: int = 0
    succeeded: int = 0
    failed: int = 0


class ProposalExtractionOutput(BaseModel):
    schema_version: str = PROPOSAL_EXTRACTION_SCHEMA_VERSION
    objectives: list[ExtractedObjective] = Field(default_factory=list)
    activities: list[ExtractedActivity] = Field(default_factory=list)
    indicators: list[ExtractedIndicator] = Field(default_factory=list)
    extraction_outcome: ExtractionOutcome = "complete"
    summary: ProposalExtractionSummary = Field(default_factory=ProposalExtractionSummary)


class ProposalAgentTrace(BaseModel):
    model_used: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated: bool | None = None
    cost_usd: float | None = None
    max_turns: int | None = None
    content_hash: str | None = None
    attempt_count: int | None = None
    degraded_code: str | None = None
    unreadable_code: str | None = None


class ProposalExtractedEnvelope(BaseModel):
    """Shape persisted to uploaded_documents.extracted_json."""

    extractor_agent: str = "proposal_extractor"
    extracted_at: datetime | None = None
    raw_text_ref: str | None = None
    structured: ProposalExtractionOutput
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    error: str | None = None
    agent_trace: ProposalAgentTrace | None = None
