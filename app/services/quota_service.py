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

EVENT_FIT_SCAN = UsageActionType.FIT_SCAN.value
EVENT_PROPOSAL = UsageActionType.PROPOSAL_CREATE.value
EVENT_REPORT_CREATE = UsageActionType.REPORT_CREATE.value
EVENT_REPORT_CREATE_REFUND = UsageActionType.REPORT_CREATE_REFUND.value
EVENT_REPORT_EXPORT = UsageActionType.REPORT_EXPORT.value

_QUOTA_ENFORCED_ACTIONS = frozenset(
    {
        EVENT_FIT_SCAN,
        EVENT_PROPOSAL,
        UsageActionType.DOCX_EXPORT.value,
        EVENT_REPORT_CREATE,
    }
)

_IDEMPOTENCY_ONLY_ACTIONS = frozenset(
    {
        EVENT_REPORT_EXPORT,
        EVENT_REPORT_CREATE_REFUND,
        UsageActionType.PROPOSAL_REGEN.value,
    }
)


@dataclass(frozen=True)
class PlanQuota:
    fit_scans: int
    proposals: int
    reports: int
    proposal_regenerations_per_proposal: int
    period_type: str


PLAN_QUOTAS: dict[str, PlanQuota] = {
    PLAN_FREE: PlanQuota(
        fit_scans=1,
        proposals=1,
        reports=0,
        proposal_regenerations_per_proposal=0,
        period_type="LIFETIME",
    ),
    PLAN_GROWTH: PlanQuota(
        fit_scans=10,
        proposals=3,
        reports=0,
        proposal_regenerations_per_proposal=3,
        period_type="BILLING_CYCLE",
    ),
    PLAN_IMPACT: PlanQuota(
        fit_scans=10,
        proposals=5,
        reports=2,
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
    plan = UserPlan(id=uuid.uuid4(), user_id=user_id, plan_name=PLAN_FREE)
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

    activated_at = plan.plan_activated_at or datetime.now(timezone.utc)
    if plan.plan_activated_at is None:
        plan.plan_activated_at = activated_at
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


def _report_create_net_used(
    db: Session,
    user_id: uuid.UUID,
    period_start: datetime | None,
    period_end: datetime | None,
) -> int:
    created = _usage_count(db, user_id, EVENT_REPORT_CREATE, period_start, period_end)
    refunded = _usage_count(
        db, user_id, EVENT_REPORT_CREATE_REFUND, period_start, period_end
    )
    return max(created - refunded, 0)


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


def _quota_limit_for_action(event_type: str, quota: PlanQuota) -> int:
    if event_type == EVENT_FIT_SCAN:
        return quota.fit_scans
    if event_type in (EVENT_PROPOSAL, UsageActionType.DOCX_EXPORT.value):
        return quota.proposals
    if event_type == EVENT_REPORT_CREATE:
        return quota.reports
    raise ValueError(f"No quota limit mapping for action_type {event_type!r}")


def _reports_period_type(plan_name: str, quota: PlanQuota) -> str:
    """Reports use BILLING_CYCLE on paid plans; FREE uses LIFETIME with limit 0."""
    if plan_name == PLAN_FREE:
        return quota.period_type
    return "BILLING_CYCLE"


_REPORT_QUOTA_EXCEEDED_MESSAGE = (
    "You have used all M&E reports for this billing period."
)


def _report_quota_snapshot(
    db: Session,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
) -> dict[str, int | str | None]:
    plan = get_or_create_user_plan(db, user_id, commit=commit)
    quota = PLAN_QUOTAS[plan.plan_name]
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE and commit:
        db.commit()

    period_start = plan.billing_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.billing_period_end if plan.plan_name != PLAN_FREE else None
    reset_at = period_end.isoformat() if period_end else None
    reports_period = _reports_period_type(plan.plan_name, quota)
    used = _report_create_net_used(db, user_id, period_start, period_end)
    limit = quota.reports
    remaining = max(limit - used, 0)
    return {
        "entitlement": "reports",
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "period": reports_period,
        "reset_at": reset_at if plan.plan_name != PLAN_FREE else None,
    }


def _raise_report_quota_exceeded(snapshot: dict[str, int | str | None]) -> None:
    raise ForbiddenError(
        error_code="QUOTA_EXCEEDED",
        message=_REPORT_QUOTA_EXCEEDED_MESSAGE,
        status_code=403,
        details={
            "entitlement": snapshot["entitlement"],
            "limit": snapshot["limit"],
            "used": snapshot["used"],
            "remaining": 0,
            "period": snapshot["period"],
            "reset_at": snapshot["reset_at"],
        },
    )


def _lock_user_plan_row(db: Session, user_id: uuid.UUID) -> UserPlan | None:
    return db.execute(
        select(UserPlan).where(UserPlan.user_id == user_id).with_for_update()
    ).scalar_one_or_none()


def report_create_idempotency_key(donor_report_id: uuid.UUID) -> str:
    return f"report:create:{donor_report_id}"


def has_report_create_charge(
    db: Session,
    user_id: uuid.UUID,
    donor_report_id: uuid.UUID,
) -> bool:
    key = report_create_idempotency_key(donor_report_id)
    existing = db.execute(
        select(UsageLedger).where(
            UsageLedger.user_id == user_id,
            UsageLedger.event_type == EVENT_REPORT_CREATE,
            UsageLedger.idempotency_key == key,
        )
    ).scalar_one_or_none()
    return existing is not None


def charge_report_on_first_complete(
    db: Session,
    user_id: uuid.UUID,
    donor_report_id: uuid.UUID,
    *,
    commit: bool = True,
) -> UsageLedger:
    """Record REPORT_CREATE once when a report first reaches COMPLETE (D6)."""
    key = report_create_idempotency_key(donor_report_id)
    if not has_report_create_charge(db, user_id, donor_report_id):
        enforce_report_create_quota(db, user_id, commit=False, lock=True)
    return record_usage(
        db,
        user_id,
        EVENT_REPORT_CREATE,
        idempotency_key=key,
        commit=commit,
    )


def enforce_report_create_quota(
    db: Session,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
    lock: bool = False,
) -> None:
    if lock:
        _lock_user_plan_row(db, user_id)
    snapshot = _report_quota_snapshot(db, user_id, commit=commit)
    if int(snapshot["remaining"]) <= 0:
        _raise_report_quota_exceeded(snapshot)


def get_entitlements(db: Session, user_id: uuid.UUID) -> dict[str, object]:
    plan = get_or_create_user_plan(db, user_id)
    quota = PLAN_QUOTAS[plan.plan_name]
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE:
        db.commit()

    period_start = plan.billing_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.billing_period_end if plan.plan_name != PLAN_FREE else None
    reset_at = period_end.isoformat() if period_end else None
    reports_period = _reports_period_type(plan.plan_name, quota)

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
    report_create_used = _report_create_net_used(db, user_id, period_start, period_end)
    report_export_used = _usage_count(
        db, user_id, EVENT_REPORT_EXPORT, period_start, period_end
    )

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
            "reports": _build_quota_payload(
                limit=quota.reports,
                used=report_create_used,
                period=reports_period,
                reset_at=reset_at if plan.plan_name != PLAN_FREE else None,
            ),
            "report_exports": _build_quota_payload(
                limit=quota.reports,
                used=report_export_used,
                period=reports_period,
                reset_at=reset_at if plan.plan_name != PLAN_FREE else None,
            ),
        },
    }


def enforce_quota(
    db: Session,
    user_id: uuid.UUID,
    event_type: str,
    *,
    commit: bool = True,
) -> None:
    if event_type not in _QUOTA_ENFORCED_ACTIONS:
        return

    plan = get_or_create_user_plan(db, user_id, commit=commit)
    quota = PLAN_QUOTAS[plan.plan_name]
    _ensure_paid_period(plan)
    if plan.plan_name != PLAN_FREE and commit:
        db.commit()

    period_start = plan.billing_period_start if plan.plan_name != PLAN_FREE else None
    period_end = plan.billing_period_end if plan.plan_name != PLAN_FREE else None

    if event_type == EVENT_REPORT_CREATE:
        allowed = _quota_limit_for_action(event_type, quota)
        used = _report_create_net_used(db, user_id, period_start, period_end)
        remaining = allowed - used
    else:
        allowed = _quota_limit_for_action(event_type, quota)
        used = _usage_count(db, user_id, event_type, period_start, period_end)
        remaining = allowed - used
    if remaining <= 0:
        if event_type == EVENT_REPORT_CREATE:
            snapshot = _report_quota_snapshot(db, user_id, commit=False)
            _raise_report_quota_exceeded(snapshot)
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

    if event_type in _QUOTA_ENFORCED_ACTIONS:
        if event_type == EVENT_REPORT_CREATE:
            _lock_user_plan_row(db, user_id)
        plan = get_or_create_user_plan(db, user_id, commit=commit)
        quota = PLAN_QUOTAS[plan.plan_name]
        _ensure_paid_period(plan)
        if plan.plan_name != PLAN_FREE and commit:
            db.commit()

        period_start = plan.billing_period_start if plan.plan_name != PLAN_FREE else None
        period_end = plan.billing_period_end if plan.plan_name != PLAN_FREE else None
        allowed = _quota_limit_for_action(event_type, quota)
        used = _usage_count(db, user_id, event_type, period_start, period_end)
        remaining = allowed - used
        if remaining <= 0:
            if event_type == EVENT_REPORT_CREATE:
                snapshot = _report_quota_snapshot(db, user_id, commit=False)
                _raise_report_quota_exceeded(snapshot)
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
        id=uuid.uuid4(),
        user_id=user_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        idempotency_key=idempotency_key or f"{event_type}:{user_id}:{uuid.uuid4()}",
        metadata_json={},
    )
    db.add(ledger)
    return ledger


def release_report_create_quota(
    db: Session,
    user_id: uuid.UUID,
    donor_report_id: uuid.UUID,
    *,
    commit: bool = True,
) -> bool:
    """Legacy P8 reconciliation helper — not called from production paths after D6."""
    refund_key = f"report:refund:{donor_report_id}"
    existing_refund = db.execute(
        select(UsageLedger).where(
            UsageLedger.user_id == user_id,
            UsageLedger.event_type == EVENT_REPORT_CREATE_REFUND,
            UsageLedger.idempotency_key == refund_key,
        )
    ).scalar_one_or_none()
    if existing_refund is not None:
        return False

    create_key = f"report:create:{donor_report_id}"
    original_create = db.execute(
        select(UsageLedger).where(
            UsageLedger.user_id == user_id,
            UsageLedger.event_type == EVENT_REPORT_CREATE,
            UsageLedger.idempotency_key == create_key,
        )
    ).scalar_one_or_none()
    if original_create is None:
        return False

    ledger = UsageLedger(
        id=uuid.uuid4(),
        user_id=user_id,
        event_type=EVENT_REPORT_CREATE_REFUND,
        occurred_at=datetime.now(timezone.utc),
        idempotency_key=refund_key,
        metadata_json={"donor_report_id": str(donor_report_id)},
    )
    db.add(ledger)
    if commit:
        db.commit()
    return True
