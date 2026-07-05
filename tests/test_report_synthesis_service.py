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
from app.reports.schemas.content_json_v1 import (
    merge_content_json_after_synthesis,
    section_needs_synthesis,
    sections_by_key,
)
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
from tests.test_gap_compliance_agent import _fact, _load_distilled_fcdo_kb
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
    kb = _load_distilled_fcdo_kb()
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

    assert result.section_count == 6
    assert result.generated == 6
    assert result.failed == 0
    assert report is not None
    assert report.status != "DEGRADED"
    sections = report.content_json.get("sections") or []
    assert len(sections) == 6
    by_key = sections_by_key(sections)
    assert "summary_and_overview" in by_key
    for section in sections:
        assert section.get("section_key")
        assert section.get("generation_status") == "GENERATED"
        content = section.get("content") or {}
        assert content.get("citation_mode") == "structured"
        evidence = content.get("evidence_used") or []
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

    assert result.generated == 5
    assert result.failed == 1
    assert result.degraded is True
    assert report.status == "DEGRADED"
    by_key = sections_by_key(report.content_json.get("sections") or [])
    assert by_key["performance_and_conclusions"]["generation_status"] == "FAILED"
    assert by_key["summary_and_overview"]["generation_status"] == "GENERATED"


def _tracking_query_fn(base_fn, called_keys: list[str]):
    def _query(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        called_keys.append(section_key)
        return base_fn(section_key, system_prompt, user_prompt)

    return _query


def _fail_sections_query_fn(base_fn, fail_keys: set[str]):
    def _query(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        if section_key in fail_keys:
            raise RuntimeError(f"simulated failure for {section_key}")
        return base_fn(section_key, system_prompt, user_prompt)

    return _query


def test_synthesis_resume_skips_already_generated(synthesis_db):
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    base = fcdo_synthesis_query_fn()
    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=base)
    )
    first = session.get(DonorReport, report_id)
    first_text = sections_by_key(first.content_json["sections"])[
        "summary_and_overview"
    ]["content"]["text"]
    session.close()

    called_keys: list[str] = []

    def _would_update(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        called_keys.append(section_key)
        payload = base(section_key, system_prompt, user_prompt)
        payload["generated_content"]["text"] = f"UPDATED {section_key}"
        return payload

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=_would_update)
    )
    second = session.get(DonorReport, report_id)
    session.close()

    assert called_keys == []
    unchanged = sections_by_key(second.content_json["sections"])[
        "summary_and_overview"
    ]["content"]["text"]
    assert unchanged == first_text
    assert not unchanged.startswith("UPDATED ")


def test_synthesis_resume_regenerates_only_failed_sections(synthesis_db):
    fail_keys = {"performance_and_conclusions"}
    base = fcdo_synthesis_query_fn()

    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=_fail_sections_query_fn(base, fail_keys),
        )
    )
    after_first = session.get(DonorReport, report_id)
    first_by_key = sections_by_key(after_first.content_json["sections"])
    preserved_texts = {
        key: first_by_key[key]["content"]["text"]
        for key in first_by_key
        if key not in fail_keys
    }
    assert after_first.status == "DEGRADED"
    session.close()

    called_keys: list[str] = []
    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=_tracking_query_fn(base, called_keys),
        )
    )
    after_second = session.get(DonorReport, report_id)
    second_by_key = sections_by_key(after_second.content_json["sections"])
    session.close()

    assert set(called_keys) == fail_keys
    assert len(second_by_key) == 6
    for key, text in preserved_texts.items():
        assert second_by_key[key]["content"]["text"] == text
    for key in fail_keys:
        assert second_by_key[key]["generation_status"] == "GENERATED"
    assert after_second.status != "DEGRADED"


def test_synthesis_never_regenerates_accepted_or_human_edited(synthesis_db):
    base = fcdo_synthesis_query_fn()
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=base)
    )
    report = session.get(DonorReport, report_id)
    sections = list(report.content_json["sections"])
    by_key = sections_by_key(sections)
    accepted = by_key["summary_and_overview"]
    accepted["generation_status"] = "ACCEPTED"
    accepted["content"]["text"] = "ACCEPTED LOCKED TEXT"
    accepted["critic_flags"] = [{"severity": "BLOCK", "accepted": True}]
    human = by_key["risk_and_safeguarding"]
    human["human_edited"] = True
    human["content"]["text"] = "HUMAN LOCKED TEXT"
    report.content_json = {"sections": sections}
    session.add(report)
    session.commit()
    session.close()

    called_keys: list[str] = []

    def _would_update(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        called_keys.append(section_key)
        payload = base(section_key, system_prompt, user_prompt)
        payload["generated_content"]["text"] = f"UPDATED {section_key}"
        return payload

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=_would_update)
    )
    report = session.get(DonorReport, report_id)
    by_key = sections_by_key(report.content_json["sections"])
    session.close()

    assert "summary_and_overview" not in called_keys
    assert "risk_and_safeguarding" not in called_keys
    assert by_key["summary_and_overview"]["content"]["text"] == "ACCEPTED LOCKED TEXT"
    assert by_key["summary_and_overview"]["generation_status"] == "ACCEPTED"
    assert by_key["risk_and_safeguarding"]["content"]["text"] == "HUMAN LOCKED TEXT"
    assert by_key["summary_and_overview"]["critic_flags"] == [
        {"severity": "BLOCK", "accepted": True}
    ]


def test_synthesis_merge_preserves_export_and_gate_stamps(synthesis_db):
    base = fcdo_synthesis_query_fn()
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=_fail_sections_query_fn(
                base, {"detailed_output_scoring"}
            ),
        )
    )
    report = session.get(DonorReport, report_id)
    report.content_json = {
        **report.content_json,
        "export": {"storage_ref": "users/x/reports/y/test.docx", "render_mode": "from_scratch"},
        "gate3_confirmed_at": "2026-06-04T12:00:00+00:00",
    }
    session.add(report)
    session.commit()
    session.close()

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=base)
    )
    report = session.get(DonorReport, report_id)
    session.close()

    assert report.content_json["export"]["storage_ref"] == "users/x/reports/y/test.docx"
    assert report.content_json["gate3_confirmed_at"] == "2026-06-04T12:00:00+00:00"


def test_section_needs_synthesis_rules():
    assert section_needs_synthesis(None) is True
    assert (
        section_needs_synthesis(
            {
                "generation_status": "GENERATED",
                "content": {"text": "prose"},
                "human_edited": False,
            }
        )
        is False
    )
    assert (
        section_needs_synthesis(
            {
                "generation_status": "FAILED",
                "content": {"text": ""},
                "human_edited": False,
            }
        )
        is True
    )
    assert (
        section_needs_synthesis(
            {
                "generation_status": "ACCEPTED",
                "content": {"text": ""},
                "human_edited": False,
            }
        )
        is False
    )
    assert (
        section_needs_synthesis(
            {
                "generation_status": "GENERATED",
                "content": {"text": "x"},
                "human_edited": True,
            }
        )
        is False
    )


def test_merge_content_json_preserves_siblings():
    merged = merge_content_json_after_synthesis(
        {
            "export": {"storage_ref": "keep-me"},
            "sections": [],
        },
        [{"section_key": "a", "generation_status": "GENERATED", "content": {"text": "t"}}],
        warnings=[],
    )
    assert merged["export"] == {"storage_ref": "keep-me"}
    assert merged["generation_summary"]["generated"] == 1


def test_degraded_status_cleared_on_full_completion(synthesis_db):
    base = fcdo_synthesis_query_fn()
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=_fail_sections_query_fn(base, {"performance_and_conclusions"}),
        )
    )
    report = session.get(DonorReport, report_id)
    assert report.status == "DEGRADED"
    session.close()

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=base)
    )
    report = session.get(DonorReport, report_id)
    session.close()

    assert report.status == "DRAFT"
    assert report.content_json["generation_summary"]["failed"] == 0


def test_synthesis_hygiene_binds_evidence_and_strips_control_chars(
    synthesis_db, monkeypatch
):
    monkeypatch.setenv("SYNTHESIS_CITATION_FALLBACK", "1")
    get_settings.cache_clear()
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
    assert "fact:fcdo.summary.overall_progress" not in content["evidence_used"]
    assert "fact:indicators.op4_0?ar?_target" not in content["evidence_used"]
    assert "fact:indicators.op4_0?ar?_target" in (content.get("dropped_citations") or [])
    get_settings.cache_clear()


def test_synthesis_structured_mode_persists_citation_mode(synthesis_db, monkeypatch):
    monkeypatch.delenv("SYNTHESIS_CITATION_FALLBACK", raising=False)
    get_settings.cache_clear()
    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    session = synthesis_db()
    asyncio.run(
        synthesise_and_persist(
            session,
            report_id,
            query_fn_synthesis=fcdo_synthesis_query_fn(),
        )
    )
    report = session.get(DonorReport, report_id)
    session.close()

    section = sections_by_key(report.content_json["sections"])["summary_and_overview"]
    content = section["content"]
    assert content.get("citation_mode") == "structured"
    assert content.get("structured_bind_status") == "bound"
    get_settings.cache_clear()


def _synthesis_generated_payload(section_key: str) -> dict:
    return {
        "section_key": section_key,
        "generation_status": "GENERATED",
        "archetype": "ARCH_EXECUTIVE_REVIEW_SUMMARY",
        "generated_content": {
            "claims": [],
            "text": f"Generated text for {section_key}.",
            "assumptions": [],
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
    report = MagicMock(
        user_id=uuid.uuid4(),
        knowledge_bank_json={
            "facts": {"indicators.op1_1.ar1_actual": {"value": "1", "verification_status": "reconciled"}},
            "gap_answers": {},
            "gate1_confirmed_at": "2026-05-24T12:00:00+00:00",
        },
    )
    template = MagicMock()
    db = MagicMock()
    kb_inputs = {"knowledge_bank": {"facts": {}, "gap_answers": {}}}

    with patch(
        "app.reports.services.report_synthesis_service.build_report_inputs_for_section",
        return_value=kb_inputs,
    ), patch(
        "app.reports.services.report_synthesis_service.get_synthesis_max_concurrency",
        return_value=cap,
    ), patch(
        "app.reports.services.report_synthesis_service.section_has_synthesizable_inputs",
        return_value=True,
    ):
        ordered, _, _, _, _ = _generate_all_sections(
            sections=sections,
            report=report,
            template=template,
            db=db,
            report_context={"report_type": "annual"},
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
