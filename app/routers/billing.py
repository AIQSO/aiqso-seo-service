"""
Billing API Router

Endpoints for subscription management and payments.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import stripe

from app.database import get_db
from app.config import get_settings
from app.models.client import Client
from app.models.billing import Subscription, Payment, SubscriptionStatus
from app.services.stripe_service import StripeService, STRIPE_PRICES
from app.services.audit_service import AuditService
from app.security import require_client

# Alias for backwards compatibility with other routers
get_current_client = require_client

settings = get_settings()
router = APIRouter(prefix="/billing", tags=["Billing"])


# Request/Response schemas
class CheckoutRequest(BaseModel):
    tier: str  # starter, pro, enterprise, agency
    interval: str = "monthly"  # monthly, yearly
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


class SubscriptionResponse(BaseModel):
    id: int
    tier: str
    status: str
    amount: float
    interval: str
    current_period_end: Optional[str]
    is_active: bool


class UsageResponse(BaseModel):
    audits_this_month: int
    total_websites: int
    total_keywords: int
    period_start: str
    period_end: str


# Public endpoints (no authentication required)
@router.get("/plans")
def list_plans():
    """List available subscription plans. Public endpoint - no auth required."""
    plans = []
    for tier, config in STRIPE_PRICES.items():
        plans.append({
            "tier": tier,
            "name": tier.replace("_", " ").title(),
            "price_monthly": config["amount"] / 100,
            "price_yearly": (config["amount"] * 10) / 100,  # 2 months free
            "features": get_tier_features(tier),
        })
    return {"plans": plans}


def get_tier_features(tier: str) -> dict:
    """Get features for a tier."""
    features = {
        "starter": {
            "websites": 1,
            "keywords": 50,
            "audits_per_day": 10,
            "ai_insights": False,
            "api_access": False,
        },
        "pro": {
            "websites": 3,
            "keywords": 200,
            "audits_per_day": 50,
            "ai_insights": True,
            "api_access": True,
        },
        "enterprise": {
            "websites": 10,
            "keywords": 1000,
            "audits_per_day": 200,
            "ai_insights": True,
            "api_access": True,
        },
        "agency": {
            "websites": 100,
            "keywords": 10000,
            "audits_per_day": 1000,
            "ai_insights": True,
            "api_access": True,
            "white_label": True,
        },
    }
    return features.get(tier, features["starter"])


# Protected endpoints (authentication required via require_client dependency)
@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    request: CheckoutRequest,
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for subscription."""
    stripe_service = StripeService(db)
    audit_service = AuditService(db)

    try:
        result = stripe_service.create_checkout_session(
            client=client,
            tier=request.tier,
            interval=request.interval,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        # Log checkout session creation
        audit_service.log_action(
            client=client,
            action="checkout_created",
            resource_type="checkout_session",
            extra_data={
                "tier": request.tier,
                "interval": request.interval,
                "session_id": result.get("session_id"),
            },
        )

        return CheckoutResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscription", response_model=Optional[SubscriptionResponse])
def get_subscription(
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Get current subscription status."""
    # Ownership validation: Filter by authenticated client's ID to prevent cross-client access
    subscription = db.query(Subscription).filter(
        Subscription.client_id == client.id
    ).order_by(Subscription.created_at.desc()).first()

    if not subscription:
        return None

    # Explicit ownership check: Verify subscription belongs to authenticated client
    if subscription.client_id != client.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: subscription belongs to another client"
        )

    return SubscriptionResponse(
        id=subscription.id,
        tier=subscription.tier_name,
        status=subscription.status.value,
        amount=subscription.amount_dollars,
        interval=subscription.billing_interval,
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        is_active=subscription.is_active,
    )


@router.get("/usage", response_model=UsageResponse)
def get_usage(
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Get current usage for this billing period."""
    # Ownership validation: Only return usage for authenticated client
    stripe_service = StripeService(db)
    usage = stripe_service.get_usage_summary(client.id)
    return UsageResponse(**usage)


@router.post("/portal")
def get_billing_portal(
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Get Stripe Billing Portal URL for self-service."""
    stripe_service = StripeService(db)
    audit_service = AuditService(db)

    try:
        url = stripe_service.create_billing_portal_session(client)

        # Log portal access
        audit_service.log_action(
            client=client,
            action="portal_accessed",
            resource_type="billing_portal",
            extra_data={
                "portal_url": url,
            },
        )

        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
def cancel_subscription(
    at_period_end: bool = True,
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Cancel the current subscription."""
    # Ownership validation: StripeService.cancel_subscription filters by client.id
    # to ensure only the authenticated client's subscription can be canceled
    stripe_service = StripeService(db)
    audit_service = AuditService(db)

    if stripe_service.cancel_subscription(client, at_period_end):
        # Log subscription cancellation
        audit_service.log_action(
            client=client,
            action="subscription_cancelled",
            resource_type="subscription",
            extra_data={
                "at_period_end": at_period_end,
            },
        )

        return {"message": "Subscription will be canceled" + (" at period end" if at_period_end else " immediately")}
    else:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")


@router.get("/payments")
def list_payments(
    limit: int = 20,
    client: Client = Depends(require_client),
    db: Session = Depends(get_db),
):
    """List payment history."""
    # Ownership validation: Filter by authenticated client's ID to prevent cross-client access
    payments = db.query(Payment).filter(
        Payment.client_id == client.id
    ).order_by(Payment.created_at.desc()).limit(limit).all()

    return {
        "payments": [
            {
                "id": p.id,
                "amount": p.amount_cents / 100,
                "currency": p.currency,
                "status": p.status.value,
                "description": p.description,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "invoice_url": p.invoice_pdf_url,
            }
            for p in payments
        ]
    }


# Stripe Webhook endpoint (public - authenticated by Stripe signature)
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events. Public endpoint - authenticated by Stripe signature instead of API key."""
    payload = await request.body()
    webhook_secret = settings.stripe_webhook_secret if hasattr(settings, 'stripe_webhook_secret') else None

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    stripe_service = StripeService(db)
    audit_service = AuditService(db)

    # Handle events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        client_id = int(session["metadata"]["client_id"])
        tier = session["metadata"]["tier"]

        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            subscription = stripe_service.create_subscription(
                client=client,
                stripe_subscription_id=session["subscription"],
                stripe_customer_id=session["customer"],
                tier=tier,
                status="active",
            )

            # Log subscription creation
            audit_service.log_action(
                client=client,
                action="subscription_created",
                resource_type="subscription",
                resource_id=subscription.id if subscription else None,
                extra_data={
                    "tier": tier,
                    "stripe_subscription_id": session["subscription"],
                    "stripe_customer_id": session["customer"],
                    "event_type": event["type"],
                },
            )

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        updated_subscription = stripe_service.update_subscription_status(
            stripe_subscription_id=subscription["id"],
            status=subscription["status"],
            current_period_start=datetime.fromtimestamp(subscription["current_period_start"]),
            current_period_end=datetime.fromtimestamp(subscription["current_period_end"]),
        )

        # Log subscription update
        if updated_subscription:
            client = db.query(Client).filter(Client.id == updated_subscription.client_id).first()
            if client:
                audit_service.log_action(
                    client=client,
                    action="subscription_updated",
                    resource_type="subscription",
                    resource_id=updated_subscription.id,
                    extra_data={
                        "status": subscription["status"],
                        "stripe_subscription_id": subscription["id"],
                        "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
                        "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
                        "event_type": event["type"],
                    },
                )

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        deleted_subscription = stripe_service.update_subscription_status(
            stripe_subscription_id=subscription["id"],
            status="canceled",
            canceled_at=datetime.utcnow(),
        )

        # Log subscription deletion
        if deleted_subscription:
            client = db.query(Client).filter(Client.id == deleted_subscription.client_id).first()
            if client:
                audit_service.log_action(
                    client=client,
                    action="subscription_deleted",
                    resource_type="subscription",
                    resource_id=deleted_subscription.id,
                    extra_data={
                        "stripe_subscription_id": subscription["id"],
                        "canceled_at": datetime.utcnow().isoformat(),
                        "event_type": event["type"],
                    },
                )

    elif event["type"] == "invoice.paid":
        invoice = event["data"]["object"]
        # Find client by customer ID
        sub = db.query(Subscription).filter(
            Subscription.stripe_customer_id == invoice["customer"]
        ).first()

        if sub:
            payment = stripe_service.record_payment(
                client_id=sub.client_id,
                stripe_payment_intent_id=invoice["payment_intent"],
                amount_cents=invoice["amount_paid"],
                status="succeeded",
                description=f"Invoice {invoice['number']}",
                subscription_id=sub.id,
            )

            # Log payment received
            client = db.query(Client).filter(Client.id == sub.client_id).first()
            if client:
                audit_service.log_action(
                    client=client,
                    action="payment_received",
                    resource_type="payment",
                    resource_id=payment.id if payment else None,
                    extra_data={
                        "amount_cents": invoice["amount_paid"],
                        "currency": invoice.get("currency", "usd"),
                        "invoice_number": invoice.get("number"),
                        "stripe_payment_intent_id": invoice["payment_intent"],
                        "subscription_id": sub.id,
                        "event_type": event["type"],
                    },
                )

    return {"received": True}
