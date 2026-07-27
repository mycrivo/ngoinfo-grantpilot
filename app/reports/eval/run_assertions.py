"""Run all five assertion layers against a scoreable bundle + golden pack."""

from __future__ import annotations

from typing import Any

from app.reports.eval.bundle_schema import ScoreableBundle
from app.reports.eval.golden_pack import GoldenPack, load_golden_pack
from app.reports.eval.layers import (
    evaluate_layer1,
    evaluate_layer2,
    evaluate_layer3,
    evaluate_layer4,
    evaluate_layer5,
)
from app.reports.eval.verdicts import AssertionResult, Verdict


def run_all_layers(
    bundle: ScoreableBundle,
    pack: GoldenPack | None = None,
) -> list[AssertionResult]:
    pack = pack or load_golden_pack()
    results: list[AssertionResult] = []
    results.extend(evaluate_layer1(bundle, pack))
    results.extend(evaluate_layer2(bundle, pack))
    results.extend(evaluate_layer3(bundle, pack))
    results.extend(evaluate_layer4(bundle, pack))
    results.extend(evaluate_layer5(bundle, pack))
    return results


def gate_verdict(results: list[AssertionResult]) -> dict[str, Any]:
    """Compute a gate-facing summary.

    - ADVISORY results never affect the gate.
    - PASS-BY-STARVATION excluded from demonstrated safety counts.
    - REVIEW-REQUIRED does not auto-PASS the moat.
    - FAIL on INVARIANT fails the gate.
    """
    blocking_fail = [
        r
        for r in results
        if r.verdict == Verdict.FAIL and r.assertion_class.value != "ADVISORY"
    ]
    review = [r for r in results if r.verdict == Verdict.REVIEW_REQUIRED]
    advisory = [r for r in results if r.verdict == Verdict.ADVISORY]
    starvation = [r for r in results if r.verdict == Verdict.PASS_BY_STARVATION]
    demonstrated = [r for r in results if r.counts_as_demonstrated_safety]

    return {
        "gate_pass": not blocking_fail and not review,
        "blocking_failures": [r.assertion_id for r in blocking_fail],
        "review_required": [r.assertion_id for r in review],
        "advisory_ignored_by_gate": [r.assertion_id for r in advisory],
        "pass_by_starvation": [r.assertion_id for r in starvation],
        "demonstrated_safety_count": len(demonstrated),
        "results": [r.to_dict() for r in results],
    }
