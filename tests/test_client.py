"""
Tests for LogVault Python SDK Client
Updated November 2025 to match current implementation
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
        assert client.base_url == "https://api.logvault.eu"

    def test_valid_api_key_test(self):
        """Test initialization with valid test API key"""
        client = Client("lv_test_abc123")
        assert client.api_key == "lv_test_abc123"

    def test_invalid_api_key_format_warns(self):
        """Test initialization with invalid format logs warning but doesn't crash"""
        # Current implementation logs warning but doesn't raise
        client = Client("invalid_key")
        assert client.api_key == "invalid_key"

    def test_custom_base_url(self):
        """Test custom base URL"""
        client = Client("lv_test_abc123", base_url="https://custom.example.com")
        assert client.base_url == "https://custom.example.com"

    def test_base_url_trailing_slash_removed(self):
        """Test trailing slash is removed from base URL"""
        client = Client("lv_test_abc123", base_url="https://example.com/")
        assert client.base_url == "https://example.com"

    def test_custom_timeout(self):
        """Test custom timeout as tuple"""
        client = Client("lv_test_abc123", timeout=(3.0, 5.0))
        assert client.timeout == (3.0, 5.0)

    def test_default_timeout(self):
        """Test default timeout values"""
        client = Client("lv_test_abc123")
        assert client.timeout == (5.0, 10.0)

    def test_max_retries(self):
        """Test max retries configuration"""
        client = Client("lv_test_abc123", max_retries=5)
        # Retries are configured in the session adapter


class TestLogMethod:
    """Test client.log() method"""

    @patch('requests.Session.post')
    def test_log_minimal(self, mock_post):
        """Test logging with minimal parameters"""
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

        # Check payload - uses 'data' not 'json' (pre-serialized)
        call_args = mock_post.call_args
        data = call_args[1]['data']
        payload = json.loads(data)
        assert payload["action"] == "user.login"
        assert payload["user_id"] == "user_123"

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

        call_args = mock_post.call_args
        data = call_args[1]['data']
        payload = json.loads(data)
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
        data = call_args[1]['data']
        payload = json.loads(data)
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
        data = call_args[1]['data']
        payload = json.loads(data)
        assert payload["timestamp"] == "2025-01-01T12:00:00"

    def test_log_invalid_action_format(self):
        """Test logging with invalid action format raises ValidationError"""
        client = Client("lv_test_abc123")
        
        with pytest.raises(ValidationError, match="Invalid action format"):
            client.log(action="invalid", user_id="user_123")

    def test_log_valid_action_formats(self):
        """Test various valid action formats"""
        client = Client("lv_test_abc123")
        
        # These should not raise ValidationError (would fail on network)
        valid_actions = [
            "user.login",
            "auth.login.success",
            "document.create",
            "payment.transaction.completed",
        ]
        
        for action in valid_actions:
            # Just check validation passes (will fail on network call)
            try:
                client.log(action=action, user_id="test")
            except (APIError, ConnectionError):
                pass  # Expected - no actual API


class TestErrorHandling:
    """Test error handling"""

    @patch('requests.Session.post')
    def test_authentication_error(self, mock_post):
        """Test 401 raises AuthenticationError"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")

        with pytest.raises(AuthenticationError, match="Invalid API key"):
            client.log(action="user.login", user_id="user_123")

    @patch('requests.Session.post')
    def test_validation_error(self, mock_post):
        """Test 422 raises ValidationError"""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.text = "Invalid action format"
        mock_post.return_value = mock_response

        client = Client("lv_test_abc123")

        with pytest.raises(ValidationError, match="Validation failed"):
            client.log(action="user.login", user_id="user_123")

    @patch('requests.Session.post')
    def test_timeout_error(self, mock_post):
        """Test timeout raises APIError"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("timeout")

        client = Client("lv_test_abc123", timeout=(1, 1))

        with pytest.raises(APIError, match="Connection Error"):
            client.log(action="user.login", user_id="user_123")

    @patch('requests.Session.post')
    def test_connection_error(self, mock_post):
        """Test connection error raises APIError"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        client = Client("lv_test_abc123")

        with pytest.raises(APIError, match="Connection Error"):
            client.log(action="user.login", user_id="user_123")


class TestListEventsMethod:
    """Test client.list_events() method"""

    @patch('requests.Session.get')
    def test_list_events_default(self, mock_get):
        """Test listing events with default parameters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [{"id": "event_1"}, {"id": "event_2"}],
            "total": 2,
            "page": 1,
            "page_size": 50,
            "has_next": False
        }
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        result = client.list_events()

        assert len(result["events"]) == 2
        assert result["total"] == 2
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_list_events_with_filters(self, mock_get):
        """Test listing events with filters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [{"id": "event_1"}],
            "total": 1,
            "page": 1,
            "page_size": 50,
            "has_next": False
        }
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        result = client.list_events(user_id="user_123", action="user.login")

        assert len(result["events"]) == 1
        
        # Check query params
        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params["user_id"] == "user_123"
        assert params["action"] == "user.login"

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

        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params["page"] == 2
        assert params["page_size"] == 25

    @patch('requests.Session.get')
    def test_list_events_max_page_size(self, mock_get):
        """Test page_size is capped at 100"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": [], "total": 0}
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        client.list_events(page_size=500)

        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params["page_size"] == 100  # Capped


class TestSearchEventsMethod:
    """Test client.search_events() method"""

    @patch('requests.Session.get')
    def test_search_events(self, mock_get):
        """Test searching events"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "event_1", "action": "user.login"}],
            "count": 1,
            "has_embeddings": True
        }
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        result = client.search_events("failed login")

        assert result["count"] == 1
        assert result["has_embeddings"] is True

    def test_search_events_short_query(self):
        """Test search with too short query raises ValidationError"""
        client = Client("lv_test_abc123")
        
        with pytest.raises(ValidationError, match="at least 2 characters"):
            client.search_events("a")


class TestVerifyEventMethod:
    """Test client.verify_event() method"""

    @patch('requests.Session.get')
    def test_verify_event(self, mock_get):
        """Test verifying an event"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valid": True,
            "event_id": "event_123",
            "signature": "abc123"
        }
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")
        result = client.verify_event("event_123")

        assert result["valid"] is True

    @patch('requests.Session.get')
    def test_verify_event_not_found(self, mock_get):
        """Test verifying non-existent event"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = Client("lv_test_abc123")

        with pytest.raises(APIError, match="not found"):
            client.verify_event("nonexistent")


class TestAsyncClient:
    """Test AsyncClient"""

    def test_async_client_initialization(self):
        """Test async client initialization"""
        client = AsyncClient("lv_test_abc123")
        assert client.api_key == "lv_test_abc123"
        assert client.base_url == "https://api.logvault.eu"

    def test_async_client_invalid_key_warns(self):
        """Test async client with invalid key logs warning"""
        # Current implementation logs warning but doesn't raise
        client = AsyncClient("invalid_key")
        assert client.api_key == "invalid_key"

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async client as context manager"""
        async with AsyncClient("lv_test_abc123") as client:
            assert client.api_key == "lv_test_abc123"
            assert client._session is not None
