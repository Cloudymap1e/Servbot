"""Demo script to showcase new database features.

This script demonstrates:
1. Listing database contents
2. Getting account verifications
3. Mock account provisioning
"""

import sys
import os

from servbot import list_database
from unittest.mock import patch


def print_separator(char="=", width=70):
    """Print a separator line."""
    print(char * width, flush=True)


def print_header(text):
    """Print a section header."""
    print(f"\n{text}", flush=True)
    print_separator("-")


# Main demo
if __name__ == "__main__":
    print_separator()
    print(" SERVBOT DATABASE FEATURES DEMO", flush=True)
    print_separator()
    
    # Feature 1: List Database
    print_header("FEATURE 1: List All Database Contents")
    db = list_database()
    
    print(f"Total Accounts: {db['summary']['total_accounts']}", flush=True)
    print(f"Total Messages: {db['summary']['total_messages']}", flush=True)
    print(f"Total Verifications: {db['summary']['total_verifications']}", flush=True)
    print(f"Total Graph Accounts: {db['summary']['total_graph_accounts']}", flush=True)
    
    if db['accounts']:
        print("\nSample Accounts:", flush=True)
        for acc in db['accounts'][:5]:
            print(f"  - {acc['email']} (source: {acc['source']}, type: {acc['type']})", flush=True)
    
    if db['verifications']:
        print("\nRecent Verifications:", flush=True)
        for v in db['verifications'][:5]:
            v_type = "Link" if v['is_link'] else "Code"
            preview = v['value'][:40] + "..." if len(v['value']) > 40 else v['value']
            print(f"  - {v['service']}: {preview} ({v_type})", flush=True)
    
    # Feature 2: Get Account Verifications
    if db['accounts']:
        print_header("FEATURE 2: Get Verifications for Specific Account")
        sample_email = db['accounts'][0]['email']
        verifs = get_account_verifications(sample_email, limit=10)
        
        print(f"Verifications for {sample_email}:", flush=True)
        if verifs:
            for v in verifs:
                v_type = "Link" if v['is_link'] else "Code"
                print(f"  - {v['service']}: {v['value']} ({v_type})", flush=True)
                print(f"    Created: {v['created_at']}", flush=True)
        else:
            print("  No verifications found for this account.", flush=True)
    
    # Feature 3: Mock Account Provisioning
    print_header("FEATURE 3: Mock Flashmail Account Provisioning")
    
    with patch('servbot.clients.flashmail._http_get') as mock_http:
        # Mock API response
        mock_http.return_value = (200, "mock_demo@outlook.com----MockPassword123", {})
        
        client = FlashmailClient(card="DEMO_API_KEY")
        accounts = client.fetch_accounts(quantity=1, account_type="outlook")
        
        print("Successfully mocked account provisioning!", flush=True)
        print(f"  Email: {accounts[0].email}", flush=True)
        print(f"  Password: {accounts[0].password}", flush=True)
        print(f"  Source: {accounts[0].source}", flush=True)
    
    # Feature 4: Mock Flashmail API
    print_header("FEATURE 4: Mock Flashmail API Endpoints")
    
    with patch('servbot.clients.flashmail._http_get') as mock_http:
        # Test inventory
        mock_http.return_value = (200, '{"hotmail": 150, "outlook": 300}', {})
        client = FlashmailClient(card="DEMO_KEY")
        inventory = client.get_inventory()
        print(f"Inventory (mocked):", flush=True)
        print(f"  Hotmail: {inventory['hotmail']} available", flush=True)
        print(f"  Outlook: {inventory['outlook']} available", flush=True)
        
        # Test balance
        mock_http.return_value = (200, '{"num": 42}', {})
        balance = client.get_balance()
        print(f"Balance (mocked): {balance} credits", flush=True)
    
    # Summary
    print_separator()
    print(" DEMO COMPLETE!", flush=True)
    print_separator()
    print("\nKEY TAKEAWAYS:", flush=True)
    print("  1. Use list_database() to see everything stored", flush=True)
    print("  2. Use get_account_verifications(email) for specific account codes", flush=True)
    print("  3. All codes/links are AUTOMATICALLY saved to DB when fetched", flush=True)
    print("  4. Mock testing works for all Flashmail API operations", flush=True)
    print("\nSee DATABASE_AND_TESTING.md for full documentation.\n", flush=True)

