"""Comprehensive end-to-end mock test for servbot.

Tests the complete flow:
1. Provision a new email account
2. Receive verification emails
3. Extract codes and links
4. Verify database storage
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import datetime as dt
from typing import List

import sys
import os

# Add parent directory to path to import servbot as a package
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = parent_dir

# Add grandparent to allow 'import servbot'
if grandparent_dir not in sys.path:
    sys.path.insert(0, grandparent_dir)

# Now we can import servbot
import servbot
from servbot import (
    fetch_verification_codes,
    get_verification_for_service,
    list_database,
    get_account_verifications,
    FlashmailClient,
)
from servbot.core.models import EmailMessage, Verification
from servbot.data.database import upsert_account, save_message, save_verification


class TestCompleteEmailFlow(unittest.TestCase):
    """End-to-end test for email verification flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock account details
        self.test_email = "test_mock_account@outlook.com"
        self.test_password = "MockPassword123!"
        self.test_service = "GitHub"
        self.test_code = "123456"
        self.test_link = "https://github.com/verify?token=abc123xyz"
        
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    def test_01_provision_account_mock(self):
        """Test account provisioning with mocked Flashmail API."""
        print("\n[TEST 1] Testing Account Provisioning (Mocked)")
        print("=" * 60)
        
        # Mock the HTTP response from Flashmail
        mock_response_body = f"{self.test_email}----{self.test_password}"
        
        with patch('servbot.clients.flashmail._http_get') as mock_http:
            # Setup mock response
            mock_http.return_value = (200, mock_response_body, {})
            
            # Create client and fetch accounts
            client = FlashmailClient(card="MOCK_CARD_KEY")
            accounts = client.fetch_accounts(quantity=1, account_type="outlook")
            
            # Assertions
            self.assertEqual(len(accounts), 1, "Should provision exactly 1 account")
            self.assertEqual(accounts[0].email, self.test_email)
            self.assertEqual(accounts[0].password, self.test_password)
            self.assertEqual(accounts[0].source, "flashmail")
            
            print(f"âœ?Provisioned account: {accounts[0].email}")
            print(f"âœ?Password: {accounts[0].password}")
            print(f"âœ?Source: {accounts[0].source}")
    
    def test_02_receive_verification_code(self):
        """Test receiving and extracting verification codes from email."""
        print("\n[TEST 2] Testing Verification Code Extraction")
        print("=" * 60)
        
        # Create mock email message with verification code
        mock_message = EmailMessage(
            mailbox=self.test_email,
            provider="imap",
            message_id="mock_msg_001",
            subject=f"Your {self.test_service} verification code",
            from_addr=f"noreply@{self.test_service.lower()}.com",
            received_date=dt.datetime.now().isoformat(),
            body_text=f"Your verification code is: {self.test_code}\n\nPlease enter this code to verify your account.",
            body_html=f"<p>Your verification code is: <strong>{self.test_code}</strong></p>",
            is_read=False,
        )
        
        # Mock IMAP client to return our message
        with patch('servbot.clients.imap.IMAPClient') as MockIMAPClient:
            mock_client = MockIMAPClient.return_value
            mock_client.fetch_messages.return_value = [mock_message]
            
            # Fetch verification codes
            verifications = fetch_verification_codes(
                imap_server="outlook.office365.com",
                username=self.test_email,
                password=self.test_password,
                prefer_graph=False,  # Force IMAP
                use_ai=False,  # Disable AI for testing
            )
            
            # Assertions
            self.assertGreater(len(verifications), 0, "Should find at least one verification")
            
            # Find the code we sent
            found_code = False
            for v in verifications:
                if self.test_code in v.code:
                    found_code = True
                    self.assertEqual(v.is_link, False, "Should be a code, not a link")
                    self.assertIn(self.test_service.lower(), v.service.lower())
                    print(f"âœ?Found verification code: {v.code}")
                    print(f"âœ?Service identified: {v.service}")
                    print(f"âœ?From: {v.from_addr}")
                    break
            
            self.assertTrue(found_code, f"Should find the test code {self.test_code}")
    
    def test_03_receive_verification_link(self):
        """Test receiving and extracting verification links from email."""
        print("\n[TEST 3] Testing Verification Link Extraction")
        print("=" * 60)
        
        # Create mock email message with verification link
        mock_message = EmailMessage(
            mailbox=self.test_email,
            provider="imap",
            message_id="mock_msg_002",
            subject=f"Verify your {self.test_service} account",
            from_addr=f"verify@{self.test_service.lower()}.com",
            received_date=dt.datetime.now().isoformat(),
            body_text=f"Click here to verify: {self.test_link}",
            body_html=f'<p>Click <a href="{self.test_link}">here</a> to verify your account.</p>',
            is_read=False,
        )
        
        # Mock IMAP client to return our message
        with patch('servbot.clients.imap.IMAPClient') as MockIMAPClient:
            mock_client = MockIMAPClient.return_value
            mock_client.fetch_messages.return_value = [mock_message]
            
            # Fetch verification codes
            verifications = fetch_verification_codes(
                imap_server="outlook.office365.com",
                username=self.test_email,
                password=self.test_password,
                prefer_graph=False,  # Force IMAP
                use_ai=False,  # Disable AI
            )
            
            # Assertions
            self.assertGreater(len(verifications), 0, "Should find at least one verification")
            
            # Find the link we sent
            found_link = False
            for v in verifications:
                if self.test_link in v.code:
                    found_link = True
                    self.assertEqual(v.is_link, True, "Should be a link")
                    print(f"âœ?Found verification link: {v.code}")
                    print(f"âœ?Service identified: {v.service}")
                    break
            
            self.assertTrue(found_link, f"Should find the test link")
    
    def test_04_database_storage(self):
        """Test that verifications are properly stored in database."""
        print("\n[TEST 4] Testing Database Storage")
        print("=" * 60)
        
        test_email_db = "db_test@outlook.com"
        test_service_db = "TestService"
        test_code_db = "999888"
        
        # Insert test account
        account_id = upsert_account(
            email=test_email_db,
            password="TestPass123",
            type="outlook",
            source="manual",
        )
        
        self.assertGreater(account_id, 0, "Account should be created")
        print(f"âœ?Created test account ID: {account_id}")
        
        # Insert test message
        message_id = save_message(
            mailbox=test_email_db,
            provider="imap",
            provider_msg_id="test_db_msg_001",
            subject=f"Your {test_service_db} code",
            from_addr=f"noreply@{test_service_db.lower()}.com",
            body_text=f"Code: {test_code_db}",
            service=test_service_db,
        )
        
        self.assertGreater(message_id, 0, "Message should be saved")
        print(f"âœ?Saved message ID: {message_id}")
        
        # Insert test verification
        verification_id = save_verification(
            message_id=message_id,
            service=test_service_db,
            value=test_code_db,
            is_link=False,
        )
        
        self.assertGreater(verification_id, 0, "Verification should be saved")
        print(f"âœ?Saved verification ID: {verification_id}")
        
        # Retrieve from database
        verifications = get_account_verifications(test_email_db, limit=10)
        
        self.assertGreater(len(verifications), 0, "Should retrieve verifications")
        
        # Verify data integrity
        found = False
        for v in verifications:
            if v['value'] == test_code_db and v['service'] == test_service_db:
                found = True
                self.assertEqual(v['is_link'], 0, "Should be stored as code (0)")
                print(f"âœ?Retrieved verification: {v['service']} = {v['value']}")
                break
        
        self.assertTrue(found, "Should find the verification we just saved")
    
    def test_05_list_database_contents(self):
        """Test listing all database contents."""
        print("\n[TEST 5] Testing Database Listing")
        print("=" * 60)
        
        # Get all database contents
        db_contents = list_database()
        
        # Assertions
        self.assertIn("accounts", db_contents, "Should have accounts key")
        self.assertIn("messages", db_contents, "Should have messages key")
        self.assertIn("verifications", db_contents, "Should have verifications key")
        self.assertIn("summary", db_contents, "Should have summary key")
        
        summary = db_contents['summary']
        print(f"âœ?Total Accounts: {summary.get('total_accounts', 0)}")
        print(f"âœ?Total Messages: {summary.get('total_messages', 0)}")
        print(f"âœ?Total Verifications: {summary.get('total_verifications', 0)}")
        print(f"âœ?Total Graph Accounts: {summary.get('total_graph_accounts', 0)}")
        
        # Show some sample data if available
        if db_contents['accounts']:
            print("\nSample Accounts:")
            for acc in db_contents['accounts'][:3]:
                print(f"  - {acc['email']} ({acc['source']})")
        
        if db_contents['verifications']:
            print("\nRecent Verifications:")
            for v in db_contents['verifications'][:5]:
                v_type = "Link" if v['is_link'] else "Code"
                print(f"  - {v['service']}: {v['value'][:20]}... ({v_type})")
    
    def test_06_poll_for_verification(self):
        """Test polling for verification with timeout."""
        print("\n[TEST 6] Testing Verification Polling")
        print("=" * 60)
        
        target_service = "Discord"
        expected_code = "778899"
        
        # Create mock messages that arrive over time
        messages_sequence = [
            [],  # First poll: no messages
            [],  # Second poll: still no messages
            [   # Third poll: message arrives!
                EmailMessage(
                    mailbox=self.test_email,
                    provider="imap",
                    message_id="mock_msg_poll",
                    subject=f"Your {target_service} verification code",
                    from_addr=f"noreply@{target_service.lower()}.com",
                    received_date=dt.datetime.now().isoformat(),
                    body_text=f"Your code is {expected_code}",
                    body_html=f"<p>Code: {expected_code}</p>",
                    is_read=False,
                )
            ]
        ]
        
        call_count = [0]
        
        def mock_fetch_messages(*args, **kwargs):
            """Returns different messages on each call to simulate polling."""
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(messages_sequence):
                return messages_sequence[idx]
            return []
        
        with patch('servbot.clients.imap.IMAPClient') as MockIMAPClient:
            mock_client = MockIMAPClient.return_value
            mock_client.fetch_messages.side_effect = mock_fetch_messages
            
            # Attempt to get verification with polling
            code = get_verification_for_service(
                target_service=target_service,
                imap_server="outlook.office365.com",
                username=self.test_email,
                password=self.test_password,
                timeout_seconds=15,
                poll_interval_seconds=1,
                prefer_graph=False,
            )
            
            # Assertions
            self.assertIsNotNone(code, "Should eventually find the code")
            self.assertEqual(code, expected_code)
            print(f"âœ?Successfully polled and found code: {code}")
            print(f"âœ?Took {call_count[0]} polling attempts")


class TestFlashmailAPIEndpoints(unittest.TestCase):
    """Test Flashmail API endpoint integration."""
    
    def test_inventory_endpoint(self):
        """Test inventory query endpoint."""
        print("\n[TEST] Testing Flashmail Inventory Endpoint")
        print("=" * 60)
        
        mock_response = '{"hotmail": 150, "outlook": 250}'
        
        with patch('servbot.clients.flashmail._http_get') as mock_http:
            mock_http.return_value = (200, mock_response, {})
            
            client = FlashmailClient(card="MOCK_KEY")
            inventory = client.get_inventory()
            
            self.assertEqual(inventory['hotmail'], 150)
            self.assertEqual(inventory['outlook'], 250)
            print(f"âœ?Hotmail available: {inventory['hotmail']}")
            print(f"âœ?Outlook available: {inventory['outlook']}")
    
    def test_balance_endpoint(self):
        """Test balance query endpoint."""
        print("\n[TEST] Testing Flashmail Balance Endpoint")
        print("=" * 60)
        
        mock_response = '{"num": 42}'
        
        with patch('servbot.clients.flashmail._http_get') as mock_http:
            mock_http.return_value = (200, mock_response, {})
            
            client = FlashmailClient(card="MOCK_KEY")
            balance = client.get_balance()
            
            self.assertEqual(balance, 42)
            print(f"âœ?Account balance: {balance}")


def run_complete_test_suite():
    """Run all tests and display results."""
    print("\n" + "=" * 70)
    print(" SERVBOT COMPREHENSIVE MOCK TEST SUITE")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCompleteEmailFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestFlashmailAPIEndpoints))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\nâœ“âœ“âœ?ALL TESTS PASSED! âœ“âœ“âœ?)
    else:
        print("\nâœ—âœ—âœ?SOME TESTS FAILED âœ—âœ—âœ?)
    
    print("=" * 70 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_complete_test_suite()
    sys.exit(0 if success else 1)

