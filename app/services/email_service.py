from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.models.user_plan import UserPlan
from app.services.email_templates import (
    EmailTemplate,
    build_fit_scan_ready_template,
    build_magic_link_template,
    build_payment_failed_template,
    build_profile_complete_template,
    build_proposal_ready_template,
    build_subscription_activated_template,
    build_subscription_cancelled_template,
    build_welcome_template,
)

logger = logging.getLogger("email")

_IDEMPOTENT_SENT_KEYS: dict[str, str] = {}
_IDEMPOTENCY_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_user_id(user_id: uuid.UUID | str | None) -> str | None:
    if user_id is None:
        return None
    return str(user_id)


def frontend_base_url() -> str:
    settings = get_settings()
    return settings.EMAIL_BASE_URL.rstrip("/")


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _log_event(
        self,
        *,
        user_id: uuid.UUID | str | None,
        email_to: str,
        template_name: str,
        status: str,
        provider_message_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        logger.info(
            "email_send user_id=%s email_to=%s template_name=%s status=%s provider_message_id=%s error_message=%s timestamp=%s",
            _normalize_user_id(user_id) or "unknown",
            email_to,
            template_name,
            status,
            provider_message_id or "none",
            error_message or "none",
            _now_iso(),
        )

    def _already_sent(self, idempotency_key: str | None) -> bool:
        if not idempotency_key:
            return False
        with _IDEMPOTENCY_LOCK:
            return idempotency_key in _IDEMPOTENT_SENT_KEYS

    def _mark_sent(self, idempotency_key: str | None) -> None:
        if not idempotency_key:
            return
        with _IDEMPOTENCY_LOCK:
            _IDEMPOTENT_SENT_KEYS[idempotency_key] = _now_iso()

    def _send_email(
        self,
        *,
        user_id: uuid.UUID | str | None,
        email_to: str,
        template_name: str,
        template: EmailTemplate,
        idempotency_key: str | None,
    ) -> None:
        if self.settings.EMAIL_PROVIDER.lower() != "resend":
            self._log_event(
                user_id=user_id,
                email_to=email_to,
                template_name=template_name,
                status="failed",
                error_message=f"unsupported_provider:{self.settings.EMAIL_PROVIDER}",
            )
            return

        if self._already_sent(idempotency_key):
            self._log_event(
                user_id=user_id,
                email_to=email_to,
                template_name=template_name,
                status="suppressed",
                error_message="idempotency_key_already_sent",
            )
            return

        if self.settings.EMAIL_SUPPRESS_SENDING:
            self._log_event(
                user_id=user_id,
                email_to=email_to,
                template_name=template_name,
                status="suppressed",
                error_message="EMAIL_SUPPRESS_SENDING=true",
            )
            return

        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self.settings.EMAIL_API_KEY}"},
                json={
                    "from": f"{self.settings.EMAIL_FROM_NAME} <{self.settings.EMAIL_FROM_ADDRESS}>",
                    "to": [email_to],
                    "subject": template.subject,
                    "html": template.html,
                    "text": template.text,
                },
                timeout=10.0,
            )
            provider_message_id: str | None = None
            if response.status_code < 400:
                try:
                    payload = response.json()
                    if isinstance(payload, dict) and payload.get("id") is not None:
                        provider_message_id = str(payload.get("id"))
                except Exception:
                    provider_message_id = None
                self._mark_sent(idempotency_key)
                self._log_event(
                    user_id=user_id,
                    email_to=email_to,
                    template_name=template_name,
                    status="sent",
                    provider_message_id=provider_message_id,
                )
                return

            self._log_event(
                user_id=user_id,
                email_to=email_to,
                template_name=template_name,
                status="failed",
                error_message=f"provider_status_{response.status_code}",
            )
        except Exception as exc:
            self._log_event(
                user_id=user_id,
                email_to=email_to,
                template_name=template_name,
                status="failed",
                error_message=str(exc)[:300],
            )

    def send_magic_link(
        self,
        *,
        user_email: str,
        full_name: str | None,
        login_link: str,
        expires_minutes: int,
        user_id: uuid.UUID | str | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        template = build_magic_link_template(
            full_name=full_name,
            login_link=login_link,
            expires_minutes=expires_minutes,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="magic_link",
            template=template,
            idempotency_key=idempotency_key,
        )

    def send_welcome(
        self,
        *,
        user_id: uuid.UUID | str,
        user_email: str,
        full_name: str | None,
        profile_link: str,
        idempotency_key: str | None = None,
    ) -> None:
        key = idempotency_key or f"{user_id}:welcome"
        template = build_welcome_template(
            full_name=full_name,
            profile_link=profile_link,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="welcome",
            template=template,
            idempotency_key=key,
        )

    def send_profile_complete(
        self,
        *,
        user_id: uuid.UUID | str,
        user_email: str,
        full_name: str | None,
        dashboard_link: str,
        idempotency_key: str | None = None,
    ) -> None:
        key = idempotency_key or f"{user_id}:profile_complete"
        template = build_profile_complete_template(
            full_name=full_name,
            dashboard_link=dashboard_link,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="profile_complete",
            template=template,
            idempotency_key=key,
        )

    def send_fit_scan_ready(
        self,
        *,
        fit_scan_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
        user_email: str,
        full_name: str | None,
        opportunity_title: str,
        overall_fit_rating: str,
        fit_scan_link: str,
        idempotency_key: str | None = None,
    ) -> None:
        key = idempotency_key or f"{fit_scan_id}:result_ready"
        template = build_fit_scan_ready_template(
            full_name=full_name,
            opportunity_title=opportunity_title,
            overall_fit_rating=overall_fit_rating,
            fit_scan_link=fit_scan_link,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="fit_scan_ready",
            template=template,
            idempotency_key=key,
        )

    def send_proposal_ready(
        self,
        *,
        proposal_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
        user_email: str,
        full_name: str | None,
        opportunity_title: str,
        proposal_link: str,
        upgrade_link: str,
        is_free_plan: bool,
        idempotency_key: str | None = None,
    ) -> None:
        key = idempotency_key or f"{proposal_id}:draft_ready"
        template = build_proposal_ready_template(
            full_name=full_name,
            opportunity_title=opportunity_title,
            proposal_link=proposal_link,
            upgrade_link=upgrade_link,
            is_free_plan=is_free_plan,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="proposal_ready",
            template=template,
            idempotency_key=key,
        )

    def send_subscription_activated(
        self,
        *,
        stripe_event_id: str,
        user_id: uuid.UUID | str,
        user_email: str,
        full_name: str | None,
        plan_name: str,
        dashboard_link: str,
        billing_portal_link: str,
        idempotency_key: str | None = None,
    ) -> None:
        key = idempotency_key or stripe_event_id
        template = build_subscription_activated_template(
            full_name=full_name,
            plan_name=plan_name,
            dashboard_link=dashboard_link,
            billing_portal_link=billing_portal_link,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="subscription_activated",
            template=template,
            idempotency_key=key,
        )

    def send_payment_failed(
        self,
        *,
        stripe_event_id: str,
        user_id: uuid.UUID | str,
        user_email: str,
        full_name: str | None,
        plan_name: str,
        billing_portal_link: str,
        idempotency_key: str | None = None,
    ) -> None:
        key = idempotency_key or stripe_event_id
        template = build_payment_failed_template(
            full_name=full_name,
            plan_name=plan_name,
            billing_portal_link=billing_portal_link,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="payment_failed",
            template=template,
            idempotency_key=key,
        )

    def send_subscription_cancelled(
        self,
        *,
        stripe_event_id: str,
        user_id: uuid.UUID | str,
        user_email: str,
        full_name: str | None,
        plan_name: str,
        access_end_date: datetime | None,
        billing_portal_link: str,
        idempotency_key: str | None = None,
    ) -> None:
        key = idempotency_key or stripe_event_id
        template = build_subscription_cancelled_template(
            full_name=full_name,
            plan_name=plan_name,
            access_end_date=access_end_date,
            billing_portal_link=billing_portal_link,
            base_url=frontend_base_url(),
        )
        self._send_email(
            user_id=user_id,
            email_to=user_email,
            template_name="subscription_cancelled",
            template=template,
            idempotency_key=key,
        )


_EMAIL_SERVICE = EmailService()


def send_magic_link(
    *,
    user_email: str,
    full_name: str | None,
    login_link: str,
    expires_minutes: int,
    user_id: uuid.UUID | str | None = None,
    idempotency_key: str | None = None,
) -> None:
    _EMAIL_SERVICE.send_magic_link(
        user_email=user_email,
        full_name=full_name,
        login_link=login_link,
        expires_minutes=expires_minutes,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )


def maybe_send_welcome_email(db: Session, *, user: User) -> None:
    if user.first_login_at is not None:
        return
    user.first_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    _EMAIL_SERVICE.send_welcome(
        user_id=user.id,
        user_email=user.email,
        full_name=user.full_name,
        profile_link=f"{frontend_base_url()}/profile",
        idempotency_key=f"{user.id}:welcome",
    )


def send_magic_link_email(
    db: Session,  # kept for compatibility with existing call sites
    *,
    to_email: str,
    login_link: str,
    expires_minutes: int,
    event_key: str,
) -> None:
    _ = db
    _ = event_key
    send_magic_link(
        user_email=to_email,
        full_name=None,
        login_link=login_link,
        expires_minutes=expires_minutes,
        idempotency_key=None,
    )


def send_welcome_email(db: Session, *, user: User, event_key: str) -> None:
    _ = db
    _EMAIL_SERVICE.send_welcome(
        user_id=user.id,
        user_email=user.email,
        full_name=user.full_name,
        profile_link=f"{frontend_base_url()}/profile",
        idempotency_key=event_key,
    )


def send_proposal_draft_ready_email(
    db: Session,
    *,
    user: User,
    proposal_id: uuid.UUID,
    opportunity_title: str,
    event_key: str,
) -> None:
    plan = db.execute(select(UserPlan).where(UserPlan.user_id == user.id)).scalar_one_or_none()
    is_free_plan = not plan or plan.plan_name == "FREE"
    _EMAIL_SERVICE.send_proposal_ready(
        proposal_id=proposal_id,
        user_id=user.id,
        user_email=user.email,
        full_name=user.full_name,
        opportunity_title=opportunity_title,
        proposal_link=f"{frontend_base_url()}/proposal/{proposal_id}",
        upgrade_link=f"{frontend_base_url()}/billing",
        is_free_plan=is_free_plan,
        idempotency_key=event_key,
    )


def send_subscription_activated_email(
    db: Session,
    *,
    user: User,
    plan_name: str,
    billing_portal_url: str,
    event_key: str,
) -> None:
    _ = db
    _EMAIL_SERVICE.send_subscription_activated(
        stripe_event_id=event_key,
        user_id=user.id,
        user_email=user.email,
        full_name=user.full_name,
        plan_name=plan_name,
        dashboard_link=f"{frontend_base_url()}/dashboard",
        billing_portal_link=billing_portal_url,
        idempotency_key=event_key,
    )
