"""Gate 3 review routes — critique resume and section acceptance (P0-2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.reports.schemas.report_read import ReportDetailResponse
from app.reports.schemas.report_review import (
    PatchReportSectionRequest,
    ResumeCritiqueResponse,
)
from app.reports.services.critique_resume_service import resume_critique_for_report
from app.reports.services.report_read_service import report_detail_payload
from app.reports.services.report_section_review_service import (
    accept_all_sections_for_gate3,
    patch_report_section,
)

router = APIRouter(tags=["reports"])


@router.post(
    "/api/reports/{donor_report_id}/job/resume-critique",
    response_model=ResumeCritiqueResponse,
)
def resume_critique_route(
    donor_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeCritiqueResponse:
    job = resume_critique_for_report(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
    )
    return ResumeCritiqueResponse(
        job_id=job.id,
        donor_report_id=job.donor_report_id,
        stage=job.stage,
        status=job.status,
    )


@router.patch(
    "/api/reports/{donor_report_id}/sections/{section_key}",
    response_model=ReportDetailResponse,
)
def patch_report_section_route(
    donor_report_id: uuid.UUID,
    section_key: str,
    body: PatchReportSectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetailResponse:
    report = patch_report_section(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
        section_key=section_key,
        content_text=body.content_text,
        accept_critic_flags=body.accept_critic_flags,
        accept_section=body.accept_section,
    )
    return ReportDetailResponse(**report_detail_payload(report))


@router.post(
    "/api/reports/{donor_report_id}/sections/accept-all",
    response_model=ReportDetailResponse,
)
def accept_all_sections_route(
    donor_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetailResponse:
    report = accept_all_sections_for_gate3(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
    )
    return ReportDetailResponse(**report_detail_payload(report))
