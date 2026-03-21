"""Tests for billing webhook idempotency."""

from datetime import UTC, datetime

from app.models.billing import Payment, PaymentStatus
from app.services.stripe_service import StripeService


def test_record_payment_idempotent(db_session, test_client_record):
    """Recording the same payment_intent twice should not create duplicates."""
    service = StripeService(db_session)
    client_id = test_client_record["client"].id

    # Record first time
    p1 = service.record_payment(
        client_id=client_id,
        stripe_payment_intent_id="pi_test_123",
        amount_cents=4900,
        status="succeeded",
        description="Test payment",
    )
    assert p1.id is not None

    # Record same payment_intent again
    p2 = service.record_payment(
        client_id=client_id,
        stripe_payment_intent_id="pi_test_123",
        amount_cents=4900,
        status="succeeded",
        description="Test payment duplicate",
    )

    # Should return the same record, not create a new one
    assert p1.id == p2.id
    assert db_session.query(Payment).filter(Payment.stripe_payment_intent_id == "pi_test_123").count() == 1


def test_record_different_payments(db_session, test_client_record):
    """Different payment_intents should create separate records."""
    service = StripeService(db_session)
    client_id = test_client_record["client"].id

    p1 = service.record_payment(
        client_id=client_id,
        stripe_payment_intent_id="pi_test_a",
        amount_cents=4900,
        status="succeeded",
    )
    p2 = service.record_payment(
        client_id=client_id,
        stripe_payment_intent_id="pi_test_b",
        amount_cents=4900,
        status="succeeded",
    )

    assert p1.id != p2.id
