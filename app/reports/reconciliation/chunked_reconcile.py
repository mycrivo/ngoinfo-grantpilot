"""Chunk large E1 reconciliation inputs and merge chunk outputs."""

from __future__ import annotations

import json
import os
from typing import Any

from app.reports.agents.knowledge_bank_reconciler import (
    KnowledgeBankReconcilerResult,
    build_reconciliation_prompt,
    reconcile_bundle,
)
from app.reports.reconciliation.input_builder import FactCandidate, ReconciliationInputBundle
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KnowledgeBankFact,
    KnowledgeBankReconciliationOutput,
    ReconciliationAgentTrace,
)


def chunk_candidate_size() -> int:
    return int(os.getenv("ME_RECONCILER_CHUNK_CANDIDATES", "40"))


def split_bundle(bundle: ReconciliationInputBundle) -> list[ReconciliationInputBundle]:
    size = chunk_candidate_size()
    candidates = list(bundle.fact_candidates)
    if len(candidates) <= size:
        return [bundle]
    chunks: list[ReconciliationInputBundle] = []
    for start in range(0, len(candidates), size):
        chunks.append(
            ReconciliationInputBundle(
                fact_candidates=candidates[start : start + size],
                unreadable_sources=bundle.unreadable_sources if start == 0 else [],
            )
        )
    return chunks


def _merge_facts(facts_list: list[dict[str, KnowledgeBankFact]]) -> dict[str, KnowledgeBankFact]:
    merged: dict[str, KnowledgeBankFact] = {}
    for facts in facts_list:
        for key, fact in facts.items():
            if key not in merged:
                merged[key] = fact
    return merged


def merge_chunk_results(
    results: list[KnowledgeBankReconcilerResult],
    *,
    truncated_candidate_ids: list[str] | None = None,
    output_truncated: bool = False,
) -> KnowledgeBankReconcilerResult:
    if not results:
        raise ValueError("merge_chunk_results requires at least one result")
    if len(results) == 1:
        result = results[0]
        if truncated_candidate_ids or output_truncated:
            structured = result.envelope.structured.model_copy(deep=True)
            if output_truncated or truncated_candidate_ids:
                structured.reconciliation_outcome = "degraded"
            trace = result.envelope.agent_trace
            trace_data = trace.model_dump() if trace else {}
            if truncated_candidate_ids:
                trace_data["reconciliation_truncated_input"] = True
                trace_data["truncated_candidate_ids"] = truncated_candidate_ids
            if output_truncated:
                trace_data["degraded_code"] = trace_data.get("degraded_code") or "OUTPUT_TRUNCATED"
            new_trace = ReconciliationAgentTrace.model_validate(trace_data)
            result.envelope.structured = structured
            result.envelope.agent_trace = new_trace
        return result

    base = results[0]
    all_facts = [_r.envelope.structured.facts for _r in results]
    all_conflicts = []
    unreadable = list(base.envelope.structured.unreadable_sources)
    degraded = False
    output_truncated = output_truncated or any(
        (_r.envelope.agent_trace or ReconciliationAgentTrace()).degraded_code
        == "OUTPUT_TRUNCATED"
        for _r in results
    )
    for result in results:
        all_conflicts.extend(result.envelope.structured.conflicts)
        if result.envelope.structured.reconciliation_outcome == "degraded":
            degraded = True
        unreadable.extend(result.envelope.structured.unreadable_sources)

    seen_ids: set[str] = set()
    deduped_unreadable = []
    for item in unreadable:
        if item.source_document_id in seen_ids:
            continue
        seen_ids.add(item.source_document_id)
        deduped_unreadable.append(item)

    merged_structured = KnowledgeBankReconciliationOutput(
        facts=_merge_facts(all_facts),
        conflicts=all_conflicts,
        unreadable_sources=deduped_unreadable,
        reconciliation_outcome="degraded" if degraded or truncated_candidate_ids or output_truncated else "complete",
    )
    trace_data = (base.envelope.agent_trace or ReconciliationAgentTrace()).model_dump()
    if truncated_candidate_ids:
        trace_data["reconciliation_truncated_input"] = True
        trace_data["truncated_candidate_ids"] = truncated_candidate_ids
    if output_truncated:
        trace_data["degraded_code"] = "OUTPUT_TRUNCATED"
    base.envelope.structured = merged_structured
    base.envelope.agent_trace = ReconciliationAgentTrace.model_validate(trace_data)
    return base


def detect_prompt_truncation(bundle: ReconciliationInputBundle) -> tuple[str, list[str]]:
    """Build prompt and return truncated candidate ids when input is cut."""
    from app.reports.agents.knowledge_bank_reconciler import MAX_INPUT_CHARS

    payload = bundle.model_dump(mode="json")
    text = json.dumps(payload, indent=2)
    if len(text) <= MAX_INPUT_CHARS:
        return build_reconciliation_prompt(bundle), []
    truncated = [
        c.candidate_id
        for c in bundle.fact_candidates
        if c.candidate_id not in text[:MAX_INPUT_CHARS]
    ]
    return build_reconciliation_prompt(bundle), truncated


async def reconcile_bundle_chunked(
    bundle: ReconciliationInputBundle,
    **kwargs: Any,
) -> KnowledgeBankReconcilerResult:
    chunks = split_bundle(bundle)
    if len(chunks) == 1:
        _, truncated = detect_prompt_truncation(bundle)
        result = await reconcile_bundle(bundle, **kwargs)
        if truncated:
            structured = result.envelope.structured.model_copy(deep=True)
            structured.reconciliation_outcome = "degraded"
            trace_data = (result.envelope.agent_trace or ReconciliationAgentTrace()).model_dump()
            trace_data["reconciliation_truncated_input"] = True
            trace_data["truncated_candidate_ids"] = truncated
            result.envelope.structured = structured
            result.envelope.agent_trace = ReconciliationAgentTrace.model_validate(trace_data)
        return result

    results: list[KnowledgeBankReconcilerResult] = []
    for chunk in chunks:
        results.append(await reconcile_bundle(chunk, **kwargs))
    omitted = [
        c.candidate_id
        for c in bundle.fact_candidates
        if c.candidate_id not in {x.candidate_id for chunk in chunks for x in chunk.fact_candidates}
    ]
    return merge_chunk_results(results, truncated_candidate_ids=omitted or None)
