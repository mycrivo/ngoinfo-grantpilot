#!/usr/bin/env python3
"""Distil FCDO complete-gap KB fixture from walk 3347590c (P2-CORRECTIONS).

Usage:
  python scripts/audit/distill_fcdo_complete_gap_fixture.py
  python scripts/audit/distill_fcdo_complete_gap_fixture.py --probe-gaps
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMITTED_KB_FIXTURE = (
    ROOT / "tests" / "fixtures" / "gap" / "fcdo_complete_3347590c_knowledge_bank.json"
)
FCDO_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
OUTPUT_PATH = COMMITTED_KB_FIXTURE
EXPECTED_GAPS_PATH = (
    ROOT / "tests" / "fixtures" / "gap" / "fcdo_complete_3347590c_expected_gaps.json"
)

SOURCE_REPORT_ID = "3347590c-5b4f-4443-8a3d-a5ae455932e2"
SOURCE_FIXTURE = "tests/fixtures/gap/fcdo_complete_3347590c_knowledge_bank.json"


def _load_kb_slice(*, walk_path: Path | None = None) -> dict:
    if walk_path is not None and walk_path.exists():
        walk = json.loads(walk_path.read_text(encoding="utf-8"))
        return walk["snapshots"]["after_gap"]["report"]["knowledge_bank_json"]
    fixture = json.loads(COMMITTED_KB_FIXTURE.read_text(encoding="utf-8"))
    return fixture["knowledge_bank_json"]


def _build_fixture(kb: dict) -> dict:
    facts = kb.get("facts") or {}
    return {
        "description": (
            "FCDO BridgeLight complete-gap KB — distilled from walk 3347590c "
            "(Gate-1 confirmed, empty gap_answers). No synthetic backfill."
        ),
        "source_report_id": SOURCE_REPORT_ID,
        "source_walk": SOURCE_FIXTURE,
        "distilled_at": datetime.now(timezone.utc).isoformat(),
        "fact_count": len(facts),
        "knowledge_bank_json": kb,
    }


async def _probe_gaps(kb: dict) -> list[dict]:
    from app.reports.agents.gap_compliance_agent import run_gap_compliance

    template = json.loads(FCDO_TEMPLATE.read_text(encoding="utf-8"))
    result = await run_gap_compliance(
        knowledge_bank_json=kb,
        template_payload=template,
        report_context={"report_type": "annual"},
    )
    gaps = result.envelope.structured.gaps
    return [
        {
            "section_key": g.section_key,
            "required_item_type": g.required_item_type,
            "required_item_ref": g.required_item_ref,
            "item_key": g.item_key,
        }
        for g in gaps
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Distil 3347590c FCDO complete-gap KB fixture")
    parser.add_argument(
        "--probe-gaps",
        action="store_true",
        help="Run deterministic gap compliance and write expected_gaps sidecar",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print fixture JSON to stdout instead of writing file",
    )
    parser.add_argument(
        "--walk",
        type=Path,
        default=None,
        help="Optional local walk JSON (default: committed KB fixture)",
    )
    args = parser.parse_args()

    kb = _load_kb_slice(walk_path=args.walk)
    fixture = _build_fixture(kb)

    if args.probe_gaps:
        gaps = asyncio.run(_probe_gaps(kb))
        sidecar = {
            "source_report_id": SOURCE_REPORT_ID,
            "source_walk": SOURCE_FIXTURE,
            "probed_at": datetime.now(timezone.utc).isoformat(),
            "open_items_count": len(gaps),
            "expected_missing": [
                {
                    "section_key": g["section_key"],
                    "required_item_type": g["required_item_type"],
                    "required_item_ref": g["required_item_ref"],
                }
                for g in gaps
            ],
            "required_item_refs": sorted(g["required_item_ref"] for g in gaps),
        }
        EXPECTED_GAPS_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXPECTED_GAPS_PATH.write_text(
            json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {EXPECTED_GAPS_PATH} ({len(gaps)} gaps)", file=sys.stderr)

    if args.stdout:
        print(json.dumps(fixture, indent=2, ensure_ascii=False))
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH} ({fixture['fact_count']} facts)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
