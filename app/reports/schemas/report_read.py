"""Schemas for M&E read endpoints (list, detail, templates)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportListItemResponse(BaseModel):
    id: uuid.UUID
    funder_name: str
    template_name: str
    status: str
    reporting_period_start: date
    reporting_period_end: date
    current_gate: str
    latest_job_status: str | None = None
    latest_job_stage: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportListResponse(BaseModel):
    reports: list[ReportListItemResponse]


class ReportDetailResponse(BaseModel):
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
    content_json: dict[str, Any] = Field(default_factory=dict)
    knowledge_bank_json: dict[str, Any] = Field(default_factory=dict)
    gap_analysis_json: dict[str, Any] = Field(default_factory=dict)
    indicator_actuals_json: dict[str, Any] = Field(default_factory=dict)
    current_gate: str
    gate3_confirmed_at: str | None = None


class ReportTemplateItemResponse(BaseModel):
    id: uuid.UUID
    funder_name: str
    template_name: str
    region: str
    reporting_frequency: str
    version: int


class ReportTemplateListResponse(BaseModel):
    report_templates: list[ReportTemplateItemResponse]
