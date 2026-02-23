from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class StandardErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class FundingOpportunityResponseItem(BaseModel):
    id: UUID
    title: str
    donor_organization: str
    funding_type: str
    applicant_type: str
    location_text: str
    focus_areas: list[str]
    deadline_type: str
    application_deadline: date | None = None
    short_summary: str
    source_url: str
    application_url: str
    status: str
    is_active: bool
    last_verified: date | None = None


class FundingOpportunityResponse(BaseModel):
    funding_opportunity: FundingOpportunityResponseItem
