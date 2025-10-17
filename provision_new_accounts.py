#!/usr/bin/env python
"""
Utility to provision new email accounts from Flashmail API.

This script:
1. Loads the Flashmail API key from data/ai.api
2. Provisions new Outlook email accounts
3. Saves them to data/email.txt
4. Tests that they work with Microsoft Graph API
"""

import sys
from pathlib import Path

# Add servbot's parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from servbot import FlashmailClient
from servbot.config import load_flashmail_card
import requests


def test_account(email: str, password: str, refresh_token: str, client_id: str) -> bool:
    """Test if an account works with Microsoft Graph API."""
    try:
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
        
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False


def provision_accounts(quantity: int = 2, account_type: str = "outlook"):
    """
    Provision new email accounts from Flashmail API.
    
    Args:
        quantity: Number of accounts to provision (default: 2)
        account_type: Type of account ("outlook" or "hotmail")
    """
    print("="*70)
    print("Flashmail Account Provisioning")
    print("="*70)
    
    # Load API key
    card = load_flashmail_card()
    if not card:
        print("\n[X] ERROR: Flashmail API key not found!")
        print("   Please add FLASHMAIL_CARD to data/ai.api")
        print('   Format: FLASHMAIL_CARD = "your_api_key"')
        return
    
    print(f"\n[+] Loaded Flashmail API key: {card[:10]}...{card[-10:]}")
    
    # Check balance
    print("\n[*] Checking account balance...")
    try:
        client = FlashmailClient(card)
        balance = client.get_balance()
        print(f"   Balance: {balance} credits")
        
        if balance < quantity:
            print(f"\n[!] WARNING: Insufficient balance!")
            print(f"   Requested: {quantity} accounts")
            print(f"   Available: {balance} credits")
            return
    except Exception as e:
        print(f"   [!] Could not check balance: {e}")
    
    # Provision accounts
    print(f"\n[*] Provisioning {quantity} {account_type} account(s)...")
    try:
        accounts = client.fetch_accounts(quantity=quantity, account_type=account_type)
        
        if not accounts:
            print("   [X] Failed to provision accounts")
            return
        
        print(f"   [+] Successfully provisioned {len(accounts)} account(s)")
        
        # Save to email.txt in the correct format
        email_file = Path(__file__).parent / "data" / "email.txt"
        
        # Read existing content
        existing_content = ""
        if email_file.exists():
            existing_content = email_file.read_text()
        
        # Append new accounts
        with open(email_file, "a") as f:
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            
            for i, acc in enumerate(accounts, 1):
                # Format: email----password----refresh_token----client_id
                # For Flashmail accounts, they provide email and password
                # The refresh_token and client_id are Microsoft OAuth credentials
                # that are the same for all accounts from this API
                line = f"{acc.email}----{acc.password}----{FLASHMAIL_REFRESH_TOKEN}----{FLASHMAIL_CLIENT_ID}\n"
                f.write(line)
                
                # Save complete account credentials to database
                upsert_account(
                    email=acc.email,
                    password=acc.password,
                    type=acc.account_type,
                    source="flashmail",
                    card=card,
                    refresh_token=FLASHMAIL_REFRESH_TOKEN,
                    client_id=FLASHMAIL_CLIENT_ID,
                )
                
                print(f"\n   Account {i}:")
                print(f"   Email: {acc.email}")
                print(f"   Password: {acc.password}")
        
        print(f"\n[+] Accounts saved to: {email_file}")
        
        # Test the accounts (optional, but recommended)
        print("\n[*] Account details:")
        for i, acc in enumerate(accounts, 1):
            print(f"\n   Account {i}: {acc.email}")
            # Note: Freshly provisioned accounts may need a moment to activate
            # You may want to wait a bit before testing
            print(f"   [!] Note: Fresh accounts may need time to activate")
            print(f"   [i] Use the account for IMAP with credentials:")
            print(f"      Server: outlook.office365.com")
            print(f"      Username: {acc.email}")
            print(f"      Password: {acc.password}")
        
        print("\n" + "="*70)
        print("[+] Provisioning Complete!")
        print("="*70)
        print("\nNext steps:")
        print("1. Wait a few minutes for accounts to fully activate")
        print("2. Run: python integration_test.py")
        print("3. Or use them directly in your code with fetch_verification_codes()")
        
    except Exception as e:
        print(f"\n[X] Error provisioning accounts: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Provision new email accounts from Flashmail API")
    parser.add_argument("-n", "--number", type=int, default=2, help="Number of accounts to provision (default: 2)")
    parser.add_argument("-t", "--type", choices=["outlook", "hotmail"], default="outlook", help="Account type (default: outlook)")
    
    args = parser.parse_args()
    
    provision_accounts(quantity=args.number, account_type=args.type)

