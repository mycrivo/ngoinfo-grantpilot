"""M&E read routes — list reports, report detail, template catalogue."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.reports.schemas.report_read import (
    ReportDetailResponse,
    ReportListItemResponse,
    ReportListResponse,
    ReportTemplateItemResponse,
    ReportTemplateListResponse,
)
from app.reports.services.report_read_service import (
    get_user_report_detail,
    list_active_report_templates,
    list_user_reports,
    report_detail_payload,
    report_list_item_payload,
)

router = APIRouter(tags=["reports"])


@router.get("/api/reports", response_model=ReportListResponse)
def list_reports(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportListResponse:
    reports = list_user_reports(db, user_id=current_user.id, limit=limit)
    return ReportListResponse(
        reports=[
            ReportListItemResponse(**report_list_item_payload(report))
            for report in reports
        ]
    )


@router.get("/api/reports/{report_id}", response_model=ReportDetailResponse)
def get_report_detail(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetailResponse:
    report = get_user_report_detail(
        db, user_id=current_user.id, report_id=report_id
    )
    return ReportDetailResponse(**report_detail_payload(report))


@router.get("/api/report-templates", response_model=ReportTemplateListResponse)
def list_report_templates(
    region: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportTemplateListResponse:
    templates = list_active_report_templates(db, region=region)
    return ReportTemplateListResponse(
        report_templates=[
            ReportTemplateItemResponse(
                id=template.id,
                funder_name=template.funder_name,
                template_name=template.template_name,
                region=template.region,
                reporting_frequency=template.reporting_frequency,
                version=template.version,
            )
            for template in templates
        ]
    )
