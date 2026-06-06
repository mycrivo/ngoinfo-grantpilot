"""Generate A-04 sample DOCX files for founder review."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.reports.export.docx_renderer import render_donor_report_docx
from app.services.proposal_docx_renderer import build_proposal_docx_bytes
AUDITS = ROOT / "audits"
FCDO_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
FCDO_CONTENT = ROOT / "tests" / "fixtures" / "export" / "fcdo_recorded_content_json.json"


def main() -> None:
    AUDITS.mkdir(parents=True, exist_ok=True)
    generated_at = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)

    proposal_bytes = build_proposal_docx_bytes(
        content_json={
            "sections": [
                {
                    "label": "Executive Summary",
                    "generation_status": "GENERATED",
                    "content": {
                        "text": (
                            "BridgeLight will re-enrol out-of-school girls across three districts, "
                            "combining community mobilisation with targeted learning support."
                        ),
                        "assumptions": [
                            "Exchange rate held at planning assumptions.",
                            "Partner schools remain accessible during term.",
                        ],
                    },
                },
                {
                    "label": "Project Design",
                    "generation_status": "GENERATED",
                    "content": {
                        "text": (
                            "Activities focus on safe return pathways, teacher coaching, and "
                            "menstrual health support in upper-primary cohorts."
                        ),
                        "assumptions": [],
                    },
                },
                {
                    "label": "Budget Narrative",
                    "generation_status": "MANUAL_REQUIRED",
                    "content": {"text": "", "assumptions": []},
                },
            ]
        },
        opportunity_title="FCDO Girls' Education Fund",
        ngo_name="BridgeLight Education Trust",
        generated_at=generated_at,
    )
    proposal_path = AUDITS / "A_04_SAMPLE_proposal.docx"
    proposal_path.write_bytes(proposal_bytes)

    fcdo = json.loads(FCDO_TEMPLATE.read_text(encoding="utf-8"))
    content_json = json.loads(FCDO_CONTENT.read_text(encoding="utf-8"))
    sections = list(content_json["sections"])
    for section in sections:
        if section.get("section_key") == "risk_and_safeguarding":
            section["content"]["assumptions"] = [
                "Teacher focal points remain in post for the review period.",
            ]
    content_json["sections"] = sections

    me_bytes, _ = render_donor_report_docx(
        content_json=content_json,
        template_sections=fcdo["report_sections_json"],
        format_rules_json=fcdo["format_rules_json"],
        terminology_map_json=fcdo["terminology_map_json"],
        docx_template_ref=None,
        reporting_period_start="2024-10-15",
        reporting_period_end="2025-10-14",
        funder_name=fcdo["funder_name"],
        template_name=fcdo["template_name"],
        ngo_name="BridgeLight Education Trust",
        generated_at=generated_at,
    )
    me_path = AUDITS / "A_04_SAMPLE_me_report.docx"
    me_path.write_bytes(me_bytes)

    print(f"Wrote {proposal_path}")
    print(f"Wrote {me_path}")


if __name__ == "__main__":
    main()
