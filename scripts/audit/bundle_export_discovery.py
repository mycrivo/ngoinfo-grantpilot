#!/usr/bin/env python3
"""Owner-triggered, read-only discovery of persisted shapes for one donor report.

Observation only: paths, types, cardinalities, minimal redacted samples.
No mapping proposal, no scoring, no engine/model calls, no writes to production.

Usage (owner):
  # With DATABASE_URL / DATABASE_PUBLIC_URL already set:
  python scripts/audit/bundle_export_discovery.py [--report-id UUID] [--out PATH]

  # Or via Railway Postgres variables (same pattern as scripts/_check_report_status_db.py):
  python scripts/audit/bundle_export_discovery.py --railway
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_ID = "dfd17248-9b46-48d9-8bc6-5348eab44a1c"
DEFAULT_OUT_DIR = REPO / "docs" / "artefacts" / "me_module" / "audits"

# Keys whose values are free text — never emit full content in the artefact.
_FREE_TEXT_KEY_FRAGMENTS = (
    "text",
    "prose",
    "body",
    "excerpt",
    "question",
    "rationale",
    "answer_text",
    "interpretation_note",
    "annotation",
    "error",
    "filename",
    "original_filename",
    "storage_ref",
    "email",
    "organization",
    "organisation",
    "parse_failure",
    "response_head",
    "response_tail",
)

_MAX_DEPTH = 8
_MAX_SAMPLES_PER_PATH = 1
_SAMPLE_PREFIX_LEN = 48


def _bootstrap_railway_db_url() -> str:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise SystemExit("railway CLI not found; set DATABASE_URL or install railway")
    pg = json.loads(
        subprocess.check_output(
            [railway, "variables", "--json", "--service", "Postgres"],
            cwd=str(REPO),
            text=True,
        )
    )
    url = pg.get("DATABASE_PUBLIC_URL") or pg.get("DATABASE_URL")
    if not url:
        raise SystemExit("Postgres service has no DATABASE_PUBLIC_URL / DATABASE_URL")
    return str(url)


def _is_free_text_key(key: str) -> bool:
    low = key.lower()
    return any(frag in low for frag in _FREE_TEXT_KEY_FRAGMENTS)


def _redact_scalar(value: Any) -> dict[str, Any]:
    if value is None:
        return {"kind": "null"}
    if isinstance(value, bool):
        return {"kind": "bool", "sample": value}
    if isinstance(value, (int, float)):
        return {"kind": type(value).__name__, "sample": value}
    if isinstance(value, str):
        digest = hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:16]
        # Length + digest only for path-like, identity-bearing, or filename strings.
        lower = value.lower()
        if (
            "/" in value
            or "@" in value
            or "users/" in value
            or lower.endswith((".docx", ".pdf", ".xlsx", ".csv", ".doc", ".txt"))
            or "\\" in value
        ):
            return {
                "kind": "str",
                "length": len(value),
                "sha256_16": digest,
                "prefix_redacted": "[redacted_path_or_identity]",
            }
        prefix = value[:_SAMPLE_PREFIX_LEN].replace("\n", "\\n")
        return {
            "kind": "str",
            "length": len(value),
            "sha256_16": digest,
            "prefix_redacted": prefix if value else "",
        }
    return {"kind": type(value).__name__, "repr_type_only": True}


def _emptiness(value: Any) -> str:
    """present | empty | absent — absent is only for missing keys (caller)."""
    if value is None:
        return "empty"
    if isinstance(value, (dict, list, str, bytes)) and len(value) == 0:
        return "empty"
    return "present"


def _walk(
    value: Any,
    path: str,
    *,
    depth: int,
    out_paths: list[dict[str, Any]],
    parent_key: str | None = None,
) -> None:
    if depth > _MAX_DEPTH:
        out_paths.append(
            {
                "path": path,
                "presence": _emptiness(value),
                "type": type(value).__name__,
                "note": "max_depth_reached",
            }
        )
        return

    if isinstance(value, dict):
        keys = sorted(value.keys(), key=str)
        entry: dict[str, Any] = {
            "path": path,
            "presence": _emptiness(value),
            "type": "object",
            "cardinality": len(keys),
            "keys": keys[:40],
        }
        if len(keys) > 40:
            entry["keys_truncated"] = True
            entry["key_count"] = len(keys)
        out_paths.append(entry)
        for k in keys:
            child = value[k]
            child_path = f"{path}.{k}" if path else str(k)
            if _is_free_text_key(str(k)) and isinstance(child, str):
                out_paths.append(
                    {
                        "path": child_path,
                        "presence": _emptiness(child),
                        "type": "str",
                        "redacted": True,
                        "sample": _redact_scalar(child),
                    }
                )
                continue
            _walk(child, child_path, depth=depth + 1, out_paths=out_paths, parent_key=str(k))
        return

    if isinstance(value, list):
        entry = {
            "path": path,
            "presence": _emptiness(value),
            "type": "array",
            "cardinality": len(value),
        }
        if value:
            entry["element_types"] = sorted({type(x).__name__ for x in value[:50]})
            # Sample first element's key set if object
            first = value[0]
            if isinstance(first, dict):
                entry["element0_keys"] = sorted(first.keys(), key=str)[:40]
                entry["element0_sample"] = {
                    k: (
                        _redact_scalar(first[k])
                        if _is_free_text_key(str(k)) or isinstance(first[k], str)
                        else {"kind": type(first[k]).__name__, "presence": _emptiness(first[k])}
                    )
                    for k in list(first.keys())[:12]
                }
            else:
                entry["element0_sample"] = _redact_scalar(first)
        out_paths.append(entry)
        # Walk one representative element for nested shape
        if value and isinstance(value[0], (dict, list)):
            _walk(
                value[0],
                f"{path}[0]",
                depth=depth + 1,
                out_paths=out_paths,
                parent_key=parent_key,
            )
        return

    # Scalar
    sample = _redact_scalar(value)
    if parent_key and _is_free_text_key(parent_key) and isinstance(value, str):
        out_paths.append(
            {
                "path": path,
                "presence": _emptiness(value),
                "type": "str",
                "redacted": True,
                "sample": sample,
            }
        )
        return
    out_paths.append(
        {
            "path": path,
            "presence": _emptiness(value),
            "type": type(value).__name__,
            "sample": sample,
        }
    )


def _stage_summary(column_name: str, value: Any) -> dict[str, Any]:
    """Column-level present / empty / absent for a JSONB payload."""
    if value is None:
        return {
            "column": column_name,
            "column_presence": "absent",
            "note": "SQL NULL",
            "paths": [],
        }
    presence = _emptiness(value)
    paths: list[dict[str, Any]] = []
    _walk(value, column_name, depth=0, out_paths=paths)
    return {
        "column": column_name,
        "column_presence": presence,
        "root_type": type(value).__name__,
        "root_cardinality": len(value) if isinstance(value, (dict, list)) else None,
        "paths": paths,
    }


def _fetch_report(conn: Any, report_id: str) -> dict[str, Any]:
    from psycopg2.extras import RealDictCursor

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT
            dr.id,
            dr.status,
            dr.version,
            dr.reporting_period_start,
            dr.reporting_period_end,
            dr.created_at,
            dr.updated_at,
            dr.knowledge_bank_json,
            dr.gap_analysis_json,
            dr.indicator_actuals_json,
            dr.content_json,
            ft.funder_name,
            ft.template_name
        FROM donor_reports dr
        LEFT JOIN funder_report_templates ft ON ft.id = dr.funder_report_template_id
        WHERE dr.id = %s::uuid
        """,
        (report_id,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"report not found: {report_id}")

    cur.execute(
        """
        SELECT id, stage, status, error, started_at, finished_at, agent_trace_json
        FROM report_jobs
        WHERE donor_report_id = %s::uuid
        ORDER BY started_at DESC NULLS LAST, id DESC
        LIMIT 5
        """,
        (report_id,),
    )
    jobs = list(cur.fetchall())

    cur.execute(
        """
        SELECT id, classification, extraction_status, size_bytes,
               original_filename, mime_type,
               (extracted_json IS NULL) AS extracted_json_is_null,
               CASE
                 WHEN extracted_json IS NULL THEN NULL
                 ELSE jsonb_typeof(extracted_json)
               END AS extracted_json_typeof,
               CASE
                 WHEN extracted_json IS NULL THEN NULL
                 WHEN jsonb_typeof(extracted_json) = 'object'
                   THEN (SELECT count(*) FROM jsonb_object_keys(extracted_json))
                 WHEN jsonb_typeof(extracted_json) = 'array'
                   THEN jsonb_array_length(extracted_json)
                 ELSE NULL
               END AS extracted_json_cardinality
        FROM uploaded_documents
        WHERE donor_report_id = %s::uuid
        ORDER BY created_at
        """,
        (report_id,),
    )
    docs = list(cur.fetchall())
    cur.close()
    return {"report": dict(row), "jobs": [dict(j) for j in jobs], "documents": [dict(d) for d in docs]}


def _logical_stages(report: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    kb = report.get("knowledge_bank_json")
    gaps = report.get("gap_analysis_json")
    content = report.get("content_json")
    indicators = report.get("indicator_actuals_json")

    export_meta = None
    if isinstance(content, dict):
        export_meta = content.get("export") if "export" in content else None
        export_key_presence = "present" if "export" in content else "absent"
    else:
        export_key_presence = "absent"

    latest_job = jobs[0] if jobs else None
    trace = (latest_job or {}).get("agent_trace_json")

    def _stage(name: str, value: Any, *, key_absent: bool = False) -> dict[str, Any]:
        if key_absent:
            return {"stage": name, "presence": "absent", "detail": "key_missing_from_parent"}
        if value is None:
            return {"stage": name, "presence": "absent", "detail": "null"}
        return {
            "stage": name,
            "presence": _emptiness(value),
            "root_type": type(value).__name__,
            "root_cardinality": len(value) if isinstance(value, (dict, list)) else None,
        }

    export_blob = {
        "stage": "export",
        "content_json_export_key": export_key_presence,
        "export_object_presence": (
            "absent"
            if export_key_presence == "absent"
            else _emptiness(export_meta)
        ),
    }
    if isinstance(export_meta, dict):
        export_blob["export_keys"] = sorted(export_meta.keys(), key=str)
        ref = export_meta.get("storage_ref")
        export_blob["storage_ref"] = {
            "presence": "absent" if "storage_ref" not in export_meta else _emptiness(ref),
            "sample": _redact_scalar(ref) if isinstance(ref, str) else None,
        }
        # Do not fetch the DOCX blob — only note whether a ref string exists.
        export_blob["docx_bytes_fetched"] = False

    return {
        "knowledge_bank": _stage("knowledge_bank", kb),
        "gaps": _stage("gaps", gaps),
        "content": _stage("content", content),
        "export": export_blob,
        "job_trace": _stage("job_trace", trace),
        "indicator_actuals": _stage("indicator_actuals", indicators),
        "latest_job": (
            {
                "id": str(latest_job["id"]),
                "stage": latest_job.get("stage"),
                "status": latest_job.get("status"),
                "error_presence": _emptiness(latest_job.get("error")),
            }
            if latest_job
            else None
        ),
        "jobs_listed": len(jobs),
    }


def build_discovery_artefact(payload: dict[str, Any], report_id: str) -> dict[str, Any]:
    report = payload["report"]
    jobs = payload["jobs"]
    docs = payload["documents"]

    # Strip identity-bearing scalars from the top-level record summary.
    funder_name = report.get("funder_name")
    template_name = report.get("template_name")

    stages = _logical_stages(report, jobs)

    columns = {
        "knowledge_bank_json": _stage_summary(
            "knowledge_bank_json", report.get("knowledge_bank_json")
        ),
        "gap_analysis_json": _stage_summary(
            "gap_analysis_json", report.get("gap_analysis_json")
        ),
        "content_json": _stage_summary("content_json", report.get("content_json")),
        "indicator_actuals_json": _stage_summary(
            "indicator_actuals_json", report.get("indicator_actuals_json")
        ),
    }

    # Job traces — shape of latest only
    latest_trace = jobs[0].get("agent_trace_json") if jobs else None
    columns["agent_trace_json_latest"] = _stage_summary(
        "agent_trace_json", latest_trace
    )

    doc_shapes = []
    for d in docs:
        doc_shapes.append(
            {
                "id": str(d["id"]),
                "classification": d.get("classification"),
                "extraction_status": d.get("extraction_status"),
                "size_bytes": d.get("size_bytes"),
                "mime_type": d.get("mime_type"),
                "original_filename": _redact_scalar(d.get("original_filename") or ""),
                "extracted_json_is_null": d.get("extracted_json_is_null"),
                "extracted_json_typeof": d.get("extracted_json_typeof"),
                "extracted_json_cardinality": d.get("extracted_json_cardinality"),
                "note": "extracted_json body not dumped (volume / PII)",
            }
        )

    return {
        "artefact": "bundle_export_discovery",
        "artefact_version": "1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "report_id": report_id,
        "purpose": (
            "Read-only observation of persisted production shapes for the named report. "
            "No mapping, no scoring, no adjudication reference."
        ),
        "read_mode": "postgresql_readonly",
        "report_meta": {
            "status": report.get("status"),
            "version": report.get("version"),
            "reporting_period_start": str(report.get("reporting_period_start")),
            "reporting_period_end": str(report.get("reporting_period_end")),
            "created_at": str(report.get("created_at")),
            "updated_at": str(report.get("updated_at")),
            "funder_name_redacted": _redact_scalar(funder_name or ""),
            "template_name_redacted": _redact_scalar(template_name or ""),
        },
        "logical_stages": stages,
        "columns": columns,
        "uploaded_documents_shape": doc_shapes,
        "explicit_non_goals": [
            "no_ScoreableBundle_mapping",
            "no_scoring",
            "no_mapping_proposal",
            "no_engine_or_model_execution",
            "no_docx_body_fetched",
            "no_adjudication_reference",
        ],
        "owner_gate": (
            "Discovery complete. Mapping and export must not be authored until the owner "
            "releases the embedded gate after reviewing this artefact."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-id", default=DEFAULT_REPORT_ID)
    parser.add_argument(
        "--railway",
        action="store_true",
        help="Load DATABASE_PUBLIC_URL from Railway Postgres service variables",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: docs/artefacts/me_module/audits/BUNDLE_EXPORT_DISCOVERY_<short>_<date>.json)",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print JSON to stdout; do not write a file",
    )
    args = parser.parse_args()

    if args.railway:
        os.environ["DATABASE_URL"] = _bootstrap_railway_db_url()

    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit(
            "No DATABASE_URL / DATABASE_PUBLIC_URL. Pass --railway or set the env var."
        )

    import psycopg2

    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=True)
    try:
        payload = _fetch_report(conn, args.report_id)
    finally:
        conn.close()

    artefact = build_discovery_artefact(payload, args.report_id)
    text = json.dumps(artefact, indent=2, ensure_ascii=False, default=str) + "\n"

    if args.stdout_only:
        sys.stdout.write(text)
        return

    short = args.report_id.split("-")[0]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = args.out or (DEFAULT_OUT_DIR / f"BUNDLE_EXPORT_DISCOVERY_{short}_{date}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    print(f"logical_stages: {json.dumps(artefact['logical_stages'], indent=2, default=str)}")


if __name__ == "__main__":
    main()
