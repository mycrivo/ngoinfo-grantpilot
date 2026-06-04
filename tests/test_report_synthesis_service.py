"""Unit tests for F1 report synthesis service."""

from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.reports.models.donor_report import DonorReport
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.schemas.content_json_v1 import sections_by_key
from app.reports.services.report_synthesis_service import (
    DEFAULT_SYNTHESIS_MAX_CONCURRENCY,
    _generate_all_sections,
    get_synthesis_max_concurrency,
    synthesise_and_persist,
)
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
)
from tests.orchestrator_mocks import fcdo_synthesis_query_fn
from tests.test_gap_compliance_agent import _build_incomplete_fcdo_kb, _fact
from tests.worker_validation_seed import create_worker_validation_sessionmaker

FCDO_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "artefacts"
    / "me_module"
    / "TEMPLATE_INSTANCE_FCDO.json"
)


@pytest.fixture
def synthesis_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    return session_factory


def _apply_fcdo_template(session, report_id: uuid.UUID) -> None:
    fcdo = json.loads(FCDO_TEMPLATE_PATH.read_text(encoding="utf-8"))
    report = session.get(DonorReport, report_id)
    assert report is not None
    template = session.get(FunderReportTemplate, report.funder_report_template_id)
    assert template is not None
    template.funder_name = fcdo["funder_name"]
    template.template_name = fcdo["template_name"]
    template.report_sections_json = fcdo["report_sections_json"]
    template.format_rules_json = fcdo.get("format_rules_json", {})
    template.terminology_map_json = fcdo.get("terminology_map_json", {})
    session.add(template)
    session.commit()


def _seed_report_ready_for_synthesis(session) -> uuid.UUID:
    from app.models.user import User

    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=f"synth-test-{uuid.uuid4().hex[:8]}@example.org",
        auth_provider="email",
        created_at=now,
        updated_at=now,
    )
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name="FCDO",
        template_name="Annual Review",
        region="uk",
        reporting_frequency="annual",
        report_sections_json=[],
        format_rules_json={},
        terminology_map_json={},
        docx_template_ref="validation/fcdo.docx",
        is_active=True,
        version=1,
        created_at=now,
        updated_at=now,
    )
    kb = _build_incomplete_fcdo_kb()
    kb["schema_version"] = KNOWLEDGE_BANK_RECONCILIATION_VERSION
    kb["reconciler_agent"] = RECONCILER_AGENT_NAME
    kb["gate1_confirmed_at"] = "2026-05-24T12:00:00+00:00"
    kb["gate2_confirmed_at"] = "2026-05-25T12:00:00+00:00"
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=user.id,
        funder_report_template_id=template.id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        status="DRAFT",
        knowledge_bank_json=kb,
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add_all([user, template, report])
    session.commit()
    _apply_fcdo_template(session, report.id)
    return report.id


def test_synthesis_persists_all_fcdo_sections(synthesis_db):
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    session = synthesis_db()
    result = asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=fcdo_synthesis_query_fn(),
        )
    )
    report = session.get(DonorReport, report_id)
    session.close()

    assert result.section_count == 8
    assert result.generated == 8
    assert result.failed == 0
    assert report is not None
    sections = report.content_json.get("sections") or []
    assert len(sections) == 8
    by_key = sections_by_key(sections)
    assert "summary_and_overview" in by_key
    for section in sections:
        assert section.get("section_key")
        assert section.get("generation_status") == "GENERATED"
        evidence = section.get("content", {}).get("evidence_used") or []
        assert all(
            str(e).startswith("fact:") or str(e).startswith("gap:")
            for e in evidence
        )


def test_single_section_failure_degrades_others_persist(synthesis_db):
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    session = synthesis_db()
    result = asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=fcdo_synthesis_query_fn(
                fail_section_key="performance_and_conclusions"
            ),
        )
    )
    report = session.get(DonorReport, report_id)
    session.close()

    assert result.generated == 7
    assert result.failed == 1
    assert result.degraded is True
    by_key = sections_by_key(report.content_json.get("sections") or [])
    assert by_key["performance_and_conclusions"]["generation_status"] == "FAILED"
    assert by_key["summary_and_overview"]["generation_status"] == "GENERATED"


def test_idempotent_overwrite(synthesis_db):
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    mock = fcdo_synthesis_query_fn()
    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=mock)
    )
    first = session.get(DonorReport, report_id)
    first_text = sections_by_key(first.content_json["sections"])[
        "summary_and_overview"
    ]["content"]["text"]
    session.close()

    def _second_mock(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        payload = mock(section_key, system_prompt, user_prompt)
        payload["generated_content"]["text"] = f"UPDATED {section_key}"
        return payload

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=_second_mock)
    )
    second = session.get(DonorReport, report_id)
    session.close()

    sections = second.content_json.get("sections") or []
    assert len(sections) == 8
    assert len(sections_by_key(sections)) == 8
    updated = sections_by_key(sections)["summary_and_overview"]["content"]["text"]
    assert updated.startswith("UPDATED ")
    assert updated != first_text


def test_synthesis_hygiene_binds_evidence_and_strips_control_chars(synthesis_db):
    from sqlalchemy.orm.attributes import flag_modified

    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    report = session.get(DonorReport, report_id)
    kb = dict(report.knowledge_bank_json or {})
    facts = dict(kb.get("facts") or {})
    facts["indicators.op2_1.ar1_target"] = _fact(
        "indicators.op2_1.ar1_target", "latrine target", "24"
    )
    kb["facts"] = facts
    report.knowledge_bank_json = kb
    flag_modified(report, "knowledge_bank_json")
    session.add(report)
    session.commit()
    session.close()

    def _dirty_mock(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        _ = system_prompt
        _ = user_prompt
        return {
            "section_key": section_key,
            "generation_status": "GENERATED",
            "archetype": "ARCH_EXECUTIVE_REVIEW_SUMMARY",
            "generated_content": {
                "text": "Year\u0010 milestone delivery for section.",
                "assumptions": [],
                "evidence_used": [
                    "fact:indicators.op2_\u09e7.ar\u0967_target",
                    "fact:indicators.op4_0?ar?_target",
                    "fact:fcdo.summary.overall_progress",
                ],
            },
            "constraints_applied": {
                "word_limit": 900,
                "word_limit_respected": True,
            },
            "warnings": [],
        }

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=_dirty_mock,
        )
    )
    report = session.get(DonorReport, report_id)
    session.close()

    section = sections_by_key(report.content_json["sections"])["summary_and_overview"]
    content = section["content"]
    assert "\u0010" not in content["text"]
    assert content["text"] == "Year milestone delivery for section."
    assert "fact:indicators.op2_1.ar1_target" in content["evidence_used"]
    assert "fact:fcdo.summary.overall_progress" in content["evidence_used"]
    assert "fact:indicators.op4_0?ar?_target" not in content["evidence_used"]
    assert content["dropped_citations"] == ["fact:indicators.op4_0?ar?_target"]


def _synthesis_generated_payload(section_key: str) -> dict:
    return {
        "section_key": section_key,
        "generation_status": "GENERATED",
        "archetype": "ARCH_EXECUTIVE_REVIEW_SUMMARY",
        "generated_content": {
            "text": f"Generated text for {section_key}.",
            "assumptions": [],
            "evidence_used": [],
        },
        "constraints_applied": {"word_limit": 100, "word_limit_respected": True},
        "warnings": [],
    }


def _eight_test_sections() -> list[dict]:
    return [
        {
            "section_key": f"section_{index}",
            "label": f"Section {index}",
            "word_limit": 100,
            "archetype": "ARCH_EXECUTIVE_REVIEW_SUMMARY",
        }
        for index in range(8)
    ]


def _run_generate_all_with_tracking(
    *,
    cap: int,
    section_count: int = 8,
) -> tuple[list[dict[str, Any]], int]:
    active = 0
    peak = 0
    lock = threading.Lock()

    def tracking_query(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        nonlocal active, peak
        _ = system_prompt
        _ = user_prompt
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.08)
        with lock:
            active -= 1
        return _synthesis_generated_payload(section_key)

    sections = _eight_test_sections()[:section_count]
    report = MagicMock(user_id=uuid.uuid4())
    template = MagicMock()
    db = MagicMock()
    kb_inputs = {"knowledge_bank": {"facts": {}, "gap_answers": {}}}

    with patch(
        "app.reports.services.report_synthesis_service.build_report_inputs_for_section",
        return_value=kb_inputs,
    ), patch(
        "app.reports.services.report_synthesis_service.get_synthesis_max_concurrency",
        return_value=cap,
    ):
        ordered, _ = _generate_all_sections(
            sections=sections,
            report=report,
            template=template,
            db=db,
            query_fn_synthesis=tracking_query,
        )
    return ordered, peak


def test_synthesis_max_concurrency_default_when_unset(monkeypatch):
    monkeypatch.delenv("ME_SYNTHESIS_MAX_CONCURRENCY", raising=False)
    get_settings.cache_clear()
    assert get_synthesis_max_concurrency() == DEFAULT_SYNTHESIS_MAX_CONCURRENCY
    assert DEFAULT_SYNTHESIS_MAX_CONCURRENCY == 2


def test_synthesis_max_concurrency_env_override(monkeypatch):
    monkeypatch.setenv("ME_SYNTHESIS_MAX_CONCURRENCY", "3")
    get_settings.cache_clear()
    assert get_synthesis_max_concurrency() == 3


def test_synthesis_concurrency_peak_never_exceeds_cap():
    ordered, peak = _run_generate_all_with_tracking(cap=2, section_count=8)
    assert len(ordered) == 8
    assert peak <= 2


def test_synthesis_all_sections_attempted_under_lower_concurrency():
    ordered, _ = _run_generate_all_with_tracking(cap=2, section_count=8)
    keys = [section["section_key"] for section in ordered]
    assert keys == [f"section_{index}" for index in range(8)]
    assert all(section.get("generation_status") == "GENERATED" for section in ordered)
