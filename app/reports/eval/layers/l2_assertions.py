"""Layer 2 — conflict handling assertions."""

from __future__ import annotations

from typing import Any

from app.reports.eval.bundle_schema import ScoreableBundle
from app.reports.eval.golden_pack import GoldenPack
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, AssertionResult, Verdict


def _bank_conflicts(bundle: ScoreableBundle) -> list[dict[str, Any]]:
    kb = bundle.knowledge_bank or {}
    conflicts = kb.get("conflicts")
    if isinstance(conflicts, dict):
        return [dict(v, **{"_key": k}) for k, v in conflicts.items() if isinstance(v, dict)]
    if isinstance(conflicts, list):
        return [c for c in conflicts if isinstance(c, dict)]
    return []


def evaluate_layer2(bundle: ScoreableBundle, pack: GoldenPack) -> list[AssertionResult]:
    results: list[AssertionResult] = []
    if is_starved(bundle, "l2_conflicts"):
        for aid, name in [
            ("L2-DETECT", "Golden conflicts detected"),
            ("L2-FALSE", "False conflicts manufactured"),
            ("L2-DESTROY", "Resolution path destroys a true fact"),
        ]:
            results.append(
                AssertionResult(
                    assertion_id=aid,
                    layer=2,
                    name=name,
                    assertion_class=AssertionClass.BASELINED,
                    verdict=Verdict.PASS_BY_STARVATION,
                    detail="knowledge_bank stage absent",
                )
            )
        return results

    bank = _bank_conflicts(bundle)
    golden_ids = [c["id"] for c in pack.conflicts]

    # Detection: look for conflict ids or titles / side values mentioned in bank entries
    detected = []
    for g in pack.conflicts:
        gid = g["id"]
        title = (g.get("title") or "").lower()
        for b in bank:
            blob = " ".join(
                str(x) for x in (b.get("id"), b.get("title"), b.get("fact_key"), b)
            ).lower()
            if gid.lower() in blob or (title and title[:48] in blob):
                detected.append(gid)
                break
            # Side-value heuristic
            sides = g.get("sides") or []
            side_hits = 0
            for side in sides:
                val = str(side.get("value") or "")
                if val and val.lower() in blob:
                    side_hits += 1
            if side_hits >= 2:
                detected.append(gid)
                break

    detected_set = set(detected)
    results.append(
        AssertionResult(
            assertion_id="L2-DETECT",
            layer=2,
            name="Golden conflicts detected",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.PASS,  # metric recorded; floor in WI4
            detail=f"Detected {len(detected_set)}/{len(golden_ids)} golden conflicts",
            metrics={
                "detected": sorted(detected_set),
                "golden": golden_ids,
                "detected_count": len(detected_set),
                "golden_count": len(golden_ids),
            },
        )
    )

    # False conflicts: bank conflicts that don't map to any golden
    false = []
    for b in bank:
        blob = " ".join(str(x) for x in b.values()).lower()
        mapped = False
        for g in pack.conflicts:
            if g["id"].lower() in blob or (g.get("title") or "").lower()[:40] in blob:
                mapped = True
                break
        if not mapped:
            false.append(b)

    results.append(
        AssertionResult(
            assertion_id="L2-FALSE",
            layer=2,
            name="False conflicts manufactured",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.FAIL if false else Verdict.PASS,
            detail=f"Unmapped bank conflicts: {len(false)}",
            metrics={"false_conflict_count": len(false)},
        )
    )

    # Destroy true fact: choose-A/B resolution without both_are_true path when golden says both true
    destroy = False
    both_true_ids = {
        c["id"]
        for c in pack.conflicts
        if c.get("resolution_type") == "both_are_true_different_facts"
    }
    for b in bank:
        rtype = str(b.get("resolution_type") or b.get("resolution") or "").lower()
        if any(x in rtype for x in ("choose", "prefer", "overwrite", "replace")):
            # If a both-true golden conflict was "resolved" by choosing one side
            blob = " ".join(str(x) for x in b.values()).lower()
            if any(gid.lower() in blob for gid in both_true_ids) or "1200" in blob or "650" in blob:
                destroy = True
                break
        if b.get("destroyed_true_fact") is True:
            destroy = True
            break

    results.append(
        AssertionResult(
            assertion_id="L2-DESTROY",
            layer=2,
            name="Resolution path destroys a true fact",
            assertion_class=AssertionClass.INVARIANT,
            verdict=Verdict.FAIL if destroy else Verdict.PASS,
            detail=(
                "Resolution destroyed a true fact (both-are-true path absent or unused)"
                if destroy
                else "No destroy-true-fact signal"
            ),
            metrics={"both_true_golden": sorted(both_true_ids)},
        )
    )

    return results
