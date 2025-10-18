#!/usr/bin/env python
"""Analyze the password format to understand authentication requirements."""

import sys
from pathlib import Path

from servbot.data.database import get_accounts

accounts = get_accounts()
if not accounts:
    print("No accounts found")
    sys.exit(1)

account = accounts[0]
email = account['email']
password = account.get('password', '')

print("=" * 80)
print("PASSWORD ANALYSIS")
print("=" * 80)
print(f"\nAccount: {email}")
print(f"Password length: {len(password)} characters")
print(f"\nFirst 100 characters:")
print(f"  {password[:100]}")
print(f"\nLast 50 characters:")
print(f"  ...{password[-50:]}")

print(f"\nFormat analysis:")
print(f"  Contains spaces: {' ' in password}")
print(f"  Contains newlines: {'\\n' in password or '\\r' in password}")
print(f"  All alphanumeric: {password.isalnum()}")
print(f"  Looks like OAuth token: {password.startswith('ey') or password.startswith('M.C')}")
print(f"  Looks like normal password: {len(password) < 50 and not password.startswith('ey')}")

# Check if it's an OAuth access token (JWT format)
if password.startswith('eyJ'):
    print(f"\n⚠️  This appears to be a JWT (JSON Web Token)")
    print(f"  JWT tokens are for OAuth, not IMAP username/password auth")
    
# Check if it's a Microsoft refresh token
if password.startswith('M.C') or password.startswith('0.A'):
    print(f"\n⚠️  This appears to be a Microsoft OAuth refresh token")
    print(f"  OAuth tokens cannot be used as IMAP passwords")
    print(f"  You need the ACTUAL password, not the OAuth token")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if len(password) > 200:
    print("""
⚠️  WARNING: Password is extremely long ({} chars)

This is likely NOT a regular password. Flashmail accounts might be using:
1. OAuth tokens instead of passwords (won't work with IMAP)
2. Encoded/encrypted format that needs decoding
3. API-specific authentication token

IMAP requires either:
- Regular username + password
- App-specific password (for OAuth-protected accounts)

ACTION NEEDED:
1. Check if Flashmail provides the ACTUAL password
2. Or use Microsoft Graph API with the OAuth token instead
3. Or provision a new account with known password
""".format(len(password)))
else:
    print(f"\nPassword length seems reasonable ({len(password)} chars)")
    print("Should work with standard IMAP authentication")
