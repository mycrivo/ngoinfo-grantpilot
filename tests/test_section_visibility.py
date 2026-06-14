"""Package A — section-scoped visibility + remit-scoped, disclosure-complete caveats.

Proven against the REAL NLCF re-walk knowledge bank (pkg2_nlcf_rewalk_703f0dcf.json)
and the REAL Docling-captured monitoring section column
(tests/fixtures/kb/nlcf_monitoring_section_column.json), never a favourable fixture.

Covers:
- source-section PIN routing (real facts routed to the section the source assigned),
- over-widening prevention (volunteer count does NOT bleed into learning),
- namespace-root matcher (grant_*/reporting_*/objectives.* now visible),
- resolver fail-safe (unmatched source label -> declared-needs, observable, not dropped),
- forward-compatible routing of the four locked namespaces (synthetic facts),
- remit-scoped, disclosure-complete caveats (owner-only + present-suppressed).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pytest

from app.reports.services.remit_disclosure import (
    build_owned_absent_disclosure,
    owned_absent_requirements,
)
from app.reports.services.report_inputs_builder import subset_facts_for_section

REPO = Path(__file__).resolve().parents[1]
NLCF_TEMPLATE_PATH = REPO / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_NLCF.json"
WALK_PATH = (
    REPO
    / "docs"
    / "artefacts"
    / "me_module"
    / "audits"
    / "snapshots"
    / "pkg2_nlcf_rewalk_703f0dcf.json"
)
SECTION_COLUMN_PATH = REPO / "tests" / "fixtures" / "kb" / "nlcf_monitoring_section_column.json"

GATE1_TS = "2026-01-01T00:00:00+00:00"


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def nlcf_sections() -> list[dict]:
    template = json.loads(NLCF_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template["report_sections_json"]


@pytest.fixture(scope="module")
def sections_by_key(nlcf_sections) -> dict[str, dict]:
    return {s["section_key"]: s for s in nlcf_sections}


@pytest.fixture(scope="module")
def section_column() -> dict[str, str]:
    raw = json.loads(SECTION_COLUMN_PATH.read_text(encoding="utf-8"))
    return raw["Table2"]


@pytest.fixture(scope="module")
def walk_facts(section_column) -> dict[str, dict]:
    """Real walk KB facts with source_section attached EXACTLY as the runtime carrier
    does: deterministically from the source section column, joined by cell_ref, for
    indicator facts only (financials/targets carry no source_section, matching schema)."""
    walk = json.loads(WALK_PATH.read_text(encoding="utf-8"))
    kb = walk["snapshots"]["after_reconcile"]["report"]["knowledge_bank_json"]
    out: dict[str, dict] = {}
    for key, fact in kb["facts"].items():
        fact = dict(fact)
        if key.startswith("indicators."):
            cell_ref = (fact.get("provenance") or {}).get("cell_ref")
            if cell_ref and "!" in cell_ref:
                sheet, ref = cell_ref.split("!", 1)
                match = re.search(r"(\d+)", ref)
                if sheet == "Table2" and match and match.group(1) in section_column:
                    fact["source_section"] = section_column[match.group(1)]
        out[key] = fact
    return out


def _subset(facts, sections_by_key, key, nlcf_sections):
    return subset_facts_for_section(
        facts, sections_by_key[key], report_sections=nlcf_sections
    )


# ------------------------------------------------------------------ source-section PIN


def test_learning_sees_its_source_routed_notes(walk_facts, sections_by_key, nlcf_sections):
    learning = _subset(walk_facts, sections_by_key, "learning", nlcf_sections)
    assert "indicators.monitoring_row9.actual" in learning
    assert "indicators.monitoring_row10.actual" in learning


def test_volunteer_count_does_not_bleed_into_learning(walk_facts, sections_by_key, nlcf_sections):
    learning = _subset(walk_facts, sections_by_key, "learning", nlcf_sections)
    # Source-pinned to "Difference made"; must NOT appear in learning/changes/community.
    assert "indicators.ind3_volunteers_recruited.actual" not in learning
    assert "indicators.ind4_participants_less_isolated.actual" not in learning
    assert "indicators.ind1_people_attend_one_session.actual" not in learning
    changes = _subset(walk_facts, sections_by_key, "changes_and_next_steps", nlcf_sections)
    community = _subset(walk_facts, sections_by_key, "community_involvement", nlcf_sections)
    assert "indicators.ind3_volunteers_recruited.actual" not in changes
    assert "indicators.ind3_volunteers_recruited.actual" not in community


def test_difference_made_sees_its_numbers_not_learning_or_story(
    walk_facts, sections_by_key, nlcf_sections
):
    diff = _subset(walk_facts, sections_by_key, "difference_made", nlcf_sections)
    # Its own source-pinned actuals.
    assert "indicators.ind3_volunteers_recruited.actual" in diff
    assert "indicators.ind4_participants_less_isolated.actual" in diff
    assert "indicators.ind1_people_attend_one_session.actual" in diff
    # Unpinned proposal targets route here via the indicators.*.target namespace.
    assert "indicators.ind1_people_attend_one_session.target" in diff
    # Learning notes (pinned elsewhere) and project-story rows must NOT bleed here.
    assert "indicators.monitoring_row9.actual" not in diff
    assert "indicators.monitoring_row10.actual" not in diff
    assert "indicators.monitoring_row2.actual" not in diff


def test_project_story_sees_its_row_not_finance_or_volunteers(
    walk_facts, sections_by_key, nlcf_sections
):
    story = _subset(walk_facts, sections_by_key, "project_story", nlcf_sections)
    assert "indicators.monitoring_row2.actual" in story  # source-pinned to Project story
    assert not any(k.startswith("financials.") for k in story)
    assert "indicators.ind3_volunteers_recruited.actual" not in story


def test_spend_summary_sees_financials(walk_facts, sections_by_key, nlcf_sections):
    spend = _subset(walk_facts, sections_by_key, "spend_summary", nlcf_sections)
    assert any(k.startswith("financials.lines.") for k in spend)
    # Spend summary is not a narrative beneficiary section: no volunteer actual.
    assert "indicators.ind3_volunteers_recruited.actual" not in spend


# --------------------------------------------------------------- namespace-root matcher


@pytest.mark.parametrize(
    "section_key", ["project_story", "difference_made", "learning", "community_involvement"]
)
def test_narrative_sections_see_programme_facts(
    section_key, walk_facts, sections_by_key, nlcf_sections
):
    """The matcher bug fix: underscore roots grant_/reporting_ + dotted objectives."""
    subset = _subset(walk_facts, sections_by_key, section_key, nlcf_sections)
    assert "grant_reference" in subset
    assert "grant_period.start" in subset
    assert "reporting_period.start" in subset
    assert any(k.startswith("objectives.") for k in subset)


# ---------------------------------------------------------------- resolver fail-safe


def test_unmatched_source_label_falls_back_and_is_observable(
    walk_facts, sections_by_key, nlcf_sections, caplog
):
    facts = dict(walk_facts)
    facts["indicators.mystery_row.actual"] = {
        "value": 7,
        "semantic_label": "mystery actual",
        "verification_status": "reconciled",
        "source_document_id": "doc",
        "source_label": "doc",
        "provenance": {"cell_ref": "Table2!D99"},
        "source_section": "Totally Unknown Funder Wording",
    }
    with caplog.at_level(logging.WARNING):
        diff = _subset(facts, sections_by_key, "difference_made", nlcf_sections)
        learning = _subset(facts, sections_by_key, "learning", nlcf_sections)
    # Fail-safe: not dropped — lands in declared-needs of an indicators-bearing section.
    assert "indicators.mystery_row.actual" in diff
    # Not misrouted to a section whose declared-needs don't admit it.
    assert "indicators.mystery_row.actual" not in learning
    # Observable, not silently swallowed.
    assert any("Totally Unknown Funder Wording" in rec.message for rec in caplog.records)


# ---------------------------------------------------- forward-compatible locked namespaces


def _synthetic_fact(value="x"):
    return {
        "value": value,
        "semantic_label": "synthetic",
        "verification_status": "reconciled",
        "source_document_id": "doc",
        "source_label": "doc",
        "provenance": {"excerpt": "synthetic"},
    }


def test_locked_namespaces_route_to_correct_sections(sections_by_key, nlcf_sections):
    facts = {
        "partnerships.partner_a.name": _synthetic_fact("Local Library"),
        "engagement.consultation_1.summary": _synthetic_fact("Residents consulted"),
        "indicators.monitoring_row5.note": _synthetic_fact("Boiler repair paused sessions"),
        "indicators.monitoring_row3.disaggregation.female": _synthetic_fact(86),
    }

    def sub(key):
        return _subset(facts, sections_by_key, key, nlcf_sections)

    community = sub("community_involvement")
    assert "partnerships.partner_a.name" in community
    assert "engagement.consultation_1.summary" in community

    changes = sub("changes_and_next_steps")
    assert "indicators.monitoring_row5.note" in changes

    diff = sub("difference_made")
    assert "indicators.monitoring_row3.disaggregation.female" in diff
    # Notes must NOT bleed into the numbers section.
    assert "indicators.monitoring_row5.note" not in diff
    # Partnerships/engagement must NOT bleed into learning.
    learning = sub("learning")
    assert "partnerships.partner_a.name" not in learning
    assert "engagement.consultation_1.summary" not in learning


# --------------------------------------------- remit-scoped, disclosure-complete caveats


@pytest.fixture(scope="module")
def walk_kb_citable(walk_facts) -> dict:
    """Real KB facts with gate1 set so reconciled facts are citable (post-Gate-1 state)."""
    return {"facts": dict(walk_facts), "gap_answers": {}, "gate1_confirmed_at": GATE1_TS}


def test_project_story_never_disclaims_finance(walk_kb_citable, sections_by_key):
    """The self-contradiction fix: an empty-financial-remit section discloses no finance."""
    names = owned_absent_requirements(sections_by_key["project_story"], walk_kb_citable)
    joined = " ".join(names).lower()
    for forbidden in ("budget", "spend", "financial", "cost"):
        assert forbidden not in joined
    disclosure = build_owned_absent_disclosure(sections_by_key["project_story"], walk_kb_citable)
    if disclosure:
        low = disclosure.lower()
        for forbidden in ("budget", "spend", "financial"):
            assert forbidden not in low


def test_present_budget_is_suppressed(walk_kb_citable, sections_by_key):
    """Present-elsewhere suppression: budget facts present -> fewer spend disclosures."""
    with_budget = owned_absent_requirements(sections_by_key["spend_summary"], walk_kb_citable)
    kb_without = {
        "facts": {
            k: v for k, v in walk_kb_citable["facts"].items() if not k.startswith("financials.")
        },
        "gap_answers": {},
        "gate1_confirmed_at": GATE1_TS,
    }
    without_budget = owned_absent_requirements(sections_by_key["spend_summary"], kb_without)
    assert len(without_budget) > len(with_budget)


def test_genuinely_absent_owned_item_is_disclosed_in_output(walk_kb_citable, sections_by_key):
    """Disclosure-completeness: a genuinely-absent OWNED item is disclosed by its owner."""
    # community_involvement requires partner/collaboration examples; KB has no
    # partnerships.* facts -> genuinely absent -> must be disclosed in this section's output.
    disclosure = build_owned_absent_disclosure(
        sections_by_key["community_involvement"], walk_kb_citable
    )
    assert disclosure is not None
    assert disclosure.strip() != ""


def test_disclosure_completeness_union_no_orphan(nlcf_sections, sections_by_key):
    """With an empty KB every non-section required item is genuinely absent; each such
    section must disclose (no real gap orphaned by remit-scoping)."""
    from app.reports.gap.template_requirements import enumerate_template_requirements

    empty_kb = {"facts": {}, "gap_answers": {}, "gate1_confirmed_at": GATE1_TS}
    ctx = {"report_type": "annual"}
    for section in nlcf_sections:
        reqs = [
            r
            for r in enumerate_template_requirements([section], report_context=ctx)
            if r.required_item_type != "section"
        ]
        if not reqs:
            continue
        names = owned_absent_requirements(section, empty_kb)
        assert names, f"{section['section_key']} orphaned its absent required items"


def test_no_section_discloses_another_sections_item(nlcf_sections, sections_by_key):
    """Owner-only emission: a section discloses only items it owns."""
    from app.reports.gap.template_requirements import enumerate_template_requirements

    empty_kb = {"facts": {}, "gap_answers": {}, "gate1_confirmed_at": GATE1_TS}
    ctx = {"report_type": "annual"}
    for section in nlcf_sections:
        section_key = section["section_key"]
        own_refs = {
            r.required_item_ref
            for r in enumerate_template_requirements([section], report_context=ctx)
            if r.required_item_type != "section"
        }
        # Disclosures are derived only from this section's own requirements by construction;
        # assert the humanised names map back to this section's own refs (no foreign items).
        from app.reports.services.ngo_text_redaction import humanize_identifier

        own_names = {humanize_identifier(ref) for ref in own_refs}
        for name in owned_absent_requirements(section, empty_kb):
            assert name in own_names, f"{section_key} disclosed foreign item {name!r}"
