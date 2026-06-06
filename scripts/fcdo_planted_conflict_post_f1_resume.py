#!/usr/bin/env python3
"""Resume post-F1 planted walk from gap retry through critique (throwaway)."""

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
    CLAUDE_INPUT_USD_PER_1M,
    CLAUDE_OUTPUT_USD_PER_1M,
    MAX_WAIT_POST_GATE1,
    MAX_WAIT_POST_GATE2,
    OPENAI_INPUT_USD_PER_1M,
    OPENAI_OUTPUT_USD_PER_1M,
    UPLOAD_FILES,
    _bootstrap_db_env,
    _collect_claude_tokens,
    _db_read,
    _openai_synth_tokens,
    _substantive_gap_answer,
    mint_token,
    poll_job,
)

MAX_WAIT_CRITIQUE = 1800
from scripts.fcdo_planted_conflict_post_f1_walk import (  # noqa: E402
    DOC03_OMITTED_REASON,
    PRIOR_WALK_REPORT_ID,
    _audit_f1_hygiene,
    _collect_critic_claude_tokens,
    _load_answer_key_rows,
    _requeue_job,
    _score_planted_row,
)

REPORT_ID = os.environ.get("REPORT_ID", "fda69a23-7e31-4ff9-afaf-0b5486eac54b")
JOB_ID = os.environ.get("JOB_ID", "9148e0a2-dfd7-4dd8-9215-970c7293e7a2")


def _user_email(report_id: str) -> str:
    _bootstrap_db_env()
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        return str(
            conn.execute(
                text(
                    """
                    SELECT u.email FROM donor_reports dr
                    JOIN users u ON dr.user_id = u.id
                    WHERE dr.id = CAST(:r AS uuid)
                    """
                ),
                {"r": report_id},
            ).scalar()
        )


def main() -> int:
    _bootstrap_db_env()
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE report_jobs SET status='queued', error=NULL WHERE id = CAST(:j AS uuid)"),
            {"j": JOB_ID},
        )
    print(f"REQUEUED gap job {JOB_ID} for report {REPORT_ID}", flush=True)

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {mint_token(session, _user_email(REPORT_ID))}"

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
        print(f"STOP expected synthesise got {post_gap.get('stage')}")
        return 2

    db2 = _db_read(REPORT_ID)
    kb_pre = db2["report"].get("knowledge_bank_json") or {}
    conflicts_pre = kb_pre.get("conflicts") or []
    gaps = (db2["report"].get("gap_analysis_json") or {}).get("gaps") or []
    gap_keys = {g["item_key"] for g in gaps}
    answered, skipped, responses = [], [], {}
    for g in gaps:
        resp = _substantive_gap_answer(g)
        responses[g["item_key"]] = resp
        (answered if resp["disposition"] == "answered" else skipped).append(g["item_key"])
    print(f"GAPS={len(gaps)} answered={len(answered)} skipped={len(skipped)}", flush=True)

    g2 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{REPORT_ID}/knowledge-bank/gate2/gap-responses",
        json={"responses": responses},
        timeout=180,
    )
    if g2.status_code != 200 or not g2.json().get("gate2_unlocked"):
        print(f"STOP gate2 {g2.status_code} {g2.text[:300]}")
        return 3

    post_g2 = poll_job(
        session,
        REPORT_ID,
        label="synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_WAIT_POST_GATE2,
    )
    if post_g2.get("status") == "failed":
        print("STOP synthesis failed", post_g2.get("error"))
        return 4

    job_id = post_g2.get("job_id") or JOB_ID
    _requeue_job(str(job_id))
    print(f"REQUEUED for critique job_id={job_id}", flush=True)

    post_crit = poll_job(
        session,
        REPORT_ID,
        label="critique",
        until_status={"awaiting_human", "failed"},
        until_stage={"export"},
        max_seconds=MAX_WAIT_CRITIQUE,
    )
    print(
        f"FINAL stage={post_crit.get('stage')} status={post_crit.get('status')} "
        f"error={post_crit.get('error')!r}",
        flush=True,
    )

    final_db = _db_read(REPORT_ID)
    content = final_db["report"].get("content_json") or {}
    sections = content.get("sections") or []
    job_trace = final_db["job"].get("agent_trace_json") or {}
    critique_trace = (job_trace.get("stages") or {}).get("critique") or {}

    answer_key = _load_answer_key_rows()
    f1_audit = _audit_f1_hygiene(sections)
    scoring = [
        _score_planted_row(
            i + 1,
            row,
            conflicts_pre=conflicts_pre,
            gap_keys=gap_keys,
            gap_items=gaps,
            sections=sections,
            gate1_actions=[],
        )
        for i, row in enumerate(answer_key)
    ]
    dangerous_all = [d for row in scoring for d in row.get("dangerous_unflagged_in_prose") or []]

    false_positives = []
    for s in sections:
        text_body = (s.get("content") or {}).get("text") or ""
        for f in s.get("critic_flags") or []:
            if f.get("severity") != "BLOCK":
                continue
            ct = f.get("claim_text") or ""
            reason = (f.get("reason") or "").lower()
            if ct in text_body and "684" in ct and "cited" not in reason:
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
        "report_id": REPORT_ID,
        "prior_walk_report_id": PRIOR_WALK_REPORT_ID,
        "precondition": {"github_main_sha_prefix": "cd15e37", "f1_hygiene_live": True},
        "upload_set": UPLOAD_FILES,
        "doc03_omitted_reason": DOC03_OMITTED_REASON,
        "reconcile": {
            "outcome": kb_pre.get("reconciliation_outcome"),
            "conflicts_pre_gate1": conflicts_pre,
        },
        "gate2": {"answered": answered, "skipped": skipped, "gap_item_keys": sorted(gap_keys)},
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
                "critic_flags": s.get("critic_flags") or [],
            }
            for s in sections
        ],
        "final_job": {"stage": post_crit.get("stage"), "status": post_crit.get("status")},
        "gap_retry": True,
    }

    out_path = REPO / f"FCDO_PLANTED_CONFLICT_POST_F1_WALK_{REPORT_ID[:8]}.json"
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    print(f"ARTIFACT={out_path}", flush=True)
    print(json.dumps({"f1_hygiene_audit": f1_audit, "scoring": scoring, "cost": artifact["cost"]}, indent=2), flush=True)
    return 0 if post_crit.get("stage") == "export" else 5


if __name__ == "__main__":
    sys.exit(main())
