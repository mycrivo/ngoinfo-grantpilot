"""Unit tests for the generic, template-driven KB table renderer.

The previous hardcoded 12-row OP-skeleton builder (build_logframe_output_score_rows)
was removed as a latent integrity defect; these tests cover the generic dispatch,
fail-closed facet mapping, and the two-real-operand variance guard.
"""

from __future__ import annotations

from app.reports.export.kb_table_renderer import (
    NOT_PROVIDED,
    is_honest_empty_rows,
    table_headers_for_definition,
    table_rows_for_definition,
)

_FIN_TABLE = {
    "table_key": "budget_vs_actual",
    "data_source": "financials",
    "columns": [
        {"column_key": "cost_type", "label": "Cost type"},
        {"column_key": "budgeted_amount", "label": "Budget"},
        {"column_key": "actual_spend", "label": "Actual"},
        {"column_key": "variance", "label": "Variance"},
    ],
}


def test_headers_from_columns():
    assert table_headers_for_definition(_FIN_TABLE) == [
        "Cost type",
        "Budget",
        "Actual",
        "Variance",
    ]


def test_financials_row_fills_both_columns_and_computes_variance():
    facts = {
        "financials.lines.coordinator.budget": {"value": 31200, "semantic_label": "Budget: coordinator"},
        "financials.lines.coordinator.actual_spend": {"value": 29950, "semantic_label": "Actual: coordinator"},
    }
    rows = table_rows_for_definition(table_def=_FIN_TABLE, facts=facts)
    assert rows == [["coordinator", "31200", "29950", "-1250"]]


def test_variance_guard_actual_only_renders_not_provided():
    facts = {"financials.lines.x.actual_spend": {"value": 16480, "semantic_label": "X"}}
    row = table_rows_for_definition(table_def=_FIN_TABLE, facts=facts)[0]
    assert row == ["X", NOT_PROVIDED, "16480", NOT_PROVIDED]


def test_variance_guard_budget_only_renders_not_provided():
    facts = {"financials.lines.y.budget": {"value": 13600, "semantic_label": "Y"}}
    row = table_rows_for_definition(table_def=_FIN_TABLE, facts=facts)[0]
    assert row == ["Y", "13600", NOT_PROVIDED, NOT_PROVIDED]


def test_fail_closed_unmappable_facet_not_forced_into_column():
    # A real fact whose facet has no value family must never be placed in a
    # best-guess column. The mappable fact fills its own column; the unmappable
    # value appears nowhere and its column reads "not provided".
    facts = {
        "financials.lines.z.budget": {"value": 5000, "semantic_label": "Z line"},
        "financials.lines.z.forecast_q3": {"value": 9999, "semantic_label": "Z line"},
    }
    row = table_rows_for_definition(table_def=_FIN_TABLE, facts=facts)[0]
    assert "9999" not in row
    assert row == ["Z line", "5000", NOT_PROVIDED, NOT_PROVIDED]


def test_ambiguous_same_family_facts_fail_closed():
    facts = {
        "financials.lines.a.actual": {"value": 100, "semantic_label": "A"},
        "financials.lines.a.actual_spend": {"value": 200, "semantic_label": "A"},
        "financials.lines.a.budget": {"value": 50, "semantic_label": "A"},
    }
    row = table_rows_for_definition(table_def=_FIN_TABLE, facts=facts)[0]
    # two actual-family facts -> ambiguous -> actual cell + variance not provided
    assert row[2] == NOT_PROVIDED
    assert row[3] == NOT_PROVIDED
    assert row[1] == "50"


def test_manual_table_renders_declared_columns_with_one_honest_row():
    manual = {
        "table_key": "outcomes_summary",
        "data_source": "manual",
        "columns": [{"column_key": "a", "label": "A"}, {"column_key": "b", "label": "B"}],
    }
    rows = table_rows_for_definition(table_def=manual, facts={})
    assert rows == [[NOT_PROVIDED, NOT_PROVIDED]]
    assert is_honest_empty_rows(rows)


def test_narrative_indicators_table_is_honest_empty_not_dumped():
    # Only one fillable family among columns -> not a per-entity data table.
    narrative = {
        "table_key": "vfm_measures",
        "data_source": "indicators",
        "columns": [
            {"column_key": "vfm_measure", "label": "Measure"},
            {"column_key": "current_performance", "label": "Current performance"},
            {"column_key": "evidence", "label": "Evidence"},
        ],
    }
    facts = {"indicators.op1.actual": {"value": 985, "semantic_label": "Output 1"}}
    rows = table_rows_for_definition(table_def=narrative, facts=facts)
    assert rows == [[NOT_PROVIDED, NOT_PROVIDED, NOT_PROVIDED]]


def test_table_without_columns_returns_none():
    assert table_rows_for_definition(table_def={"data_source": "manual"}, facts={}) is None
