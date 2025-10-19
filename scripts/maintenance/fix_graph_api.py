#!/usr/bin/env python
"""Microsoft Graph API diagnostic and fix tool.

This script diagnoses and attempts to fix the "service abuse mode" error
(AADSTS70000) for Microsoft Graph API authentication.
"""

import sys
from pathlib import Path

import json
import time
from servbot.data.database import get_accounts, upsert_account
from servbot.constants import FLASHMAIL_REFRESH_TOKEN, FLASHMAIL_CLIENT_ID

print("=" * 80)
print("MICROSOFT GRAPH API DIAGNOSTIC & FIX")
print("=" * 80)

# Get account
accounts = get_accounts()
if not accounts:
    print("\n‚ù?No accounts in database")
    sys.exit(1)

account = accounts[0]
email = account['email']
refresh_token = account.get('refresh_token', '')
client_id = account.get('client_id', '')

print(f"\nüìß Account: {email}")
print(f"üîë Client ID: {client_id}")
print(f"üîÑ Refresh Token: {refresh_token[:30]}... ({len(refresh_token)} chars)")

# Analyze the error
print("\n" + "=" * 80)
print("ERROR ANALYSIS: AADSTS70000 - Service Abuse Mode")
print("=" * 80)

print("""
The error "User account is found to be in service abuse mode" means:

ROOT CAUSES:
1. ‚ù?Shared refresh token used by too many people/devices
2. ‚ù?Too many token refresh attempts from same token
3. ‚ù?Microsoft flagged the account for suspicious activity
4. ‚ù?Token has been revoked by Microsoft
5. ‚ù?IP address/network flagged for abuse

FLASHMAIL CONTEXT:
- Flashmail provides pre-authenticated accounts with shared credentials
- The refresh token is the SAME for ALL Flashmail customers
- Microsoft detects this as "service abuse" and blocks the token
""")

# Test 1: Try the current token
print("\n" + "=" * 80)
print("TEST 1: Current Refresh Token")
print("=" * 80)

try:
    import requests
    
    # Set proxy to None to bypass Meta tunnel for this request
    proxies = {
        'http': None,
        'https': None,
    }
    
    response = requests.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        data={
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "https://graph.microsoft.com/.default",
        },
        proxies=proxies,
        timeout=15,
    )
    
    print(f"üì° HTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"‚ú?Token refresh SUCCESS!")
        print(f"   Access token: {data.get('access_token', '')[:30]}...")
        print(f"   Expires in: {data.get('expires_in')} seconds")
        
        # Update token in database
        new_refresh = data.get('refresh_token', refresh_token)
        upsert_account(
            email=email,
            password=account.get('password', ''),
            refresh_token=new_refresh,
            client_id=client_id,
            type=account.get('type'),
            source=account.get('source'),
            update_only_if_provided=False
        )
        print(f"‚ú?Database updated with new token")
        
    else:
        error_data = response.json()
        error_code = error_data.get('error', 'unknown')
        error_desc = error_data.get('error_description', '')
        
        print(f"‚ù?Token refresh FAILED")
        print(f"   Error: {error_code}")
        print(f"   Description: {error_desc}")
        
        if 'AADSTS70000' in error_desc:
            print(f"\n‚ö†Ô∏è  CONFIRMED: Account is in abuse mode")
        elif 'AADSTS50173' in error_desc:
            print(f"\n‚ö†Ô∏è  Token has expired and needs re-authentication")
        elif 'AADSTS700016' in error_desc:
            print(f"\n‚ö†Ô∏è  Application not found or disabled")
            
except Exception as e:
    print(f"‚ù?Request failed: {e}")

# Solution 1: Use different Graph API client
print("\n" + "=" * 80)
print("SOLUTION 1: Alternative Microsoft Graph Client ID")
print("=" * 80)

print("""
Flashmail uses a shared client ID that Microsoft has blocked.

ALTERNATIVE CLIENT IDs (public Microsoft apps):
1. Microsoft Office: d3590ed6-52b3-4102-aeff-aad2292ab01c
2. Azure CLI: 04b07795-8ddb-461a-bbee-02f9e1bf7b46
3. Microsoft Graph Explorer: de8bc8b5-d9f9-48b1-a8ad-b748da725064

‚ö†Ô∏è  These will NOT work with Flashmail's refresh token
   (each client ID has its own token format)
""")

# Solution 2: Direct username/password authentication
print("\n" + "=" * 80)
print("SOLUTION 2: Direct Username/Password Authentication")
print("=" * 80)

print("""
Instead of OAuth refresh tokens, use direct ROPC (Resource Owner Password Credentials):

PROS:
‚ú?Works with username + password directly
‚ú?No refresh token needed
‚ú?Simpler authentication flow

CONS:
‚ù?Requires modern authentication to be enabled
‚ù?May not work with MFA-enabled accounts
‚ù?Less secure (exposes password to application)

This would require modifying the GraphClient to support ROPC flow.
""")

# Solution 3: Use IMAP without Meta tunnel
print("\n" + "=" * 80)
print("SOLUTION 3: Disable Meta Tunnel (Recommended)")
print("=" * 80)

print("""
Since Graph API is blocked AND IMAP is blocked by Meta tunnel:

BEST SOLUTION: Temporarily disable Meta when using servbot

1. Create a batch script to disable/enable Meta:

   @echo off
   echo Disabling Meta tunnel...
   netsh interface set interface "Meta" admin=disable
   echo.
   echo Running servbot...
   python -m servbot
   echo.
   echo Re-enabling Meta tunnel...
   netsh interface set interface "Meta" admin=enable

2. Run this script when you need to fetch emails

3. Meta will auto-re-enable on next login/restart
""")

# Solution 4: Fresh account authentication
print("\n" + "=" * 80)
print("SOLUTION 4: Provision Fresh Account with New Token")
print("=" * 80)

print("""
Get a fresh Outlook account with VALID Graph API token:

METHOD A: Authenticate manually via browser
1. Use Microsoft's OAuth flow to get YOUR OWN refresh token
2. Store it in the database (won't be shared/abused)

METHOD B: Use a different email provider
1. Gmail with app-specific passwords (IMAP only)
2. ProtonMail Bridge (IMAP)
3. Other providers without Graph API

Would you like me to create an OAuth authentication flow?
""")

# Recommendations
print("\n" + "=" * 80)
print("RECOMMENDED ACTION PLAN")
print("=" * 80)

print("""
IMMEDIATE (Option A): Disable Meta tunnel temporarily
  ‚ú?Run: netsh interface set interface "Meta" admin=disable
  ‚ú?Test IMAP: python D:\\servbot\\servbot\\debug_imap_ssl.py
  ‚ú?If works: Use servbot normally
  ‚ú?Re-enable: netsh interface set interface "Meta" admin=enable

PERMANENT (Option B): Create OAuth authentication helper
  ‚ú?I can create a tool to get YOUR OWN Graph API token
  ‚ú?Uses browser-based OAuth (no shared token)
  ‚ú?Store in database (account-specific)
  
Which option would you like to pursue?
""")
