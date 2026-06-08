"""Create donor reports, upload documents, enqueue jobs, and read pipeline state."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.models.usage_ledger import UsageActionType
from app.services.quota_service import enforce_report_create_quota, record_usage
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import (
    DonorReportStatus,
    ExtractionStatus,
    ReportJobStage,
    ReportJobStatus,
)
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.services.document_storage_service import DocumentStorageService
from app.reports.services.gate_preconditions import require_gate1_confirmed
from app.reports.services.report_access import get_owned_donor_report
from app.reports.services.upload_format_validation import validate_upload_format

logger = logging.getLogger("reports.services.donor_report_lifecycle")

DEFAULT_FUNDER_NAME = "__default__"
DEFAULT_TEMPLATE_NAME = "__lifecycle_default__"
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024

_ACTIVE_JOB_STATUSES = frozenset(
    {
        ReportJobStatus.QUEUED.value,
        ReportJobStatus.RUNNING.value,
        ReportJobStatus.AWAITING_HUMAN.value,
    }
)


def is_system_funder_template(template: FunderReportTemplate) -> bool:
    return (
        template.funder_name == DEFAULT_FUNDER_NAME
        and template.template_name == DEFAULT_TEMPLATE_NAME
    )


def _resolve_funder_template(
    db: Session,
    *,
    funder_report_template_id: uuid.UUID,
) -> FunderReportTemplate:
    template = db.get(FunderReportTemplate, funder_report_template_id)
    if template is None or not template.is_active:
        raise NotFoundError(
            error_code="TEMPLATE_NOT_FOUND",
            message=f"Funder template {funder_report_template_id} not found",
            status_code=404,
        )
    if is_system_funder_template(template):
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="This funder template cannot be used to create a report.",
            status_code=422,
        )
    return template


def create_donor_report(
    db: Session,
    *,
    user_id: uuid.UUID,
    reporting_period_start,
    reporting_period_end,
    linked_proposal_id: uuid.UUID | None = None,
    funder_report_template_id: uuid.UUID,
) -> DonorReport:
    if reporting_period_end < reporting_period_start:
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="reporting_period_end must be on or after reporting_period_start",
            status_code=422,
        )

    template = _resolve_funder_template(
        db, funder_report_template_id=funder_report_template_id
    )
    enforce_report_create_quota(db, user_id, commit=False, lock=True)

    now = datetime.now(timezone.utc)
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=user_id,
        funder_report_template_id=template.id,
        linked_proposal_id=linked_proposal_id,
        reporting_period_start=reporting_period_start,
        reporting_period_end=reporting_period_end,
        status=DonorReportStatus.DRAFT.value,
        knowledge_bank_json={},
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    try:
        db.add(report)
        db.flush()
        record_usage(
            db,
            user_id,
            UsageActionType.REPORT_CREATE.value,
            idempotency_key=f"report:create:{report.id}",
            commit=False,
        )
        db.commit()
    except DomainError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(report)
    logger.info("donor_report_created id=%s user_id=%s", report.id, user_id)
    return report


def upload_document(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    mime_type: str,
    data: bytes,
    storage: DocumentStorageService | None = None,
) -> UploadedDocument:
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )

    if not filename.strip():
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="filename is required",
            status_code=422,
        )
    if not data:
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="file is empty",
            status_code=422,
        )
    if len(data) > _MAX_UPLOAD_BYTES:
        raise DomainError(
            error_code="FILE_TOO_LARGE",
            message=f"Upload exceeds {_MAX_UPLOAD_BYTES} bytes",
            status_code=413,
        )

    validate_upload_format(filename=filename, mime_type=mime_type)

    store = storage or DocumentStorageService()
    storage_ref = DocumentStorageService.build_storage_ref(
        user_id, report.id, filename
    )
    store.upload_bytes(storage_ref, data, mime_type)

    document = UploadedDocument(
        id=uuid.uuid4(),
        donor_report_id=report.id,
        user_id=user_id,
        storage_ref=storage_ref,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=len(data),
        classification=None,
        extracted_json={},
        extraction_status=ExtractionStatus.PENDING.value,
        created_at=datetime.now(timezone.utc),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    logger.info(
        "document_uploaded donor_report_id=%s document_id=%s bytes=%d",
        report.id,
        document.id,
        len(data),
    )
    return document


def _assert_documents_mutable(db: Session, *, donor_report_id: uuid.UUID) -> None:
    """Job-state guard for document delete — not gated on donor_reports.status (D5)."""
    active = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status.in_(_ACTIVE_JOB_STATUSES),
        )
        .first()
    )
    if active is not None:
        raise ConflictError(
            error_code="ACTIVE_JOB_EXISTS",
            message="Documents cannot be removed while a report job is in progress",
            status_code=409,
            details={"job_id": str(active.id), "status": active.status},
        )

    completed = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.DONE.value,
        )
        .first()
    )
    if completed is not None:
        raise ConflictError(
            error_code="REPORT_HAS_COMPLETED_RUN",
            message="Documents cannot be removed after a report run has completed",
            status_code=409,
            details={"job_id": str(completed.id), "status": completed.status},
        )


def list_documents(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[UploadedDocument]:
    get_owned_donor_report(db, donor_report_id=donor_report_id, user_id=user_id)
    return (
        db.query(UploadedDocument)
        .filter(UploadedDocument.donor_report_id == donor_report_id)
        .order_by(UploadedDocument.created_at.asc())
        .all()
    )


def delete_document(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    storage: DocumentStorageService | None = None,
) -> None:
    get_owned_donor_report(db, donor_report_id=donor_report_id, user_id=user_id)
    _assert_documents_mutable(db, donor_report_id=donor_report_id)

    document = (
        db.query(UploadedDocument)
        .filter(
            UploadedDocument.id == document_id,
            UploadedDocument.donor_report_id == donor_report_id,
        )
        .first()
    )
    if document is None:
        raise NotFoundError(
            error_code="DOCUMENT_NOT_FOUND",
            message=f"Document {document_id} not found",
            status_code=404,
        )

    store = storage or DocumentStorageService()
    store.delete_object(document.storage_ref)
    db.delete(document)
    db.commit()
    logger.info(
        "document_deleted donor_report_id=%s document_id=%s",
        donor_report_id,
        document_id,
    )


def _try_reclaim_failed_job(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    report: DonorReport,
) -> ReportJob | None:
    """Re-queue a failed job at its failed stage after Gate 1 confirm.

    Never touches running or awaiting_human jobs — caller must reject those first.
    """
    try:
        require_gate1_confirmed(report.knowledge_bank_json)
    except DomainError:
        return None

    failed_job = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.FAILED.value,
            ReportJob.stage == ReportJobStage.GAP.value,
        )
        .order_by(
            ReportJob.started_at.desc().nullslast(),
            ReportJob.id.desc(),
        )
        .first()
    )
    if failed_job is None:
        return None

    trace = dict(failed_job.agent_trace_json or {})
    trace.pop("failed_stage", None)
    trace.pop("failure", None)
    failed_job.agent_trace_json = trace
    failed_job.status = ReportJobStatus.QUEUED.value
    failed_job.error = None
    failed_job.finished_at = None
    db.add(failed_job)
    db.commit()
    db.refresh(failed_job)
    logger.info(
        "report_job_reclaimed donor_report_id=%s job_id=%s stage=%s",
        donor_report_id,
        failed_job.id,
        failed_job.stage,
    )
    return failed_job


def enqueue_report_job(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ReportJob:
    report = get_owned_donor_report(db, donor_report_id=donor_report_id, user_id=user_id)

    active = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status.in_(_ACTIVE_JOB_STATUSES),
        )
        .first()
    )
    if active is not None:
        raise ConflictError(
            error_code="ACTIVE_JOB_EXISTS",
            message="An active report job already exists for this donor report",
            status_code=409,
            details={"job_id": str(active.id), "status": active.status},
        )

    reclaimed = _try_reclaim_failed_job(
        db, donor_report_id=donor_report_id, report=report
    )
    if reclaimed is not None:
        return reclaimed

    job = ReportJob(
        id=uuid.uuid4(),
        donor_report_id=donor_report_id,
        stage=ReportJobStage.CLASSIFY.value,
        status=ReportJobStatus.QUEUED.value,
        agent_trace_json={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(
        "report_job_enqueued donor_report_id=%s job_id=%s",
        donor_report_id,
        job.id,
    )
    return job


def get_report_job_status(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    job_id: uuid.UUID | None = None,
) -> ReportJob:
    get_owned_donor_report(db, donor_report_id=donor_report_id, user_id=user_id)

    query = db.query(ReportJob).filter(ReportJob.donor_report_id == donor_report_id)
    if job_id is not None:
        job = query.filter(ReportJob.id == job_id).first()
    else:
        job = (
            query.filter(ReportJob.status.in_(_ACTIVE_JOB_STATUSES))
            .order_by(ReportJob.started_at.desc().nullslast())
            .first()
        )
        if job is None:
            job = query.order_by(ReportJob.started_at.desc().nullslast()).first()

    if job is None:
        raise NotFoundError(
            error_code="JOB_NOT_FOUND",
            message="No report job found for this donor report",
            status_code=404,
        )
    return job


def get_knowledge_bank(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    kb = dict(report.knowledge_bank_json or {})
    reconciled = bool(kb.get("reconciler_agent") or kb.get("reconciliation_outcome"))
    ready = reconciled and not kb.get("gate1_confirmed_at")
    return {
        "donor_report_id": report.id,
        "facts": kb.get("facts") or {},
        "conflicts": kb.get("conflicts") or [],
        "unreadable_sources": kb.get("unreadable_sources") or [],
        "reconciliation_outcome": kb.get("reconciliation_outcome"),
        "gate1_confirmed_at": kb.get("gate1_confirmed_at"),
        "ready_for_gate1": ready,
        "knowledge_bank_json": kb,
    }
