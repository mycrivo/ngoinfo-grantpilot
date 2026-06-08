"""Report lifecycle entry routes — create, upload, enqueue, poll."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.reports.models.donor_report import DonorReport
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.schemas.report_lifecycle import (
    CreateDonorReportRequest,
    DonorReportSummaryResponse,
    EnqueueReportJobResponse,
    KnowledgeBankResponse,
    ReportJobStatusResponse,
    UploadedDocumentListResponse,
    UploadedDocumentResponse,
)
from app.reports.services.donor_report_lifecycle_service import (
    create_donor_report,
    delete_document,
    enqueue_report_job,
    get_knowledge_bank,
    get_report_job_status,
    list_documents,
    upload_document,
)

router = APIRouter(tags=["reports"])


def _report_summary(report: DonorReport) -> DonorReportSummaryResponse:
    template = report.funder_report_template
    return DonorReportSummaryResponse(
        id=report.id,
        funder_report_template_id=report.funder_report_template_id,
        funder_name=template.funder_name if template else "",
        template_name=template.template_name if template else "",
        linked_proposal_id=report.linked_proposal_id,
        reporting_period_start=report.reporting_period_start,
        reporting_period_end=report.reporting_period_end,
        status=report.status,
        version=report.version,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _document_response(document: UploadedDocument) -> UploadedDocumentResponse:
    return UploadedDocumentResponse(
        id=document.id,
        donor_report_id=document.donor_report_id,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        classification=document.classification,
        extraction_status=document.extraction_status,
        created_at=document.created_at,
    )


@router.post("/api/reports", response_model=DonorReportSummaryResponse)
def create_report(
    body: CreateDonorReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DonorReportSummaryResponse:
    report = create_donor_report(
        db,
        user_id=current_user.id,
        reporting_period_start=body.reporting_period_start,
        reporting_period_end=body.reporting_period_end,
        linked_proposal_id=body.linked_proposal_id,
        funder_report_template_id=body.funder_report_template_id,
    )
    db.refresh(report, attribute_names=["funder_report_template"])
    return _report_summary(report)


@router.post(
    "/api/reports/{donor_report_id}/documents",
    response_model=UploadedDocumentResponse,
)
async def upload_report_document(
    donor_report_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadedDocumentResponse:
    data = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload.bin"
    document = upload_document(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
        filename=filename,
        mime_type=mime_type,
        data=data,
    )
    return _document_response(document)


@router.get(
    "/api/reports/{donor_report_id}/documents",
    response_model=UploadedDocumentListResponse,
)
def list_report_documents(
    donor_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadedDocumentListResponse:
    documents = list_documents(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
    )
    return UploadedDocumentListResponse(
        documents=[_document_response(document) for document in documents]
    )


@router.delete(
    "/api/reports/{donor_report_id}/documents/{document_id}",
    status_code=204,
)
def delete_report_document(
    donor_report_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_document(
        db,
        donor_report_id=donor_report_id,
        document_id=document_id,
        user_id=current_user.id,
    )
    return Response(status_code=204)


@router.post(
    "/api/reports/{donor_report_id}/job",
    response_model=EnqueueReportJobResponse,
)
def start_report_job(
    donor_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnqueueReportJobResponse:
    job = enqueue_report_job(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
    )
    return EnqueueReportJobResponse(
        job_id=job.id,
        donor_report_id=job.donor_report_id,
        stage=job.stage,
        status=job.status,
    )


@router.get(
    "/api/reports/{donor_report_id}/job",
    response_model=ReportJobStatusResponse,
)
def read_report_job_status(
    donor_report_id: uuid.UUID,
    job_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportJobStatusResponse:
    job = get_report_job_status(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
        job_id=job_id,
    )
    return ReportJobStatusResponse(
        job_id=job.id,
        donor_report_id=job.donor_report_id,
        stage=job.stage,
        status=job.status,
        error=job.error,
        started_at=job.started_at,
        finished_at=job.finished_at,
        agent_trace_json=job.agent_trace_json or {},
    )


@router.get(
    "/api/reports/{donor_report_id}/knowledge-bank",
    response_model=KnowledgeBankResponse,
)
def read_knowledge_bank(
    donor_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBankResponse:
    payload = get_knowledge_bank(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
    )
    return KnowledgeBankResponse(**payload)
