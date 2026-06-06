#!/usr/bin/env python3
"""Planted-conflict FCDO BridgeLight prod walk through F2 critique (throwaway)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.fcdo_d4_f1_fresh_prod_walk import (  # noqa: E402
    BASE_URL,
    CLAUDE_INPUT_USD_PER_1M,
    CLAUDE_OUTPUT_USD_PER_1M,
    DOC_DIR,
    FCDO_TEMPLATE_ID,
    MAX_WAIT_GATE1,
    MAX_WAIT_POST_GATE1,
    MAX_WAIT_POST_GATE2,
    OPENAI_INPUT_USD_PER_1M,
    OPENAI_OUTPUT_USD_PER_1M,
    POLL_SECONDS,
    XLSX_NAME,
    UPLOAD_FILES,
    _bootstrap_db_env,
    _collect_claude_tokens,
    _db_read,
    _openai_synth_tokens,
    _secret,
    _substantive_gap_answer,
    mint_token,
    poll_job,
)

EXPECTED_DEPLOY_SHA_PREFIX = "1e1b124"
MAX_WAIT_CRITIQUE = 1800
DOC03_OMITTED_REASON = (
    "Answer-key Document 3 is spreadsheet content fully carried by the .xlsx; "
    "the .docx duplicate only triggers DEGRADED_EXTRACTION_UNPARSEABLE without "
    "unique planted conflicts."
)

# Answer-key true/intended values for Gate 1 conflict resolution hints
GATE1_TRUTH = {
    "budget": "1240000",
    "budget_display": "GBP 1,240,000",
    "op11_actual": "684",
    "ar1_period": "15 October 2024 to 14 October 2025",
    "project_period": "15 October 2024 to 14 October 2026",
    "full_grant": "1240000",
    "ar1_forecast": "880000",
    "ar1_actual_spend": "920420",
}


def _railway() -> str:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise RuntimeError("railway CLI not found")
    return railway


def _verify_precondition() -> dict:
    gh = subprocess.check_output(
        ["gh", "api", "repos/mycrivo/ngoinfo-grantpilot/commits/main", "--jq", ".sha"],
        cwd=REPO,
        text=True,
    ).strip()
    openapi = requests.get(f"{BASE_URL}/openapi.json", timeout=30).json()
    gate3_paths = [p for p in openapi.get("paths", {}) if "gate3" in p]
    f2_on_main = subprocess.run(
        [
            "gh",
            "api",
            "repos/mycrivo/ngoinfo-grantpilot/contents/app/reports/agents/fact_safety_critic.py",
        ],
        cwd=REPO,
        capture_output=True,
    ).returncode == 0
    health = requests.get(f"{BASE_URL}/health", timeout=30)
    ok = gh.startswith(EXPECTED_DEPLOY_SHA_PREFIX) and f2_on_main and bool(gate3_paths)
    return {
        "github_main_sha_prefix": gh[:7],
        "f2_on_main": f2_on_main,
        "gate3_paths": gate3_paths,
        "health_status": health.status_code,
        "precondition_pass": ok,
    }


def _load_answer_key_rows() -> list[dict[str, str]]:
    p = DOC_DIR / "04_FCDO_Answer_Key_DO_NOT_INCLUDE_IN_DOCUMENTS.docx"
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras = []
    for p_el in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        texts = [
            t.text
            for t in p_el.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
            if t.text
        ]
        if texts:
            paras.append("".join(texts))
    # Skip header lines; rows are groups of 5 after line 4
    data_lines = paras[4:]
    rows: list[dict[str, str]] = []
    for i in range(0, len(data_lines) - 4, 5):
        chunk = data_lines[i : i + 5]
        if len(chunk) < 5:
            break
        rows.append(
            {
                "issue_type": chunk[0],
                "planted_problem": chunk[1],
                "documents": chunk[2],
                "true_value": chunk[3],
                "expected_catch": chunk[4],
            }
        )
    return rows


def _resolve_gate1_conflicts(kb: dict[str, Any]) -> tuple[dict[str, Any], list[dict]]:
    """Apply answer-key true values to unresolved conflicts where identifiable."""
    kb = dict(kb)
    conflicts = list(kb.get("conflicts") or [])
    actions: list[dict] = []
    if not conflicts:
        return kb, actions

    resolved_conflicts = []
    for c in conflicts:
        c = dict(c)
        desc = json.dumps(c).lower()
        chosen = None
        reason = None
        if "1240000" in desc or "1184000" in desc or "1184000" in desc.replace(",", ""):
            for v in c.get("values") or []:
                norm = str(v.get("normalized") or v.get("value") or "").replace(",", "")
                if "1240000" in norm:
                    chosen = v
                    reason = "answer_key budget true GBP 1,240,000"
                    break
        elif "684" in desc and "612" in desc:
            for v in c.get("values") or []:
                norm = str(v.get("normalized") or v.get("value") or "")
                if norm in ("684", "684.0"):
                    chosen = v
                    reason = "answer_key OP1.1 actual 684"
                    break
        elif "40" in desc and "24" in desc:
            for v in c.get("values") or []:
                norm = str(v.get("normalized") or v.get("value") or "")
                if norm == "31":
                    chosen = v
                    reason = "AR1 actual 31 latrine stances (achieved value in export)"
                    break
            if chosen is None:
                for v in c.get("values") or []:
                    norm = str(v.get("normalized") or v.get("value") or "")
                    if norm == "24":
                        chosen = v
                        reason = "answer_key spreadsheet Year 1 target 24 (defer full 40 endline)"
                        break
        if chosen is not None:
            c["resolved_value"] = chosen.get("normalized") or chosen.get("value")
            c["resolved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            actions.append(
                {
                    "conflict_id": c.get("conflict_id") or c.get("fact_key"),
                    "resolved_value": c["resolved_value"],
                    "reason": reason,
                }
            )
        resolved_conflicts.append(c)

    kb["conflicts"] = resolved_conflicts
    return kb, actions


def _requeue_job(job_id: str) -> None:
    _bootstrap_db_env()
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE report_jobs SET status='queued', error=NULL "
                "WHERE id = CAST(:j AS uuid)"
            ),
            {"j": job_id},
        )


def _collect_critic_claude_tokens(job_trace: dict) -> tuple[int, int, str | None]:
    critique = (job_trace or {}).get("stages", {}).get("critique", {})
    inp = int(critique.get("input_tokens") or 0)
    out = int(critique.get("output_tokens") or 0)
    model = critique.get("model_used")
    return inp, out, model


def _find_in_text(hay: str, needles: list[str]) -> list[str]:
    found = []
    h = hay.lower()
    for n in needles:
        if n.lower() in h:
            found.append(n)
    return found


def _score_row(
    row: dict[str, str],
    *,
    kb: dict,
    gap_keys: set[str],
    sections: list[dict],
    reconcile_actions: list[dict],
) -> dict[str, Any]:
    problem = row["planted_problem"].lower()
    true_val = row["true_value"]
    expected = row["expected_catch"].lower()
    conflicts = kb.get("conflicts") or []
    facts = kb.get("facts") or {}
    all_prose = " ".join(
        (s.get("content") or {}).get("text") or "" for s in sections
    ).lower()
    all_flags = []
    for s in sections:
        for f in s.get("critic_flags") or []:
            all_flags.append({**f, "section_key": s.get("section_key")})

    caught_at: list[str] = []
    evidence: list[str] = []

    # Reconcile / Gate 1 signals
    if any(
        k in problem
        for k in ("612", "684", "1184000", "1240000", "1,184", "1,240", "40", "24")
    ):
        for c in conflicts:
            blob = json.dumps(c).lower()
            if "612" in problem and "684" in blob:
                caught_at.append("reconcile")
                evidence.append(f"conflict record: {json.dumps(c)[:400]}")
            if "1184000" in problem or "1240000" in problem or "1,184" in problem:
                if "1240000" in blob or "1184000" in blob:
                    caught_at.append("reconcile")
                    evidence.append(f"conflict record: {json.dumps(c)[:400]}")
            if "40" in problem and "24" in problem and ("40" in blob and "24" in blob):
                caught_at.append("reconcile")
                evidence.append(f"conflict record: {json.dumps(c)[:400]}")
    for act in reconcile_actions:
        caught_at.append("Gate 1")
        evidence.append(f"Gate1 resolution: {json.dumps(act)}")

    # Gap agent
    if "op2.3" in problem or "op4.2" in problem or "missing" in row["issue_type"].lower():
        for gk in gap_keys:
            if "op2.3" in problem and "op2.3" in gk.lower():
                caught_at.append("gap")
                evidence.append(f"gap item_key={gk}")
            if "op4.2" in problem and "op4.2" in gk.lower():
                caught_at.append("gap")
                evidence.append(f"gap item_key={gk}")

    # F2 flags
    needles: list[str] = []
    if "612" in problem:
        needles.extend(["612", "684"])
    if "1184000" in problem or "1240000" in problem or "budget" in problem:
        needles.extend(["1,184", "1184000", "1,240", "1240000"])
    if "oct" in problem or "date" in row["issue_type"].lower():
        needles.extend(["01-oct", "30-sep", "15 oct", "14 oct", "1 oct"])
    if "681" in problem or "disaggregation" in problem:
        needles.extend(["681", "684", "58", "590", "33"])
    if "920,420" in problem or "880,000" in problem or "forecast" in problem:
        needles.extend(["920", "880", "694,860", "653,000"])
    if "392" in problem or "caregiver" in problem:
        needles.extend(["392", "caregiver"])

    for flag in all_flags:
        ct = (flag.get("claim_text") or "").lower()
        if any(n.lower() in ct for n in needles if n):
            caught_at.append("F2 flag")
            evidence.append(
                f"critic_flags[] section={flag.get('section_key')}: "
                f"{json.dumps(flag, default=str)}"
            )

    # Prose presence of wrong values without flag
    dangerous: list[str] = []
    if "612" in problem and "612" in all_prose:
        if not any("612" in (f.get("claim_text") or "") for f in all_flags):
            dangerous.append("612 in prose unflagged")
    if ("1184000" in problem or "1,184" in problem) and (
        "1,184" in all_prose or "1184000" in all_prose
    ):
        if not any("184" in (f.get("claim_text") or "") for f in all_flags):
            dangerous.append("old budget 1.184m in prose unflagged")

    where = " / ".join(dict.fromkeys(caught_at)) if caught_at else "NOT CAUGHT"
    return {
        "issue_type": row["issue_type"],
        "planted_problem": row["planted_problem"][:200],
        "true_intended": true_val[:120],
        "where_caught": where,
        "evidence": evidence[:5],
        "expected_catch_layer": row["expected_catch"][:120],
        "dangerous_unflagged_in_prose": dangerous,
    }


def main() -> int:
    print("=== FCDO planted-conflict prod walk ===", flush=True)
    pre = _verify_precondition()
    print(f"PRECONDITION {json.dumps(pre)}", flush=True)
    if not pre["precondition_pass"]:
        print("STOP: F2 not live on prod")
        return 1

    answer_key = _load_answer_key_rows()
    print(f"ANSWER_KEY rows={len(answer_key)}", flush=True)
    print(f"UPLOAD_SET {UPLOAD_FILES} omit_03={DOC03_OMITTED_REASON}", flush=True)

    email = f"fcdo-planted-{int(time.time())}@grantpilot-test.org"
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {mint_token(session, email)}"

    r = session.post(
        f"{BASE_URL}/api/reports",
        json={
            "reporting_period_start": "2025-04-01",
            "reporting_period_end": "2026-03-31",
            "funder_report_template_id": FCDO_TEMPLATE_ID,
        },
        timeout=60,
    )
    r.raise_for_status()
    report_id = r.json()["id"]
    print(f"CREATE report_id={report_id}", flush=True)

    for name in UPLOAD_FILES:
        path = DOC_DIR / name
        mime = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if name.endswith(".xlsx")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        with path.open("rb") as fh:
            ur = session.post(
                f"{BASE_URL}/api/reports/{report_id}/documents",
                files={"file": (name, fh, mime)},
                timeout=120,
            )
        ur.raise_for_status()
        print(f"UPLOAD {name}", flush=True)

    session.post(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60).raise_for_status()

    gate1_job = poll_job(
        session,
        report_id,
        label="to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_WAIT_GATE1,
    )
    if gate1_job.get("status") == "failed":
        print("STOP: failed before Gate 1", gate1_job.get("error"))
        return 1

    db1 = _db_read(report_id)
    kb_pre = db1["report"].get("knowledge_bank_json") or {}
    conflicts_pre = kb_pre.get("conflicts") or []
    recon_outcome = kb_pre.get("reconciliation_outcome")
    print(
        f"RECONCILE outcome={recon_outcome} conflicts={len(conflicts_pre)} "
        f"facts={len(kb_pre.get('facts') or {})}",
        flush=True,
    )
    for i, c in enumerate(conflicts_pre[:10]):
        print(f"  CONFLICT[{i}] {json.dumps(c, default=str)[:500]}", flush=True)

    xlsx_doc = next(
        (d for d in db1["documents"] if d["original_filename"] == XLSX_NAME), None
    )
    ej = (xlsx_doc or {}).get("extracted_json") or {}
    struct = ej.get("structured") or {}
    trace = ej.get("agent_trace") or {}
    d4_outcome = struct.get("extraction_outcome")
    print(
        f"D4 outcome={d4_outcome} attempt={trace.get('attempt_count')} "
        f"latency={trace.get('latency_ms')} degraded={trace.get('degraded_code')}",
        flush=True,
    )
    if d4_outcome == "degraded":
        print("STOP: D4 degraded")
        return 2

    kb_r = session.get(f"{BASE_URL}/api/reports/{report_id}/knowledge-bank", timeout=60)
    kb_r.raise_for_status()
    kb = kb_r.json().get("knowledge_bank_json") or kb_r.json()
    kb, gate1_actions = _resolve_gate1_conflicts(kb)
    print(f"GATE1 resolutions={json.dumps(gate1_actions)}", flush=True)

    g1 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{report_id}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": kb},
        timeout=60,
    )
    print(f"GATE1 status={g1.status_code} {g1.text[:200]}", flush=True)
    if g1.status_code != 200:
        return 1

    post_g1 = poll_job(
        session,
        report_id,
        label="post-gate1",
        until_status={"awaiting_human", "failed"},
        max_seconds=MAX_WAIT_POST_GATE1,
    )
    if post_g1.get("stage") != "synthesise":
        print(f"STOP: expected synthesise halt got {post_g1.get('stage')}")
        return 1

    db2 = _db_read(report_id)
    gaps = (db2["report"].get("gap_analysis_json") or {}).get("gaps") or []
    gap_keys = {g["item_key"] for g in gaps}
    answered, skipped, responses = [], [], {}
    for g in gaps:
        resp = _substantive_gap_answer(g)
        responses[g["item_key"]] = resp
        (answered if resp["disposition"] == "answered" else skipped).append(g["item_key"])
    print(f"GAPS={len(gaps)} GATE2 answered={len(answered)} skipped={len(skipped)}", flush=True)

    g2 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{report_id}/knowledge-bank/gate2/gap-responses",
        json={"responses": responses},
        timeout=180,
    )
    if g2.status_code != 200 or not g2.json().get("gate2_unlocked"):
        print(f"STOP gate2 {g2.status_code} {g2.text[:300]}")
        return 1

    post_g2 = poll_job(
        session,
        report_id,
        label="post-gate2-synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_WAIT_POST_GATE2,
    )
    if post_g2.get("status") == "failed":
        print("STOP: synthesis failed", post_g2.get("error"))
        return 1

    job_id = post_g2.get("job_id")
    print(f"SYNTH parked critique job_id={job_id}", flush=True)

    _requeue_job(str(job_id))
    print("REQUEUED for F2 critique", flush=True)

    post_crit = poll_job(
        session,
        report_id,
        label="post-critique",
        until_status={"awaiting_human", "failed"},
        until_stage={"export"},
        max_seconds=MAX_WAIT_CRITIQUE,
    )
    print(
        f"POST_CRITIQUE stage={post_crit.get('stage')} status={post_crit.get('status')} "
        f"error={post_crit.get('error')!r}",
        flush=True,
    )

    final_db = _db_read(report_id)
    kb_final = final_db["report"].get("knowledge_bank_json") or {}
    content = final_db["report"].get("content_json") or {}
    sections = content.get("sections") or []
    job_trace = final_db["job"].get("agent_trace_json") or {}
    critique_trace = (job_trace.get("stages") or {}).get("critique") or {}

    claude_in, claude_out = _collect_claude_tokens(final_db)
    critic_in, critic_out, critic_model = _collect_critic_claude_tokens(job_trace)
    oai_in, oai_out = _openai_synth_tokens(job_trace)

    claude_usd = (
        (claude_in + critic_in) * CLAUDE_INPUT_USD_PER_1M / 1_000_000
        + (claude_out + critic_out) * CLAUDE_OUTPUT_USD_PER_1M / 1_000_000
    )
    oai_usd = (
        oai_in * OPENAI_INPUT_USD_PER_1M / 1_000_000
        + oai_out * OPENAI_OUTPUT_USD_PER_1M / 1_000_000
    )

    scoring = [
        _score_row(
            row,
            kb=kb_final,
            gap_keys=gap_keys,
            sections=sections,
            reconcile_actions=gate1_actions,
        )
        for row in answer_key
    ]

    dangerous_all = []
    false_positives = []
    for s in sections:
        text = (s.get("content") or {}).get("text") or ""
        for f in s.get("critic_flags") or []:
            ct = f.get("claim_text") or ""
            if ct == "[section unverified]":
                false_positives.append(
                    {"section": s.get("section_key"), "flag": f, "note": "critic fail-closed"}
                )
            elif ct in text and ct in ("684", "472", "1240000", "GBP 1,240,000"):
                false_positives.append(
                    {
                        "section": s.get("section_key"),
                        "flag": f,
                        "note": "possible FP on KB-true value",
                    }
                )

    for row in scoring:
        dangerous_all.extend(row.get("dangerous_unflagged_in_prose") or [])

    artifact = {
        "report_id": report_id,
        "precondition": pre,
        "upload_set": UPLOAD_FILES,
        "doc03_omitted_reason": DOC03_OMITTED_REASON,
        "reconcile": {
            "outcome": recon_outcome,
            "conflicts_pre_gate1": conflicts_pre,
            "gate1_resolutions": gate1_actions,
        },
        "d4_xlsx": {
            "extraction_outcome": d4_outcome,
            "attempt_count": trace.get("attempt_count"),
            "latency_ms": trace.get("latency_ms"),
        },
        "gate2": {"answered": answered, "skipped": skipped, "gap_item_keys": sorted(gap_keys)},
        "critique_trace": critique_trace,
        "scoring_table": scoring,
        "dangerous_unflagged": dangerous_all,
        "false_positives": false_positives,
        "cost": {
            "claude_upstream_input": claude_in,
            "claude_upstream_output": claude_out,
            "claude_critic_input": critic_in,
            "claude_critic_output": critic_out,
            "claude_critic_model": critic_model,
            "claude_total_input": claude_in + critic_in,
            "claude_total_output": claude_out + critic_out,
            "claude_usd": claude_usd,
            "openai_input_tokens": oai_in,
            "openai_output_tokens": oai_out,
            "openai_usd": oai_usd,
            "total_usd": claude_usd + oai_usd,
            "critic_vendor": "Anthropic Messages API (Claude)",
        },
        "sections_summary": [
            {
                "section_key": s.get("section_key"),
                "generation_status": s.get("generation_status"),
                "critic_flags_count": len(s.get("critic_flags") or []),
                "critic_flags": s.get("critic_flags") or [],
            }
            for s in sections
        ],
        "content_json": content,
        "job": final_db["job"],
    }

    out_path = REPO / f"FCDO_PLANTED_CONFLICT_WALK_{report_id[:8]}.json"
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    print(f"ARTIFACT={out_path}", flush=True)
    print("\n=== SCORING TABLE ===", flush=True)
    print(json.dumps(scoring, indent=2), flush=True)
    print("\n=== DANGEROUS UNFLAGGED ===", flush=True)
    print(json.dumps(dangerous_all, indent=2), flush=True)
    print("\n=== COST ===", flush=True)
    print(json.dumps(artifact["cost"], indent=2), flush=True)

    ok = (
        post_crit.get("stage") == "export"
        and critique_trace.get("action") == "critique_completed"
    )
    print(f"STRUCTURAL_OK={ok}", flush=True)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
