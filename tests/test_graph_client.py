"""Tests for Microsoft Graph API client."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from servbot.clients.graph import GraphClient
from servbot.core.models import EmailMessage


class TestGraphClient(unittest.TestCase):
    """Test cases for GraphClient."""

    def test_init(self):
        """Test GraphClient initialization."""
        client = GraphClient("test_token", "refresh_token", "client_id")
        self.assertEqual(client.access_token, "test_token")
        self.assertEqual(client.refresh_token, "refresh_token")
        self.assertEqual(client.client_id, "client_id")

    @patch('servbot.clients.graph.requests')
    def test_fetch_messages_success(self, mock_requests):
        """Test successful message fetching."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "msg1",
                    "subject": "Test Subject",
                    "from": {
                        "emailAddress": {
                            "address": "test@example.com"
                        }
                    },
                    "body": {
                        "content": "<p>Test body</p>",
                        "contentType": "html"
                    },
                    "bodyPreview": "Test body",
                    "receivedDateTime": "2025-01-01T12:00:00Z",
                    "isRead": False
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        client = GraphClient("test_token")
        messages = client.fetch_messages()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].subject, "Test Subject")
        self.assertEqual(messages[0].from_addr, "test@example.com")
        self.assertEqual(messages[0].provider, "graph")

    @patch('servbot.clients.graph.requests')
    def test_fetch_messages_empty(self, mock_requests):
        """Test fetching when no messages exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        client = GraphClient("test_token")
        messages = client.fetch_messages()

        self.assertEqual(len(messages), 0)

    @patch('servbot.clients.graph.requests')
    def test_fetch_messages_error(self, mock_requests):
        """Test error handling in fetch_messages."""
        mock_requests.get.side_effect = Exception("Network error")

        client = GraphClient("test_token")
        messages = client.fetch_messages()

        self.assertEqual(len(messages), 0)

    @patch('servbot.clients.graph.requests')
    def test_mark_as_read_success(self, mock_requests):
        """Test marking message as read."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_requests.patch.return_value = mock_response

        client = GraphClient("test_token")
        result = client.mark_as_read("msg_id")

        self.assertTrue(result)

    @patch('servbot.clients.graph.requests')
    def test_mark_as_read_failure(self, mock_requests):
        """Test failure in marking message as read."""
        mock_requests.patch.side_effect = Exception("Error")

        client = GraphClient("test_token")
        result = client.mark_as_read("msg_id")

        self.assertFalse(result)

    @patch('servbot.clients.graph.requests')
    def test_refresh_access_token_success(self, mock_requests):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_token"}
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        client = GraphClient("old_token", "refresh_token", "client_id")
        new_token = client.refresh_access_token()

        self.assertEqual(new_token, "new_token")
        self.assertEqual(client.access_token, "new_token")

    @patch('servbot.clients.graph.requests')
    def test_refresh_access_token_no_credentials(self, mock_requests):
        """Test token refresh without credentials."""
        client = GraphClient("token")  # No refresh token or client_id
        result = client.refresh_access_token()

        self.assertIsNone(result)
        mock_requests.post.assert_not_called()

    @patch('servbot.clients.graph.requests')
    def test_from_credentials_success(self, mock_requests):
        """Test creating client from credentials."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "access_token"}
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        client = GraphClient.from_credentials("refresh_token", "client_id")

        self.assertIsNotNone(client)
        self.assertEqual(client.access_token, "access_token")

    @patch('servbot.clients.graph.requests')
    def test_from_credentials_failure(self, mock_requests):
        """Test creating client with invalid credentials."""
        mock_requests.post.side_effect = Exception("Auth error")

        client = GraphClient.from_credentials("bad_token", "client_id")

        self.assertIsNone(client)


if __name__ == "__main__":
    unittest.main()

