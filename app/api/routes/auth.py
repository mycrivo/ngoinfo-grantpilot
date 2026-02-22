import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from authlib.integrations.httpx_client import OAuth2Client
from authlib.oauth2.rfc7636 import create_s256_code_challenge
import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import generate_opaque_token, hash_token
from app.db.session import get_db
from app.models.auth_magic_link_token import AuthMagicLinkToken
from app.models.auth_oauth_exchange_code import AuthOAuthExchangeCode
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.user import User
from app.services.auth_service import (
    build_magic_link_url,
    consume_oauth_exchange_code,
    create_oauth_exchange_code,
    get_post_login_redirect_url,
    get_or_create_user_for_google,
    get_or_create_user_for_magic_link,
    issue_access_token,
    is_redirect_allowed,
    normalize_email,
)
from app.services.email_service import maybe_send_welcome_email, send_magic_link_email

logger = logging.getLogger("auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])
rate_limiter = RateLimiter()
oauth_state_store: dict[str, dict[str, Any]] = {}
SMOKE_TEST_EMAIL = "smoke-test@grantpilot.local"
OAUTH_EXCHANGE_REPLAY_WINDOW_SECONDS = 15


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkConsumeRequest(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class OAuthExchangeRequest(BaseModel):
    code: str


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


def _store_oauth_state(state: str, *, code_verifier: str) -> None:
    oauth_state_store[state] = {
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        "code_verifier": code_verifier,
    }


def _consume_oauth_state(state: str) -> dict[str, Any] | None:
    record = oauth_state_store.pop(state, None)
    if not record:
        return None
    expires_at = record.get("expires_at")
    if not expires_at or expires_at <= datetime.now(timezone.utc):
        return None
    return record


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _lookup_oauth_exchange_code(db: Session, raw_code: str) -> AuthOAuthExchangeCode | None:
    return db.execute(
        select(AuthOAuthExchangeCode).where(AuthOAuthExchangeCode.code_hash == hash_token(raw_code))
    ).scalar_one_or_none()


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
    scopes = (
        request.query_params.get("scopes")
        or get_settings().GOOGLE_OAUTH_SCOPES
        or "openid email profile"
    )
    code_verifier = generate_opaque_token(48)
    code_challenge = create_s256_code_challenge(code_verifier)
    client = OAuth2Client(
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scope=scopes,
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
    )
    authorization_url, returned_state = client.create_authorization_url(
        "https://accounts.google.com/o/oauth2/v2/auth",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    _store_oauth_state(returned_state, code_verifier=code_verifier)
    return JSONResponse(
        status_code=200, content={"authorization_url": authorization_url, "state": returned_state}
    )


@router.get("/google/callback")
def google_oauth_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    state_record = _consume_oauth_state(state) if state else None

    if not code:
        _log_auth_failure(request, "oauth_code_missing")
        return error_response(request, 400, "OAUTH_CODE_MISSING", "Missing OAuth code")
    if not state or not state_record:
        _log_auth_failure(request, "oauth_state_invalid")
        return error_response(request, 400, "OAUTH_STATE_INVALID", "Invalid OAuth state")

    settings = get_settings()
    code_verifier = state_record.get("code_verifier") if state_record else None
    if not code_verifier:
        _log_auth_failure(request, "oauth_state_invalid")
        return error_response(request, 400, "OAUTH_STATE_INVALID", "Invalid OAuth state")

    client = OAuth2Client(
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scope=settings.GOOGLE_OAUTH_SCOPES or "openid email profile",
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
    )
    try:
        token = client.fetch_token(
            "https://oauth2.googleapis.com/token",
            code=code,
            code_verifier=code_verifier,
        )
    except Exception as exc:
        error_category = type(exc).__name__
        logger.warning(
            "oauth_callback_token_exchange_failed handler=google_callback error_category=%s redirect_uri=%s",
            error_category,
            settings.GOOGLE_OAUTH_REDIRECT_URI,
        )
        _log_auth_failure(
            request, "oauth_internal_error", detail=f"google_token_exchange:{error_category}"
        )
        return error_response(
            request, 500, "OAUTH_INTERNAL_ERROR", "OAuth internal error"
        )

    access_token = token.get("access_token") if isinstance(token, dict) else None
    if not access_token:
        _log_auth_failure(request, "oauth_exchange_failed", detail="google_access_token_missing")
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )

    try:
        userinfo_resp = httpx.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
    except Exception:
        logger.exception("oauth_userinfo_failed")
        _log_auth_failure(request, "oauth_internal_error")
        return error_response(
            request, 500, "OAUTH_INTERNAL_ERROR", "OAuth internal error"
        )

    if userinfo_resp.status_code != 200:
        _log_auth_failure(
            request, "oauth_exchange_failed", detail=f"userinfo_status:{userinfo_resp.status_code}"
        )
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )

    userinfo = userinfo_resp.json()
    email = userinfo.get("email") or ""
    google_sub = userinfo.get("sub")
    full_name = userinfo.get("name")
    avatar_url = userinfo.get("picture")

    if not email or not google_sub:
        _log_auth_failure(request, "oauth_exchange_failed", detail="userinfo_missing_claims")
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )

    user = get_or_create_user_for_google(
        db,
        email=email,
        google_sub=google_sub,
        full_name=full_name,
        avatar_url=avatar_url,
    )

    base_redirect = get_post_login_redirect_url()
    if not is_redirect_allowed(base_redirect):
        _log_auth_failure(request, "oauth_redirect_not_allowed")
        return error_response(
            request, 400, "OAUTH_EXCHANGE_FAILED", "Redirect URL is not allowlisted"
        )
    code = create_oauth_exchange_code(db, user.id)
    db.commit()
    redirect_url = f"{base_redirect}?code={code}"
    return RedirectResponse(url=redirect_url)


@router.post("/exchange")
def oauth_exchange(
    payload: OAuthExchangeRequest, request: Request, db: Session = Depends(get_db)
):
    if not payload.code:
        _log_auth_failure(request, "oauth_code_missing")
        return error_response(request, 400, "OAUTH_CODE_MISSING", "Missing OAuth code")

    code_record = consume_oauth_exchange_code(db, payload.code)
    if not code_record:
        existing_record = _lookup_oauth_exchange_code(db, payload.code)
        now = _now_utc()
        replay_allowed = False

        if existing_record and existing_record.consumed_at is not None:
            expires_at = _as_utc(existing_record.expires_at)
            consumed_at = _as_utc(existing_record.consumed_at)
            replay_deadline = consumed_at + timedelta(seconds=OAUTH_EXCHANGE_REPLAY_WINDOW_SECONDS)
            replay_allowed = expires_at > now and now <= replay_deadline

        if replay_allowed and existing_record is not None:
            code_record = existing_record
            _log_auth_failure(request, "oauth_exchange_replay", user_id=code_record.user_id, detail="accepted")
        else:
            detail = "code_not_found"
            if existing_record:
                if existing_record.consumed_at is not None:
                    detail = "code_already_consumed"
                elif _as_utc(existing_record.expires_at) <= now:
                    detail = "code_expired"
            _log_auth_failure(request, "oauth_exchange_failed", detail=detail)
            return error_response(
                request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
            )

    user = db.execute(select(User).where(User.id == code_record.user_id)).scalar_one_or_none()
    if not user:
        _log_auth_failure(request, "oauth_exchange_failed")
        return error_response(
            request, 401, "OAUTH_EXCHANGE_FAILED", "OAuth exchange failed"
        )

    _revoke_active_refresh_tokens(db, user.id)
    refresh_token, _ = _issue_refresh_token(db, user.id)
    access_token, expires_in, plan = issue_access_token(db, user)
    db.commit()
    try:
        maybe_send_welcome_email(db, user=user)
    except Exception:
        logger.exception("welcome_email_send_failed user_id=%s", user.id)

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
                "plan": plan,
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
    email = normalize_email(payload.email)
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

    login_link = build_magic_link_url(raw_token)
    try:
        send_magic_link_email(
            db,
            to_email=email,
            login_link=login_link,
            expires_minutes=settings.AUTH_MAGIC_LINK_TTL_MIN,
            event_key=f"magic_link:{token_record.id}",
        )
    except Exception:
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
    user = get_or_create_user_for_magic_link(db, email=email)

    _revoke_active_refresh_tokens(db, user.id)
    refresh_token, _ = _issue_refresh_token(db, user.id)
    access_token, expires_in, plan = issue_access_token(db, user)
    db.commit()
    try:
        maybe_send_welcome_email(db, user=user)
    except Exception:
        logger.exception("welcome_email_send_failed user_id=%s", user.id)

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
                "plan": plan,
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
    db.flush()
    token_record.revoked_at = datetime.now(timezone.utc)
    token_record.replaced_by_token_id = new_token_id
    access_token, expires_in, _ = issue_access_token(db, user)
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
    access_token, expires_in, plan = issue_access_token(db, user)
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
                "plan": plan,
            },
        },
    )
