"""D-058/D-060 conflict integrity normalizer — orphan repair + exact sibling marking."""

from __future__ import annotations

import logging

from app.reports.knowledge.conflict_integrity import ensure_conflicts_materializable
from app.reports.knowledge.confirmed_kb import is_fact_citable
from app.reports.services.knowledge_bank_patch_service import materialize_conflict_resolution
from app.core.errors import DomainError


def _orphan_kb() -> dict:
    """Prod-shaped orphan: conflict on reporting_period.end; siblings only."""
    return {
        "reconciler_agent": {"status": "ok"},
        "facts": {
            "reporting_period.end_formal": {
                "value": "2025-10-14",
                "semantic_label": "Formal end",
                "source_document_id": "doc-award",
                "source_label": "02_FCDO_BridgeLight_Award_Letter.docx",
                "provenance": {"excerpt": "to 14 October 2025"},
                "coverage": "single_source",
                "verification_status": "reconciled",
            },
            "reporting_period.end_inception_call": {
                "value": None,
                "semantic_label": "Inception end",
                "source_document_id": "doc-award",
                "source_label": "02_FCDO_BridgeLight_Award_Letter.docx",
                "provenance": {"excerpt": "October to September"},
                "coverage": "single_source",
                "verification_status": "reconciled",
            },
        },
        "conflicts": [
            {
                "fact_key": "reporting_period.end",
                "conflict_type": "VALUE_MISMATCH",
                "annotation": "internal: reporting_period.end",
                "resolved_value": None,
                "resolved_at": None,
                "values": [
                    {
                        "value": "2025-10-14",
                        "unit": None,
                        "source_document_id": "doc-award",
                        "source_label": "02_FCDO_BridgeLight_Award_Letter.docx",
                        "provenance": {"excerpt": "to 14 October 2025"},
                    },
                    {
                        "value": None,
                        "unit": None,
                        "source_document_id": "doc-award",
                        "source_label": "02_FCDO_BridgeLight_Award_Letter.docx",
                        "provenance": {"excerpt": "October to September"},
                    },
                ],
            }
        ],
    }


def test_orphan_shape_normalized_creates_stub_and_marks_exact_siblings(caplog):
    kb = _orphan_kb()
    assert "reporting_period.end" not in kb["facts"]
    with caplog.at_level(logging.WARNING, logger="reports.knowledge.conflict_integrity"):
        ensure_conflicts_materializable(
            kb, donor_report_id="cb090edb-test", emit_log=True
        )

    stub = kb["facts"]["reporting_period.end"]
    assert stub["value"] is None
    assert stub["verification_status"] == "unverified"
    assert stub["confirmed"] is False
    assert stub["confirmed_by_user"] is False

    assert (
        kb["facts"]["reporting_period.end_formal"]["provenance_only_for"]
        == "reporting_period.end"
    )
    assert (
        kb["facts"]["reporting_period.end_inception_call"]["provenance_only_for"]
        == "reporting_period.end"
    )

    events = kb["agent_trace"]["conflict_integrity_repairs"]
    assert len(events) == 1
    assert events[0]["conflict_key"] == "reporting_period.end"
    assert events[0]["created_canonical_stub"] is True
    assert set(events[0]["provenance_only_fact_keys"]) == {
        "reporting_period.end_formal",
        "reporting_period.end_inception_call",
    }
    assert "conflict_integrity_orphan_repaired" in caplog.text


def test_unrelated_fact_not_marked_provenance_only():
    kb = _orphan_kb()
    kb["facts"]["grant_period.end"] = {
        "value": "2026-10-14",
        "semantic_label": "Programme end",
        "source_document_id": "doc-award",
        "source_label": "02_FCDO_BridgeLight_Award_Letter.docx",
        "provenance": {"excerpt": "programme ends"},
        "coverage": "single_source",
        "verification_status": "reconciled",
    }
    ensure_conflicts_materializable(kb, donor_report_id="x", emit_log=False)
    assert "provenance_only_for" not in kb["facts"]["grant_period.end"]


def test_inexact_sibling_not_marked():
    kb = _orphan_kb()
    kb["facts"]["reporting_period.end_other"] = {
        "value": "2025-09-30",  # does not match either candidate value
        "semantic_label": "Other",
        "source_document_id": "doc-award",
        "source_label": "02_FCDO_BridgeLight_Award_Letter.docx",
        "provenance": {"excerpt": "other"},
        "coverage": "single_source",
        "verification_status": "reconciled",
    }
    ensure_conflicts_materializable(kb, donor_report_id="x", emit_log=False)
    assert "provenance_only_for" not in kb["facts"]["reporting_period.end_other"]


def test_repaired_orphan_resolves_concrete_and_explicit():
    kb = _orphan_kb()
    ensure_conflicts_materializable(kb, donor_report_id="x", emit_log=False)

    materialize_conflict_resolution(
        kb,
        fact_key="reporting_period.end",
        resolved_value="2025-10-14",
        resolved_at_iso="2026-07-19T12:00:00+00:00",
    )
    fact = kb["facts"]["reporting_period.end"]
    assert fact["value"] == "2025-10-14"
    assert fact["source_document_id"] == "doc-award"
    assert fact["confirmed_by_user"] is True
    assert fact["confirmed"] is True
    assert is_fact_citable(fact, gate1_confirmed_at="2026-07-19T12:00:00+00:00")
    assert not is_fact_citable(
        kb["facts"]["reporting_period.end_formal"],
        gate1_confirmed_at="2026-07-19T12:00:00+00:00",
    )

    kb2 = _orphan_kb()
    ensure_conflicts_materializable(kb2, donor_report_id="x", emit_log=False)
    materialize_conflict_resolution(
        kb2,
        fact_key="reporting_period.end",
        resolved_value="2025-09-30",
        resolved_at_iso="2026-07-19T12:00:00+00:00",
    )
    fact2 = kb2["facts"]["reporting_period.end"]
    assert fact2["value"] == "2025-09-30"
    assert fact2["source_document_id"] == "owner-attested"
    assert fact2["confirmed_by_user"] is True


def test_null_and_blank_resolved_value_rejected():
    kb = _orphan_kb()
    ensure_conflicts_materializable(kb, donor_report_id="x", emit_log=False)
    for bad in (None, "", "   "):
        try:
            materialize_conflict_resolution(
                kb,
                fact_key="reporting_period.end",
                resolved_value=bad,
                resolved_at_iso="2026-07-19T12:00:00+00:00",
            )
            raise AssertionError(f"expected DomainError for {bad!r}")
        except DomainError as exc:
            assert exc.error_code == "KB_CONFLICT_RESOLUTION_VALUE_REQUIRED"
            assert exc.status_code == 422


def test_missing_fact_guard_still_strict_without_normalizer():
    """Anti-bent-ruler: PATCH moat unchanged — orphan without stub still 422."""
    kb = _orphan_kb()
    try:
        materialize_conflict_resolution(
            kb,
            fact_key="reporting_period.end",
            resolved_value="2025-10-14",
            resolved_at_iso="2026-07-19T12:00:00+00:00",
        )
        raise AssertionError("expected missing-fact DomainError")
    except DomainError as exc:
        assert exc.error_code == "KB_PATCH_VALIDATION_FAILED"
        assert "no matching fact entry" in exc.message
