from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.core.security import generate_opaque_token, hash_token
from app.models.auth_oauth_exchange_code import AuthOAuthExchangeCode
from app.models.user import User
from app.models.user_plan import UserPlan

PLAN_FREE = "FREE"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_or_create_user_for_google(
    db: Session,
    *,
    email: str,
    google_sub: str,
    full_name: str | None,
    avatar_url: str | None,
) -> User:
    normalized_email = normalize_email(email)
    user = db.execute(select(User).where(User.google_sub == google_sub)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user:
        if user.email != normalized_email:
            user.email = normalized_email
        user.full_name = full_name or user.full_name
        user.avatar_url = avatar_url or user.avatar_url
        user.auth_provider = "google"
        user.last_login_at = now
        return user

    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if user:
        if not user.google_sub:
            user.google_sub = google_sub
        if user.email != normalized_email:
            user.email = normalized_email
        user.full_name = full_name or user.full_name
        user.avatar_url = avatar_url or user.avatar_url
        user.auth_provider = "google"
        user.last_login_at = now
        return user

    user = User(
        email=normalized_email,
        full_name=full_name,
        avatar_url=avatar_url,
        google_sub=google_sub,
        auth_provider="google",
        last_login_at=now,
    )
    db.add(user)
    db.flush()
    return user


def get_or_create_user_for_magic_link(db: Session, *, email: str) -> User:
    normalized_email = normalize_email(email)
    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user:
        if user.email != normalized_email:
            user.email = normalized_email
        user.auth_provider = "email"
        user.last_login_at = now
        return user

    user = User(
        email=normalized_email,
        auth_provider="email",
        last_login_at=now,
    )
    db.add(user)
    db.flush()
    return user


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


def is_redirect_allowed(url: str) -> bool:
    settings = get_settings()
    allowlist = [item.strip() for item in settings.AUTH_ALLOWED_REDIRECT_URLS.split(",") if item.strip()]
    return url in allowlist


def create_oauth_exchange_code(
    db: Session, user_id: uuid.UUID, *, ttl_seconds: int = 60
) -> str:
    raw_code = generate_opaque_token(24)
    code_hash = hash_token(raw_code)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    record = AuthOAuthExchangeCode(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=expires_at,
    )
    db.add(record)
    return raw_code


def consume_oauth_exchange_code(
    db: Session, code: str
) -> AuthOAuthExchangeCode | None:
    code_hash = hash_token(code)
    record = db.execute(
        select(AuthOAuthExchangeCode).where(AuthOAuthExchangeCode.code_hash == code_hash)
    ).scalar_one_or_none()
    if not record:
        return None
    if record.consumed_at is not None:
        return None
    if record.expires_at.tzinfo is None:
        now = datetime.utcnow()
    else:
        now = datetime.now(timezone.utc)
    if record.expires_at <= now:
        return None
    record.consumed_at = now
    return record
