"""Shared graders for D4 indicator-data extractor tests and live gate."""

from __future__ import annotations

import json
from typing import Any

from app.reports.schemas.indicator_data_extraction_v1 import (
    ExtractedIndicatorRow,
    IndicatorDataExtractionOutput,
)


def _row_by_id(rows: list[ExtractedIndicatorRow] | list[dict], row_id: str) -> Any:
    for row in rows:
        rid = row.row_id if hasattr(row, "row_id") else row.get("row_id")
        if rid == row_id:
            return row
    return None


def assert_row_integrity(
    structured: IndicatorDataExtractionOutput | dict,
    key: dict,
) -> None:
    expected_ids = key["source_row_ids"]
    if isinstance(structured, dict):
        output_ids = [r["row_id"] for r in structured.get("indicators") or []]
    else:
        output_ids = [r.row_id for r in structured.indicators]
    assert sorted(output_ids) == sorted(expected_ids), (
        f"row_id mismatch: got {output_ids}, expected {expected_ids}"
    )
    assert len(output_ids) == key["data_row_count"]


def assert_no_recompute_planted(
    structured: IndicatorDataExtractionOutput | dict,
    key: dict,
) -> None:
    planted = key["planted_conflicts"]["planted_a_no_recompute"]
    row = _row_by_id(
        structured.indicators if hasattr(structured, "indicators") else structured["indicators"],
        planted["row_id"],
    )
    assert row is not None
    disagg = row.disaggregation if hasattr(row, "disaggregation") else row.get("disaggregation")
    assert disagg, "disaggregation required for no-recompute row"
    dim = disagg[0]
    if hasattr(dim, "stated_total"):
        total = dim.stated_total
        breakdown = dim.breakdown
    else:
        total = dim.get("stated_total")
        breakdown = dim.get("breakdown") or []
    assert total is not None
    total_norm = total.normalized if hasattr(total, "normalized") else total.get("normalized")
    total_raw = total.raw if hasattr(total, "raw") else total.get("raw")
    assert planted["stated_total_raw"] in (total_raw or "")
    assert total_norm == planted["stated_total_raw"]
    assert planted["forbidden_normalized_total"] not in (total_norm or "")
    labels = []
    raws = []
    for item in breakdown:
        if hasattr(item, "label"):
            labels.append(item.label)
            val = item.value
            raws.append(val.raw if hasattr(val, "raw") else val.get("raw"))
        else:
            labels.append(item["label"])
            raws.append(item["value"].get("raw"))
    labels_lower = [lb.lower() for lb in labels]
    for label, raw in zip(planted["breakdown_labels"], planted["breakdown_raws"], strict=True):
        assert label.lower() in labels_lower
        assert raw in raws


def assert_absent_not_dropped(
    structured: IndicatorDataExtractionOutput | dict,
    key: dict,
) -> None:
    planted = key["planted_conflicts"]["planted_b_absent_actual"]
    rows = structured.indicators if hasattr(structured, "indicators") else structured["indicators"]
    row = _row_by_id(rows, planted["row_id"])
    assert row is not None
    actual = row.actual if hasattr(row, "actual") else row["actual"]
    if hasattr(actual, "absent"):
        assert actual.absent is True
        assert actual.raw is None
    else:
        assert actual.get("absent") is True
        assert actual.get("raw") is None
    target = row.target if hasattr(row, "target") else row["target"]
    tnorm = target.normalized if hasattr(target, "normalized") else target.get("normalized")
    assert tnorm == planted["target_normalized"]


def assert_cell_state_fidelity(
    structured: IndicatorDataExtractionOutput | dict,
    key: dict,
) -> None:
    demo = key["cell_state_demo"]
    expected = demo["expected"]
    rows = structured.indicators if hasattr(structured, "indicators") else structured["indicators"]
    row = _row_by_id(rows, demo["row_id"])
    assert row is not None
    target = row.target if hasattr(row, "target") else row["target"]
    actual = row.actual if hasattr(row, "actual") else row["actual"]
    unit = row.unit if hasattr(row, "unit") else row.get("unit")
    assert (target.cell_state if hasattr(target, "cell_state") else target.get("cell_state")) == (
        expected["target_cell_state"]
    )
    assert (target.raw if hasattr(target, "raw") else target.get("raw")) == expected["target_raw"]
    assert actual.absent if hasattr(actual, "absent") else actual.get("absent")
    assert (unit.cell_state if hasattr(unit, "cell_state") else unit.get("cell_state")) == (
        expected["unit_cell_state"]
    )
    assert (unit.raw if hasattr(unit, "raw") else unit.get("raw")) == expected["unit_raw"]


def assert_answer_key_present(
    structured: IndicatorDataExtractionOutput,
    key: dict,
) -> None:
    exp = key["expected_present"]
    refs = set()
    for row in structured.indicators:
        if not row.indicator_ref.absent:
            refs.add(row.indicator_ref.raw or "")
    for ref in exp["indicator_refs"]:
        assert any(ref in r for r in refs), f"missing indicator_ref {ref}"

    assert structured.financials and structured.financials.lines, "financials sheet required"
    line = structured.financials.lines[0]
    assert line.budget.normalized == exp["financials_budget_normalized"]
    assert line.actual.normalized == exp["financials_actual_normalized"]
    currency = exp["financials_currency"]
    if structured.financials.currency and (
        structured.financials.currency.normalized or structured.financials.currency.raw
    ):
        cur = structured.financials.currency.normalized or structured.financials.currency.raw
        assert currency in (cur or "")


def grade_extraction_output(
    structured: IndicatorDataExtractionOutput,
    key: dict,
) -> None:
    assert structured.extraction_outcome == "complete"
    assert_row_integrity(structured, key)
    assert_answer_key_present(structured, key)
    assert_no_recompute_planted(structured, key)
    assert_absent_not_dropped(structured, key)
    assert_cell_state_fidelity(structured, key)


def _norm_fingerprint_value(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("%", "").replace(",", "").strip() or None


def stability_fingerprint(structured: IndicatorDataExtractionOutput | dict) -> str:
    if isinstance(structured, IndicatorDataExtractionOutput):
        data = structured.model_dump(mode="json")
    else:
        data = structured

    rows = []
    for row in sorted(data.get("indicators") or [], key=lambda r: r["row_id"]):
        target = row["target"]
        actual = row["actual"]
        entry = {
            "row_id": row["row_id"],
            "target_norm": _norm_fingerprint_value(target.get("normalized")),
            "actual_norm": (
                _norm_fingerprint_value(actual.get("normalized"))
                if not actual.get("absent")
                else None
            ),
            "actual_absent": actual.get("absent"),
        }
        if row["row_id"] == "disagg_non_sum" and row.get("disaggregation"):
            total = row["disaggregation"][0].get("stated_total") or {}
            entry["disagg_total_norm"] = _norm_fingerprint_value(total.get("normalized"))
            entry["breakdown_norms"] = sorted(
                _norm_fingerprint_value((b.get("value") or {}).get("normalized"))
                for b in row["disaggregation"][0].get("breakdown") or []
            )
        rows.append(entry)
    fin = data.get("financials") or {}
    fin_fp = None
    if fin.get("lines"):
        line = fin["lines"][0]
        fin_fp = {
            "budget": line["budget"].get("normalized"),
            "actual": line["actual"].get("normalized"),
        }
    canonical = {"rows": rows, "financials": fin_fp}
    return json.dumps(canonical, sort_keys=True)
