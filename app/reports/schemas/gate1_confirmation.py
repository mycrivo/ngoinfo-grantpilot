"""Gate 1 (human knowledge-bank confirmation) API schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class FactPromotionEntry(BaseModel):
    """One fact in a user-reviewed cluster batch — server validates per-fact."""

    fact_key: str = Field(min_length=1)
    confirmed_value_snapshot: Any = None


class Gate1ConfirmRequest(BaseModel):
    """Final confirmed knowledge bank — same persisted shape as E1 output."""

    knowledge_bank_json: dict[str, Any] = Field(
        ...,
        description="donor_reports.knowledge_bank_json shape after human edits",
    )
    promote_fact_keys: list[FactPromotionEntry] = Field(
        default_factory=list,
        description=(
            "Optional batch from one user-reviewed cluster; each entry promotes "
            "one unverified fact after snapshot validation — never blind confirm-all."
        ),
    )
    cluster_id: str | None = Field(
        default=None,
        description="Observability: identifies the reviewed cluster for this batch.",
    )


class Gate1PromoteRequest(BaseModel):
    """Promote unverified facts from one cluster without setting gate1_confirmed_at."""

    promote_fact_keys: list[FactPromotionEntry] = Field(min_length=1)
    cluster_id: str | None = None


class Gate1PromotionResult(BaseModel):
    promoted_fact_keys: list[str] = Field(default_factory=list)
    rejected_promotions: list[dict[str, Any]] = Field(default_factory=list)
    unverified_excluded_count: int = 0
    cluster_id: str | None = None


class Gate1ConfirmResponse(BaseModel):
    donor_report_id: uuid.UUID
    knowledge_bank_json: dict[str, Any]
    gate1_confirmed_at: str
    promoted_fact_keys: list[str] = Field(default_factory=list)
    rejected_promotions: list[dict[str, Any]] = Field(default_factory=list)
    unverified_excluded_count: int = 0
    cluster_id: str | None = None
