#!/usr/bin/env python3
"""Phase A diagnosis for E3 gap stage failures (read-only).

Usage:
  REPORT_ID=230290ce-d28a-4138-ae08-901cf1ad69c0 python scripts/gap_stage_diagnosis.py
  KB_FIXTURE=tests/fixtures/reconciler/recorded/fcdo_bridgelight_recorded_knowledge_bank.json \\
    TEMPLATE_FIXTURE=docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json \\
    python scripts/gap_stage_diagnosis.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from app.reports.agents.gap_compliance_agent import (  # noqa: E402
    MAX_INPUT_CHARS,
    build_gap_compliance_prompt,
)
from app.reports.gap.deterministic_gaps import (  # noqa: E402
    build_deterministic_gap_compliance_output,
)
from app.reports.gap.logframe_completeness import (  # noqa: E402
    derive_missing_logframe_actuals,
    missing_to_gap_items,
    missing_to_template_requirements,
)
from app.reports.gap.satisfaction import unsatisfied_requirements  # noqa: E402
from app.reports.gap.template_requirements import (  # noqa: E402
    enumerate_template_requirements,
    merge_template_requirements,
)

REPORT_ID = os.environ.get(
    "REPORT_ID", "230290ce-d28a-4138-ae08-901cf1ad69c0"
)
REPORT_CONTEXT = {"report_type": "annual"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _bootstrap_db_env() -> None:
    if os.environ.get("DATABASE_URL"):
        return
    env_path = REPO / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _fetch_prod_snapshot(report_id: str) -> dict:
    from sqlalchemy import create_engine, text

    _bootstrap_db_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set — use KB_FIXTURE/TEMPLATE_FIXTURE instead")
    engine = create_engine(url)
    with engine.connect() as conn:
        report = conn.execute(
            text(
                """
                SELECT knowledge_bank_json, gap_analysis_json, funder_report_template_id
                FROM donor_reports WHERE id = CAST(:rid AS uuid)
                """
            ),
            {"rid": report_id},
        ).mappings().first()
        if report is None:
            raise RuntimeError(f"report not found: {report_id}")
        job = conn.execute(
            text(
                """
                SELECT id, stage, status, error, agent_trace_json
                FROM report_jobs
                WHERE donor_report_id = CAST(:rid AS uuid)
                ORDER BY started_at DESC NULLS LAST, id DESC
                LIMIT 1
                """
            ),
            {"rid": report_id},
        ).mappings().first()
        template_row = conn.execute(
            text(
                """
                SELECT report_sections_json, format_rules_json, template_name, funder_name
                FROM funder_report_templates
                WHERE id = CAST(:tid AS uuid)
                """
            ),
            {"tid": str(report["funder_report_template_id"])},
        ).mappings().first()
    return {
        "report_id": report_id,
        "knowledge_bank_json": report["knowledge_bank_json"] or {},
        "gap_analysis_json": report["gap_analysis_json"],
        "job": dict(job) if job else None,
        "template_payload": {
            "funder_name": template_row["funder_name"],
            "template_name": template_row["template_name"],
            "report_sections_json": template_row["report_sections_json"],
            "format_rules_json": template_row["format_rules_json"] or {},
        },
    }


def _kb_metrics(kb: dict) -> dict:
    facts = kb.get("facts") or {}
    conflicts = kb.get("conflicts") or []
    degraded_keys = sum(
        1 for key in facts if str(key).startswith("degraded_pass_through:")
    )
    unresolved = sum(
        1
        for conflict in conflicts
        if isinstance(conflict, dict) and conflict.get("resolved_value") is None
    )
    return {
        "fact_count": len(facts),
        "degraded_pass_through_count": degraded_keys,
        "conflict_count": len(conflicts),
        "unresolved_conflict_count": unresolved,
        "reconciliation_outcome": kb.get("reconciliation_outcome"),
        "gate1_confirmed_at": kb.get("gate1_confirmed_at"),
    }


def _prompt_metrics(kb: dict, template_payload: dict) -> dict:
    sections = template_payload.get("report_sections_json") or []
    format_rules = template_payload.get("format_rules_json") or {}
    base_requirements = enumerate_template_requirements(
        sections, report_context=REPORT_CONTEXT
    )
    logframe_missing = derive_missing_logframe_actuals(
        kb,
        format_rules_json=format_rules,
        report_sections_json=sections,
    )
    requirements = merge_template_requirements(
        base_requirements, missing_to_template_requirements(logframe_missing)
    )
    checklist_non_section = len(
        [req for req in requirements if req.required_item_type != "section"]
    )
    prompt = build_gap_compliance_prompt(
        knowledge_bank_json=kb,
        template_payload=template_payload,
        requirements=requirements,
        report_context=REPORT_CONTEXT,
        logframe_missing_actuals=[
            {
                "indicator_id": entry.indicator_id,
                "item_key": entry.item_key,
                "required_item_ref": entry.required_item_ref,
            }
            for entry in logframe_missing
        ],
    )
    missing_reqs = unsatisfied_requirements(requirements, kb)
    det_output = build_deterministic_gap_compliance_output(
        requirements=requirements,
        knowledge_bank_json=kb,
        logframe_gaps=missing_to_gap_items(logframe_missing),
        checklist_non_section_count=checklist_non_section,
    )
    return {
        "prompt_chars": len(prompt),
        "max_input_chars": MAX_INPUT_CHARS,
        "prompt_truncated": len(prompt) >= MAX_INPUT_CHARS,
        "checklist_non_section_count": checklist_non_section,
        "logframe_missing_count": len(logframe_missing),
        "deterministic_unsatisfied_count": len(missing_reqs),
        "deterministic_gap_count": len(det_output.gaps),
        "deterministic_readiness_score": det_output.readiness_score,
    }


def main() -> int:
    kb_fixture = os.environ.get("KB_FIXTURE")
    template_fixture = os.environ.get("TEMPLATE_FIXTURE")
    if kb_fixture and template_fixture:
        kb = _load_json(REPO / kb_fixture)
        template_payload = _load_json(REPO / template_fixture)
        snapshot = {
            "report_id": REPORT_ID,
            "knowledge_bank_json": kb,
            "gap_analysis_json": None,
            "job": None,
            "template_payload": template_payload,
            "source": "fixtures",
        }
    else:
        snapshot = _fetch_prod_snapshot(REPORT_ID)
        snapshot["source"] = "database"

    kb = snapshot["knowledge_bank_json"]
    metrics = {
        "report_id": snapshot["report_id"],
        "source": snapshot["source"],
        "kb": _kb_metrics(kb),
        "prompt": _prompt_metrics(kb, snapshot["template_payload"]),
    }
    job = snapshot.get("job")
    if job:
        metrics["job"] = {
            "id": str(job.get("id")),
            "stage": job.get("stage"),
            "status": job.get("status"),
            "error_head": (job.get("error") or "")[:500],
        }
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
