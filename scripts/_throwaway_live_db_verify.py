#!/usr/bin/env python3
"""READ-ONLY prod DB verification (throwaway). Outputs JSON to stdout."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
FCDO_REF = REPO / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"

TEMPLATE_FIELDS = (
    "funder_name",
    "template_name",
    "region",
    "reporting_frequency",
    "docx_template_ref",
    "report_sections_json",
    "format_rules_json",
    "terminology_map_json",
)

EXPECTED_COLUMNS: dict[str, list[tuple[str, str, str, str | None]]] = {
    "funder_report_templates": [
        ("id", "uuid", "NO", "gen_random_uuid()"),
        ("funder_name", "text", "NO", None),
        ("template_name", "text", "NO", None),
        ("region", "text", "NO", None),
        ("reporting_frequency", "text", "NO", None),
        ("report_sections_json", "jsonb", "NO", "'[]'::jsonb"),
        ("format_rules_json", "jsonb", "NO", "'{}'::jsonb"),
        ("terminology_map_json", "jsonb", "NO", "'{}'::jsonb"),
        ("docx_template_ref", "text", "NO", None),
        ("is_active", "boolean", "NO", "true"),
        ("version", "integer", "NO", "1"),
        ("created_at", "timestamp with time zone", "NO", "now()"),
        ("updated_at", "timestamp with time zone", "NO", "now()"),
    ],
    "donor_reports": [
        ("id", "uuid", "NO", "gen_random_uuid()"),
        ("user_id", "uuid", "NO", None),
        ("funder_report_template_id", "uuid", "NO", None),
        ("linked_proposal_id", "uuid", "YES", None),
        ("reporting_period_start", "date", "NO", None),
        ("reporting_period_end", "date", "NO", None),
        ("status", "text", "NO", "'DRAFT'::text"),
        ("knowledge_bank_json", "jsonb", "NO", "'{}'::jsonb"),
        ("gap_analysis_json", "jsonb", "NO", "'{}'::jsonb"),
        ("indicator_actuals_json", "jsonb", "NO", "'{}'::jsonb"),
        ("content_json", "jsonb", "NO", "'{}'::jsonb"),
        ("version", "integer", "NO", "1"),
        ("created_at", "timestamp with time zone", "NO", "now()"),
        ("updated_at", "timestamp with time zone", "NO", "now()"),
    ],
    "uploaded_documents": [
        ("id", "uuid", "NO", "gen_random_uuid()"),
        ("donor_report_id", "uuid", "NO", None),
        ("user_id", "uuid", "NO", None),
        ("storage_ref", "text", "NO", None),
        ("original_filename", "text", "NO", None),
        ("mime_type", "text", "NO", None),
        ("size_bytes", "bigint", "NO", None),
        ("classification", "text", "YES", None),
        ("extracted_json", "jsonb", "NO", "'{}'::jsonb"),
        ("extraction_status", "text", "NO", "'PENDING'::text"),
        ("created_at", "timestamp with time zone", "NO", "now()"),
    ],
    "report_jobs": [
        ("id", "uuid", "NO", "gen_random_uuid()"),
        ("donor_report_id", "uuid", "NO", None),
        ("stage", "text", "NO", "'classify'::text"),
        ("status", "text", "NO", "'queued'::text"),
        ("agent_trace_json", "jsonb", "NO", "'{}'::jsonb"),
        ("error", "text", "YES", None),
        ("started_at", "timestamp with time zone", "YES", None),
        ("finished_at", "timestamp with time zone", "YES", None),
    ],
}

EXPECTED_CHECKS = {
    "funder_report_templates": r"reporting_frequency IN \('end_of_grant', 'annual', 'quarterly', 'interim', 'final'\)",
    "donor_reports_status": r"status IN \('DRAFT', 'EXTRACTING', 'AWAITING_REVIEW', 'GENERATING', 'DEGRADED', 'COMPLETE'\)",
    "uploaded_documents_classification": r"classification IS NULL OR classification IN \('proposal', 'grant_letter', 'mou', 'indicator_data', 'photo', 'deck', 'other'\)",
    "report_jobs_stage": r"stage IN \('classify', 'extract', 'reconcile', 'gap', 'synthesise', 'critique', 'export'\)",
    "report_jobs_status": r"status IN \('queued', 'running', 'awaiting_human', 'failed', 'done'\)",
}


def _railway_db_url() -> str:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise RuntimeError("railway CLI not found")
    out = subprocess.check_output(
        [railway, "variables", "--json", "--service", "Postgres"],
        cwd=REPO,
        text=True,
    )
    data = json.loads(out)
    url = data.get("DATABASE_PUBLIC_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL not found")
    env = data.get("RAILWAY_ENVIRONMENT_NAME")
    project = data.get("RAILWAY_PROJECT_NAME")
    if env != "production":
        raise RuntimeError(f"Not production environment: {env!r}")
    return url


def _norm_default(val: str | None) -> str | None:
    if val is None:
        return None
    s = val.strip()
    s = re.sub(r"::\w+", "", s)
    s = s.replace("'", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower() if s else None


def _compare_columns(table: str, rows: list[dict]) -> list[str]:
    issues: list[str] = []
    expected = EXPECTED_COLUMNS[table]
    prod_map = {r["column_name"]: r for r in rows}
    exp_names = [c[0] for c in expected]
    prod_names = list(prod_map.keys())
    if prod_names != exp_names:
        missing = [n for n in exp_names if n not in prod_map]
        extra = [n for n in prod_names if n not in exp_names]
        if missing:
            issues.append(f"{table}: missing columns {missing}")
        if extra:
            issues.append(f"{table}: extra columns {extra}")
        if prod_names != exp_names and not missing and not extra:
            issues.append(f"{table}: column order differs (names match)")
    for name, dtype, nullable, default in expected:
        if name not in prod_map:
            continue
        r = prod_map[name]
        if r["data_type"] != dtype:
            issues.append(f"{table}.{name}: type prod={r['data_type']!r} expected={dtype!r}")
        if r["is_nullable"] != nullable:
            issues.append(
                f"{table}.{name}: nullable prod={r['is_nullable']} expected={nullable}"
            )
        if default is not None:
            pd = _norm_default(r.get("column_default"))
            ed = _norm_default(default)
            if pd != ed and not (pd and ed and pd in ed or ed in (pd or "")):
                # allow gen_random_uuid() variants
                if "gen_random_uuid" in (pd or "") and "gen_random_uuid" in (ed or ""):
                    pass
                elif name == "status" and pd == "draft" and ed == "'draft'":
                    pass
                elif name in ("stage", "extraction_status") and pd and ed and pd.replace("'", "") in ed.replace("'", ""):
                    pass
                else:
                    issues.append(
                        f"{table}.{name}: default prod={r.get('column_default')!r} expected~={default!r}"
                    )
    return issues


def _json_diff(path: str, a: Any, b: Any, mismatches: list, missing_in_b: list, missing_in_a: list) -> None:
    if type(a) != type(b):
        mismatches.append(f"{path}: type prod={type(a).__name__} repo={type(b).__name__}")
        return
    if isinstance(a, dict):
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        for k in sorted(keys_a - keys_b):
            missing_in_b.append(f"{path}.{k}" if path else k)
        for k in sorted(keys_b - keys_a):
            missing_in_a.append(f"{path}.{k}" if path else k)
        for k in sorted(keys_a & keys_b):
            p = f"{path}.{k}" if path else k
            _json_diff(p, a[k], b[k], mismatches, missing_in_b, missing_in_a)
        return
    if isinstance(a, list):
        if len(a) != len(b):
            mismatches.append(f"{path}: array length prod={len(a)} repo={len(b)}")
        for i, (ai, bi) in enumerate(zip(a, b)):
            _json_diff(f"{path}[{i}]", ai, bi, mismatches, missing_in_b, missing_in_a)
        if len(a) > len(b):
            for i in range(len(b), len(a)):
                missing_in_a.append(f"{path}[{i}] (prod only)")
        elif len(b) > len(a):
            for i in range(len(a), len(b)):
                missing_in_b.append(f"{path}[{i}] (repo only)")
        return
    if a != b:
        mismatches.append(f"{path}: prod={json.dumps(a, ensure_ascii=False)[:200]!r} repo={json.dumps(b, ensure_ascii=False)[:200]!r}")


def main() -> int:
    url = _railway_db_url()
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    out: dict[str, Any] = {"read_only_confirmed": False}

    with engine.connect() as conn:
        ro = conn.execute(text("SHOW default_transaction_read_only")).scalar()
        conn.execute(text("SET default_transaction_read_only = on"))
        ro_after = conn.execute(text("SHOW default_transaction_read_only")).scalar()
        out["read_only_confirmed"] = ro_after == "on"

        out["alembic_version"] = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

        out["tables"] = [
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN (
                        'funder_report_templates', 'donor_reports',
                        'uploaded_documents', 'report_jobs'
                      )
                    ORDER BY 1
                    """
                )
            )
        ]

        column_issues: list[str] = []
        out["columns"] = {}
        for table in (
            "donor_reports",
            "funder_report_templates",
            "uploaded_documents",
            "report_jobs",
        ):
            rows = [
                dict(r._mapping)
                for r in conn.execute(
                    text(
                        """
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = :t
                        ORDER BY ordinal_position
                        """
                    ),
                    {"t": table},
                )
            ]
            out["columns"][table] = rows
            column_issues.extend(_compare_columns(table, rows))
        out["column_issues"] = column_issues

        checks: dict[str, list] = {}
        for table in ("funder_report_templates", "donor_reports", "uploaded_documents", "report_jobs"):
            checks[table] = [
                {"conname": r[0], "def": r[1]}
                for r in conn.execute(
                    text(
                        """
                        SELECT conname, pg_get_constraintdef(oid)
                        FROM pg_constraint
                        WHERE conrelid = CAST(:t AS regclass) AND contype = 'c'
                        """
                    ),
                    {"t": table},
                )
            ]
        out["check_constraints"] = checks

        templates = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    """
                    SELECT id::text AS id, funder_name, template_name, region,
                           reporting_frequency, version, is_active,
                           jsonb_array_length(report_sections_json) AS section_count,
                           docx_template_ref
                    FROM funder_report_templates
                    ORDER BY funder_name, template_name
                    """
                )
            )
        ]
        out["templates"] = templates

        fcdo_candidates = [
            t
            for t in templates
            if "fcdo" in t["funder_name"].lower()
            or "foreign, commonwealth" in t["funder_name"].lower()
        ]
        if not fcdo_candidates:
            out["fcdo_error"] = "No FCDO template row found in query 6"
            print(json.dumps(out, indent=2, default=str))
            return 2

        fcdo_id = fcdo_candidates[0]["id"]
        out["fcdo_template_id"] = fcdo_id
        out["fcdo_selection"] = fcdo_candidates

        q7 = conn.execute(
            text(
                """
                SELECT id::text, funder_name, template_name,
                       report_sections_json ? 'section_key' AS sections_is_array,
                       format_rules_json ? 'document_title' AS has_doc_title,
                       format_rules_json ? 'logframe' AS has_logframe,
                       format_rules_json ? 'value_for_money' AS has_vfm,
                       terminology_map_json ? 'canonical_to_funder' AS has_term_map
                FROM funder_report_templates
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": fcdo_id},
        ).mappings().first()
        out["fcdo_query7"] = dict(q7) if q7 else None

        prod_row = conn.execute(
            text(
                """
                SELECT funder_name, template_name, region, reporting_frequency,
                       report_sections_json, format_rules_json, terminology_map_json,
                       docx_template_ref, version
                FROM funder_report_templates
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": fcdo_id},
        ).mappings().first()
        prod_dict = dict(prod_row) if prod_row else {}
        for k in ("report_sections_json", "format_rules_json", "terminology_map_json"):
            if isinstance(prod_dict.get(k), str):
                prod_dict[k] = json.loads(prod_dict[k])

        repo = json.loads(FCDO_REF.read_text(encoding="utf-8"))
        prod_cmp = {k: prod_dict[k] for k in TEMPLATE_FIELDS if k in prod_dict}
        repo_cmp = {k: repo[k] for k in TEMPLATE_FIELDS if k in repo}

        mismatches: list[str] = []
        missing_in_repo: list[str] = []
        missing_in_prod: list[str] = []
        for field in TEMPLATE_FIELDS:
            if field not in repo_cmp:
                missing_in_repo.append(f"top-level field {field} missing in repo")
            if field not in prod_cmp:
                missing_in_prod.append(f"top-level field {field} missing in prod")
        for field in TEMPLATE_FIELDS:
            if field in repo_cmp and field in prod_cmp:
                if field.endswith("_json"):
                    _json_diff(
                        field,
                        prod_cmp[field],
                        repo_cmp[field],
                        mismatches,
                        missing_in_repo,
                        missing_in_prod,
                    )
                elif prod_cmp[field] != repo_cmp[field]:
                    mismatches.append(
                        f"{field}: prod={prod_cmp[field]!r} repo={repo_cmp[field]!r}"
                    )

        out["fcdo_diff"] = {
            "scalar_and_json_mismatches": mismatches,
            "keys_or_paths_in_prod_not_repo": missing_in_prod,
            "keys_or_paths_in_repo_not_prod": missing_in_repo,
        }

        out["indexes"] = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    """
                    SELECT tablename, indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename IN (
                        'funder_report_templates', 'donor_reports',
                        'uploaded_documents', 'report_jobs'
                      )
                    ORDER BY tablename, indexname
                    """
                )
            )
        ]

    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
