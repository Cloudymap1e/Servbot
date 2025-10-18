#!/usr/bin/env python
"""Standalone integration test for credential handling fixes.

This test can be run directly without package installation.
"""

import sys
import os
import sqlite3

# Set up paths for proper imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# Change to servbot directory for database operations
os.chdir(script_dir)

print("=" * 70)
print("CREDENTIAL HANDLING FIX - INTEGRATION TEST")
print("=" * 70)
print()

# Test 1: Import all modified modules
print("Test 1: Import all modified modules...")
try:
    from servbot.clients.graph import GraphClient
    from servbot.core.verification import fetch_verification_codes
    from servbot.data.database import (
        ensure_db,
        upsert_account,
        get_accounts,
        migrate_graph_accounts_to_accounts,
        _connect,
    )
    from servbot.config import load_account_credentials, load_graph_account
    from servbot.core.models import EmailMessage
    print("‚ú?All imports successful")
except ImportError as e:
    print(f"‚ù?Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Initialize database
print("\nTest 2: Initialize database...")
try:
    ensure_db()
    print("‚ú?Database initialized")
except Exception as e:
    print(f"‚ù?Database initialization failed: {e}")
    sys.exit(1)

# Test 3: Test upsert with NULL clearing (new behavior)
print("\nTest 3: Test upsert allows NULL to clear credentials...")
test_email = "test_null_clear@example.com"
try:
    # Create account with credentials
    upsert_account(
        email=test_email,
        password="test_pass",
        refresh_token="test_token",
        client_id="test_client",
        update_only_if_provided=False,
    )
    
    # Verify created
    accounts = get_accounts()
    acc = next((a for a in accounts if a['email'] == test_email), None)
    assert acc is not None, "Account should exist"
    assert acc['refresh_token'] == "test_token", "Token should be set"
    
    # Clear token with NULL
    upsert_account(
        email=test_email,
        refresh_token=None,
        client_id=None,
        update_only_if_provided=False,
    )
    
    # Verify cleared
    accounts = get_accounts()
    acc = next((a for a in accounts if a['email'] == test_email), None)
    assert acc['refresh_token'] is None, "Token should be cleared"
    assert acc['client_id'] is None, "Client ID should be cleared"
    
    # Cleanup
    conn = _connect()
    conn.execute("DELETE FROM accounts WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()
    
    print("‚ú?NULL clearing works correctly")
except Exception as e:
    print(f"‚ù?NULL clearing test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test legacy mode (COALESCE behavior)
print("\nTest 4: Test legacy mode preserves non-empty values...")
test_email = "test_legacy_mode@example.com"
try:
    # Create account
    upsert_account(
        email=test_email,
        password="original_pass",
        refresh_token="original_token",
        update_only_if_provided=False,
    )
    
    # Update with empty password in legacy mode
    upsert_account(
        email=test_email,
        password="",
        refresh_token="new_token",
        update_only_if_provided=True,  # Legacy mode
    )
    
    # Verify password NOT cleared (COALESCE behavior)
    accounts = get_accounts()
    acc = next((a for a in accounts if a['email'] == test_email), None)
    assert acc['password'] == "original_pass", "Password should NOT be cleared in legacy mode"
    assert acc['refresh_token'] == "new_token", "Token should be updated"
    
    # Cleanup
    conn = _connect()
    conn.execute("DELETE FROM accounts WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()
    
    print("‚ú?Legacy mode works correctly (COALESCE)")
except Exception as e:
    print(f"‚ù?Legacy mode test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test GraphClient mailbox parameter
print("\nTest 5: Test GraphClient requires mailbox parameter...")
try:
    # Create client without mailbox
    client = GraphClient(
        access_token="dummy_token",
        refresh_token="dummy_refresh",
        client_id="dummy_client"
    )
    
    # Should fail when trying to fetch without mailbox
    try:
        client.fetch_messages()
        print("‚ù?Should have raised RuntimeError for missing mailbox")
        sys.exit(1)
    except RuntimeError as e:
        if "Mailbox not set" in str(e):
            print(f"‚ú?Validation works: {e}")
        else:
            print(f"‚ù?Wrong error: {e}")
            sys.exit(1)
    
    # Create client WITH mailbox
    client = GraphClient(
        access_token="dummy_token",
        refresh_token="dummy_refresh",
        client_id="dummy_client",
        mailbox="test@outlook.com"
    )
    assert client.mailbox == "test@outlook.com", "Mailbox should be set"
    print("‚ú?Mailbox parameter works correctly")
    
except Exception as e:
    print(f"‚ù?GraphClient test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Test EmailMessage mailbox field
print("\nTest 6: Test EmailMessage mailbox field...")
try:
    msg = EmailMessage(
        message_id="test123",
        provider="graph",
        mailbox="user@outlook.com",
        subject="Test",
        from_addr="sender@example.com",
        received_date="2024-01-01T10:00:00Z",
        body_text="Test",
        body_html="<p>Test</p>",
        is_read=False,
    )
    
    assert msg.mailbox == "user@outlook.com", "Mailbox should be set"
    assert msg.mailbox != "", "Mailbox should not be empty"
    print("‚ú?EmailMessage mailbox field works")
except Exception as e:
    print(f"‚ù?EmailMessage test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Test unified credential loader
print("\nTest 7: Test unified credential loader...")
test_email = "test_loader@example.com"
try:
    # Create account with both IMAP and Graph credentials
    upsert_account(
        email=test_email,
        password="test_pass",
        imap_server="imap.test.com",
        refresh_token="test_token",
        client_id="test_client",
        type="outlook",
        source="manual",
        update_only_if_provided=False,
    )
    
    # Test new unified loader
    creds = load_account_credentials(test_email)
    assert creds is not None, "Should find credentials"
    assert creds['email'] == test_email
    assert creds['password'] == "test_pass"
    assert creds['refresh_token'] == "test_token"
    assert creds['client_id'] == "test_client"
    assert creds['imap_server'] == "imap.test.com"
    print("‚ú?Unified loader returns all credential types")
    
    # Test case-insensitive lookup
    creds_upper = load_account_credentials(test_email.upper())
    assert creds_upper is not None, "Should work with uppercase"
    assert creds_upper['email'] == test_email
    print("‚ú?Case-insensitive lookup works")
    
    # Test legacy loader still works
    legacy_creds = load_graph_account()
    assert legacy_creds is not None, "Legacy loader should work"
    assert 'email' in legacy_creds
    assert 'refresh_token' in legacy_creds
    print("‚ú?Legacy loader backward compatible")
    
    # Cleanup
    conn = _connect()
    conn.execute("DELETE FROM accounts WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()
    
except Exception as e:
    print(f"‚ù?Credential loader test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Test migration idempotency
print("\nTest 8: Test migration can run multiple times...")
try:
    # Run migration 3 times
    for i in range(3):
        migrate_graph_accounts_to_accounts()
    print("‚ú?Migration is idempotent (safe to run multiple times)")
except Exception as e:
    print(f"‚ù?Migration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 9: Verify database schema
print("\nTest 9: Verify database schema...")
try:
    conn = _connect()
    cur = conn.cursor()
    
    # Check accounts table has all required columns
    cur.execute("PRAGMA table_info(accounts)")
    columns = {row[1] for row in cur.fetchall()}
    required = {'email', 'password', 'refresh_token', 'client_id', 'imap_server', 'type', 'source'}
    assert required.issubset(columns), f"Missing columns: {required - columns}"
    print("‚ú?accounts table has all required columns")
    
    # Check messages table
    cur.execute("PRAGMA table_info(messages)")
    columns = {row[1] for row in cur.fetchall()}
    assert 'mailbox' in columns, "messages table should have mailbox column"
    print("‚ú?messages table has mailbox column")
    
    # Check graph_accounts table exists (deprecated but kept for compatibility)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='graph_accounts'")
    assert cur.fetchone() is not None, "graph_accounts table should exist (legacy)"
    print("‚ú?graph_accounts table exists (deprecated, kept for compatibility)")
    
    conn.close()
except Exception as e:
    print(f"‚ù?Schema verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 10: Test GraphClient.from_credentials with mailbox
print("\nTest 10: Test GraphClient.from_credentials signature...")
try:
    import inspect
    sig = inspect.signature(GraphClient.from_credentials)
    params = list(sig.parameters.keys())
    
    assert 'refresh_token' in params, "Should have refresh_token parameter"
    assert 'client_id' in params, "Should have client_id parameter"
    assert 'mailbox' in params, "Should have mailbox parameter"
    
    print(f"‚ú?GraphClient.from_credentials has correct signature: {params}")
except Exception as e:
    print(f"‚ù?Signature test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Final summary
print("\n" + "=" * 70)
print("‚ú?ALL TESTS PASSED!")
print("=" * 70)
print("\nTest Summary:")
print("  1. ‚ú?All modules import successfully")
print("  2. ‚ú?Database initializes correctly")
print("  3. ‚ú?NULL clearing works (new mode)")
print("  4. ‚ú?Legacy mode works (COALESCE)")
print("  5. ‚ú?GraphClient validates mailbox")
print("  6. ‚ú?EmailMessage has mailbox field")
print("  7. ‚ú?Unified credential loader works")
print("  8. ‚ú?Migration is idempotent")
print("  9. ‚ú?Database schema is correct")
print(" 10. ‚ú?GraphClient.from_credentials signature correct")
print("\n" + "=" * 70)
print("All credential handling fixes verified and working!")
print("=" * 70)

sys.exit(0)
