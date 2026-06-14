"""Deterministic, template-driven KB-backed table rows for export - no LLM.

Generic across funders (Package 2). Rows come from the REAL knowledge-bank
fact-key namespaces (``financials.lines.*``, ``financials.<aggregate>.*``,
``indicators.*`` / ``indicator.*``), grouped into entities. There are NO
hardcoded per-funder key shapes or row skeletons.

Moat rules inside the table:

- A cell fills ONLY on EXACT value-family membership (fail closed). A fact whose
  facet does not map to a column of the same family renders "not provided" - it is
  never placed in a best-guess or nearest-match column.
- Every value traces to a real fact. ``variance`` is derived only when BOTH real
  operands (actual and budget) are present; a missing operand is never treated as
  zero.
- A declared table never vanishes: where no fact backs it, it renders its declared
  columns plus one honest-empty row.
"""

from __future__ import annotations

import re
from typing import Any

NOT_PROVIDED = "not provided"

# Fillable value families - generic, funder-agnostic vocabulary shared by template
# column_keys and KB fact facets. Membership is EXACT: a cell fills only when a
# fact facet and a column resolve to the SAME family. Tokens absent here have no
# family and always render "not provided" (never a nearest-match guess).
_ACTUAL_TOKENS = frozenset(
    {"actual", "actual_spend", "ar1_actual", "y1_actual", "actual_position", "current_performance"}
)
_BUDGET_TOKENS = frozenset(
    {"budget", "budgeted_amount", "y1_budget", "planned_position"}
)
_TARGET_TOKENS = frozenset(
    {
        "target",
        "milestone",
        "ar1_target",
        "ar1_milestone_target",
        "milestone_target",
        "proposal_target",
        "target_proposal",
    }
)
_VARIANCE_TOKENS = frozenset({"variance", "variance_or_issue"})

# Families a value column can be filled from directly (variance is derived, not
# looked up; it is intentionally excluded from the data-table discriminator).
_FILLABLE_FAMILIES = ("actual", "budget", "target")

_FACET_PREFIX_RE = re.compile(
    r"^(?:budget|actual|target|milestone|spend|forecast|planned)(?:\s+spend)?\s*[:\-\u2013\u2014]\s*",
    re.IGNORECASE,
)
_FACET_SUFFIX_RE = re.compile(
    r"\s*[\-\u2013\u2014]\s*(?:budget|actual(?:\s+spend)?|target|milestone|spend|forecast|planned)\s*$",
    re.IGNORECASE,
)
# Deterministic family order for picking an entity's display label.
_LABEL_FAMILY_ORDER = ("budget", "actual", "target")


def _family(token: str) -> str | None:
    t = str(token or "").strip().lower()
    if t in _ACTUAL_TOKENS:
        return "actual"
    if t in _BUDGET_TOKENS:
        return "budget"
    if t in _TARGET_TOKENS:
        return "target"
    if t in _VARIANCE_TOKENS:
        return "variance"
    return None


def _parse_fact_key(key: str) -> tuple[str, str, str] | None:
    """Return (namespace, entity_id, facet) for financials/indicators KB keys."""
    parts = str(key).split(".")
    if len(parts) < 3:
        return None
    head = parts[0].lower()
    if head == "financials":
        if parts[1].lower() == "lines" and len(parts) >= 4:
            return ("financials", ".".join(parts[2:-1]), parts[-1])
        return ("financials", ".".join(parts[1:-1]), parts[-1])
    if head in ("indicators", "indicator"):
        return ("indicators", ".".join(parts[1:-1]), parts[-1])
    return None


def _group_entities(
    facts: dict[str, Any], namespace: str
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """entity_id -> family -> list of fact dicts (only fillable-family facets)."""
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for key, fact in (facts or {}).items():
        if not isinstance(fact, dict):
            continue
        parsed = _parse_fact_key(key)
        if not parsed:
            continue
        ns, entity, facet = parsed
        if ns != namespace or not entity:
            continue
        fam = _family(facet)
        if fam is None:
            continue
        grouped.setdefault(entity, {}).setdefault(fam, []).append(fact)
    return grouped


def _value_for_family(entity_facts: dict[str, list[dict[str, Any]]], family: str) -> str:
    """Fail-closed value lookup: fills only on a single unambiguous family fact."""
    candidates = entity_facts.get(family) or []
    if len(candidates) != 1:
        return ""  # zero or ambiguous -> caller renders "not provided"
    value = candidates[0].get("value")
    if value is None:
        return ""
    return str(value).strip()


def _strip_facet_prefix(label: str) -> str:
    out = _FACET_PREFIX_RE.sub("", label)
    out = _FACET_SUFFIX_RE.sub("", out)
    return out.strip() or label


def _entity_label(entity_id: str, entity_facts: dict[str, list[dict[str, Any]]]) -> str:
    ordered = list(_LABEL_FAMILY_ORDER) + [
        f for f in entity_facts if f not in _LABEL_FAMILY_ORDER
    ]
    for fam in ordered:
        for fact in entity_facts.get(fam, []):
            label = str(fact.get("semantic_label") or "").strip()
            if label:
                return _strip_facet_prefix(label)
    return entity_id.replace("_", " ").strip()


def _format_number(n: float) -> str:
    if n == int(n):
        return str(int(n))
    return f"{n:g}"


def _variance(actual: str, budget: str) -> str:
    """Derived only when BOTH real operands present; missing operand is never zero."""
    if not actual or not budget:
        return NOT_PROVIDED
    try:
        return _format_number(
            float(actual.replace(",", "")) - float(budget.replace(",", ""))
        )
    except ValueError:
        return NOT_PROVIDED


def _is_total_entity(entity_id: str, label: str) -> bool:
    return "total" in entity_id.lower() or "total" in label.lower()


def _is_fact_data_table(col_families: list[str | None]) -> bool:
    """A table takes per-entity rows only if >=2 distinct fillable families are declared."""
    fams = {f for f in col_families if f in _FILLABLE_FAMILIES}
    return len(fams) >= 2


def _build_rows(table_def: dict[str, Any], facts: dict[str, Any], namespace: str) -> list[list[str]]:
    columns = [c for c in (table_def.get("columns") or []) if isinstance(c, dict)]
    col_count = len(columns)
    if col_count == 0:
        return []
    col_families = [_family(c.get("column_key") or "") for c in columns]

    honest_empty = [NOT_PROVIDED] * col_count
    if not _is_fact_data_table(col_families):
        return [list(honest_empty)]

    grouped = _group_entities(facts, namespace)
    if not grouped:
        return [list(honest_empty)]

    ordered_entities = sorted(
        grouped,
        key=lambda e: (_is_total_entity(e, _entity_label(e, grouped[e])), e.lower()),
    )

    rows: list[list[str]] = []
    for entity_id in ordered_entities:
        entity_facts = grouped[entity_id]
        fam_value = {fam: _value_for_family(entity_facts, fam) for fam in _FILLABLE_FAMILIES}
        label = _entity_label(entity_id, entity_facts)
        row: list[str] = []
        for idx, fam in enumerate(col_families):
            if idx == 0:
                row.append(label or NOT_PROVIDED)
            elif fam == "variance":
                row.append(_variance(fam_value["actual"], fam_value["budget"]))
            elif fam in _FILLABLE_FAMILIES:
                row.append(fam_value.get(fam) or NOT_PROVIDED)
            else:
                row.append(NOT_PROVIDED)
        rows.append(row)
    return rows or [list(honest_empty)]


def table_rows_for_definition(
    *,
    table_def: dict[str, Any],
    facts: dict[str, Any],
    format_rules_json: dict[str, Any] | None = None,
    gap_analysis: dict[str, Any] | None = None,
) -> list[list[str]] | None:
    """Body rows for a template required_tables entry.

    Returns a list for every declared table that has columns (never a bare
    heading): populated rows where facts back them, otherwise a single
    honest-empty row. Returns None only when the table declares no columns.
    """
    columns = [c for c in (table_def.get("columns") or []) if isinstance(c, dict)]
    if not columns:
        return None

    data_source = str(table_def.get("data_source") or "").lower()
    if data_source in ("financials", "indicators"):
        return _build_rows(table_def, facts or {}, data_source)

    # manual (and any other declared source): no structured fact namespace to
    # group; render the declared columns with one honest-empty row.
    return [[NOT_PROVIDED] * len(columns)]


def table_headers_for_definition(table_def: dict[str, Any]) -> list[str]:
    columns = table_def.get("columns") or []
    return [
        str(col.get("label") or col.get("column_key") or "")
        for col in columns
        if isinstance(col, dict)
    ]


def is_honest_empty_rows(rows: list[list[str]] | None) -> bool:
    """True when a rendered table carries no real values (every cell 'not provided')."""
    if not rows:
        return True
    for row in rows:
        for cell in row:
            if str(cell).strip() and str(cell).strip() != NOT_PROVIDED:
                return False
    return True
