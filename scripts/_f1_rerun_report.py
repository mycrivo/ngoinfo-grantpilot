#!/usr/bin/env python3
"""Throwaway: re-run F1 synthesis for one prod report (live OpenAI + prod DB)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

REPORT_ID = os.environ.get("REPORT_ID", "6643d922-150d-4000-b878-4025e7c9145a").strip()
FOCUS_SECTIONS = (
    "detailed_output_scoring",
    "value_for_money",
)


def _section_summary(content_json: dict, section_key: str) -> dict:
    for sec in content_json.get("sections") or []:
        if sec.get("section_key") == section_key:
            text = (sec.get("content") or {}).get("text") or ""
            return {
                "section_key": section_key,
                "generation_status": sec.get("generation_status"),
                "failure_reason": sec.get("failure_reason"),
                "text_len": len(text),
                "text_preview": text[:200].replace("\n", " ") if text else "",
            }
    return {"section_key": section_key, "missing": True}


def main() -> int:
    from scripts.f1_prod_synthesis_prose_walk import (
        _bootstrap_prod_env,
        _make_tracking_query_fn,
        _read_report,
        _run_synthesis_direct,
        _usage_totals,
    )

    _bootstrap_prod_env()
    import app.models  # noqa: F401
    from app.db.session import SessionLocal

    if SessionLocal is None:
        print("STOP: DATABASE_URL not set")
        return 1

    print(f"=== F1 re-run report_id={REPORT_ID} ===", flush=True)
    before = _read_report(SessionLocal, REPORT_ID)
    job = before.get("job") or {}
    print(
        f"BEFORE job stage={job.get('stage')} status={job.get('status')} "
        f"kb_facts={before.get('kb_facts')}",
        flush=True,
    )
    before_content = before.get("content_json") or {}
    for key in FOCUS_SECTIONS:
        print(f"BEFORE {json.dumps(_section_summary(before_content, key))}", flush=True)

    totals = _usage_totals()
    print("RUNNING synthesise_and_persist (live OpenAI)...", flush=True)
    result = _run_synthesis_direct(SessionLocal, REPORT_ID, totals)
    print(f"SYNTH_RESULT {json.dumps(result)}", flush=True)
    print(
        f"TOKENS input={totals['input_tokens']} output={totals['output_tokens']} "
        f"sections_called={totals['sections']}",
        flush=True,
    )

    after = _read_report(SessionLocal, REPORT_ID)
    after_content = after.get("content_json") or {}
    summary = after_content.get("generation_summary") or {}
    print(f"GENERATION_SUMMARY {json.dumps(summary)}", flush=True)

    focus_ok = True
    for key in FOCUS_SECTIONS:
        row = _section_summary(after_content, key)
        print(f"AFTER {json.dumps(row)}", flush=True)
        if row.get("generation_status") != "GENERATED" or row.get("text_len", 0) == 0:
            focus_ok = False

    out_path = REPO / f"F1_RERUN_{REPORT_ID[:8]}.json"
    out_path.write_text(
        json.dumps(
            {
                "report_id": REPORT_ID,
                "before_focus": [_section_summary(before_content, k) for k in FOCUS_SECTIONS],
                "after_focus": [_section_summary(after_content, k) for k in FOCUS_SECTIONS],
                "synth_result": result,
                "generation_summary": summary,
                "tokens": totals,
                "content_json": after_content,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"ARTIFACT={out_path}", flush=True)
    print(f"FOCUS_SECTIONS_OK={focus_ok}", flush=True)
    return 0 if focus_ok and int(result.get("failed") or 0) == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
