"""
Billing Models - Stripe Integration

Handles subscriptions, invoices, and payment tracking.
"""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class SubscriptionStatus(enum.Enum):
    """Subscription status."""

    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    PAUSED = "paused"


class PaymentStatus(enum.Enum):
    """Payment status."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Subscription(Base, TimestampMixin):
    """Customer subscription model."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    # Stripe IDs
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Subscription details
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, nullable=False)
    tier_name = Column(String(50), nullable=False)  # starter, pro, enterprise, agency

    # Billing
    amount_cents = Column(Integer, nullable=False)  # Price in cents
    currency = Column(String(3), default="usd", nullable=False)
    billing_interval = Column(String(20), default="month", nullable=False)  # month, year

    # Dates
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", backref="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        """Check if subscription is active or trialing."""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]

    @property
    def amount_dollars(self) -> float:
        """Get amount in dollars."""
        return self.amount_cents / 100


class Payment(Base, TimestampMixin):
    """Payment/Invoice record."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    # Stripe IDs
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_invoice_id = Column(String(255), nullable=True)

    # Payment details
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="usd", nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Description
    description = Column(String(500), nullable=True)
    invoice_pdf_url = Column(String(500), nullable=True)

    # Dates
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="payments")
    client = relationship("Client", backref="payments")


class UsageRecord(Base, TimestampMixin):
    """Track usage for metered billing."""

    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    # Usage type
    usage_type = Column(String(50), nullable=False)  # audit, api_call, report, etc.
    quantity = Column(Integer, default=1, nullable=False)

    # Extra data
    resource_id = Column(Integer, nullable=True)  # ID of the resource (audit_id, etc.)
    resource_type = Column(String(50), nullable=True)  # Type of resource
    extra_data = Column(Text, nullable=True)  # JSON metadata

    # Billing period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Relationships
    client = relationship("Client", backref="usage_records")
