"""Unit tests for F2 report fact-safety service."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

import pytest

from app.reports.models.donor_report import DonorReport
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.schemas.content_json_v1 import build_generated_section, assemble_content_json
from app.reports.services.report_fact_safety_service import critique_and_persist
from tests.orchestrator_mocks import fcdo_critic_query_fn
from tests.test_gap_compliance_agent import _build_incomplete_fcdo_kb
from tests.worker_validation_seed import create_worker_validation_sessionmaker


@pytest.fixture
def critic_db():
    return create_worker_validation_sessionmaker()


def _seed_report_with_content(session) -> uuid.UUID:
    from app.models.user import User

    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=f"critic-test-{uuid.uuid4().hex[:8]}@example.org",
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
    kb["gate2_confirmed_at"] = now.isoformat()
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=user.id,
        funder_report_template_id=template.id,
        reporting_period_start=date(2024, 10, 15),
        reporting_period_end=date(2025, 10, 14),
        status="DRAFT",
        knowledge_bank_json=kb,
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json=assemble_content_json(
            [
                build_generated_section(
                    section_key="summary_and_overview",
                    label="Summary",
                    archetype=None,
                    text="684 girls were re-enrolled during the period.",
                    assumptions=[],
                    evidence_used=["fact:indicators.OP1.1.actual"],
                    word_limit=900,
                    word_limit_respected=True,
                )
            ],
            warnings=[],
        ),
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add_all([user, template, report])
    session.commit()
    return report.id


def test_clean_section_gets_zero_flags(critic_db):
    session = critic_db()
    report_id = _seed_report_with_content(session)
    session.close()

    result = asyncio.run(
        critique_and_persist(
            critic_db(),
            report_id,
            query_fn_critic=fcdo_critic_query_fn(),
        )
    )
    assert result.verified == 1
    assert result.flagged == 0
    assert result.critic_blocks == 0

    after = critic_db()
    report = after.get(DonorReport, report_id)
    after.close()
    section = report.content_json["sections"][0]
    assert section["critic_flags"] == []
    assert section["generation_status"] == "GENERATED"


def test_planted_unsupported_specific_persists_flag(critic_db):
    session = critic_db()
    report_id = _seed_report_with_content(session)
    report = session.get(DonorReport, report_id)
    report.content_json["sections"][0]["content"]["text"] = (
        "The programme reported 99999 girls re-enrolled."
    )
    session.add(report)
    session.commit()
    session.close()

    result = asyncio.run(
        critique_and_persist(
            critic_db(),
            report_id,
            query_fn_critic=fcdo_critic_query_fn(plant_unsupported="summary_and_overview"),
        )
    )
    assert result.flagged == 1
    assert result.critic_blocks == 1

    after = critic_db()
    report = after.get(DonorReport, report_id)
    after.close()
    section = report.content_json["sections"][0]
    assert section["generation_status"] == "AWAITING_REVIEW"
    assert len(section["critic_flags"]) == 1
    flag = section["critic_flags"][0]
    assert flag["claim_text"] == "99999"
    assert flag["severity"] == "BLOCK"
    assert flag["accepted"] is False


def test_critic_error_marks_section_unverified(critic_db):
    session = critic_db()
    report_id = _seed_report_with_content(session)
    session.close()

    result = asyncio.run(
        critique_and_persist(
            critic_db(),
            report_id,
            query_fn_critic=fcdo_critic_query_fn(fail_section_key="summary_and_overview"),
        )
    )
    assert result.unverified == 1

    after = critic_db()
    report = after.get(DonorReport, report_id)
    after.close()
    section = report.content_json["sections"][0]
    assert section["generation_status"] == "AWAITING_REVIEW"
    assert section["critic_flags"][0]["claim_text"] == "[section unverified]"
    assert section["critic_flags"][0]["severity"] == "BLOCK"
