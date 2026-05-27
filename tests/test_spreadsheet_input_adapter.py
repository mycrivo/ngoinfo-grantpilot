from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reports.extraction.spreadsheet_input import (
    compute_spreadsheet_hash,
    get_cell_at_ref,
    list_data_row_ids,
    parse_spreadsheet_from_path,
    spreadsheet_to_json_text,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "indicator_extractor"
XLSX = FIXTURES / "fcdo_bridgelight_indicator_data.xlsx"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_indicator_data_answer_key.json"


def _load_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parsed_workbook() -> dict:
    assert XLSX.is_file(), f"Run scripts/build_fcdo_indicator_fixture.py — missing {XLSX}"
    return parse_spreadsheet_from_path(XLSX)


def test_parse_xlsx_row_ids_match_answer_key(parsed_workbook: dict) -> None:
    key = _load_key()
    row_ids = list_data_row_ids(parsed_workbook, sheet_name=key["sheet_name"])
    assert row_ids == key["source_row_ids"]
    assert len(row_ids) == key["data_row_count"]


def test_cell_state_zero_blank_na(parsed_workbook: dict) -> None:
    key = _load_key()
    demo = key["cell_state_demo"]["expected"]
    target = get_cell_at_ref(
        parsed_workbook, "Indicators", key["cell_state_demo"]["target_cell_ref"]
    )
    actual = get_cell_at_ref(
        parsed_workbook, "Indicators", key["cell_state_demo"]["actual_cell_ref"]
    )
    unit = get_cell_at_ref(
        parsed_workbook, "Indicators", key["cell_state_demo"]["unit_cell_ref"]
    )
    assert target is not None
    assert target["cell_state"] == demo["target_cell_state"]
    assert target["raw"] == demo["target_raw"]
    assert actual is not None
    assert actual["cell_state"] == demo["actual_cell_state"]
    assert unit is not None
    assert unit["cell_state"] == demo["unit_cell_state"]
    assert unit["raw"] == demo["unit_raw"]


def test_blank_actual_cell_planted_b(parsed_workbook: dict) -> None:
    key = _load_key()
    cell = get_cell_at_ref(
        parsed_workbook, "Indicators", key["structural_cells"]["blank_actual_ref"]
    )
    assert cell is not None
    assert cell["cell_state"] == "blank"
    assert cell["raw"] is None


def test_hidden_row_present_in_grid(parsed_workbook: dict) -> None:
    key = _load_key()
    row_ids = list_data_row_ids(parsed_workbook)
    planted_id = key["planted_conflicts"]["planted_c_row_integrity"]["row_id"]
    assert planted_id in row_ids


def test_spreadsheet_hash_stable(parsed_workbook: dict) -> None:
    h1 = compute_spreadsheet_hash(parsed_workbook)
    h2 = compute_spreadsheet_hash(parse_spreadsheet_from_path(XLSX))
    assert h1 == h2


def test_spreadsheet_to_json_roundtrip(parsed_workbook: dict) -> None:
    text, truncated = spreadsheet_to_json_text(parsed_workbook)
    assert len(text) > 100
    assert truncated is False
    loaded = json.loads(text)
    assert loaded["format"] == "xlsx"
