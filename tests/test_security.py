"""Tests for security: API key hashing, ownership checks, SSRF protection."""

import pytest

from app.security import hash_api_key, validate_audit_url, verify_api_key


class TestApiKeyHashing:
    def test_hash_is_deterministic(self):
        key = "aiqso_seo_test123"
        assert hash_api_key(key) == hash_api_key(key)

    def test_different_keys_different_hashes(self):
        assert hash_api_key("key1") != hash_api_key("key2")

    def test_verify_correct_key(self):
        key = "aiqso_seo_test123"
        hashed = hash_api_key(key)
        assert verify_api_key(key, hashed)

    def test_verify_wrong_key(self):
        hashed = hash_api_key("correct_key")
        assert not verify_api_key("wrong_key", hashed)


class TestSSRFProtection:
    def test_blocks_localhost(self):
        with pytest.raises(ValueError, match="Blocked hostname"):
            validate_audit_url("http://localhost/test")

    def test_blocks_metadata_endpoint(self):
        with pytest.raises(ValueError, match="Blocked hostname"):
            validate_audit_url("http://169.254.169.254/latest/meta-data/")

    def test_blocks_private_ip(self):
        with pytest.raises(ValueError, match="blocked network"):
            validate_audit_url("http://192.168.1.1/test")

    def test_blocks_loopback(self):
        with pytest.raises(ValueError, match="blocked network"):
            validate_audit_url("http://127.0.0.1/test")

    def test_blocks_non_http_scheme(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate_audit_url("file:///etc/passwd")

    def test_blocks_ftp(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate_audit_url("ftp://internal.server/data")

    def test_allows_public_url(self):
        # This should not raise (google.com resolves to public IP)
        result = validate_audit_url("https://www.google.com")
        assert result == "https://www.google.com"


class TestAuthEndpoints:
    def test_unauthenticated_request_rejected(self, client):
        """Requests without API key should be rejected when REQUIRE_API_KEY=true."""
        response = client.get("/api/v1/clients/")
        assert response.status_code == 401

    def test_invalid_api_key_rejected(self, client):
        response = client.get("/api/v1/clients/", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == 401

    def test_valid_api_key_accepted(self, client, auth_headers):
        response = client.get("/api/v1/clients/", headers=auth_headers)
        # Should succeed (200) or return empty list, not 401
        assert response.status_code != 401
