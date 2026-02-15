from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.services.email_service import (
    frontend_base_url,
    send_subscription_activated_email,
)
from app.models.stripe_event import StripeEvent
from app.models.user import User
from app.models.user_plan import UserPlan

logger = logging.getLogger("billing")

PLAN_FREE = "FREE"
PLAN_GROWTH = "GROWTH"
PLAN_IMPACT = "IMPACT"

PROCESSING_SUCCESS = "SUCCESS"
PROCESSING_FAILED = "FAILED"
PROCESSING_SKIPPED = "SKIPPED"


def _stripe_settings() -> SimpleNamespace:
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return SimpleNamespace(
        STRIPE_PRICE_ID_GROWTH=settings.STRIPE_PRICE_ID_GROWTH,
        STRIPE_PRICE_ID_IMPACT=settings.STRIPE_PRICE_ID_IMPACT,
    )


def _plan_for_price_id(price_id: str, settings: SimpleNamespace) -> str | None:
    if price_id == settings.STRIPE_PRICE_ID_GROWTH:
        return PLAN_GROWTH
    if price_id == settings.STRIPE_PRICE_ID_IMPACT:
        return PLAN_IMPACT
    return None


def _to_datetime(timestamp: int | None) -> datetime | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)


def _get_or_create_user_plan(db: Session, user_id: uuid.UUID) -> UserPlan:
    plan = db.execute(select(UserPlan).where(UserPlan.user_id == user_id)).scalar_one_or_none()
    if plan:
        return plan
    plan = UserPlan(user_id=user_id, plan_name=PLAN_FREE)
    db.add(plan)
    return plan


def _resolve_user_id(
    db: Session, *, metadata: dict | None, customer_id: str | None
) -> uuid.UUID | None:
    if metadata and metadata.get("user_id"):
        try:
            return uuid.UUID(str(metadata["user_id"]))
        except ValueError:
            return None
    if not customer_id:
        return None
    user = db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    ).scalar_one_or_none()
    return user.id if user else None


def _sync_paid_plan(
    db: Session,
    user_id: uuid.UUID,
    *,
    subscription_id: str,
    plan_name: str,
    period_start: datetime | None,
    period_end: datetime | None,
) -> None:
    plan = _get_or_create_user_plan(db, user_id)
    plan.plan_name = plan_name
    plan.stripe_subscription_id = subscription_id
    plan.billing_period_start = period_start
    plan.billing_period_end = period_end
    if plan.plan_activated_at is None:
        plan.plan_activated_at = datetime.now(timezone.utc)


def _sync_free_plan(db: Session, user_id: uuid.UUID) -> None:
    plan = _get_or_create_user_plan(db, user_id)
    plan.plan_name = PLAN_FREE
    plan.stripe_subscription_id = None
    plan.billing_period_start = None
    plan.billing_period_end = None


def create_checkout_session(db: Session, user: User, plan_name: str) -> str:
    if plan_name not in {PLAN_GROWTH, PLAN_IMPACT}:
        raise DomainError(
            error_code="BAD_REQUEST",
            message="Invalid plan",
            status_code=400,
        )

    settings = get_settings()
    stripe_settings = _stripe_settings()
    price_id = (
        stripe_settings.STRIPE_PRICE_ID_GROWTH
        if plan_name == PLAN_GROWTH
        else stripe_settings.STRIPE_PRICE_ID_IMPACT
    )

    stripe_customer_id = user.stripe_customer_id
    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        stripe_customer_id = customer.id
        user.stripe_customer_id = stripe_customer_id
        db.add(user)
        db.commit()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=stripe_customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.STRIPE_CHECKOUT_SUCCESS_URL,
        cancel_url=settings.STRIPE_CHECKOUT_CANCEL_URL,
        client_reference_id=str(user.id),
        metadata={"user_id": str(user.id), "plan": plan_name},
    )

    checkout_url = getattr(session, "url", None) or session.get("url")
    if not checkout_url:
        raise DomainError(
            error_code="INTERNAL_SERVER_ERROR",
            message="Checkout session creation failed",
            status_code=500,
        )
    return str(checkout_url)


def create_portal_session(db: Session, user: User) -> str:
    settings = get_settings()
    _stripe_settings()
    if not user.stripe_customer_id:
        raise DomainError(
            error_code="BAD_REQUEST",
            message="No billing account for user",
            status_code=400,
        )
    return_url = settings.STRIPE_PORTAL_RETURN_URL or settings.STRIPE_CHECKOUT_SUCCESS_URL
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )
    portal_url = getattr(session, "url", None) or session.get("url")
    if not portal_url:
        raise DomainError(
            error_code="INTERNAL_SERVER_ERROR",
            message="Portal session creation failed",
            status_code=500,
        )
    return str(portal_url)


def persist_stripe_event(
    db: Session, *, stripe_event_id: str, event_type: str, payload: dict
) -> bool:
    existing = db.execute(
        select(StripeEvent.id).where(StripeEvent.stripe_event_id == stripe_event_id)
    ).scalar_one_or_none()
    if existing:
        return False
    record = StripeEvent(
        id=uuid.uuid4(),
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        payload=payload,
        received_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.flush()
    return True


def handle_stripe_event(
    db: Session, event: dict, *, settings: SimpleNamespace | None = None
) -> tuple[str, str | None, bool]:
    if settings is None:
        settings = _stripe_settings()

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata") or {}
        subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        user_id = _resolve_user_id(db, metadata=metadata, customer_id=customer_id)
        if not user_id:
            return PROCESSING_FAILED, "USER_NOT_FOUND", False
        if customer_id:
            user = db.get(User, user_id)
            if user and not user.stripe_customer_id:
                user.stripe_customer_id = customer_id
        if not subscription_id:
            return PROCESSING_FAILED, "SUBSCRIPTION_ID_MISSING", False

        subscription = stripe.Subscription.retrieve(subscription_id)
        price_id = (
            subscription.get("items", {})
            .get("data", [{}])[0]
            .get("price", {})
            .get("id")
        )
        plan_name = metadata.get("plan") if metadata.get("plan") in {PLAN_GROWTH, PLAN_IMPACT} else None
        plan_name = plan_name or _plan_for_price_id(price_id, settings)
        if not plan_name:
            return PROCESSING_FAILED, "UNKNOWN_PRICE_ID", False

        _sync_paid_plan(
            db,
            user_id,
            subscription_id=subscription_id,
            plan_name=plan_name,
            period_start=_to_datetime(subscription.get("current_period_start")),
            period_end=_to_datetime(subscription.get("current_period_end")),
        )
        user = db.get(User, user_id)
        if user:
            try:
                billing_portal_url = create_portal_session(db, user)
            except Exception:
                billing_portal_url = f"{frontend_base_url()}/billing"
            try:
                send_subscription_activated_email(
                    db,
                    user=user,
                    plan_name=plan_name,
                    billing_portal_url=billing_portal_url,
                    event_key=f"stripe:{event.get('id')}:subscription_activated",
                )
            except Exception:
                logger.exception(
                    "subscription_activated_email_failed event_id=%s user_id=%s",
                    event.get("id"),
                    user_id,
                )
        return PROCESSING_SUCCESS, None, False

    if event_type == "customer.subscription.updated":
        subscription_id = data_object.get("id")
        customer_id = data_object.get("customer")
        user_id = _resolve_user_id(db, metadata=None, customer_id=customer_id)
        if not user_id:
            return PROCESSING_FAILED, "USER_NOT_FOUND", False

        price_id = (
            data_object.get("items", {})
            .get("data", [{}])[0]
            .get("price", {})
            .get("id")
        )
        plan_name = _plan_for_price_id(price_id, settings)
        if not plan_name:
            return PROCESSING_FAILED, "UNKNOWN_PRICE_ID", False
        if not subscription_id:
            return PROCESSING_FAILED, "SUBSCRIPTION_ID_MISSING", False

        _sync_paid_plan(
            db,
            user_id,
            subscription_id=subscription_id,
            plan_name=plan_name,
            period_start=_to_datetime(data_object.get("current_period_start")),
            period_end=_to_datetime(data_object.get("current_period_end")),
        )
        return PROCESSING_SUCCESS, None, False

    if event_type == "customer.subscription.deleted":
        customer_id = data_object.get("customer")
        user_id = _resolve_user_id(db, metadata=None, customer_id=customer_id)
        if not user_id:
            return PROCESSING_FAILED, "USER_NOT_FOUND", False
        _sync_free_plan(db, user_id)
        return PROCESSING_SUCCESS, None, False

    if event_type == "invoice.payment_failed":
        logger.info("stripe_payment_failed event_id=%s", event.get("id"))
        return PROCESSING_SUCCESS, None, False

    return PROCESSING_SKIPPED, None, False
