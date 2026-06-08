"""Request/response schemas for report lifecycle entry routes."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateDonorReportRequest(BaseModel):
    reporting_period_start: date
    reporting_period_end: date
    linked_proposal_id: uuid.UUID | None = None
    funder_report_template_id: uuid.UUID


class DonorReportSummaryResponse(BaseModel):
    id: uuid.UUID
    funder_report_template_id: uuid.UUID
    funder_name: str
    template_name: str
    linked_proposal_id: uuid.UUID | None
    reporting_period_start: date
    reporting_period_end: date
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class UploadedDocumentResponse(BaseModel):
    id: uuid.UUID
    donor_report_id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    classification: str | None
    extraction_status: str
    created_at: datetime


class UploadedDocumentListResponse(BaseModel):
    documents: list[UploadedDocumentResponse]


class EnqueueReportJobResponse(BaseModel):
    job_id: uuid.UUID
    donor_report_id: uuid.UUID
    stage: str
    status: str


class ReportJobStatusResponse(BaseModel):
    job_id: uuid.UUID
    donor_report_id: uuid.UUID
    stage: str
    status: str
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    agent_trace_json: dict[str, Any] = Field(default_factory=dict)


class KnowledgeBankResponse(BaseModel):
    donor_report_id: uuid.UUID
    facts: dict[str, Any] = Field(default_factory=dict)
    conflicts: list[Any] = Field(default_factory=list)
    unreadable_sources: list[Any] = Field(default_factory=list)
    reconciliation_outcome: str | None = None
    gate1_confirmed_at: str | None = None
    ready_for_gate1: bool = False
    knowledge_bank_json: dict[str, Any] = Field(default_factory=dict)
