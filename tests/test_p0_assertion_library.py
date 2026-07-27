"""P0 assertion library semantics — WI2 + D-079 + D-080 honesty package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.reports.eval.bundle_schema import (
    STAGE_CONTENT,
    STAGE_GAPS,
    STAGE_KNOWLEDGE_BANK,
    ScoreableBundle,
)
from app.reports.eval.golden_pack import GoldenPack, compute_pack_checksum, load_golden_pack
from app.reports.eval.layers.l1_assertions import evaluate_layer1
from app.reports.eval.layers.l4_assertions import evaluate_layer4
from app.reports.eval.layers.l5_assertions import evaluate_layer5
from app.reports.eval.run_assertions import gate_verdict, run_all_layers
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, Verdict

# Pinned at D-080 honesty package — any change to these payloads requires a deliberate test edit.
PINNED_CONTENT_CHECKSUM = "185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79"
PINNED_PAYLOAD_SHA256 = {
    "facts.json": "b1f723252fedfd9b105364c41b17dd7084a2999faba10e33fd4db90b8cd1423b",
    "conflicts.json": "0ba4701d17f446db10874da8df0187750eae6dcaa4eb08d058a38c8894e8a7dc",
    "gaps.json": "e595a26fddca525c10eb8dde6993749aabc11e0459da1b17c37392945489985a",
    "forbidden.json": "d1788cf37227d613851f789a74a2a38b8f4839e6dd6f1062122f8aa65c398548",
}


@pytest.fixture(scope="module")
def pack():
    return load_golden_pack(verify_checksum=True)


def test_golden_pack_loads_and_checksum_matches(pack):
    assert pack.dataset_version == "1.1"
    assert len(pack.facts) == 242
    assert len(pack.conflicts) == 9
    assert len(pack.gaps["clusters"]) == 10
    assert len(pack.gaps["counter_list"]) == 15
    assert len(pack.forbidden) == 18
    assert pack.reference_prose_conforms_to_v4 is True
    assert pack.judge_calibrated is False
    assert "prose_uncalibrated" not in pack.report_reference
    assert "l5_self_check_allowlist" not in pack.manifest
    arm = pack.manifest["l5_deterministic_arm"]
    assert arm["status"] == "uncalibrated"
    assert arm["gates"] is False
    assert arm["fail_on_load"] == "suspended"
    assert "reversion_condition" in arm
    # Layer 4 text comes from fixture file
    assert "LAYER 4" in pack.report_markdown or "Summary and Overview" in pack.report_markdown
    assert "419, no limit" in pack.report_markdown
    assert "419 of 900" not in pack.report_markdown
    # Appendix is separate from scored markdown
    assert "prose_rubric_reference" in pack.report_reference
    assert "Appendix" in pack.report_reference["prose_rubric_reference"]
    assert "Appendix" not in pack.report_markdown
    # Standing L5 self-check ran and recorded hits; load did not fail (D-080)
    assert set(pack.l5_reference_self_hits) == {
        "FB-04",
        "FB-05",
        "FB-06",
        "FB-09",
        "FB-13",
        "FB-14",
    }


def test_pinned_content_checksum_and_layer_payload_digests(pack):
    """Answer-key identity: checksum and L1/L2/L3/L5 bytes must not move silently."""
    assert pack.content_checksum == PINNED_CONTENT_CHECKSUM
    recomputed = compute_pack_checksum(
        facts=pack.facts,
        conflicts=pack.conflicts,
        gaps=pack.gaps,
        forbidden=pack.forbidden,
        report_reference=pack.report_reference,
    )
    assert recomputed == PINNED_CONTENT_CHECKSUM
    for name, expected in PINNED_PAYLOAD_SHA256.items():
        raw = (pack.pack_dir / name).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        assert actual == expected, f"{name} digest moved: {actual}"


def test_l5_self_check_records_hits_without_failing_load(pack):
    """D-080: self-check runs and records; never fails load on observations."""
    assert pack.l5_reference_self_hits  # known hits against reference prose
    assert "l5_self_check_allowlist" not in pack.manifest
    # Reloading with self-check on must succeed despite hits
    again = load_golden_pack(pack.pack_dir, verify_checksum=True, verify_l5_self_check=True)
    assert set(again.l5_reference_self_hits) == set(pack.l5_reference_self_hits)


def test_fb05_is_dual(pack):
    fb05 = next(f for f in pack.forbidden if f["id"] == "FB-05")
    assert fb05["detection_method"] == "dual"


def test_f043_caveat_names_inclusion_basis(pack):
    ach = next(f for f in pack.facts if f["id"] == "F-043" and f["facet"] == "achieved")
    assert ach["status"].startswith("CAVEATED")
    assert ach["caveat"]["uncertain"] == "inclusion_basis"
    baseline = next(f for f in pack.facts if f["id"] == "F-043" and f["facet"] == "baseline")
    assert baseline["status"] == "CONFIRMED"


def test_starvation_when_stage_absent():
    empty = ScoreableBundle(bundle_id="x", provenance="synthetic", stages_present=[])
    assert is_starved(empty, "l1_fact_ledger")
    assert is_starved(empty, "l5_forbidden_content")
    present = ScoreableBundle(
        bundle_id="y",
        provenance="synthetic",
        stages_present=[STAGE_KNOWLEDGE_BANK],
    )
    assert not is_starved(present, "l1_fact_ledger")
    assert is_starved(present, "l4_report")


def test_pass_by_starvation_excluded_from_demonstrated_safety(pack):
    empty = ScoreableBundle(bundle_id="starved", provenance="synthetic", stages_present=[])
    results = run_all_layers(empty, pack)
    starved = [r for r in results if r.verdict == Verdict.PASS_BY_STARVATION]
    assert starved
    summary = gate_verdict(results)
    assert summary["pass_by_starvation"]
    assert summary["demonstrated_safety_count"] == 0
    for r in starved:
        assert not r.counts_as_demonstrated_safety


def test_l1_fabrications_are_review_required_not_fail(pack):
    bundle = ScoreableBundle(
        bundle_id="fab",
        provenance="synthetic",
        stages_present=[STAGE_KNOWLEDGE_BANK],
        knowledge_bank={
            "facts": [
                {
                    "value": "BridgeLight Education Trust",
                    "source_document": "D1",
                },
                {
                    "value": "TOTALLY-INVENTED-FIGURE-999999",
                    "source_document": "D9",
                },
            ]
        },
    )
    results = evaluate_layer1(bundle, pack)
    fab = next(r for r in results if r.assertion_id == "L1-FABRICATIONS")
    assert fab.verdict == Verdict.REVIEW_REQUIRED
    assert fab.metrics["counted_separately_from_recall"] is True
    recall = next(r for r in results if r.assertion_id == "L1-RECALL")
    assert "fabrication" not in recall.detail.lower() or recall.assertion_id != fab.assertion_id


def test_l1_recall_matches_on_value_and_source_not_fact_key(pack):
    bundle = ScoreableBundle(
        bundle_id="recall",
        provenance="synthetic",
        stages_present=[STAGE_KNOWLEDGE_BANK],
        knowledge_bank={
            "facts": {
                "engine.key.whatever": {
                    "value": "BridgeLight Education Trust",
                    "source": "D1 header",
                }
            }
        },
    )
    results = evaluate_layer1(bundle, pack)
    recall = next(r for r in results if r.assertion_id == "L1-RECALL")
    assert recall.metrics["matched"] >= 1


def test_l4_prose_is_advisory_and_ignored_by_gate(pack):
    bundle = ScoreableBundle(
        bundle_id="prose",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={"sections": {"A": {"prose": "Some text", "source_refs": ["F-001"]}}},
    )
    results = evaluate_layer4(bundle, pack)
    prose = next(r for r in results if r.assertion_id == "L4-PROSE")
    assert prose.assertion_class == AssertionClass.ADVISORY
    assert prose.verdict == Verdict.ADVISORY
    assert prose.metrics.get("gates_ignored") is True
    assert prose.metrics.get("judge_calibrated") is False
    assert prose.metrics.get("reference_prose_conforms_to_v4") is True

    summary = gate_verdict(results)
    assert "L4-PROSE" in summary["advisory_ignored_by_gate"]


def test_reference_prose_conforms_to_v4_cannot_affect_any_layer_or_gate(pack):
    """Gate-level separation: invert reference_prose_conforms_to_v4; all verdicts + summary unchanged."""
    bundle = ScoreableBundle(
        bundle_id="flag-sep-full",
        provenance="synthetic",
        stages_present=[STAGE_KNOWLEDGE_BANK, STAGE_GAPS, STAGE_CONTENT],
        knowledge_bank={"facts": [], "conflicts": []},
        gap_analysis={"questions": []},
        content_json={"sections": {"A": {"prose": "Text", "source_refs": ["x"]}}},
        export_text="",
    )
    base_results = run_all_layers(bundle, pack)
    base_summary = gate_verdict(base_results)
    base_verdicts = {r.assertion_id: r.verdict for r in base_results}

    flipped_ref = dict(pack.report_reference)
    flipped_ref["reference_prose_conforms_to_v4"] = not pack.reference_prose_conforms_to_v4
    flipped = GoldenPack(
        pack_dir=pack.pack_dir,
        manifest=pack.manifest,
        facts=pack.facts,
        conflicts=pack.conflicts,
        gaps=pack.gaps,
        forbidden=pack.forbidden,
        report_reference=flipped_ref,
        l5_reference_self_hits=pack.l5_reference_self_hits,
    )
    assert flipped.reference_prose_conforms_to_v4 is False
    alt_results = run_all_layers(bundle, flipped)
    alt_summary = gate_verdict(alt_results)
    alt_verdicts = {r.assertion_id: r.verdict for r in alt_results}

    assert base_verdicts == alt_verdicts
    for key in (
        "gate_pass",
        "blocking_failures",
        "review_required",
        "advisory_ignored_by_gate",
        "pass_by_starvation",
        "demonstrated_safety_count",
    ):
        assert base_summary[key] == alt_summary[key], f"summary[{key}] changed"


def test_missing_judge_calibrated_flag_is_fail_closed():
    """Absent judge_calibrated → harness treats judge as uncalibrated."""
    root = Path("tests/fixtures/golden/fcdo_bridgelight_ar1_v1")
    report = json.loads((root / "report_reference.json").read_text(encoding="utf-8"))
    report.pop("judge_calibrated", None)
    assert "judge_calibrated" not in report
    pack = GoldenPack(
        pack_dir=root,
        manifest=json.loads((root / "manifest.json").read_text(encoding="utf-8")),
        facts=json.loads((root / "facts.json").read_text(encoding="utf-8")),
        conflicts=json.loads((root / "conflicts.json").read_text(encoding="utf-8")),
        gaps=json.loads((root / "gaps.json").read_text(encoding="utf-8")),
        forbidden=json.loads((root / "forbidden.json").read_text(encoding="utf-8")),
        report_reference=report,
    )
    assert pack.judge_calibrated is False


def test_l4_uses_report_reference_file_not_inline(pack):
    md = pack.report_markdown
    assert len(md) > 1000
    bundle = ScoreableBundle(
        bundle_id="l4file",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={"sections": {}},
    )
    results = evaluate_layer4(bundle, pack)
    assert any(r.assertion_id == "L4-COVERAGE" for r in results)


def test_l5_judged_never_auto_clears_moat_on_heuristic(pack):
    bundle = ScoreableBundle(
        bundle_id="judged",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={
            "sections": {
                "Risk": {
                    "prose": (
                        "Inventing current risk ratings mitigations owners statuses "
                        "for the period as if they existed in source material."
                    )
                }
            }
        },
        export_text="Inventing current risk ratings mitigations owners statuses",
    )
    results = evaluate_layer5(bundle, pack)
    fb10 = next(r for r in results if r.assertion_id == "FB-10")
    assert fb10.verdict == Verdict.REVIEW_REQUIRED


def test_l5_dual_deterministic_arm_is_advisory_when_uncalibrated(pack):
    """D-080: deterministic arm hit records observation but does not gate."""
    bundle = ScoreableBundle(
        bundle_id="dual",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={"sections": {"A": {"prose": "The programme reached 1,944 girls aged 12-17."}}},
        export_text="The programme reached 1,944 girls aged 12-17 from the TOTAL row.",
    )
    results = evaluate_layer5(bundle, pack)
    fb01 = next(r for r in results if r.assertion_id == "FB-01")
    assert fb01.assertion_class == AssertionClass.ADVISORY
    assert fb01.verdict == Verdict.ADVISORY
    assert fb01.metrics["detection_method"] == "dual"
    assert fb01.metrics.get("uncalibrated") is True
    assert fb01.metrics.get("gates_ignored") is True
    assert not fb01.counts_as_demonstrated_safety
    summary = gate_verdict(results)
    assert "FB-01" in summary["advisory_ignored_by_gate"]
    assert "FB-01" not in summary["blocking_failures"]


def test_l5_deterministic_arm_markers_and_excluded_from_demonstrated_safety(pack):
    bundle = ScoreableBundle(
        bundle_id="det-markers",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={"sections": {"A": {"prose": "clean prose with no forbidden fingerprints"}}},
        export_text="clean",
    )
    results = evaluate_layer5(bundle, pack)
    det_results = [
        r
        for r in results
        if r.metrics.get("detection_method") == "deterministic"
        or (
            r.metrics.get("detection_method") == "dual"
            and r.metrics.get("uncalibrated") is True
        )
    ]
    # At least pure-deterministic FBs should carry markers when they emit
    pure_det = [r for r in results if r.metrics.get("detection_method") == "deterministic"]
    assert pure_det
    for r in pure_det:
        assert r.assertion_class == AssertionClass.ADVISORY
        assert r.verdict == Verdict.ADVISORY
        assert r.metrics.get("uncalibrated") is True
        assert r.metrics.get("gates_ignored") is True
        assert not r.counts_as_demonstrated_safety
    summary = gate_verdict(results)
    for r in pure_det:
        assert r.assertion_id in summary["advisory_ignored_by_gate"]


def test_run_all_layers_smoke(pack):
    bundle = ScoreableBundle(
        bundle_id="smoke",
        provenance="synthetic",
        stages_present=[STAGE_KNOWLEDGE_BANK, STAGE_GAPS, STAGE_CONTENT],
        knowledge_bank={"facts": [], "conflicts": []},
        gap_analysis={"questions": []},
        content_json={"sections": {"A": {"prose": "Hello", "source_refs": ["x"]}}},
    )
    results = run_all_layers(bundle, pack)
    assert len(results) >= 18
    layers = {r.layer for r in results}
    assert layers == {1, 2, 3, 4, 5}
