"""
Billing Authentication Integration Tests

Tests authentication and authorization for billing endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.models.client import Client, ClientTier
from app.models.billing import Subscription, Payment, SubscriptionStatus, PaymentStatus


class TestPublicBillingEndpoints:
    """Test public billing endpoints that don't require authentication."""

    def setup_method(self):
        """Setup test client for each test."""
        from app.main import app
        self.client = TestClient(app)

    def test_list_plans_no_auth_required(self):
        """Should allow access to /billing/plans without authentication."""
        response = self.client.get("/api/v1/billing/plans")
        assert response.status_code == 200
        body = response.json()
        assert "plans" in body
        assert len(body["plans"]) > 0

    def test_list_plans_with_auth_still_works(self):
        """Should allow access to /billing/plans even with invalid auth."""
        response = self.client.get(
            "/api/v1/billing/plans",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 200


class TestProtectedBillingEndpoints:
    """Test protected billing endpoints that require authentication."""

    def setup_method(self):
        """Setup test client for each test."""
        from app.main import app
        self.client = TestClient(app)

    def _create_mock_client(self, api_key="valid-key", is_active=True):
        """Create a mock Client object."""
        client = Mock(spec=Client)
        client.id = 1
        client.name = "Test Client"
        client.email = "test@example.com"
        client.api_key = api_key
        client.is_active = is_active
        client.tier = ClientTier.PROFESSIONAL
        client.stripe_customer_id = "cus_test123"
        return client

    @patch('app.routers.billing.StripeService')
    @patch('app.routers.billing.AuditService')
    @patch('app.security.SessionLocal')
    def test_checkout_with_valid_api_key(self, mock_session_local, mock_audit_service, mock_stripe_service):
        """Should allow checkout with valid API key."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_client = self._create_mock_client()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_client

        # Mock StripeService
        mock_stripe_instance = MagicMock()
        mock_stripe_instance.create_checkout_session.return_value = {
            "session_id": "cs_test123",
            "url": "https://checkout.stripe.com/test"
        }
        mock_stripe_service.return_value = mock_stripe_instance

        # Mock AuditService
        mock_audit_instance = MagicMock()
        mock_audit_service.return_value = mock_audit_instance

        response = self.client.post(
            "/api/v1/billing/checkout",
            json={"tier": "pro", "interval": "monthly"},
            headers={"X-API-Key": "valid-key"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == "cs_test123"
        assert body["url"] == "https://checkout.stripe.com/test"

    def test_checkout_without_api_key_fails(self):
        """Should reject checkout request without API key."""
        response = self.client.post(
            "/api/v1/billing/checkout",
            json={"tier": "pro", "interval": "monthly"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "API key required"

    @patch('app.security.SessionLocal')
    def test_checkout_with_invalid_api_key_fails(self, mock_session_local):
        """Should reject checkout request with invalid API key."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        response = self.client.post(
            "/api/v1/billing/checkout",
            json={"tier": "pro", "interval": "monthly"},
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    @patch('app.security.SessionLocal')
    def test_checkout_with_inactive_client_fails(self, mock_session_local):
        """Should reject checkout request when client is inactive."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_client = self._create_mock_client(is_active=False)
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_client

        response = self.client.post(
            "/api/v1/billing/checkout",
            json={"tier": "pro", "interval": "monthly"},
            headers={"X-API-Key": "valid-key"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Client is not active"

    def test_get_subscription_without_auth_fails(self):
        """Should reject subscription request without authentication."""
        response = self.client.get("/api/v1/billing/subscription")
        assert response.status_code == 401
        assert response.json()["detail"] == "API key required"

    def test_get_usage_without_auth_fails(self):
        """Should reject usage request without authentication."""
        response = self.client.get("/api/v1/billing/usage")
        assert response.status_code == 401

    def test_billing_portal_without_auth_fails(self):
        """Should reject billing portal request without authentication."""
        response = self.client.post("/api/v1/billing/portal")
        assert response.status_code == 401

    def test_cancel_subscription_without_auth_fails(self):
        """Should reject cancel request without authentication."""
        response = self.client.post("/api/v1/billing/cancel")
        assert response.status_code == 401

    def test_list_payments_without_auth_fails(self):
        """Should reject payments list request without authentication."""
        response = self.client.get("/api/v1/billing/payments")
        assert response.status_code == 401

    @patch('app.security.SessionLocal')
    def test_invalid_api_key_rejected_across_endpoints(self, mock_session_local):
        """Should consistently reject invalid API keys across all protected endpoints."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        endpoints = [
            ("GET", "/api/v1/billing/subscription"),
            ("GET", "/api/v1/billing/usage"),
            ("POST", "/api/v1/billing/portal"),
            ("POST", "/api/v1/billing/cancel"),
            ("GET", "/api/v1/billing/payments"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = self.client.get(endpoint, headers={"X-API-Key": "invalid-key"})
            else:
                response = self.client.post(endpoint, headers={"X-API-Key": "invalid-key"})

            assert response.status_code == 401, f"{method} {endpoint} should reject invalid API key"
            assert "Invalid API key" in response.json()["detail"]


class TestWebhookAuthentication:
    """Test webhook endpoint which uses Stripe signature instead of API key."""

    def setup_method(self):
        """Setup test client for each test."""
        from app.main import app
        self.client = TestClient(app)


    def test_webhook_does_not_require_api_key(self):
        """Should not require API key for webhook endpoint."""
        # This test ensures webhook doesn't use the same auth as other endpoints
        # Actual signature validation is tested separately
        response = self.client.post(
            "/api/v1/billing/webhook",
            json={"type": "test"}
        )
        # Should fail on signature/payload validation, not auth
        assert response.status_code in [400, 422, 500]
        # Should not be 401 (which would indicate auth failure)
        assert response.status_code != 401


class TestAuthorizationHeaderVariations:
    """Test different variations of Authorization header."""

    def setup_method(self):
        """Setup test client for each test."""
        from app.main import app
        self.client = TestClient(app)

    def test_missing_auth_header_rejected(self):
        """Should reject requests with no authentication headers."""
        endpoints = [
            "/api/v1/billing/subscription",
            "/api/v1/billing/usage",
            "/api/v1/billing/payments",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} should require authentication"
            assert "API key required" in response.json()["detail"]

    def test_empty_auth_header_rejected(self):
        """Should reject requests with empty authentication headers."""
        response = self.client.get(
            "/api/v1/billing/subscription",
            headers={"X-API-Key": ""}
        )
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_bearer_without_token_rejected(self):
        """Should reject 'Bearer' header without actual token."""
        response = self.client.get(
            "/api/v1/billing/subscription",
            headers={"Authorization": "Bearer   "}
        )
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]
