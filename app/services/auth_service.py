from __future__ import annotations

import uuid
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.user_plan import UserPlan

PLAN_FREE = "FREE"


def resolve_user_plan(db: Session, user_id: uuid.UUID) -> str:
    plan = db.execute(
        select(UserPlan.plan_name).where(UserPlan.user_id == user_id)
    ).scalar_one_or_none()
    return plan or PLAN_FREE


def issue_access_token(db: Session, user: User) -> tuple[str, int, str]:
    plan = resolve_user_plan(db, user.id)
    access_token, expires_in = create_access_token(str(user.id), user.email, plan)
    return access_token, expires_in, plan


def get_post_login_redirect_url() -> str:
    return get_settings().AUTH_POST_LOGIN_REDIRECT_URL


def build_magic_link_url(raw_token: str) -> str:
    post_login_url = get_post_login_redirect_url()
    parsed = urlparse(post_login_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return f"{base_url}/auth/magic-link?token={raw_token}"
