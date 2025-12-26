"""
Stripe Billing Service

Handles subscription management, payments, and webhooks.
"""

from datetime import datetime
from typing import Any

import stripe
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.billing import Payment, PaymentStatus, Subscription, SubscriptionStatus
from app.models.client import Client, ClientTier

settings = get_settings()


# Stripe price IDs (set these in your Stripe dashboard)
STRIPE_PRICES = {
    "starter": {
        "monthly": "price_starter_monthly",
        "yearly": "price_starter_yearly",
        "amount": 4900,  # $49
    },
    "pro": {
        "monthly": "price_pro_monthly",
        "yearly": "price_pro_yearly",
        "amount": 14900,  # $149
    },
    "enterprise": {
        "monthly": "price_enterprise_monthly",
        "yearly": "price_enterprise_yearly",
        "amount": 39900,  # $399
    },
    "agency": {
        "monthly": "price_agency_monthly",
        "yearly": "price_agency_yearly",
        "amount": 79900,  # $799
    },
}


class StripeService:
    """Service for Stripe billing operations."""

    def __init__(self, db: Session):
        self.db = db
        stripe.api_key = settings.stripe_secret_key if hasattr(settings, "stripe_secret_key") else None

    def create_customer(self, client: Client) -> str:
        """Create a Stripe customer for a client."""
        customer = stripe.Customer.create(
            email=client.email,
            name=client.name,
            metadata={
                "client_id": str(client.id),
                "company": client.company or "",
            },
        )
        return customer.id

    def create_checkout_session(
        self,
        client: Client,
        tier: str,
        interval: str = "monthly",
        success_url: str = "",
        cancel_url: str = "",
    ) -> dict[str, Any]:
        """Create a Stripe Checkout session for subscription."""
        price_config = STRIPE_PRICES.get(tier)
        if not price_config:
            raise ValueError(f"Invalid tier: {tier}")

        price_id = price_config.get(interval, price_config["monthly"])

        # Get or create Stripe customer
        subscription = self.db.query(Subscription).filter(Subscription.client_id == client.id).first()

        customer_id = subscription.stripe_customer_id if subscription else None
        if not customer_id:
            customer_id = self.create_customer(client)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=success_url or f"{settings.app_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url or f"{settings.app_url}/billing/cancel",
            metadata={
                "client_id": str(client.id),
                "tier": tier,
            },
            subscription_data={
                "trial_period_days": 14,
                "metadata": {
                    "client_id": str(client.id),
                    "tier": tier,
                },
            },
        )

        return {
            "session_id": session.id,
            "url": session.url,
        }

    def create_subscription(
        self,
        client: Client,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        tier: str,
        status: str,
    ) -> Subscription:
        """Create a subscription record from Stripe webhook data."""
        price_config = STRIPE_PRICES.get(tier, STRIPE_PRICES["starter"])

        subscription = Subscription(
            client_id=client.id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            tier_name=tier,
            status=SubscriptionStatus(status),
            amount_cents=price_config["amount"],
            currency="usd",
            billing_interval="month",
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        # Update client tier
        tier_map = {
            "starter": ClientTier.STARTER,
            "pro": ClientTier.PROFESSIONAL,
            "enterprise": ClientTier.ENTERPRISE,
            "agency": ClientTier.AGENCY,
        }
        client.tier = tier_map.get(tier, ClientTier.STARTER)
        self.db.commit()

        return subscription

    def update_subscription_status(
        self,
        stripe_subscription_id: str,
        status: str,
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        canceled_at: datetime | None = None,
    ) -> Subscription | None:
        """Update subscription status from webhook."""
        subscription = (
            self.db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_subscription_id).first()
        )

        if not subscription:
            return None

        subscription.status = SubscriptionStatus(status)
        if current_period_start:
            subscription.current_period_start = current_period_start
        if current_period_end:
            subscription.current_period_end = current_period_end
        if canceled_at:
            subscription.canceled_at = canceled_at

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def record_payment(
        self,
        client_id: int,
        stripe_payment_intent_id: str,
        amount_cents: int,
        status: str,
        description: str = "",
        subscription_id: int | None = None,
    ) -> Payment:
        """Record a payment from Stripe webhook."""
        payment = Payment(
            client_id=client_id,
            subscription_id=subscription_id,
            stripe_payment_intent_id=stripe_payment_intent_id,
            amount_cents=amount_cents,
            status=PaymentStatus(status),
            description=description,
            paid_at=datetime.utcnow() if status == "succeeded" else None,
        )

        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        return payment

    def create_billing_portal_session(self, client: Client) -> str:
        """Create a Stripe Billing Portal session for self-service."""
        subscription = self.db.query(Subscription).filter(Subscription.client_id == client.id).first()

        if not subscription or not subscription.stripe_customer_id:
            raise ValueError("No active subscription found")

        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.app_url}/dashboard",
        )

        return session.url

    def cancel_subscription(self, client: Client, at_period_end: bool = True) -> bool:
        """Cancel a subscription."""
        subscription = (
            self.db.query(Subscription)
            .filter(
                Subscription.client_id == client.id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            )
            .first()
        )

        if not subscription or not subscription.stripe_subscription_id:
            return False

        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=at_period_end,
        )

        if not at_period_end:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            self.db.commit()

        return True

    def get_usage_summary(self, client_id: int) -> dict[str, Any]:
        """Get usage summary for billing."""

        from app.models.audit import Audit
        from app.models.keyword import Keyword
        from app.models.website import Website

        # Current month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        audits_this_month = (
            self.db.query(Audit)
            .filter(
                Audit.website.has(client_id=client_id),
                Audit.created_at >= month_start,
            )
            .count()
        )

        total_websites = self.db.query(Website).filter(Website.client_id == client_id).count()

        total_keywords = self.db.query(Keyword).filter(Keyword.website.has(client_id=client_id)).count()

        return {
            "audits_this_month": audits_this_month,
            "total_websites": total_websites,
            "total_keywords": total_keywords,
            "period_start": month_start.isoformat(),
            "period_end": now.isoformat(),
        }
