#!/usr/bin/env python
"""Comprehensive debugging script for email fetching issues."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def debug_email_fetch(email_address):
    """Debug why emails aren't being fetched."""
    
    print("=" * 80)
    print("COMPREHENSIVE EMAIL FETCH DEBUGGING")
    print("=" * 80)
    print(f"\nTarget Email: {email_address}")
    
    # Step 1: Check account in database
    print("\n" + "=" * 80)
    print("STEP 1: Checking Account Details")
    print("=" * 80)
    
    from servbot.data.database import get_accounts, _connect
    accounts = get_accounts()
    account = None
    
    for acc in accounts:
        if acc['email'].lower() == email_address.lower():
            account = acc
            break
    
    if not account:
        print(f"ERROR: Account {email_address} not found in database!")
        return
    
    print(f"[OK] Account found in database")
    print(f"  Email: {account['email']}")
    print(f"  Password: {'*' * 10} (length: {len(account.get('password', ''))})")
    print(f"  Type: {account['type']}")
    print(f"  Source: {account['source']}")
    print(f"  IMAP Server: {account.get('imap_server', 'N/A')}")
    print(f"  Has Refresh Token: {bool(account.get('refresh_token'))}")
    print(f"  Has Client ID: {bool(account.get('client_id'))}")
    
    # Step 2: Try Graph API
    print("\n" + "=" * 80)
    print("STEP 2: Testing Microsoft Graph API")
    print("=" * 80)
    
    if account.get('refresh_token') and account.get('client_id'):
        try:
            from servbot.clients import GraphClient
            
            print("Attempting Graph API connection...")
            client = GraphClient.from_credentials(
                account['refresh_token'],
                account['client_id']
            )
            
            print("[OK] Graph API client created")
            
            # Try to fetch messages
            print("Fetching messages via Graph API...")
            messages = client.fetch_messages(
                folder='inbox',
                unseen_only=False,
                limit=20
            )
            
            print(f"[OK] Fetched {len(messages)} messages via Graph API")
            
            if messages:
                print("\nMessages fetched:")
                for i, msg in enumerate(messages[:5], 1):
                    print(f"\n{i}. Subject: {msg.subject}")
                    print(f"   From: {msg.from_addr}")
                    print(f"   Date: {msg.received_date}")
                    body_preview = (msg.body_text or msg.body_html or '')[:100]
                    print(f"   Body Preview: {body_preview}...")
            else:
                print("[WARN] No messages returned from Graph API")
                
        except Exception as e:
            print(f"[ERROR] Graph API failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[WARN] No Graph API credentials available, skipping")
    
    # Step 3: Try IMAP
    print("\n" + "=" * 80)
    print("STEP 3: Testing IMAP Connection")
    print("=" * 80)
    
    password = account.get('password')
    imap_server = account.get('imap_server', 'outlook.office365.com')
    
    if password:
        try:
            from servbot.clients import IMAPClient
            
            print(f"Attempting IMAP connection to {imap_server}...")
            client = IMAPClient(
                server=imap_server,
                username=email_address,
                password=password,
                port=993,
                ssl=True
            )
            
            print("[OK] IMAP client created and connected")
            
            # Try to fetch messages
            print("Fetching messages via IMAP...")
            messages = client.fetch_messages(
                folder='INBOX',
                unseen_only=False,
                limit=20
            )
            
            print(f"[OK] Fetched {len(messages)} messages via IMAP")
            
            if messages:
                print("\nMessages fetched:")
                for i, msg in enumerate(messages[:5], 1):
                    print(f"\n{i}. Subject: {msg.subject}")
                    print(f"   From: {msg.from_addr}")
                    print(f"   Date: {msg.received_date}")
                    body_preview = (msg.body_text or msg.body_html or '')[:100]
                    print(f"   Body Preview: {body_preview}...")
            else:
                print("[WARN] No messages returned from IMAP")
                
        except Exception as e:
            print(f"[ERROR] IMAP failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERROR] No password available for IMAP")
    
    # Step 4: Check database messages
    print("\n" + "=" * 80)
    print("STEP 4: Checking Database Messages")
    print("=" * 80)
    
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, subject, from_addr, received_date, body_preview, service
        FROM messages
        WHERE mailbox = ?
        ORDER BY received_date DESC
        LIMIT 10
    """, (email_address,))
    db_messages = cur.fetchall()
    conn.close()
    
    if db_messages:
        print(f"Found {len(db_messages)} messages in database:")
        for i, msg in enumerate(db_messages, 1):
            print(f"\n{i}. Subject: {msg[1]}")
            print(f"   From: {msg[2]}")
            print(f"   Date: {msg[3]}")
            print(f"   Service: {msg[5] or 'N/A'}")
            print(f"   Preview: {msg[4][:80]}..." if msg[4] else "   Preview: N/A")
    else:
        print("[WARN] No messages found in database")
        print("This suggests messages are not being saved/fetched at all")
    
    # Step 5: Test verification code extraction
    print("\n" + "=" * 80)
    print("STEP 5: Testing Verification Code Extraction")
    print("=" * 80)
    
    print("Running fetch_verification_codes()...")
    from servbot import fetch_verification_codes
    
    try:
        verifications = fetch_verification_codes(
            imap_server=imap_server,
            username=email_address,
            password=password,
            unseen_only=False,
            limit=50,
            prefer_graph=True,
            use_ai=True
        )
        
        print(f"\n[OK] Function completed, found {len(verifications)} verifications")
        
        if verifications:
            print("\nVerifications extracted:")
            for i, v in enumerate(verifications, 1):
                print(f"\n{i}. Service: {v.service}")
                print(f"   Code: {v.code}")
                print(f"   Type: {'Link' if v.is_link else 'Code'}")
                print(f"   Subject: {v.subject}")
                print(f"   From: {v.from_addr}")
        else:
            print("\n[WARN] No verifications extracted")
            print("\nThis means either:")
            print("  1. Messages aren't being fetched from server")
            print("  2. Messages are fetched but don't match verification patterns")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 6: Final diagnosis
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email_address,))
    msg_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM verifications v JOIN messages m ON v.message_id = m.id WHERE m.mailbox = ?", (email_address,))
    ver_count = cur.fetchone()[0]
    conn.close()
    
    print(f"\nMessages in database: {msg_count}")
    print(f"Verifications in database: {ver_count}")
    
    if msg_count == 0:
        print("\n❌ PROBLEM: No messages are being fetched from the server")
        print("   Possible causes:")
        print("   - Authentication failure (wrong credentials)")
        print("   - Network/firewall issues")
        print("   - Server not responding")
        print("   - Account not fully activated yet")
    elif ver_count == 0:
        print("\n❌ PROBLEM: Messages fetched but no codes extracted")
        print("   Possible causes:")
        print("   - Verification emails haven't arrived yet")
        print("   - Code patterns not matching")
        print("   - Emails in different format than expected")
    else:
        print("\n✓ System appears to be working")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_email_fetch.py <email>")
        sys.exit(1)
    
    debug_email_fetch(sys.argv[1])

