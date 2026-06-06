#!/usr/bin/env python3
"""Re-queue failed gap job and finish FCDO walk (throwaway)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.fcdo_d4_f1_fresh_prod_walk import (  # noqa: E402
    BASE_URL,
    MAX_WAIT_POST_GATE1,
    MAX_WAIT_POST_GATE2,
    OPENAI_INPUT_USD_PER_1M,
    OPENAI_OUTPUT_USD_PER_1M,
    CLAUDE_INPUT_USD_PER_1M,
    CLAUDE_OUTPUT_USD_PER_1M,
    XLSX_NAME,
    _bootstrap_db_env,
    _collect_claude_tokens,
    _db_read,
    _openai_synth_tokens,
    _substantive_gap_answer,
    mint_token,
    poll_job,
)

REPORT_ID = os.environ.get("REPORT_ID", "cabb8796-195b-4089-afab-94d6fe841d50")
JOB_ID = os.environ.get("JOB_ID", "cc879453-653f-4953-8619-d7c6e28634bb")


def main() -> int:
    _bootstrap_db_env()
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE report_jobs SET status='queued', error=NULL "
                "WHERE id = CAST(:j AS uuid)"
            ),
            {"j": JOB_ID},
        )
    print("REQUEUED gap job", flush=True)

    with engine.connect() as conn:
        email = conn.execute(
            text(
                """
                SELECT u.email FROM donor_reports dr
                JOIN users u ON dr.user_id = u.id
                WHERE dr.id = CAST(:r AS uuid)
                """
            ),
            {"r": REPORT_ID},
        ).scalar()

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {mint_token(session, str(email))}"

    post_gap = poll_job(
        session,
        REPORT_ID,
        label="gap-retry",
        until_status={"awaiting_human", "failed"},
        max_seconds=MAX_WAIT_POST_GATE1,
    )
    print(
        f"POST_GAP status={post_gap.get('status')} stage={post_gap.get('stage')} "
        f"error={post_gap.get('error')!r}",
        flush=True,
    )
    if post_gap.get("status") == "failed":
        return 2
    if post_gap.get("stage") != "synthesise":
        print(f"STOP: expected synthesise halt, got {post_gap.get('stage')}")
        return 2

    db2 = _db_read(REPORT_ID)
    facts = (db2["report"].get("knowledge_bank_json") or {}).get("facts") or {}
    actual_facts = {k: v for k, v in facts.items() if "actual" in k.lower()}
    print(f"KB facts={len(facts)} actuals={len(actual_facts)}", flush=True)
    for k, v in list(actual_facts.items())[:10]:
        val = v.get("value") if isinstance(v, dict) else v
        print(f"  ACTUAL {k}={val!r}", flush=True)

    gaps = (db2["report"].get("gap_analysis_json") or {}).get("gaps") or []
    answered, skipped, responses = [], [], {}
    for g in gaps:
        resp = _substantive_gap_answer(g)
        responses[g["item_key"]] = resp
        (answered if resp["disposition"] == "answered" else skipped).append(
            g["item_key"]
        )
    print(f"GATE2 gaps={len(gaps)} answered={len(answered)} skipped={len(skipped)}", flush=True)

    g2 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{REPORT_ID}/knowledge-bank/gate2/gap-responses",
        json={"responses": responses},
        timeout=180,
    )
    print(f"GATE2 status={g2.status_code} {g2.text[:250]}", flush=True)
    if g2.status_code != 200:
        return 3

    post_g2 = poll_job(
        session,
        REPORT_ID,
        label="synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_WAIT_POST_GATE2,
    )
    print(
        f"FINAL stage={post_g2.get('stage')} status={post_g2.get('status')}",
        flush=True,
    )

    final_db = _db_read(REPORT_ID)
    content = final_db["report"].get("content_json") or {}
    sections = content.get("sections") or []
    job_trace = final_db["job"].get("agent_trace_json") or {}
    xlsx = next(
        (d for d in final_db["documents"] if d["original_filename"] == XLSX_NAME),
        {},
    )
    ej = xlsx.get("extracted_json") or {}
    tr = ej.get("agent_trace") or {}
    st = ej.get("structured") or {}

    claude_in, claude_out = _collect_claude_tokens(final_db)
    oai_in, oai_out = _openai_synth_tokens(job_trace)
    claude_usd = (
        claude_in * CLAUDE_INPUT_USD_PER_1M / 1_000_000
        + claude_out * CLAUDE_OUTPUT_USD_PER_1M / 1_000_000
    )
    oai_usd = (
        oai_in * OPENAI_INPUT_USD_PER_1M / 1_000_000
        + oai_out * OPENAI_OUTPUT_USD_PER_1M / 1_000_000
    )

    artifact = {
        "report_id": REPORT_ID,
        "precondition": {"github_main_prefix": "98d7512", "d4_fix_live": True},
        "d4_xlsx": {
            "outcome": st.get("extraction_outcome"),
            "attempt_count": tr.get("attempt_count"),
            "latency_ms": tr.get("latency_ms"),
            "indicator_rows": len(st.get("indicators") or []),
            "degraded_code": tr.get("degraded_code"),
        },
        "kb": {
            "facts_total": len(facts),
            "actual_keys_count": len(actual_facts),
            "actual_sample": {
                k: (v.get("value") if isinstance(v, dict) else v)
                for k, v in list(actual_facts.items())[:20]
            },
        },
        "gate2": {"answered": answered, "skipped": skipped},
        "job": {
            "stage": final_db["job"].get("stage"),
            "status": final_db["job"].get("status"),
            "agent_trace_json": job_trace,
        },
        "cost": {
            "claude_input_tokens": claude_in,
            "claude_output_tokens": claude_out,
            "claude_usd": claude_usd,
            "openai_input_tokens": oai_in,
            "openai_output_tokens": oai_out,
            "openai_usd": oai_usd,
            "total_usd": claude_usd + oai_usd,
        },
        "content_json": content,
    }

    out_path = REPO / f"FCDO_D4_F1_WALK_{REPORT_ID[:8]}.json"
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    print(f"ARTIFACT={out_path}", flush=True)

    for sec in sections:
        print("\n---", flush=True)
        print(f"section_key={sec.get('section_key')}", flush=True)
        print(f"label={sec.get('label')}", flush=True)
        print(f"generation_status={sec.get('generation_status')}", flush=True)
        constraints = sec.get("constraints_applied") or {}
        print(f"word_limit_respected={constraints.get('word_limit_respected')}", flush=True)
        block = sec.get("content") or {}
        print(f"evidence_used={json.dumps(block.get('evidence_used') or [])}", flush=True)
        if sec.get("generation_status") == "FAILED":
            print(f"failure_reason={sec.get('failure_reason')!r}", flush=True)
        else:
            print("FULL_TEXT_BEGIN", flush=True)
            print(block.get("text") or "", flush=True)
            print("FULL_TEXT_END", flush=True)

    print("\n=== COST ===", flush=True)
    print(json.dumps(artifact["cost"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
