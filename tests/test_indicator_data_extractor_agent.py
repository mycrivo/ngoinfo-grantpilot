from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.reports.agents.indicator_data_extractor import (
    AGENT_NAME,
    DEGRADED_EXTRACTION_TIMEOUT,
    DEGRADED_EXTRACTION_UNPARSEABLE,
    MAX_EXTRACTION_ATTEMPTS,
    MAX_TURNS,
    IndicatorDataExtractorError,
    build_degraded_unparseable_result,
    extract_indicator_data_from_path,
    extract_indicator_data_text,
)
from app.reports.extraction.spreadsheet_input import (
    parse_spreadsheet_from_path,
    spreadsheet_to_json_text,
)
from app.reports.models.enums import ExtractionStatus
from app.reports.schemas.indicator_data_extraction_v1 import IndicatorDataExtractionOutput
from app.reports.services.indicator_data_extraction_service import (
    IndicatorDataExtractionServiceError,
    extract_and_persist_indicator_data,
    persist_degraded_indicator_unparseable,
)
from claude_agent_sdk import ResultMessage
from tests.indicator_data_grading import (
    assert_absent_not_dropped,
    assert_cell_state_fidelity,
    assert_no_recompute_planted,
    assert_row_integrity,
    grade_extraction_output,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "indicator_extractor"
XLSX = FIXTURES / "fcdo_bridgelight_indicator_data.xlsx"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_indicator_data_answer_key.json"
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
        usage={"input_tokens": 100, "output_tokens": 1200},
    )


def _mock_query_factory(response: dict):
    async def _mock_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(response)

    return _mock_query


def _load_answer_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


def _loc(sheet: str, cell_range: str) -> dict:
    return {"sheet": sheet, "cell_range": cell_range}


def _cell(
    raw: str | None,
    normalized: str | None,
    cell_state: str,
    *,
    sheet: str = "Indicators",
    ref: str = "A1",
    absent: bool = False,
) -> dict:
    if absent:
        return {
            "absent": True,
            "raw": None,
            "normalized": None,
            "cell_state": None,
            "normalization_ambiguous": False,
            "source_locator": None,
            "multi_value": False,
            "stated_values": [],
        }
    return {
        "absent": False,
        "raw": raw,
        "normalized": normalized,
        "cell_state": cell_state,
        "normalization_ambiguous": False,
        "source_locator": _loc(sheet, ref),
        "multi_value": False,
        "stated_values": [],
    }


def _indicator_row(
    row_id: str,
    ref: str,
    name: str,
    target_raw: str,
    target_norm: str,
    actual_raw: str | None,
    actual_norm: str | None,
    *,
    actual_absent: bool = False,
    unit_raw: str | None = "persons",
    unit_state: str = "stated",
    row_ref: str = "A2",
    disaggregation: list | None = None,
) -> dict:
    actual = (
        _cell(None, None, "blank", absent=True, ref=f"E{row_ref[1:]}")
        if actual_absent
        else _cell(actual_raw, actual_norm, "stated", ref=f"E{row_ref[1:]}")
    )
    unit = None
    if unit_raw is not None:
        unit = _cell(
            unit_raw,
            unit_raw if unit_state == "not_applicable" else unit_raw,
            unit_state,
            ref=f"F{row_ref[1:]}",
        )
    return {
        "row_id": row_id,
        "indicator_ref": _cell(ref, ref, "stated", ref=f"B{row_ref[1:]}"),
        "indicator_name": _cell(name, name, "stated", ref=f"C{row_ref[1:]}"),
        "target": _cell(target_raw, target_norm, "stated", ref=f"D{row_ref[1:]}"),
        "actual": actual,
        "unit": unit,
        "disaggregation": disaggregation or [],
        "source_locator": _loc("Indicators", row_ref),
        "multi_value": False,
    }


def _fcdo_mock_llm_response() -> dict:
    return {
        "confidence": 0.91,
        "indicators": [
            _indicator_row(
                "op1_1_girls_reenrolled",
                "OP1.1",
                "Girls re-enrolled to formal education",
                "1200",
                "1200",
                "985",
                "985",
                row_ref="A2",
            ),
            _indicator_row(
                "op1_2_girls_attending",
                "OP1.2",
                "Girls attending at least 80% of sessions",
                "900",
                "900",
                "712",
                "712",
                row_ref="A3",
            ),
            _indicator_row(
                "disagg_non_sum",
                "DISAGG",
                "Beneficiaries reached by gender",
                "100",
                "100",
                "98",
                "98",
                row_ref="A4",
                disaggregation=[
                    {
                        "dimension": "gender",
                        "stated_total": _cell("100", "100", "stated", ref="H4"),
                        "breakdown": [
                            {
                                "label": "Male",
                                "value": _cell("40", "40", "stated", ref="I4"),
                            },
                            {
                                "label": "Female",
                                "value": _cell("35", "35", "stated", ref="J4"),
                            },
                            {
                                "label": "Other",
                                "value": _cell("30", "30", "stated", ref="K4"),
                            },
                        ],
                    }
                ],
            ),
            _indicator_row(
                "op1_1_target_only",
                "OP1.T",
                "Girls trained Q4 (target only row)",
                "500",
                "500",
                None,
                None,
                actual_absent=True,
                row_ref="A5",
            ),
            _indicator_row(
                "hidden_continuation_row",
                "OP-HIDDEN",
                "District learning meetings held (continuation block)",
                "12",
                "12",
                "11",
                "11",
                unit_raw="count",
                row_ref="A7",
            ),
            _indicator_row(
                "cell_state_demo",
                "DEMO",
                "Cell state demonstration row",
                "0",
                "0",
                None,
                None,
                actual_absent=True,
                unit_raw="N/A",
                unit_state="not_applicable",
                row_ref="A8",
            ),
            _indicator_row(
                "op2_1_latrine_stances",
                "OP2.1",
                "Latrine stances rehabilitated",
                "24",
                "24",
                "22",
                "22",
                unit_raw="stances",
                row_ref="A9",
            ),
            _indicator_row(
                "ocm1_attendance_80pct",
                "OCM1",
                "Girls meeting 80% attendance threshold",
                "70%",
                "70",
                "68%",
                "68",
                unit_raw="percent",
                row_ref="A10",
            ),
        ],
        "financials": {
            "currency": _cell("GBP", "GBP", "stated", sheet="Financials", ref="E2"),
            "lines": [
                {
                    "line_key": "budget_total",
                    "label": _cell(
                        "Total programme budget",
                        "Total programme budget",
                        "stated",
                        sheet="Financials",
                        ref="B2",
                    ),
                    "budget": _cell(
                        "1240000", "1240000", "stated", sheet="Financials", ref="C2"
                    ),
                    "actual": _cell(
                        "1184000", "1184000", "stated", sheet="Financials", ref="D2"
                    ),
                }
            ],
        },
    }


@pytest.fixture
def spreadsheet_json() -> str:
    data = parse_spreadsheet_from_path(XLSX)
    text, _ = spreadsheet_to_json_text(data)
    return text


@pytest.mark.asyncio
async def test_extract_empty_raises_stop():
    with pytest.raises(IndicatorDataExtractorError) as exc:
        await extract_indicator_data_text("  ", query_fn=_mock_query_factory({}))
    assert exc.value.code == "STOP_EMPTY_INPUT"


@pytest.mark.asyncio
async def test_mock_envelope_shape(spreadsheet_json: str):
    result = await extract_indicator_data_text(
        spreadsheet_json,
        filename="fcdo_bridgelight_indicator_data.xlsx",
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert result.envelope.extractor_agent == AGENT_NAME
    assert result.envelope.structured.schema_version == "1.0.0"
    assert result.envelope.structured.extraction_outcome == "complete"
    assert len(result.envelope.structured.indicators) == 8


@pytest.mark.asyncio
async def test_planted_no_recompute(spreadsheet_json: str):
    key = _load_answer_key()
    result = await extract_indicator_data_text(
        spreadsheet_json,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert_no_recompute_planted(result.envelope.structured, key)


@pytest.mark.asyncio
async def test_planted_absent_not_dropped(spreadsheet_json: str):
    key = _load_answer_key()
    result = await extract_indicator_data_text(
        spreadsheet_json,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert_absent_not_dropped(result.envelope.structured, key)


@pytest.mark.asyncio
async def test_planted_row_integrity(spreadsheet_json: str):
    key = _load_answer_key()
    result = await extract_indicator_data_text(
        spreadsheet_json,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert_row_integrity(result.envelope.structured, key)


@pytest.mark.asyncio
async def test_cell_state_fidelity(spreadsheet_json: str):
    key = _load_answer_key()
    result = await extract_indicator_data_text(
        spreadsheet_json,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert_cell_state_fidelity(result.envelope.structured, key)


@pytest.mark.asyncio
async def test_unparseable_docx_from_path_returns_degraded_no_raise(tmp_path):
    path = tmp_path / "logframe_data.docx"
    path.write_bytes(b"not a real spreadsheet")
    result = await extract_indicator_data_from_path(path)
    assert result.envelope.structured.extraction_outcome == "degraded"
    assert result.envelope.error == DEGRADED_EXTRACTION_UNPARSEABLE
    assert result.envelope.agent_trace is not None
    assert result.envelope.agent_trace.degraded_code == DEGRADED_EXTRACTION_UNPARSEABLE
    assert result.envelope.agent_trace.attempt_count is None


def test_build_degraded_unparseable_matches_timeout_envelope_shape():
    unparseable = build_degraded_unparseable_result(
        content_hash="hash-unparseable",
        filename="logframe.docx",
    )
    assert unparseable.envelope.structured.extraction_outcome == "degraded"
    assert unparseable.envelope.error == DEGRADED_EXTRACTION_UNPARSEABLE
    assert unparseable.envelope.structured.indicators == []
    assert unparseable.envelope.agent_trace.degraded_code == DEGRADED_EXTRACTION_UNPARSEABLE


@pytest.mark.asyncio
async def test_service_persists_unparseable_without_raise():
    db = MagicMock()
    doc_id = uuid.uuid4()

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "indicator_data"
            self.original_filename = "logframe_data.docx"
            self.extracted_json: dict = {}
            self.extraction_status = ExtractionStatus.PENDING.value

    doc = Doc()
    db.get.return_value = doc

    result = await persist_degraded_indicator_unparseable(db, doc_id)
    assert doc.extraction_status == ExtractionStatus.FAILED.value
    assert doc.extracted_json["structured"]["extraction_outcome"] == "degraded"
    assert doc.extracted_json["error"] == DEGRADED_EXTRACTION_UNPARSEABLE
    assert result.envelope.structured.extraction_outcome == "degraded"


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

    result = await extract_indicator_data_text(
        "{}",
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
async def test_successful_run_records_attempt_count_one(spreadsheet_json: str):
    result = await extract_indicator_data_text(
        spreadsheet_json,
        query_fn=_mock_query_factory(_fcdo_mock_llm_response()),
    )
    assert result.envelope.structured.extraction_outcome == "complete"
    assert result.envelope.agent_trace is not None
    assert result.envelope.agent_trace.attempt_count == 1
    assert result.envelope.agent_trace.degraded_code is None


@pytest.mark.asyncio
async def test_service_persists_degraded_without_raise(spreadsheet_json: str):
    db = MagicMock()
    doc_id = uuid.uuid4()

    class Doc:
        def __init__(self) -> None:
            self.id = doc_id
            self.classification = "indicator_data"
            self.original_filename = "fcdo.xlsx"
            self.extracted_json: dict = {}
            self.extraction_status = ExtractionStatus.PENDING.value

    doc = Doc()
    db.get.return_value = doc

    async def _slow_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        await asyncio.sleep(5)
        yield _result_message(_fcdo_mock_llm_response())

    result = await extract_and_persist_indicator_data(
        db,
        doc_id,
        spreadsheet_json,
        query_fn=_slow_query,
        per_attempt_timeout_seconds=0.01,
    )
    assert doc.extraction_status == ExtractionStatus.FAILED.value
    assert doc.extracted_json["structured"]["extraction_outcome"] == "degraded"
    assert result.envelope.structured.extraction_outcome == "degraded"


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
    with pytest.raises(IndicatorDataExtractionServiceError) as exc:
        await extract_and_persist_indicator_data(
            db, doc.id, "{}", query_fn=_mock_query_factory({})
        )
    assert exc.value.code == "STOP_WRONG_CLASSIFICATION"


def test_build_agent_options_bounded():
    from app.reports.agents.indicator_data_extractor import build_agent_options

    options = build_agent_options()
    assert options.max_turns == MAX_TURNS


def test_recorded_fcdo_live_extraction_matches_answer_key_contract():
    assert RECORDED_EXTRACTION.is_file(), (
        f"Missing recorded extraction at {RECORDED_EXTRACTION}. "
        "Generate via: python scripts/indicator_data_gate.py"
    )
    key = _load_answer_key()
    payload = json.loads(RECORDED_EXTRACTION.read_text(encoding="utf-8"))
    structured = IndicatorDataExtractionOutput.model_validate(payload["structured"])
    grade_extraction_output(structured, key)
