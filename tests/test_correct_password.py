#!/usr/bin/env python
"""Test IMAP connection with correctly parsed password."""

import sys
from pathlib import Path

from servbot.data.database import get_accounts
from servbot.clients import IMAPClient

print("=" * 80)
print("IMAP TEST WITH CORRECT PASSWORD")
print("=" * 80)

accounts = get_accounts()
if not accounts:
    print("\nNo accounts found")
    sys.exit(1)

account = accounts[0]
email = account['email']
password_field = account.get('password', '')

# Parse Flashmail format: password----refresh_token----client_id
if '----' in password_field:
    parts = password_field.split('----')
    actual_password = parts[0]
    print(f"\n‚ú?Detected Flashmail format")
    print(f"   Full field length: {len(password_field)} chars")
    print(f"   Actual password: {actual_password} ({len(actual_password)} chars)")
else:
    actual_password = password_field
    print(f"\n‚ú?Standard password format")
    print(f"   Password length: {len(actual_password)} chars")

# Try outlook.office365.com (Microsoft's official IMAP)
imap_server = 'outlook.office365.com'

print(f"\nüìß Account: {email}")
print(f"üñ•Ô∏? Server: {imap_server}")
print(f"üîë Password: {'*' * len(actual_password)}")

print("\n" + "-" * 80)
print("CONNECTING TO IMAP...")
print("-" * 80)

try:
    # Use relaxed SSL (certificate might be expired)
    import ssl
    import imaplib
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    M = imaplib.IMAP4_SSL(imap_server, 993, ssl_context=ssl_context)
    print(f"‚ú?Connected!")
    print(f"   Server: {M.welcome}")
    
    # Try login
    print(f"\nüîê Attempting login...")
    M.login(email, actual_password)
    print(f"‚ú?LOGIN SUCCESSFUL!")
    
    # List folders
    print(f"\nüìÅ Listing folders...")
    typ, folders = M.list()
    print(f"‚ú?Found {len(folders)} folder(s):")
    for folder in folders[:10]:
        print(f"   - {folder.decode()}")
    
    # Select INBOX
    print(f"\nüì• Opening INBOX...")
    M.select('INBOX')
    
    # Search for all messages
    typ, data = M.search(None, 'ALL')
    message_ids = data[0].split()
    print(f"‚ú?Found {len(message_ids)} message(s) in INBOX")
    
    if message_ids:
        # Fetch first few messages
        print(f"\nüìß Fetching first {min(5, len(message_ids))} message(s)...")
        print("=" * 80)
        
        for i, msg_id in enumerate(message_ids[:5], 1):
            typ, msg_data = M.fetch(msg_id, '(RFC822)')
            if typ == 'OK' and msg_data and msg_data[0]:
                import email
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                subject = msg.get('Subject', 'No Subject')
                from_addr = msg.get('From', 'Unknown')
                date = msg.get('Date', 'Unknown')
                
                print(f"\nMESSAGE {i}:")
                print(f"  Subject: {subject}")
                print(f"  From: {from_addr}")
                print(f"  Date: {date}")
                
                # Get body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = str(msg.get_payload())
                
                if body:
                    print(f"\n  Content (first 500 chars):")
                    print("  " + "-" * 76)
                    content_preview = body[:500].replace('\n', '\n  ')
                    print(f"  {content_preview}")
                    if len(body) > 500:
                        print(f"  ... ({len(body) - 500} more characters)")
                    print("  " + "-" * 76)
                else:
                    print(f"  (No text content)")
    else:
        print("\nüì≠ INBOX is empty")
    
    M.logout()
    print(f"\n‚ú?IMAP TEST SUCCESSFUL!")
    
except Exception as e:
    print(f"\n‚ù?Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
