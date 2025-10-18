#!/usr/bin/env python
"""Detailed debugging of email fetch with step-by-step output."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("DETAILED EMAIL FETCH DEBUG")
print("=" * 80)

email = "fgmzknbmmt7648@outlook.com"

# Step 1: Get account
print("\nSTEP 1: Getting account from database...")
from servbot.data.database import get_accounts
accounts = get_accounts()
account = None
for acc in accounts:
    if acc['email'].lower() == email.lower():
        account = acc
        break

if not account:
    print(f"ERROR: Account {email} not found!")
    sys.exit(1)

print(f"[OK] Account found")
print(f"  Email: {account['email']}")
print(f"  Has password: {bool(account.get('password'))} ({len(account.get('password', ''))} chars)")
print(f"  Has refresh_token: {bool(account.get('refresh_token'))} ({len(account.get('refresh_token', ''))} chars)")
print(f"  Has client_id: {bool(account.get('client_id'))} ({len(account.get('client_id', ''))} chars)")

# Step 2: Try Graph API token exchange
print("\n" + "=" * 80)
print("STEP 2: Testing Graph API Token Exchange")
print("=" * 80)

from servbot.clients import GraphClient
from servbot.constants import FLASHMAIL_REFRESH_TOKEN, FLASHMAIL_CLIENT_ID

print(f"\nUsing credentials:")
print(f"  Refresh Token: {account['refresh_token'][:30]}... ({len(account['refresh_token'])} chars)")
print(f"  Client ID: {account['client_id']}")

print("\nAttempting to create GraphClient...")
try:
    graph_client = GraphClient.from_credentials(
        account['refresh_token'],
        account['client_id']
    )
    
    if graph_client:
        print("[SUCCESS] Graph client created!")
        print(f"  Access token length: {len(graph_client.access_token) if hasattr(graph_client, 'access_token') else 'N/A'}")
        
        # Try to fetch messages
        print("\nAttempting to fetch messages via Graph API...")
        try:
            messages = graph_client.fetch_messages(
                folder='inbox',
                unseen_only=False,
                limit=20
            )
            print(f"[SUCCESS] Fetched {len(messages)} messages via Graph API")
            
            if messages:
                for i, msg in enumerate(messages[:3], 1):
                    print(f"\n  Message {i}:")
                    print(f"    Subject: {msg.subject}")
                    print(f"    From: {msg.from_addr}")
                    print(f"    Date: {msg.received_date}")
        except Exception as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[FAILED] GraphClient.from_credentials() returned None")
        print("This means token exchange failed.")
        
        # Try manual token exchange to see error
        print("\nTrying manual token exchange to see error...")
        import requests
        try:
            response = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": account['client_id'],
                    "grant_type": "refresh_token",
                    "refresh_token": account['refresh_token'],
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=10,
            )
            print(f"  HTTP Status: {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data:
                    print(f"  [OK] Got access token ({len(data['access_token'])} chars)")
                else:
                    print(f"  [ERROR] No access_token in response")
            else:
                print(f"  [ERROR] Token exchange failed")
                
        except Exception as e:
            print(f"  [ERROR] Request failed: {e}")
            import traceback
            traceback.print_exc()
            
except Exception as e:
    print(f"[ERROR] Graph API failed: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Try IMAP
print("\n" + "=" * 80)
print("STEP 3: Testing IMAP Connection")
print("=" * 80)

from servbot.clients import IMAPClient

imap_server = account.get('imap_server', 'outlook.office365.com')
password = account['password']

print(f"\nConnection details:")
print(f"  Server: {imap_server}")
print(f"  Username: {email}")
print(f"  Password: {'*' * 10} ({len(password)} chars)")
print(f"  Port: 993")
print(f"  SSL: True")

print("\nAttempting IMAP connection...")
try:
    client = IMAPClient(
        server=imap_server,
        username=email,
        password=password,
        port=993,
        use_ssl=True
    )
    print("[SUCCESS] IMAP client created")
    
    print("\nAttempting to fetch messages...")
    try:
        messages = client.fetch_messages(
            folder='INBOX',
            unseen_only=False,
            limit=20
        )
        print(f"[SUCCESS] Fetched {len(messages)} messages via IMAP")
        
        if messages:
            for i, msg in enumerate(messages[:3], 1):
                print(f"\n  Message {i}:")
                print(f"    Subject: {msg.subject}")
                print(f"    From: {msg.from_addr}")
                print(f"    Date: {msg.received_date}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch messages: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"[ERROR] IMAP connection failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

from servbot.data.database import _connect
conn = _connect()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email,))
msg_count = cur.fetchone()[0]
conn.close()

print(f"\nMessages in database: {msg_count}")

if msg_count == 0:
    print("\n[PROBLEM] No messages were fetched by either method")
    print("Both Graph API and IMAP are failing.")
    print("\nPossible reasons:")
    print("  1. Graph API refresh token expired/invalid")
    print("  2. IMAP credentials incorrect")
    print("  3. Account not fully activated yet (needs time)")
    print("  4. Network/firewall blocking connections")
else:
    print(f"\n[SUCCESS] {msg_count} messages were saved!")

print("=" * 80)

