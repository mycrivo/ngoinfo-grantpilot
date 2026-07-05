"""Package B1: proposal partner + consultation capture and A-routing proof.

Proven against the REAL NLCF proposal text (tests/fixtures/proposal_extractor/
nlcf_southbank_proposal.md), Docling-exported from the real .docx - NOT a hand-built
favourable fixture. On the Smoke Test P0 M&E allowlist (.github/workflows).

Anti-self-shaping discipline (owner pin): every partner name and every consultation
label/count asserted by these tests is verified to be a literal substring of the REAL
proposal text, so the mocked LLM response cannot smuggle in content that is not on the
page.

What these tests PROVE:
- The schema/mapper carry named partners + the consultation narrative.
- The flattener promotes them into partnerships.* / engagement.* (the namespaces
  merged-A routes to community_involvement); zero invented entries.
- Through merged-A's REAL routing the facts are visible to community_involvement and do
  NOT bleed into difference_made / learning / changes / spend_summary / project_story.

What these tests do NOT prove:
- That the live model extracts partners/consultation from the prose on its own. That is
  the owner re-walk (out of scope here).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.reports.agents.knowledge_bank_reconciler import _llm_to_structured
from app.reports.agents.proposal_extractor import extract_proposal_text_sync
from app.reports.reconciliation.input_builder import (
    ReconciliationInputBundle,
    _flatten_proposal,
)
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KnowledgeBankReconcilerLLMOutput,
)
from app.reports.services.report_inputs_builder import (
    section_has_synthesizable_inputs,
    subset_facts_for_section,
)
from claude_agent_sdk import ResultMessage

_REPO = Path(__file__).resolve().parents[1]
_PROPOSAL = _REPO / "tests/fixtures/proposal_extractor/nlcf_southbank_proposal.md"
_TEMPLATE = _REPO / "docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json"

_DOC_ID = "proposal-doc"
_SOURCE_LABEL = "01_NLCF_Southbank_Application_Proposal.docx"


def _proposal_text() -> str:
    return _PROPOSAL.read_text(encoding="utf-8")


def _sections() -> list[dict]:
    return json.loads(_TEMPLATE.read_text(encoding="utf-8"))["report_sections_json"]


def _section(key: str) -> dict:
    return next(s for s in _sections() if s.get("section_key") == key)


# Partner names + consultation items, each a verbatim slice of the REAL proposal prose.
_REAL_PARTNERS = [
    "local schools",
    "the GP social prescribing team",
    "two tenants groups",
    "the food pantry",
]
_REAL_CONSULTATION = [
    ("parents_consulted", "spoke to 26 parents at the food pantry", "26", "parents"),
    ("young_people_consulted", "14 young people at the homework club", "14", "young people"),
    ("older_residents_consulted", "7 older residents who use the warm space", "7", "older residents"),
    (
        "ongoing_involvement",
        "short feedback cards, monthly volunteer catch-ups and informal conversations",
        None,
        None,
    ),
]


def _mock_llm_response() -> dict:
    partners = [
        {
            "partner_key": f"partner_{i}",
            "name": name,
            "relationship": None,
            "status": "extracted",
            "provenance": {
                "excerpt": "work with local schools, the GP social prescribing team",
                "section_label": "Project story",
            },
        }
        for i, name in enumerate(_REAL_PARTNERS)
    ]
    consultation = [
        {
            "engagement_key": key,
            "label": label,
            "value": value,
            "unit": unit,
            "status": "extracted",
            "provenance": {
                "excerpt": label[:80],
                "section_label": "How the community shaped the project",
            },
        }
        for key, label, value, unit in _REAL_CONSULTATION
    ]
    return {
        "confidence": 0.9,
        "objectives": [],
        "activities": [],
        "indicators": [],
        "partners": partners,
        "consultation": consultation,
    }


def _result_message(payload: dict) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=150,
        duration_api_ms=130,
        is_error=False,
        num_turns=1,
        session_id="test-session",
        structured_output=payload,
        usage={"input_tokens": 80, "output_tokens": 200},
    )


def _mock_query_factory(response: dict):
    async def _mock_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(response)

    return _mock_query


def _structured() -> dict:
    result = extract_proposal_text_sync(
        _proposal_text(),
        filename=_SOURCE_LABEL,
        query_fn=_mock_query_factory(_mock_llm_response()),
    )
    return result.envelope.structured.model_dump()


def _bundle() -> ReconciliationInputBundle:
    return ReconciliationInputBundle(
        fact_candidates=_flatten_proposal(_DOC_ID, _SOURCE_LABEL, _structured())
    )


def _reconciled_facts() -> dict[str, dict]:
    bundle = _bundle()
    llm_facts = [
        {
            "fact_key": cand.field_path,
            "value": cand.value_normalized,
            "unit": cand.unit,
            "semantic_label": cand.semantic_hint,
            "source_document_id": cand.document_id,
            "source_label": cand.source_label,
            "provenance": {
                "excerpt": (cand.provenance or {}).get("excerpt") or "(no excerpt)",
                "cell_ref": (cand.provenance or {}).get("cell_ref"),
            },
        }
        for cand in bundle.fact_candidates
    ]
    parsed = KnowledgeBankReconcilerLLMOutput.model_validate({"facts": llm_facts})
    structured = _llm_to_structured(parsed, bundle)
    return {key: fact.model_dump() for key, fact in structured.facts.items()}


# ===========================================================================
# Anti-self-shaping: the captured values are genuinely on the page
# ===========================================================================
def test_captured_values_trace_to_real_proposal_text():
    text = _proposal_text()
    for name in _REAL_PARTNERS:
        assert name in text, f"partner not in real proposal: {name}"
    for _key, label, value, _unit in _REAL_CONSULTATION:
        assert label in text, f"consultation phrase not in real proposal: {label}"
        if value is not None:
            assert value in text, f"consultation count not in real proposal: {value}"


# ===========================================================================
# Mapper - partners + consultation survive into the schema
# ===========================================================================
def test_mapper_carries_partners_and_consultation():
    structured = _structured()
    partners = structured["partners"]
    consultation = structured["consultation"]
    assert [p["name"] for p in partners] == _REAL_PARTNERS
    assert all(p["provenance"]["excerpt"] for p in partners)
    assert {e["engagement_key"] for e in consultation} == {
        k for k, *_ in _REAL_CONSULTATION
    }
    # Stated counts preserved; the unquantified item stays value=null (no invention).
    by_key = {e["engagement_key"]: e for e in consultation}
    assert by_key["parents_consulted"]["value"] == "26"
    assert by_key["ongoing_involvement"]["value"] is None


# ===========================================================================
# Promotion - real, zero-invented partnerships.* / engagement.* candidates
# ===========================================================================
def test_partners_and_consultation_promoted_to_namespaces():
    bundle = _bundle()
    partner_paths = {
        c.field_path for c in bundle.fact_candidates if c.field_path.startswith("partnerships.")
    }
    eng_paths = {
        c.field_path for c in bundle.fact_candidates if c.field_path.startswith("engagement.")
    }
    assert len(partner_paths) == len(_REAL_PARTNERS)
    assert len(eng_paths) == len(_REAL_CONSULTATION)

    # No source_section -> these route by declared namespace, not source-pin.
    for cand in bundle.fact_candidates:
        if cand.field_path.startswith(("partnerships.", "engagement.")):
            assert cand.source_section is None
            assert (cand.provenance or {}).get("excerpt")
            # D clean-label discipline: human hint carries no provenance tokens.
            assert "!" not in cand.semantic_hint

    # The partner fact value is the real name (e.g. food pantry).
    values = {c.value_raw for c in bundle.fact_candidates if c.field_path.startswith("partnerships.")}
    assert "the food pantry" in values


# ===========================================================================
# Routing through A - visible to community_involvement only
# ===========================================================================
def test_partners_and_consultation_route_to_community_involvement_only():
    facts = _reconciled_facts()
    sections = _sections()

    target_keys = {
        k for k in facts if k.startswith("partnerships.") or k.startswith("engagement.")
    }
    assert target_keys, "no partnership/engagement facts after reconcile join"

    ci = subset_facts_for_section(
        facts, _section("community_involvement"), report_sections=sections
    )
    assert {
        k for k in ci if k.startswith("partnerships.") or k.startswith("engagement.")
    } == target_keys

    for blind in (
        "difference_made",
        "learning",
        "changes_and_next_steps",
        "spend_summary",
        "project_story",
    ):
        view = subset_facts_for_section(
            facts, _section(blind), report_sections=sections
        )
        assert not any(
            k.startswith("partnerships.") or k.startswith("engagement.") for k in view
        ), f"partner/consultation content bled into {blind}"


def test_community_involvement_synthesizable_only_with_b_facts():
    """B un-starves the section: it becomes synthesizable once partners/consultation are
    captured, and is correctly insufficient when they are absent."""
    facts = _reconciled_facts()
    sec = _section("community_involvement")
    kb_with = {"facts": facts, "gate1_confirmed_at": "2026-01-01T00:00:00Z"}
    kb_without = {"facts": {}, "gate1_confirmed_at": "2026-01-01T00:00:00Z"}
    assert section_has_synthesizable_inputs(
        kb_with, sec, report_sections=_sections()
    ) is True
    assert section_has_synthesizable_inputs(
        kb_without, sec, report_sections=_sections()
    ) is False


def test_absent_partners_stay_absent():
    """Honest gaps: a proposal with no named partners promotes no partnership facts."""
    response = _mock_llm_response()
    response["partners"] = []
    response["consultation"] = []
    result = extract_proposal_text_sync(
        _proposal_text(),
        filename=_SOURCE_LABEL,
        query_fn=_mock_query_factory(response),
    )
    candidates = _flatten_proposal(
        _DOC_ID, _SOURCE_LABEL, result.envelope.structured.model_dump()
    )
    assert not any(
        c.field_path.startswith(("partnerships.", "engagement.")) for c in candidates
    )
