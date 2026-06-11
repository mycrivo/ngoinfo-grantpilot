"""Unit tests for deterministic KB table renderer."""

from __future__ import annotations

from app.reports.export.kb_table_renderer import (
    NOT_PROVIDED,
    build_logframe_output_score_rows,
)


def test_logframe_table_renders_ten_actual_rows_and_honest_gap_cells():
    facts = {
        "indicators.OP1.1.logframe_ar1_actual": {"value": 684, "semantic_label": "OP1.1 actual"},
        "indicators.OP1.1.logframe_ar1_target": {"value": 650},
        "indicators.OP1.2.logframe_ar1_actual": {"value": 472, "semantic_label": "OP1.2 actual"},
        "indicators.OP1.2.logframe_ar1_target": {"value": 500},
        "indicators.OP1.3.logframe_ar1_actual": {"value": 438, "semantic_label": "OP1.3 actual"},
        "indicators.OP1.3.logframe_ar1_target": {"value": 420},
        "indicators.OP2.1.logframe_ar1_actual": {"value": 31, "semantic_label": "OP2.1 actual"},
        "indicators.OP2.1.logframe_ar1_target": {"value": 24},
        "indicators.OP2.2.logframe_ar1_actual": {"value": 5, "semantic_label": "OP2.2 actual"},
        "indicators.OP2.2.logframe_ar1_target": {"value": 5},
        "indicators.OP3.1.logframe_ar1_actual": {"value": 10, "semantic_label": "OP3.1 actual"},
        "indicators.OP3.1.logframe_ar1_target": {"value": 8},
        "indicators.OP3.2.logframe_ar1_actual": {"value": 11, "semantic_label": "OP3.2 actual"},
        "indicators.OP3.2.logframe_ar1_target": {"value": 10},
        "indicators.OP3.3.logframe_ar1_actual": {"value": 12, "semantic_label": "OP3.3 actual"},
        "indicators.OP3.3.logframe_ar1_target": {"value": 10},
        "indicators.OP4.1.logframe_ar1_actual": {"value": 3, "semantic_label": "OP4.1 actual"},
        "indicators.OP4.1.logframe_ar1_target": {"value": 3},
        "indicators.OP4.3.logframe_ar1_actual": {"value": 2, "semantic_label": "OP4.3 actual"},
        "indicators.OP4.3.logframe_ar1_target": {"value": 2},
    }
    gap_refs = {"logframe_row:op2_3", "logframe_row:op4_2"}
    rows = build_logframe_output_score_rows(facts=facts, gap_refs=gap_refs)

    assert len(rows) == 12
    actual_values = [row[6] for row in rows]
    assert actual_values.count(NOT_PROVIDED) == 2
    op23_row = next(r for r in rows if r[0] == "OP2.3")
    op42_row = next(r for r in rows if r[0] == "OP4.2")
    assert op23_row[6] == NOT_PROVIDED
    assert op42_row[6] == NOT_PROVIDED
    assert sum(1 for v in actual_values if v not in ("", NOT_PROVIDED)) == 10
