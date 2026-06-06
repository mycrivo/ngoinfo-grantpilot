"""Impact-plan gate for all authenticated M&E routes."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.errors import ForbiddenError
from app.db.session import get_db
from app.models.user import User
from app.models.user_plan import UserPlan
from app.services.quota_service import PLAN_IMPACT

_UPGRADE_REQUIRED_MESSAGE = "M&E reporting is available on the Impact plan."


def require_impact_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    plan = db.execute(
        select(UserPlan).where(UserPlan.user_id == current_user.id)
    ).scalar_one_or_none()
    if plan is None or plan.plan_name != PLAN_IMPACT:
        raise ForbiddenError(
            error_code="UPGRADE_REQUIRED",
            message=_UPGRADE_REQUIRED_MESSAGE,
            status_code=403,
            details={
                "required_plan": PLAN_IMPACT,
                "feature": "me_reports",
            },
        )
    return current_user
