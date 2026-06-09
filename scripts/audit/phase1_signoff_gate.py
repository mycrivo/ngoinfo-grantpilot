#!/usr/bin/env python3
"""Phase 1 sign-off gate — post-CLEAN faithfulness, DYN-02, live adversarial probes.

Runs after the CLEAN docset walk. Exits non-zero on any failure (honest harness).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from scripts.audit import _common as C
from scripts.audit.analyze_run import analyze
from scripts.audit.full_walk import PASSING_VERDICTS


def _load_clean_walk_artifact() -> tuple[Path, dict]:
    run_label = os.environ.get("SIGNOFF_WALK_RUN", "p1_clean_docset")
    patterns = [
        f"walk_{run_label}_*.json",
        "walk_p1_clean_docset_*.json",
        "walk_p1_clean_*.json",
    ]
    cands: list[Path] = []
    for pattern in patterns:
        cands.extend(sorted(C.ARTIFACT_DIR.glob(pattern)))
    cands = sorted(set(cands), key=lambda p: p.stat().st_mtime)
    if not cands:
        print(f"SIGNOFF_FAIL no CLEAN walk artifact (label={run_label})", flush=True)
        sys.exit(1)
    path = cands[-1]
    return path, json.loads(path.read_text(encoding="utf-8"))


def _report_body_from_artifact(artifact: dict) -> dict[str, Any]:
    snaps = artifact.get("snapshots") or {}
    for key in ("after_critique_detail", "after_critique", "after_export"):
        snap = snaps.get(key) or {}
        if key == "after_critique_detail":
            body = snap.get("body")
            if isinstance(body, dict) and body.get("content_json"):
                return body
            continue
        report = snap.get("report") or {}
        if report.get("content_json"):
            return report
    extra = artifact.get("extra") or {}
    detail = extra.get("report_detail")
    if isinstance(detail, dict) and detail.get("content_json"):
        return detail
    return {}


def _expected_presence_from_content(content_json: dict[str, Any]) -> dict[str, list[str]]:
    expected: dict[str, list[str]] = {}
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_key = str(section.get("section_key") or "")
        content = section.get("content") or {}
        tokens: list[str] = []
        for claim in content.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            if claim.get("bind_status") not in ("bound", "omitted_numeric"):
                continue
            for token in claim.get("value_tokens") or []:
                raw = str(token).strip()
                if raw:
                    tokens.append(raw)
        if tokens:
            expected[section_key] = tokens
    return expected


def _faithfulness_gate(content_json: dict[str, Any]) -> dict[str, Any]:
    from app.reports.eval.faithfulness_check import check_content_json_faithfulness

    expected = _expected_presence_from_content(content_json)
    report = check_content_json_faithfulness(
        content_json,
        expected_presence=expected,
    )
    summary = report.to_summary_dict()
    summary["expected_presence_sections"] = len(expected)
    return summary


def _dyn02_gate(artifact_path: Path) -> dict[str, Any]:
    analysis = analyze(artifact_path)
    blocks = analysis.get("block_flags") or []
    return {
        "dyn02_false_positives": len(blocks),
        "block_flags": blocks,
        "passed": len(blocks) == 0,
        "sections": analysis.get("sections") or [],
    }


def _load_anthropic_env() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    try:
        vars_map = C.railway_vars("--service", C.BACKEND_SERVICE)
        for key in (
            "ANTHROPIC_API_KEY",
            "ME_FACT_SAFETY_CRITIC_MODEL",
            "ME_RECONCILER_MODEL",
        ):
            if vars_map.get(key):
                os.environ[key] = str(vars_map[key])
    except Exception as exc:
        print(f"SIGNOFF_WARN anthropic bootstrap failed: {exc}", flush=True)


def _pick_bound_numeric_fact(kb: dict[str, Any]) -> tuple[str, str] | None:
    for key, fact in (kb.get("facts") or {}).items():
        if not isinstance(fact, dict):
            continue
        value = fact.get("value")
        if not isinstance(value, (int, float)):
            continue
        as_float = float(value)
        token = str(int(as_float)) if as_float == int(as_float) else f"{as_float:g}"
        if len(token.replace(".", "")) >= 2:
            return key, token
    return None


async def _run_split_critic_flags(
    *,
    kb: dict[str, Any],
    section_key: str,
    section_label: str,
    archetype: str,
    content: dict[str, Any],
) -> list[dict[str, Any]]:
    from app.reports.agents.fact_safety_critic import run_qualitative_fact_safety_critic
    from app.reports.knowledge.confirmed_kb import build_confirmed_kb_view
    from app.reports.knowledge.qualitative_kb_scope import (
        build_qualitative_kb_view,
        serialize_qualitative_kb_for_critic,
    )
    from app.reports.schemas.qualitative_critic_v1 import qualitative_flag_from_specific
    from app.reports.services.numeric_fact_verifier import (
        numeric_flag_to_critic_dict,
        verify_section_numerics,
    )

    section_text = str(content.get("text") or "")
    claims = list(content.get("claims") or [])
    citation_mode = content.get("citation_mode")
    kb_view = build_confirmed_kb_view(kb)
    numeric_flags = verify_section_numerics(
        section_text=section_text,
        claims=claims,
        citation_mode=citation_mode,
        kb_view=kb_view,
    )
    flags = [numeric_flag_to_critic_dict(item) for item in numeric_flags]

    section = {
        "section_key": section_key,
        "label": section_label,
        "archetype": archetype,
    }
    qual_view = build_qualitative_kb_view(kb, section=section)
    scoped_kb = serialize_qualitative_kb_for_critic(qual_view)
    qual_result = await run_qualitative_fact_safety_critic(
        section_key=section_key,
        section_label=section_label,
        section_text=section_text,
        scoped_citable_kb=scoped_kb,
        query_fn=None,
    )
    flags.extend(
        qualitative_flag_from_specific(item)
        for item in qual_result.output.specifics
        if item.status == "FLAGGED"
    )
    return flags


async def _live_adversarial_probes(kb: dict[str, Any]) -> dict[str, Any]:
    picked = _pick_bound_numeric_fact(kb)
    if picked is None:
        return {
            "passed": False,
            "cases": [],
            "error": "no_numeric_fact_in_kb_for_probes",
        }
    fact_key, token = picked
    fact_ref = f"fact:{fact_key}"
    tampered = "5000" if token != "5000" else "99999"
    section_key = "summary_and_overview"
    section_label = "Summary and Overview"
    archetype = "ARCH_EXECUTIVE_REVIEW_SUMMARY"

    cases = [
        {
            "name": "uncited_number",
            "content": {
                "citation_mode": "structured",
                "text": (
                    f"The programme reported {token} beneficiaries and also "
                    "99999 uncited fabricated beneficiaries."
                ),
                "claims": [
                    {
                        "text": f"{token} beneficiaries reported.",
                        "source_refs": [fact_ref],
                        "value_tokens": [token],
                        "bind_status": "bound",
                    }
                ],
            },
            "must_block": True,
        },
        {
            "name": "tampered_value",
            "content": {
                "citation_mode": "structured",
                "text": f"The programme reported {tampered} beneficiaries during the period.",
                "claims": [
                    {
                        "text": f"{tampered} beneficiaries reported.",
                        "source_refs": [fact_ref],
                        "value_tokens": [tampered],
                        "bind_status": "bound",
                    }
                ],
            },
            "must_block": True,
        },
        {
            "name": "qualitative_fabrication_no_number",
            "content": {
                "citation_mode": "structured",
                "text": (
                    "The programme expanded into Zambezi Province under partner "
                    "Save the Children UK during the reporting period."
                ),
                "claims": [],
            },
            "must_block": True,
        },
    ]

    results: list[dict[str, Any]] = []
    all_pass = True
    for case in cases:
        flags = await _run_split_critic_flags(
            kb=kb,
            section_key=section_key,
            section_label=section_label,
            archetype=archetype,
            content=case["content"],
        )
        blocks = [
            flag
            for flag in flags
            if flag.get("severity") == "BLOCK" and not flag.get("accepted")
        ]
        passed = bool(blocks) if case["must_block"] else not blocks
        if not passed:
            all_pass = False
        results.append(
            {
                "case": case["name"],
                "passed": passed,
                "block_count": len(blocks),
                "blocks": blocks,
                "verification_paths": sorted(
                    {str(flag.get("verification_path")) for flag in blocks}
                ),
            }
        )
        print(
            f"ADV_PROBE case={case['name']} passed={passed} blocks={len(blocks)}",
            flush=True,
        )

    return {"passed": all_pass, "cases": results}


def main() -> int:
    artifact_path, artifact = _load_clean_walk_artifact()
    verdict = str(artifact.get("verdict") or "")
    if verdict not in PASSING_VERDICTS:
        print(
            f"SIGNOFF_FAIL clean walk verdict={verdict} (expected one of {sorted(PASSING_VERDICTS)})",
            flush=True,
        )
        return 1

    failures: list[str] = []

    report_body = _report_body_from_artifact(artifact)
    content_json = report_body.get("content_json") or {}
    if not content_json.get("sections"):
        failures.append("missing_content_json_for_faithfulness")
    else:
        fh = _faithfulness_gate(content_json)
        C.write_artifact("phase1_faithfulness_summary.json", fh)
        print(f"FAITHFULNESS {json.dumps(fh)}", flush=True)
        if not fh.get("faithfulness.passed"):
            failures.append(f"faithfulness:{fh}")

    dyn02 = _dyn02_gate(artifact_path)
    C.write_artifact("phase1_dyn02_summary.json", dyn02)
    print(
        f"DYN02 false_positives={dyn02['dyn02_false_positives']}",
        flush=True,
    )
    if not dyn02["passed"]:
        failures.append(f"dyn02:{dyn02['dyn02_false_positives']} false positives")

    kb = report_body.get("knowledge_bank_json") or {}
    if not kb.get("facts"):
        failures.append("missing_kb_for_live_adversarial_probes")
    else:
        _load_anthropic_env()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            failures.append("missing_ANTHROPIC_API_KEY_for_live_qualitative_probe")
        else:
            adv = asyncio.run(_live_adversarial_probes(kb))
            C.write_artifact("phase1_adversarial_probes.json", adv)
            if not adv.get("passed"):
                failures.append(f"adversarial:{adv}")

    summary = {
        "passed": not failures,
        "failures": failures,
        "clean_walk_artifact": str(artifact_path),
        "clean_verdict": verdict,
        "report_id": artifact.get("report_id"),
    }
    C.write_artifact("phase1_signoff_summary.json", summary)
    print(f"PHASE1_SIGNOFF {json.dumps(summary)}", flush=True)
    if failures:
        print(f"SIGNOFF_FAIL failures={failures}", flush=True)
        return 1
    print("SIGNOFF_PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
