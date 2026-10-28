"""
services/payment_service.py
Business logic for Stripe checkout sessions and subscription webhooks.
"""

import logging
import stripe
from sqlalchemy.orm import Session

from config import settings
from db import models

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Maps your Stripe Price IDs to the subscription tier they unlock.
# Fill these in once you have real Stripe Price objects.
PRICE_ID_TO_TIER = {
    # "price_XXXXXXXXXXXX": "pro",
}


def create_checkout_session(
    user: models.User,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Creates a Stripe Checkout session for the given user and price.
    Returns the checkout session URL to redirect the user to.
    """
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        client_reference_id=str(user.id),
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id)},
    )
    return session.url


def handle_checkout_completed(db: Session, event_data: dict) -> None:
    """Activates the user's subscription after a successful checkout."""
    user_id = event_data.get("metadata", {}).get("user_id") or event_data.get("client_reference_id")
    customer_id = event_data.get("customer")

    if not user_id:
        logger.warning("checkout.session.completed event without user_id metadata")
        return

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        logger.warning(f"checkout.session.completed: user {user_id} not found")
        return

    user.subscription_status = "active"
    user.stripe_customer_id = customer_id
    db.commit()
    logger.info(f"Subscription activated for user {user_id}")


def handle_subscription_deleted(db: Session, event_data: dict) -> None:
    """Downgrades the user when their Stripe subscription is cancelled."""
    customer_id = event_data.get("customer")
    if not customer_id:
        return

    user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
    if not user:
        logger.warning(f"customer.subscription.deleted: no user for customer {customer_id}")
        return

    user.subscription_status = "free"
    db.commit()
    logger.info(f"Subscription cancelled for user {user.id}")


def construct_webhook_event(payload: bytes, sig_header: str, webhook_secret: str):
    """
    Verifies and parses a Stripe webhook payload.
    Raises stripe.error.SignatureVerificationError on an invalid signature.
    """
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
