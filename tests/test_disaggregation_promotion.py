"""Package C - demographic disaggregation promotion + A-routing proof.

Proven against the REAL post-A walk monitoring structured (rows 3-7 disaggregation,
pkg2_nlcf_rewalk_703f0dcf.json) joined with the REAL captured section column
(nlcf_monitoring_section_column.json) - NOT a hand-built favourable fixture. The
703f0dcf walk predates Package A's section_assignment capture, so this test attaches
the REAL captured section labels exactly as A's deterministic post-pass would; it
never invents a section. On the Smoke Test P0 M&E allowlist (.github/workflows).

What this proves:
- Real demographic bands become source-located FactCandidates; zero invented bands
  (the promoted set equals the source set exactly; stated_total never promoted).
- Through A's REAL routing (source-pin via the reconciler cell_ref join), the
  demographics are visible to the section the source assigned them to
  (difference_made) and do NOT bleed into learning / changes_and_next_steps.
- The declared-needs fallback (indicators.*.disaggregation*) routes a band that
  carries no source section, so a funder table without a section column is covered.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.reports.agents.knowledge_bank_reconciler import _llm_to_structured
from app.reports.reconciliation.input_builder import (
    ReconciliationInputBundle,
    _flatten_indicator_data,
    _slug,
)
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KnowledgeBankReconcilerLLMOutput,
)
from app.reports.services.report_inputs_builder import subset_facts_for_section

_REPO = Path(__file__).resolve().parents[1]
_WALK = _REPO / "docs/artefacts/me_module/audits/snapshots/pkg2_nlcf_rewalk_703f0dcf.json"
_SECTION_COL = _REPO / "tests/fixtures/kb/nlcf_monitoring_section_column.json"
_TEMPLATE = _REPO / "docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json"

_DOC_ID = "monitoring-doc"
_SOURCE_LABEL = "03_NLCF_Southbank_Monitoring_and_Spend_Table.docx"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _monitoring_structured() -> dict:
    walk = _load(_WALK)
    docs = walk["snapshots"]["after_reconcile"]["documents"]
    doc = next(d for d in docs if d.get("classification") == "indicator_data")
    structured = doc["extracted_json"]["structured"]
    # Join the REAL captured section column (A's deterministic post-pass output).
    section_col = _load(_SECTION_COL)["Table2"]
    for row in structured.get("indicators") or []:
        label = section_col.get(str(row.get("row_id")))
        if label:
            row["section_assignment"] = {"raw": label}
    return structured


def _sections() -> list[dict]:
    return _load(_TEMPLATE)["report_sections_json"]


def _section(key: str) -> dict:
    return next(s for s in _sections() if s.get("section_key") == key)


def _bundle() -> ReconciliationInputBundle:
    structured = _monitoring_structured()
    return ReconciliationInputBundle(
        fact_candidates=_flatten_indicator_data(_DOC_ID, _SOURCE_LABEL, structured)
    )


def _expected_demo_keys(structured: dict) -> dict[str, str | None]:
    """Independent re-derivation of the promotion rule for the zero-invention check."""
    expected: dict[str, str | None] = {}
    for row in structured.get("indicators") or []:
        rid = row.get("row_id")
        for dim in row.get("disaggregation") or []:
            dim_slug = _slug(dim.get("dimension") or "breakdown")
            for band in dim.get("breakdown") or []:
                value = band.get("value") or {}
                if value.get("absent"):
                    continue
                key = (
                    f"indicators.{rid}.disaggregation."
                    f"{dim_slug}.{_slug(band.get('label') or '')}"
                )
                expected[key] = value.get("normalized")
    return expected


def _reconciled_facts() -> dict[str, dict]:
    """Run candidates through the REAL reconciler join (no LLM) -> KB facts dict."""
    bundle = _bundle()
    llm_facts = [
        {
            "fact_key": cand.field_path,
            "value": cand.value_normalized,
            "unit": cand.unit,
            "semantic_label": cand.semantic_hint,
            "source_document_id": cand.document_id,
            "source_label": cand.source_label,
            "provenance": {
                "excerpt": (cand.provenance or {}).get("excerpt") or "(no excerpt)",
                "cell_ref": (cand.provenance or {}).get("cell_ref"),
            },
        }
        for cand in bundle.fact_candidates
    ]
    parsed = KnowledgeBankReconcilerLLMOutput.model_validate({"facts": llm_facts})
    structured = _llm_to_structured(parsed, bundle)
    return {key: fact.model_dump() for key, fact in structured.facts.items()}


# ===========================================================================
# Promotion - real, source-located, zero invented bands
# ===========================================================================
def test_real_demographics_promoted_with_provenance_and_source_section():
    structured = _monitoring_structured()
    bundle = ReconciliationInputBundle(
        fact_candidates=_flatten_indicator_data(_DOC_ID, _SOURCE_LABEL, structured)
    )
    demo = [c for c in bundle.fact_candidates if ".disaggregation." in c.field_path]
    assert demo, "no demographic candidates promoted from real disaggregation"

    for cand in demo:
        cell_ref = (cand.provenance or {}).get("cell_ref")
        assert cell_ref and str(cell_ref).startswith("Table2!"), cand.field_path
        assert cand.value_normalized is not None, cand.field_path
        # rows 3-7 are the captured "Difference made" rows.
        assert cand.source_section == "Difference made", cand.field_path

    # Zero invented / zero dropped: promoted set == source-derived set exactly.
    promoted = {c.field_path: c.value_normalized for c in demo}
    assert promoted == _expected_demo_keys(structured)
    # Anchor to a real source cell (row 3 Age, Children 8-11 = 42 @ Table2!F3).
    assert promoted["indicators.3.disaggregation.age.children_8_11"] == "42"
    # stated_total is never promoted (it would duplicate the row actual).
    assert not any(
        c.field_path.endswith(".stated_total") for c in bundle.fact_candidates
    )


def test_promotion_does_not_disturb_target_actual_or_financials():
    bundle = _bundle()
    paths = {c.field_path for c in bundle.fact_candidates}
    # Existing facets still flatten (no regression to the rest of the row).
    assert "indicators.2.actual" in paths
    assert "indicators.3.target" in paths
    assert any(p.startswith("financials.lines.") for p in paths)


# ===========================================================================
# Routing through A - visible where assigned, not bleeding elsewhere
# ===========================================================================
def test_demographics_route_to_difference_made_only():
    facts = _reconciled_facts()
    sections = _sections()

    demo_keys = {k for k in facts if ".disaggregation." in k}
    assert demo_keys, "no demographic facts after reconcile join"
    # source_section attached by the real cell_ref join.
    assert all(facts[k]["source_section"] == "Difference made" for k in demo_keys)

    df = subset_facts_for_section(
        facts, _section("difference_made"), report_sections=sections
    )
    assert {k for k in df if ".disaggregation." in k} == demo_keys

    for blind in ("learning", "changes_and_next_steps", "community_involvement"):
        view = subset_facts_for_section(
            facts, _section(blind), report_sections=sections
        )
        assert not any(".disaggregation." in k for k in view), (
            f"demographics bled into {blind}"
        )


# ===========================================================================
# Declared-needs fallback - no source column still routes by namespace
# ===========================================================================
def test_declared_needs_fallback_routes_disaggregation_without_source_section():
    sections = _sections()
    synthetic = {
        "indicators.synthrow.disaggregation.age.children_5_7": {
            "value": "10",
            "semantic_label": "Attendance - Age - Children 5-7",
            "source_section": None,
            "provenance": {"excerpt": "10", "cell_ref": "Sheet1!F9"},
        }
    }
    df = subset_facts_for_section(
        synthetic, _section("difference_made"), report_sections=sections
    )
    assert "indicators.synthrow.disaggregation.age.children_5_7" in df

    learning = subset_facts_for_section(
        synthetic, _section("learning"), report_sections=sections
    )
    assert "indicators.synthrow.disaggregation.age.children_5_7" not in learning
