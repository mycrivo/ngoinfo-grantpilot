"""Indicator-data extraction schema v1.0.0 — spreadsheets / CSV only.

Maps to uploaded_documents.extracted_json.structured when classification is
indicator_data. Aligns envelope and stated-value conventions with D3; does not
write donor_reports.indicator_actuals_json (E1 reconciles).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.reports.schemas.grant_terms_extraction_v1 import (
    ExtractionOutcome,
    SourceProvenance,
    StatedValue,
)

INDICATOR_DATA_EXTRACTION_SCHEMA_VERSION = "1.0.0"

CellState = Literal["stated", "blank", "not_applicable"]


class SourceLocator(BaseModel):
    sheet: str = Field(min_length=1)
    cell_range: str = Field(min_length=1)


class TabularCellField(BaseModel):
    absent: bool = False
    raw: str | None = None
    normalized: str | None = None
    cell_state: CellState | None = None
    normalization_ambiguous: bool = False
    source_locator: SourceLocator | None = None
    multi_value: bool = False
    stated_values: list[StatedValue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_absent_and_multi(self) -> TabularCellField:
        if self.absent:
            if self.raw is not None or self.normalized is not None:
                raise ValueError("absent=true requires raw=null and normalized=null")
            if self.cell_state is not None:
                raise ValueError("absent=true requires cell_state=null")
            if self.multi_value or self.stated_values:
                raise ValueError("absent=true cannot have stated_values")
            return self
        if self.multi_value:
            if len(self.stated_values) < 2:
                raise ValueError("multi_value=true requires at least two stated_values")
        elif self.cell_state is None:
            raise ValueError("non-absent field requires cell_state")
        return self


class DisaggregationBreakdownItem(BaseModel):
    label: str = Field(min_length=1)
    value: TabularCellField


class DisaggregationDimension(BaseModel):
    dimension: str = Field(min_length=1)
    stated_total: TabularCellField | None = None
    breakdown: list[DisaggregationBreakdownItem] = Field(default_factory=list)


class ExtractedIndicatorRow(BaseModel):
    row_id: str = Field(min_length=1)
    indicator_ref: TabularCellField
    indicator_name: TabularCellField
    target: TabularCellField
    actual: TabularCellField
    unit: TabularCellField | None = None
    disaggregation: list[DisaggregationDimension] = Field(default_factory=list)
    # Package B: the row's evidence/note/commentary cell (e.g. NLCF monitoring column
    # "Evidence or note") — delivery notes, reasons for variance, data caveats.
    # Captured verbatim with cell_state + source_locator; absent stays absent.
    note: TabularCellField | None = None
    source_locator: SourceLocator | None = None
    multi_value: bool = False
    # Section-routing carrier (Package A): the funder's own source-declared section
    # assignment for this row (e.g. NLCF monitoring column "Section for NLCF update").
    # Captured DETERMINISTICALLY from the source grid post-extraction; the LLM never
    # authors section membership. None when the source has no such column.
    section_assignment: TabularCellField | None = None


class FinancialLine(BaseModel):
    line_key: str = Field(min_length=1)
    label: TabularCellField
    budget: TabularCellField
    actual: TabularCellField


class IndicatorFinancials(BaseModel):
    currency: TabularCellField | None = None
    lines: list[FinancialLine] = Field(default_factory=list)


class IndicatorDataExtractionSummary(BaseModel):
    total_rows: int = 0
    rows_with_target: int = 0
    rows_with_actual_absent: int = 0
    multi_value_fields: int = 0


class IndicatorDataExtractionOutput(BaseModel):
    schema_version: str = INDICATOR_DATA_EXTRACTION_SCHEMA_VERSION
    indicators: list[ExtractedIndicatorRow] = Field(default_factory=list)
    financials: IndicatorFinancials | None = None
    extraction_outcome: ExtractionOutcome = "complete"
    summary: IndicatorDataExtractionSummary = Field(
        default_factory=IndicatorDataExtractionSummary
    )


class IndicatorDataAgentTrace(BaseModel):
    model_used: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated: bool | None = None
    cost_usd: float | None = None
    max_turns: int | None = None
    num_turns: int | None = None
    content_hash: str | None = None
    attempt_count: int | None = None
    degraded_code: str | None = None


class IndicatorDataExtractedEnvelope(BaseModel):
    extractor_agent: str = "indicator_data_extractor"
    extracted_at: datetime | None = None
    raw_text_ref: str | None = None
    structured: IndicatorDataExtractionOutput
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    error: str | None = None
    agent_trace: IndicatorDataAgentTrace | None = None
