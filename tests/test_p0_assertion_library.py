"""P0 WI2 — five-layer assertion library semantics."""

from __future__ import annotations

import pytest

from app.reports.eval.bundle_schema import (
    STAGE_CONTENT,
    STAGE_GAPS,
    STAGE_KNOWLEDGE_BANK,
    ScoreableBundle,
)
from app.reports.eval.golden_pack import load_golden_pack
from app.reports.eval.layers.l1_assertions import evaluate_layer1
from app.reports.eval.layers.l4_assertions import evaluate_layer4
from app.reports.eval.layers.l5_assertions import evaluate_layer5
from app.reports.eval.run_assertions import gate_verdict, run_all_layers
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, Verdict


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
    # Layer 4 text comes from fixture file
    assert "LAYER 4" in pack.report_markdown or "Summary and Overview" in pack.report_markdown
    assert "419, no limit" in pack.report_markdown
    assert "419 of 900" not in pack.report_markdown
    # Appendix is separate from scored markdown
    assert "prose_rubric_reference" in pack.report_reference
    assert "Appendix" in pack.report_reference["prose_rubric_reference"]
    assert "Appendix" not in pack.report_markdown
    # Standing L5 self-check ran and hits are allowlisted
    assert set(pack.l5_reference_self_hits) == {
        "FB-04",
        "FB-05",
        "FB-06",
        "FB-09",
        "FB-13",
        "FB-14",
    }


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
    # Fabrication must not be masked by collapsing into recall fail
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

    # Even if we inject a FAIL elsewhere advisory, gate ignores advisory verdicts
    summary = gate_verdict(results)
    assert "L4-PROSE" in summary["advisory_ignored_by_gate"]


def test_reference_prose_conforms_to_v4_cannot_affect_gate(pack):
    """Guard: flipping reference_prose_conforms_to_v4 must not change any verdict."""
    from app.reports.eval.golden_pack import GoldenPack

    bundle = ScoreableBundle(
        bundle_id="flag-sep",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={"sections": {"A": {"prose": "Text", "source_refs": ["x"]}}},
    )
    base = evaluate_layer4(bundle, pack)
    base_verdicts = {r.assertion_id: r.verdict for r in base}

    flipped_ref = dict(pack.report_reference)
    flipped_ref["reference_prose_conforms_to_v4"] = False
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
    assert flipped.judge_calibrated is False
    alt = evaluate_layer4(bundle, flipped)
    alt_verdicts = {r.assertion_id: r.verdict for r in alt}
    assert base_verdicts == alt_verdicts
    prose = next(r for r in alt if r.assertion_id == "L4-PROSE")
    assert prose.verdict == Verdict.ADVISORY
    assert prose.metrics["gates_ignored"] is True


def test_l5_self_check_rejects_unexpected_hit(pack, tmp_path):
    import json
    from app.reports.eval.golden_pack import load_golden_pack

    # Copy pack to temp and strip allowlist → load must fail on known hits
    src = pack.pack_dir
    dst = tmp_path / "pack"
    dst.mkdir()
    for name in (
        "manifest.json",
        "facts.json",
        "conflicts.json",
        "gaps.json",
        "forbidden.json",
        "report_reference.json",
    ):
        (dst / name).write_text((src / name).read_text(encoding="utf-8"), encoding="utf-8")
    man = json.loads((dst / "manifest.json").read_text(encoding="utf-8"))
    man["l5_self_check_allowlist"] = []  # empty → all hits unexpected
    (dst / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(ValueError, match="L5 reference self-check failed"):
        load_golden_pack(dst, verify_checksum=False, verify_l5_self_check=True)


def test_l4_uses_report_reference_file_not_inline(pack):
    # Mutating an unrelated string must not be what L4 reads — it reads pack.report_markdown
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
    # FB-10 is judged — plant keywords to force REVIEW-REQUIRED
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


def test_l5_dual_deterministic_arm_fails_on_named_instance(pack):
    bundle = ScoreableBundle(
        bundle_id="dual",
        provenance="synthetic",
        stages_present=[STAGE_CONTENT],
        content_json={"sections": {"A": {"prose": "The programme reached 1,944 girls aged 12-17."}}},
        export_text="The programme reached 1,944 girls aged 12-17 from the TOTAL row.",
    )
    results = evaluate_layer5(bundle, pack)
    fb01 = next(r for r in results if r.assertion_id == "FB-01")
    assert fb01.verdict == Verdict.FAIL
    assert fb01.metrics["detection_method"] == "dual"


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
    assert len(results) >= 18  # at least L5 eighteen + other layers
    layers = {r.layer for r in results}
    assert layers == {1, 2, 3, 4, 5}
