"""Deterministic dedup and conflict surfacing for degraded reconciliation pass-through."""

from __future__ import annotations

import json
from collections import defaultdict

from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    ConflictValueEntry,
    KnowledgeBankConflict,
    KnowledgeBankFact,
    KnowledgeProvenance,
)

CONFLICT_ANNOTATION = (
    "Same semantic label with differing values from multiple sources; "
    "human must choose at Gate 1."
)


def _label_key(fact: KnowledgeBankFact) -> str:
    return fact.semantic_label.strip().lower()


def _value_key(fact: KnowledgeBankFact) -> str:
    return f"{json.dumps(fact.value, sort_keys=True, default=str)}::{fact.unit or ''}"


def _provenance_from_fact(fact: KnowledgeBankFact) -> KnowledgeProvenance:
    return fact.provenance


def optimize_degraded_pass_through(
    facts: dict[str, KnowledgeBankFact],
) -> tuple[dict[str, KnowledgeBankFact], list[KnowledgeBankConflict]]:
    """Collapse exact duplicates; surface value mismatches as conflicts."""
    by_label: dict[str, list[tuple[str, KnowledgeBankFact]]] = defaultdict(list)
    for fact_key, fact in facts.items():
        by_label[_label_key(fact)].append((fact_key, fact))

    optimized: dict[str, KnowledgeBankFact] = {}
    conflicts: list[KnowledgeBankConflict] = []

    for label_key, entries in by_label.items():
        by_value: dict[str, list[tuple[str, KnowledgeBankFact]]] = defaultdict(list)
        for fact_key, fact in entries:
            by_value[_value_key(fact)].append((fact_key, fact))

        if len(by_value) > 1:
            primary_key, primary_fact = entries[0]
            conflict_values: list[ConflictValueEntry] = []
            for _fact_key, fact in entries:
                conflict_values.append(
                    ConflictValueEntry(
                        value=fact.value,
                        unit=fact.unit,
                        source_document_id=fact.source_document_id,
                        source_label=fact.source_label,
                        provenance=_provenance_from_fact(fact),
                    )
                )
            conflicts.append(
                KnowledgeBankConflict(
                    fact_key=primary_key,
                    conflict_type="VALUE_MISMATCH",
                    values=conflict_values,
                    annotation=CONFLICT_ANNOTATION,
                )
            )
            optimized[primary_key] = primary_fact
            continue

        bucket = next(iter(by_value.values()))
        primary_key, primary_fact = bucket[0]
        alternate_sources = [fact.source_label for _, fact in bucket[1:]]
        note = primary_fact.interpretation_note
        if alternate_sources:
            also = ", ".join(alternate_sources)
            merge_note = f"Also corroborated in: {also}."
            note = f"{note} {merge_note}".strip() if note else merge_note
        optimized[primary_key] = primary_fact.model_copy(update={"interpretation_note": note})
        for fact_key, _ in bucket[1:]:
            continue

    return optimized, conflicts
