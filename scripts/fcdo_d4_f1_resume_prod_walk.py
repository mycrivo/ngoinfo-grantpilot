#!/usr/bin/env python3
"""Resume FCDO walk from report_id (throwaway)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

# Import helpers from main walk script
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.fcdo_d4_f1_fresh_prod_walk import (  # noqa: E402
    BASE_URL,
    MAX_WAIT_GATE1,
    MAX_WAIT_POST_GATE1,
    MAX_WAIT_POST_GATE2,
    _bootstrap_db_env,
    _collect_claude_tokens,
    _db_read,
    _openai_synth_tokens,
    _substantive_gap_answer,
    mint_token,
    poll_job,
    CLAUDE_INPUT_USD_PER_1M,
    CLAUDE_OUTPUT_USD_PER_1M,
    OPENAI_INPUT_USD_PER_1M,
    OPENAI_OUTPUT_USD_PER_1M,
    XLSX_NAME,
)

REPORT_ID = os.environ.get("REPORT_ID", "cabb8796-195b-4089-afab-94d6fe841d50")


def _owner_email(report_id: str) -> str:
    _bootstrap_db_env()
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as c:
        row = c.execute(
            text(
                """
                SELECT u.email FROM donor_reports dr
                JOIN users u ON dr.user_id = u.id
                WHERE dr.id = CAST(:r AS uuid)
                """
            ),
            {"r": report_id},
        ).first()
    if not row:
        raise RuntimeError(f"owner not found for report {report_id}")
    return str(row[0])


def main() -> int:
    email = _owner_email(REPORT_ID)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {mint_token(session, email)}"

    print(f"RESUME report_id={REPORT_ID}", flush=True)

    gate1_job = poll_job(
        session,
        REPORT_ID,
        label="to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_WAIT_GATE1,
    )
    if gate1_job.get("status") == "failed":
        print("STOP: failed before gate1")
        return 1

    db1 = _db_read(REPORT_ID)
    xlsx_doc = next(
        (d for d in db1["documents"] if d["original_filename"] == XLSX_NAME),
        None,
    )
    ej = (xlsx_doc or {}).get("extracted_json") or {}
    struct = ej.get("structured") or {}
    trace = ej.get("agent_trace") or {}
    print(
        f"D4_XLSX outcome={struct.get('extraction_outcome')} attempt={trace.get('attempt_count')} "
        f"latency_ms={trace.get('latency_ms')} rows={len(struct.get('indicators') or [])}",
        flush=True,
    )

    kb_r = session.get(f"{BASE_URL}/api/reports/{REPORT_ID}/knowledge-bank", timeout=60)
    kb_r.raise_for_status()
    kb = kb_r.json().get("knowledge_bank_json") or kb_r.json()

    g1 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{REPORT_ID}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": kb},
        timeout=60,
    )
    g1.raise_for_status()
    print(f"GATE1_CONFIRM at={g1.json().get('gate1_confirmed_at')}", flush=True)

    post_g1 = poll_job(
        session,
        REPORT_ID,
        label="post-gate1",
        until_status={"awaiting_human", "failed"},
        max_seconds=MAX_WAIT_POST_GATE1,
    )

    db2 = _db_read(REPORT_ID)
    facts = (db2["report"].get("knowledge_bank_json") or {}).get("facts") or {}
    actual_facts = {k: v for k, v in facts.items() if "actual" in k.lower()}
    print(f"KB facts_total={len(facts)} actual_keys={len(actual_facts)}", flush=True)
    for k, v in list(actual_facts.items())[:10]:
        val = v.get("value") if isinstance(v, dict) else v
        print(f"  ACTUAL {k}={val!r}", flush=True)

    gaps = (db2["report"].get("gap_analysis_json") or {}).get("gaps") or []
    answered, skipped, responses = [], [], {}
    for g in gaps:
        resp = _substantive_gap_answer(g)
        responses[g["item_key"]] = resp
        (answered if resp["disposition"] == "answered" else skipped).append(g["item_key"])

    print(f"GATE2 answered={len(answered)} skipped={len(skipped)}", flush=True)
    g2 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{REPORT_ID}/knowledge-bank/gate2/gap-responses",
        json={"responses": responses},
        timeout=180,
    )
    print(f"GATE2 status={g2.status_code}", flush=True)
    if g2.status_code != 200:
        print(g2.text[:500])
        return 1

    post_g2 = poll_job(
        session,
        REPORT_ID,
        label="post-gate2-synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_WAIT_POST_GATE2,
    )

    final_db = _db_read(REPORT_ID)
    content = final_db["report"].get("content_json") or {}
    sections = content.get("sections") or []
    job_trace = final_db["job"].get("agent_trace_json") or {}

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
        "d4_xlsx": {
            "extraction_outcome": struct.get("extraction_outcome"),
            "attempt_count": trace.get("attempt_count"),
            "latency_ms": trace.get("latency_ms"),
            "indicator_rows": len(struct.get("indicators") or []),
        },
        "kb": {
            "facts_total": len(facts),
            "actual_facts_sample": {
                k: (v.get("value") if isinstance(v, dict) else v)
                for k, v in list(actual_facts.items())[:15]
            },
        },
        "gate2": {"answered": answered, "skipped": skipped},
        "job": final_db["job"],
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
