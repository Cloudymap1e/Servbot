#!/usr/bin/env python
"""Test IMAP with relaxed SSL settings."""

import sys
from pathlib import Path

import imaplib
import ssl

email = "fgmzknbmmt7648@outlook.com"

# Get password from database
from servbot.data.database import get_accounts
accounts = get_accounts()
account = None
for acc in accounts:
    if acc['email'].lower() == email.lower():
        account = acc
        break

if not account:
    print("Account not found!")
    sys.exit(1)

password = account['password']

print("=" * 80)
print("TESTING IMAP WITH DIFFERENT SSL SETTINGS")
print("=" * 80)

# Test 1: Standard SSL (Port 993)
print("\nTest 1: Port 993 with standard SSL...")
try:
    context = ssl.create_default_context()
    M = imaplib.IMAP4_SSL('outlook.office365.com', 993, ssl_context=context)
    M.login(email, password)
    print("[SUCCESS] Port 993 works!")
    M.logout()
except Exception as e:
    print(f"[FAILED] Port 993: {e}")

# Test 2: Port 993 with unverified SSL
print("\nTest 2: Port 993 with unverified SSL...")
try:
    context = ssl._create_unverified_context()
    M = imaplib.IMAP4_SSL('outlook.office365.com', 993, ssl_context=context)
    M.login(email, password)
    print("[SUCCESS] Port 993 unverified works!")
    
    # Try to fetch messages
    M.select('INBOX')
    typ, data = M.search(None, 'ALL')
    if typ == 'OK' and data and data[0]:
        msg_count = len(data[0].split())
        print(f"  Found {msg_count} messages in inbox!")
    else:
        print("  Inbox is empty")
    M.logout()
except Exception as e:
    print(f"[FAILED] Port 993 unverified: {e}")

# Test 3: Port 143 with STARTTLS
print("\nTest 3: Port 143 with STARTTLS...")
try:
    M = imaplib.IMAP4('outlook.office365.com', 143)
    context = ssl.create_default_context()
    M.starttls(ssl_context=context)
    M.login(email, password)
    print("[SUCCESS] Port 143 STARTTLS works!")
    
    # Try to fetch messages
    M.select('INBOX')
    typ, data = M.search(None, 'ALL')
    if typ == 'OK' and data and data[0]:
        msg_count = len(data[0].split())
        print(f"  Found {msg_count} messages in inbox!")
    else:
        print("  Inbox is empty")
    M.logout()
except Exception as e:
    print(f"[FAILED] Port 143 STARTTLS: {e}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nIf all tests failed, the account is either:")
print("  1. Too new (wait 20-30 minutes)")
print("  2. Flagged/blocked by Microsoft")
print("  3. IMAP access not enabled yet")
print("\nRecommendation: Wait 30 minutes and try again.")
print("=" * 80)

