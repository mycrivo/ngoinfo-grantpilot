"""Tests for degraded pass-through dedup and conflict surfacing."""

from app.reports.reconciliation.degrade_dedup import optimize_degraded_pass_through
from app.reports.schemas.knowledge_bank_reconciliation_v1 import KnowledgeBankFact, KnowledgeProvenance


def _fact(
    *,
    label: str,
    value: str,
    source_label: str,
    source_document_id: str = "doc-1",
) -> KnowledgeBankFact:
    return KnowledgeBankFact(
        value=value,
        unit=None,
        semantic_label=label,
        source_document_id=source_document_id,
        source_label=source_label,
        provenance=KnowledgeProvenance(excerpt=value),
    )


def test_collapses_identical_label_and_value():
    facts = {
        "a": _fact(label="Financials currency", value="GBP", source_label="doc-a", source_document_id="d1"),
        "b": _fact(label="Financials currency", value="GBP", source_label="doc-b", source_document_id="d2"),
    }

    optimized, conflicts = optimize_degraded_pass_through(facts)

    assert len(optimized) == 1
    assert "a" in optimized
    assert "Also corroborated in: doc-b." in (optimized["a"].interpretation_note or "")
    assert conflicts == []


def test_surfaces_value_mismatch_as_conflict():
    facts = {
        "a": _fact(label="indicator target (OP1.1)", value="650", source_label="proposal"),
        "b": _fact(label="indicator target (OP1.1)", value="700", source_label="sheet", source_document_id="d2"),
    }

    optimized, conflicts = optimize_degraded_pass_through(facts)

    assert len(optimized) == 1
    assert len(conflicts) == 1
    assert conflicts[0].fact_key == "a"
    assert len(conflicts[0].values) == 2
