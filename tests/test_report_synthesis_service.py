"""Unit tests for F1 report synthesis service."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.reports.models.donor_report import DonorReport
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.schemas.content_json_v1 import sections_by_key
from app.reports.services.report_synthesis_service import synthesise_and_persist
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
)
from tests.orchestrator_mocks import fcdo_synthesis_query_fn
from tests.test_gap_compliance_agent import _build_incomplete_fcdo_kb
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
