from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.reports.agents.grant_terms_extractor import (
    AGENT_NAME,
    DEGRADED_EXTRACTION_TIMEOUT,
    MAX_EXTRACTION_ATTEMPTS,
    MAX_TURNS,
    GrantTermsExtractorError,
    extract_grant_terms_from_path,
    extract_grant_terms_text,
)
from app.reports.extraction.docling_content_guard import (
    UNREADABLE_DOCUMENT_LOW_CONTENT,
)
from app.reports.schemas.grant_terms_extraction_v1 import (
    GrantTermsExtractedEnvelope,
    GrantTermsExtractionOutput,
)
from app.reports.models.enums import ExtractionStatus
from app.reports.services.grant_terms_extraction_service import (
    GrantTermsExtractionServiceError,
    extract_and_persist_grant_terms,
)
from tests.grant_terms_grading import (
    assert_answer_key_present,
    assert_no_budget_drift,
    assert_reporting_period_conflict_intact,
    grade_extraction_output,
)
from claude_agent_sdk import ResultMessage

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "grant_terms_extractor"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_award_letter_answer_key.json"
FCDO_TEXT = FIXTURES / "fcdo_bridgelight_award_letter.md"
RECORDED_EXTRACTION = (
    FIXTURES / "recorded" / "fcdo_bridgelight_recorded_extraction.json"
)


def _result_message(payload: dict) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=200,
        duration_api_ms=180,
        is_error=False,
        num_turns=3,
        session_id="test-session",
        structured_output=payload,
        usage={"input_tokens": 100, "output_tokens": 800},
    )


def _mock_query_factory(response: dict):
    async def _mock_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(response)

    return _mock_query


def _load_answer_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


def _prov(excerpt: str, section: str = "Award Letter") -> dict:
    return {"excerpt": excerpt[:80], "section_label": section}


def _field(
    raw: str,
    normalized: str,
    *,
    excerpt: str | None = None,
) -> dict:
    return {
        "absent": False,
        "raw": raw,
        "normalized": normalized,
        "normalization_ambiguous": False,
        "provenance": _prov(excerpt or raw),
        "multi_value": False,
        "stated_values": [],
    }


def _absent_field() -> dict:
    return {
        "absent": True,
        "raw": None,
        "normalized": None,
        "normalization_ambiguous": False,
        "provenance": None,
        "multi_value": False,
        "stated_values": [],
    }


def _fcdo_mock_llm_response() -> dict:
    return {
        "confidence": 0.92,
        "funder": _field(
            "Foreign, Commonwealth & Development Office",
            "FCDO",
            excerpt="Foreign, Commonwealth & Development Office",
        ),
        "grant_reference": _field("MWI-EDU-AR-4471", "MWI-EDU-AR-4471"),
        "award_budget": {
            "amount": _field("GBP 1,240,000", "1240000", excerpt="GBP 1,240,000"),
            "currency": _field("GBP", "GBP"),
            "tranches": [],
        },
        "grant_period": {
            "start": _field("15 October 2024", "2024-10-15"),
            "end": _field("14 October 2026", "2026-10-14"),
        },
        "reporting_period": {
            "start": {
                "absent": False,
                "raw": None,
                "normalized": None,
                "normalization_ambiguous": False,
                "provenance": None,
                "multi_value": True,
                "stated_values": [
                    {
                        "raw": "15 October 2024 to 14 October 2025",
                        "normalized": "2024-10-15",
                        "normalization_ambiguous": False,
                        "provenance": _prov("15 October 2024 to 14 October 2025"),
                    },
                    {
                        "raw": "October to September",
                        "normalized": None,
                        "normalization_ambiguous": True,
                        "provenance": _prov("October to September"),
                    },
                ],
            },
            "end": _field("14 October 2025", "2025-10-14"),
        },
        "reporting_obligations": [
            {
                "report_type": "Annual Review",
                "frequency": "annual",
                "raw": "Annual Review narrative against the agreed results framework",
                "provenance": _prov("Annual Review narrative"),
            }
        ],
        "reporting_deadlines": [
            _field("21 November 2025", "2025-11-21", excerpt="21 November 2025"),
        ],
    }


@pytest.mark.asyncio
async def test_extract_empty_text_raises_stop():
    with pytest.raises(GrantTermsExtractorError) as exc:
        await extract_grant_terms_text("  ", query_fn=_mock_query_factory({}))
    assert exc.value.code == "STOP_EMPTY_INPUT"


@pytest.mark.asyncio
async def test_mock_grant_terms_persistence_envelope_shape():
    text = FCDO_TEXT.read_text(encoding="utf-8")
    result = await extract_grant_terms_text(
        text,
        filename="fcdo_bridgelight_award_letter.md",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert result.envelope.extractor_agent == AGENT_NAME
    assert result.envelope.structured.schema_version == "1.0.0"
    assert result.envelope.structured.extraction_outcome == "complete"


@pytest.mark.asyncio
async def test_answer_key_all_present_terms_captured():
    key = _load_answer_key()
    result = await extract_grant_terms_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert_answer_key_present(result.envelope.structured, key)
    for item in (
        result.envelope.structured.reporting_obligations
        + [result.envelope.structured.funder, result.envelope.structured.grant_reference]
    ):
        if hasattr(item, "provenance") and item.provenance:
            assert item.provenance.excerpt


@pytest.mark.asyncio
async def test_answer_key_absent_terms_marked_absent():
    key = _load_answer_key()
    result = await extract_grant_terms_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert "award_budget.tranches" in key["expected_absent_fields"]
    assert len(result.envelope.structured.award_budget.tranches) == 0


@pytest.mark.asyncio
async def test_planted_conflict_reporting_period_intra_doc():
    key = _load_answer_key()
    planted = key["planted_conflicts"]["conflict_3_reporting_period_intra_doc"]
    result = await extract_grant_terms_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert_reporting_period_conflict_intact(
        result.envelope.structured.reporting_period,
        planted,
    )


@pytest.mark.asyncio
async def test_planted_conflict_budget_no_cross_doc_drift():
    key = _load_answer_key()
    result = await extract_grant_terms_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert_no_budget_drift(result.envelope.structured, key)


@pytest.mark.asyncio
async def test_timeout_one_retry_then_degraded_no_raise():
    call_count = 0

    async def _slow_query(*, prompt: str, options=None):
        nonlocal call_count
        _ = prompt
        _ = options
        call_count += 1
        await asyncio.sleep(5)
        yield _result_message(_fcdo_mock_llm_response())

    result = await extract_grant_terms_text(
        "sample text",
        query_fn=_slow_query,
        per_attempt_timeout_seconds=0.01,
    )
    assert call_count == MAX_EXTRACTION_ATTEMPTS
    assert result.envelope.structured.extraction_outcome == "degraded"
    assert result.envelope.error == DEGRADED_EXTRACTION_TIMEOUT
    assert result.envelope.agent_trace is not None
    assert result.envelope.agent_trace.attempt_count == MAX_EXTRACTION_ATTEMPTS
    assert result.envelope.agent_trace.degraded_code == DEGRADED_EXTRACTION_TIMEOUT


@pytest.mark.asyncio
async def test_service_persists_degraded_without_raise():
    db = MagicMock()
    doc_id = uuid.uuid4()

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "grant_letter"
            self.original_filename = "award.md"
            self.extracted_json: dict = {}
            self.extraction_status = ExtractionStatus.PENDING.value

    doc = Doc()
    db.get.return_value = doc

    async def _slow_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        await asyncio.sleep(5)
        yield _result_message(_fcdo_mock_llm_response())

    result = await extract_and_persist_grant_terms(
        db,
        doc_id,
        "sample text",
        query_fn=_slow_query,
        per_attempt_timeout_seconds=0.01,
    )
    assert doc.extraction_status == ExtractionStatus.FAILED.value
    assert doc.extracted_json["structured"]["extraction_outcome"] == "degraded"
    assert doc.extracted_json["error"] == DEGRADED_EXTRACTION_TIMEOUT
    assert result.envelope.structured.extraction_outcome == "degraded"


def test_build_agent_options_bounded():
    from app.reports.agents.grant_terms_extractor import build_agent_options

    options = build_agent_options()
    assert options.max_turns == MAX_TURNS
    assert "Read" in options.disallowed_tools
    assert options.output_format["type"] == "json_schema"


@pytest.mark.asyncio
async def test_service_wrong_classification_raises():
    db = MagicMock()
    doc = SimpleNamespace(
        id=uuid.uuid4(),
        classification="proposal",
        original_filename="proposal.pdf",
        extracted_json={},
        extraction_status=ExtractionStatus.PENDING.value,
    )
    db.get.return_value = doc

    with pytest.raises(GrantTermsExtractionServiceError) as exc:
        await extract_and_persist_grant_terms(
            db, doc.id, "text", query_fn=_mock_query_factory({})
        )
    assert exc.value.code == "STOP_WRONG_CLASSIFICATION"


@pytest.mark.asyncio
async def test_service_persists_complete_and_overwrites_on_rerun():
    db = MagicMock()
    doc_id = uuid.uuid4()
    text = FCDO_TEXT.read_text(encoding="utf-8")

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "grant_letter"
            self.original_filename = "fcdo_bridgelight_award_letter.md"
            self.extracted_json: dict = {}
            self.extraction_status = ExtractionStatus.PENDING.value

    doc = Doc()
    db.get.return_value = doc

    await extract_and_persist_grant_terms(
        db, doc_id, text, query_fn=_mock_query_factory(_fcdo_mock_llm_response())
    )
    assert doc.extraction_status == ExtractionStatus.COMPLETE.value
    assert doc.extracted_json["extractor_agent"] == AGENT_NAME

    second = _fcdo_mock_llm_response()
    second["confidence"] = 0.88
    await extract_and_persist_grant_terms(
        db, doc_id, text, query_fn=_mock_query_factory(second)
    )
    assert doc.extracted_json["confidence"] == 0.88


@pytest.mark.asyncio
async def test_envelope_round_trip_json():
    result = await extract_grant_terms_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    data = result.envelope.model_dump(mode="json")
    assert data["extractor_agent"] == AGENT_NAME
    assert data["structured"]["schema_version"] == "1.0.0"


def test_recorded_fcdo_live_extraction_matches_answer_key_contract():
    """Recorded from a real haiku extraction — fails if live grant-terms capture regresses."""
    assert RECORDED_EXTRACTION.is_file(), (
        f"Missing recorded extraction at {RECORDED_EXTRACTION}. "
        "Generate via correctness + stability gate: python scripts/grant_terms_gate.py"
    )
    key = _load_answer_key()
    payload = json.loads(RECORDED_EXTRACTION.read_text(encoding="utf-8"))
    structured = GrantTermsExtractionOutput.model_validate(payload["structured"])
    grade_extraction_output(structured, key)


@pytest.mark.asyncio
async def test_from_path_unreadable_skips_llm(monkeypatch, tmp_path: Path):
    doc_path = tmp_path / "scan.pdf"
    doc_path.write_bytes(b"%PDF-1.4")

    def fake_extract(path: Path):
        return {
            "text": "# Scanned\n",
            "metadata": {"source_path": str(path)},
            "conversion_status": "failure",
        }

    llm_called = False

    async def _no_query(*args, **kwargs):
        nonlocal llm_called
        llm_called = True
        raise AssertionError("LLM must not run for unreadable intake")

    monkeypatch.setattr(
        "app.reports.extraction.docling_adapter.extract_text_from_path",
        fake_extract,
    )

    result = await extract_grant_terms_from_path(doc_path, query_fn=_no_query)
    assert llm_called is False
    assert result.envelope.structured.extraction_outcome == "unreadable"
    assert result.envelope.error == UNREADABLE_DOCUMENT_LOW_CONTENT
    assert result.envelope.agent_trace.unreadable_code == UNREADABLE_DOCUMENT_LOW_CONTENT


@pytest.mark.asyncio
async def test_from_path_short_valid_proceeds_to_llm(monkeypatch):
    intake_fixtures = Path(__file__).resolve().parent / "fixtures" / "docling_intake"
    text = (intake_fixtures / "short_valid_grant_letter.md").read_text(encoding="utf-8")
    doc_path = intake_fixtures / "short_valid_grant_letter.md"

    def fake_extract(path: Path):
        return {
            "text": text,
            "metadata": {"source_path": str(path)},
            "conversion_status": "success",
        }

    monkeypatch.setattr(
        "app.reports.extraction.docling_adapter.extract_text_from_path",
        fake_extract,
    )

    result = await extract_grant_terms_from_path(
        doc_path,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert result.envelope.structured.extraction_outcome == "complete"


@pytest.mark.asyncio
async def test_service_persists_unreadable_without_raise(monkeypatch):
    from app.reports.agents.grant_terms_extractor import (
        _build_unreadable_result,
        compute_content_hash,
    )

    db = MagicMock()
    doc_id = uuid.uuid4()

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "grant_letter"
            self.original_filename = "scan.pdf"
            self.extracted_json: dict = {}
            self.extraction_status = ExtractionStatus.PENDING.value

    doc = Doc()
    db.get.return_value = doc

    unreadable_result = _build_unreadable_result(
        content_hash=compute_content_hash("tiny"),
    )

    async def _stub(*args, **kwargs):
        return unreadable_result

    monkeypatch.setattr(
        "app.reports.services.grant_terms_extraction_service.extract_grant_terms_text",
        _stub,
    )

    out = await extract_and_persist_grant_terms(db, doc_id, "ignored")
    assert doc.extraction_status == ExtractionStatus.FAILED.value
    assert doc.extracted_json["structured"]["extraction_outcome"] == "unreadable"
    assert doc.extracted_json["error"] == UNREADABLE_DOCUMENT_LOW_CONTENT
    assert out.envelope.structured.extraction_outcome == "unreadable"
