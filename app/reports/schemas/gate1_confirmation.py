"""Gate 1 (human knowledge-bank confirmation) API schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class Gate1ConfirmRequest(BaseModel):
    """Final confirmed knowledge bank — same persisted shape as E1 output."""

    knowledge_bank_json: dict[str, Any] = Field(
        ...,
        description="donor_reports.knowledge_bank_json shape after human edits",
    )


class Gate1ConfirmResponse(BaseModel):
    donor_report_id: uuid.UUID
    knowledge_bank_json: dict[str, Any]
    gate1_confirmed_at: str
