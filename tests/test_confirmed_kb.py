"""Tests for P1-3 confirmed_kb citability fence."""

from __future__ import annotations

import uuid

from app.reports.knowledge.confirmed_kb import (
    build_confirmed_kb_view,
    count_unverified_excluded,
    effective_verification_status,
    filter_citable_facts,
    is_evidence_ref_citable,
    is_fact_citable,
    non_citable_evidence_refs,
)


def _fact(*, status: str, confirmed_by_user: bool = False, value: int = 1) -> dict:
    return {
        "value": value,
        "verification_status": status,
        "confirmed_by_user": confirmed_by_user,
        "source_document_id": str(uuid.uuid4()),
        "source_label": "doc",
        "semantic_label": "label",
        "provenance": {"excerpt": "x"},
    }


def test_missing_verification_status_is_unverified():
    assert effective_verification_status({}) == "unverified"


def test_reconciled_citable_after_gate1_stamp():
    fact = _fact(status="reconciled")
    assert is_fact_citable(fact, gate1_confirmed_at="2026-01-01T00:00:00+00:00")
    assert not is_fact_citable(fact, gate1_confirmed_at=None)


def test_unverified_not_citable_until_promoted():
    fact = _fact(status="unverified")
    gate = "2026-01-01T00:00:00+00:00"
    assert not is_fact_citable(fact, gate1_confirmed_at=gate)
    fact["confirmed_by_user"] = True
    assert is_fact_citable(fact, gate1_confirmed_at=gate)


def test_filter_citable_excludes_unpromoted_unverified():
    kb = {
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
        "facts": {
            "good": _fact(status="reconciled"),
            "bad": _fact(status="unverified"),
        },
    }
    citable = filter_citable_facts(kb)
    assert "good" in citable
    assert "bad" not in citable
    assert count_unverified_excluded(kb) == 1


def test_non_citable_evidence_ref_detection():
    kb = {
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
        "facts": {
            "degraded_pass_through:x:indicators.op1": _fact(status="unverified"),
            "indicators.op1": _fact(status="reconciled", value=684),
        },
    }
    blocked = non_citable_evidence_refs(
        ["fact:degraded_pass_through:x:indicators.op1", "fact:indicators.op1"],
        kb,
    )
    assert blocked == ["fact:degraded_pass_through:x:indicators.op1"]
    assert is_evidence_ref_citable("fact:indicators.op1", kb)


def test_build_confirmed_kb_view():
    kb = {
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
        "facts": {"a": _fact(status="reconciled")},
        "gap_answers": {},
        "conflicts": [],
    }
    view = build_confirmed_kb_view(kb)
    assert list(view.facts.keys()) == ["a"]
