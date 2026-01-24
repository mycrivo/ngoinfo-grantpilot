import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import create_access_token, generate_opaque_token, hash_token
from app.db.session import get_db
from app.models.auth_magic_link_token import AuthMagicLinkToken
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.user import User

logger = logging.getLogger("auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])
rate_limiter = RateLimiter()
oauth_state_store: dict[str, datetime] = {}
AUTH_POST_LOGIN_REDIRECT_URL = "https://grantpilot.ngoinfo.org/auth/callback"
SMOKE_TEST_EMAIL = "smoke-test@grantpilot.local"


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkConsumeRequest(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


def error_response(
    request: Request, status_code: int, error_code: str, message: str, details: dict | None = None
) -> JSONResponse:
    payload: dict[str, Any] = {"error_code": error_code, "message": message}
    if details:
        payload["details"] = details
    request_id = request.headers.get("x-request-id")
    if request_id:
        payload["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=payload)


def _is_valid_email(value: str) -> bool:
    if "@" not in value:
        return False
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain


def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limit_enabled() -> bool:
    return get_settings().AUTH_RATE_LIMIT_ENABLED


def _enforce_rate_limit(request: Request, key: str, limit: int, window_seconds: int) -> bool:
    if not _rate_limit_enabled():
        return True
    allowed = rate_limiter.allow(key, limit, window_seconds)
    if not allowed:
        logger.info("auth_rate_limited")
    return allowed


def _log_test_mode_event(request: Request, outcome: str) -> None:
    request_id = request.headers.get("x-request-id") or "unknown"
    ip = _get_client_ip(request)
    logger.info("test_mode_mint outcome=%s request_id=%s ip=%s", outcome, request_id, ip)


def _log_auth_failure(
    request: Request, event: str, *, user_id: uuid.UUID | None = None, detail: str | None = None
) -> None:
    request_id = request.headers.get("x-request-id") or "unknown"
    ip = _get_client_ip(request)
    logger.info(
        "auth_failure event=%s request_id=%s ip=%s user_id=%s detail=%s",
        event,
        request_id,
        ip,
        str(user_id) if user_id else "unknown",
        detail or "none",
    )


def _issue_refresh_token(db: Session, user_id: uuid.UUID) -> tuple[str, uuid.UUID]:
    now = datetime.now(timezone.utc)
    settings = get_settings()
    expires_at = now + timedelta(days=settings.AUTH_REFRESH_TOKEN_TTL_DAYS)
    raw_token = generate_opaque_token()
    token_hash = hash_token(raw_token)
    token_id = uuid.uuid4()
    token_record = AuthRefreshToken(
        id=token_id,
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token_record)
    return raw_token, token_id


def _revoke_active_refresh_tokens(db: Session, user_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(AuthRefreshToken)
        .where(
            AuthRefreshToken.user_id == user_id,
            AuthRefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )


def _store_oauth_state(state: str) -> None:
    oauth_state_store[state] = datetime.now(timezone.utc) + timedelta(minutes=10)


def _consume_oauth_state(state: str) -> bool:
    expires_at = oauth_state_store.pop(state, None)
    return bool(expires_at and expires_at > datetime.now(timezone.utc))


@router.get("/google/start")
def google_oauth_start(request: Request) -> JSONResponse:
    ip = _get_client_ip(request)
    if not _enforce_rate_limit(request, f"google_start_ip:{ip}", 60, 3600):
        return error_response(request, 429, "RATE_LIMITED", "Too many requests")

    settings = get_settings()
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_REDIRECT_URI:
        return error_response(
            request, 500, "OAUTH_CONFIG_ERROR", "OAuth configuration error"
        )

    state = generate_opaque_token(24)
    _store_oauth_state(state)
    scopes = (
        request.query_params.get("scopes")
        or get_settings().GOOGLE_OAUTH_SCOPES
        or "openid,email,profile"
    )
    query = urlencode(
        {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": scopes,
            "state": state,
        }
    )
    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    return JSONResponse(
        status_code=200, content={"authorization_url": authorization_url, "state": state}
    )


@router.get("/google/callback")
def google_oauth_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    redirect = request.query_params.get("redirect") == "1"

    if not code:
        _log_auth_failure(request, "oauth_code_missing")
        return error_response(request, 400, "OAUTH_CODE_MISSING", "Missing OAuth code")
    if not state or not _consume_oauth_state(state):
        _log_auth_failure(request, "oauth_state_invalid")
        return error_response(request, 400, "OAUTH_STATE_INVALID", "Invalid OAuth state")

    settings = get_settings()
    try:
        token_resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
    except Exception:
        _log_auth_failure(request, "oauth_internal_error")
        return error_response(
            request, 500, "OAUTH_INTERNAL_ERROR", "OAuth internal error"
        )

    if token_resp.status_code != 200:
        _log_auth_failure(request, "oauth_exchange_failed")
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )

    access_token = token_resp.json().get("access_token")
    if not access_token:
        _log_auth_failure(request, "oauth_exchange_failed")
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )

    userinfo_resp = httpx.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10.0,
    )
    if userinfo_resp.status_code != 200:
        _log_auth_failure(request, "oauth_exchange_failed")
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )
    userinfo = userinfo_resp.json()
    email = (userinfo.get("email") or "").lower()
    google_sub = userinfo.get("sub")
    full_name = userinfo.get("name")
    avatar_url = userinfo.get("picture")

    if not email:
        _log_auth_failure(request, "oauth_exchange_failed")
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            google_sub=google_sub,
            auth_provider="google",
            last_login_at=now,
        )
        db.add(user)
    else:
        if not user.google_sub:
            user.google_sub = google_sub
        user.full_name = full_name or user.full_name
        user.avatar_url = avatar_url or user.avatar_url
        user.auth_provider = "google"
        user.last_login_at = now

    _revoke_active_refresh_tokens(db, user.id)
    refresh_token, _ = _issue_refresh_token(db, user.id)
    access_token, expires_in = create_access_token(str(user.id), user.email, "FREE")
    db.commit()

    logger.info("auth_success provider=google user_id=%s", user.id)

    if redirect:
        params = urlencode(
            {"access_token": access_token, "refresh_token": refresh_token, "expires_in": expires_in}
        )
        redirect_url = f"{AUTH_POST_LOGIN_REDIRECT_URL}?{params}"
        return RedirectResponse(url=redirect_url)

    return JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "plan": "FREE",
            },
        },
    )


@router.post("/magic-link/request")
def magic_link_request(
    payload: MagicLinkRequest, request: Request, db: Session = Depends(get_db)
) -> JSONResponse:
    if not _is_valid_email(payload.email):
        _log_auth_failure(request, "magic_link_invalid_email")
        return error_response(request, 422, "VALIDATION_ERROR", "Invalid email")
    email = payload.email.lower()
    ip = _get_client_ip(request)

    if not _enforce_rate_limit(request, f"magic_email:{email}", 5, 3600):
        return error_response(request, 429, "RATE_LIMITED", "Too many requests")
    if not _enforce_rate_limit(request, f"magic_ip:{ip}", 20, 3600):
        return error_response(request, 429, "RATE_LIMITED", "Too many requests")

    settings = get_settings()
    if settings.EMAIL_PROVIDER.lower() != "resend":
        _log_auth_failure(request, "magic_link_provider_error")
        return error_response(
            request, 500, "EMAIL_PROVIDER_ERROR", "Email provider error"
        )

    raw_token = generate_opaque_token(32)
    token_hash = hash_token(raw_token)
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.AUTH_MAGIC_LINK_TTL_MIN)
    token_record = AuthMagicLinkToken(
        email=email,
        token_hash=token_hash,
        requested_ip=ip,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at,
    )
    db.add(token_record)
    db.commit()

    try:
        email_resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.EMAIL_API_KEY}"},
            json={
                "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
                "to": [email],
                "subject": "Your GrantPilot login link",
                "text": f"Your login token: {raw_token}",
            },
            timeout=10.0,
        )
    except Exception:
        _log_auth_failure(request, "magic_link_provider_error")
        return error_response(
            request, 500, "EMAIL_PROVIDER_ERROR", "Email provider error"
        )
    if email_resp.status_code >= 400:
        _log_auth_failure(request, "magic_link_provider_error")
        return error_response(
            request, 500, "EMAIL_PROVIDER_ERROR", "Email provider error"
        )

    logger.info("magic_link_requested")
    return JSONResponse(status_code=200, content={"status": "sent"})


@router.post("/magic-link/consume")
def magic_link_consume(
    payload: MagicLinkConsumeRequest, request: Request, db: Session = Depends(get_db)
):
    ip = _get_client_ip(request)
    if not _enforce_rate_limit(request, f"magic_consume_ip:{ip}", 30, 3600):
        return error_response(request, 429, "RATE_LIMITED", "Too many requests")

    token_hash = hash_token(payload.token)
    token_record = db.execute(
        select(AuthMagicLinkToken).where(AuthMagicLinkToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if token_record is None:
        _log_auth_failure(request, "magic_link_token_invalid")
        return error_response(
            request, 400, "MAGIC_TOKEN_INVALID", "Invalid magic link token"
        )
    if token_record.consumed_at is not None:
        _log_auth_failure(request, "magic_link_token_used")
        return error_response(
            request, 409, "MAGIC_TOKEN_ALREADY_USED", "Magic link already used"
        )
    if token_record.expires_at <= datetime.now(timezone.utc):
        _log_auth_failure(request, "magic_link_token_expired")
        return error_response(
            request, 400, "MAGIC_TOKEN_EXPIRED", "Magic link token expired"
        )

    token_record.consumed_at = datetime.now(timezone.utc)
    email = token_record.email
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            email=email,
            auth_provider="email",
            last_login_at=now,
        )
        db.add(user)
    else:
        user.auth_provider = "email"
        user.last_login_at = now

    _revoke_active_refresh_tokens(db, user.id)
    refresh_token, _ = _issue_refresh_token(db, user.id)
    access_token, expires_in = create_access_token(str(user.id), user.email, "FREE")
    db.commit()

    logger.info("auth_success provider=magic_link user_id=%s", user.id)

    return JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "plan": "FREE",
            },
        },
    )


@router.post("/refresh")
def refresh_tokens(
    payload: RefreshRequest, request: Request, db: Session = Depends(get_db)
):
    token_hash = hash_token(payload.refresh_token)
    token_record = db.execute(
        select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    ip = _get_client_ip(request)
    if token_record is not None:
        if not _enforce_rate_limit(
            request, f"refresh_user:{token_record.user_id}", 120, 3600
        ):
            return error_response(request, 429, "RATE_LIMITED", "Too many requests")
    else:
        if not _enforce_rate_limit(request, f"refresh_ip:{ip}", 120, 3600):
            return error_response(request, 429, "RATE_LIMITED", "Too many requests")

    if token_record is None:
        _log_auth_failure(request, "refresh_token_invalid", detail="not_found")
        return error_response(
            request, 401, "REFRESH_TOKEN_INVALID", "Invalid refresh token"
        )
    if token_record.revoked_at is not None:
        _log_auth_failure(request, "refresh_token_revoked", user_id=token_record.user_id)
        return error_response(
            request, 401, "REFRESH_TOKEN_REVOKED", "Refresh token revoked"
        )
    if token_record.expires_at <= datetime.now(timezone.utc):
        _log_auth_failure(request, "refresh_token_expired", user_id=token_record.user_id)
        return error_response(
            request, 401, "REFRESH_TOKEN_EXPIRED", "Refresh token expired"
        )

    user = db.execute(select(User).where(User.id == token_record.user_id)).scalar_one()
    _revoke_active_refresh_tokens(db, user.id)
    new_refresh_token, new_token_id = _issue_refresh_token(db, user.id)
    token_record.revoked_at = datetime.now(timezone.utc)
    token_record.replaced_by_token_id = new_token_id
    access_token, expires_in = create_access_token(str(user.id), user.email, "FREE")
    db.commit()

    logger.info("auth_refreshed user_id=%s", user.id)

    return JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        },
    )


@router.post("/logout")
def logout(payload: LogoutRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)
    token_record = db.execute(
        select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if token_record is None or token_record.revoked_at is not None:
        _log_auth_failure(request, "logout_token_invalid")
        return error_response(
            request, 401, "REFRESH_TOKEN_INVALID", "Invalid refresh token"
        )
    if token_record.expires_at <= datetime.now(timezone.utc):
        _log_auth_failure(request, "logout_token_expired", user_id=token_record.user_id)
        return error_response(
            request, 401, "REFRESH_TOKEN_INVALID", "Invalid refresh token"
        )

    token_record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("auth_logout user_id=%s", token_record.user_id)
    return JSONResponse(status_code=200, content={"status": "logged_out"})


@router.post("/test-mode/mint")
def test_mode_mint(request: Request, db: Session = Depends(get_db)):
    """TODO: Remove test-mode mint endpoint post-launch."""
    settings = get_settings()
    if not settings.TEST_MODE:
        _log_test_mode_event(request, "disabled")
        return error_response(request, 404, "TEST_MODE_DISABLED", "Not found")

    secret = request.headers.get("x-test-mode-secret")
    if not secret or secret != settings.TEST_MODE_SECRET:
        _log_test_mode_event(request, "unauthorized")
        return error_response(request, 404, "TEST_MODE_DISABLED", "Not found")

    ip = _get_client_ip(request)
    if not _enforce_rate_limit(request, f"test_mode_ip:{ip}", 3, 3600):
        _log_test_mode_event(request, "rate_limited")
        return error_response(request, 429, "RATE_LIMITED", "Too many requests")

    user = db.execute(select(User).where(User.email == SMOKE_TEST_EMAIL)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            email=SMOKE_TEST_EMAIL,
            auth_provider="email",
            last_login_at=now,
        )
        db.add(user)
    else:
        user.last_login_at = now

    db.flush()
    if user.id is None:
        _log_test_mode_event(request, "user_id_missing")
        return error_response(request, 500, "TEST_MODE_ERROR", "Test mode mint failed")

    _revoke_active_refresh_tokens(db, user.id)
    refresh_token, _ = _issue_refresh_token(db, user.id)
    access_token, expires_in = create_access_token(str(user.id), user.email, "FREE")
    db.commit()

    _log_test_mode_event(request, "success")
    return JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "plan": "FREE",
            },
        },
    )
