import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe

from db.database import get_db
from db import models
from schemas.payment import CheckoutSessionRequest, CheckoutSessionResponse
from utils.auth import get_current_user
from services import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        checkout_url = payment_service.create_checkout_session(
            user=current_user,
            price_id=request.price_id,
            success_url=str(request.success_url),
            cancel_url=str(request.cancel_url),
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout session creation failed: {e}")
        raise HTTPException(status_code=502, detail="Could not create checkout session")

    return CheckoutSessionResponse(checkout_url=checkout_url)


@router.get("/subscription-status")
def get_subscription_status(current_user: models.User = Depends(get_current_user)):
    return {
        "subscription_status": current_user.subscription_status,
        "subscription_end": current_user.subscription_end,
    }
