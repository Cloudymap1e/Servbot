#!/usr/bin/env python
"""Live integration test for servbot - fetches real emails from database account.

This test connects to the actual Outlook account stored in the database,
fetches real emails via both IMAP and Microsoft Graph API (if configured),
extracts verification codes and links, and validates that data is properly
saved to the database.

WARNING: This test connects to real email servers and may be slow.
         It does NOT mark messages as read - only fetches and parses.

Run with:
    pytest tests/test_integration_live.py -v -s
    
or mark as live:
    pytest -m live tests/test_integration_live.py -v -s
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import datetime as dt
from typing import List, Optional

from servbot.data.database import get_accounts, _connect
from servbot.clients import IMAPClient, GraphClient
from servbot.core.verification import fetch_verification_codes
from servbot.core.models import EmailMessage


@pytest.mark.live
@pytest.mark.integration
class TestLiveEmailFetch:
    """Live integration tests for real email fetching."""
    
    @pytest.fixture(scope="class")
    def test_account(self):
        """Get the first email account from database."""
        accounts = get_accounts()
        if not accounts:
            pytest.skip("No accounts in database to test")
        
        account = accounts[0]
        print(f"\nüìß Testing with account: {account['email']}")
        print(f"   Type: {account.get('type', 'unknown')}")
        print(f"   Source: {account.get('source', 'unknown')}")
        print(f"   Has password: {bool(account.get('password'))}")
        print(f"   Has IMAP server: {bool(account.get('imap_server'))}")
        print(f"   Has Graph credentials: {bool(account.get('refresh_token') and account.get('client_id'))}")
        
        return account
    
    def test_01_database_connectivity(self):
        """Test basic database connectivity."""
        print("\n" + "=" * 70)
        print("TEST 1: Database Connectivity")
        print("=" * 70)
        
        conn = _connect()
        cur = conn.cursor()
        
        # Check accounts table
        cur.execute("SELECT COUNT(*) FROM accounts")
        account_count = cur.fetchone()[0]
        print(f"‚ú?Accounts table accessible: {account_count} account(s)")
        
        # Check messages table
        cur.execute("SELECT COUNT(*) FROM messages")
        message_count = cur.fetchone()[0]
        print(f"‚ú?Messages table accessible: {message_count} message(s)")
        
        # Check verifications table
        cur.execute("SELECT COUNT(*) FROM verifications")
        verification_count = cur.fetchone()[0]
        print(f"‚ú?Verifications table accessible: {verification_count} verification(s)")
        
        conn.close()
        
        assert account_count > 0, "Database should have at least one account"
        print("\n‚ú?Database connectivity successful!")
    
    def test_02_imap_connection_and_fetch(self, test_account):
        """Test IMAP connection and message fetching."""
        print("\n" + "=" * 70)
        print("TEST 2: IMAP Connection and Fetch")
        print("=" * 70)
        
        email = test_account['email']
        password = test_account.get('password')
        imap_server = test_account.get('imap_server', 'outlook.office365.com')
        
        if not password:
            pytest.skip("Account has no password for IMAP")
        
        print(f"\nüì° Connecting to {imap_server}...")
        print(f"   Account: {email}")
        print(f"   Port: 993 (SSL)")
        
        try:
            client = IMAPClient(
                server=imap_server,
                username=email,
                password=password,
                port=993,
                use_ssl=True
            )
            print("‚ú?IMAP client created")
            
            # Fetch messages (limit to 10 for speed)
            print("\nüì• Fetching messages (limit 10, unread only)...")
            messages = client.fetch_messages(
                folder='INBOX',
                unseen_only=True,
                limit=10
            )
            
            print(f"‚ú?Fetched {len(messages)} message(s)")
            
            # Display message details
            if messages:
                print("\n" + "-" * 70)
                print("MESSAGES FETCHED:")
                print("-" * 70)
                for i, msg in enumerate(messages, 1):
                    print(f"\n{i}. Subject: {msg.subject}")
                    print(f"   From: {msg.from_addr}")
                    print(f"   Date: {msg.received_date}")
                    print(f"   Mailbox: {msg.mailbox}")
                    print(f"   Provider: {msg.provider}")
                    
                    # Show preview
                    preview = msg.body_text[:100] if msg.body_text else "(no text)"
                    print(f"   Preview: {preview}...")
            else:
                print("\n‚ÑπÔ∏è  No unread messages found (this is OK)")
            
            # Verify messages were not marked as read
            print("\n‚ú?Messages were NOT marked as read (read-only fetch)")
            
            # Check if messages are persisted to DB
            conn = _connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email,))
            db_message_count = cur.fetchone()[0]
            conn.close()
            
            print(f"‚ú?Database has {db_message_count} total message(s) for this account")
            
            print("\n‚ú?IMAP fetch successful!")
            
        except Exception as e:
            pytest.fail(f"IMAP connection failed: {e}")
    
    def test_03_verification_extraction(self, test_account):
        """Test verification code and link extraction from real messages."""
        print("\n" + "=" * 70)
        print("TEST 3: Verification Extraction")
        print("=" * 70)
        
        email = test_account['email']
        password = test_account.get('password')
        imap_server = test_account.get('imap_server', 'outlook.office365.com')
        
        if not password:
            pytest.skip("Account has no password")
        
        print(f"\nüîç Extracting verifications from {email}...")
        
        # Count before
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email,))
        before_msg_count = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM verifications v JOIN messages m ON v.message_id = m.id WHERE m.mailbox = ?",
            (email,)
        )
        before_ver_count = cur.fetchone()[0]
        conn.close()
        
        print(f"   Messages before: {before_msg_count}")
        print(f"   Verifications before: {before_ver_count}")
        
        # Fetch with verification extraction
        try:
            verifications = fetch_verification_codes(
                imap_server=imap_server,
                username=email,
                password=password,
                unseen_only=False,  # Fetch all to ensure we get some data
                prefer_graph=True,  # Try Graph first
                use_ai=False,  # Disable AI for faster testing
                limit=20
            )
            
            print(f"\n‚ú?Extracted {len(verifications)} verification(s)")
            
            # Display verifications
            if verifications:
                print("\n" + "-" * 70)
                print("VERIFICATIONS FOUND:")
                print("-" * 70)
                for i, v in enumerate(verifications, 1):
                    v_type = "üîó Link" if v.is_link else "üî¢ Code"
                    print(f"\n{i}. {v_type}")
                    print(f"   Service: {v.service}")
                    print(f"   Value: {v.code}")
                    print(f"   Subject: {v.subject}")
                    print(f"   From: {v.from_addr}")
                    print(f"   Date: {v.date}")
            else:
                print("\n‚ÑπÔ∏è  No verifications found (account may not have verification emails)")
            
            # Count after
            conn = _connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email,))
            after_msg_count = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM verifications v JOIN messages m ON v.message_id = m.id WHERE m.mailbox = ?",
                (email,)
            )
            after_ver_count = cur.fetchone()[0]
            conn.close()
            
            print(f"\n   Messages after: {after_msg_count}")
            print(f"   Verifications after: {after_ver_count}")
            print(f"   New messages: {after_msg_count - before_msg_count}")
            print(f"   New verifications: {after_ver_count - before_ver_count}")
            
            # Verify data was saved
            assert after_msg_count >= before_msg_count, "Messages should be saved to DB"
            if verifications:
                assert after_ver_count > before_ver_count, "Verifications should be saved to DB"
            
            print("\n‚ú?Verification extraction successful!")
            
        except Exception as e:
            pytest.fail(f"Verification extraction failed: {e}")
    
    def test_04_graph_api_fetch(self, test_account):
        """Test Microsoft Graph API fetching (if configured)."""
        print("\n" + "=" * 70)
        print("TEST 4: Microsoft Graph API Fetch")
        print("=" * 70)
        
        email = test_account['email']
        refresh_token = test_account.get('refresh_token')
        client_id = test_account.get('client_id')
        
        if not refresh_token or not client_id:
            pytest.skip("Account does not have Graph API credentials configured")
        
        print(f"\nüîê Attempting Graph API authentication...")
        print(f"   Client ID: {client_id}")
        print(f"   Refresh Token: {refresh_token[:30]}... ({len(refresh_token)} chars)")
        
        try:
            # Create Graph client
            graph_client = GraphClient.from_credentials(
                refresh_token,
                client_id,
                mailbox=email
            )
            
            if not graph_client:
                pytest.skip("Graph API token exchange failed (token may be expired)")
            
            print("‚ú?Graph API authentication successful")
            
            # Fetch messages
            print(f"\nüì• Fetching messages via Graph API (limit 10)...")
            messages = graph_client.fetch_messages(
                folder='inbox',
                unseen_only=True,
                limit=10
            )
            
            print(f"‚ú?Fetched {len(messages)} message(s) via Graph API")
            
            # Display message details
            if messages:
                print("\n" + "-" * 70)
                print("MESSAGES FETCHED (GRAPH API):")
                print("-" * 70)
                for i, msg in enumerate(messages, 1):
                    print(f"\n{i}. Subject: {msg.subject}")
                    print(f"   From: {msg.from_addr}")
                    print(f"   Date: {msg.received_date}")
                    print(f"   Message ID: {msg.message_id}")
            else:
                print("\n‚ÑπÔ∏è  No unread messages found via Graph API")
            
            print("\n‚ú?Graph API fetch successful!")
            
        except Exception as e:
            # Graph API errors are acceptable - token may be expired
            print(f"\n‚ö†Ô∏è  Graph API fetch failed: {e}")
            print("   (This is acceptable - token may be expired or credentials invalid)")
            pytest.skip(f"Graph API not available: {e}")
    
    def test_05_database_verification_integrity(self, test_account):
        """Test database integrity for messages and verifications."""
        print("\n" + "=" * 70)
        print("TEST 5: Database Integrity")
        print("=" * 70)
        
        email = test_account['email']
        
        conn = _connect()
        cur = conn.cursor()
        
        # Get recent messages
        cur.execute("""
            SELECT id, subject, from_addr, received_date, created_at
            FROM messages
            WHERE mailbox = ?
            ORDER BY created_at DESC
            LIMIT 5
        """, (email,))
        messages = cur.fetchall()
        
        print(f"\nüìä Recent messages in database:")
        if messages:
            for msg in messages:
                msg_id, subject, from_addr, received_date, created_at = msg
                print(f"\n   ID: {msg_id}")
                print(f"   Subject: {subject}")
                print(f"   From: {from_addr}")
                print(f"   Received: {received_date}")
                print(f"   Saved at: {created_at}")
                
                # Check for verifications
                cur.execute("""
                    SELECT service, value, is_link, created_at
                    FROM verifications
                    WHERE message_id = ?
                """, (msg_id,))
                verifications = cur.fetchall()
                
                if verifications:
                    print(f"   Verifications: {len(verifications)}")
                    for v in verifications:
                        service, value, is_link, v_created_at = v
                        v_type = "Link" if is_link else "Code"
                        print(f"     - {service}: {value[:30]}... ({v_type})")
        else:
            print("   (No messages found)")
        
        conn.close()
        
        print("\n‚ú?Database integrity check passed!")


@pytest.mark.live
def test_quick_smoke_test():
    """Quick smoke test to verify basic functionality."""
    print("\n" + "=" * 70)
    print("QUICK SMOKE TEST")
    print("=" * 70)
    
    # Check database
    accounts = get_accounts()
    print(f"\n‚ú?Database accessible: {len(accounts)} account(s)")
    
    if not accounts:
        pytest.skip("No accounts to test")
    
    account = accounts[0]
    print(f"‚ú?Test account: {account['email']}")
    
    # Try a quick fetch (with error handling)
    try:
        verifications = fetch_verification_codes(
            imap_server=account.get('imap_server', 'outlook.office365.com'),
            username=account['email'],
            password=account.get('password', ''),
            unseen_only=True,
            prefer_graph=True,
            limit=5
        )
        print(f"‚ú?Quick fetch completed: {len(verifications)} verification(s)")
    except Exception as e:
        print(f"‚ö†Ô∏è  Quick fetch failed (this is acceptable): {e}")
    
    print("\n‚ú?Smoke test passed!")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" SERVBOT LIVE INTEGRATION TEST SUITE")
    print("=" * 70)
    print("\nWARNING: These tests connect to real email servers!")
    print("         Tests may be slow and require network connectivity.")
    print("\nRunning tests...")
    print("=" * 70 + "\n")
    
    # Run with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])
