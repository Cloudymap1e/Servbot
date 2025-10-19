#!/usr/bin/env python
"""Integration test for servbot with Microsoft Graph API."""

import sys
from pathlib import Path
import pprint
from typing import Optional, Tuple

print("Loading integration_test module...", flush=True)

# Add servbot's parent directory to the path to allow package imports

print("Importing servbot...", flush=True)
from servbot import fetch_verification_codes, GraphClient
print("Imports complete", flush=True)


def load_account_from_file() -> Optional[Tuple[str, str, str, str]]:
    """
    Loads account credentials from data/email.txt.
    
    Format: email----password----refresh_token----client_id
    
    Returns:
        Tuple of (email, password, refresh_token, client_id) or None
    """
    try:
        email_file = Path(__file__).parent / "data" / "email.txt"
        if not email_file.exists():
            print(f"[-] Email file not found: {email_file}")
            return None
        
        content = email_file.read_text().strip()
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not lines:
            print("[-] Email file is empty")
            return None
        
        # Use the last non-empty line
        account_line = lines[-1]
        parts = account_line.split("----")
        
        if len(parts) != 4:
            print(f"[-] Invalid account format. Expected 4 parts, got {len(parts)}")
            print(f"    Format should be: email----password----refresh_token----client_id")
            return None
        
        email, password, refresh_token, client_id = parts
        print(f"[+] Loaded account: {email}")
        return email, password, refresh_token, client_id
        
    except Exception as e:
        print(f"[-] Error loading account: {e}")
        return None


def run_graph_api_test():
    """
    Runs a diagnostic test using Microsoft Graph API to fetch and display
    recent emails, and shows what verification info is parsed from them.
    """
    import sys
    
    def log(msg):
        """Print and flush to ensure output is visible."""
        print(msg, flush=True)
        sys.stdout.flush()
    
    log("="*70)
    log("Microsoft Graph API Integration Test")
    log("="*70)
    
    # Load account credentials
    account = load_account_from_file()
    if not account:
        log("\n[X] Failed to load account credentials")
        return
    
    email, password, refresh_token, client_id = account
    
    # Create Graph client using refresh token - with detailed error handling
    log(f"\n[*] Creating Graph API client...")
    try:
        import requests
        
        # Try to get access token with detailed error reporting
        response = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=10,
        )
        
        if response.status_code != 200:
            log(f"[X] Failed to obtain access token")
            log(f"    Status: {response.status_code}")
            log(f"    Error: {response.text[:300]}")
            
            # Check for specific error codes
            if "AADSTS70000" in response.text:
                log("\n    NOTE: Account flagged for service abuse by Microsoft")
                log("    This is a problem with the account, not the code.")
            
            return
        
        access_token = response.json().get("access_token")
        if not access_token:
            log("[X] No access token in response")
            return
        
        # Create client with the token
        client = GraphClient(access_token, refresh_token, client_id)
        log("[+] Successfully obtained access token")
        
    except Exception as e:
        log(f"[X] Error creating Graph client: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test fetching messages directly
    log(f"\n[*] Fetching messages from inbox...")
    try:
        messages = client.fetch_messages(
            folder="inbox",
            unseen_only=False,
            limit=10
        )
        
        if not messages:
            log("[-] No messages found in inbox")
        else:
            log(f"[+] Found {len(messages)} message(s)")
            log("\nMessage Details:")
            log("-"*70)
            for i, msg in enumerate(messages, 1):
                log(f"\n{i}. Subject: {msg.subject}")
                log(f"   From: {msg.from_addr}")
                log(f"   Date: {msg.received_date}")
                log(f"   Preview: {msg.body_text[:100]}...")
                log(f"   Read: {msg.is_read}")
                
    except Exception as e:
        log(f"[X] Error fetching messages: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test using the main fetch_verification_codes function
    log(f"\n{'='*70}")
    log("Testing fetch_verification_codes with Graph API")
    log("="*70)
    
    try:
        results = fetch_verification_codes(
            username=email,
            password=password,
            folder="INBOX",
            unseen_only=False,
            limit=50,
            prefer_graph=True
        )
        
        if not results:
            log("[-] No verification codes found by the parsing pipeline")
        else:
            log(f"[+] Found {len(results)} verification item(s):")
            log("-"*70)
            for i, verif in enumerate(results, 1):
                log(f"\n{i}. Service: {verif.service}")
                log(f"   Code: {verif.code}")
                log(f"   Is Link: {verif.is_link}")
                log(f"   From: {verif.from_addr}")
                log(f"   Subject: {verif.email_subject}")
                if hasattr(verif, 'confidence'):
                    log(f"   Confidence: {verif.confidence}")
    
    except Exception as e:
        log(f"[X] Error in fetch_verification_codes: {e}")
        import traceback
        traceback.print_exc()
    
    log(f"\n{'='*70}")
    log("Test Complete")
    log("="*70)


def run_imap_fallback_test():
    """
    Tests IMAP fallback using email and password from the account file.
    """
    print("\n" + "="*70)
    print("IMAP Fallback Test")
    print("="*70)
    
    account = load_account_from_file()
    if not account:
        print("[X] Failed to load account credentials")
        return
    
    email, password, _, _ = account
    imap_server = "outlook.office365.com"
    
    print(f"\n[*] Testing IMAP connection to {imap_server}")
    print(f"    Username: {email}")
    
    try:
        results = fetch_verification_codes(
            imap_server=imap_server,
            username=email,
            password=password,
            folder="INBOX",
            unseen_only=False,
            limit=10,
            prefer_graph=False  # Force IMAP
        )
        
        if not results:
            print("[-] No verification codes found via IMAP")
        else:
            print(f"[+] Found {len(results)} verification item(s) via IMAP")
            for i, verif in enumerate(results, 1):
                print(f"\n{i}. Service: {verif.service}, Code: {verif.code}")
    
    except Exception as e:
        print(f"[X] IMAP test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run Graph API test (primary method)
    run_graph_api_test()
    
    # Optionally test IMAP fallback
    # Uncomment to test IMAP as well:
    # run_imap_fallback_test()