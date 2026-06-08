"""Schemas for Gate 3 review and critique resume (P0-2)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, model_validator


class ResumeCritiqueResponse(BaseModel):
    job_id: uuid.UUID
    donor_report_id: uuid.UUID
    stage: str
    status: str


class PatchReportSectionRequest(BaseModel):
    content_text: str | None = None
    accept_critic_flags: list[str] = Field(default_factory=list)
    accept_section: bool = False

    @model_validator(mode="after")
    def at_least_one_field(self) -> PatchReportSectionRequest:
        if (
            self.content_text is None
            and not self.accept_critic_flags
            and not self.accept_section
        ):
            raise ValueError(
                "At least one of content_text, accept_critic_flags, or accept_section is required"
            )
        return self


class AcceptAllSectionsResponse(BaseModel):
    donor_report_id: uuid.UUID
    sections_accepted: int
