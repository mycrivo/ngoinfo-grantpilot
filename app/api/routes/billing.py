import logging
from datetime import datetime, timezone
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.stripe_event import StripeEvent
from app.models.user_plan import UserPlan
from app.services.billing_service import (
    PROCESSING_FAILED,
    PROCESSING_SKIPPED,
    PROCESSING_SUCCESS,
    create_checkout_session,
    create_portal_session,
    handle_stripe_event,
    persist_stripe_event,
)

logger = logging.getLogger("billing")

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: Literal["GROWTH", "IMPACT"]


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


def _billing_current_user(
    request: Request, db: Session = Depends(get_db)
):
    try:
        return get_current_user(request, db)
    except DomainError as exc:
        if exc.status_code == 401:
            raise DomainError(
                error_code="UNAUTHORIZED",
                message="Unauthorized",
                status_code=401,
            ) from exc
        raise


@router.post("/checkout", response_model=CheckoutResponse)
def billing_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_billing_current_user),
) -> JSONResponse:
    existing_plan = db.execute(
        select(UserPlan).where(UserPlan.user_id == current_user.id)
    ).scalar_one_or_none()
    if existing_plan and (
        existing_plan.plan_name in {"GROWTH", "IMPACT"}
        or existing_plan.stripe_subscription_id
    ):
        raise DomainError(
            error_code="CONFLICT",
            message="Active paid subscription already exists",
            status_code=409,
        )

    try:
        checkout_url = create_checkout_session(db, current_user, payload.plan)
    except stripe.error.StripeError as exc:
        logger.exception("stripe_checkout_error")
        raise DomainError(
            error_code="INTERNAL_SERVER_ERROR",
            message="Checkout session creation failed",
            status_code=500,
        ) from exc

    return JSONResponse(status_code=200, content={"checkout_url": checkout_url})


@router.get("/portal", response_model=PortalResponse)
def billing_portal(
    db: Session = Depends(get_db),
    current_user=Depends(_billing_current_user),
) -> JSONResponse:
    try:
        portal_url = create_portal_session(db, current_user)
    except stripe.error.StripeError as exc:
        logger.exception("stripe_portal_error")
        raise DomainError(
            error_code="INTERNAL_SERVER_ERROR",
            message="Portal session creation failed",
            status_code=500,
        ) from exc

    return JSONResponse(status_code=200, content={"portal_url": portal_url})


@router.post("/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    settings = get_settings()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise DomainError(
            error_code="BAD_REQUEST",
            message="Missing Stripe signature",
            status_code=400,
        )
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception as exc:
        logger.warning("stripe_webhook_invalid")
        raise DomainError(
            error_code="BAD_REQUEST",
            message="Invalid Stripe webhook payload",
            status_code=400,
        ) from exc

    event_dict = event.to_dict()
    stripe_event_id = event_dict.get("id")
    event_type = event_dict.get("type")
    if not stripe_event_id or not event_type:
        raise DomainError(
            error_code="BAD_REQUEST",
            message="Invalid Stripe webhook payload",
            status_code=400,
        )

    try:
        if not persist_stripe_event(
            db, stripe_event_id=stripe_event_id, event_type=event_type, payload=event_dict
        ):
            return JSONResponse(status_code=200, content={"status": "duplicate"})
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("stripe_webhook_persist_error")
        raise DomainError(
            error_code="INTERNAL_SERVER_ERROR",
            message="Stripe webhook persistence failed",
            status_code=500,
        ) from exc

    processing_result = PROCESSING_SUCCESS
    error_message = None
    should_retry = False
    try:
        processing_result, error_message, should_retry = handle_stripe_event(
            db, event_dict
        )
    except stripe.error.StripeError as exc:
        logger.exception("stripe_webhook_processing_error")
        processing_result = PROCESSING_FAILED
        error_message = "STRIPE_API_ERROR"
        should_retry = True
    except Exception as exc:
        logger.exception("stripe_webhook_processing_error")
        processing_result = PROCESSING_FAILED
        error_message = "PROCESSING_ERROR"
        should_retry = True

    record = db.execute(
        select(StripeEvent).where(StripeEvent.stripe_event_id == stripe_event_id)
    ).scalar_one()
    record.processed_at = datetime.now(timezone.utc)
    record.processing_result = processing_result
    record.error_message = error_message
    db.commit()

    if processing_result == PROCESSING_FAILED and should_retry:
        raise DomainError(
            error_code="INTERNAL_SERVER_ERROR",
            message="Stripe webhook processing failed",
            status_code=500,
        )
    if processing_result == PROCESSING_FAILED:
        return JSONResponse(status_code=200, content={"status": "failed"})
    if processing_result == PROCESSING_SKIPPED:
        return JSONResponse(status_code=200, content={"status": "skipped"})
    return JSONResponse(status_code=200, content={"status": "processed"})
