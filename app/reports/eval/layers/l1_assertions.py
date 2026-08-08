"""Layer 1 — fact-ledger fidelity assertions."""

from __future__ import annotations

from typing import Any

from app.reports.eval.bundle_schema import ScoreableBundle
from app.reports.eval.golden_pack import GoldenPack
from app.reports.eval.matching import sources_compatible, values_match
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, AssertionResult, Verdict


def _bank_facts(bundle: ScoreableBundle) -> list[dict[str, Any]]:
    kb = bundle.knowledge_bank or {}
    facts = kb.get("facts")
    if isinstance(facts, dict):
        # Engine shape: facts keyed by fact_key → materialise as list of value records.
        out = []
        for key, payload in facts.items():
            if not isinstance(payload, dict):
                continue
            row = dict(payload)
            row.setdefault("fact_key", key)
            out.append(row)
        return out
    if isinstance(facts, list):
        return [f for f in facts if isinstance(f, dict)]
    return []


def _bank_match_candidates(bank_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten bank facts to value+source rows (ignore engine fact_key for matching)."""
    rows = []
    for f in bank_facts:
        value = f.get("value")
        if value is None and f.get("absent"):
            rows.append(
                {
                    "value": None,
                    "source": f.get("source_document") or f.get("source"),
                    "absent": True,
                    "raw": f,
                }
            )
            continue
        rows.append(
            {
                "value": value,
                "source": f.get("source_document") or f.get("source"),
                "absent": False,
                "raw": f,
            }
        )
    return rows


def _golden_present_records(pack: GoldenPack) -> list[dict[str, Any]]:
    """Golden facts that should appear in the bank (non-absent)."""
    return [f for f in pack.facts if not f.get("absent")]


def _golden_absent_records(pack: GoldenPack) -> list[dict[str, Any]]:
    return [f for f in pack.facts if f.get("absent")]


def evaluate_layer1(bundle: ScoreableBundle, pack: GoldenPack) -> list[AssertionResult]:
    results: list[AssertionResult] = []

    if is_starved(bundle, "l1_fact_ledger"):
        results.append(
            AssertionResult(
                assertion_id="L1-RECALL",
                layer=1,
                name="Golden fact recall (value+source)",
                assertion_class=AssertionClass.BASELINED,
                verdict=Verdict.PASS_BY_STARVATION,
                detail="knowledge_bank stage absent — recall not demonstrated",
            )
        )
        results.append(
            AssertionResult(
                assertion_id="L1-FABRICATIONS",
                layer=1,
                name="Bank fabrications (no golden counterpart)",
                assertion_class=AssertionClass.BASELINED,
                verdict=Verdict.PASS_BY_STARVATION,
                detail="knowledge_bank stage absent — fabrications not inspectable",
            )
        )
        return results

    bank = _bank_match_candidates(_bank_facts(bundle))
    present_golden = _golden_present_records(pack)
    matched = 0
    matched_keys: set[tuple[str, str]] = set()
    for g in present_golden:
        key = (g["id"], g["facet"])
        hit = False
        for b in bank:
            if b["absent"]:
                continue
            if values_match(g.get("value"), b.get("value")) and sources_compatible(
                g.get("source_document"), b.get("source")
            ):
                hit = True
                break
        if hit:
            matched += 1
            matched_keys.add(key)

    recall = matched / len(present_golden) if present_golden else 0.0
    results.append(
        AssertionResult(
            assertion_id="L1-RECALL",
            layer=1,
            name="Golden fact recall (value+source)",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.PASS,  # floor comparison is WI4; here we record the metric
            detail=f"Matched {matched}/{len(present_golden)} present golden facets",
            metrics={
                "matched": matched,
                "present_golden": len(present_golden),
                "recall": round(recall, 4),
            },
        )
    )

    # Fabrications: bank entries with no golden counterpart → REVIEW-REQUIRED (Addition 3)
    fabrications = []
    for b in bank:
        if b["absent"]:
            continue
        found = False
        for g in present_golden:
            if values_match(g.get("value"), b.get("value")) and sources_compatible(
                g.get("source_document"), b.get("source")
            ):
                found = True
                break
        if not found:
            fabrications.append(b["raw"])

    results.append(
        AssertionResult(
            assertion_id="L1-FABRICATIONS",
            layer=1,
            name="Bank fabrications (no golden counterpart)",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.REVIEW_REQUIRED if fabrications else Verdict.PASS,
            detail=(
                f"{len(fabrications)} bank entr(y/ies) with no golden counterpart — "
                "owner bins: golden amendment | invention"
                if fabrications
                else "No fabrications detected"
            ),
            metrics={
                "fabrication_count": len(fabrications),
                "counted_separately_from_recall": True,
            },
        )
    )

    # Absent-facet holes: golden absent should not be "matched" by a string
    absent_golden = _golden_absent_records(pack)
    wrongly_filled = 0
    for g in absent_golden:
        for b in bank:
            if b["absent"]:
                continue
            # Any concrete value for an id+facet that golden marks absent is a fill-in
            # We cannot match by id (engine keys differ); detect by ontology_slot label in raw if present
            label = (g.get("label") or "").lower()
            raw_label = str(b["raw"].get("label") or b["raw"].get("name") or "").lower()
            if label and raw_label and label[:40] in raw_label:
                wrongly_filled += 1
                break
    results.append(
        AssertionResult(
            assertion_id="L1-ABSENCE-HOLES",
            layer=1,
            name="Absent golden facets remain holes (not filled strings)",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.FAIL if wrongly_filled else Verdict.PASS,
            detail=f"Possible filled absences: {wrongly_filled}",
            metrics={"absent_golden": len(absent_golden), "wrongly_filled": wrongly_filled},
        )
    )

    return results
