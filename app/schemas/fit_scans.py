from datetime import datetime
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
