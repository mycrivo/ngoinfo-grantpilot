#!/usr/bin/env python3
"""Analyze FCDO template instances for B1 re-stage M1/M2."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json"
SNAPSHOT = ROOT / "docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json"
PROPOSAL = ROOT / "docs/artefacts/me_module/audits/P2_FUNDER_ROW_DELETION_PROPOSAL.md"

KILL_SECTIONS = frozenset({"detailed_output_scoring", "value_for_money"})
KILL_INDICATORS = frozenset(
    {
        "output_scores",
        "impact_weightings",
        "risk_ratings",
        "economy",
        "efficiency",
        "effectiveness",
        "equity",
        "commercial_improvement_where_relevant",
        "FCDO_management_actions",
    }
)
KILL_TABLES = frozenset({"output_score_table", "vfm_measures", "review_summary_sheet"})


def _tag_stats(sections: list[dict]) -> dict:
    total_indicators = 0
    total_tables = 0
    tagged_indicators = 0
    tagged_tables = 0
    by_section: dict[str, dict] = {}
    for sec in sections:
        key = str(sec.get("section_key") or "")
        inds = list(sec.get("required_indicators") or [])
        tbls = [t.get("table_key") for t in (sec.get("required_tables") or []) if isinstance(t, dict)]
        ind_req = sec.get("indicator_requirements") or {}
        tbl_req = sec.get("table_requirements") or {}
        ti = sum(1 for i in inds if isinstance(ind_req.get(i), dict) and (ind_req[i].get("owner") or ind_req[i].get("requirement_type")))
        tt = sum(1 for t in tbls if isinstance(tbl_req.get(t), dict) and (tbl_req[t].get("owner") or tbl_req[t].get("requirement_type")))
        total_indicators += len(inds)
        total_tables += len(tbls)
        tagged_indicators += ti
        tagged_tables += tt
        by_section[key] = {
            "owner": sec.get("owner"),
            "indicators": len(inds),
            "tables": len(tbls),
            "tagged_indicators": ti,
            "tagged_tables": tt,
        }
    return {
        "total_indicators": total_indicators,
        "total_tables": total_tables,
        "tagged_indicators": tagged_indicators,
        "tagged_tables": tagged_tables,
        "tagged_requirements": tagged_indicators + tagged_tables,
        "total_requirements": total_indicators + total_tables,
        "by_section": by_section,
    }


def _collect_refs(sections: list[dict]) -> set[str]:
    refs: set[str] = set()
    for sec in sections:
        for i in sec.get("required_indicators") or []:
            refs.add(str(i))
        for t in sec.get("required_tables") or []:
            if isinstance(t, dict) and t.get("table_key"):
                refs.add(str(t["table_key"]))
    return refs


def build_cleaned(sections: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for sec in sections:
        key = str(sec.get("section_key") or "")
        if key in KILL_SECTIONS:
            continue
        sec = json.loads(json.dumps(sec))
        sec["required_indicators"] = [
            i for i in (sec.get("required_indicators") or []) if str(i) not in KILL_INDICATORS
        ]
        sec["required_tables"] = [
            t
            for t in (sec.get("required_tables") or [])
            if isinstance(t, dict) and str(t.get("table_key") or "") not in KILL_TABLES
        ]
        ind_req = dict(sec.get("indicator_requirements") or {})
        for k in list(ind_req):
            if k in KILL_INDICATORS:
                ind_req.pop(k, None)
        sec["indicator_requirements"] = ind_req
        tbl_req = dict(sec.get("table_requirements") or {})
        for k in list(tbl_req):
            if k in KILL_TABLES:
                tbl_req.pop(k, None)
        sec["table_requirements"] = tbl_req
        cleaned.append(sec)
    return cleaned


def build_tags_only(prod_sections: list[dict], repo_sections: list[dict]) -> list[dict]:
    repo_ix = {str(s.get("section_key")): s for s in repo_sections}
    merged: list[dict] = []
    for prod_sec in prod_sections:
        key = str(prod_sec.get("section_key") or "")
        repo_sec = repo_ix.get(key, {})
        sec = json.loads(json.dumps(prod_sec))
        for field in ("owner", "requirement_type_default", "indicator_requirements", "table_requirements"):
            if field in repo_sec:
                sec[field] = repo_sec[field]
        merged.append(sec)
    return merged


def main() -> None:
    repo = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    prod = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    repo_secs = list(repo["report_sections_json"])
    prod_secs = list(prod["report_sections_json"])
    cleaned_secs = build_cleaned(repo_secs)
    tags_only_secs = build_tags_only(prod_secs, repo_secs)

    out = ROOT / "docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json"
    tags_out = ROOT / "docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_intended_tags_only_2026-06-11.json"
    payload = {
        "id": "55f891ac-bb8b-4137-bc42-6de8ff935064",
        "source": "TEMPLATE_INSTANCE_FCDO.json + P2_FUNDER_ROW_DELETION_PROPOSAL kill list",
        "report_sections_json": cleaned_secs,
        "format_rules_json": repo.get("format_rules_json"),
        "terminology_map_json": repo.get("terminology_map_json"),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8")

    tags_payload = {
        **payload,
        "operation": "tags_only_two_step",
        "report_sections_json": tags_only_secs,
    }
    tags_text = json.dumps(tags_payload, indent=2, ensure_ascii=False) + "\n"
    tags_out.write_text(tags_text, encoding="utf-8")

    print(json.dumps({
        "template_instance_fcdo": {
            "section_count": len(repo_secs),
            "section_keys": sorted(s.get("section_key") for s in repo_secs),
            "tag_stats": _tag_stats(repo_secs),
            "kill_list_refs_present": sorted(_collect_refs(repo_secs) & (KILL_INDICATORS | KILL_TABLES)),
            "kill_sections_present": sorted(KILL_SECTIONS & {s.get("section_key") for s in repo_secs}),
        },
        "prod_snapshot": {
            "section_count": len(prod_secs),
            "section_keys": sorted(s.get("section_key") for s in prod_secs),
            "tag_stats": _tag_stats(prod_secs),
        },
        "intended_post_mutation_one_op": {
            "artifact": str(out.relative_to(ROOT)),
            "section_count": len(cleaned_secs),
            "section_keys": sorted(s.get("section_key") for s in cleaned_secs),
            "tag_stats": _tag_stats(cleaned_secs),
            "kill_list_refs_remaining": sorted(_collect_refs(cleaned_secs) & (KILL_INDICATORS | KILL_TABLES)),
            "checksum_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "removed_section_keys": sorted(set(s.get("section_key") for s in prod_secs) - {s.get("section_key") for s in cleaned_secs}),
            "removed_refs_vs_prod": sorted(_collect_refs(prod_secs) - _collect_refs(cleaned_secs)),
        },
        "intended_tags_only_two_step": {
            "artifact": str(tags_out.relative_to(ROOT)),
            "section_count": len(tags_only_secs),
            "section_keys": sorted(s.get("section_key") for s in tags_only_secs),
            "tag_stats": _tag_stats(tags_only_secs),
            "checksum_sha256": hashlib.sha256(tags_text.encode()).hexdigest(),
        },
    }, indent=2))


if __name__ == "__main__":
    main()
