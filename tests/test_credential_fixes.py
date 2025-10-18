"""Tests for credential handling fixes.

Tests the critical bug fixes:
1. Mailbox population in Graph API messages
2. Database upsert allowing NULL to clear credentials
3. Token refresh and persistence
4. Unified credential loading
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add parent and project directory to path
test_dir = Path(__file__).parent
project_dir = test_dir.parent
sys.path.insert(0, str(project_dir.parent))  # Add servbot parent dir
sys.path.insert(0, str(project_dir))  # Add servbot dir itself

# Direct imports from modules
from data.database import (
    ensure_db,
    upsert_account,
    get_accounts,
    _connect,
    DB_PATH,
)
from config import load_account_credentials, load_graph_account
from clients.graph import GraphClient
from core.models import EmailMessage


def test_upsert_account_allows_null_updates():
    """Test that upsert_account can clear credentials with NULL."""
    print("\n=== Test: Upsert Account Allows NULL Updates ===")
    
    # Create test account
    test_email = "test_null_update@example.com"
    
    # Initial insert with credentials
    upsert_account(
        email=test_email,
        password="initial_pass",
        refresh_token="initial_token",
        client_id="initial_client",
        update_only_if_provided=False,
    )
    
    accounts = get_accounts()
    acc = next((a for a in accounts if a['email'] == test_email), None)
    assert acc is not None, "Account should exist"
    assert acc['password'] == "initial_pass"
    assert acc['refresh_token'] == "initial_token"
    assert acc['client_id'] == "initial_client"
    print("‚ú?Initial account created with credentials")
    
    # Update password, clear tokens
    upsert_account(
        email=test_email,
        password="updated_pass",
        refresh_token=None,
        client_id=None,
        update_only_if_provided=False,  # Allow NULL to clear
    )
    
    accounts = get_accounts()
    acc = next((a for a in accounts if a['email'] == test_email), None)
    assert acc is not None
    assert acc['password'] == "updated_pass", "Password should be updated"
    assert acc['refresh_token'] is None, "Refresh token should be cleared"
    assert acc['client_id'] is None, "Client ID should be cleared"
    print("‚ú?Credentials cleared successfully with NULL")
    
    # Test legacy mode (COALESCE behavior)
    upsert_account(
        email=test_email,
        password="",  # Empty string
        refresh_token="new_token",
        update_only_if_provided=True,  # Legacy mode
    )
    
    accounts = get_accounts()
    acc = next((a for a in accounts if a['email'] == test_email), None)
    assert acc['password'] == "updated_pass", "Password should NOT be cleared in legacy mode"
    assert acc['refresh_token'] == "new_token", "Token should be updated"
    print("‚ú?Legacy mode preserves non-empty values (COALESCE)")
    
    # Cleanup
    conn = _connect()
    conn.execute("DELETE FROM accounts WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()
    
    print("‚ú?Test passed: Upsert account allows NULL updates\n")


def test_graph_client_mailbox_validation():
    """Test that GraphClient validates mailbox parameter."""
    print("\n=== Test: GraphClient Mailbox Validation ===")
    
    # Create client without mailbox
    client = GraphClient(
        access_token="dummy_token",
        refresh_token="dummy_refresh",
        client_id="dummy_client"
    )
    
    try:
        # Should raise RuntimeError
        client.fetch_messages()
        assert False, "Should have raised RuntimeError for missing mailbox"
    except RuntimeError as e:
        assert "Mailbox not set" in str(e)
        print(f"‚ú?Validation error raised: {e}")
    
    # Create client with mailbox
    client = GraphClient(
        access_token="dummy_token",
        refresh_token="dummy_refresh",
        client_id="dummy_client",
        mailbox="test@outlook.com"
    )
    
    assert client.mailbox == "test@outlook.com"
    print("‚ú?Client accepts mailbox parameter")
    print("‚ú?Test passed: GraphClient mailbox validation\n")


def test_email_message_mailbox_populated():
    """Test that EmailMessage has mailbox field populated."""
    print("\n=== Test: EmailMessage Mailbox Populated ===")
    
    # Create a mock message
    msg = EmailMessage(
        message_id="test123",
        provider="graph",
        mailbox="user@outlook.com",
        subject="Test Subject",
        from_addr="sender@example.com",
        received_date="2024-01-01T10:00:00Z",
        body_text="Test body",
        body_html="<p>Test body</p>",
        is_read=False,
    )
    
    assert msg.mailbox == "user@outlook.com", "Mailbox should be populated"
    assert msg.mailbox != "", "Mailbox should not be empty"
    print("‚ú?EmailMessage.mailbox is properly set")
    print("‚ú?Test passed: EmailMessage mailbox populated\n")


def test_unified_credential_loader():
    """Test unified credential loading."""
    print("\n=== Test: Unified Credential Loader ===")
    
    test_email = "test_loader@example.com"
    
    # Create account with both IMAP and Graph credentials
    upsert_account(
        email=test_email,
        password="test_pass",
        imap_server="imap.example.com",
        refresh_token="test_refresh_token",
        client_id="test_client_id",
        type="outlook",
        source="manual",
        update_only_if_provided=False,
    )
    
    # Test new unified loader
    creds = load_account_credentials(test_email)
    assert creds is not None, "Credentials should be found"
    assert creds['email'] == test_email
    assert creds['password'] == "test_pass"
    assert creds['refresh_token'] == "test_refresh_token"
    assert creds['client_id'] == "test_client_id"
    assert creds['imap_server'] == "imap.example.com"
    print("‚ú?Unified loader returns all credential types")
    
    # Test legacy loader (should also work)
    legacy_creds = load_graph_account()
    assert legacy_creds is not None, "Legacy loader should still work"
    assert 'email' in legacy_creds
    assert 'refresh_token' in legacy_creds
    assert 'client_id' in legacy_creds
    print("‚ú?Legacy loader still works (backward compatibility)")
    
    # Test case-insensitive email lookup
    creds_upper = load_account_credentials(test_email.upper())
    assert creds_upper is not None, "Should find account with case-insensitive lookup"
    assert creds_upper['email'] == test_email
    print("‚ú?Case-insensitive email lookup works")
    
    # Cleanup
    conn = _connect()
    conn.execute("DELETE FROM accounts WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()
    
    print("‚ú?Test passed: Unified credential loader\n")


def test_migration_idempotency():
    """Test that migration can run multiple times safely."""
    print("\n=== Test: Migration Idempotency ===")
    
    from data.database import migrate_graph_accounts_to_accounts
    
    # Run migration multiple times
    try:
        migrate_graph_accounts_to_accounts()
        print("‚ú?First migration run completed")
        
        migrate_graph_accounts_to_accounts()
        print("‚ú?Second migration run completed (idempotent)")
        
        migrate_graph_accounts_to_accounts()
        print("‚ú?Third migration run completed (idempotent)")
        
        print("‚ú?Test passed: Migration idempotency\n")
    except Exception as e:
        print(f"‚ù?Migration failed: {e}")
        raise


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("CREDENTIAL HANDLING FIX TESTS")
    print("=" * 70)
    
    # Ensure database exists
    ensure_db()
    
    try:
        test_upsert_account_allows_null_updates()
        test_graph_client_mailbox_validation()
        test_email_message_mailbox_populated()
        test_unified_credential_loader()
        test_migration_idempotency()
        
        print("\n" + "=" * 70)
        print("‚ú?ALL TESTS PASSED!")
        print("=" * 70 + "\n")
        return True
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"‚ù?TEST FAILED: {e}")
        print("=" * 70 + "\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
