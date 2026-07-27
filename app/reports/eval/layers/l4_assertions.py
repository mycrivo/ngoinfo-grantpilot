"""Layer 4 — report assertions. Prose is advisory until ngo-reviewer calibration."""

from __future__ import annotations

import re
from typing import Any

from app.reports.eval.bundle_schema import ScoreableBundle
from app.reports.eval.golden_pack import GoldenPack
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, AssertionResult, Verdict


_CLAIM_MAP_RE = re.compile(r"\*\*Claim map:\*\*\s*(.+)", re.IGNORECASE)


def _section_keys_from_reference(pack: GoldenPack) -> list[str]:
    return [s["section_key"] for s in pack.report_reference.get("sections_present") or []]


def _content_sections(bundle: ScoreableBundle) -> dict[str, Any]:
    content = bundle.content_json or {}
    sections = content.get("sections") or content.get("section_outputs") or {}
    if isinstance(sections, list):
        out = {}
        for s in sections:
            if isinstance(s, dict):
                key = s.get("section_key") or s.get("key") or s.get("id")
                if key:
                    out[str(key)] = s
        return out
    if isinstance(sections, dict):
        return sections
    return {}


def evaluate_layer4(bundle: ScoreableBundle, pack: GoldenPack) -> list[AssertionResult]:
    results: list[AssertionResult] = []
    if is_starved(bundle, "l4_report"):
        for aid, name, cls in [
            ("L4-COVERAGE", "Section coverage vs reference", AssertionClass.BASELINED),
            ("L4-CLAIM-BIND", "Claim-to-fact binding integrity", AssertionClass.BASELINED),
            ("L4-HONEST-SHORT", "Empty-table / honest-short-section behaviour", AssertionClass.INVARIANT),
            ("L4-PROSE", "Prose quality (ngo-reviewer)", AssertionClass.ADVISORY),
        ]:
            results.append(
                AssertionResult(
                    assertion_id=aid,
                    layer=4,
                    name=name,
                    assertion_class=cls,
                    verdict=Verdict.PASS_BY_STARVATION,
                    detail="content stage absent",
                )
            )
        return results

    # Always load Layer 4 from the fixture file via GoldenPack — never inline text.
    ref_md = pack.report_markdown
    ref_keys = _section_keys_from_reference(pack)
    content_sections = _content_sections(bundle)

    # Coverage: fraction of reference section keys that have non-empty prose in content
    covered = 0
    for key in ref_keys:
        # soft match — FCDO keys may differ slightly
        hit = False
        for ck, payload in content_sections.items():
            if key.lower() in str(ck).lower() or str(ck).lower() in key.lower():
                prose = ""
                if isinstance(payload, dict):
                    prose = str(payload.get("prose") or payload.get("text") or payload.get("body") or "")
                elif isinstance(payload, str):
                    prose = payload
                if prose.strip():
                    hit = True
                    break
        if hit:
            covered += 1
    coverage = covered / len(ref_keys) if ref_keys else 0.0
    results.append(
        AssertionResult(
            assertion_id="L4-COVERAGE",
            layer=4,
            name="Section coverage vs reference",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.PASS,
            detail=f"Covered {covered}/{len(ref_keys)} reference sections",
            metrics={"covered": covered, "reference_sections": len(ref_keys), "coverage": round(coverage, 4)},
        )
    )

    # Claim maps in reference — ensure content has some source_refs / claim bindings
    claim_maps = _CLAIM_MAP_RE.findall(ref_md)
    bound = 0
    for _payload in content_sections.values():
        if not isinstance(_payload, dict):
            continue
        refs = _payload.get("source_refs") or _payload.get("claims") or []
        if refs:
            bound += 1
    results.append(
        AssertionResult(
            assertion_id="L4-CLAIM-BIND",
            layer=4,
            name="Claim-to-fact binding integrity",
            assertion_class=AssertionClass.BASELINED,
            verdict=Verdict.PASS if bound > 0 or not claim_maps else Verdict.FAIL,
            detail=f"Sections with bindings: {bound}; reference claim maps: {len(claim_maps)}",
            metrics={"sections_with_bindings": bound, "reference_claim_maps": len(claim_maps)},
        )
    )

    # Honest short / empty table: look for padding flags or all-empty tables without disclosure
    honest = True
    detail = "No dishonest empty-table/padding signal"
    for payload in content_sections.values():
        if not isinstance(payload, dict):
            continue
        if payload.get("off_topic_padding") is True:
            honest = False
            detail = "off_topic_padding flag set"
            break
        tables = payload.get("tables") or []
        if isinstance(tables, list):
            for t in tables:
                if isinstance(t, dict) and t.get("all_not_provided") and not t.get("disclosed_as_gap"):
                    honest = False
                    detail = "empty table without gap disclosure"
                    break
    results.append(
        AssertionResult(
            assertion_id="L4-HONEST-SHORT",
            layer=4,
            name="Empty-table / honest-short-section behaviour",
            assertion_class=AssertionClass.INVARIANT,
            verdict=Verdict.PASS if honest else Verdict.FAIL,
            detail=detail,
        )
    )

    # Prose — advisory until ngo-reviewer charter records calibration
    prose_uncalibrated = bool(pack.report_reference.get("prose_uncalibrated", True))
    results.append(
        AssertionResult(
            assertion_id="L4-PROSE",
            layer=4,
            name="Prose quality (ngo-reviewer)",
            assertion_class=AssertionClass.ADVISORY,
            verdict=Verdict.ADVISORY,
            detail=(
                "Prose assertions are advisory and gate nothing while uncalibrated "
                f"(report_reference.prose_uncalibrated={prose_uncalibrated})"
            ),
            metrics={"uncalibrated": prose_uncalibrated, "gates_ignored": True},
        )
    )

    return results
