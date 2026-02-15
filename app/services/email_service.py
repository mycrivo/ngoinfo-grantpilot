from __future__ import annotations

import logging
import uuid
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.models.email_event import EmailEvent
from app.models.user import User

logger = logging.getLogger("email")

STATUS_SENT = "SENT"
STATUS_FAILED = "FAILED"
STATUS_SUPPRESSED = "SUPPRESSED"

EVENT_MAGIC_LINK_LOGIN = "MAGIC_LINK_LOGIN"
EVENT_WELCOME = "WELCOME"
EVENT_PROPOSAL_DRAFT_READY = "PROPOSAL_DRAFT_READY"
EVENT_SUBSCRIPTION_ACTIVATED = "SUBSCRIPTION_ACTIVATED"

LOGO_URL = "https://ngoinfo.org/wp-content/uploads/2025/06/NGOInfo-logo-1.png"
BG_COLOR = "#F8F9FC"
CARD_COLOR = "#FFFFFF"
CTA_COLOR = "#1A1F71"
TEXT_COLOR = "#111827"
MUTED_COLOR = "#6B7280"


def frontend_base_url() -> str:
    settings = get_settings()
    parsed = urlparse(settings.AUTH_POST_LOGIN_REDIRECT_URL)
    if not parsed.scheme or not parsed.netloc:
        return settings.APP_BASE_URL.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"


def maybe_send_welcome_email(db: Session, *, user: User) -> None:
    if user.first_login_at is not None:
        return
    user.first_login_at = _now_utc()
    db.add(user)
    db.commit()
    send_welcome_email(
        db,
        user=user,
        event_key=f"user:{user.id}:welcome",
    )


def send_magic_link_email(
    db: Session,
    *,
    to_email: str,
    login_link: str,
    expires_minutes: int,
    event_key: str,
) -> None:
    subject = "Your GrantPilot login link"
    title = "Sign in to NGOInfo GrantPilot"
    body_lines = [
        "Use the secure link below to sign in to your account.",
        f"This link expires in {expires_minutes} minutes.",
    ]
    html = _render_email_html(
        title=title,
        body_lines=body_lines,
        primary_cta_label="Sign in to GrantPilot",
        primary_cta_url=login_link,
        fallback_url=login_link,
    )
    text = (
        "Sign in to NGOInfo GrantPilot.\n\n"
        "Use the secure link below to sign in:\n"
        f"{login_link}\n\n"
        f"This link expires in {expires_minutes} minutes."
    )
    _send_transactional_email(
        db,
        event_type=EVENT_MAGIC_LINK_LOGIN,
        event_key=event_key,
        user_id=None,
        to_email=to_email,
        subject=subject,
        html=html,
        text=text,
        raise_on_failure=True,
    )


def send_welcome_email(db: Session, *, user: User, event_key: str) -> None:
    dashboard_url = f"{frontend_base_url()}/dashboard"
    explore_url = "https://ngoinfo.org"
    html = _render_email_html(
        title="Welcome to NGOInfo GrantPilot",
        body_lines=[
            "You are now part of a growing community of NGOs using smarter tools to find funding and develop stronger proposals.",
            "GrantPilot helps you assess donor fit, generate structured drafts, refine submissions, and maintain proposal history.",
            "If you have feedback, you can reply to this email.",
        ],
        primary_cta_label="Go to Dashboard",
        primary_cta_url=dashboard_url,
        secondary_link_label="Explore NGOInfo.org",
        secondary_link_url=explore_url,
    )
    text = (
        "Welcome to NGOInfo GrantPilot.\n\n"
        "GrantPilot helps you assess donor fit, generate proposal drafts, and maintain proposal history.\n"
        f"Go to Dashboard: {dashboard_url}\n"
        f"Explore NGOInfo.org: {explore_url}"
    )
    _send_transactional_email(
        db,
        event_type=EVENT_WELCOME,
        event_key=event_key,
        user_id=user.id,
        to_email=user.email,
        subject="Welcome to NGOInfo",
        html=html,
        text=text,
        raise_on_failure=False,
    )


def send_proposal_draft_ready_email(
    db: Session,
    *,
    user: User,
    proposal_id: uuid.UUID,
    opportunity_title: str,
    event_key: str,
) -> None:
    proposal_url = f"{frontend_base_url()}/proposals/{proposal_id}"
    html = _render_email_html(
        title="Your proposal draft is ready",
        body_lines=[
            "Your AI-generated proposal is now available in your NGOInfo GrantPilot dashboard.",
            f"Opportunity: {opportunity_title}",
            "You can review, refine, or export your draft at any time.",
        ],
        primary_cta_label="View Proposal",
        primary_cta_url=proposal_url,
    )
    text = (
        "Your proposal draft is ready.\n\n"
        f"Opportunity: {opportunity_title}\n"
        f"View Proposal: {proposal_url}"
    )
    _send_transactional_email(
        db,
        event_type=EVENT_PROPOSAL_DRAFT_READY,
        event_key=event_key,
        user_id=user.id,
        to_email=user.email,
        subject="Your proposal draft is ready - NGOInfo",
        html=html,
        text=text,
        raise_on_failure=False,
    )


def send_subscription_activated_email(
    db: Session,
    *,
    user: User,
    plan_name: str,
    billing_portal_url: str,
    event_key: str,
) -> None:
    plan_label = (plan_name or "").strip().upper() or "PAID"
    html = _render_email_html(
        title="Your plan is now active",
        body_lines=[
            f"Your {plan_label} plan is now active within NGOInfo GrantPilot.",
            "You now have access to proposal generation, fit scoring, and proposal history.",
        ],
        primary_cta_label="Manage Billing",
        primary_cta_url=billing_portal_url,
    )
    text = (
        "Your subscription is active.\n\n"
        f"Plan: {plan_label}\n"
        f"Manage Billing: {billing_portal_url}"
    )
    _send_transactional_email(
        db,
        event_type=EVENT_SUBSCRIPTION_ACTIVATED,
        event_key=event_key,
        user_id=user.id,
        to_email=user.email,
        subject="Your subscription is active - NGOInfo",
        html=html,
        text=text,
        raise_on_failure=False,
    )


def _send_transactional_email(
    db: Session,
    *,
    event_type: str,
    event_key: str,
    user_id: uuid.UUID | None,
    to_email: str,
    subject: str,
    html: str,
    text: str,
    raise_on_failure: bool,
) -> None:
    settings = get_settings()
    existing = db.execute(
        select(EmailEvent).where(EmailEvent.event_key == event_key)
    ).scalar_one_or_none()
    if existing and existing.status in {STATUS_SENT, STATUS_SUPPRESSED}:
        logger.info(
            "email_event_duplicate event_type=%s event_key=%s status=%s",
            event_type,
            event_key,
            existing.status,
        )
        return

    event = existing or EmailEvent(
        event_key=event_key,
        event_type=event_type,
        user_id=user_id,
        to_email=to_email,
        status=STATUS_FAILED,
    )
    if existing is None:
        db.add(event)
        db.flush()

    if settings.EMAIL_SUPPRESS_SENDING:
        event.status = STATUS_SUPPRESSED
        event.provider_message_id = None
        event.error_message = None
        db.add(event)
        db.commit()
        logger.info(
            "email_event event_type=%s user_id=%s to_email=%s event_key=%s status=%s",
            event_type,
            user_id,
            to_email,
            event_key,
            STATUS_SUPPRESSED,
        )
        return

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.EMAIL_API_KEY}"},
            json={
                "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
                "to": [to_email],
                "subject": subject,
                "html": html,
                "text": text,
            },
            timeout=10.0,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"provider_status_{resp.status_code}")
        provider_id = None
        try:
            payload = resp.json()
            provider_id = str(payload.get("id")) if payload.get("id") else None
        except Exception:
            provider_id = None

        event.status = STATUS_SENT
        event.provider_message_id = provider_id
        event.error_message = None
        db.add(event)
        db.commit()
        logger.info(
            "email_event event_type=%s user_id=%s to_email=%s event_key=%s status=%s provider_message_id=%s",
            event_type,
            user_id,
            to_email,
            event_key,
            STATUS_SENT,
            provider_id,
        )
    except Exception as exc:
        safe_error = str(exc)[:300]
        event.status = STATUS_FAILED
        event.provider_message_id = None
        event.error_message = safe_error
        db.add(event)
        db.commit()
        logger.error(
            "email_event event_type=%s user_id=%s to_email=%s event_key=%s status=%s",
            event_type,
            user_id,
            to_email,
            event_key,
            STATUS_FAILED,
        )
        if raise_on_failure:
            raise DomainError(
                error_code="EMAIL_PROVIDER_ERROR",
                message="Email provider error",
                status_code=500,
            ) from exc


def _render_email_html(
    *,
    title: str,
    body_lines: list[str],
    primary_cta_label: str,
    primary_cta_url: str,
    secondary_link_label: str | None = None,
    secondary_link_url: str | None = None,
    fallback_url: str | None = None,
) -> str:
    body_html = "".join(
        f'<p style="margin:0 0 14px 0;color:{TEXT_COLOR};line-height:1.6;">{line}</p>'
        for line in body_lines
    )
    secondary_html = ""
    if secondary_link_label and secondary_link_url:
        secondary_html = (
            f'<p style="margin:18px 0 0 0;color:{MUTED_COLOR};line-height:1.6;">'
            f'<a href="{secondary_link_url}" style="color:{CTA_COLOR};text-decoration:none;">'
            f"{secondary_link_label}</a></p>"
        )
    fallback_html = ""
    if fallback_url:
        fallback_html = (
            f'<p style="margin:18px 0 0 0;color:{MUTED_COLOR};line-height:1.6;">'
            f"If the button does not work, use this link:<br>"
            f'<a href="{fallback_url}" style="color:{CTA_COLOR};word-break:break-all;">{fallback_url}</a></p>'
        )
    return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:{BG_COLOR};font-family:'DM Sans',Arial,sans-serif;color:{TEXT_COLOR};">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;margin:0 auto;background:{CARD_COLOR};border:1px solid #E5E7EB;border-radius:12px;">
      <tr>
        <td style="padding:24px;">
          <img src="{LOGO_URL}" alt="NGOInfo" width="180" style="display:block;margin:0 0 20px 0;" />
          <h1 style="margin:0 0 14px 0;font-size:24px;line-height:1.3;color:{CTA_COLOR};">{title}</h1>
          {body_html}
          <p style="margin:22px 0 0 0;">
            <a href="{primary_cta_url}" style="display:inline-block;background:{CTA_COLOR};color:#FFFFFF;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:600;">
              {primary_cta_label}
            </a>
          </p>
          {secondary_html}
          {fallback_html}
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


def _now_utc():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)

