from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError
from app.models.usage_ledger import UsageLedger
from app.models.user_plan import UserPlan

PLAN_FREE = "FREE"
PLAN_GROWTH = "GROWTH"
PLAN_IMPACT = "IMPACT"

EVENT_FIT_SCAN = "FIT_SCAN"
EVENT_PROPOSAL = "PROPOSAL"


@dataclass(frozen=True)
class PlanQuota:
    fit_scans: int
    proposals: int
    period_type: str


PLAN_QUOTAS: dict[str, PlanQuota] = {
    PLAN_FREE: PlanQuota(fit_scans=1, proposals=1, period_type="LIFETIME"),
    PLAN_GROWTH: PlanQuota(fit_scans=10, proposals=3, period_type="BILLING_CYCLE"),
    PLAN_IMPACT: PlanQuota(fit_scans=20, proposals=5, period_type="BILLING_CYCLE"),
}


def get_or_create_user_plan(db: Session, user_id: uuid.UUID) -> UserPlan:
    plan = db.execute(select(UserPlan).where(UserPlan.user_id == user_id)).scalar_one_or_none()
    if plan:
        return plan
    plan = UserPlan(user_id=user_id, plan_name=PLAN_FREE)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _ensure_paid_period(plan: UserPlan) -> None:
    if plan.plan_name == PLAN_FREE:
        return
    if plan.current_period_start and plan.current_period_end:
        return
    activated_at = plan.plan_activated_at
    if activated_at.tzinfo is None:
        activated_at = activated_at.replace(tzinfo=timezone.utc)
    else:
        activated_at = activated_at.astimezone(timezone.utc)
    plan.current_period_start = activated_at
    plan.current_period_end = activated_at + timedelta(days=30)


def _period_payload(plan: UserPlan) -> dict[str, str | None]:
    if plan.plan_name == PLAN_FREE:
        return {
            "type": "LIFETIME",
            "start_at": None,
            "end_at": None,
            "resets_at": None,
        }
    _ensure_paid_period(plan)
    start_at = plan.current_period_start
    end_at = plan.current_period_end
    return {
        "type": "BILLING_CYCLE",
        "start_at": start_at.isoformat() if start_at else None,
        "end_at": end_at.isoformat() if end_at else None,
        "resets_at": end_at.isoformat() if end_at else None,
    }


def _usage_count(
    db: Session,
    user_id: uuid.UUID,
    event_type: str,
    period_start: datetime | None,
    period_end: datetime | None,
) -> int:
    query = select(func.count()).select_from(UsageLedger).where(
        UsageLedger.user_id == user_id,
        UsageLedger.event_type == event_type,
    )
    if period_start:
        query = query.where(UsageLedger.occurred_at >= period_start)
    if period_end:
        query = query.where(UsageLedger.occurred_at < period_end)
    return int(db.execute(query).scalar_one())


def _build_quota_payload(allowed: int, used: int) -> dict[str, int]:
    remaining = max(allowed - used, 0)
    return {"allowed": allowed, "used": used, "remaining": remaining}


def get_entitlements(db: Session, user_id: uuid.UUID) -> dict[str, object]:
    plan = get_or_create_user_plan(db, user_id)
    quota = PLAN_QUOTAS[plan.plan_name]
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE:
        db.commit()

    period_start = plan.current_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.current_period_end if plan.plan_name != PLAN_FREE else None

    fit_used = _usage_count(db, user_id, EVENT_FIT_SCAN, period_start, period_end)
    proposal_used = _usage_count(db, user_id, EVENT_PROPOSAL, period_start, period_end)

    return {
        "plan": plan.plan_name,
        "period": _period_payload(plan),
        "quotas": {
            "fit_scans": _build_quota_payload(quota.fit_scans, fit_used),
            "proposals": _build_quota_payload(quota.proposals, proposal_used),
        },
    }


def enforce_quota(db: Session, user_id: uuid.UUID, event_type: str) -> None:
    plan = get_or_create_user_plan(db, user_id)
    quota = PLAN_QUOTAS[plan.plan_name]
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE:
        db.commit()

    period_start = plan.current_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.current_period_end if plan.plan_name != PLAN_FREE else None

    allowed = quota.fit_scans if event_type == EVENT_FIT_SCAN else quota.proposals
    used = _usage_count(db, user_id, event_type, period_start, period_end)
    remaining = allowed - used
    if remaining <= 0:
        raise ForbiddenError(
            error_code="QUOTA_EXCEEDED",
            message="Quota exhausted for this action.",
            status_code=403,
            details={
                "resource": event_type,
                "remaining": max(remaining, 0),
                "resets_at": period_end.isoformat() if period_end else None,
            },
        )


def record_usage(
    db: Session,
    user_id: uuid.UUID,
    event_type: str,
    *,
    idempotency_key: str | None = None,
) -> UsageLedger:
    if idempotency_key:
        existing = db.execute(
            select(UsageLedger).where(
                UsageLedger.user_id == user_id,
                UsageLedger.event_type == event_type,
                UsageLedger.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    plan = get_or_create_user_plan(db, user_id)
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE:
        db.commit()

    ledger = UsageLedger(
        user_id=user_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        period_start=plan.current_period_start if plan.plan_name != PLAN_FREE else None,
        period_end=plan.current_period_end if plan.plan_name != PLAN_FREE else None,
        idempotency_key=idempotency_key,
    )
    db.add(ledger)
    return ledger
