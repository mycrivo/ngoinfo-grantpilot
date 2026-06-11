"""Grant-terms extraction schema v1.0.0 — award letter / MoU only.

Maps to uploaded_documents.extracted_json.structured when classification is
grant_letter or mou. Mirrors D2 envelope conventions; does not touch donor_reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

GRANT_TERMS_EXTRACTION_SCHEMA_VERSION = "1.0.0"

ExtractionOutcome = Literal["complete", "partial", "failed", "degraded", "unreadable"]


class SourceProvenance(BaseModel):
    excerpt: str = Field(min_length=1)
    section_label: str | None = None
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None


class StatedValue(BaseModel):
    raw: str = Field(min_length=1)
    normalized: str | None = None
    normalization_ambiguous: bool = False
    provenance: SourceProvenance


class GrantTermField(BaseModel):
    absent: bool = False
    raw: str | None = None
    normalized: str | None = None
    normalization_ambiguous: bool = False
    provenance: SourceProvenance | None = None
    multi_value: bool = False
    stated_values: list[StatedValue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_absent_and_multi(self) -> GrantTermField:
        if self.absent:
            if self.raw is not None or self.normalized is not None:
                raise ValueError("absent=true requires raw=null and normalized=null")
            if self.multi_value or self.stated_values:
                raise ValueError("absent=true cannot have stated_values")
            return self
        if self.multi_value:
            if len(self.stated_values) < 2:
                raise ValueError("multi_value=true requires at least two stated_values")
        return self


class BudgetTranche(BaseModel):
    raw: str = Field(min_length=1)
    normalized: str | None = None
    normalization_ambiguous: bool = False
    provenance: SourceProvenance


class AwardBudgetTerms(BaseModel):
    amount: GrantTermField
    currency: GrantTermField
    tranches: list[BudgetTranche] = Field(default_factory=list)


class DateRangeTerms(BaseModel):
    start: GrantTermField
    end: GrantTermField


class ReportingObligation(BaseModel):
    report_type: str = Field(min_length=1)
    frequency: str | None = None
    raw: str = Field(min_length=1)
    provenance: SourceProvenance


class GrantTermsExtractionSummary(BaseModel):
    total_fields: int = 0
    present_fields: int = 0
    absent_fields: int = 0
    multi_value_fields: int = 0


class GrantTermsExtractionOutput(BaseModel):
    schema_version: str = GRANT_TERMS_EXTRACTION_SCHEMA_VERSION
    funder: GrantTermField
    grant_reference: GrantTermField
    award_budget: AwardBudgetTerms
    grant_period: DateRangeTerms
    reporting_period: DateRangeTerms
    reporting_obligations: list[ReportingObligation] = Field(default_factory=list)
    reporting_deadlines: list[GrantTermField] = Field(default_factory=list)
    extraction_outcome: ExtractionOutcome = "complete"
    summary: GrantTermsExtractionSummary = Field(
        default_factory=GrantTermsExtractionSummary
    )


class GrantTermsAgentTrace(BaseModel):
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


class GrantTermsExtractedEnvelope(BaseModel):
    """Shape persisted to uploaded_documents.extracted_json."""

    extractor_agent: str = "grant_terms_extractor"
    extracted_at: datetime | None = None
    raw_text_ref: str | None = None
    structured: GrantTermsExtractionOutput
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    error: str | None = None
    agent_trace: GrantTermsAgentTrace | None = None
