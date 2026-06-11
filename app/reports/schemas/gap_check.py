"""§12.6 / §12.7 — Gate 2 gap-check read and draft answer patch."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

GapCheckSeverity = Literal["required", "recommended"]


class GapCheckMissingItemResponse(BaseModel):
    item_key: str
    label: str
    prompt: str
    severity: GapCheckSeverity = "required"
    section_key: str | None = None
    section_label: str | None = None
    question: str | None = None
    rationale: str | None = None
    owner: str | None = None
    requirement_type: str | None = None
    suggested_action: str | None = None
    confirm_existing_excerpt: str | None = None


class GapCheckResponse(BaseModel):
    donor_report_id: uuid.UUID
    open_items_count: int = Field(ge=0, default=0)
    ready_for_gate2: bool = False
    missing_items: list[GapCheckMissingItemResponse] = Field(default_factory=list)
    gate2_confirmed_at: str | None = None
    readiness_basis: str | None = None
    readiness_message: str | None = None


class GapAnswerPatchInput(BaseModel):
    answer_text: str | None = None
    disposition: Literal["answered", "skipped"] | None = None
    skip_reason: Literal["not_applicable", "cannot_provide"] | None = None


class PatchGapAnswersRequest(BaseModel):
    gap_answers: dict[str, GapAnswerPatchInput] = Field(default_factory=dict)
    confirm_gate2: bool = False
