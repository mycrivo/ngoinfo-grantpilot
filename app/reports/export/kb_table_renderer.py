"""Deterministic KB-backed table rows for export — no LLM (P3-7 F-6)."""

from __future__ import annotations

import re
from typing import Any

NOT_PROVIDED = "not provided"

FCDO_LOGFRAME_OPS = (
    "OP1.1",
    "OP1.2",
    "OP1.3",
    "OP2.1",
    "OP2.2",
    "OP2.3",
    "OP3.1",
    "OP3.2",
    "OP3.3",
    "OP4.1",
    "OP4.2",
    "OP4.3",
)

_OP_KEY_RE = re.compile(r"^indicators\.(OP\d+\.\d+)\.", re.IGNORECASE)


def _fact_value(facts: dict[str, Any], key: str) -> str:
    fact = facts.get(key)
    if not isinstance(fact, dict):
        return ""
    value = fact.get("value")
    if value is None:
        return ""
    return str(value).strip()


def _fact_label(facts: dict[str, Any], key: str) -> str:
    fact = facts.get(key)
    if not isinstance(fact, dict):
        return ""
    label = fact.get("semantic_label")
    if label:
        return str(label).strip()
    return ""


def _resolve_fact_key(facts: dict[str, Any], suffix: str) -> str | None:
    """Match indicators.OP1.1.logframe_ar1_actual style keys case-insensitively."""
    target = suffix.lower()
    for key in facts:
        if str(key).lower().endswith(target.lower()):
            return str(key)
    return None


def _cell(value: str, *, missing_ok: bool = False) -> str:
    stripped = str(value or "").strip()
    if stripped:
        return stripped
    return NOT_PROVIDED if missing_ok else ""


def build_logframe_output_score_rows(
    *,
    facts: dict[str, Any],
    gap_refs: set[str] | None = None,
) -> list[list[str]]:
    """Rows for FCDO detailed_output_scoring output_score_table (12 OP indicators)."""
    gap_refs = {ref.lower() for ref in (gap_refs or set())}
    rows: list[list[str]] = []
    for op in FCDO_LOGFRAME_OPS:
        op_lower = op.lower().replace(".", "_")
        is_gap = f"logframe_row:{op_lower}" in gap_refs
        actual_key = _resolve_fact_key(facts, f"{op}.logframe_ar1_actual")
        target_key = _resolve_fact_key(facts, f"{op}.logframe_ar1_target")
        actual = _fact_value(facts, actual_key) if actual_key else ""
        target = _fact_value(facts, target_key) if target_key else ""
        indicator = _fact_label(facts, actual_key) if actual_key else ""
        if is_gap and not actual:
            actual = NOT_PROVIDED
        rows.append(
            [
                op,
                NOT_PROVIDED,
                NOT_PROVIDED,
                indicator or NOT_PROVIDED,
                NOT_PROVIDED,
                target or NOT_PROVIDED,
                actual or (NOT_PROVIDED if is_gap else ""),
                NOT_PROVIDED,
                NOT_PROVIDED,
                NOT_PROVIDED,
            ]
        )
    return rows


def build_budget_vs_actual_rows(*, facts: dict[str, Any]) -> list[list[str]]:
    """Rows for NLCF spend_summary budget_vs_actual from financials.lines.* facts."""
    line_keys: dict[str, dict[str, str]] = {}
    for key in facts:
        match = re.match(
            r"^financials\.lines\.(OP\d+\.\d+)\.(y1_actual|y1_budget|actual|budget)$",
            str(key),
            re.IGNORECASE,
        )
        if not match:
            continue
        op = match.group(1).upper()
        field = match.group(2).lower()
        bucket = line_keys.setdefault(op, {})
        if field in ("y1_actual", "actual"):
            bucket["actual"] = str(key)
        elif field in ("y1_budget", "budget"):
            bucket["budget"] = str(key)

    total_actual = _resolve_fact_key(facts, "financials.y1_actual.total") or _resolve_fact_key(
        facts, "financials.total.y1_actual"
    )
    total_budget = _resolve_fact_key(facts, "financials.y1_budget.total") or _resolve_fact_key(
        facts, "financials.total.y1_budget"
    )

    rows: list[list[str]] = []
    for op in sorted(line_keys.keys()):
        refs = line_keys[op]
        budget = _fact_value(facts, refs.get("budget", ""))
        actual = _fact_value(facts, refs.get("actual", ""))
        variance = ""
        if budget and actual:
            try:
                variance = str(float(actual.replace(",", "")) - float(budget.replace(",", "")))
            except ValueError:
                variance = NOT_PROVIDED
        rows.append(
            [
                op,
                budget or NOT_PROVIDED,
                actual or NOT_PROVIDED,
                variance or NOT_PROVIDED,
                NOT_PROVIDED,
            ]
        )

    if total_budget or total_actual:
        variance = ""
        if total_budget and total_actual:
            try:
                variance = str(
                    float(_fact_value(facts, total_actual).replace(",", ""))
                    - float(_fact_value(facts, total_budget).replace(",", ""))
                )
            except ValueError:
                variance = NOT_PROVIDED
        rows.append(
            [
                "Total",
                _fact_value(facts, total_budget) if total_budget else NOT_PROVIDED,
                _fact_value(facts, total_actual) if total_actual else NOT_PROVIDED,
                variance or NOT_PROVIDED,
                NOT_PROVIDED,
            ]
        )
    return rows


def gap_refs_from_analysis(gap_analysis: dict[str, Any] | None) -> set[str]:
    refs: set[str] = set()
    for gap in (gap_analysis or {}).get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        ref = str(gap.get("required_item_ref") or "").strip()
        if ref:
            refs.add(ref)
    return refs


def table_rows_for_definition(
    *,
    table_def: dict[str, Any],
    facts: dict[str, Any],
    format_rules_json: dict[str, Any],
    gap_analysis: dict[str, Any] | None,
) -> list[list[str]] | None:
    """Return body rows for a template required_tables entry, or None if not KB-backed."""
    table_key = str(table_def.get("table_key") or "")
    data_source = str(table_def.get("data_source") or "")

    logframe_enabled = bool((format_rules_json.get("logframe") or {}).get("enabled"))
    if table_key == "output_score_table" and data_source == "indicators" and logframe_enabled:
        return build_logframe_output_score_rows(
            facts=facts,
            gap_refs=gap_refs_from_analysis(gap_analysis),
        )

    if table_key == "budget_vs_actual" and data_source == "financials":
        rows = build_budget_vs_actual_rows(facts=facts)
        return rows if rows else None

    return None


def table_headers_for_definition(table_def: dict[str, Any]) -> list[str]:
    columns = table_def.get("columns") or []
    return [
        str(col.get("label") or col.get("column_key") or "")
        for col in columns
        if isinstance(col, dict)
    ]
