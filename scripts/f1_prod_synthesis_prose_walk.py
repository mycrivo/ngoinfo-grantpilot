#!/usr/bin/env python3
"""Disposable F1 prod prose walk — resume synthesise checkpoint, live OpenAI, readback."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

BASE_URL = os.environ.get(
    "BASE_URL", "https://ngoinfo-grantpilot-production.up.railway.app"
).rstrip("/")
POLL_SECONDS = 15
MAX_WAIT_SYNTH = 1800
KNOWN_REPORT = "fe6bf98b-70b7-46f2-9bc2-a1306546af18"

# OpenAI gpt-5.4 list pricing (USD per 1M tokens) — update if console differs
OPENAI_INPUT_USD_PER_1M = 2.50
OPENAI_OUTPUT_USD_PER_1M = 10.00


def _bootstrap_prod_env() -> None:
    """Inject public DATABASE_URL + backend secrets for local execution against prod."""
    import shutil
    import subprocess

    repo = REPO
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise RuntimeError("railway CLI not found on PATH")

    def _railway_vars(*extra: str) -> dict:
        cmd = [railway, "variables", "--json", *extra]
        out = subprocess.check_output(cmd, cwd=repo, text=True)
        return json.loads(out)

    if "DATABASE_URL" not in os.environ or "railway.internal" in os.environ.get(
        "DATABASE_URL", ""
    ):
        pg = _railway_vars("--service", "Postgres")
        public = pg.get("DATABASE_PUBLIC_URL") or pg.get("DATABASE_URL")
        if not public:
            raise RuntimeError("DATABASE_PUBLIC_URL not found on Postgres service")
        os.environ["DATABASE_URL"] = public
        print("BOOTSTRAP DATABASE_URL=public proxy", flush=True)

    backend = _railway_vars()
    for key, value in backend.items():
        if value is None or key.startswith("RAILWAY_"):
            continue
        if key == "DATABASE_URL":
            continue
        os.environ.setdefault(key, str(value))


def _find_checkpoints(session_factory) -> list[dict]:
    from app.reports.models.donor_report import DonorReport
    from app.reports.models.enums import ReportJobStage, ReportJobStatus
    from app.reports.models.report_job import ReportJob

    db = session_factory()
    try:
        rows = (
            db.query(ReportJob, DonorReport)
            .join(DonorReport, ReportJob.donor_report_id == DonorReport.id)
            .filter(
                ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
                ReportJob.stage == ReportJobStage.SYNTHESISE.value,
            )
            .order_by(ReportJob.started_at.desc().nullslast())
            .all()
        )
        out: list[dict] = []
        for job, report in rows:
            kb = report.knowledge_bank_json or {}
            facts = kb.get("facts") or {}
            out.append(
                {
                    "report_id": str(report.id),
                    "job_id": str(job.id),
                    "facts_count": len(facts),
                    "gate1": kb.get("gate1_confirmed_at"),
                    "gate2": kb.get("gate2_confirmed_at"),
                    "reconciliation_outcome": kb.get("reconciliation_outcome"),
                }
            )
        return out
    finally:
        db.close()


def _pick_checkpoint(candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    for c in candidates:
        if c["report_id"] == KNOWN_REPORT and c.get("gate2") and c.get("facts_count", 0) > 0:
            return c
    for c in candidates:
        if c.get("gate2") and c.get("facts_count", 0) >= 10:
            return c
    for c in candidates:
        if c.get("gate2"):
            return c
    return candidates[0]


def _usage_totals() -> dict:
    return {"input_tokens": 0, "output_tokens": 0, "sections": 0}


def _make_tracking_query_fn(totals: dict):
    from app.core.config import get_settings
    from app.integrations.openai_client import OpenAIClient
    from app.reports.ai.prompts.synthesis import REPORT_SYNTHESIS_SYSTEM_PROMPT
    from app.reports.services.report_synthesis_service import (
        _extract_json_payload,
        _max_tokens_for_section,
        SYNTHESIS_FREQUENCY_PENALTY,
        SYNTHESIS_TEMPERATURE,
    )

    settings = get_settings()
    client = OpenAIClient()

    def _query(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        word_limit = 900
        if '"word_limit":' in user_prompt:
            try:
                idx = user_prompt.index('"word_limit":')
                frag = user_prompt[idx : idx + 40]
                word_limit = int(frag.split(":")[1].split(",")[0].strip())
            except (ValueError, IndexError):
                pass
        response = client.create_chat_completion(
            model=settings.OPENAI_MODEL_PRIMARY,
            fallback_model=settings.OPENAI_MODEL_FALLBACK,
            messages=[
                {"role": "system", "content": system_prompt or REPORT_SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=SYNTHESIS_TEMPERATURE,
            top_p=1.0,
            frequency_penalty=SYNTHESIS_FREQUENCY_PENALTY,
            presence_penalty=0.0,
            max_tokens=_max_tokens_for_section(word_limit),
            feature="report_synthesis",
        )
        usage = response.get("usage") or {}
        totals["input_tokens"] += int(usage.get("prompt_tokens") or 0)
        totals["output_tokens"] += int(usage.get("completion_tokens") or 0)
        totals["sections"] += 1
        return _extract_json_payload(response)

    return _query


def _re_enqueue(session_factory, report_id: str) -> bool:
    import uuid

    from app.reports.services.gate2_gap_answer_service import re_enqueue_gate2_job

    db = session_factory()
    try:
        job = re_enqueue_gate2_job(db, donor_report_id=uuid.UUID(report_id))
        if job is None:
            return False
        db.commit()
        return True
    finally:
        db.close()


def _run_synthesis_direct(session_factory, report_id: str, totals: dict) -> dict:
    import uuid

    from app.reports.models.enums import ReportJobStage, ReportJobStatus
    from app.reports.models.report_job import ReportJob
    from app.reports.services.report_synthesis_service import synthesise_and_persist

    db = session_factory()
    try:
        result = asyncio.run(
            synthesise_and_persist(
                db,
                uuid.UUID(report_id),
                query_fn_synthesis=_make_tracking_query_fn(totals),
            )
        )
        job = (
            db.query(ReportJob)
            .filter(ReportJob.donor_report_id == uuid.UUID(report_id))
            .order_by(ReportJob.started_at.desc().nullslast())
            .first()
        )
        if job:
            trace = dict(job.agent_trace_json or {})
            stages = dict(trace.get("stages") or {})
            stages["synthesise"] = {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "action": "synthesise_completed",
                "section_count": result.section_count,
                "generated": result.generated,
                "failed": result.failed,
                "degraded": result.degraded,
                "openai_input_tokens": totals["input_tokens"],
                "openai_output_tokens": totals["output_tokens"],
            }
            stages["critique"] = {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "action": "parked_at_critique_boundary",
            }
            trace["stages"] = stages
            job.agent_trace_json = trace
            job.stage = ReportJobStage.CRITIQUE.value
            job.status = ReportJobStatus.AWAITING_HUMAN.value
            db.add(job)
            db.commit()
        return {
            "section_count": result.section_count,
            "generated": result.generated,
            "failed": result.failed,
        }
    finally:
        db.close()


def _read_report(session_factory, report_id: str) -> dict:
    import uuid

    from app.reports.models.donor_report import DonorReport
    from app.reports.models.report_job import ReportJob

    db = session_factory()
    try:
        report = db.get(DonorReport, uuid.UUID(report_id))
        job = (
            db.query(ReportJob)
            .filter(ReportJob.donor_report_id == uuid.UUID(report_id))
            .order_by(ReportJob.started_at.desc().nullslast())
            .first()
        )
        return {
            "content_json": report.content_json if report else {},
            "job": {
                "stage": job.stage if job else None,
                "status": job.status if job else None,
                "agent_trace_json": job.agent_trace_json if job else {},
            },
            "kb_facts": len((report.knowledge_bank_json or {}).get("facts") or {})
            if report
            else 0,
        }
    finally:
        db.close()


def _poll_db_job(session_factory, report_id: str, max_seconds: int) -> dict:
    import uuid

    from app.reports.models.report_job import ReportJob

    deadline = time.time() + max_seconds
    last = {}
    while time.time() < deadline:
        db = session_factory()
        try:
            job = (
                db.query(ReportJob)
                .filter(ReportJob.donor_report_id == uuid.UUID(report_id))
                .order_by(ReportJob.started_at.desc().nullslast())
                .first()
            )
            if job:
                last = {
                    "stage": job.stage,
                    "status": job.status,
                    "error": job.error,
                    "agent_trace_json": job.agent_trace_json or {},
                }
                print(
                    f"  [db-poll] status={job.status} stage={job.stage} error={job.error!r}",
                    flush=True,
                )
                synth_action = (
                    (job.agent_trace_json or {})
                    .get("stages", {})
                    .get("synthesise", {})
                    .get("action")
                )
                if job.stage == "critique" and job.status == "awaiting_human":
                    last["_synth_action"] = synth_action
                    return last
                if job.status == "failed":
                    return last
                if job.status == "queued":
                    pass
        finally:
            db.close()
        time.sleep(POLL_SECONDS)
    last["_timeout"] = True
    return last


def _usd_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * OPENAI_INPUT_USD_PER_1M / 1_000_000
        + output_tokens * OPENAI_OUTPUT_USD_PER_1M / 1_000_000
    )


def main() -> int:
    _bootstrap_prod_env()
    import app.models  # noqa: F401 — register User etc. for DonorReport relationships
    from app.db.session import SessionLocal

    if SessionLocal is None:
        print("STOP: DATABASE_URL not set — run via `railway run python scripts/...`")
        return 1

    print("=== F1 prod synthesis prose walk ===", flush=True)
    candidates = _find_checkpoints(SessionLocal)
    print(f"CHECKPOINTS found={len(candidates)}", flush=True)
    for c in candidates[:5]:
        print(f"  {json.dumps(c)}", flush=True)

    picked = _pick_checkpoint(candidates)
    if not picked:
        print("STOP: no parked (awaiting_human, synthesise) checkpoint — fresh walk required")
        return 1

    report_id = picked["report_id"]
    mode = "resume"
    print(f"USING report_id={report_id} mode={mode} facts={picked['facts_count']}", flush=True)

    re_ok = _re_enqueue(SessionLocal, report_id)
    print(f"RE_ENQUEUE gate2={'ok' if re_ok else 'miss'}", flush=True)

    polled = _poll_db_job(SessionLocal, report_id, max_seconds=300)
    worker_advanced = (
        polled.get("stage") == "critique"
        and polled.get("status") == "awaiting_human"
        and polled.get("_synth_action") == "synthesise_completed"
    )

    totals = _usage_totals()
    if worker_advanced:
        print("WORKER ran F1 synthesis (deployed code detected)", flush=True)
        synth_trace = (polled.get("agent_trace_json") or {}).get("stages", {}).get(
            "synthesise", {}
        )
        totals["input_tokens"] = int(synth_trace.get("openai_input_tokens") or 0)
        totals["output_tokens"] = int(synth_trace.get("openai_output_tokens") or 0)
    else:
        print(
            "WORKER did not advance to critique (F1 may not be deployed) — "
            "running live synthesis via prod DB + OpenAI",
            flush=True,
        )
        synth_result = _run_synthesis_direct(SessionLocal, report_id, totals)
        print(f"DIRECT_SYNTH {json.dumps(synth_result)}", flush=True)

    payload = _read_report(SessionLocal, report_id)
    job = payload["job"]
    content = payload.get("content_json") or {}
    sections = content.get("sections") or []

    print("\n=== READBACK ===", flush=True)
    print(f"report_id={report_id}", flush=True)
    print(f"mode={mode}", flush=True)
    print(f"job stage={job.get('stage')} status={job.get('status')}", flush=True)
    print(f"sections_count={len(sections)} kb_facts={payload['kb_facts']}", flush=True)

    openai_usd = _usd_cost(totals["input_tokens"], totals["output_tokens"])
    print("\n=== COST (this run) ===", flush=True)
    print(f"claude_upstream_usd=0.00 (resume — no upstream re-run)", flush=True)
    print(
        f"openai_gpt54 input_tokens={totals['input_tokens']} "
        f"output_tokens={totals['output_tokens']} "
        f"sections_called={totals['sections']}",
        flush=True,
    )
    print(f"openai_gpt54_usd={openai_usd:.4f}", flush=True)
    print(f"total_usd={openai_usd:.4f}", flush=True)

    print("\n=== SECTIONS (verbatim) ===", flush=True)
    for sec in sections:
        print("\n---", flush=True)
        print(f"section_key={sec.get('section_key')}", flush=True)
        print(f"label={sec.get('label')}", flush=True)
        print(f"generation_status={sec.get('generation_status')}", flush=True)
        constraints = sec.get("constraints_applied") or {}
        print(f"word_limit_respected={constraints.get('word_limit_respected')}", flush=True)
        content_block = sec.get("content") or {}
        print(f"evidence_used={json.dumps(content_block.get('evidence_used') or [])}", flush=True)
        if sec.get("generation_status") == "FAILED":
            print(f"failure_reason={sec.get('failure_reason')!r}", flush=True)
        else:
            print("FULL_TEXT_BEGIN", flush=True)
            print(content_block.get("text") or "", flush=True)
            print("FULL_TEXT_END", flush=True)

    out_path = REPO / f"F1_PROSE_WALK_{report_id[:8]}.json"
    out_path.write_text(
        json.dumps(
            {
                "report_id": report_id,
                "mode": mode,
                "job": job,
                "cost": {
                    "openai_input_tokens": totals["input_tokens"],
                    "openai_output_tokens": totals["output_tokens"],
                    "openai_usd": openai_usd,
                    "claude_usd": 0.0,
                    "total_usd": openai_usd,
                },
                "content_json": content,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nARTIFACT_JSON={out_path}", flush=True)

    ok = (
        job.get("stage") == "critique"
        and job.get("status") == "awaiting_human"
        and len(sections) == 6
    )
    print(f"STRUCTURAL_OK={ok}", flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
