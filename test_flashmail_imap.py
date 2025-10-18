#!/usr/bin/env python
"""Test Flashmail IMAP proxy server."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import imaplib

# Get account from database
from servbot.data.database import get_accounts, _connect
accounts = get_accounts()
if not accounts:
    print("No accounts found!")
    sys.exit(1)

account = accounts[0]
email = account['email']
password = account['password']

print("=" * 80)
print("TESTING FLASHMAIL IMAP PROXY SERVER")
print("=" * 80)

# Update database first
conn = _connect()
cur = conn.cursor()
cur.execute("UPDATE accounts SET imap_server = ? WHERE email = ?", 
            ('imap.shanyouxiang.com', email))
conn.commit()
conn.close()

print(f"\nAccount: {email}")
print("Testing imap.shanyouxiang.com (Flashmail proxy)")

# Test Port 143 (no SSL) - Recommended by Flashmail
print("\n" + "-" * 80)
print("Test 1: Port 143 (no SSL) - RECOMMENDED BY FLASHMAIL")
print("-" * 80)
try:
    M = imaplib.IMAP4('imap.shanyouxiang.com', 143)
    M.login(email, password)
    print("[SUCCESS] Connected!")
    
    # Select inbox
    M.select('INBOX')
    typ, data = M.search(None, 'ALL')
    
    if typ == 'OK' and data and data[0]:
        msg_nums = data[0].split()
        print(f"[SUCCESS] Found {len(msg_nums)} messages in inbox!")
        
        # Fetch first few message subjects
        if msg_nums:
            print("\nRecent messages:")
            for num in msg_nums[-5:]:  # Last 5 messages
                typ, msg_data = M.fetch(num, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                if typ == 'OK':
                    print(f"  Message {num.decode()}: {msg_data[0][1].decode('utf-8', errors='ignore')[:100]}...")
    else:
        print("[INFO] Inbox is empty or no messages found")
    
    M.logout()
except Exception as e:
    print(f"[FAILED] {e}")
    import traceback
    traceback.print_exc()

# Test Port 993 (SSL)
print("\n" + "-" * 80)
print("Test 2: Port 993 (SSL)")
print("-" * 80)
try:
    import ssl
    context = ssl.create_default_context()
    M = imaplib.IMAP4_SSL('imap.shanyouxiang.com', 993, ssl_context=context)
    M.login(email, password)
    print("[SUCCESS] Connected with SSL!")
    
    M.select('INBOX')
    typ, data = M.search(None, 'ALL')
    
    if typ == 'OK' and data and data[0]:
        msg_count = len(data[0].split())
        print(f"[SUCCESS] Found {msg_count} messages!")
    else:
        print("[INFO] Inbox is empty")
    
    M.logout()
except Exception as e:
    print(f"[FAILED] {e}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nFlashmail IMAP proxy: imap.shanyouxiang.com")
print("Recommended: Port 143 (no SSL)")
print("Alternative: Port 993 (SSL)")
print("=" * 80)

