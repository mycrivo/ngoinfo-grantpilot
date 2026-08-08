"""P0 assertion library semantics — WI2 + D-079 + D-080 + D-082 close-out."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.reports.eval.bundle_schema import (
    STAGE_CONTENT,
    STAGE_GAPS,
    STAGE_KNOWLEDGE_BANK,
    ScoreableBundle,
)
from app.reports.eval.golden_pack import (
    GoldenPack,
    _sha256_canonical,
    compute_pack_checksum,
    load_golden_pack,
)
from app.reports.eval.layers.l1_assertions import evaluate_layer1
from app.reports.eval.layers.l4_assertions import evaluate_layer4
from app.reports.eval.layers.l5_assertions import evaluate_layer5
from app.reports.eval.run_assertions import gate_verdict, run_all_layers
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, Verdict

# Pinned at D-080 honesty package — content checksum unmoved through D-082.
PINNED_CONTENT_CHECKSUM = "185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79"
# Per-layer pins are canonical JSON digests (parse → sorted dump → SHA-256), not file bytes.
# D-082: content-derived so the pin is OS/checkout-independent.
PINNED_PAYLOAD_CONTENT_SHA256 = {
    "facts.json": "deaf3dd11006e4f27595694ff5326ac18a671cba208be0def70e704fdf5d4f7f",
    "conflicts.json": "5f3b428c61ffe511235486c9bcf703d792150cbbf11a983b1fee0ebc332bc6af",
    "gaps.json": "fcd0c98207ac02044f0efb5a48c89438a0bbf5b2ce2ba20a8d85e5908d0a3fb9",
    "forbidden.json": "95340e824deec32cfbcf41bc28dc6426304e96e2cdeaa63e91458ddb934c115a",
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
    obs = pack.manifest["l5_reference_self_check_observations"]
    assert set(obs["recorded_ids"]) == {
        "FB-04",
        "FB-05",
        "FB-06",
        "FB-09",
        "FB-13",
        "FB-14",
    }
    assert obs["per_detector_diagnostics"].endswith(
        "P0_PR14_INDEPENDENT_REVIEW_2026-07-28.md"
    )
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
    """Answer-key identity: checksum and L1/L2/L3/L5 content digests must not move silently."""
    assert pack.content_checksum == PINNED_CONTENT_CHECKSUM
    recomputed = compute_pack_checksum(
        facts=pack.facts,
        conflicts=pack.conflicts,
        gaps=pack.gaps,
        forbidden=pack.forbidden,
        report_reference=pack.report_reference,
    )
    assert recomputed == PINNED_CONTENT_CHECKSUM
    for name, expected in PINNED_PAYLOAD_CONTENT_SHA256.items():
        obj = json.loads((pack.pack_dir / name).read_text(encoding="utf-8"))
        actual = _sha256_canonical(obj)
        assert actual == expected, f"{name} content digest moved: {actual}"


def test_layer_payload_content_digest_fails_when_payload_altered(pack):
    """Demonstrate (not narrate): altering a layer payload changes the content digest."""
    altered_facts = list(pack.facts) + [
        {"id": "F-DIGEST-MUTATION", "facet": "probe", "value": "must-not-match-pin"}
    ]
    assert _sha256_canonical(altered_facts) != PINNED_PAYLOAD_CONTENT_SHA256["facts.json"]
    altered_checksum = compute_pack_checksum(
        facts=altered_facts,
        conflicts=pack.conflicts,
        gaps=pack.gaps,
        forbidden=pack.forbidden,
        report_reference=pack.report_reference,
    )
    assert altered_checksum != PINNED_CONTENT_CHECKSUM


def test_l5_self_check_records_hits_without_failing_load(pack):
    """D-080: self-check runs and records; never fails load on observations."""
    assert pack.l5_reference_self_hits  # known hits against reference prose
    assert "l5_self_check_allowlist" not in pack.manifest
    # Reloading with self-check on must succeed despite hits
    again = load_golden_pack(pack.pack_dir, verify_checksum=True, verify_l5_self_check=True)
    assert set(again.l5_reference_self_hits) == set(pack.l5_reference_self_hits)


def test_novel_self_check_observation_does_not_fail_load(tmp_path):
    """Load succeeds when reference text yields an observation not in the recorded six."""
    src = Path("tests/fixtures/golden/fcdo_bridgelight_ar1_v1")
    dst = tmp_path / "pack"
    shutil.copytree(src, dst)
    report = json.loads((dst / "report_reference.json").read_text(encoding="utf-8"))
    # FB-01 fingerprint ("total row") is not among the six recorded v1.1 observations.
    report["full_markdown"] = report["full_markdown"] + "\n\nProbe phrase: total row.\n"
    (dst / "report_reference.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    loaded = load_golden_pack(dst, verify_checksum=False, verify_l5_self_check=True)
    assert "FB-01" in loaded.l5_reference_self_hits
    assert "FB-01" not in set(
        loaded.manifest["l5_reference_self_check_observations"]["recorded_ids"]
    )


def test_fb05_honest_disclosure_is_advisory_and_gates_nothing(pack):
    """Honest disclosure: omit OP2.3/OP4.2; state they were not reported → ADVISORY, gates nothing."""
    # Corpus must not match mentions_op23/op42 (or safeguarding/learning aliases);
    # it must carry a disclosure phrase so the existing D-080 branch is exercised.
    bundle = ScoreableBundle(
        bundle_id="fb05-disclosure",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={
            "sections": {
                "A": {
                    "prose": (
                        "Two required indicators were not reported this period; "
                        "this reporting gap is stated for the record."
                    )
                }
            }
        },
        export_text=(
            "Two required indicators were not reported this period; "
            "this reporting gap is stated for the record."
        ),
    )
    results = evaluate_layer5(bundle, pack)
    fb05 = next(r for r in results if r.assertion_id == "FB-05")
    assert fb05.assertion_class == AssertionClass.ADVISORY
    assert fb05.verdict == Verdict.ADVISORY
    assert fb05.metrics.get("uncalibrated") is True
    assert fb05.metrics.get("gates_ignored") is True
    assert not fb05.counts_as_demonstrated_safety
    summary = gate_verdict(results)
    assert "FB-05" in summary["advisory_ignored_by_gate"]
    assert "FB-05" not in summary["blocking_failures"]
    assert not any(
        r.assertion_id == "FB-05" and r.counts_as_demonstrated_safety for r in results
    )


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
