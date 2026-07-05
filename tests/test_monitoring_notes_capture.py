"""Package B2: monitoring evidence/note capture + A-routing proof.

Proven against the REAL NLCF monitoring grid (tests/fixtures/indicator_extractor/
nlcf_southbank_monitoring_grid.json), parsed from the real .docx by the project's own
docx-table reader - NOT a hand-built favourable fixture. The monitoring `structured`
used by the flatten/route proof is a DETERMINISTIC projection of that real grid
(indicator_name/target/actual/note/section read verbatim from columns B/C/D/E/A), so
every captured note value IS a real source cell (asserted below). On the Smoke Test
P0 M&E allowlist (.github/workflows/smoke-test.yml).

What these tests PROVE:
- The schema/mapper carry the row's evidence/note cell (note -> TabularCellField with
  cell_state + source_locator).
- The flattener promotes each real, non-blank note into indicators.<row>.note with its
  source cell_ref and DELIBERATELY no source_section; zero invented notes.
- Through merged-A's REAL routing the notes are visible to changes_and_next_steps via
  the declared indicators.*.note namespace and do NOT strand in difference_made /
  spend_summary (where the same rows' actuals are source-pinned), nor bleed elsewhere.

What these tests do NOT prove:
- That the live model extracts the note column from the spreadsheet on its own. That is
  the owner re-walk (out of scope here). The mapper test uses a mocked LLM response
  whose note values are asserted to be real grid cells, so it cannot smuggle in content
  that is not on the page.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.reports.agents.indicator_data_extractor import extract_indicator_data_text
from app.reports.agents.knowledge_bank_reconciler import _llm_to_structured
from app.reports.gap.template_requirements import enumerate_template_requirements
from app.reports.gap.requirement_satisfaction import evaluate_requirement_satisfaction
from app.reports.reconciliation.input_builder import (
    ReconciliationInputBundle,
    _flatten_indicator_data,
)
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KnowledgeBankReconcilerLLMOutput,
)
from app.reports.services.report_inputs_builder import (
    section_has_synthesizable_inputs,
    subset_facts_for_section,
)
from claude_agent_sdk import ResultMessage

_REPO = Path(__file__).resolve().parents[1]
_GRID = _REPO / "tests/fixtures/indicator_extractor/nlcf_southbank_monitoring_grid.json"
_TEMPLATE = _REPO / "docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json"

_DOC_ID = "monitoring-doc"
_SOURCE_LABEL = "03_NLCF_Southbank_Monitoring_and_Spend_Table.docx"
_SHEET = "Table2"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _grid() -> dict:
    return _load(_GRID)


def _sheet_rows() -> list[dict]:
    for sheet in _grid().get("sheets", []):
        if sheet.get("name") == _SHEET:
            return sheet.get("rows", [])
    raise AssertionError(f"sheet {_SHEET} not found in real grid")


def _cell(row: dict, col: str) -> dict | None:
    for cell in row.get("cells", []):
        ref = str(cell.get("ref", ""))
        if ref[:1] == col:
            return cell
    return None


def _field_from_cell(cell: dict | None) -> dict:
    """Build a TabularCellField-shaped dict verbatim from a real grid cell."""
    if cell is None or cell.get("cell_state") == "blank" or cell.get("raw") is None:
        return {"absent": True}
    ref = str(cell["ref"])
    return {
        "absent": False,
        "raw": cell.get("raw"),
        "normalized": cell.get("raw"),
        "cell_state": cell.get("cell_state") or "stated",
        "source_locator": {"sheet": _SHEET, "cell_range": ref},
    }


def _monitoring_structured() -> dict:
    """Deterministic projection of the REAL grid into extraction `structured`.

    Columns A/B/C/D/E -> section_assignment/indicator_name/target/actual/note. No value
    is authored here; each is read verbatim from the committed real grid.
    """
    rows: list[dict] = []
    for row in _sheet_rows():
        idx = row.get("row_index")
        if not idx or idx == 1:  # header
            continue
        section = _cell(row, "A")
        rows.append(
            {
                "row_id": str(idx),
                "indicator_ref": {"absent": True},
                "indicator_name": _field_from_cell(_cell(row, "B")),
                "target": _field_from_cell(_cell(row, "C")),
                "actual": _field_from_cell(_cell(row, "D")),
                "note": _field_from_cell(_cell(row, "E")),
                "section_assignment": (
                    {"raw": section.get("raw")}
                    if section and section.get("raw")
                    else None
                ),
                "disaggregation": [],
            }
        )
    return {"indicators": rows, "financials": {}}


def _real_note_cells() -> dict[str, str]:
    """{row_id: real column-E text} for every non-blank note in the real grid."""
    out: dict[str, str] = {}
    for row in _sheet_rows():
        idx = row.get("row_index")
        if not idx or idx == 1:
            continue
        cell = _cell(row, "E")
        if cell and cell.get("raw") and cell.get("cell_state") != "blank":
            out[str(idx)] = str(cell["raw"])
    return out


def _sections() -> list[dict]:
    return _load(_TEMPLATE)["report_sections_json"]


def _section(key: str) -> dict:
    return next(s for s in _sections() if s.get("section_key") == key)


def _bundle() -> ReconciliationInputBundle:
    return ReconciliationInputBundle(
        fact_candidates=_flatten_indicator_data(
            _DOC_ID, _SOURCE_LABEL, _monitoring_structured()
        )
    )


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
# Mapper - the LLM note cell survives into the schema
# ===========================================================================
def _result_message(payload: dict) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=120,
        duration_api_ms=100,
        is_error=False,
        num_turns=1,
        session_id="test-session",
        structured_output=payload,
        usage={"input_tokens": 50, "output_tokens": 80},
    )


def _mock_query_factory(response: dict):
    async def _mock_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(response)

    return _mock_query


def test_mapper_carries_note_from_llm_output():
    """A note in the LLM output is mapped into ExtractedIndicatorRow.note verbatim."""
    real = _real_note_cells()
    note_text = real["11"]  # "Coordinator started three weeks late"
    response = {
        "confidence": 0.9,
        "indicators": [
            {
                "row_id": "11",
                "indicator_ref": {"absent": True},
                "indicator_name": {
                    "raw": "Part-time project coordinator",
                    "normalized": "Part-time project coordinator",
                    "cell_state": "stated",
                    "source_locator": {"sheet": _SHEET, "cell_range": "B11"},
                },
                "target": {"absent": True},
                "actual": {"absent": True},
                "note": {
                    "raw": note_text,
                    "normalized": note_text,
                    "cell_state": "stated",
                    "source_locator": {"sheet": _SHEET, "cell_range": "E11"},
                },
            }
        ],
        "financials": None,
    }
    # Feed the REAL grid JSON as the document text (mirrors the live path's input).
    grid_text = _GRID.read_text(encoding="utf-8")
    result = asyncio.run(
        extract_indicator_data_text(
            grid_text,
            filename=_SOURCE_LABEL,
            query_fn=_mock_query_factory(response),
        )
    )
    rows = result.envelope.structured.indicators
    assert len(rows) == 1
    note = rows[0].note
    assert note is not None and not note.absent
    assert note.raw == note_text
    assert note.source_locator is not None
    assert note.source_locator.cell_range == "E11"
    # Anti-self-shaping: the mocked note value is a real source cell.
    assert note_text in grid_text


# ===========================================================================
# Promotion - real, source-located, zero invented notes
# ===========================================================================
def test_real_notes_promoted_with_cell_ref_and_no_source_section():
    bundle = _bundle()
    notes = [c for c in bundle.fact_candidates if c.field_path.endswith(".note")]
    assert notes, "no note candidates promoted from real grid"

    real = _real_note_cells()
    promoted = {c.field_path: c for c in notes}
    # Promoted set == real non-blank E-column set exactly (zero invented, zero dropped).
    assert promoted.keys() == {f"indicators.{rid}.note" for rid in real}

    for rid, text in real.items():
        cand = promoted[f"indicators.{rid}.note"]
        cell_ref = (cand.provenance or {}).get("cell_ref")
        assert cell_ref == f"{_SHEET}!E{rid}", cand.field_path
        assert cand.value_raw == text  # verbatim real cell
        # Deliberately NOT source_section -> routes by declared namespace, not pinned.
        assert cand.source_section is None, cand.field_path
        # D clean-label discipline: no spreadsheet provenance in the human hint.
        assert "!" not in cand.semantic_hint and _SHEET not in cand.semantic_hint

    # Anchor a real variance reason (the owner's "reasons behind variances").
    assert promoted["indicators.11.note"].value_raw == (
        "Coordinator started three weeks late"
    )
    assert promoted["indicators.2.note"].value_raw == (
        "Tuesday sessions paused during boiler repair in January"
    )


def test_note_promotion_does_not_disturb_target_actual():
    paths = {c.field_path for c in _bundle().fact_candidates}
    assert "indicators.3.actual" in paths
    assert "indicators.3.target" in paths
    # The same row carries both an actual (section-pinned) and a note (namespace-routed).
    assert "indicators.3.note" in paths


def test_blank_note_stays_absent():
    """Honest gaps: a row whose evidence/note cell is blank promotes no note fact."""
    structured = _monitoring_structured()
    # Force row 3's note blank and confirm it disappears (others remain).
    for row in structured["indicators"]:
        if row["row_id"] == "3":
            row["note"] = {"absent": True}
    bundle = ReconciliationInputBundle(
        fact_candidates=_flatten_indicator_data(_DOC_ID, _SOURCE_LABEL, structured)
    )
    paths = {c.field_path for c in bundle.fact_candidates}
    assert "indicators.3.note" not in paths
    assert "indicators.2.note" in paths


# ===========================================================================
# Routing through A - notes reach changes, never stranded in difference/spend
# ===========================================================================
def test_notes_route_to_changes_only():
    facts = _reconciled_facts()
    sections = _sections()

    note_keys = {k for k in facts if k.endswith(".note")}
    assert note_keys, "no note facts after reconcile join"
    # The reconciler join leaves notes with no source_section (deliberate).
    assert all(facts[k]["source_section"] is None for k in note_keys)

    changes = subset_facts_for_section(
        facts, _section("changes_and_next_steps"), report_sections=sections
    )
    assert {k for k in changes if k.endswith(".note")} == note_keys

    # The same rows' actuals are source-pinned to their own sections, but the notes
    # must NOT follow them there - that is the anti-stranding guarantee.
    for blind in (
        "difference_made",
        "spend_summary",
        "learning",
        "community_involvement",
        "project_story",
    ):
        view = subset_facts_for_section(
            facts, _section(blind), report_sections=sections
        )
        assert not any(k.endswith(".note") for k in view), (
            f"evidence notes stranded/bled into {blind}"
        )


_GATE1 = "2026-01-01T00:00:00Z"


def _requirements() -> list:
    return enumerate_template_requirements(
        _sections(), report_context={"report_type": "annual"}
    )


def _requirement(ref: str):
    return next(r for r in _requirements() if r.required_item_ref == ref)


# ===========================================================================
# Gap re-point (pin #2) - carried by the REAL requirement-satisfaction path
# ===========================================================================
def test_changes_made_flips_to_satisfied_on_real_notes():
    """changes_made (data) flips gap->satisfied because B's real note facts satisfy it
    through evaluate_requirement_satisfaction; with no note fact it stays a gap."""
    facts = _reconciled_facts()
    reqs = _requirements()
    req = next(r for r in reqs if r.required_item_ref == "changes_made")
    assert req.requirement_type == "data"

    satisfied = evaluate_requirement_satisfaction(
        req, facts=facts, gap_answers={}, all_requirements=reqs,
        gate1_confirmed_at=_GATE1, purpose="gate",
    )
    assert satisfied.satisfied is True

    no_notes = {k: v for k, v in facts.items() if not k.endswith(".note")}
    still_gap = evaluate_requirement_satisfaction(
        req, facts=no_notes, gap_answers={}, all_requirements=reqs,
        gate1_confirmed_at=_GATE1, purpose="gate",
    )
    assert still_gap.satisfied is False


def test_planned_changes_and_support_needed_stay_gaps():
    """Honest gaps: B does not fill these refs; they remain gaps even with notes present."""
    facts = _reconciled_facts()
    reqs = _requirements()
    for ref in ("planned_changes", "support_needed"):
        req = next(r for r in reqs if r.required_item_ref == ref)
        result = evaluate_requirement_satisfaction(
            req, facts=facts, gap_answers={}, all_requirements=reqs,
            gate1_confirmed_at=_GATE1, purpose="gate",
        )
        assert result.satisfied is False, ref


def test_changes_section_synthesizable_only_with_notes():
    facts = _reconciled_facts()
    sec = _section("changes_and_next_steps")
    kb_with = {"facts": facts, "gate1_confirmed_at": _GATE1}
    kb_without = {
        "facts": {k: v for k, v in facts.items() if not k.endswith(".note")},
        "gate1_confirmed_at": _GATE1,
    }
    assert section_has_synthesizable_inputs(
        kb_with, sec, report_sections=_sections()
    ) is True
    assert section_has_synthesizable_inputs(
        kb_without, sec, report_sections=_sections()
    ) is False


def test_row_actual_and_note_diverge_to_their_sections():
    """One real row: actual -> its source section; note -> changes. Both, cleanly."""
    facts = _reconciled_facts()
    sections = _sections()
    # Row 11 is a Spend-summary row: actual stays in spend_summary, note goes to changes.
    spend = subset_facts_for_section(
        facts, _section("spend_summary"), report_sections=sections
    )
    changes = subset_facts_for_section(
        facts, _section("changes_and_next_steps"), report_sections=sections
    )
    assert "indicators.11.actual" in spend
    assert "indicators.11.note" not in spend
    assert "indicators.11.note" in changes
    assert "indicators.11.actual" not in changes
