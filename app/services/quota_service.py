from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, InvalidActionTypeError
from app.models.usage_ledger import UsageActionType, UsageLedger
from app.models.user_plan import UserPlan

PLAN_FREE = "FREE"
PLAN_GROWTH = "GROWTH"
PLAN_IMPACT = "IMPACT"

EVENT_FIT_SCAN = "FIT_SCAN"
EVENT_PROPOSAL = UsageActionType.PROPOSAL_CREATE.value


@dataclass(frozen=True)
class PlanQuota:
    fit_scans: int
    proposals: int
    proposal_regenerations_per_proposal: int
    period_type: str


PLAN_QUOTAS: dict[str, PlanQuota] = {
    PLAN_FREE: PlanQuota(
        fit_scans=1,
        proposals=1,
        proposal_regenerations_per_proposal=0,
        period_type="LIFETIME",
    ),
    PLAN_GROWTH: PlanQuota(
        fit_scans=10,
        proposals=3,
        proposal_regenerations_per_proposal=3,
        period_type="BILLING_CYCLE",
    ),
    PLAN_IMPACT: PlanQuota(
        fit_scans=20,
        proposals=5,
        proposal_regenerations_per_proposal=3,
        period_type="BILLING_CYCLE",
    ),
}


def get_or_create_user_plan(
    db: Session,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
) -> UserPlan:
    plan = db.execute(select(UserPlan).where(UserPlan.user_id == user_id)).scalar_one_or_none()
    if plan:
        return plan
    plan = UserPlan(user_id=user_id, plan_name=PLAN_FREE)
    db.add(plan)
    if commit:
        db.commit()
        db.refresh(plan)
    else:
        db.flush()
        db.refresh(plan)
    return plan


def _ensure_paid_period(plan: UserPlan) -> None:
    if plan.plan_name == PLAN_FREE:
        return
    if plan.billing_period_start and plan.billing_period_end:
        return
    activated_at = plan.plan_activated_at
    if activated_at.tzinfo is None:
        activated_at = activated_at.replace(tzinfo=timezone.utc)
    else:
        activated_at = activated_at.astimezone(timezone.utc)
    plan.billing_period_start = activated_at
    plan.billing_period_end = activated_at + timedelta(days=30)


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


def _build_quota_payload(
    *, limit: int, used: int, period: str, reset_at: str | None
) -> dict[str, int | str | None]:
    remaining = max(limit - used, 0)
    return {
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "period": period,
        "reset_at": reset_at,
    }


def get_entitlements(db: Session, user_id: uuid.UUID) -> dict[str, object]:
    plan = get_or_create_user_plan(db, user_id)
    quota = PLAN_QUOTAS[plan.plan_name]
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE:
        db.commit()

    period_start = plan.billing_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.billing_period_end if plan.plan_name != PLAN_FREE else None
    reset_at = period_end.isoformat() if period_end else None

    fit_used = _usage_count(db, user_id, EVENT_FIT_SCAN, period_start, period_end)
    proposal_create_used = _usage_count(db, user_id, EVENT_PROPOSAL, period_start, period_end)
    docx_export_used = _usage_count(
        db,
        user_id,
        UsageActionType.DOCX_EXPORT.value,
        period_start,
        period_end,
    )
    proposal_used = proposal_create_used + docx_export_used

    return {
        "plan": plan.plan_name,
        "entitlements": {
            "fit_scans": _build_quota_payload(
                limit=quota.fit_scans,
                used=fit_used,
                period=quota.period_type,
                reset_at=reset_at,
            ),
            "proposals": _build_quota_payload(
                limit=quota.proposals,
                used=proposal_used,
                period=quota.period_type,
                reset_at=reset_at,
            ),
            "proposal_regenerations": {
                "limit_per_proposal": quota.proposal_regenerations_per_proposal
            },
        },
    }


def enforce_quota(
    db: Session,
    user_id: uuid.UUID,
    event_type: str,
    *,
    commit: bool = True,
) -> None:
    plan = get_or_create_user_plan(db, user_id, commit=commit)
    quota = PLAN_QUOTAS[plan.plan_name]
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE and commit:
        db.commit()

    period_start = plan.billing_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.billing_period_end if plan.plan_name != PLAN_FREE else None

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
    commit: bool = True,
) -> UsageLedger:
    try:
        validated_action = UsageActionType(event_type)
    except ValueError as exc:
        valid_values = ", ".join(action.value for action in UsageActionType)
        raise InvalidActionTypeError(
            f"Invalid action_type '{event_type}'. "
            f"Valid values: {valid_values}."
        ) from exc

    event_type = validated_action.value
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

    plan = get_or_create_user_plan(db, user_id, commit=commit)
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE and commit:
        db.commit()

    period_start = plan.billing_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.billing_period_end if plan.plan_name != PLAN_FREE else None
    quota = PLAN_QUOTAS[plan.plan_name]
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

    ledger = UsageLedger(
        user_id=user_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        idempotency_key=idempotency_key,
    )
    db.add(ledger)
    return ledger
