from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.reports.agents.knowledge_bank_reconciler import (
    AGENT_NAME,
    DEGRADED_RECONCILIATION_TIMEOUT,
    envelope_to_knowledge_bank_json,
    reconcile_from_fixture,
)
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    ConflictValueEntry,
    KnowledgeBankConflict,
    KnowledgeBankReconciliationOutput,
    KnowledgeProvenance,
    validate_e1_knowledge_bank as validate_kb,
)
from app.reports.services.knowledge_bank_reconciliation_service import (
    reconcile_and_persist,
)
from tests.reconciliation_grading import (
    assert_no_spurious_conflicts,
    grade_knowledge_bank,
    stability_fingerprint,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "reconciler"
MANIFEST = FIXTURES / "inputs" / "fcdo_bridgelight_documents.json"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_reconciliation_answer_key.json"


def _load_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


def _prov(excerpt: str, **kwargs) -> dict:
    return {"excerpt": excerpt, **kwargs}


def _fcdo_mock_llm_response() -> dict:
    """Deliberately wrong fact_key strings — graders locate by value + source only."""
    key = _load_key()
    ids = key["document_ids"]
    return {
        "facts": [
            {
                "fact_key": "ZZZ_NOT_IN_ANSWER_KEY_TARGET_CORROBORATED",
                "value": "1200",
                "unit": "number",
                "semantic_label": "OP1.1 girls re-enrolled target (corroborated)",
                "coverage": "agreed",
                "source_document_id": ids["proposal"],
                "source_label": "fcdo_bridgelight_proposal.md",
                "provenance": _prov(
                    "Number of out-of-school or at-risk girls re-enrolled "
                    "or newly retained through support package"
                ),
                "interpretation_note": (
                    f"Corroborated by indicator sheet ({ids['indicator_data']}): "
                    "Girls re-enrolled to formal education target 1200."
                ),
            },
            {
                "fact_key": "ZZZ_NOT_IN_ANSWER_KEY_ACTUAL_SHEET",
                "value": "985",
                "unit": "number",
                "semantic_label": "OP1.1 girls re-enrolled actual (indicator sheet)",
                "coverage": "single_source",
                "source_document_id": ids["indicator_data"],
                "source_label": "fcdo_bridgelight_indicator_data.xlsx",
                "provenance": _prov("985"),
                "interpretation_note": "Measured achievement — not the planned target.",
            },
        ],
        "conflicts": [
            {
                "fact_key": "ZZZ_WRONG_CASE1_CONFLICT_KEY",
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "1240000",
                        "unit": "GBP",
                        "source_document_id": ids["grant_letter"],
                        "source_label": "fcdo_bridgelight_award_letter.md",
                        "provenance": _prov("approved FCDO contribution is GBP 1,240,000"),
                    },
                    {
                        "value": "1240000",
                        "unit": "GBP",
                        "source_document_id": ids["indicator_data"],
                        "source_label": "fcdo_bridgelight_indicator_data.xlsx",
                        "provenance": _prov("Total programme budget"),
                    },
                    {
                        "value": "1184000",
                        "unit": "GBP",
                        "source_document_id": ids["synthetic_same_field"],
                        "source_label": "fcdo_amended_budget_schedule.xlsx",
                        "provenance": _prov("Total approved programme budget (contract)"),
                    },
                ],
                "annotation": "Same-field approved budget — not resolved at E1.",
            },
            {
                "fact_key": "ZZZ_WRONG_CASE3_CONFLICT_KEY",
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "40",
                        "unit": "number",
                        "source_document_id": ids["proposal"],
                        "source_label": "fcdo_bridgelight_proposal.md",
                        "provenance": _prov(
                            "Number of separate, lockable girls latrine stances "
                            "rehabilitated or newly functional"
                        ),
                    },
                    {
                        "value": "24",
                        "unit": "number",
                        "source_document_id": ids["indicator_data"],
                        "source_label": "fcdo_bridgelight_indicator_data.xlsx",
                        "provenance": _prov("Latrine stances rehabilitated"),
                    },
                ],
                "annotation": "Proposal target vs logframe revision — human must confirm.",
            },
        ],
        "unreadable_sources": [],
        "confidence": 0.9,
    }


def _mock_query_factory(payload: dict):
    from claude_agent_sdk import ResultMessage

    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield ResultMessage(
            subtype="success",
            duration_ms=500,
            duration_api_ms=480,
            is_error=False,
            num_turns=2,
            session_id="test-session",
            structured_output=payload,
        )

    return _query


@pytest.mark.asyncio
async def test_fcdo_fixture_reconciliation_grades():
    result = await reconcile_from_fixture(
        MANIFEST,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    kb = envelope_to_knowledge_bank_json(result.envelope)
    key = _load_key()
    errors = grade_knowledge_bank(kb, key)
    assert errors == [], "\n".join(errors)
    assert kb["reconciliation_outcome"] == "complete"
    assert len(kb.get("unreadable_sources") or []) >= 1


def test_case1_grader_requires_all_corroborating_sources():
    """Partial corroboration (grant letter only) must fail — not widened to OR."""
    key = _load_key()
    ids = key["document_ids"]
    kb = {
        "reconciliation_outcome": "complete",
        "facts": {},
        "conflicts": [
            {
                "fact_key": "budget",
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "1240000",
                        "source_document_id": ids["grant_letter"],
                        "source_label": "award",
                        "provenance": _prov("approved FCDO contribution is GBP 1,240,000"),
                    },
                    {
                        "value": "1184000",
                        "source_document_id": ids["synthetic_same_field"],
                        "source_label": "amended",
                        "provenance": _prov("contract budget"),
                    },
                ],
            }
        ],
        "unreadable_sources": [
            {
                "source_document_id": ids["unreadable"],
                "source_label": "scan.pdf",
                "code": "UNREADABLE_DOCUMENT_LOW_CONTENT",
                "message": "low content",
            }
        ],
    }
    errors = grade_knowledge_bank(kb, key)
    assert any("case1" in e for e in errors)


def test_no_spurious_conflicts_rejects_single_distinct_value():
    kb = {
        "facts": {},
        "conflicts": [
            {
                "fact_key": "phantom",
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "22",
                        "source_document_id": "a",
                        "source_label": "sheet",
                        "provenance": _prov("22"),
                    }
                ],
            }
        ],
    }
    with pytest.raises(AssertionError, match="need >= 2"):
        assert_no_spurious_conflicts(kb)


def test_no_spurious_conflicts_rejects_one_distinct_value_two_entries():
    kb = {
        "facts": {},
        "conflicts": [
            {
                "fact_key": "phantom",
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "22",
                        "source_document_id": "a",
                        "source_label": "a",
                        "provenance": _prov("22"),
                    },
                    {
                        "value": "22",
                        "source_document_id": "b",
                        "source_label": "b",
                        "provenance": _prov("also 22"),
                    },
                ],
            }
        ],
    }
    with pytest.raises(AssertionError, match="only one distinct"):
        assert_no_spurious_conflicts(kb)


def test_no_spurious_conflicts_rejects_blank_party():
    kb = {
        "facts": {},
        "conflicts": [
            {
                "fact_key": "phantom",
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "",
                        "source_document_id": "a",
                        "source_label": "a",
                        "provenance": _prov("missing"),
                    },
                    {
                        "value": "22",
                        "source_document_id": "b",
                        "source_label": "b",
                        "provenance": _prov("22"),
                    },
                ],
            }
        ],
    }
    with pytest.raises(AssertionError, match="blank"):
        assert_no_spurious_conflicts(kb)


def test_no_spurious_conflicts_passes_case1_corroboration_shape():
    key = _load_key()
    ids = key["document_ids"]
    kb = {
        "facts": {},
        "conflicts": [
            {
                "fact_key": "budget",
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "1240000",
                        "source_document_id": ids["grant_letter"],
                        "source_label": "award",
                        "provenance": _prov("award amount"),
                    },
                    {
                        "value": "1240000",
                        "source_document_id": ids["indicator_data"],
                        "source_label": "sheet",
                        "provenance": _prov("programme budget"),
                    },
                    {
                        "value": "1184000",
                        "source_document_id": ids["synthetic_same_field"],
                        "source_label": "amended",
                        "provenance": _prov("contract budget"),
                    },
                ],
            }
        ],
    }
    assert_no_spurious_conflicts(kb)


@pytest.mark.asyncio
async def test_validator_rejects_resolved_conflict():
    kb = KnowledgeBankReconciliationOutput(
        conflicts=[
            KnowledgeBankConflict(
                fact_key="x",
                conflict_type="VALUE_MISMATCH",
                values=[
                    ConflictValueEntry(
                        value="1",
                        source_document_id="a",
                        source_label="a",
                        provenance=KnowledgeProvenance(excerpt="one"),
                    ),
                    ConflictValueEntry(
                        value="2",
                        source_document_id="b",
                        source_label="b",
                        provenance=KnowledgeProvenance(excerpt="two"),
                    ),
                ],
                resolved_value="1",
            )
        ]
    )
    errors = validate_kb(kb)
    assert any("resolved_value" in e for e in errors)


@pytest.mark.asyncio
async def test_timeout_degraded_no_raise():
    import asyncio

    from app.reports.agents import knowledge_bank_reconciler as mod
    from app.reports.reconciliation.input_builder import (
        build_reconciliation_bundle_from_fixture,
    )

    async def _slow(*args, **kwargs):
        await asyncio.sleep(5)
        if False:  # pragma: no cover
            yield None

    bundle = build_reconciliation_bundle_from_fixture(MANIFEST)
    result = await mod.reconcile_bundle(
        bundle,
        query_fn=_slow,
        per_attempt_timeout_seconds=0.01,
    )
    assert result.envelope.structured.reconciliation_outcome == "degraded"
    assert result.envelope.error == DEGRADED_RECONCILIATION_TIMEOUT


@pytest.mark.asyncio
async def test_stability_fingerprint_deterministic():
    kb = envelope_to_knowledge_bank_json(
        (await reconcile_from_fixture(
            MANIFEST,
            query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
        )).envelope
    )
    fp1 = stability_fingerprint(kb)
    fp2 = stability_fingerprint(kb)
    assert fp1 == fp2


@pytest.mark.asyncio
async def test_service_persists_complete(monkeypatch):
    import app.reports.services.knowledge_bank_reconciliation_service as svc

    db = MagicMock()
    report_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.knowledge_bank_json: dict = {}

    report = Report()
    db.get.return_value = report
    db.query.return_value.filter.return_value.all.return_value = []

    mock_result = await reconcile_from_fixture(
        MANIFEST,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )

    async def _stub(docs, **kwargs):
        return mock_result

    monkeypatch.setattr(svc, "reconcile_documents", _stub)
    out = await reconcile_and_persist(db, report_id)
    assert report.knowledge_bank_json.get("reconciler_agent") == AGENT_NAME
    assert out.envelope.structured.reconciliation_outcome == "complete"


def test_input_builder_unreadable_from_manifest():
    from app.reports.reconciliation.input_builder import (
        build_reconciliation_bundle_from_fixture,
    )

    bundle = build_reconciliation_bundle_from_fixture(MANIFEST)
    assert len(bundle.unreadable_sources) == 1
    assert bundle.unreadable_sources[0].code == "UNREADABLE_DOCUMENT_LOW_CONTENT"
