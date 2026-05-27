"""Generate gap compliance answer keys from T2 templates (one-off helper)."""

from __future__ import annotations

import json
from pathlib import Path

from app.reports.gap.satisfaction import unsatisfied_requirements
from app.reports.gap.template_requirements import enumerate_template_requirements

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "docs" / "artefacts" / "me_module"
KEYS = ROOT / "tests" / "fixtures" / "gap" / "keys"
REPORT_CONTEXT = {"report_type": "annual"}
DOC_ID = "a1111111-1111-4111-8111-111111111101"


def _fact(fact_key: str, label: str, excerpt: str) -> dict:
    return {
        "value": excerpt[:80],
        "unit": None,
        "semantic_label": label,
        "coverage": "single_source",
        "source_document_id": DOC_ID,
        "source_label": "uploaded_doc",
        "provenance": {"excerpt": excerpt},
    }


def _confirmed_kb(facts: dict | None = None) -> dict:
    return {
        "schema_version": "1.0.0",
        "facts": facts or {},
        "conflicts": [],
        "gap_answers": {},
        "gate1_confirmed_at": "2026-05-24T12:00:00+00:00",
        "reconciler_agent": "knowledge_bank_reconciler",
    }


def _complete_nlcf(template: dict) -> dict:
    facts = {}
    for section in template["report_sections_json"]:
        if not section.get("required", True):
            continue
        for indicator in section.get("required_indicators") or []:
            key = f"nlcf.{section['section_key']}.{indicator}"
            facts[key] = _fact(key, indicator, f"Evidence for {indicator}")
        for table in section.get("required_tables") or []:
            if (table.get("min_rows") or 0) < 1:
                continue
            tk = table["table_key"]
            key = f"nlcf.{section['section_key']}.table.{tk}"
            facts[key] = _fact(key, tk, f"Table {tk}")
    return _confirmed_kb(facts)


def _incomplete_nlcf() -> dict:
    return _confirmed_kb(
        {
            "nlcf.project_story.summary": _fact(
                "nlcf.project_story.summary", "project story", "Activities delivered."
            )
        }
    )


def _incomplete_fcdo() -> dict:
    return _confirmed_kb(
        {
            "fcdo.summary.overall_progress": _fact(
                "fcdo.summary.overall_progress", "overall progress", "On track."
            )
        }
    )


def _complete_fcdo(template: dict) -> dict:
    recorded = json.loads(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "reconciler"
            / "recorded"
            / "fcdo_bridgelight_recorded_knowledge_bank.json"
        ).read_text(encoding="utf-8")
    )
    recorded["gate1_confirmed_at"] = "2026-05-24T12:00:00+00:00"
    reqs = enumerate_template_requirements(
        template["report_sections_json"], report_context=REPORT_CONTEXT
    )
    for req in unsatisfied_requirements(reqs, recorded):
        recorded.setdefault("facts", {})[req.required_item_ref] = _fact(
            req.required_item_ref, req.required_item_ref, f"Evidence for {req.required_item_ref}"
        )
    return recorded


def write_key(name: str, template: dict, kb: dict, *, max_gaps: int | None = None) -> None:
    reqs = enumerate_template_requirements(
        template["report_sections_json"], report_context=REPORT_CONTEXT
    )
    missing = unsatisfied_requirements(reqs, kb)
    key = {
        "fixture": name,
        "report_context": REPORT_CONTEXT,
        "expected_missing": [
            {
                "section_key": r.section_key,
                "required_item_type": r.required_item_type,
                "required_item_ref": r.required_item_ref,
            }
            for r in missing
        ],
        "forbidden_gaps": [],
        "max_gaps": max_gaps,
    }
    KEYS.mkdir(parents=True, exist_ok=True)
    out = KEYS / f"{name}_answer_key.json"
    out.write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"{name}: {len(key['expected_missing'])} expected gaps")


def main() -> None:
    nlcf = json.loads((TEMPLATES / "TEMPLATE_INSTANCE_NLCF.json").read_text(encoding="utf-8"))
    fcdo = json.loads((TEMPLATES / "TEMPLATE_INSTANCE_FCDO.json").read_text(encoding="utf-8"))
    write_key("nlcf_incomplete", nlcf, _incomplete_nlcf())
    write_key("nlcf_complete", nlcf, _complete_nlcf(nlcf), max_gaps=0)
    write_key("fcdo_incomplete", fcdo, _incomplete_fcdo())
    write_key("fcdo_complete", fcdo, _complete_fcdo(fcdo), max_gaps=0)


if __name__ == "__main__":
    main()
