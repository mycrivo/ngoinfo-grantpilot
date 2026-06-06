#!/usr/bin/env python3
"""Post-F1-hygiene planted-conflict prod walk (throwaway)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import unicodedata
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

EXPECTED_F1_SHA_PREFIX = "d19b9de"
MAX_WAIT_CRITIQUE = 1800
DOC03_OMITTED_REASON = (
    "Answer-key Document 3 is spreadsheet content fully carried by the .xlsx; "
    "the .docx duplicate only triggers DEGRADED_EXTRACTION_UNPARSEABLE without "
    "unique planted conflicts."
)
PRIOR_WALK_REPORT_ID = "5026ab66-9e30-413b-a823-7931c16fe435"
PRIOR_CITATION_RESOLUTION_BLOCKS = 55  # from walk 5026ab66 artifact


def _verify_precondition() -> dict:
    gh = subprocess.check_output(
        ["gh", "api", "repos/mycrivo/ngoinfo-grantpilot/commits/main", "--jq", ".sha"],
        cwd=REPO,
        text=True,
    ).strip()
    f1_on_main = subprocess.run(
        [
            "gh",
            "api",
            "repos/mycrivo/ngoinfo-grantpilot/contents/app/reports/services/synthesis_output_hygiene.py",
        ],
        cwd=REPO,
        capture_output=True,
    ).returncode == 0
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
    ok = gh.startswith(EXPECTED_F1_SHA_PREFIX) and f1_on_main and f2_on_main and bool(gate3_paths)
    return {
        "github_main_sha_prefix": gh[:7],
        "f1_hygiene_on_main": f1_on_main,
        "f2_on_main": f2_on_main,
        "gate3_paths": gate3_paths,
        "health_status": health.status_code,
        "precondition_pass": ok,
        "required_sha_prefix": EXPECTED_F1_SHA_PREFIX,
    }


def _load_answer_key_rows() -> list[dict[str, str]]:
    p = DOC_DIR / "04_FCDO_Answer_Key_DO_NOT_INCLUDE_IN_DOCUMENTS.docx"
    with zipfile.ZipFile(p) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paras: list[str] = []
    for pel in root.iter(f"{ns}p"):
        texts = [t.text for t in pel.iter(f"{ns}t") if t.text]
        if texts:
            paras.append("".join(texts))
    rows: list[dict[str, str]] = []
    for i in range(7, len(paras) - 4, 5):
        chunk = paras[i : i + 5]
        if len(chunk) < 5:
            break
        rows.append(
            {
                "issue_type": chunk[0],
                "planted_problem": chunk[1],
                "documents": chunk[2],
                "true_intended": chunk[3],
                "expected_catch_layer": chunk[4],
            }
        )
    return rows


def _resolve_gate1_conflicts(kb: dict[str, Any]) -> tuple[dict[str, Any], list[dict]]:
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
        if "1240000" in desc or "1184000" in desc:
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
            text("UPDATE report_jobs SET status='queued', error=NULL WHERE id = CAST(:j AS uuid)"),
            {"j": job_id},
        )


def _collect_critic_claude_tokens(job_trace: dict) -> tuple[int, int, str | None]:
    critique = (job_trace or {}).get("stages", {}).get("critique", {})
    return (
        int(critique.get("input_tokens") or 0),
        int(critique.get("output_tokens") or 0),
        critique.get("model_used"),
    )


def _non_ascii_digits(s: str) -> bool:
    return any(c.isdigit() and ord(c) > 127 for c in s)


def _control_chars(s: str) -> list[str]:
    return [
        f"U+{ord(c):04X}"
        for c in s
        if ord(c) < 32 and c not in "\n\r\t"
    ]


def _is_citation_resolution_flag(flag: dict) -> bool:
    reason = (flag.get("reason") or "").lower()
    needles = (
        "no resolved value",
        "not present in cited",
        "not in cited_sources",
        "cited source",
        "evidence_used",
        "bengali",
        "variant key",
        "malformed",
        "does not match any",
    )
    return flag.get("severity") == "BLOCK" and any(n in reason for n in needles)


def _audit_f1_hygiene(sections: list[dict]) -> dict[str, Any]:
    citation_blocks: list[dict] = []
    all_eu: list[str] = []
    dropped_all: list[dict] = []
    prose_ctrl: list[dict] = []
    eu_non_ascii: list[dict] = []

    for sec in sections:
        sk = sec.get("section_key")
        content = sec.get("content") or {}
        text_body = content.get("text") or ""
        ctrl = _control_chars(text_body)
        if ctrl:
            prose_ctrl.append({"section_key": sk, "control_chars": ctrl[:8]})
        for ref in content.get("evidence_used") or []:
            all_eu.append(ref)
            if isinstance(ref, str) and ref.startswith("fact:"):
                key = ref[5:]
                if _non_ascii_digits(key):
                    eu_non_ascii.append({"section_key": sk, "ref": ref})
        for dropped in content.get("dropped_citations") or []:
            dropped_all.append({"section_key": sk, "dropped": dropped})
        for flag in sec.get("critic_flags") or []:
            if _is_citation_resolution_flag(flag):
                citation_blocks.append(
                    {"section_key": sk, "severity": flag.get("severity"), "reason": flag.get("reason"), "claim_text": flag.get("claim_text")}
                )

    total_blocks = sum(
        1 for s in sections for f in (s.get("critic_flags") or []) if f.get("severity") == "BLOCK"
    )
    return {
        "citation_resolution_block_count": len(citation_blocks),
        "prior_walk_citation_resolution_blocks_approx": PRIOR_CITATION_RESOLUTION_BLOCKS,
        "total_critic_blocks": total_blocks,
        "citation_resolution_flags": citation_blocks,
        "evidence_used_non_ascii_digit_keys": eu_non_ascii,
        "prose_control_char_hits": prose_ctrl,
        "dropped_citations": dropped_all,
        "evidence_used_count": len(all_eu),
    }


def _score_planted_row(
    idx: int,
    row: dict[str, str],
    *,
    conflicts_pre: list,
    gap_keys: set[str],
    gap_items: list[dict],
    sections: list[dict],
    gate1_actions: list[dict],
) -> dict[str, Any]:
    problem = row["planted_problem"].lower()
    issue = row["issue_type"].lower()
    layers: list[str] = []
    evidence: list[str] = []

    for c in conflicts_pre:
        blob = json.dumps(c).lower()
        if "612" in problem and "612" in blob and "684" in blob:
            layers.append("RECONCILER")
            evidence.append(json.dumps(c, default=str)[:500])
        if ("1184000" in problem or "1,184" in problem) and ("1184000" in blob or "1240000" in blob):
            layers.append("RECONCILER")
            evidence.append(json.dumps(c, default=str)[:500])
        if "date" in issue and ("2024-10-01" in blob or "2025-09-30" in blob or "october to september" in blob):
            layers.append("RECONCILER")
            evidence.append(json.dumps(c, default=str)[:500])
        if "880" in problem and "920" in problem and ("880" in blob or "920" in blob):
            layers.append("RECONCILER")
            evidence.append(json.dumps(c, default=str)[:500])
        if "681" in problem and ("681" in blob or "684" in blob):
            layers.append("RECONCILER")
            evidence.append(json.dumps(c, default=str)[:500])

    for act in gate1_actions:
        layers.append("RECONCILER")
        evidence.append(f"Gate1 resolution: {json.dumps(act)}")

    for g in gap_items:
        gk = (g.get("item_key") or "").lower()
        ref = (g.get("required_item_ref") or "").lower()
        q = (g.get("question") or "").lower()
        if "op2.3" in problem and ("op2.3" in gk or "op2.3" in ref or "op2.3" in q or "safeguarding" in ref):
            layers.append("GAP")
            evidence.append(f"gap item_key={g.get('item_key')} ref={g.get('required_item_ref')}")
        if "op4.2" in problem and ("op4.2" in gk or "op4.2" in ref or "op4.2" in q or "learning brief" in q):
            layers.append("GAP")
            evidence.append(f"gap item_key={g.get('item_key')} ref={g.get('required_item_ref')}")
        if "missing indicator" in issue and ("op2.3" in problem or "op4.2" in problem):
            if "missing" in q or "provide" in q:
                if "GAP" not in layers:
                    layers.append("GAP")
                    evidence.append(f"gap item_key={g.get('item_key')}")

    all_flags = []
    for s in sections:
        for f in s.get("critic_flags") or []:
            all_flags.append({**f, "section_key": s.get("section_key")})

    needles: list[str] = []
    if "612" in problem:
        needles.extend(["612", "684", "op1.1"])
    if "1184000" in problem or "1240000" in problem or "budget" in issue:
        needles.extend(["1,184", "1184000", "1,240", "1240000", "budget"])
    if "date" in issue or "oct" in problem:
        needles.extend(["01-oct", "30-sep", "15 oct", "14 oct", "1 oct", "review window", "reporting period"])
    if "880" in problem or "920" in problem or "forecast" in issue:
        needles.extend(["880", "920", "694,860", "653,000", "forecast", "actual spend"])
    if "681" in problem or "disaggregation arithmetic" in issue:
        needles.extend(["681", "684", "58", "590", "33", "disaggreg"])
    if "392" in problem or "caregiver" in problem or "category" in issue:
        needles.extend(["392", "caregiver", "disaggreg", "gender", "age band"])
    if "buried" in issue or "formatting" in issue:
        needles.extend(["1.184", "1184000", "1240000", "october to september"])

    for flag in all_flags:
        blob = f"{flag.get('claim_text','')} {flag.get('reason','')}".lower()
        if any(n.lower() in blob for n in needles):
            layers.append("CRITIC")
            evidence.append(
                f"critic_flags[] section={flag.get('section_key')}: "
                f"{json.dumps({k: flag.get(k) for k in ('severity','claim_text','reason')}, default=str)}"
            )

    all_prose = " ".join((s.get("content") or {}).get("text") or "" for s in sections).lower()
    dangerous: list[str] = []
    if "612" in problem and "612" in all_prose and "CRITIC" not in layers:
        dangerous.append("612 appears in final prose without critic flag")
    if ("1184000" in problem or "1,184" in problem) and ("1,184" in all_prose or "1184000" in all_prose):
        if "CRITIC" not in layers and "RECONCILER" not in layers:
            dangerous.append("stale £1.184m budget in prose unflagged")

    layer_str = " / ".join(dict.fromkeys(layers)) if layers else "NOT CAUGHT"
    return {
        "num": idx,
        "issue_type": row["issue_type"],
        "planted_problem": row["planted_problem"][:220],
        "true_intended": row["true_intended"][:120],
        "expected_catch_layer": row["expected_catch_layer"][:120],
        "caught_at": layer_str,
        "evidence": evidence[:6],
        "dangerous_unflagged_in_prose": dangerous,
    }


def main() -> int:
    print("=== FCDO planted-conflict POST-F1 prod walk ===", flush=True)
    pre = _verify_precondition()
    print(f"PRECONDITION {json.dumps(pre)}", flush=True)
    if not pre["precondition_pass"]:
        print(f"STOP: F1 fix not live (need sha prefix {EXPECTED_F1_SHA_PREFIX})")
        return 1

    answer_key = _load_answer_key_rows()
    print(f"ANSWER_KEY rows={len(answer_key)}", flush=True)

    email = f"fcdo-postf1-{int(time.time())}@grantpilot-test.org"
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
            session.post(
                f"{BASE_URL}/api/reports/{report_id}/documents",
                files={"file": (name, fh, mime)},
                timeout=120,
            ).raise_for_status()
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
    print(
        f"RECONCILE outcome={kb_pre.get('reconciliation_outcome')} "
        f"conflicts_pre_gate1={len(conflicts_pre)} facts={len(kb_pre.get('facts') or {})}",
        flush=True,
    )
    for i, c in enumerate(conflicts_pre):
        print(f"  CONFLICT[{i}] {json.dumps(c, default=str)[:600]}", flush=True)

    xlsx_doc = next((d for d in db1["documents"] if d["original_filename"] == XLSX_NAME), None)
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

    for d in db1["documents"]:
        print(
            f"  CLASSIFY {d['original_filename']} -> {d.get('classification')} "
            f"status={d.get('extraction_status')}",
            flush=True,
        )

    kb_r = session.get(f"{BASE_URL}/api/reports/{report_id}/knowledge-bank", timeout=60)
    kb_r.raise_for_status()
    kb = kb_r.json().get("knowledge_bank_json") or kb_r.json()
    kb, gate1_actions = _resolve_gate1_conflicts(kb)
    g1 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{report_id}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": kb},
        timeout=60,
    )
    print(f"GATE1 status={g1.status_code} resolutions={json.dumps(gate1_actions)}", flush=True)
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
        print(f"STOP: expected synthesise halt got stage={post_g1.get('stage')}")
        return 1

    db2 = _db_read(report_id)
    gaps = (db2["report"].get("gap_analysis_json") or {}).get("gaps") or []
    gap_keys = {g["item_key"] for g in gaps}
    answered, skipped, responses = [], [], {}
    for g in gaps:
        resp = _substantive_gap_answer(g)
        responses[g["item_key"]] = resp
        (answered if resp["disposition"] == "answered" else skipped).append(g["item_key"])

    op23_gaps = [g for g in gaps if "op2.3" in json.dumps(g).lower() or "safeguarding" in json.dumps(g).lower()]
    op42_gaps = [g for g in gaps if "op4.2" in json.dumps(g).lower() or "learning brief" in json.dumps(g).lower()]
    print(
        f"GAPS total={len(gaps)} answered={len(answered)} skipped={len(skipped)} "
        f"op23_related={len(op23_gaps)} op42_related={len(op42_gaps)}",
        flush=True,
    )

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
    _requeue_job(str(job_id))
    print(f"REQUEUED job_id={job_id} for F2 critique", flush=True)

    post_crit = poll_job(
        session,
        report_id,
        label="post-critique",
        until_status={"awaiting_human", "failed"},
        until_stage={"export"},
        max_seconds=MAX_WAIT_CRITIQUE,
    )
    print(
        f"FINAL stage={post_crit.get('stage')} status={post_crit.get('status')} "
        f"error={post_crit.get('error')!r}",
        flush=True,
    )

    final_db = _db_read(report_id)
    content = final_db["report"].get("content_json") or {}
    sections = content.get("sections") or []
    job_trace = final_db["job"].get("agent_trace_json") or {}
    critique_trace = (job_trace.get("stages") or {}).get("critique") or {}

    f1_audit = _audit_f1_hygiene(sections)
    scoring = [
        _score_planted_row(i + 1, row, conflicts_pre=conflicts_pre, gap_keys=gap_keys, gap_items=gaps, sections=sections, gate1_actions=gate1_actions)
        for i, row in enumerate(answer_key)
    ]
    dangerous_all = [d for row in scoring for d in row.get("dangerous_unflagged_in_prose") or []]

    false_positives = []
    for s in sections:
        text_body = (s.get("content") or {}).get("text") or ""
        for f in s.get("critic_flags") or []:
            ct = f.get("claim_text") or ""
            if f.get("severity") != "BLOCK":
                continue
            if ct in ("684", "472", "1240000") or ct.startswith("GBP 1,240"):
                if ct in text_body and not _is_citation_resolution_flag(f):
                    false_positives.append({"section": s.get("section_key"), "flag": f})

    claude_in, claude_out = _collect_claude_tokens(final_db)
    critic_in, critic_out, critic_model = _collect_critic_claude_tokens(job_trace)
    oai_in, oai_out = _openai_synth_tokens(job_trace)
    claude_usd = (
        (claude_in + critic_in) * CLAUDE_INPUT_USD_PER_1M / 1_000_000
        + (claude_out + critic_out) * CLAUDE_OUTPUT_USD_PER_1M / 1_000_000
    )
    oai_usd = oai_in * OPENAI_INPUT_USD_PER_1M / 1_000_000 + oai_out * OPENAI_OUTPUT_USD_PER_1M / 1_000_000

    artifact = {
        "report_id": report_id,
        "prior_walk_report_id": PRIOR_WALK_REPORT_ID,
        "precondition": pre,
        "upload_set": UPLOAD_FILES,
        "doc03_omitted_reason": DOC03_OMITTED_REASON,
        "reconcile": {
            "outcome": kb_pre.get("reconciliation_outcome"),
            "conflicts_pre_gate1": conflicts_pre,
            "gate1_resolutions": gate1_actions,
        },
        "d4_xlsx": {
            "extraction_outcome": d4_outcome,
            "attempt_count": trace.get("attempt_count"),
            "latency_ms": trace.get("latency_ms"),
        },
        "gate2": {
            "answered": answered,
            "skipped": skipped,
            "gap_item_keys": sorted(gap_keys),
            "op23_related_gaps": op23_gaps,
            "op42_related_gaps": op42_gaps,
        },
        "f1_hygiene_audit": f1_audit,
        "three_layer_scoring": scoring,
        "dangerous_unflagged": dangerous_all,
        "false_positives": false_positives,
        "critique_trace": critique_trace,
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
        },
        "sections_summary": [
            {
                "section_key": s.get("section_key"),
                "generation_status": s.get("generation_status"),
                "critic_flags_count": len(s.get("critic_flags") or []),
            }
            for s in sections
        ],
        "final_job": {"stage": post_crit.get("stage"), "status": post_crit.get("status")},
    }

    out_path = REPO / f"FCDO_PLANTED_CONFLICT_POST_F1_WALK_{report_id[:8]}.json"
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    print(f"ARTIFACT={out_path}", flush=True)
    print("\n=== F1 HYGIENE AUDIT ===", flush=True)
    print(json.dumps(f1_audit, indent=2), flush=True)
    print("\n=== THREE-LAYER SCORING ===", flush=True)
    print(json.dumps(scoring, indent=2), flush=True)
    return 0 if post_crit.get("stage") == "export" else 3


if __name__ == "__main__":
    sys.exit(main())
