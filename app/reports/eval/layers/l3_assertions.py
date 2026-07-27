"""Layer 3 — gap behaviour assertions."""

from __future__ import annotations

from typing import Any

from app.reports.eval.bundle_schema import ScoreableBundle
from app.reports.eval.golden_pack import GoldenPack
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, AssertionResult, Verdict


def _questions(bundle: ScoreableBundle) -> list[dict[str, Any]]:
    ga = bundle.gap_analysis or {}
    for key in ("questions", "gap_questions", "items"):
        raw = ga.get(key)
        if isinstance(raw, list):
            return [q for q in raw if isinstance(q, dict) or isinstance(q, str)]
    return []


def _question_blob(q: Any) -> str:
    if isinstance(q, str):
        return q.lower()
    return " ".join(str(v) for v in q.values()).lower()


def evaluate_layer3(bundle: ScoreableBundle, pack: GoldenPack) -> list[AssertionResult]:
    results: list[AssertionResult] = []
    if is_starved(bundle, "l3_gaps"):
        for aid, name in [
            ("L3-RECALL", "Gap cluster recall"),
            ("L3-PRECISION", "Gap precision vs counter-list"),
            ("L3-COMPARATOR", "Correct period comparator quoted"),
        ]:
            results.append(
                AssertionResult(
                    assertion_id=aid,
                    layer=3,
                    name=name,
                    assertion_class=AssertionClass.BASELINED,
                    verdict=Verdict.PASS_BY_STARVATION,
                    detail="gaps stage absent",
                )
            )
        return results

    questions = _questions(bundle)
    blobs = [_question_blob(q) for q in questions]
    joined = "\n".join(blobs)

    clusters = pack.gaps["clusters"]
    recalled = []
    for c in clusters:
        cid = c["id"].lower()
        intent = (c.get("question_intent") or "").lower()
        gap = (c.get("gap") or "").lower()
        hit = False
        for blob in blobs:
            if cid in blob:
                hit = True
                break
            # Keyword overlap on distinctive phrases
            needles = [w for w in gap.replace("—", " ").split() if len(w) > 5][:4]
            if needles and sum(1 for n in needles if n in blob) >= 2:
                hit = True
                break
            if intent and intent[:60] in blob:
                hit = True
                break
        if hit:
            recalled.append(c["id"])

    results.append(
        AssertionResult(
            assertion_id="L3-RECALL",
            layer=3,
            name="Gap cluster recall",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.PASS,
            detail=f"Recalled {len(recalled)}/{len(clusters)} clusters",
            metrics={
                "recalled": recalled,
                "recall": round(len(recalled) / len(clusters), 4) if clusters else 0.0,
                "cluster_count": len(clusters),
            },
        )
    )

    # Precision: counter-list hits are false positives (FB-14 / FB-15)
    counter = pack.gaps["counter_list"]
    violations = []
    for item in counter:
        needle = (item.get("do_not_ask_for") or "").lower()
        if not needle:
            continue
        # Match distinctive tokens
        tokens = [t for t in needle.replace(",", " ").split() if len(t) > 4]
        for blob in blobs:
            if needle in blob or (tokens and sum(1 for t in tokens if t in blob) >= max(2, len(tokens) // 2)):
                violations.append(item)
                break

    asked = max(len(questions), 1)
    precision = 1.0 - (len(violations) / asked)
    results.append(
        AssertionResult(
            assertion_id="L3-PRECISION",
            layer=3,
            name="Gap precision vs counter-list",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.FAIL if violations else Verdict.PASS,
            detail=f"Counter-list violations: {len(violations)}",
            metrics={
                "violations": [v.get("do_not_ask_for") for v in violations],
                "precision": round(max(0.0, precision), 4),
                "questions_asked": len(questions),
            },
        )
    )

    # Comparator: for recalled high-severity gaps that specify y1 milestone, check wording
    comparator_ok = 0
    comparator_checked = 0
    for c in clusters:
        if c["id"] not in recalled:
            continue
        comp = (c.get("correct_period_comparator") or "").lower()
        if "year 1" not in comp and "milestone" not in comp:
            continue
        comparator_checked += 1
        # Fail if question quotes endline-only without year-1/milestone
        for blob in blobs:
            if c["id"].lower() in blob or (c.get("gap") or "").lower()[:30] in blob:
                if "endline" in blob and "milestone" not in blob and "year 1" not in blob and "y1" not in blob:
                    break
                if "milestone" in blob or "year 1" in blob or "y1" in blob or "target for the year" in blob:
                    comparator_ok += 1
                break

    results.append(
        AssertionResult(
            assertion_id="L3-COMPARATOR",
            layer=3,
            name="Correct period comparator quoted",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.PASS if comparator_checked == 0 or comparator_ok == comparator_checked else Verdict.FAIL,
            detail=f"Comparator OK {comparator_ok}/{comparator_checked}",
            metrics={"comparator_ok": comparator_ok, "comparator_checked": comparator_checked},
        )
    )

    return results
