"""Tests for core data models."""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from servbot.core.models import Verification, EmailMessage, EmailAccount


class TestModels(unittest.TestCase):
    """Test cases for data models."""

    def test_verification_init(self):
        """Test Verification model initialization."""
        v = Verification(
            service="GitHub",
            code="123456",
            subject="Verification Code",
            from_addr="noreply@github.com",
            date="2025-01-01",
            is_link=False
        )
        
        self.assertEqual(v.service, "GitHub")
        self.assertEqual(v.code, "123456")
        self.assertEqual(v.subject, "Verification Code")
        self.assertEqual(v.from_addr, "noreply@github.com")
        self.assertEqual(v.date, "2025-01-01")
        self.assertFalse(v.is_link)

    def test_verification_subject_property(self):
        """Test subject property."""
        v = Verification("Service", "code", subject="Test Subject")
        self.assertEqual(v.subject, "Test Subject")

    def test_verification_as_pair(self):
        """Test as_pair method."""
        v = Verification("GitHub", "123456")
        pair = v.as_pair()
        
        self.assertIsInstance(pair, str)
        self.assertEqual(pair, "<GitHub, 123456>")

    def test_email_message_init(self):
        """Test EmailMessage initialization."""
        msg = EmailMessage(
            message_id="123",
            provider="imap",
            mailbox="test@example.com",
            subject="Test",
            from_addr="sender@example.com",
            received_date="2025-01-01",
            body_text="Hello",
            body_html="<p>Hello</p>",
            is_read=False
        )
        
        self.assertEqual(msg.message_id, "123")
        self.assertEqual(msg.provider, "imap")
        self.assertEqual(msg.mailbox, "test@example.com")
        self.assertEqual(msg.subject, "Test")
        self.assertFalse(msg.is_read)

    def test_email_account_init(self):
        """Test EmailAccount initialization."""
        acc = EmailAccount(
            email="test@example.com",
            password="password123",
            account_type="outlook",
            source="flashmail",
            imap_server="imap.test.com",
            card="test_card"
        )
        
        self.assertEqual(acc.email, "test@example.com")
        self.assertEqual(acc.password, "password123")
        self.assertEqual(acc.account_type, "outlook")
        self.assertEqual(acc.source, "flashmail")
        self.assertEqual(acc.imap_server, "imap.test.com")
        self.assertEqual(acc.card, "test_card")

    def test_email_account_default_fields(self):
        """Test EmailAccount with default fields."""
        acc = EmailAccount(
            email="test@example.com",
            password="pass"
        )
        
        self.assertEqual(acc.email, "test@example.com")
        self.assertEqual(acc.password, "pass")
        self.assertEqual(acc.account_type, "other")  # default value
        self.assertEqual(acc.source, "manual")  # default value
        self.assertIsNone(acc.imap_server)
        self.assertIsNone(acc.card)


if __name__ == "__main__":
    unittest.main()

