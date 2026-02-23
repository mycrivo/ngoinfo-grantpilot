from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class FitScanCreateRequest(BaseModel):
    funding_opportunity_id: UUID


class FitScanSubscores(BaseModel):
    eligibility: int
    alignment: int
    readiness: int


class FitScanRiskFlag(BaseModel):
    risk_type: str
    severity: str
    description: str


class FitScanResponse(BaseModel):
    id: UUID
    funding_opportunity_id: UUID
    overall_recommendation: str
    model_rating: str
    subscores: FitScanSubscores
    primary_rationale: str
    risk_flags: list[FitScanRiskFlag]
    created_at: datetime


class FitScanResponseEnvelope(BaseModel):
    fit_scan: FitScanResponse


class StandardErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class FitScanListItem(BaseModel):
    id: UUID
    funding_opportunity_id: UUID
    opportunity_title: str | None = None
    overall_recommendation: Literal[
        "RECOMMENDED", "APPLY_WITH_CAVEATS", "NOT_RECOMMENDED"
    ]
    model_rating: Literal["STRONG", "MODERATE", "WEAK"]
    subscores: FitScanSubscores
    created_at: datetime


class FitScanListResponse(BaseModel):
    fit_scans: list[FitScanListItem]
