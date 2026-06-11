"""Tests for E1 reconciliation input chunking (Phase 2-3)."""

from __future__ import annotations

from app.reports.reconciliation.chunked_reconcile import chunk_candidate_size, split_bundle
from app.reports.reconciliation.input_builder import FactCandidate, ReconciliationInputBundle


def _candidate(index: int) -> FactCandidate:
    return FactCandidate(
        candidate_id=f"c{index}",
        document_id="doc-1",
        source_label="doc",
        classification="proposal",
        field_path=f"field_{index}",
        semantic_hint=f"hint {index}",
        value_raw=str(index),
    )


def test_split_bundle_chunks_large_candidate_lists(monkeypatch):
    monkeypatch.setenv("ME_RECONCILER_CHUNK_CANDIDATES", "3")
    bundle = ReconciliationInputBundle(
        fact_candidates=[_candidate(i) for i in range(7)],
        unreadable_sources=[],
    )
    chunks = split_bundle(bundle)
    assert len(chunks) == 3
    assert len(chunks[0].fact_candidates) == 3
    assert len(chunks[-1].fact_candidates) == 1


def test_split_bundle_keeps_small_bundles_intact():
    bundle = ReconciliationInputBundle(
        fact_candidates=[_candidate(i) for i in range(2)],
        unreadable_sources=[],
    )
    assert split_bundle(bundle) == [bundle]
    assert chunk_candidate_size() >= 1
