"""Constructed-input tests for bundle export + scorecard emitter (D-083).

No production reads. No adjudication figures. Shapes mirror discovery artefact
BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.
"""

from __future__ import annotations

from app.reports.eval.bundle_export import (
    PersistedReportRecord,
    export_scoreable_bundle,
)
from app.reports.eval.bundle_schema import (
    STAGE_CONTENT,
    STAGE_EXPORT,
    STAGE_GAPS,
    STAGE_KNOWLEDGE_BANK,
    ScoreableBundle,
)
from app.reports.eval.scorecard import emit_scorecard, scorecard_to_dict
from app.reports.eval.verdicts import Verdict


def _constructed_record(**overrides) -> PersistedReportRecord:
    """Minimal persisted-shaped record matching discovery keys."""
    base = dict(
        report_id="00000000-0000-0000-0000-000000000099",
        status="COMPLETE",
        version=1,
        reporting_period_start="2024-01-01",
        reporting_period_end="2024-06-30",
        knowledge_bank_json={
            "schema_version": "1",
            "facts": {
                "family_a.indicator.one": {
                    "value": 10,
                    "unit": "count",
                    "verification_status": "confirmed",
                    "semantic_label": "indicator one",
                    "source_document_id": "doc-1",
                    "source_label": "D1",
                    "provenance": {
                        "excerpt": "ten units",
                        "page": 1,
                        "cell_ref": None,
                        "char_start": 0,
                        "char_end": 9,
                        "section_label": "Results",
                    },
                },
                "family_b.other.metric": {
                    "value": 10,
                    "unit": "count",
                    "verification_status": "confirmed",
                    "semantic_label": "other metric",
                    "source_document_id": "doc-2",
                    "source_label": "D2",
                    "provenance": {"excerpt": "also ten", "page": 2},
                },
            },
            "conflicts": [
                {
                    "fact_key": "family_a.indicator.one",
                    "conflict_type": "value_mismatch",
                    "values": [
                        {"value": 10, "unit": "count", "source_document_id": "doc-1"},
                        {"value": 12, "unit": "count", "source_document_id": "doc-2"},
                    ],
                    "resolved_value": 10,
                    "annotation": "owner chose D1",
                    "resolved_at": "2024-07-01T00:00:00Z",
                }
            ],
            "gap_answers": {},
            "gate1_confirmed_at": "2024-07-01T00:00:00Z",
            "gate2_confirmed_at": "2024-07-02T00:00:00Z",
            "gate3_confirmed_at": "2024-07-03T00:00:00Z",
            "reconciled_at": "2024-07-01T00:00:00Z",
            "reconciler_agent": "knowledge_bank_reconciler",
            "reconciliation_outcome": "ok",
            "reconciliation_version": "1",
            "unreadable_sources": [],
            "agent_trace": {"model_used": "test-model-kb", "input_tokens": 1},
        },
        gap_analysis_json={
            "schema_version": "1",
            "gaps": [
                {
                    "item_key": "g1",
                    "section_key": "A",
                    "section_label": "Summary",
                    "question": "What was the outcome for indicator X?",
                    "rationale": "Required by template",
                    "severity": "required",
                    "owner": "user",
                    "required_item_type": "fact",
                    "required_item_ref": "family_a.indicator.one",
                    "requirement_type": "must",
                    "suggested_action": "provide",
                }
            ],
            "open_items_count": 1,
            "ready_for_gate2": True,
            "readiness_basis": "test",
            "report_context": {"report_type": "AR1"},
            "gap_agent": "gap_compliance",
            "analyzed_at": "2024-07-02T00:00:00Z",
            "agent_trace": {"model_used": "test-model-gap"},
        },
        content_json={
            "sections": [
                {
                    "section_key": "A",
                    "label": "Summary",
                    "generation_status": "generated",
                    "archetype": "narrative",
                    "human_edited": False,
                    "content": {
                        "text": "We supported ten people.",
                        "claims": [
                            {
                                "text": "ten people",
                                "bind_status": "bound",
                                "source_refs": ["family_a.indicator.one"],
                                "dropped_refs": [],
                                "value_tokens": ["10"],
                            }
                        ],
                        "assumptions": [],
                        "evidence_used": ["family_a.indicator.one"],
                        "structured_bind_status": "ok",
                        "citation_mode": "inline",
                    },
                    "critic_flags": [],
                    "constraints_applied": {"word_limit": 500, "word_limit_respected": True},
                    "failure_reason": None,
                    "last_edited_at": None,
                }
            ],
            "generation_summary": {
                "total_sections": 1,
                "generated": 1,
                "accepted": 1,
                "awaiting_review": 0,
                "critic_blocks": 0,
                "failed": 0,
                "warnings": [],
            },
            "export": {
                "storage_ref": "users/x/reports/y/z/report.docx",
                "filename": "report.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "generated_at": "2024-07-04T00:00:00Z",
                "template_version": 1,
                "render_mode": "from_scratch",
            },
        },
        indicator_actuals_json={},
        agent_trace_json={
            "stages": {
                "export": {"action": "exported", "completed_at": "2024-07-04T00:00:00Z"},
                "synthesise": {"section_count": 1, "completed_at": "2024-07-03T00:00:00Z"},
            }
        },
        export_plaintext=None,
    )
    base.update(overrides)
    return PersistedReportRecord(**base)


def test_export_transcribes_facts_object_keys_exactly():
    result = export_scoreable_bundle(_constructed_record(), git_commit="abc123", exported_at="2026-08-08T00:00:00Z")
    bundle = result.bundle
    assert STAGE_KNOWLEDGE_BANK in bundle.stages_present
    facts = bundle.knowledge_bank["facts"]
    assert isinstance(facts, dict)
    assert "family_a.indicator.one" in facts
    assert "family_b.other.metric" in facts
    assert facts["family_a.indicator.one"]["value"] == 10
    assert facts["family_a.indicator.one"]["provenance"]["excerpt"] == "ten units"
    # No aliasing of source fields
    assert "source_document_id" in facts["family_a.indicator.one"]
    assert any("multiple key-prefix families" in o for o in result.observations)


def test_export_carries_conflicts_and_gap_questions_intact():
    result = export_scoreable_bundle(_constructed_record(), git_commit="abc123")
    bundle = result.bundle
    assert STAGE_GAPS in bundle.stages_present
    assert bundle.knowledge_bank["conflicts"][0]["resolved_value"] == 10
    assert bundle.knowledge_bank["conflicts"][0]["annotation"] == "owner chose D1"
    gaps = bundle.gap_analysis["gaps"]
    assert gaps[0]["question"].startswith("What was the outcome")
    assert gaps[0]["rationale"] == "Required by template"
    # Must not alias gaps → questions
    assert "questions" not in bundle.gap_analysis


def test_export_preserves_section_claims_and_bindings():
    result = export_scoreable_bundle(_constructed_record(), git_commit="abc123")
    section = result.bundle.content_json["sections"][0]
    claim = section["content"]["claims"][0]
    assert claim["bind_status"] == "bound"
    assert claim["source_refs"] == ["family_a.indicator.one"]
    assert section["content"]["text"] == "We supported ten people."


def test_empty_indicator_actuals_recorded_as_absent_not_reconstructed():
    result = export_scoreable_bundle(_constructed_record(), git_commit="abc123")
    assert any("indicator_actuals_json: empty or null — recorded as absent" in o for o in result.observations)
    assert "indicator_actuals_json" not in result.bundle.meta


def test_absent_knowledge_bank_omits_stage():
    result = export_scoreable_bundle(
        _constructed_record(knowledge_bank_json={}),
        git_commit="abc123",
    )
    assert STAGE_KNOWLEDGE_BANK not in result.bundle.stages_present
    assert result.bundle.knowledge_bank == {}


def test_export_stage_from_persisted_export_metadata():
    result = export_scoreable_bundle(_constructed_record(), git_commit="abc123")
    assert STAGE_CONTENT in result.bundle.stages_present
    assert STAGE_EXPORT in result.bundle.stages_present
    assert result.bundle.export_text == ""
    assert any("export_text: not supplied" in o for o in result.observations)


def test_export_text_optional_owner_supplied():
    result = export_scoreable_bundle(
        _constructed_record(export_plaintext="Exported body text"),
        git_commit="abc123",
    )
    assert result.bundle.export_text == "Exported body text"
    assert STAGE_EXPORT in result.bundle.stages_present


def test_unobserved_root_key_recorded_and_transcribed():
    kb = _constructed_record().knowledge_bank_json
    assert kb is not None
    kb = dict(kb)
    kb["brand_new_unobserved_field"] = {"x": 1}
    result = export_scoreable_bundle(
        _constructed_record(knowledge_bank_json=kb),
        git_commit="abc123",
    )
    assert any("unobserved root key 'brand_new_unobserved_field'" in o for o in result.observations)
    assert "brand_new_unobserved_field" in result.bundle.knowledge_bank


def test_bundle_carries_report_identity_timestamp_commit():
    result = export_scoreable_bundle(
        _constructed_record(),
        git_commit="deadbeef",
        exported_at="2026-08-08T12:00:00Z",
    )
    meta = result.bundle.meta
    assert meta["report_id"] == "00000000-0000-0000-0000-000000000099"
    assert meta["git_commit"] == "deadbeef"
    assert meta["exported_at"] == "2026-08-08T12:00:00Z"
    assert meta["report_meta"]["status"] == "COMPLETE"
    assert result.bundle.provenance == "export"
    assert result.bundle.model_config["knowledge_bank.agent_trace.model_used"] == "test-model-kb"


def test_scorecard_separates_judged_from_starvation_and_carries_provenance():
    # Bundle with no stages → all starvation
    empty = ScoreableBundle(
        bundle_id="starved-run",
        provenance="synthetic",
        stages_present=[],
        meta={"git_commit": "c0ffee", "exported_at": "2026-08-08T00:00:00Z"},
        model_config={"knowledge_bank.agent_trace.model_used": "m"},
    )
    md = emit_scorecard(empty, git_commit="c0ffee")
    assert "Harness scorecard" in md
    assert "does **not** judge" in md
    assert "`c0ffee`" in md
    assert "golden.dataset_version" in md
    assert "golden.content_checksum" in md
    assert "starved-run" in md
    assert "Nothing to judge" in md
    assert "PASS-BY-STARVATION" in md or "PASS-BY-STARVATION" in md.replace("`", "")
    # Must not present a pass-mark / expected comparison as a grade
    assert "gate_pass" not in md
    assert "does **not** judge" in md
    assert "No threshold, baseline, ratchet, or expected-result comparison is applied." in md

    structured = scorecard_to_dict(empty, git_commit="c0ffee")
    assert structured["report_only"] is True
    assert structured["no_threshold"] is True
    assert structured["provenance"]["git_commit"] == "c0ffee"
    assert structured["provenance"]["golden_content_checksum"]
    # Starvation land in nothing_to_judge
    layer1 = structured["layers"]["1"]
    assert layer1["nothing_to_judge"]
    assert all(r["verdict"] == Verdict.PASS_BY_STARVATION.value for r in layer1["nothing_to_judge"])


def test_scorecard_judged_section_populated_when_stages_present():
    result = export_scoreable_bundle(_constructed_record(), git_commit="abc123")
    md = emit_scorecard(result.bundle)
    assert "### Judged" in md
    assert "L1-RECALL" in md or "Layer 1" in md
    structured = scorecard_to_dict(result.bundle)
    assert structured["layers"]["1"]["judged"]
    assert structured["provenance"]["stages_present"]
