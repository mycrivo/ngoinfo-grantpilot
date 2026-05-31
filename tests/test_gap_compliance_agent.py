from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.errors import DomainError
from app.reports.agents.gap_compliance_agent import (
    AGENT_NAME,
    DEFAULT_MODEL,
    build_gap_compliance_prompt,
    run_gap_compliance,
)
from app.reports.gap.satisfaction import unsatisfied_requirements
from app.reports.gap.template_requirements import enumerate_template_requirements
from app.reports.schemas.gap_compliance_v1 import envelope_to_gap_analysis_json
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
)
from app.reports.services.gap_compliance_service import run_gap_compliance_and_persist
from app.reports.services.gate_preconditions import require_gate1_confirmed
from app.reports.orchestration.dispatch import StageFailure
from tests.gap_grading import grade_gap_compliance

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "docs" / "artefacts" / "me_module"
NLCF_TEMPLATE = TEMPLATES / "TEMPLATE_INSTANCE_NLCF.json"
FCDO_TEMPLATE = TEMPLATES / "TEMPLATE_INSTANCE_FCDO.json"
KEYS = Path(__file__).resolve().parent / "fixtures" / "gap" / "keys"
FCDO_KB_RECORDED = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "reconciler"
    / "recorded"
    / "fcdo_bridgelight_recorded_knowledge_bank.json"
)

REPORT_CONTEXT = {"report_type": "annual"}
DOC_ID = "a1111111-1111-4111-8111-111111111101"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_key(name: str) -> dict:
    return _load_json(KEYS / name)


def _fact(fact_key: str, label: str, excerpt: str) -> dict:
    return {
        "value": excerpt[:80],
        "unit": None,
        "semantic_label": label,
        "coverage": "single_source",
        "source_document_id": DOC_ID,
        "source_label": "uploaded_doc",
        "provenance": {"excerpt": excerpt},
        "interpretation_note": None,
        "confirmed": True,
        "confirmed_at": None,
        "confirmed_by_user": True,
    }


def _confirmed_kb(*, facts: dict | None = None) -> dict:
    return {
        "schema_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "facts": facts or {},
        "conflicts": [],
        "unreadable_sources": [],
        "reconciliation_outcome": "complete",
        "gap_answers": {},
        "gate1_confirmed_at": "2026-05-24T12:00:00+00:00",
        "reconciliation_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "reconciler_agent": RECONCILER_AGENT_NAME,
        "reconciled_at": "2026-01-01T00:00:00+00:00",
    }


def _build_complete_nlcf_kb(template: dict) -> dict:
    facts: dict = {}
    for section in template["report_sections_json"]:
        if not section.get("required", True):
            continue
        for indicator in section.get("required_indicators") or []:
            key = f"nlcf.{section['section_key']}.{indicator}"
            facts[key] = _fact(
                key,
                indicator.replace("_", " "),
                f"Evidence for {indicator} in {section['label']}.",
            )
        for table in section.get("required_tables") or []:
            if (table.get("min_rows") or 0) < 1:
                continue
            table_key = table["table_key"]
            key = f"nlcf.{section['section_key']}.table.{table_key}"
            facts[key] = _fact(
                key,
                table.get("label") or table_key,
                f"Table evidence for {table_key}.",
            )
    return _confirmed_kb(facts=facts)


def _build_incomplete_nlcf_kb() -> dict:
    return _confirmed_kb(
        facts={
            "nlcf.project_story.summary": _fact(
                "nlcf.project_story.summary",
                "project story",
                "We delivered community activities this year.",
            )
        }
    )


def _build_incomplete_fcdo_kb() -> dict:
    return _confirmed_kb(
        facts={
            "fcdo.summary.overall_progress": _fact(
                "fcdo.summary.overall_progress",
                "overall progress",
                "Programme is broadly on track.",
            )
        }
    )


def _build_complete_fcdo_kb(template: dict) -> dict:
    recorded = _load_json(FCDO_KB_RECORDED)
    recorded["gate1_confirmed_at"] = "2026-05-24T12:00:00+00:00"
    requirements = enumerate_template_requirements(
        template["report_sections_json"], report_context=REPORT_CONTEXT
    )
    still_missing = unsatisfied_requirements(requirements, recorded)
    for req in still_missing:
        recorded.setdefault("facts", {})[req.required_item_ref] = _fact(
            req.required_item_ref,
            req.required_item_ref.replace("_", " "),
            f"Supplemental evidence for {req.required_item_ref}.",
        )
    return recorded


def _mock_gap_response_from_key(answer_key: dict, template: dict) -> dict:
    sections = template["report_sections_json"]
    requirements = enumerate_template_requirements(
        sections, report_context=answer_key.get("report_context", REPORT_CONTEXT)
    )
    by_identity = {req.identity: req for req in requirements}
    gaps = []
    for item in answer_key.get("expected_missing") or []:
        identity = (
            item["section_key"],
            item["required_item_type"],
            item["required_item_ref"],
        )
        req = by_identity.get(identity)
        if req is None:
            continue
        gaps.append(
            {
                "item_key": req.item_key,
                "section_key": req.section_key,
                "section_label": req.section_label,
                "required_item_type": req.required_item_type,
                "required_item_ref": req.required_item_ref,
                "severity": "required",
                "question": (
                    f"Please provide {req.required_item_ref} for the "
                    f"\"{req.section_label}\" section."
                ),
                "rationale": "Not found in confirmed knowledge bank from allowed sources.",
            }
        )
    expected_count = len(answer_key.get("expected_missing") or [])
    total_checks = len([r for r in requirements if r.required_item_type != "section"])
    satisfied = total_checks - expected_count
    readiness = (
        100
        if expected_count == 0
        else max(0, int(round(100 * satisfied / max(total_checks, 1))))
    )
    return {"readiness_score": readiness, "gaps": gaps}


async def _mock_query_factory(payload: dict):
    async def _query(**kwargs):
        class _Msg:
            structured_output = payload
            is_error = False
            stop_reason = "end_turn"
            duration_ms = 1
            usage = None

        yield _Msg()

    return _query


@pytest.mark.parametrize(
    ("template_path", "kb_builder", "key_name"),
    [
        (NLCF_TEMPLATE, "_nlcf_incomplete", "nlcf_incomplete_answer_key.json"),
        (NLCF_TEMPLATE, "_nlcf_complete", "nlcf_complete_answer_key.json"),
        (FCDO_TEMPLATE, "_fcdo_incomplete", "fcdo_incomplete_answer_key.json"),
        (FCDO_TEMPLATE, "_fcdo_complete", "fcdo_complete_answer_key.json"),
    ],
)
@pytest.mark.asyncio
async def test_gap_compliance_grades_t2_fixtures(template_path, kb_builder, key_name):
    template = _load_json(template_path)
    key = _load_key(key_name)
    if kb_builder == "_nlcf_incomplete":
        kb = _build_incomplete_nlcf_kb()
    elif kb_builder == "_nlcf_complete":
        kb = _build_complete_nlcf_kb(template)
    elif kb_builder == "_fcdo_incomplete":
        kb = _build_incomplete_fcdo_kb()
    else:
        kb = _build_complete_fcdo_kb(template)

    mock_payload = _mock_gap_response_from_key(key, template)
    result = await run_gap_compliance(
        knowledge_bank_json=kb,
        template_payload=template,
        report_context=REPORT_CONTEXT,
        query_fn=await _mock_query_factory(mock_payload),
    )
    persisted = envelope_to_gap_analysis_json(result.envelope)
    errors = grade_gap_compliance(
        persisted,
        template_sections=template["report_sections_json"],
        knowledge_bank_json=kb,
        answer_key=key,
        report_context=REPORT_CONTEXT,
    )
    assert errors == [], f"grading errors: {errors}"


def test_same_agent_module_for_nlcf_and_fcdo():
    import inspect

    source = inspect.getsource(run_gap_compliance)
    assert "FCDO" not in source
    assert "NLCF" not in source
    assert "if funder" not in source.lower()


def test_default_model_is_strong_tier():
    assert DEFAULT_MODEL == "claude-sonnet-4-6"
    import app.reports.agents.gap_compliance_agent as mod

    assert "claude_agent_sdk" not in Path(mod.__file__).read_text(encoding="utf-8")


def test_require_gate1_confirmed_raises_409():
    kb = _build_incomplete_nlcf_kb()
    kb.pop("gate1_confirmed_at")
    with pytest.raises(DomainError) as exc_info:
        require_gate1_confirmed(kb)
    assert exc_info.value.error_code == "GATE1_NOT_CONFIRMED"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_service_refuses_unconfirmed_bank(monkeypatch):
    import app.reports.services.gap_compliance_service as svc

    db = MagicMock()
    report_id = uuid.uuid4()
    template_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.funder_report_template_id = template_id
            self.knowledge_bank_json = _build_incomplete_nlcf_kb()
            self.knowledge_bank_json.pop("gate1_confirmed_at")
            self.gap_analysis_json: dict = {}

    class Template:
        def __init__(self) -> None:
            self.funder_name = "Test"
            self.template_name = "Test"
            self.report_sections_json = []
            self.format_rules_json = {}
            self.terminology_map_json = {}

    report = Report()
    db.get.side_effect = lambda model, pk: report if pk == report_id else Template()

    with pytest.raises(DomainError) as exc_info:
        await run_gap_compliance_and_persist(db, report_id)
    assert exc_info.value.error_code == "GATE1_NOT_CONFIRMED"


@pytest.mark.asyncio
async def test_service_persists_gap_analysis(monkeypatch):
    import app.reports.services.gap_compliance_service as svc

    template = _load_json(NLCF_TEMPLATE)
    key = _load_key("nlcf_incomplete_answer_key.json")
    kb = _build_incomplete_nlcf_kb()
    mock_payload = _mock_gap_response_from_key(key, template)

    async def _stub(**kwargs):
        return await run_gap_compliance(
            query_fn=await _mock_query_factory(mock_payload),
            **{k: v for k, v in kwargs.items() if k != "query_fn"},
        )

    monkeypatch.setattr(svc, "run_gap_compliance", _stub)

    db = MagicMock()
    report_id = uuid.uuid4()
    template_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.funder_report_template_id = template_id
            self.knowledge_bank_json = kb
            self.gap_analysis_json: dict = {}

    class TemplateModel:
        funder_name = template["funder_name"]
        template_name = template["template_name"]
        report_sections_json = template["report_sections_json"]
        format_rules_json = template["format_rules_json"]
        terminology_map_json = template["terminology_map_json"]

    report = Report()
    db.get.side_effect = lambda model, pk: (
        report if pk == report_id else TemplateModel()
    )

    result = await run_gap_compliance_and_persist(db, report_id)
    assert report.gap_analysis_json.get("gap_agent") == AGENT_NAME
    assert report.gap_analysis_json.get("readiness_score") is not None
    assert isinstance(report.gap_analysis_json.get("gaps"), list)
    db.commit.assert_called_once()


def _dispatch_minimal_e3_inputs() -> tuple[dict, dict]:
    kb = {
        "schema_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "facts": {},
        "conflicts": [],
        "unreadable_sources": [],
        "gap_answers": {},
        "gate1_confirmed_at": "2026-05-24T12:00:00+00:00",
    }
    template_payload = {
        "funder_name": "Test Funder",
        "template_name": "Dispatch Test Template",
        "report_sections_json": [],
        "format_rules_json": {},
        "terminology_map_json": {},
    }
    return kb, template_payload


def _record_stage_failure_trace(job: SimpleNamespace, exc: StageFailure) -> None:
    """Mirror run_pipeline StageFailure trace persistence."""
    trace = dict(job.agent_trace_json or {})
    trace["failed_stage"] = exc.stage
    job.agent_trace_json = trace


def test_e3_dispatch_resolves_stop_and_timeout_to_stage_failure(monkeypatch):
    """E3 failures through dispatch_stage must become clean stage failures with trace."""
    import asyncio

    from app.reports.orchestration.dispatch import dispatch_stage

    kb, template_payload = _dispatch_minimal_e3_inputs()

    async def _error_query(*, prompt, options=None):
        _ = prompt
        _ = options
        yield SimpleNamespace(is_error=True, stop_reason="injected_stop")

    job = SimpleNamespace(agent_trace_json={})

    async def _run_stop_error():
        await dispatch_stage(
            run_gap_compliance(
                knowledge_bank_json=kb,
                template_payload=template_payload,
                query_fn=_error_query,
            ),
            stage="gap",
        )

    with pytest.raises(StageFailure) as stop_exc:
        asyncio.run(_run_stop_error())
    assert stop_exc.value.stage == "gap"
    assert "injected_stop" in stop_exc.value.message
    _record_stage_failure_trace(job, stop_exc.value)
    assert job.agent_trace_json["failed_stage"] == "gap"

    async def _slow_query(*, prompt, options=None):
        _ = prompt
        _ = options
        await asyncio.sleep(5)
        yield SimpleNamespace(is_error=False, structured_output={})

    monkeypatch.setattr(
        "app.reports.agents.gap_compliance_agent.TIMEOUT_SECONDS",
        0.05,
    )
    job_timeout = SimpleNamespace(agent_trace_json={})

    async def _run_timeout():
        await dispatch_stage(
            run_gap_compliance(
                knowledge_bank_json=kb,
                template_payload=template_payload,
                query_fn=_slow_query,
            ),
            stage="gap",
        )

    with pytest.raises(StageFailure) as timeout_exc:
        asyncio.run(_run_timeout())
    assert timeout_exc.value.stage == "gap"
    assert "timeout" in timeout_exc.value.message.lower()
    _record_stage_failure_trace(job_timeout, timeout_exc.value)
    assert job_timeout.agent_trace_json["failed_stage"] == "gap"
