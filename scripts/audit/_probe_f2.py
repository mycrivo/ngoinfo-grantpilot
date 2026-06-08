"""Isolated F2 fact-safety critic probe — false-negative (dangerous) direction.

Loads backend secrets from Railway so the live Anthropic path runs.
"""
import asyncio
import json
import os

from scripts.audit import _common as C


def _load_anthropic_key() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    v = C.railway_vars("--service", C.BACKEND_SERVICE)
    for k in ("ANTHROPIC_API_KEY", "ME_FACT_SAFETY_CRITIC_MODEL", "ME_RECONCILER_MODEL"):
        if v.get(k):
            os.environ[k] = str(v[k])


_load_anthropic_key()
from app.reports.agents.fact_safety_critic import run_fact_safety_critic


CASES = [
    {
        "name": "A_uncited_fabricated_specifics",
        "section_key": "summary_and_overview",
        "section_label": "Summary and Overview",
        "section_text": (
            "During the reporting period BridgeLight re-enrolled 684 girls. "
            "The programme also constructed 1,247 boreholes across Kasungu district, "
            "directly reaching 99,812 households and training 415 community health volunteers."
        ),
        "evidence_used": ["fact:indicators.OP1.1.ar1_actual"],
        "cited_sources": {"fact:indicators.OP1.1.ar1_actual": 684},
    },
    {
        "name": "B_control_supported_and_cited",
        "section_key": "summary_and_overview",
        "section_label": "Summary and Overview",
        "section_text": (
            "BridgeLight re-enrolled 684 girls against an annual milestone target of 650."
        ),
        "evidence_used": [
            "fact:indicators.OP1.1.ar1_actual",
            "fact:indicators.OP1.1.ar1_milestone_target",
        ],
        "cited_sources": {
            "fact:indicators.OP1.1.ar1_actual": 684,
            "fact:indicators.OP1.1.ar1_milestone_target": 650,
        },
    },
    {
        "name": "C_cited_key_but_value_mismatch",
        "section_key": "summary_and_overview",
        "section_label": "Summary and Overview",
        "section_text": (
            "BridgeLight re-enrolled 5,000 girls against an annual milestone target of 650."
        ),
        "evidence_used": [
            "fact:indicators.OP1.1.ar1_actual",
            "fact:indicators.OP1.1.ar1_milestone_target",
        ],
        "cited_sources": {
            "fact:indicators.OP1.1.ar1_actual": 684,
            "fact:indicators.OP1.1.ar1_milestone_target": 650,
        },
    },
]


async def run() -> None:
    results = []
    for case in CASES:
        res = await run_fact_safety_critic(
            section_key=case["section_key"],
            section_label=case["section_label"],
            section_text=case["section_text"],
            evidence_used=case["evidence_used"],
            cited_sources=case["cited_sources"],
        )
        out = res.output
        specifics = [
            {"text": getattr(s, "specific", None) or getattr(s, "claim", None),
             "status": getattr(s, "status", None),
             "severity": getattr(s, "severity", None),
             "reason": getattr(s, "reason", None)}
            for s in (out.specifics or [])
        ]
        row = {
            "case": case["name"],
            "fact_safety_status": out.fact_safety_status,
            "model": res.model_used,
            "specifics": specifics,
        }
        results.append(row)
        print(json.dumps(row, indent=2, default=str))
    C.write_artifact("f2_falseneg_probe.json", {"cases": results})


if __name__ == "__main__":
    asyncio.run(run())
