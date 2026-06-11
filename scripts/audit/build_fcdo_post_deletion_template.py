#!/usr/bin/env python3
"""Build fully-tagged FCDO post-deletion template JSON for B2b one-op replace."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.reports.gap.requirement_metadata import resolve_owner, resolve_requirement_type
from scripts.audit.b1_template_analysis import (
    KILL_INDICATORS,
    KILL_SECTIONS,
    KILL_TABLES,
    _collect_refs,
    _tag_stats,
    build_cleaned,
)

TEMPLATE = ROOT / "docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json"
OUT = ROOT / "tests/fixtures/templates/fcdo_55f891ac_post_deletion_v1.2.0.json"
TEMPLATE_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"


def _apply_v120_tags(sections: list[dict]) -> list[dict]:
    tagged: list[dict] = []
    for sec in sections:
        sec = json.loads(json.dumps(sec))
        ind_req: dict = dict(sec.get("indicator_requirements") or {})
        tbl_req: dict = dict(sec.get("table_requirements") or {})
        for ind in sec.get("required_indicators") or []:
            key = str(ind)
            existing = dict(ind_req.get(key) or {})
            owner = existing.get("owner") or resolve_owner(
                sec, item_ref=key, item_type="indicator"
            )
            rtype = existing.get("requirement_type") or resolve_requirement_type(
                sec, item_ref=key, item_type="indicator"
            )
            ind_req[key] = {"owner": owner, "requirement_type": rtype}
        for tbl in sec.get("required_tables") or []:
            if not isinstance(tbl, dict):
                continue
            tkey = str(tbl.get("table_key") or "")
            if not tkey:
                continue
            existing = dict(tbl_req.get(tkey) or {})
            owner = existing.get("owner") or resolve_owner(
                sec, item_ref=tkey, item_type="table"
            )
            rtype = existing.get("requirement_type") or resolve_requirement_type(
                sec, item_ref=tkey, item_type="table"
            )
            tbl_req[tkey] = {"owner": owner, "requirement_type": rtype}
        sec["indicator_requirements"] = ind_req
        sec["table_requirements"] = tbl_req
        tagged.append(sec)
    return tagged


def _fully_tagged(stats: dict) -> bool:
    return (
        stats["tagged_requirements"] == stats["total_requirements"]
        and stats["total_requirements"] > 0
    )


def _per_item_tagged(sections: list[dict]) -> tuple[int, int]:
    tagged = 0
    total = 0
    for sec in sections:
        ind_req = sec.get("indicator_requirements") or {}
        for ind in sec.get("required_indicators") or []:
            total += 1
            meta = ind_req.get(str(ind)) or {}
            if meta.get("owner") and meta.get("requirement_type"):
                tagged += 1
        tbl_req = sec.get("table_requirements") or {}
        for tbl in sec.get("required_tables") or []:
            if not isinstance(tbl, dict):
                continue
            tkey = str(tbl.get("table_key") or "")
            if not tkey:
                continue
            total += 1
            meta = tbl_req.get(tkey) or {}
            if meta.get("owner") and meta.get("requirement_type"):
                tagged += 1
    return tagged, total


def main() -> int:
    repo = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    cleaned = build_cleaned(list(repo["report_sections_json"]))
    sections = _apply_v120_tags(cleaned)

    kill_refs = KILL_INDICATORS | KILL_TABLES
    remaining_kill = sorted(_collect_refs(sections) & kill_refs)
    remaining_kill_sections = sorted(
        {str(s.get("section_key")) for s in sections} & KILL_SECTIONS
    )

    strict_tagged, strict_total = _per_item_tagged(sections)
    stats = _tag_stats(sections)

    payload = {
        "id": TEMPLATE_ID,
        "source": (
            "TEMPLATE_INSTANCE_FCDO.json + P2_FUNDER_ROW_DELETION_PROPOSAL kill list "
            "+ requirement_metadata v1.2.0 tag enrichment"
        ),
        "report_sections_json": sections,
        "format_rules_json": repo.get("format_rules_json"),
        "terminology_map_json": repo.get("terminology_map_json"),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")

    report = {
        "artifact": str(OUT.relative_to(ROOT)),
        "section_count": len(sections),
        "section_keys": sorted(s.get("section_key") for s in sections),
        "tag_stats": stats,
        "strict_v120_tagged": strict_tagged,
        "strict_v120_total": strict_total,
        "kill_list_refs_remaining": remaining_kill,
        "kill_sections_remaining": remaining_kill_sections,
        "checksum_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }
    print(json.dumps(report, indent=2))

    if len(sections) != 6:
        return 1
    if remaining_kill or remaining_kill_sections:
        return 1
    if strict_tagged != strict_total:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
