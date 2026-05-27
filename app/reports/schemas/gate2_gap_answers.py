"""Gate 2 — human gap-answer intake (answer-or-skip, no model call)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

GapAnswerDisposition = Literal["answered", "skipped"]
GapSkipReason = Literal["not_applicable", "cannot_provide"]


class Gate2GapResponseInput(BaseModel):
    """One human response for an E3-surfaced gap (keyed by item_key)."""

    disposition: GapAnswerDisposition
    answer_text: str | None = None
    skip_reason: GapSkipReason | None = None

    @model_validator(mode="after")
    def validate_answer_or_skip(self) -> Gate2GapResponseInput:
        if self.disposition == "answered":
            if not self.answer_text or not self.answer_text.strip():
                raise ValueError("answer_text is required when disposition is answered")
            if self.skip_reason is not None:
                raise ValueError("skip_reason must be null when disposition is answered")
        else:
            if self.skip_reason is None:
                raise ValueError("skip_reason is required when disposition is skipped")
            if self.answer_text is not None and str(self.answer_text).strip():
                raise ValueError("answer_text must be null when disposition is skipped")
        return self


class Gate2GapAnswersRequest(BaseModel):
    responses: dict[str, Gate2GapResponseInput] = Field(
        default_factory=dict,
        description="Map of E3 gap item_key → human response",
    )


class Gate2GapAnswerProvenance(BaseModel):
    source: Literal["human_confirmed_gap_answer"] = "human_confirmed_gap_answer"
    excerpt: str = Field(min_length=1)


class Gate2GapAnswerPersisted(BaseModel):
    disposition: GapAnswerDisposition
    answer_text: str | None = None
    skip_reason: GapSkipReason | None = None
    responded_at: str
    provenance: Gate2GapAnswerProvenance | None = None
    source_label: str | None = None
    source_document_id: str | None = None


class Gate2RemainingGap(BaseModel):
    item_key: str
    section_key: str
    section_label: str
    required_item_type: str
    required_item_ref: str
    question: str


class Gate2GapAnswersResponse(BaseModel):
    donor_report_id: uuid.UUID
    gate2_confirmed_at: str | None = None
    gate2_unlocked: bool = False
    gap_answers: dict[str, Any]
    remaining_gaps: list[Gate2RemainingGap] = Field(default_factory=list)
