from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class ProposalCreateRequest(BaseModel):
    funding_opportunity_id: UUID
    fit_scan_id: UUID | None = None
    selected_variant_id: str | None = None
    user_overrides: dict[str, Any] | None = None


class ProposalGenerationSummary(BaseModel):
    total_items: int
    generated: int
    failed: int
    manual_required: int
    warnings: list[str]


class ProposalSectionContent(BaseModel):
    text: str
    assumptions: list[str]
    evidence_used: list[str]


class ProposalSectionConstraints(BaseModel):
    word_limit: int
    word_limit_respected: bool


class ProposalSection(BaseModel):
    submission_item_id: str | None = None
    label: str
    generation_status: Literal["GENERATED", "FAILED", "MANUAL_REQUIRED"]
    archetype: str | None = None
    content: ProposalSectionContent
    failure_reason: str | None = None
    constraints_applied: ProposalSectionConstraints


class ProposalContentJson(BaseModel):
    sections: list[ProposalSection]
    generation_summary: ProposalGenerationSummary


class ProposalResponse(BaseModel):
    id: UUID
    funding_opportunity_id: UUID
    fit_scan_id: UUID | None = None
    opportunity_title: str | None = None
    status: Literal["DRAFT", "DEGRADED"]
    version: int
    created_at: datetime
    generation_summary: ProposalGenerationSummary | None = None


class ProposalDetailResponse(BaseModel):
    id: UUID
    funding_opportunity_id: UUID
    fit_scan_id: UUID | None = None
    opportunity_title: str | None = None
    status: Literal["DRAFT", "DEGRADED"]
    version: int
    regeneration_count: int
    content_json: ProposalContentJson
    created_at: datetime
    updated_at: datetime


class ProposalExportRequest(BaseModel):
    format: str


class StandardErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class ProposalListItem(BaseModel):
    id: UUID
    funding_opportunity_id: UUID
    fit_scan_id: UUID | None = None
    opportunity_title: str | None = None
    status: Literal["DRAFT", "DEGRADED"]
    version: int
    created_at: datetime
    updated_at: datetime
    generation_summary: ProposalGenerationSummary | None = None


class ProposalListResponse(BaseModel):
    proposals: list[ProposalListItem]
