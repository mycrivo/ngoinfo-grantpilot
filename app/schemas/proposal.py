from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProposalCreateRequest(BaseModel):
    funding_opportunity_id: UUID
    fit_scan_id: UUID | None = None
    selected_variant_id: str | None = None
    user_overrides: dict[str, Any] | None = None


class ProposalResponse(BaseModel):
    id: UUID
    funding_opportunity_id: UUID
    status: str
    created_at: datetime
    generation_summary: dict[str, Any] | None = None


class ProposalDetailResponse(BaseModel):
    id: UUID
    funding_opportunity_id: UUID
    status: str
    version: int
    regeneration_count: int
    content_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
