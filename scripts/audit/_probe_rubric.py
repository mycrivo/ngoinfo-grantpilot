import json
import os

from scripts.audit import _common as C

C.bootstrap_db_env()
import app.models  # noqa
from sqlalchemy import create_engine, text

rid = "3347590c-5b4f-4443-8a3d-a5ae455932e2"
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    job = c.execute(text(
        "SELECT agent_trace_json, started_at, finished_at FROM report_jobs "
        "WHERE donor_report_id=CAST(:r AS uuid) ORDER BY started_at DESC NULLS LAST LIMIT 1"),
        {"r": rid}).mappings().first()
    docs = c.execute(text(
        "SELECT original_filename, classification, extraction_status, extracted_json "
        "FROM uploaded_documents WHERE donor_report_id=CAST(:r AS uuid) ORDER BY created_at"),
        {"r": rid}).mappings().all()

stages = (job["agent_trace_json"] or {}).get("stages") or {}
print("=== STAGE TRACES ===")
for name, s in stages.items():
    if not isinstance(s, dict):
        print(name, s); continue
    keys = {k: s.get(k) for k in (
        "action", "model_used", "model", "latency_ms", "input_tokens", "output_tokens",
        "openai_input_tokens", "openai_output_tokens", "attempt_count", "num_turns",
        "degraded_code", "degraded_documents", "conflicts_surfaced_count",
        "section_count", "verified", "completed_at") if s.get(k) is not None}
    print(f"  {name}: {json.dumps(keys, default=str)}")

print("\n=== PER-DOC EXTRACTION (D1/D2-D4) ===")
for d in docs:
    ej = d["extracted_json"] or {}
    tr = ej.get("agent_trace") or {}
    struct = ej.get("structured") or {}
    print(f"  {d['original_filename'][:40]} class={d['classification']} status={d['extraction_status']}")
    print(f"    trace: model={tr.get('model_used') or tr.get('model')} latency_ms={tr.get('latency_ms')} "
          f"in={tr.get('input_tokens')} out={tr.get('output_tokens')} attempts={tr.get('attempt_count')} "
          f"outcome={struct.get('extraction_outcome')} degraded={tr.get('degraded_code')}")

C.write_artifact("rubric_traces.json", {
    "stages": stages,
    "docs": [{"file": d["original_filename"], "class": d["classification"],
              "status": d["extraction_status"],
              "trace": (d["extracted_json"] or {}).get("agent_trace"),
              "outcome": ((d["extracted_json"] or {}).get("structured") or {}).get("extraction_outcome")}
             for d in docs],
})
