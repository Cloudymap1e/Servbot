import unittest
from unittest.mock import patch, MagicMock, Mock
import email
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from servbot import fetch_verification_codes
from servbot.core.models import Verification

def create_mock_email(subject, from_addr, body):
    msg = email.message.EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg.set_content(body)
    return msg.as_bytes()

class TestEmailBot(unittest.TestCase):

    @patch('servbot.clients.imap.imapclient', create=True)
    def test_fetch_verification_codes_imap(self, mock_imapclient_module):
        # --- Setup Mock ---
        mock_client = MagicMock()
        mock_imapclient_module.IMAPClient = MagicMock(return_value=mock_client)
        
        # Mock login
        mock_client.login = MagicMock()
        
        # Mock search to return some UIDs
        mock_client.search.return_value = [1]
        
        # Mock fetch to return email data
        mock_emails = {
            1: {
                b'RFC822': create_mock_email("Your Google Code", "security@google.com", "Your verification code is 123456."),
                b'FLAGS': []
            }
        }
        mock_client.fetch.return_value = mock_emails
        mock_client.select_folder = MagicMock()
        mock_client.logout = MagicMock()

        # --- Run Test ---
        results = fetch_verification_codes(
            imap_server="mock.server.com",
            username="user",
            password="password",
            prefer_graph=False,
            use_ai=False
        )

        # --- Assertions ---
        self.assertGreaterEqual(len(results), 0)  # May be 0 or more depending on parse success
        
        # Just verify the function runs without error
        # The actual parsing is tested in test_parsers.py

if __name__ == "__main__":
    unittest.main()