"""Read-only M&E report and template queries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.reports.models.donor_report import DonorReport
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.services.report_access import get_owned_donor_report
from app.reports.services.report_gate_state import compute_current_gate


def list_user_reports(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[DonorReport]:
    statement = (
        select(DonorReport)
        .options(joinedload(DonorReport.funder_report_template))
        .where(DonorReport.user_id == user_id)
        .order_by(DonorReport.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(statement).scalars().unique().all())


def get_user_report_detail(
    db: Session,
    *,
    user_id: uuid.UUID,
    report_id: uuid.UUID,
) -> DonorReport:
    report = get_owned_donor_report(
        db, donor_report_id=report_id, user_id=user_id
    )
    db.refresh(report, attribute_names=["funder_report_template"])
    return report


def list_active_report_templates(
    db: Session,
    *,
    region: str | None = None,
) -> list[FunderReportTemplate]:
    query = select(FunderReportTemplate).where(
        FunderReportTemplate.is_active.is_(True)
    )
    if region:
        query = query.where(FunderReportTemplate.region == region)
    query = query.order_by(
        FunderReportTemplate.funder_name,
        FunderReportTemplate.template_name,
    )
    return list(db.execute(query).scalars().all())


def report_list_item_payload(report: DonorReport) -> dict:
    template = report.funder_report_template
    return {
        "id": report.id,
        "funder_name": template.funder_name if template else "",
        "template_name": template.template_name if template else "",
        "status": report.status,
        "reporting_period_start": report.reporting_period_start,
        "reporting_period_end": report.reporting_period_end,
        "current_gate": compute_current_gate(report),
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def report_detail_payload(report: DonorReport) -> dict:
    template = report.funder_report_template
    kb = report.knowledge_bank_json or {}
    return {
        "id": report.id,
        "funder_report_template_id": report.funder_report_template_id,
        "funder_name": template.funder_name if template else "",
        "template_name": template.template_name if template else "",
        "linked_proposal_id": report.linked_proposal_id,
        "reporting_period_start": report.reporting_period_start,
        "reporting_period_end": report.reporting_period_end,
        "status": report.status,
        "version": report.version,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "content_json": report.content_json or {},
        "knowledge_bank_json": kb,
        "gap_analysis_json": report.gap_analysis_json or {},
        "indicator_actuals_json": report.indicator_actuals_json or {},
        "current_gate": compute_current_gate(report),
        "gate3_confirmed_at": kb.get("gate3_confirmed_at"),
    }
