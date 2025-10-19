#!/usr/bin/env python
"""Test script: Save account credentials and fetch emails via Microsoft Graph."""
import sys
from pathlib import Path

# Ensure local package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from servbot.data.database import ensure_db, upsert_account
from servbot.clients import GraphClient


def main():
    # Account credentials (format: email----password----refresh_token----client_id)
    account_string = "cjrhedy083@outlook.com----c4JGJbE2mT3rb----M.C512_BAY.0.U.-CtbJivPAa0yNOfKEQVJfkLHUi2J0mbmBAcMkyBteA0qVEePZ8LkyktHeODJ69Oh!c5XtatOaJIyD4Gg*OfmIxgcScKSIx8xBnlKSnaUTBTYygnose7PMWqVAQHaIXpbRAOQ8H7rcPGNnpzmT8wmflqP2GXtP4solr!lkc3BG75zyf7NOMVk58cVugTBzxTCdi2M7QcGoVIu9u2TX7*OYMYXRFCJybQdoJqSMMNkqkrx4BzGZnKVzlXjxMnkMlN2ppmXNrxm7EMeiy85XUBzuNE933c!Yf7Z4i8re!wVAAwoVfS3tep4QDacmLDvAEu*9tzJ6N8GBoyC4WyW!ArSDV7v*GC126YRKbJapEYbCkIqLo3PumofNZXjaS3w5DSPK*7mSagBKtRhd4auzCr0jYSY$----8b4ba9dd-3ea5-4e5f-86f1-ddba2230dcf2"
    
    # Parse account string
    parts = [p.strip() for p in account_string.split('----')]
    if len(parts) != 4:
        print(f"ERROR: Invalid account format. Expected 4 parts, got {len(parts)}")
        return 1
    
    email, password, refresh_token, client_id = parts
    
    print("=" * 70)
    print("STEP 1: Save account to database")
    print("=" * 70)
    print(f"Email: {email}")
    print(f"Password: {'*' * len(password)}")
    print(f"Refresh token length: {len(refresh_token)} chars")
    print(f"Client ID: {client_id}")
    print()
    
    # Initialize database
    ensure_db()
    
    # Save account to database
    account_id = upsert_account(
        email=email,
        password=password,
        type="outlook",
        source="manual",
        refresh_token=refresh_token,
        client_id=client_id,
        update_only_if_provided=False,  # Direct update mode
    )
    
    print(f"✓ Account saved to database (ID: {account_id})")
    print()
    
    print("=" * 70)
    print("STEP 2: Authenticate and fetch emails via Microsoft Graph")
    print("=" * 70)
    print("Creating GraphClient from credentials...")
    
    # Create GraphClient using from_credentials
    client = GraphClient.from_credentials(
        refresh_token=refresh_token,
        client_id=client_id,
        mailbox=email
    )
    
    if not client:
        print("ERROR: Failed to create GraphClient. Token refresh failed.")
        return 1
    
    print(f"✓ GraphClient created successfully")
    print(f"  Access token length: {len(client.access_token)} chars")
    print()
    
    # Fetch messages
    print("Fetching messages from inbox...")
    try:
        messages = client.fetch_messages(
            folder="inbox",
            unseen_only=False,
            limit=10
        )
    except Exception as e:
        print(f"ERROR: Failed to fetch messages: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print(f"✓ Fetched {len(messages)} message(s)")
    print()
    
    if not messages:
        print("No messages found in inbox.")
        return 0
    
    # Display messages
    print("=" * 70)
    print(f"MESSAGES IN INBOX ({len(messages)} total)")
    print("=" * 70)
    
    for i, msg in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"Subject: {msg.subject}")
        print(f"From: {msg.from_addr}")
        print(f"Date: {msg.received_date}")
        print(f"Read: {msg.is_read}")
        
        # Body preview
        body_text = msg.body_text or msg.body_html or ""
        if body_text:
            preview = body_text.strip()[:300]
            if len(body_text) > 300:
                preview += "..."
            print(f"Body preview:\n{preview}")
        else:
            print("Body: (empty)")
        
        print("-" * 70)
    
    print()
    print("=" * 70)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
