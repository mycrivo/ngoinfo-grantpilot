"""Gate 3 — human confirmation after fact-safety review."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class Gate3ConfirmResponse(BaseModel):
    donor_report_id: uuid.UUID
    gate3_confirmed_at: str
    knowledge_bank_json: dict
