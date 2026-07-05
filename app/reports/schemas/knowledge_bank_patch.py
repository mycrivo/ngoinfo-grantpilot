"""PATCH /api/reports/{id}/knowledge-bank — Gate 1 incremental save (API_CONTRACT §12.5)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeBankFactPatch(BaseModel):
    value: Any
    confirmed: bool = False


class KnowledgeBankConflictResolution(BaseModel):
    fact_key: str = Field(min_length=1)
    resolved_value: Any


class PatchKnowledgeBankRequest(BaseModel):
    facts: dict[str, KnowledgeBankFactPatch] | None = None
    conflict_resolutions: list[KnowledgeBankConflictResolution] | None = None
    confirm_gate1: bool = False
