#!/usr/bin/env python3
"""Deep diff prod snapshot vs repo FCDO template for B1 staging."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json"
REPO = ROOT / "docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json"


def _index_sections(sections: list[dict]) -> dict[str, dict]:
    return {str(s["section_key"]): s for s in sections}


def main() -> None:
    prod = json.loads(SNAP.read_text(encoding="utf-8"))
    repo = json.loads(REPO.read_text(encoding="utf-8"))
    prod_ix = _index_sections(prod["report_sections_json"])
    repo_ix = _index_sections(repo["report_sections_json"])

    changes: list[str] = []
    for key, repo_sec in repo_ix.items():
        prod_sec = prod_ix.get(key)
        if prod_sec is None:
            changes.append(f"add_section:{key}")
            continue
        for field in ("owner", "required_indicators", "required_tables"):
            if prod_sec.get(field) != repo_sec.get(field):
                changes.append(f"{key}.{field}")
        prod_req = prod_sec.get("indicator_requirements") or {}
        repo_req = repo_sec.get("indicator_requirements") or {}
        if prod_req != repo_req:
            changes.append(f"{key}.indicator_requirements")
        prod_tbl = prod_sec.get("table_requirements") or {}
        repo_tbl = repo_sec.get("table_requirements") or {}
        if prod_tbl != repo_tbl:
            changes.append(f"{key}.table_requirements")

    rss_prod = (
        prod_ix.get("summary_and_overview", {})
        .get("table_requirements", {})
        .get("review_summary_sheet")
    )
    rss_repo = (
        repo_ix.get("summary_and_overview", {})
        .get("table_requirements", {})
        .get("review_summary_sheet")
    )
    print(json.dumps({
        "section_key_parity": sorted(prod_ix.keys()) == sorted(repo_ix.keys()),
        "changed_fields": changes,
        "review_summary_sheet_prod": rss_prod,
        "review_summary_sheet_repo": rss_repo,
        "format_rules_equal": prod.get("format_rules_json") == repo.get("format_rules_json"),
        "terminology_equal": prod.get("terminology_map_json") == repo.get("terminology_map_json"),
    }, indent=2))


if __name__ == "__main__":
    main()
