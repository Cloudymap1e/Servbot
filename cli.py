#!/usr/bin/env python
"""
Interactive CLI for Servbot - Email Verification Code Extraction System

This provides a command-line interface for managing email accounts and 
retrieving verification codes.

Available Commands:
- accounts: List all email accounts
- provision: Provision new email account from Flashmail
- check <email>: Check verification codes for specific email
- check-all: Check verification codes for all accounts
- inbox <email>: Fetch latest emails for an account
- balance: Check Flashmail API balance
- help: Show help message
- exit/quit: Exit the program
"""

import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

from servbot import (
    list_database,
    get_account_verifications,
    fetch_verification_codes,
    provision_flashmail_account,
    get_flashmail_balance,
    get_flashmail_inventory,
)
from servbot.config import load_flashmail_card
from servbot.data.database import get_accounts, upsert_account
from servbot.clients import FlashmailClient
from servbot.constants import FLASHMAIL_REFRESH_TOKEN, FLASHMAIL_CLIENT_ID


class ServbotCLI:
    """Interactive command-line interface for Servbot."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.running = True
        self.flashmail_card = load_flashmail_card()
        
    def run(self):
        """Main CLI loop."""
        self.print_banner()
        
        while self.running:
            try:
                command = input("\nservbot> ").strip()
                
                if not command:
                    continue
                    
                self.handle_command(command)
                
            except KeyboardInterrupt:
                print("\n\nUse 'exit' or 'quit' to exit.")
            except EOFError:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def print_banner(self):
        """Print welcome banner."""
        print("=" * 70)
        print("  SERVBOT - Email Verification Code Extraction System")
        print("=" * 70)
        print("\nType 'help' for available commands or 'exit' to quit.\n")
    
    def handle_command(self, command: str):
        """Handle user command.
        
        Args:
            command: User input command string
        """
        parts = command.lower().split()
        
        if not parts:
            return
        
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Command routing
        if cmd in ["exit", "quit", "q"]:
            self.cmd_exit()
        elif cmd in ["help", "h", "?"]:
            self.cmd_help()
        elif cmd in ["accounts", "acc", "list"]:
            self.cmd_accounts(args)
        elif cmd in ["provision", "prov", "new"]:
            self.cmd_provision(args)
        elif cmd in ["check", "verify"]:
            self.cmd_check(args)
        elif cmd == "check-all":
            self.cmd_check_all()
        elif cmd in ["inbox", "fetch", "mail"]:
            self.cmd_inbox(args)
        elif cmd in ["balance", "bal", "credits"]:
            self.cmd_balance()
        elif cmd in ["inventory", "inv", "stock"]:
            self.cmd_inventory()
        elif cmd in ["add", "add-account"]:
            self.cmd_add_account(args)
        elif cmd == "database" or cmd == "db":
            self.cmd_database()
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands.")
    
    def cmd_exit(self):
        """Exit the program."""
        print("\nGoodbye!")
        self.running = False
    
    def cmd_help(self):
        """Show help message."""
        print("\n" + "=" * 70)
        print("AVAILABLE COMMANDS")
        print("=" * 70)
        print("\nAccount Management:")
        print("  accounts [-v]         - List all email accounts in database")
        print("                          Use -v for detailed credential view")
        print("  provision [type]      - Provision new account (outlook/hotmail)")
        print("  add <email> <pass>    - Add account manually to database")
        print("\nVerification Checking:")
        print("  check <email>         - Check verification codes for specific email")
        print("  check-all             - Check verification codes for all accounts")
        print("  inbox <email>         - Fetch latest emails from account inbox")
        print("\nFlashmail API:")
        print("  balance               - Check Flashmail API credit balance")
        print("  inventory             - Check available Flashmail account stock")
        print("\nDatabase:")
        print("  database              - Show complete database contents")
        print("\nGeneral:")
        print("  help                  - Show this help message")
        print("  exit/quit             - Exit the program")
        print("=" * 70)
    
    def cmd_accounts(self, args: List[str]):
        """List all email accounts.
        
        Args:
            args: Optional source filter (e.g., 'flashmail', 'file')
                 Use 'verbose' or '-v' for detailed view
        """
        source = None
        verbose = False
        
        for arg in args:
            if arg.lower() in ['verbose', '-v', '--verbose']:
                verbose = True
            else:
                source = arg
        
        try:
            accounts = get_accounts(source=source)
            
            if not accounts:
                print("\nNo accounts found in database.")
                if source:
                    print(f"(Filtered by source: {source})")
                return
            
            print(f"\n{'=' * 70}")
            print(f"EMAIL ACCOUNTS ({len(accounts)} total)")
            if source:
                print(f"Filtered by source: {source}")
            if verbose:
                print("DETAILED VIEW")
            print("=" * 70)
            
            for i, acc in enumerate(accounts, 1):
                print(f"\n{i}. {acc['email']}")
                print(f"   Type: {acc.get('type', 'N/A')}")
                print(f"   Source: {acc.get('source', 'N/A')}")
                
                if acc.get('password'):
                    pw_len = len(acc['password'])
                    print(f"   Password: {'*' * 10} ({pw_len} chars)")
                
                if acc.get('imap_server'):
                    print(f"   IMAP Server: {acc['imap_server']}")
                
                if acc.get('created_at'):
                    print(f"   Created: {acc['created_at']}")
                
                # Graph API credentials
                has_refresh = bool(acc.get('refresh_token'))
                has_client = bool(acc.get('client_id'))
                
                if verbose:
                    print(f"\n   Credentials Status:")
                    print(f"     Password: {'YES' if acc.get('password') else 'NO'} ({len(acc.get('password', ''))} chars)")
                    print(f"     Refresh Token: {'YES' if has_refresh else 'NO'} ({len(acc.get('refresh_token', ''))} chars)")
                    print(f"     Client ID: {'YES' if has_client else 'NO'} ({len(acc.get('client_id', ''))} chars)")
                    
                    if has_client:
                        print(f"       Client ID: {acc['client_id']}")
                    if has_refresh:
                        rt = acc['refresh_token']
                        print(f"       Refresh Token: {rt[:30]}...{rt[-20:]}")
                
                # Simple status
                if has_refresh and has_client:
                    print(f"   Graph API: [OK] Configured")
                else:
                    print(f"   Graph API: [NO] Not configured")
            
            print("=" * 70)
            if not verbose:
                print("Use 'accounts -v' for detailed credential information")
            
        except Exception as e:
            print(f"Error listing accounts: {e}")
    
    def cmd_provision(self, args: List[str]):
        """Provision new email account from Flashmail.
        
        Args:
            args: Optional account type (outlook/hotmail)
        """
        if not self.flashmail_card:
            print("\nError: Flashmail API key not configured!")
            print("Please add FLASHMAIL_CARD to data/ai.api")
            print('Format: FLASHMAIL_CARD = "your_api_key"')
            return
        
        account_type = args[0] if args else "outlook"
        
        if account_type not in ["outlook", "hotmail"]:
            print(f"Invalid account type: {account_type}")
            print("Valid types: outlook, hotmail")
            return
        
        print(f"\nProvisioning {account_type} account from Flashmail...")
        
        try:
            client = FlashmailClient(self.flashmail_card)
            accounts = client.fetch_accounts(quantity=1, account_type=account_type)
            
            if not accounts:
                print("Failed to provision account.")
                return
            
            account = accounts[0]
            imap_server = FlashmailClient.infer_imap_server(account.email)
            
            # Save to database with all credentials (password + Microsoft Graph OAuth)
            # Flashmail accounts support both IMAP and Microsoft Graph API
            upsert_account(
                email=account.email,
                password=account.password,
                type=account.account_type,
                source="flashmail",
                card=self.flashmail_card,
                imap_server=imap_server,
                refresh_token=FLASHMAIL_REFRESH_TOKEN,
                client_id=FLASHMAIL_CLIENT_ID,
                update_only_if_provided=False,  # Direct update mode
            )
            
            print("\n" + "=" * 70)
            print("ACCOUNT PROVISIONED SUCCESSFULLY")
            print("=" * 70)
            print(f"\nEmail:    {account.email}")
            print(f"Password: {account.password}")
            print(f"Type:     {account.account_type}")
            print(f"IMAP:     {imap_server}")
            print(f"\nMicrosoft Graph API: Enabled (OAuth credentials saved)")
            print("  → Supports both IMAP and Graph API for email fetching")
            print("\nAccount saved to database.")
            print("=" * 70)
            
        except Exception as e:
            print(f"Error provisioning account: {e}")
    
    def cmd_check(self, args: List[str]):
        """Check verification codes for specific email.
        
        Args:
            args: Email address to check
        """
        if not args:
            print("Usage: check <email>")
            return
        
        email = args[0]
        
        print(f"\nChecking verification codes for {email}...")
        
        try:
            # First check database for recent codes
            verifications = get_account_verifications(email, limit=20)
            
            if verifications:
                print("\n" + "=" * 70)
                print(f"VERIFICATION CODES FOR {email}")
                print("=" * 70)
                
                for i, v in enumerate(verifications, 1):
                    v_type = "Link" if v['is_link'] else "Code"
                    print(f"\n{i}. {v['service']}")
                    print(f"   Value: {v['value']}")
                    print(f"   Type:  {v_type}")
                    print(f"   Date:  {v.get('created_at', 'N/A')}")
                
                print("=" * 70)
            else:
                print(f"No verification codes found for {email}.")
                print("\nTrying to fetch new codes from inbox...")
                
                # Try to fetch fresh codes
                self._fetch_codes_for_account(email)
                
        except Exception as e:
            print(f"Error checking codes: {e}")
    
    def cmd_check_all(self):
        """Check verification codes for all accounts."""
        try:
            accounts = get_accounts()
            
            if not accounts:
                print("\nNo accounts found in database.")
                return
            
            print(f"\nChecking verification codes for {len(accounts)} account(s)...")
            
            for acc in accounts:
                email = acc['email']
                print(f"\n{'=' * 70}")
                print(f"Checking: {email}")
                print("=" * 70)
                
                verifications = get_account_verifications(email, limit=5)
                
                if verifications:
                    for v in verifications:
                        v_type = "Link" if v['is_link'] else "Code"
                        print(f"  • {v['service']}: {v['value']} ({v_type})")
                else:
                    print("  No verification codes found.")
            
            print("\n" + "=" * 70)
            
        except Exception as e:
            print(f"Error checking all accounts: {e}")
    
    def cmd_inbox(self, args: List[str]):
        """Fetch latest emails from account inbox.
        
        Args:
            args: Email address to check
        """
        if not args:
            print("Usage: inbox <email>")
            return
        
        email = args[0]
        
        print(f"\nFetching inbox for {email}...")
        
        try:
            self._fetch_codes_for_account(email)
        except Exception as e:
            print(f"Error fetching inbox: {e}")
    
    def cmd_balance(self):
        """Check Flashmail API balance."""
        if not self.flashmail_card:
            print("\nError: Flashmail API key not configured!")
            print("Please add FLASHMAIL_CARD to data/ai.api")
            return
        
        try:
            balance = get_flashmail_balance(self.flashmail_card)
            print(f"\nFlashmail API Balance: {balance} credits")
        except Exception as e:
            print(f"Error checking balance: {e}")
    
    def cmd_inventory(self):
        """Check Flashmail inventory."""
        try:
            inventory = get_flashmail_inventory()
            print("\n" + "=" * 70)
            print("FLASHMAIL INVENTORY")
            print("=" * 70)
            print(f"Outlook accounts: {inventory.get('outlook', 0)}")
            print(f"Hotmail accounts: {inventory.get('hotmail', 0)}")
            print("=" * 70)
        except Exception as e:
            print(f"Error checking inventory: {e}")
    
    def cmd_add_account(self, args: List[str]):
        """Add account manually to database.
        
        Args:
            args: Email and password
        """
        if len(args) < 2:
            print("Usage: add <email> <password> [imap_server]")
            return
        
        email = args[0]
        password = args[1]
        imap_server = args[2] if len(args) > 2 else None
        
        try:
            upsert_account(
                email=email,
                password=password,
                source="manual",
                imap_server=imap_server,
                update_only_if_provided=True,  # Use legacy mode for manual adds
            )
            print(f"\nAccount added: {email}")
            print("Note: Manual accounts use IMAP. To enable Graph API, provide refresh_token and client_id.")
        except Exception as e:
            print(f"Error adding account: {e}")
    
    def cmd_database(self):
        """Show complete database contents."""
        try:
            db = list_database()
            
            print("\n" + "=" * 70)
            print("DATABASE CONTENTS")
            print("=" * 70)
            
            summary = db.get('summary', {})
            print(f"\nTotal Accounts:       {summary.get('total_accounts', 0)}")
            print(f"Total Messages:       {summary.get('total_messages', 0)}")
            print(f"Total Verifications:  {summary.get('total_verifications', 0)}")
            print(f"Total Graph Accounts: {summary.get('total_graph_accounts', 0)}")
            
            # Show recent verifications
            verifications = db.get('verifications', [])
            if verifications:
                print("\n" + "-" * 70)
                print("RECENT VERIFICATIONS (Last 10)")
                print("-" * 70)
                
                for v in verifications[:10]:
                    v_type = "Link" if v['is_link'] else "Code"
                    print(f"\n• {v['service']}")
                    print(f"  Value:   {v['value']}")
                    print(f"  Type:    {v_type}")
                    print(f"  Mailbox: {v.get('mailbox', 'N/A')}")
                    print(f"  Date:    {v.get('created_at', 'N/A')}")
            
            print("\n" + "=" * 70)
            
        except Exception as e:
            print(f"Error reading database: {e}")
    
    def _fetch_codes_for_account(self, email: str):
        """Helper to fetch verification codes for an account.
        
        Args:
            email: Email address to fetch codes for
        """
        # Get account details from database
        accounts = get_accounts()
        account = None
        
        for acc in accounts:
            if acc['email'].lower() == email.lower():
                account = acc
                break
        
        if not account:
            print(f"Account not found in database: {email}")
            return
        
        password = account.get('password')
        imap_server = account.get('imap_server')
        
        if not password:
            print("Error: Account password not available.")
            return
        
        # Determine IMAP server if not set
        if not imap_server:
            if 'outlook' in email.lower() or 'hotmail' in email.lower() or 'live' in email.lower():
                imap_server = "outlook.office365.com"
            elif 'gmail' in email.lower():
                imap_server = "imap.gmail.com"
            else:
                print("Error: IMAP server not configured for this account.")
                return
        
        print(f"Connecting to {imap_server}...")
        
        try:
            # First, check what messages are in the database to show fetching status
            from servbot.data.database import _connect
            conn = _connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email,))
            before_count = cur.fetchone()[0]
            conn.close()
            
            # Fetch verification codes
            verifications = fetch_verification_codes(
                imap_server=imap_server,
                username=email,
                password=password,
                unseen_only=False,
                limit=50,  # Increased limit
                prefer_graph=True,  # Try Graph API first if available
            )
            
            # Check how many messages were fetched
            conn = _connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email,))
            after_count = cur.fetchone()[0]
            
            # Get recent messages to show what was fetched
            cur.execute("""
                SELECT subject, from_addr, received_date, body_preview
                FROM messages
                WHERE mailbox = ?
                ORDER BY received_date DESC
                LIMIT 10
            """, (email,))
            messages = cur.fetchall()
            conn.close()
            
            new_messages = after_count - before_count
            
            print(f"\nFetched {after_count} total messages ({new_messages} new)")
            
            if messages:
                print("\n" + "=" * 70)
                print("RECENT MESSAGES IN INBOX")
                print("=" * 70)
                for i, msg in enumerate(messages, 1):
                    print(f"\n{i}. {msg[0]}")
                    print(f"   From: {msg[1]}")
                    print(f"   Date: {msg[2] or 'N/A'}")
                    if msg[3]:
                        preview = msg[3][:80] + "..." if len(msg[3]) > 80 else msg[3]
                        print(f"   Preview: {preview}")
            
            if verifications:
                print("\n" + "=" * 70)
                print(f"VERIFICATION CODES FOUND ({len(verifications)} total)")
                print("=" * 70)
                
                for i, v in enumerate(verifications, 1):
                    v_type = "Link" if v.is_link else "Code"
                    print(f"\n{i}. {v.service}")
                    print(f"   Value:   {v.code}")
                    print(f"   Type:    {v_type}")
                    print(f"   Subject: {v.subject}")
                    print(f"   From:    {v.from_addr}")
                    print(f"   Date:    {v.date or 'N/A'}")
                
                print("\n" + "=" * 70)
                print("Codes saved to database.")
            else:
                print("\n" + "=" * 70)
                print("NO VERIFICATION CODES DETECTED")
                print("=" * 70)
                if messages:
                    print("\nMessages were fetched but no verification codes were found.")
                    print("This could mean:")
                    print("  1. The verification email hasn't arrived yet")
                    print("  2. The code pattern isn't recognized (check message preview above)")
                    print("  3. The email is in a different folder")
                else:
                    print("\nNo messages found in inbox.")
                    print("The account may be empty or emails aren't syncing yet.")
                
        except Exception as e:
            print(f"Error fetching codes: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point for CLI."""
    cli = ServbotCLI()
    cli.run()


if __name__ == "__main__":
    main()

