"""VALIDATION ONLY — NOT THE PRODUCTION ENQUEUE PATH.

Minimal seed helper for worker seam tests: inserts real FK rows plus one
queued ``report_jobs`` row so ``poll_once`` / ``claim_next_job`` can be exercised.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import User
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "TEXT"


def _register_sqlite_functions(dbapi_connection, _connection_record) -> None:
    dbapi_connection.create_function(
        "gen_random_uuid", 0, lambda: str(uuid.uuid4())
    )
    dbapi_connection.create_function(
        "now", 0, lambda: datetime.now(timezone.utc).isoformat()
    )


def create_worker_validation_sessionmaker():
    """In-memory SQLite with M&E tables needed for worker seam validation."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _register_sqlite_functions)

    tables = (
        User.__table__,
        FunderReportTemplate.__table__,
        DonorReport.__table__,
        UploadedDocument.__table__,
        ReportJob.__table__,
    )
    originals: dict[tuple[str, str], object] = {}
    for table in tables:
        for column in table.columns:
            originals[(table.name, column.name)] = column.server_default
            column.server_default = None

    for table in tables:
        table.create(engine)

    for table in tables:
        for column in table.columns:
            column.server_default = originals.get((table.name, column.name))

    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def seed_queued_report_job(
    session: Session,
    *,
    donor_report_id: uuid.UUID | None = None,
    stage: str = ReportJobStage.CLASSIFY.value,
) -> ReportJob:
    """Insert FK chain + one queued job. Reuses donor report when id supplied."""
    now = datetime.now(timezone.utc)

    if donor_report_id is not None:
        report = session.get(DonorReport, donor_report_id)
        if report is None:
            raise ValueError(f"donor_report_id {donor_report_id} not found")
    else:
        user = User(
            id=uuid.uuid4(),
            email=f"worker-test-{uuid.uuid4().hex[:8]}@example.org",
            auth_provider="email",
            created_at=now,
            updated_at=now,
        )
        template = FunderReportTemplate(
            id=uuid.uuid4(),
            funder_name="Validation Funder",
            template_name="Worker Test Template",
            region="uk",
            reporting_frequency="annual",
            report_sections_json=[],
            format_rules_json={},
            terminology_map_json={},
            docx_template_ref="validation/test.docx",
            is_active=True,
            version=1,
            created_at=now,
            updated_at=now,
        )
        report = DonorReport(
            id=uuid.uuid4(),
            user_id=user.id,
            funder_report_template_id=template.id,
            reporting_period_start=date(2025, 1, 1),
            reporting_period_end=date(2025, 12, 31),
            status="DRAFT",
            knowledge_bank_json={},
            gap_analysis_json={},
            indicator_actuals_json={},
            content_json={},
            version=1,
            created_at=now,
            updated_at=now,
        )
        session.add_all([user, template, report])

    job = ReportJob(
        id=uuid.uuid4(),
        donor_report_id=report.id,
        stage=stage,
        status=ReportJobStatus.QUEUED.value,
        agent_trace_json={},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def seed_uploaded_document(
    session: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    mime_type: str = "application/pdf",
    storage_ref: str | None = None,
) -> UploadedDocument:
    document = UploadedDocument(
        id=uuid.uuid4(),
        donor_report_id=donor_report_id,
        user_id=user_id,
        storage_ref=storage_ref or f"validation/{uuid.uuid4().hex}/{filename}",
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=1024,
        classification=None,
        extracted_json={},
        extraction_status="PENDING",
        created_at=datetime.now(timezone.utc),
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def seed_orchestrator_fixture(
    session: Session,
    *,
    documents: list[tuple[str, str]] | None = None,
    job_stage: str = ReportJobStage.CLASSIFY.value,
    job_status: str = ReportJobStatus.QUEUED.value,
) -> dict:
    """Seed report + job + uploaded documents for orchestrator validation."""
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=f"orch-test-{uuid.uuid4().hex[:8]}@example.org",
        auth_provider="email",
        created_at=now,
        updated_at=now,
    )
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name="Validation Funder",
        template_name="Orchestrator Test Template",
        region="uk",
        reporting_frequency="annual",
        report_sections_json=[],
        format_rules_json={},
        terminology_map_json={},
        docx_template_ref="validation/test.docx",
        is_active=True,
        version=1,
        created_at=now,
        updated_at=now,
    )
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=user.id,
        funder_report_template_id=template.id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        status="DRAFT",
        knowledge_bank_json={},
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add_all([user, template, report])
    session.flush()

    doc_specs = documents or [
        ("proposal.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("award_letter.pdf", "application/pdf"),
    ]
    uploaded = [
        seed_uploaded_document(
            session,
            donor_report_id=report.id,
            user_id=user.id,
            filename=name,
            mime_type=mime,
        )
        for name, mime in doc_specs
    ]

    job = ReportJob(
        id=uuid.uuid4(),
        donor_report_id=report.id,
        stage=job_stage,
        status=job_status,
        agent_trace_json={},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return {
        "user": user,
        "report": report,
        "job": job,
        "documents": uploaded,
    }
