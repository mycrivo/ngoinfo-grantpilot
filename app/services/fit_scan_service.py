from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.fit_scan_executor import FitScanExecutor, PROMPT_LIBRARY_VERSION
from app.core.errors import ConflictError, DomainError, ForbiddenError, NotFoundError
from app.models.fit_scan import FitScan
from app.models.funding_opportunity import FundingOpportunity
from app.models.ngo_profile import NGOProfile
from app.models.user_plan import UserPlan
from app.models.usage_ledger import UsageActionType
from app.services.fit_scan_prompt_inputs import build_fit_scan_prompt_inputs
from app.services.email_service import EmailService, frontend_base_url
from app.services.profile_service import get_completeness, get_profile
from app.services.quota_service import enforce_quota, record_usage

RECOMMENDATION_MAP = {
    "STRONG": "RECOMMENDED",
    "MODERATE": "APPLY_WITH_CAVEATS",
    "WEAK": "NOT_RECOMMENDED",
}

MISSING_PROFILE_FIELDS = [
    "organization_name",
    "country_of_registration",
    "mission_statement",
    "focus_sectors",
    "geographic_areas_of_work",
    "target_groups",
    "past_projects",
]
logger = logging.getLogger("fit_scan")
_email_service = EmailService()


class FitScanService:
    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.executor = FitScanExecutor()

    def run_fit_scan(self, *, user, funding_opportunity_id: uuid.UUID) -> FitScan:
        opportunity = self.db.get(FundingOpportunity, funding_opportunity_id)
        if not opportunity or not opportunity.is_active or opportunity.is_archived:
            raise NotFoundError(
                error_code="OPPORTUNITY_NOT_FOUND",
                message="Funding opportunity not found",
                status_code=404,
            )

        profile = self._load_profile_or_raise(user.id)
        status, _, missing_fields = get_completeness(self.db, user.id)
        if status != "COMPLETE":
            raise ConflictError(
                error_code="PROFILE_INCOMPLETE",
                message="Profile is incomplete",
                status_code=409,
                details={"missing_fields": missing_fields},
            )

        enforce_quota(self.db, user.id, UsageActionType.FIT_SCAN.value)

        prompt_inputs = build_fit_scan_prompt_inputs(profile, opportunity)
        result_json = self.executor.execute(
            prompt_inputs, feature="fit_scan", user_id=str(user.id)
        )

        fit_summary = result_json["fit_summary"]
        model_rating = fit_summary["overall_fit_rating"]
        subscores = fit_summary["subscores"]
        overall_recommendation = RECOMMENDATION_MAP.get(model_rating)
        if overall_recommendation is None:
            raise DomainError(
                error_code="FIT_SCAN_FAILED",
                message="Invalid model rating in Fit Scan output",
                status_code=500,
            )

        plan_at_time_of_scan = _get_plan_name(self.db, user.id)
        record_usage(
            self.db,
            user.id,
            UsageActionType.FIT_SCAN.value,
            idempotency_key=str(uuid.uuid4()),
        )

        fit_scan = FitScan(
            user_id=user.id,
            funding_opportunity_id=opportunity.id,
            plan_at_time_of_scan=plan_at_time_of_scan,
            prompt_version=PROMPT_LIBRARY_VERSION,
            model_rating=model_rating,
            overall_recommendation=overall_recommendation,
            subscores=subscores,
            result_json=result_json,
        )
        self.db.add(fit_scan)

        try:
            self.db.commit()
        except Exception as exc:  # pragma: no cover - DB-level failure
            self.db.rollback()
            raise DomainError(
                error_code="FIT_SCAN_FAILED",
                message="Failed to persist Fit Scan",
                status_code=500,
            ) from exc

        self.db.refresh(fit_scan)
        try:
            _email_service.send_fit_scan_ready(
                fit_scan_id=fit_scan.id,
                user_id=user.id,
                user_email=user.email,
                full_name=user.full_name,
                opportunity_title=opportunity.title,
                overall_fit_rating=fit_scan.overall_recommendation,
                fit_scan_link=f"{frontend_base_url()}/fit-scan/{fit_scan.id}",
                idempotency_key=f"{fit_scan.id}:result_ready",
            )
        except Exception:
            logger.exception("fit_scan_ready_email_failed fit_scan_id=%s", fit_scan.id)
        return fit_scan

    def get_fit_scan(self, *, user, fit_scan_id: uuid.UUID) -> FitScan:
        fit_scan = self.db.get(FitScan, fit_scan_id)
        if not fit_scan:
            raise NotFoundError(
                error_code="FIT_SCAN_NOT_FOUND",
                message="Fit Scan not found",
                status_code=404,
            )
        if str(fit_scan.user_id) != str(user.id):
            raise ForbiddenError(
                error_code="FORBIDDEN",
                message="Forbidden",
                status_code=403,
            )
        return fit_scan

    def list_fit_scans(self, *, user, limit: int) -> list[FitScan]:
        statement = (
            select(FitScan)
            .where(FitScan.user_id == user.id)
            .order_by(FitScan.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def _load_profile_or_raise(self, user_id: uuid.UUID) -> NGOProfile:
        try:
            return get_profile(self.db, user_id)
        except NotFoundError as exc:
            raise ConflictError(
                error_code="PROFILE_INCOMPLETE",
                message="Profile is incomplete",
                status_code=409,
                details={"missing_fields": MISSING_PROFILE_FIELDS},
            ) from exc


def _get_plan_name(db: Session, user_id: uuid.UUID) -> str:
    plan = db.execute(select(UserPlan).where(UserPlan.user_id == user_id)).scalar_one_or_none()
    return plan.plan_name if plan else "FREE"
