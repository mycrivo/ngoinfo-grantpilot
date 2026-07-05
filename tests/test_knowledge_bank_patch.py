"""Tests for PATCH /api/reports/{id}/knowledge-bank — Gate 1 fact-decision save."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import create_app
from app.models.user import User
from app.reports.knowledge.confirmed_kb import filter_citable_facts
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.schemas.knowledge_bank_patch import PatchKnowledgeBankRequest
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
    validate_gate1_confirm_payload,
)
from app.reports.services.donor_report_lifecycle_service import (
    create_donor_report,
    enqueue_report_job,
)
from app.reports.services.gate1_confirmation_service import confirm_gate1
from app.reports.services.knowledge_bank_patch_service import (
    OWNER_ATTESTED_SOURCE_ID,
    USER_PROVIDED_SOURCE_ID,
    apply_fact_patches,
    materialize_conflict_resolution,
    patch_knowledge_bank,
)
from app.reports.services.report_inputs_builder import build_knowledge_bank_inputs
from app.services.quota_service import PLAN_IMPACT
from tests.test_report_lifecycle_routes import _seed_template
from tests.worker_validation_seed import (
    create_worker_validation_sessionmaker,
    seed_user_plan,
)

get_settings.cache_clear()

OP11_FACT_KEY = "indicators.op1_1_girls_reenrolled.target"


def _settings(*, me_enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        CORS_ALLOWED_ORIGINS="http://localhost:3000",
        ME_MODULE_ENABLED=me_enabled,
    )


def _op11_conflict_kb(*, fact_value: str | int = "1200") -> dict:
    proposal_doc = str(uuid.uuid4())
    logframe_doc = str(uuid.uuid4())
    return {
        "schema_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "reconciliation_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "reconciler_agent": RECONCILER_AGENT_NAME,
        "reconciled_at": "2026-01-01T00:00:00+00:00",
        "facts": {
            OP11_FACT_KEY: {
                "value": fact_value,
                "unit": None,
                "semantic_label": "OP1.1 girls re-enrolled target",
                "coverage": "single_source",
                "verification_status": "reconciled",
                "source_document_id": proposal_doc,
                "source_label": "fcdo_bridgelight_proposal.md",
                "provenance": {"excerpt": "1,200 endline target"},
                "interpretation_note": None,
                "confirmed": False,
                "confirmed_at": None,
                "confirmed_by_user": False,
            }
        },
        "conflicts": [
            {
                "fact_key": OP11_FACT_KEY,
                "conflict_type": "VALUE_MISMATCH",
                "values": [
                    {
                        "value": "1200",
                        "unit": None,
                        "source_document_id": proposal_doc,
                        "source_label": "fcdo_bridgelight_proposal.md",
                        "provenance": {"excerpt": "1,200 endline target"},
                    },
                    {
                        "value": "650",
                        "unit": None,
                        "source_document_id": logframe_doc,
                        "source_label": "BridgeLight Logframe AR1 Export.xlsx",
                        "provenance": {"excerpt": "650", "cell_ref": "Sheet1!G10"},
                    },
                ],
                "annotation": "Proposal states 1,200; logframe records 650 as Year-1 milestone.",
                "resolved_value": None,
                "resolved_at": None,
            }
        ],
        "unreadable_sources": [],
        "reconciliation_outcome": "complete",
    }


@pytest.fixture
def patch_api():
    session_factory = create_worker_validation_sessionmaker()
    user_id = uuid.uuid4()
    db = session_factory()
    now = datetime.now(timezone.utc)
    db.add(
        User(
            id=user_id,
            email=f"kb-patch-{user_id.hex[:8]}@example.org",
            auth_provider="email",
            created_at=now,
            updated_at=now,
        )
    )
    seed_user_plan(db, user_id, plan_name=PLAN_IMPACT)
    template = _seed_template(db)
    template_id = template.id
    db.commit()
    db.close()

    app = create_app(_settings(me_enabled=True))

    def _override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    token, _ = create_access_token(str(user_id), "kb-patch@example.org", "free")
    client = TestClient(app)
    return SimpleNamespace(
        client=client,
        token=token,
        user_id=user_id,
        template_id=template_id,
        session_factory=session_factory,
        auth_header={"Authorization": f"Bearer {token}"},
    )


def _seed_report_with_kb(api, kb: dict) -> uuid.UUID:
    session = api.session_factory()
    report = create_donor_report(
        session,
        user_id=api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        funder_report_template_id=api.template_id,
    )
    report.knowledge_bank_json = kb
    session.add(report)
    session.commit()
    report_id = report.id
    session.close()
    return report_id


def test_resolve_op11_conflict_picks_650():
    kb = _op11_conflict_kb()
    materialize_conflict_resolution(
        kb,
        fact_key=OP11_FACT_KEY,
        resolved_value=650,
        resolved_at_iso="2026-06-08T12:00:00+00:00",
    )
    conflict = kb["conflicts"][0]
    fact = kb["facts"][OP11_FACT_KEY]
    assert conflict["resolved_value"] == 650
    assert conflict["resolved_at"] is not None
    assert fact["value"] == "650"
    assert fact["value"] != "1200"
    assert fact["source_label"] == "BridgeLight Logframe AR1 Export.xlsx"


def test_resolve_op11_conflict_picks_1200_symmetric():
    kb = _op11_conflict_kb(fact_value="650")
    materialize_conflict_resolution(
        kb,
        fact_key=OP11_FACT_KEY,
        resolved_value="1200",
        resolved_at_iso="2026-06-08T12:00:00+00:00",
    )
    fact = kb["facts"][OP11_FACT_KEY]
    assert fact["value"] == "1200"
    assert fact["value"] != "650"
    assert fact["source_label"] == "fcdo_bridgelight_proposal.md"


def test_resolve_custom_owner_attested():
    kb = _op11_conflict_kb()
    materialize_conflict_resolution(
        kb,
        fact_key=OP11_FACT_KEY,
        resolved_value="775",
        resolved_at_iso="2026-06-08T12:00:00+00:00",
    )
    fact = kb["facts"][OP11_FACT_KEY]
    assert fact["value"] == "775"
    assert fact["source_document_id"] == OWNER_ATTESTED_SOURCE_ID
    assert fact["confirmed_by_user"] is True
    assert "Owner-entered value at Gate 1" in fact["provenance"]["excerpt"]


def test_materialization_atomic_no_split_state():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json = _op11_conflict_kb()

    report = Report()

    import app.reports.services.knowledge_bank_patch_service as patch_mod

    def _get_owned(_db, *, donor_report_id, user_id):  # noqa: ARG001
        assert donor_report_id == report_id
        return report

    def _get_kb(_db, *, donor_report_id, user_id):  # noqa: ARG001
        return {
            "donor_report_id": report_id,
            "facts": report.knowledge_bank_json["facts"],
            "conflicts": report.knowledge_bank_json["conflicts"],
            "gate1_confirmed_at": None,
            "ready_for_gate1": True,
            "knowledge_bank_json": report.knowledge_bank_json,
        }

    original_owned = patch_mod.get_owned_donor_report
    original_kb = patch_mod.get_knowledge_bank
    patch_mod.get_owned_donor_report = _get_owned
    patch_mod.get_knowledge_bank = _get_kb
    try:
        patch_knowledge_bank(
            db,
            donor_report_id=report_id,
            user_id=user_id,
            body=PatchKnowledgeBankRequest(
                conflict_resolutions=[
                    {"fact_key": OP11_FACT_KEY, "resolved_value": 650}
                ]
            ),
        )
    finally:
        patch_mod.get_owned_donor_report = original_owned
        patch_mod.get_knowledge_bank = original_kb

    persisted = report.knowledge_bank_json
    conflict = persisted["conflicts"][0]
    fact = persisted["facts"][OP11_FACT_KEY]
    assert conflict["resolved_value"] == 650
    assert conflict["resolved_at"] is not None
    assert fact["value"] == "650"
    db.commit.assert_called_once()


def test_chosen_value_wins_synthesis_inputs():
    kb = _op11_conflict_kb()
    materialize_conflict_resolution(
        kb,
        fact_key=OP11_FACT_KEY,
        resolved_value=650,
        resolved_at_iso="2026-06-08T12:00:00+00:00",
    )
    kb["gate1_confirmed_at"] = "2026-06-08T12:01:00+00:00"
    citable = filter_citable_facts(kb)
    assert citable[OP11_FACT_KEY]["value"] == "650"
    inputs = build_knowledge_bank_inputs(kb)
    assert inputs["facts"][OP11_FACT_KEY]["value"] == "650"
    assert "1200" not in str(inputs["facts"][OP11_FACT_KEY]["value"])


def test_confirm_blocked_until_resolved():
    kb = _op11_conflict_kb()
    errors = validate_gate1_confirm_payload(kb)
    assert any("unresolved" in err for err in errors)

    materialize_conflict_resolution(
        kb,
        fact_key=OP11_FACT_KEY,
        resolved_value=650,
        resolved_at_iso="2026-06-08T12:00:00+00:00",
    )
    assert validate_gate1_confirm_payload(kb) == []


def test_confirm_succeeds_after_patch_service():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json = _op11_conflict_kb()

    report = Report()

    import app.reports.services.knowledge_bank_patch_service as patch_mod

    original_owned = patch_mod.get_owned_donor_report
    original_kb = patch_mod.get_knowledge_bank
    patch_mod.get_owned_donor_report = lambda *_a, **_k: report
    patch_mod.get_knowledge_bank = lambda *_a, **_k: {
        "donor_report_id": report_id,
        "facts": report.knowledge_bank_json["facts"],
        "conflicts": report.knowledge_bank_json["conflicts"],
        "gate1_confirmed_at": None,
        "ready_for_gate1": True,
        "knowledge_bank_json": report.knowledge_bank_json,
    }
    try:
        patch_knowledge_bank(
            db,
            donor_report_id=report_id,
            user_id=user_id,
            body=PatchKnowledgeBankRequest(
                conflict_resolutions=[{"fact_key": OP11_FACT_KEY, "resolved_value": 650}]
            ),
        )
    finally:
        patch_mod.get_owned_donor_report = original_owned
        patch_mod.get_knowledge_bank = original_kb

    db.get.return_value = report
    persisted, _ = confirm_gate1(
        db,
        donor_report_id=report_id,
        user_id=user_id,
        knowledge_bank_json=report.knowledge_bank_json,
    )
    assert persisted.get("gate1_confirmed_at")
    assert persisted["facts"][OP11_FACT_KEY]["value"] == "650"


def test_add_fact_persists_owner_shape():
    kb = _op11_conflict_kb()
    apply_fact_patches(
        kb,
        {"user_fact_123": {"value": "extra note", "confirmed": True}},
        patched_at_iso="2026-06-08T12:00:00+00:00",
    )
    fact = kb["facts"]["user_fact_123"]
    assert fact["value"] == "extra note"
    assert fact["source_document_id"] == USER_PROVIDED_SOURCE_ID
    assert fact["confirmed_by_user"] is True
    assert fact["provenance"]["excerpt"] == "User-provided fact"


def test_edit_fact_and_client_dedup():
    kb = _op11_conflict_kb()
    kb["facts"]["notes.summary"] = {
        "value": "old",
        "unit": None,
        "semantic_label": "Summary",
        "verification_status": "reconciled",
        "source_document_id": str(uuid.uuid4()),
        "source_label": "doc",
        "provenance": {"excerpt": "old"},
        "confirmed_by_user": False,
    }
    kb["facts"]["notes.duplicate_a"] = {
        "value": "100",
        "unit": None,
        "semantic_label": "Dup label",
        "verification_status": "reconciled",
        "source_document_id": str(uuid.uuid4()),
        "source_label": "doc_a",
        "provenance": {"excerpt": "100"},
        "confirmed_by_user": False,
    }
    kb["facts"]["notes.duplicate_b"] = {
        "value": "200",
        "unit": None,
        "semantic_label": "Dup label",
        "verification_status": "reconciled",
        "source_document_id": str(uuid.uuid4()),
        "source_label": "doc_b",
        "provenance": {"excerpt": "200"},
        "confirmed_by_user": False,
    }
    apply_fact_patches(
        kb,
        {
            "notes.summary": {"value": "updated", "confirmed": True},
            "notes.duplicate_a": {"value": "150", "confirmed": True},
            "notes.duplicate_b": {"value": "150", "confirmed": True},
        },
        patched_at_iso="2026-06-08T12:00:00+00:00",
    )
    assert kb["facts"]["notes.summary"]["value"] == "updated"
    assert kb["facts"]["notes.duplicate_a"]["value"] == "150"
    assert kb["facts"]["notes.duplicate_b"]["value"] == "150"


def test_patch_after_gate1_confirmed_409():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()
    kb = _op11_conflict_kb()
    kb["gate1_confirmed_at"] = "2026-06-08T12:00:00+00:00"

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json = kb

    import app.reports.services.knowledge_bank_patch_service as patch_mod
    from app.core.errors import DomainError

    original_owned = patch_mod.get_owned_donor_report
    patch_mod.get_owned_donor_report = lambda *_a, **_k: Report()
    try:
        with pytest.raises(DomainError) as exc_info:
            patch_knowledge_bank(
                db,
                donor_report_id=report_id,
                user_id=user_id,
                body=PatchKnowledgeBankRequest(
                    conflict_resolutions=[{"fact_key": OP11_FACT_KEY, "resolved_value": 650}]
                ),
            )
    finally:
        patch_mod.get_owned_donor_report = original_owned
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "GATE_NOT_SATISFIED"


def test_patch_rejects_confirm_gate1_flag():
    db = MagicMock()
    import app.reports.services.knowledge_bank_patch_service as patch_mod
    from app.core.errors import DomainError

    with pytest.raises(DomainError) as exc_info:
        patch_knowledge_bank(
            db,
            donor_report_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            body=PatchKnowledgeBankRequest(confirm_gate1=True),
        )
    assert exc_info.value.error_code == "USE_GATE1_CONFIRM_ENDPOINT"
    assert exc_info.value.status_code == 422


def test_patch_endpoint_auth():
    app = create_app(_settings(me_enabled=True))
    client = TestClient(app)
    report_id = uuid.uuid4()
    response = client.patch(
        f"/api/reports/{report_id}/knowledge-bank",
        json={"conflict_resolutions": [{"fact_key": OP11_FACT_KEY, "resolved_value": 650}]},
    )
    assert response.status_code == 401


def test_patch_endpoint_resolve_op11_integration(patch_api):
    kb = _op11_conflict_kb()
    report_id = _seed_report_with_kb(patch_api, kb)
    response = patch_api.client.patch(
        f"/api/reports/{report_id}/knowledge-bank",
        headers=patch_api.auth_header,
        json={
            "conflict_resolutions": [
                {"fact_key": OP11_FACT_KEY, "resolved_value": 650},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["facts"][OP11_FACT_KEY]["value"] == "650"
    conflict = body["conflicts"][0]
    assert conflict["resolved_value"] == 650
    assert conflict["resolved_at"] is not None

    session = patch_api.session_factory()
    from app.reports.models.donor_report import DonorReport

    report = session.get(DonorReport, report_id)
    assert report is not None
    persisted = report.knowledge_bank_json
    assert persisted["facts"][OP11_FACT_KEY]["value"] == "650"
    session.close()


def test_patch_add_fact_integration(patch_api):
    kb = _op11_conflict_kb()
    materialize_conflict_resolution(
        kb,
        fact_key=OP11_FACT_KEY,
        resolved_value=650,
        resolved_at_iso="2026-06-08T12:00:00+00:00",
    )
    report_id = _seed_report_with_kb(patch_api, kb)
    response = patch_api.client.patch(
        f"/api/reports/{report_id}/knowledge-bank",
        headers=patch_api.auth_header,
        json={
            "facts": {
                "user_fact_999": {"value": "manual entry", "confirmed": True},
            },
        },
    )
    assert response.status_code == 200
    fact = response.json()["facts"]["user_fact_999"]
    assert fact["source_document_id"] == USER_PROVIDED_SOURCE_ID
    assert fact["confirmed_by_user"] is True
