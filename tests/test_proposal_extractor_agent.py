from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.reports.agents.proposal_extractor import (
    AGENT_NAME,
    DEGRADED_EXTRACTION_TIMEOUT,
    MAX_EXTRACTION_ATTEMPTS,
    MAX_TURNS,
    ProposalExtractorError,
    _build_unreadable_result,
    compute_content_hash,
    extract_proposal_from_path,
    extract_proposal_text,
)
from app.reports.extraction.docling_content_guard import (
    UNREADABLE_DOCUMENT_LOW_CONTENT,
)
from app.reports.models.enums import ExtractionStatus
from app.reports.schemas.proposal_extraction_v1 import ProposalExtractedEnvelope
from app.reports.services.proposal_extraction_service import (
    ProposalExtractionServiceError,
    extract_and_persist_proposal,
)
from claude_agent_sdk import ResultMessage

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "proposal_extractor"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_proposal_answer_key.json"
FCDO_TEXT = FIXTURES / "fcdo_bridgelight_proposal.md"
RECORDED_EXTRACTION = (
    FIXTURES / "recorded" / "fcdo_bridgelight_recorded_extraction.json"
)
TARGETLESS_KEY = "equity_support_reach_qualitative"
TARGETLESS_LABEL_PHRASE = "share of support reaching girls with disabilities"


def _result_message(payload: dict) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=200,
        duration_api_ms=180,
        is_error=False,
        num_turns=3,
        session_id="test-session",
        structured_output=payload,
        usage={"input_tokens": 100, "output_tokens": 400},
    )


def _mock_query_factory(response: dict):
    async def _mock_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(response)

    return _mock_query


def _load_answer_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


def _fcdo_mock_llm_response() -> dict:
    """Minimal mock covering answer-key keys and absent-target indicator."""
    return {
        "confidence": 0.91,
        "objectives": [
            {
                "objective_key": "impact_girls_complete_basic_education",
                "label": "Adolescent girls in Machinga and Mangochi complete basic education in safer, more supportive learning environments.",
                "level": "impact",
                "status": "extracted",
                "provenance": {
                    "excerpt": "Adolescent girls in Machinga and Mangochi complete basic education",
                    "section_label": "4. Impact, outcome and outputs",
                },
            },
            {
                "objective_key": "outcome_improved_retention_attendance_2026",
                "label": "By September 2026, adolescent girls targeted by the programme demonstrate improved school retention, attendance and learning continuity",
                "level": "outcome",
                "status": "extracted",
                "provenance": {
                    "excerpt": "By September 2026, adolescent girls targeted by the programme",
                    "section_label": "4. Impact, outcome and outputs",
                },
            },
        ],
        "activities": [
            {
                "activity_key": key,
                "label": key.replace("_", " "),
                "status": "extracted",
                "provenance": {"excerpt": key, "section_label": "6. Activities"},
            }
            for key in _load_answer_key()["expected_activity_keys"]
        ],
        "indicators": _build_indicator_mocks(),
    }


def _build_indicator_mocks() -> list[dict]:
    key = _load_answer_key()
    rows: list[dict] = []
    for indicator_key in key["expected_indicator_keys"]:
        rows.append(
            {
                "indicator_key": indicator_key,
                "label": indicator_key.replace("_", " "),
                "level": "outcome" if indicator_key.startswith("ocm") else "output",
                "baseline": "0",
                "milestone": "1",
                "target": {"value": "2", "unit": None, "absent": False},
                "status": "extracted",
                "provenance": {
                    "excerpt": indicator_key,
                    "section_label": "Indicators",
                },
            }
        )
    rows.append(
        {
            "indicator_key": "equity_support_reach_qualitative",
            "label": "Share of support reaching girls with disabilities, ultra-poor households and girls previously out of school",
            "level": "outcome",
            "baseline": None,
            "milestone": None,
            "target": {"value": None, "unit": None, "absent": True},
            "status": "extracted",
            "provenance": {
                "excerpt": "Equity will be assessed through the share of support reaching",
                "section_label": "8. Value for Money",
            },
        }
    )
    return rows


@pytest.mark.asyncio
async def test_extract_empty_text_raises_stop():
    with pytest.raises(ProposalExtractorError) as exc:
        await extract_proposal_text("  ", query_fn=_mock_query_factory({}))
    assert exc.value.code == "STOP_EMPTY_INPUT"


@pytest.mark.asyncio
async def test_timeout_one_retry_then_degraded_no_raise():
    call_count = 0

    async def _slow_query(*, prompt: str, options=None):
        nonlocal call_count
        _ = prompt
        _ = options
        call_count += 1
        await __import__("asyncio").sleep(5)
        yield _result_message(_fcdo_mock_llm_response())

    result = await extract_proposal_text(
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
    assert len(result.envelope.agent_trace.attempt_traces) == MAX_EXTRACTION_ATTEMPTS
    for row in result.envelope.agent_trace.attempt_traces:
        assert row.outcome == "timeout"
        assert row.wall_clock_ms >= 0
        assert row.timeout_ceiling_seconds == 0.01


@pytest.mark.asyncio
async def test_service_persists_degraded_without_raise():
    db = MagicMock()
    doc_id = uuid.uuid4()

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "proposal"
            self.original_filename = "proposal.docx"
            self.extracted_json: dict = {}
            self.extraction_status = ExtractionStatus.PENDING.value

    doc = Doc()
    db.get.return_value = doc

    async def _slow_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        await __import__("asyncio").sleep(5)
        yield _result_message(_fcdo_mock_llm_response())

    result = await extract_and_persist_proposal(
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


@pytest.mark.asyncio
async def test_fcdo_fixture_extracts_structured_output():
    text = FCDO_TEXT.read_text(encoding="utf-8")
    result = await extract_proposal_text(
        text,
        filename="fcdo_bridgelight_proposal.md",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    structured = result.envelope.structured
    assert structured.schema_version == "1.0.0"
    assert structured.extraction_outcome in ("complete", "partial")
    assert result.envelope.extractor_agent == AGENT_NAME
    assert result.envelope.confidence == 0.91
    assert result.latency_ms == 200
    assert result.content_hash == compute_content_hash(text)


@pytest.mark.asyncio
async def test_mock_fcdo_persistence_answer_key_keys_present():
    """Mock hand-feeds LLM output — verifies mapping/persistence, not live extraction."""
    text = FCDO_TEXT.read_text(encoding="utf-8")
    key = _load_answer_key()
    result = await extract_proposal_text(
        text,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    obj_keys = {o.objective_key for o in result.envelope.structured.objectives}
    act_keys = {a.activity_key for a in result.envelope.structured.activities}
    ind_keys = {i.indicator_key for i in result.envelope.structured.indicators}

    for expected in key["expected_objective_keys"]:
        assert expected in obj_keys
    for expected in key["expected_activity_keys"]:
        assert expected in act_keys
    for expected in key["expected_indicator_keys"]:
        assert expected in ind_keys
    assert "equity_support_reach_qualitative" in ind_keys


@pytest.mark.asyncio
async def test_mock_indicator_with_absent_target_not_guessed():
    result = await extract_proposal_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    absent = next(
        i
        for i in result.envelope.structured.indicators
        if i.indicator_key == "equity_support_reach_qualitative"
    )
    assert absent.target.absent is True
    assert absent.target.value is None


@pytest.mark.asyncio
async def test_provenance_on_every_item():
    result = await extract_proposal_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    s = result.envelope.structured
    for item in list(s.objectives) + list(s.activities) + list(s.indicators):
        assert item.provenance.excerpt
        assert len(item.provenance.excerpt) > 0


@pytest.mark.asyncio
async def test_partial_extraction_outcome():
    partial = _fcdo_mock_llm_response()
    partial["indicators"][0]["status"] = "failed"
    partial["indicators"][0]["error_message"] = "Malformed row"
    result = await extract_proposal_text(
        "sample",
        query_fn=_mock_query_factory(partial),
    )
    assert result.envelope.structured.extraction_outcome == "partial"
    assert result.envelope.structured.summary.failed >= 1
    assert result.envelope.structured.summary.succeeded >= 1


def test_build_agent_options_bounded():
    from app.reports.agents.proposal_extractor import build_agent_options

    options = build_agent_options()
    assert options.max_turns == MAX_TURNS
    assert "Read" in options.disallowed_tools
    assert options.output_format["type"] == "json_schema"


@pytest.mark.asyncio
async def test_service_wrong_classification_raises():
    db = MagicMock()
    doc = SimpleNamespace(
        id=uuid.uuid4(),
        classification="grant_letter",
        original_filename="letter.pdf",
        extracted_json={},
        extraction_status=ExtractionStatus.PENDING.value,
    )
    db.get.return_value = doc

    with pytest.raises(ProposalExtractionServiceError) as exc:
        await extract_and_persist_proposal(db, doc.id, "text", query_fn=_mock_query_factory({}))
    assert exc.value.code == "STOP_WRONG_CLASSIFICATION"


@pytest.mark.asyncio
async def test_service_persists_complete_and_overwrites_on_rerun():
    db = MagicMock()
    doc_id = uuid.uuid4()
    text = FCDO_TEXT.read_text(encoding="utf-8")

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "proposal"
            self.original_filename = "fcdo_bridgelight_proposal.md"
            self.extracted_json: dict = {}
            self.extraction_status = ExtractionStatus.PENDING.value

    doc = Doc()
    db.get.return_value = doc

    await extract_and_persist_proposal(
        db, doc_id, text, query_fn=_mock_query_factory(_fcdo_mock_llm_response())
    )
    assert doc.extraction_status == ExtractionStatus.COMPLETE.value
    first = dict(doc.extracted_json)
    assert first["extractor_agent"] == AGENT_NAME
    assert first["structured"]["schema_version"] == "1.0.0"

    second_response = _fcdo_mock_llm_response()
    second_response["confidence"] = 0.88
    await extract_and_persist_proposal(
        db, doc_id, text, query_fn=_mock_query_factory(second_response)
    )
    assert doc.extracted_json["confidence"] == 0.88
    assert doc.extraction_status == ExtractionStatus.COMPLETE.value


@pytest.mark.asyncio
async def test_service_failed_rerun_preserves_prior_complete_extraction():
    db = MagicMock()
    doc_id = uuid.uuid4()
    text = "proposal body"

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "proposal"
            self.original_filename = "p.pdf"
            self.extracted_json = {
                "extractor_agent": AGENT_NAME,
                "structured": {"schema_version": "1.0.0", "objectives": []},
            }
            self.extraction_status = ExtractionStatus.COMPLETE.value

    doc = Doc()
    db.get.return_value = doc

    async def _failing_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        raise ProposalExtractorError("STOP_AGENT_ERROR", "simulated failure")
        yield _result_message({})  # pragma: no cover

    with pytest.raises(ProposalExtractorError):
        await extract_and_persist_proposal(db, doc_id, text, query_fn=_failing_query)

    assert doc.extraction_status == ExtractionStatus.FAILED.value
    assert doc.extracted_json["structured"]["schema_version"] == "1.0.0"
    assert "error" in doc.extracted_json


@pytest.mark.asyncio
async def test_envelope_round_trip_json():
    result = await extract_proposal_text(
        "sample",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    envelope = result.envelope
    data = envelope.model_dump(mode="json")
    assert data["extractor_agent"] == AGENT_NAME
    assert data["structured"]["schema_version"] == "1.0.0"


def test_recorded_fcdo_live_extraction_captures_targetless_equity_indicator():
    """Recorded from a real haiku extraction — fails if live targetless capture regresses."""
    assert RECORDED_EXTRACTION.is_file(), (
        f"Missing recorded extraction at {RECORDED_EXTRACTION}. "
        "Generate via live FCDO run after prompt fix."
    )
    payload = json.loads(RECORDED_EXTRACTION.read_text(encoding="utf-8"))
    structured = payload["structured"]
    indicators = structured["indicators"]
    key = _load_answer_key()

    objectives = structured["objectives"]
    assert len(objectives) == len(key["expected_objective_keys"])
    levels = {o["level"] for o in objectives}
    assert levels == {"impact", "outcome"}

    assert len(structured["activities"]) == len(key["expected_activity_keys"])

    with_targets = [i for i in indicators if not i["target"]["absent"]]
    assert len(with_targets) == len(key["expected_indicator_keys"])
    assert len(indicators) == len(key["expected_indicator_keys"]) + 1

    ind_by_key = {i["indicator_key"]: i for i in indicators}
    equity = ind_by_key.get(TARGETLESS_KEY)
    assert equity is not None, "equity_support_reach_qualitative missing from recorded run"
    assert TARGETLESS_LABEL_PHRASE.lower() in equity["label"].lower()
    assert equity["target"]["absent"] is True
    assert equity["target"]["value"] is None


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

    result = await extract_proposal_from_path(doc_path, query_fn=_no_query)
    assert llm_called is False
    assert result.envelope.structured.extraction_outcome == "unreadable"
    assert result.envelope.error == UNREADABLE_DOCUMENT_LOW_CONTENT


@pytest.mark.asyncio
async def test_service_persists_unreadable_without_raise(monkeypatch):
    db = MagicMock()
    doc_id = uuid.uuid4()

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "proposal"
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
        "app.reports.services.proposal_extraction_service.extract_proposal_text",
        _stub,
    )

    out = await extract_and_persist_proposal(db, doc_id, "ignored")
    assert doc.extraction_status == ExtractionStatus.FAILED.value
    assert doc.extracted_json["structured"]["extraction_outcome"] == "unreadable"
    assert doc.extracted_json["error"] == UNREADABLE_DOCUMENT_LOW_CONTENT
    assert out.envelope.structured.extraction_outcome == "unreadable"
