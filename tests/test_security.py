import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, Request

from app.security import require_client, _extract_api_key
from app.models.client import Client, ClientTier


class TestExtractApiKey:
    """Test the _extract_api_key helper function."""

    def test_extract_from_x_api_key(self):
        """Should extract API key from X-API-Key header."""
        api_key = _extract_api_key(authorization=None, x_api_key="test-key-123")
        assert api_key == "test-key-123"

    def test_extract_from_x_api_key_with_whitespace(self):
        """Should strip whitespace from X-API-Key header."""
        api_key = _extract_api_key(authorization=None, x_api_key="  test-key-123  ")
        assert api_key == "test-key-123"

    def test_extract_from_authorization_bearer(self):
        """Should extract API key from Authorization: Bearer header."""
        api_key = _extract_api_key(authorization="Bearer test-key-456", x_api_key=None)
        assert api_key == "test-key-456"

    def test_extract_from_authorization_bearer_case_insensitive(self):
        """Should handle case-insensitive 'Bearer' prefix."""
        api_key = _extract_api_key(authorization="bearer test-key-789", x_api_key=None)
        assert api_key == "test-key-789"

    def test_extract_from_authorization_bearer_mixed_case(self):
        """Should handle mixed case 'Bearer' prefix."""
        api_key = _extract_api_key(authorization="BeArEr test-key-abc", x_api_key=None)
        assert api_key == "test-key-abc"

    def test_extract_from_authorization_with_whitespace(self):
        """Should strip whitespace from Bearer token."""
        api_key = _extract_api_key(authorization="Bearer   test-key-def  ", x_api_key=None)
        assert api_key == "test-key-def"

    def test_prefer_x_api_key_over_authorization(self):
        """Should prefer X-API-Key when both headers are present."""
        api_key = _extract_api_key(
            authorization="Bearer auth-key",
            x_api_key="x-api-key"
        )
        assert api_key == "x-api-key"

    def test_no_headers_returns_none(self):
        """Should return None when no headers are provided."""
        api_key = _extract_api_key(authorization=None, x_api_key=None)
        assert api_key is None

    def test_empty_authorization_returns_none(self):
        """Should return None for empty Authorization header."""
        api_key = _extract_api_key(authorization="", x_api_key=None)
        assert api_key is None

    def test_authorization_without_bearer_returns_none(self):
        """Should return None for Authorization header without Bearer prefix."""
        api_key = _extract_api_key(authorization="Basic dGVzdDp0ZXN0", x_api_key=None)
        assert api_key is None

    def test_bearer_only_returns_none(self):
        """Should return None for 'Bearer' without token."""
        api_key = _extract_api_key(authorization="Bearer", x_api_key=None)
        assert api_key is None

    def test_bearer_with_empty_token_returns_none(self):
        """Should return None for 'Bearer' with empty/whitespace token."""
        api_key = _extract_api_key(authorization="Bearer   ", x_api_key=None)
        assert api_key is None


class TestRequireClient:
    """Test the require_client authentication guard."""

    def _create_mock_request(self):
        """Create a mock FastAPI Request object."""
        mock_request = Mock(spec=Request)
        return mock_request

    def _create_mock_client(self, api_key="valid-key", is_active=True):
        """Create a mock Client object."""
        client = Mock(spec=Client)
        client.id = 1
        client.name = "Test Client"
        client.email = "test@example.com"
        client.api_key = api_key
        client.is_active = is_active
        client.tier = ClientTier.PROFESSIONAL
        return client

    @patch('app.security.SessionLocal')
    def test_valid_api_key_via_x_api_key(self, mock_session_local):
        """Should authenticate successfully with valid X-API-Key header."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_client = self._create_mock_client()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_client

        request = self._create_mock_request()
        result = require_client(
            request=request,
            authorization=None,
            x_api_key="valid-key"
        )

        assert result == mock_client
        mock_db.close.assert_called_once()

    @patch('app.security.SessionLocal')
    def test_valid_api_key_via_authorization_bearer(self, mock_session_local):
        """Should authenticate successfully with valid Authorization: Bearer header."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_client = self._create_mock_client()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_client

        request = self._create_mock_request()
        result = require_client(
            request=request,
            authorization="Bearer valid-key",
            x_api_key=None
        )

        assert result == mock_client
        mock_db.close.assert_called_once()

    @patch('app.security.SessionLocal')
    def test_no_api_key_raises_401(self, mock_session_local):
        """Should raise 401 when no API key is provided."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        request = self._create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            require_client(
                request=request,
                authorization=None,
                x_api_key=None
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "API key required"
        # Database session is not created when API key is missing
        mock_session_local.assert_not_called()

    @patch('app.security.SessionLocal')
    def test_invalid_api_key_raises_401(self, mock_session_local):
        """Should raise 401 when API key does not exist in database."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None  # No client found

        request = self._create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            require_client(
                request=request,
                authorization=None,
                x_api_key="invalid-key"
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"
        mock_db.close.assert_called_once()

    @patch('app.security.SessionLocal')
    def test_inactive_client_raises_401(self, mock_session_local):
        """Should raise 401 when client exists but is not active."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_client = self._create_mock_client(is_active=False)
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_client

        request = self._create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            require_client(
                request=request,
                authorization=None,
                x_api_key="valid-key"
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Client is not active"
        mock_db.close.assert_called_once()

    @patch('app.security.SessionLocal')
    def test_database_closes_on_success(self, mock_session_local):
        """Should close database connection after successful authentication."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_client = self._create_mock_client()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_client

        request = self._create_mock_request()
        require_client(
            request=request,
            authorization=None,
            x_api_key="valid-key"
        )

        mock_db.close.assert_called_once()

    @patch('app.security.SessionLocal')
    def test_database_closes_on_error(self, mock_session_local):
        """Should close database connection even when authentication fails."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        request = self._create_mock_request()

        with pytest.raises(HTTPException):
            require_client(
                request=request,
                authorization=None,
                x_api_key="invalid-key"
            )

        mock_db.close.assert_called_once()

    @patch('app.security.SessionLocal')
    def test_whitespace_in_api_key_is_stripped(self, mock_session_local):
        """Should strip whitespace from API key before database lookup."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_client = self._create_mock_client(api_key="trimmed-key")
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_client

        request = self._create_mock_request()
        result = require_client(
            request=request,
            authorization=None,
            x_api_key="  trimmed-key  "
        )

        assert result == mock_client
        mock_db.close.assert_called_once()

    @patch('app.security.SessionLocal')
    def test_empty_x_api_key_raises_401(self, mock_session_local):
        """Should raise 401 for empty X-API-Key header."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        request = self._create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            require_client(
                request=request,
                authorization=None,
                x_api_key=""
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "API key required"
        # Database session is not created when API key is missing
        mock_session_local.assert_not_called()

    @patch('app.security.SessionLocal')
    def test_empty_authorization_raises_401(self, mock_session_local):
        """Should raise 401 for empty Authorization header."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        request = self._create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            require_client(
                request=request,
                authorization="",
                x_api_key=None
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "API key required"
        # Database session is not created when API key is missing
        mock_session_local.assert_not_called()
