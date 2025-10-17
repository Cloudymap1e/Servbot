"""Tests for core verification logic."""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from servbot.core.verification import (
    _process_email_for_verifications,
    _deduplicate_verifications,
)
from servbot.core.models import EmailMessage, Verification


class TestVerification(unittest.TestCase):
    """Test cases for verification logic."""

    def test_process_email_with_code(self):
        """Test processing email with verification code."""
        msg = EmailMessage(
            message_id="1",
            provider="test",
            mailbox="test@example.com",
            subject="Your verification code",
            from_addr="security@github.com",
            received_date="2025-01-01",
            body_text="Your code is: 123456",
            body_html="",
            is_read=False
        )
        
        verifications = _process_email_for_verifications(msg, use_ai=False)
        
        self.assertGreater(len(verifications), 0)
        self.assertEqual(verifications[0].code, "123456")
        self.assertEqual(verifications[0].service, "GitHub")

    def test_process_email_with_link(self):
        """Test processing email with verification link."""
        msg = EmailMessage(
            message_id="2",
            provider="test",
            mailbox="test@example.com",
            subject="Verify your email",
            from_addr="support@service.com",
            received_date="2025-01-01",
            body_text="Click here to verify: https://service.com/verify?token=abc123",
            body_html="",
            is_read=False
        )
        
        verifications = _process_email_for_verifications(msg, use_ai=False)
        
        # Should find the verification link
        link_verifications = [v for v in verifications if v.is_link]
        self.assertGreater(len(link_verifications), 0)

    def test_process_email_no_verification(self):
        """Test processing email without verification."""
        msg = EmailMessage(
            message_id="3",
            provider="test",
            mailbox="test@example.com",
            subject="Newsletter",
            from_addr="news@example.com",
            received_date="2025-01-01",
            body_text="Just a regular newsletter",
            body_html="",
            is_read=False
        )
        
        verifications = _process_email_for_verifications(msg, use_ai=False)
        
        self.assertEqual(len(verifications), 0)

    def test_deduplicate_verifications(self):
        """Test deduplication of verifications."""
        v1 = Verification("Service", "123456", date="2025-01-01T10:00:00")
        v2 = Verification("Service", "123456", date="2025-01-01T09:00:00")  # Duplicate
        v3 = Verification("Service", "654321", date="2025-01-01T11:00:00")  # Different code
        v4 = Verification("OtherService", "123456", date="2025-01-01T12:00:00")  # Different service
        
        verifications = [v1, v2, v3, v4]
        deduplicated = _deduplicate_verifications(verifications)
        
        # Should have 3 unique items (v1/v2 are duplicates, only keep the newer one)
        self.assertEqual(len(deduplicated), 3)
        
        # Check that items are sorted by date (newest first)
        self.assertEqual(deduplicated[0].service, "OtherService")

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        result = _deduplicate_verifications([])
        self.assertEqual(len(result), 0)

    def test_deduplicate_single_item(self):
        """Test deduplication with single item."""
        v = Verification("Service", "123456")
        result = _deduplicate_verifications([v])
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()

