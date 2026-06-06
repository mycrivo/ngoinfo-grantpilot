#!/usr/bin/env python3
"""Throwaway: verify F2 on prod via DB + optional critique re-queue probe."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
BASE = "https://ngoinfo-grantpilot-production.up.railway.app"


def main() -> None:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    pg = json.loads(
        subprocess.check_output(
            [railway, "variables", "--json", "--service", "Postgres"],
            cwd=REPO,
            text=True,
        )
    )
    engine = create_engine(pg["DATABASE_PUBLIC_URL"])
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, stage, status,
                       agent_trace_json->'stages'->'critique' AS critique
                FROM report_jobs
                WHERE donor_report_id = CAST(:rid AS uuid)
                ORDER BY started_at DESC NULLS LAST
                LIMIT 1
                """
            ),
            {"rid": "cabb8796-195b-4089-afab-94d6fe841d50"},
        ).mappings().first()

    openapi = requests.get(f"{BASE}/openapi.json", timeout=30).json()
    gate3_paths = [p for p in openapi.get("paths", {}) if "gate3" in p]

    gh = subprocess.check_output(
        ["gh", "api", "repos/mycrivo/ngoinfo-grantpilot/commits/main", "--jq", ".sha"],
        cwd=REPO,
        text=True,
    ).strip()

    f2_on_main = subprocess.run(
        [
            "gh",
            "api",
            "repos/mycrivo/ngoinfo-grantpilot/contents/app/reports/agents/fact_safety_critic.py",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).returncode == 0

    local_f2 = (REPO / "app/reports/agents/fact_safety_critic.py").exists()

    print(
        json.dumps(
            {
                "github_main_sha_prefix": gh[:7],
                "f2_file_on_github_main": f2_on_main,
                "f2_file_local_uncommitted": local_f2,
                "prod_openapi_gate3_paths": gate3_paths,
                "cabb8796_job": dict(row) if row else None,
                "precondition_f2_live": f2_on_main and bool(gate3_paths),
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
