"""E1 degrade-path pass-through and parse-failure observability helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.reports.reconciliation.input_builder import FactCandidate, ReconciliationInputBundle
from app.reports.reconciliation.degrade_dedup import optimize_degraded_pass_through
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KnowledgeBankFact,
    KnowledgeBankReconciliationOutput,
    KnowledgeProvenance,
    ReconciliationAgentTrace,
    UnreadableSource,
)

logger = logging.getLogger("reports.agents.knowledge_bank_reconciler")

DEGRADED_PASS_THROUGH_NOTE = (
    "Degraded reconciliation pass-through from extractor candidate; "
    "not reconciled — human confirmation required at Gate 1."
)
PARSE_FAILURE_SNIPPET_CHARS = 500


@dataclass(frozen=True)
class ReconcilerFailureContext:
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_response_text: str | None = None
    latency_ms: int | None = None


def bounded_response_snippet(text: str | None) -> tuple[str | None, str | None, int | None]:
    if not text:
        return None, None, None
    length = len(text)
    if length <= PARSE_FAILURE_SNIPPET_CHARS * 2:
        return text, None, length
    return (
        text[:PARSE_FAILURE_SNIPPET_CHARS],
        text[-PARSE_FAILURE_SNIPPET_CHARS:],
        length,
    )


def _provenance_from_candidate(candidate: FactCandidate) -> KnowledgeProvenance:
    prov = candidate.provenance or {}
    excerpt = prov.get("excerpt") or candidate.semantic_hint or "(no excerpt)"
    return KnowledgeProvenance(
        excerpt=str(excerpt)[:500] or "(no excerpt)",
        section_label=prov.get("section_label"),
        page=prov.get("page"),
        char_start=prov.get("char_start"),
        char_end=prov.get("char_end"),
        cell_ref=prov.get("cell_ref"),
    )


def pass_through_facts_from_candidates(
    bundle: ReconciliationInputBundle,
) -> dict[str, KnowledgeBankFact]:
    facts: dict[str, KnowledgeBankFact] = {}
    for candidate in bundle.fact_candidates:
        fact_key = f"degraded_pass_through:{candidate.candidate_id}"
        value = (
            candidate.value_normalized
            if candidate.value_normalized is not None
            else candidate.value_raw
        )
        facts[fact_key] = KnowledgeBankFact(
            value=value,
            unit=candidate.unit,
            semantic_label=candidate.semantic_hint,
            coverage="single_source",
            source_document_id=candidate.document_id,
            source_label=candidate.source_label,
            provenance=_provenance_from_candidate(candidate),
            interpretation_note=DEGRADED_PASS_THROUGH_NOTE,
            confirmed=False,
            confirmed_by_user=False,
        )
    return facts


def unreadable_sources_from_bundle(
    bundle: ReconciliationInputBundle,
) -> list[UnreadableSource]:
    return [
        UnreadableSource(
            source_document_id=item.document_id,
            source_label=item.source_label,
            code=item.code,
            message=item.message,
        )
        for item in bundle.unreadable_sources
    ]


def build_degraded_structured_output(
    bundle: ReconciliationInputBundle | None,
) -> KnowledgeBankReconciliationOutput:
    if bundle is None or not bundle.fact_candidates:
        return KnowledgeBankReconciliationOutput(reconciliation_outcome="degraded")
    raw_facts = pass_through_facts_from_candidates(bundle)
    facts, conflicts = optimize_degraded_pass_through(raw_facts)
    return KnowledgeBankReconciliationOutput(
        reconciliation_outcome="degraded",
        facts=facts,
        conflicts=conflicts,
        unreadable_sources=unreadable_sources_from_bundle(bundle),
    )


def apply_failure_observability_to_trace(
    trace: ReconciliationAgentTrace,
    failure_context: ReconcilerFailureContext | None,
) -> ReconciliationAgentTrace:
    if failure_context is None:
        return trace
    head, tail, length = bounded_response_snippet(failure_context.raw_response_text)
    return trace.model_copy(
        update={
            "input_tokens": failure_context.input_tokens,
            "output_tokens": failure_context.output_tokens,
            "latency_ms": failure_context.latency_ms,
            "parse_failure_response_length": length,
            "parse_failure_response_head": head,
            "parse_failure_response_tail": tail,
        }
    )


def log_degraded_reconcile(
    *,
    bundle: ReconciliationInputBundle | None,
    fact_count: int,
) -> None:
    candidate_count = len(bundle.fact_candidates) if bundle else 0
    logger.warning(
        "knowledge_bank_reconciler degraded candidates=%d pass_through_facts=%d",
        candidate_count,
        fact_count,
    )
