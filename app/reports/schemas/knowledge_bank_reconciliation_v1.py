"""Knowledge-bank reconciliation schema v1.0.0 — E1 output persisted to donor_reports.knowledge_bank_json."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

KNOWLEDGE_BANK_RECONCILIATION_VERSION = "1.0.0"
RECONCILER_AGENT_NAME = "knowledge_bank_reconciler"

ReconciliationOutcome = Literal["complete", "degraded"]
ConflictType = Literal["VALUE_MISMATCH", "UNIT_GRANULARITY"]
FactCoverage = Literal["agreed", "single_source"]
FactVerificationStatus = Literal["reconciled", "unverified"]


class KnowledgeProvenance(BaseModel):
    excerpt: str = Field(min_length=1)
    section_label: str | None = None
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    cell_ref: str | None = None


class KnowledgeBankFact(BaseModel):
    value: Any = None
    unit: str | None = None
    semantic_label: str = Field(min_length=1)
    coverage: FactCoverage = "single_source"
    source_document_id: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    provenance: KnowledgeProvenance
    interpretation_note: str | None = None
    verification_status: FactVerificationStatus = "unverified"
    confirmed: bool = False
    confirmed_at: datetime | None = None
    confirmed_by_user: bool = False
    # Section-routing carrier (Package A): the funder's own source-declared section
    # for this fact, attached deterministically by the reconciler via a cell_ref join
    # to the candidate. NOT authored by the LLM (absent from _LLMFact). None when the
    # source carried no section signal -> declared-needs visibility fallback applies.
    source_section: str | None = None


class ConflictValueEntry(BaseModel):
    value: Any = None
    unit: str | None = None
    source_document_id: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    provenance: KnowledgeProvenance


class KnowledgeBankConflict(BaseModel):
    fact_key: str = Field(min_length=1)
    conflict_type: ConflictType
    values: list[ConflictValueEntry] = Field(min_length=2)
    annotation: str | None = None
    resolved_value: Any | None = None
    resolved_at: datetime | None = None


class UnreadableSource(BaseModel):
    source_document_id: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ReconciliationAgentTrace(BaseModel):
    model_used: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated: bool | None = None
    cost_usd: float | None = None
    max_turns: int | None = None
    attempt_count: int | None = None
    num_turns: int | None = None
    degraded_code: str | None = None
    conflicts_surfaced_count: int | None = None
    parse_failure_response_length: int | None = None
    parse_failure_response_head: str | None = None
    parse_failure_response_tail: str | None = None
    reconciliation_truncated_input: bool | None = None
    truncated_candidate_ids: list[str] | None = None


class KnowledgeBankReconciliationOutput(BaseModel):
    schema_version: str = KNOWLEDGE_BANK_RECONCILIATION_VERSION
    facts: dict[str, KnowledgeBankFact] = Field(default_factory=dict)
    conflicts: list[KnowledgeBankConflict] = Field(default_factory=list)
    unreadable_sources: list[UnreadableSource] = Field(default_factory=list)
    reconciliation_outcome: ReconciliationOutcome = "complete"
    gate1_confirmed_at: datetime | None = None
    gate2_confirmed_at: datetime | None = None
    gate3_confirmed_at: datetime | None = None
    gap_answers: dict[str, Any] = Field(default_factory=dict)


class KnowledgeBankReconciledEnvelope(BaseModel):
    """Shape persisted to donor_reports.knowledge_bank_json."""

    reconciliation_version: str = KNOWLEDGE_BANK_RECONCILIATION_VERSION
    reconciler_agent: str = RECONCILER_AGENT_NAME
    reconciled_at: datetime | None = None
    structured: KnowledgeBankReconciliationOutput
    error: str | None = None
    agent_trace: ReconciliationAgentTrace | None = None


STRUCTURED_KNOWLEDGE_BANK_KEYS = frozenset(
    {
        "schema_version",
        "facts",
        "conflicts",
        "unreadable_sources",
        "reconciliation_outcome",
        "gate1_confirmed_at",
        "gate2_confirmed_at",
        "gate3_confirmed_at",
        "gap_answers",
    }
)


def structured_payload_from_persisted(knowledge_bank_json: dict) -> dict:
    """Extract KnowledgeBankReconciliationOutput fields from persisted JSONB."""
    return {
        key: knowledge_bank_json.get(key)
        for key in STRUCTURED_KNOWLEDGE_BANK_KEYS
        if key in knowledge_bank_json
    }


def validate_gate1_knowledge_bank(output: KnowledgeBankReconciliationOutput) -> list[str]:
    """Gate 1 confirm — provenance required; human may set conflict resolutions."""
    errors: list[str] = []
    for fact_key, fact in output.facts.items():
        if not fact.source_document_id:
            errors.append(f"fact {fact_key!r} missing source_document_id")
        if not fact.provenance or not fact.provenance.excerpt:
            errors.append(f"fact {fact_key!r} missing provenance excerpt")
    for conflict in output.conflicts:
        if conflict.resolved_value is None:
            errors.append(
                f"conflict {conflict.fact_key!r} is unresolved — set resolved_value before Gate 1 confirm"
            )
        if len(conflict.values) < 2:
            errors.append(f"conflict {conflict.fact_key!r} requires >= 2 values")
        for entry in conflict.values:
            if not entry.source_document_id:
                errors.append(
                    f"conflict {conflict.fact_key!r} value missing source_document_id"
                )
            if not entry.provenance or not entry.provenance.excerpt:
                errors.append(
                    f"conflict {conflict.fact_key!r} value missing provenance excerpt"
                )
    return errors


def validate_gate1_confirm_payload(knowledge_bank_json: dict) -> list[str]:
    """Validate human-confirmed knowledge bank before persist (no model call)."""
    errors: list[str] = []
    if knowledge_bank_json.get("schema_version") != KNOWLEDGE_BANK_RECONCILIATION_VERSION:
        errors.append("invalid or missing schema_version")
    if knowledge_bank_json.get("reconciler_agent") != RECONCILER_AGENT_NAME:
        errors.append("knowledge bank must be reconciled before Gate 1 confirmation")
    try:
        structured = KnowledgeBankReconciliationOutput.model_validate(
            structured_payload_from_persisted(knowledge_bank_json)
        )
    except Exception as exc:
        errors.append(f"structured payload invalid: {exc}")
        return errors
    errors.extend(validate_gate1_knowledge_bank(structured))
    return errors


def validate_e1_knowledge_bank(output: KnowledgeBankReconciliationOutput) -> list[str]:
    """Deterministic E1 contract checks — fail closed before persist."""
    errors: list[str] = []
    for fact_key, fact in output.facts.items():
        if not fact.source_document_id:
            errors.append(f"fact {fact_key!r} missing source_document_id")
        if not fact.provenance or not fact.provenance.excerpt:
            errors.append(f"fact {fact_key!r} missing provenance excerpt")
    for conflict in output.conflicts:
        if conflict.resolved_value is not None:
            errors.append(
                f"conflict {conflict.fact_key!r} has resolved_value set (forbidden at E1)"
            )
        if conflict.resolved_at is not None:
            errors.append(
                f"conflict {conflict.fact_key!r} has resolved_at set (forbidden at E1)"
            )
        if len(conflict.values) < 2:
            errors.append(f"conflict {conflict.fact_key!r} requires >= 2 values")
        for entry in conflict.values:
            if not entry.source_document_id:
                errors.append(
                    f"conflict {conflict.fact_key!r} value missing source_document_id"
                )
            if not entry.provenance or not entry.provenance.excerpt:
                errors.append(
                    f"conflict {conflict.fact_key!r} value missing provenance excerpt"
                )
    return errors


class _LLMProvenance(BaseModel):
    excerpt: str
    section_label: str | None = None
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    cell_ref: str | None = None


class _LLMFact(BaseModel):
    fact_key: str
    value: Any = None
    unit: str | None = None
    semantic_label: str
    coverage: FactCoverage = "single_source"
    source_document_id: str
    source_label: str
    provenance: _LLMProvenance
    interpretation_note: str | None = None


class _LLMConflictValue(BaseModel):
    value: Any = None
    unit: str | None = None
    source_document_id: str
    source_label: str
    provenance: _LLMProvenance


class _LLMConflict(BaseModel):
    fact_key: str
    conflict_type: ConflictType
    values: list[_LLMConflictValue] = Field(min_length=2)
    annotation: str | None = None


class _LLMUnreadableSource(BaseModel):
    source_document_id: str
    source_label: str
    code: str
    message: str


class KnowledgeBankReconcilerLLMOutput(BaseModel):
    facts: list[_LLMFact] = Field(default_factory=list)
    conflicts: list[_LLMConflict] = Field(default_factory=list)
    unreadable_sources: list[_LLMUnreadableSource] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def no_resolved_fields(self) -> KnowledgeBankReconcilerLLMOutput:
        return self
