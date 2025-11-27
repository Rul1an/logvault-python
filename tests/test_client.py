"""
Tests for LogVault Python SDK Client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from logvault import Client, AsyncClient
from logvault.exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError
)


class TestClientInitialization:
    """Test client initialization"""

    def test_valid_api_key_live(self):
        """Test initialization with valid live API key"""
        client = Client("lv_live_abc123")
        assert client.api_key == "lv_live_abc123"
        assert client.base_url == "https://api.logvault.io"

    def test_valid_api_key_test(self):
        """Test initialization with valid test API key"""
        client = Client("lv_test_abc123")
        assert client.api_key == "lv_test_abc123"

    def test_missing_api_key(self):
        """Test initialization fails without API key"""
        with pytest.raises(AuthenticationError, match="API key is required"):
            Client("")

    def test_invalid_api_key_format(self):
        """Test initialization fails with invalid format"""
        with pytest.raises(AuthenticationError, match="must start with"):
            Client("invalid_key")

    def test_custom_base_url(self):
        """Test custom base URL"""
        client = Client("lv_test_abc123", base_url="https://custom.example.com")
        assert client.base_url == "https://custom.example.com"

    def test_base_url_trailing_slash_removed(self):
        """Test trailing slash is removed from base URL"""
        client = Client("lv_test_abc123", base_url="https://example.com/")
        assert client.base_url == "https://example.com"

    def test_custom_timeout(self):
        """Test custom timeout"""
        client = Client("lv_test_abc123", timeout=10)
        assert client.timeout == 10

    def test_enable_nonce(self):
        """Test nonce can be enabled"""
        client = Client("lv_test_abc123", enable_nonce=True)
        assert client.enable_nonce is True


class TestLogMethod:
    """Test client.log() method"""

    @patch('requests.Session.post')
    def test_log_minimal(self, mock_post):
        """Test logging with minimal parameters"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "event_123",
            "signature": "abc123"
        }
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")
        result = client.log(
            action="user.login",
            user_id="user_123"
        )

        assert result["id"] == "event_123"
        mock_post.assert_called_once()

        # Check payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']  # Already a dict, not JSON string
        assert payload["action"] == "user.login"
        assert payload["user_id"] == "user_123"
        assert payload["resource"] == "app"  # Default

    @patch('requests.Session.post')
    def test_log_with_metadata(self, mock_post):
        """Test logging with metadata"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "event_123"}
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")
        client.log(
            action="user.login",
            user_id="user_123",
            metadata={"ip": "1.2.3.4", "browser": "Chrome"}
        )

        # Check metadata in payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload["metadata"]["ip"] == "1.2.3.4"
        assert payload["metadata"]["browser"] == "Chrome"

    @patch('requests.Session.post')
    def test_log_with_custom_resource(self, mock_post):
        """Test logging with custom resource"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "event_123"}
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")
        client.log(
            action="document.delete",
            user_id="user_123",
            resource="document:456"
        )

        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload["resource"] == "document:456"

    @patch('requests.Session.post')
    def test_log_with_timestamp(self, mock_post):
        """Test logging with custom timestamp"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "event_123"}
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        client.log(
            action="user.login",
            user_id="user_123",
            timestamp=timestamp
        )

        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert "timestamp" in payload
        assert "2025-01-01" in payload["timestamp"]

    @patch('requests.Session.post')
    def test_log_with_nonce(self, mock_post):
        """Test logging with nonce enabled"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "event_123"}
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123", enable_nonce=True)
        client.log(action="user.login", user_id="user_123")

        # Check nonce header
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        assert 'X-Nonce' in headers
        assert len(headers['X-Nonce']) > 0


class TestErrorHandling:
    """Test error handling"""

    @patch('requests.Session.post')
    def test_authentication_error(self, mock_post):
        """Test 401 raises AuthenticationError"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")

        with pytest.raises(AuthenticationError, match="Invalid API key"):
            client.log(action="user.login", user_id="user_123")

    @patch('requests.Session.post')
    def test_rate_limit_error(self, mock_post):
        """Test 429 raises RateLimitError"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {'Retry-After': '60'}
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")

        with pytest.raises(RateLimitError) as exc_info:
            client.log(action="user.login", user_id="user_123")

        assert exc_info.value.retry_after == 60

    @patch('requests.Session.post')
    def test_validation_error(self, mock_post):
        """Test 422 raises ValidationError"""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.text = "Invalid action format"
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")

        with pytest.raises(ValidationError, match="Validation error"):
            client.log(action="user.login", user_id="user_123")

    @patch('requests.Session.post')
    def test_api_error(self, mock_post):
        """Test 500 raises APIError"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.json.return_value = {"error": "Server error"}
        mock_response.content = b'{"error": "Server error"}'
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")

        with pytest.raises(APIError) as exc_info:
            client.log(action="user.login", user_id="user_123")

        assert exc_info.value.status_code == 500

    @patch('requests.Session.post')
    def test_timeout_error(self, mock_post):
        """Test timeout raises APIError"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("timeout")

        client = Client("lv_test_abc123", timeout=1)

        with pytest.raises(APIError, match="timeout"):
            client.log(action="user.login", user_id="user_123")


class TestListEventsMethod:
    """Test client.list_events() method"""

    @patch('requests.Session.get')
    def test_list_events_default(self, mock_get):
        """Test listing events with defaults"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
            "has_next": False
        }
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        result = client.list_events()

        assert result["total"] == 0
        assert result["page"] == 1
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_list_events_with_filters(self, mock_get):
        """Test listing events with filters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
            "has_next": False
        }
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        client.list_events(user_id="user_123", action="user.login")

        # Check query params
        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params['user_id'] == "user_123"
        assert params['action'] == "user.login"

    @patch('requests.Session.get')
    def test_list_events_pagination(self, mock_get):
        """Test listing events with pagination"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [],
            "total": 100,
            "page": 2,
            "page_size": 25,
            "has_next": True
        }
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        result = client.list_events(page=2, page_size=25)

        assert result["page"] == 2
        assert result["page_size"] == 25
        assert result["has_next"] is True


class TestContextManager:
    """Test context manager support"""

    def test_context_manager(self):
        """Test client can be used as context manager"""
        with Client("lv_test_abc123") as client:
            assert isinstance(client, Client)

        # Session should be closed after exit
        # (Hard to test without mocking)

    def test_context_manager_with_exception(self):
        """Test context manager cleanup on exception"""
        try:
            with Client("lv_test_abc123") as client:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should not raise during cleanup


class TestAsyncClient:
    """Test async client"""

    def test_async_client_initialization(self):
        """Test async client initialization"""
        client = AsyncClient("lv_test_abc123")
        assert client.api_key == "lv_test_abc123"

    def test_async_client_missing_api_key(self):
        """Test async client fails without API key"""
        with pytest.raises(AuthenticationError):
            AsyncClient("")

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager"""
        async with AsyncClient("lv_test_abc123") as client:
            assert isinstance(client, AsyncClient)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
