"""R1/R2 helpers for Package 1 orphan repair evidence — no DB access."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit" / "gate1_orphan_repair_cb090edb.py"


def _load_repair_module():
    spec = importlib.util.spec_from_file_location("gate1_orphan_repair_cb090edb", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_field_level_diff_includes_stub_and_provenance_markers():
    mod = _load_repair_module()
    preimage = {
        "facts": {
            "reporting_period.end_formal": {
                "value": "2025-10-14",
                "source_document_id": "doc-award",
            }
        },
        "conflicts": [{"fact_key": "reporting_period.end", "values": []}],
    }
    postimage = {
        "facts": {
            "reporting_period.end": {
                "value": None,
                "verification_status": "unverified",
                "semantic_label": "Reporting period — End",
            },
            "reporting_period.end_formal": {
                "value": "2025-10-14",
                "source_document_id": "doc-award",
                "provenance_only_for": "reporting_period.end",
            },
        },
        "conflicts": preimage["conflicts"],
        "agent_trace": {
            "conflict_integrity_repairs": [
                {
                    "conflict_key": "reporting_period.end",
                    "created_canonical_stub": True,
                    "provenance_only_fact_keys": ["reporting_period.end_formal"],
                }
            ]
        },
    }
    diff = mod.field_level_kb_diff(preimage, postimage)
    assert "reporting_period.end" in diff["facts_added"]
    assert diff["canonical_stub"]["value"] is None
    assert diff["provenance_only_markers"]["reporting_period.end_formal"] == (
        "reporting_period.end"
    )
    assert diff["facts_changed"]["reporting_period.end_formal"]["provenance_only_for"][
        "to"
    ] == "reporting_period.end"
    assert len(diff["conflict_integrity_repairs_added"]) == 1


def test_prepare_repair_never_writes_resolved_value():
    mod = _load_repair_module()
    preimage = {
        "facts": {
            "reporting_period.end_formal": {
                "value": "2025-10-14",
                "semantic_label": "Formal end",
                "source_document_id": "doc-award",
                "source_label": "award.docx",
                "provenance": {"excerpt": "14 October 2025"},
                "coverage": "single_source",
                "verification_status": "reconciled",
            },
            "reporting_period.end_inception_call": {
                "value": None,
                "semantic_label": "Inception end",
                "source_document_id": "doc-award",
                "source_label": "award.docx",
                "provenance": {"excerpt": "October to September"},
                "coverage": "single_source",
                "verification_status": "reconciled",
            },
        },
        "conflicts": [
            {
                "fact_key": "reporting_period.end",
                "conflict_type": "VALUE_MISMATCH",
                "resolved_value": None,
                "values": [
                    {
                        "value": "2025-10-14",
                        "source_document_id": "doc-award",
                        "source_label": "award.docx",
                        "provenance": {"excerpt": "14 October 2025"},
                    },
                    {
                        "value": None,
                        "source_document_id": "doc-award",
                        "source_label": "award.docx",
                        "provenance": {"excerpt": "October to September"},
                    },
                ],
            }
        ],
    }
    repaired = mod.prepare_repair(preimage)
    assert repaired["facts"]["reporting_period.end"]["value"] is None
    assert repaired["conflicts"][0]["resolved_value"] is None
