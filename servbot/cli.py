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
from servbot.data.database import (
    get_accounts,
    upsert_account,
    list_flashmail_cards,
    add_flashmail_card,
    set_default_flashmail_card,
    update_flashmail_card_balance,
    remove_flashmail_card,
)
from servbot.clients import FlashmailClient
from servbot.constants import FLASHMAIL_REFRESH_TOKEN, FLASHMAIL_CLIENT_ID
from servbot.flashmail_cards import (
    register_card as cards_register,
    list_cards as cards_list,
    set_default as cards_set_default,
    remove_card as cards_remove,
    update_balance as cards_update_balance,
    pick_card as cards_pick,
)
from servbot.secure_store import get_secret, set_secret, FLASHMAIL_SERVICE, redact
from servbot.logging_config import setup_logging


class ServbotCLI:
    """Interactive command-line interface for Servbot."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.running = True
        self.flashmail_card = load_flashmail_card()
        
    def run(self):
        """Main CLI loop."""
        # Initialize logging with redaction
        setup_logging(debug=False)
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
        elif cmd == "cards":
            self.cmd_cards(args)
        elif cmd == "register":
            self.cmd_register(args)
        elif cmd == "register-http":
            self.cmd_register_http(args)
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
        print("\nFlashmail Cards (secure):")
        print("  cards                 - List card aliases and balances")
        print("  cards add <alias>     - Add a card (secure prompt)")
        print("  cards rm <alias>      - Remove card metadata (optionally delete secret)")
        print("  cards default <alias> - Set default card alias")
        print("  cards balance         - Refresh and display balances for all cards")
        print("\nBrowser Automation:")
        print("  register <service> --url <signup_url> [--email <mailbox>|--provision outlook|hotmail] ")
        print("                         [--headed|--headless] [--timeout <sec>] [--prefer-code|--prefer-link]")
        print("                         [--config <selectors.json>] [--user-data-dir <path>] ")
        print("                         [--email-selector <css>] [--password-selector <css>] ")
        print("                         [--submit-selector <css>] [--otp-selector <css>] [--success-selector <css>]")
        print("                         [--measure-net] [--traffic-profile minimal|ultra] ")
        print("                         [--block-third-party|--no-block-third-party] [--allow-domains d1,d2]")
        print("\nHTTP-only (no browser):")
        print("  register-http <service> --url <signup_url> [--email MAILBOX | --provision outlook|hotmail]")
        print("                [--username <name>] [--password <pass>] [--timeout <sec>] [--no-db-proxy]")
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
        
        account_type = args[0] if args and args[0] in ["outlook", "hotmail"] else "outlook"

        print(f"\nProvisioning {account_type} account from Flashmail...")
        
        try:
            # Choose card alias if available
            alias = None
            if len(args) >= 2 and args[0] in ("outlook", "hotmail") and args[1] != "":
                alias = args[1]
            elif cards_list():
                alias = cards_pick(min_required_credits=1)
            
            if alias:
                client_obj = cards_register  # just to satisfy type checker; not used
                client = None
                from servbot.flashmail_cards import get_client_by_alias
                client = get_client_by_alias(alias)
                if not client:
                    print(f"Failed to load card alias: {alias}")
                    return
            else:
                # Fallback to single configured card
                if not self.flashmail_card:
                    print("Flashmail API card not configured (data/ai.api)")
                    return
                client = FlashmailClient(self.flashmail_card)
            accounts = client.fetch_accounts(quantity=1, account_type=account_type)
            
            if not accounts:
                print("Failed to provision account.")
                return
            
            account = accounts[0]
            imap_server = FlashmailClient.infer_imap_server(account.email)
            
            # Save to database with per-account credentials (password + per-account Graph OAuth)
            # Flashmail accounts should include per-account refresh_token and client_id
            upsert_account(
                email=account.email,
                password=account.password,
                type=account.account_type,
                source="flashmail",
                card=self.flashmail_card,
                imap_server=imap_server,
                refresh_token=account.refresh_token,
                client_id=account.client_id,
                update_only_if_provided=False,  # Direct update mode
            )
            
            print("\n" + "=" * 70)
            print("ACCOUNT PROVISIONED SUCCESSFULLY")
            print("=" * 70)
            print(f"\nEmail:    {account.email}")
            print(f"Password: {account.password}")
            print(f"Type:     {account.account_type}")
            print(f"IMAP:     {imap_server}")
            # Print credentials as requested (WARNING: sensitive)
            print("\nMicrosoft Graph API credentials (per-account):")
            print(f"  refresh_token: {account.refresh_token}")
            print(f"  client_id    : {account.client_id}")
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
            # If cards module has aliases, show all balances; else fallback to single card
            cards = cards_list()
            if cards:
                print("\nFlashmail API Balances:")
                for c in cards:
                    alias = c['alias']
                    bal = cards_update_balance(alias)
                    bal = bal if bal is not None else c.get('last_known_balance', 0)
                    mark = " [DEFAULT]" if c.get('is_default') else ""
                    print(f"  • {alias}{mark}: {bal} credits")
            else:
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
            print("Usage: add <email> <password>")
            return
        
        email = args[0]
        password = args[1]
        
        try:
            upsert_account(
                email=email,
                password=password,
                source="manual",
                update_only_if_provided=True,  # Use legacy mode for manual adds
            )
            print(f"\nAccount added: {email}")
            print("Manual accounts can use Microsoft Graph when refresh_token and client_id are provided.")
        except Exception as e:
            print(f"Error adding account: {e}")
    
    def cmd_register(self, args: List[str]):
        """Run a browser registration flow.
        
        Usage:
          register SERVICE --url URL [--email MAILBOX | --provision outlook|hotmail]
                           [--headed|--headless] [--timeout SEC] [--prefer-code|--prefer-link]
                           [--config selectors.json]
                           [--user-data-dir PATH]
                           [--email-selector CSS]
                           [--password-selector CSS]
                           [--submit-selector CSS]
                           [--otp-selector CSS]
                           [--success-selector CSS]
                           [--use-db-proxy]
        """
        if not args:
            print("Usage: register SERVICE --url URL [--email MAILBOX | --provision outlook|hotmail]")
            return
        service = args[0]
        # Parse flags
        url = None
        mailbox = None
        provision = None
        headed = False
        headless = True
        timeout = 300
        prefer_link = True
        config_path = None
        user_data_dir = None
        # Quick selector overrides
        quick_cfg = {}
        use_db_proxy = False
        # Network/traffic minimization flags
        measure_net = False
        traffic_profile = None
        block_third_party = False
        allow_domains = None

        i = 1
        while i < len(args):
            a = args[i]
            if a == "--url" and i + 1 < len(args):
                url = args[i+1]; i += 2; continue
            if a == "--email" and i + 1 < len(args):
                mailbox = args[i+1]; i += 2; continue
            if a == "--provision" and i + 1 < len(args):
                provision = args[i+1]; i += 2; continue
            if a == "--headed":
                headed = True; headless = False; i += 1; continue
            if a == "--headless":
                headless = True; headed = False; i += 1; continue
            if a == "--timeout" and i + 1 < len(args):
                try:
                    timeout = int(args[i+1])
                except Exception:
                    pass
                i += 2; continue
            if a == "--prefer-code":
                prefer_link = False; i += 1; continue
            if a == "--prefer-link":
                prefer_link = True; i += 1; continue
            if a == "--config" and i + 1 < len(args):
                config_path = args[i+1]; i += 2; continue
            if a == "--user-data-dir" and i + 1 < len(args):
                user_data_dir = args[i+1]; i += 2; continue
            if a == "--use-db-proxy":
                use_db_proxy = True; i += 1; continue
            if a == "--measure-net":
                measure_net = True; i += 1; continue
            if a == "--traffic-profile" and i + 1 < len(args):
                traffic_profile = args[i+1]; i += 2; continue
            if a == "--block-third-party":
                block_third_party = True; i += 1; continue
            if a == "--no-block-third-party":
                block_third_party = False; i += 1; continue
            if a == "--allow-domains" and i + 1 < len(args):
                allow_domains = [s.strip() for s in args[i+1].split(',') if s.strip()]; i += 2; continue
            # Quick selectors
            if a == "--email-selector" and i + 1 < len(args):
                quick_cfg['email_input'] = args[i+1]; i += 2; continue
            if a == "--password-selector" and i + 1 < len(args):
                quick_cfg['password_input'] = args[i+1]; i += 2; continue
            if a == "--submit-selector" and i + 1 < len(args):
                quick_cfg['submit_button'] = args[i+1]; i += 2; continue
            if a == "--otp-selector" and i + 1 < len(args):
                quick_cfg['otp_input'] = args[i+1]; i += 2; continue
            if a == "--success-selector" and i + 1 < len(args):
                quick_cfg['success_selector'] = args[i+1]; i += 2; continue
            i += 1

        if not url:
            print("Missing --url")
            return
        if not mailbox and not provision:
            print("Provide --email or --provision outlook|hotmail")
            return

        # Load selectors config if provided
        flow_config = {}
        if config_path:
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    flow_config = json.load(f)
            except Exception as e:
                print(f"Failed to read config file: {e}")
                return
        flow_config.update(quick_cfg)
        if 'email_input' not in flow_config:
            flow_config['email_input'] = "input[type=email], input[name=email]"

        # Quick hint if Playwright is not installed
        try:
            import playwright.sync_api  # type: ignore
        except Exception:
            print("[hint] Playwright not installed. Run: pip install playwright && python -m playwright install")

        # Call API orchestration
        from servbot.api import register_service_account

        # Optional proxy from DB
        proxy_dict = None
        if use_db_proxy:
            try:
                from servbot.proxy.bridge import get_playwright_proxy_from_db
                proxy_dict = get_playwright_proxy_from_db(only_working=True)
                if not proxy_dict:
                    print("[warn] No working proxies found in DB; proceeding without proxy")
            except Exception as e:
                print(f"[warn] Failed to load proxy from DB: {e}")

        result = register_service_account(
            service=service,
            website_url=url,
            mailbox_email=mailbox,
            provision_new=bool(provision),
            account_type=(provision or 'outlook'),
            headless=headless,
            timeout_seconds=timeout,
            prefer_link=prefer_link,
            flow_config=flow_config,
            user_data_dir=user_data_dir,
            proxy=proxy_dict,
            traffic_profile=traffic_profile,
            block_third_party=block_third_party,
            allowed_domains=allow_domains,
            measure_network=measure_net,
        )
        if not result:
            print("Registration failed")
            return
        print("\n" + "=" * 70)
        print("REGISTRATION RESULT")
        print("=" * 70)
        print(f"Service:         {result['service']}")
        print(f"Mailbox:         {result['mailbox_email']}")
        print(f"Service Username:{result.get('service_username', '')}")
        print(f"Status:          {result['status']}")
        print(f"Registration ID: {result['registration_id']}")
        print("=" * 70)

    def cmd_register_http(self, args: List[str]):
        """Run a HTTP-only registration flow.
        
        Usage:
          register-http SERVICE --url URL [--email MAILBOX | --provision outlook|hotmail]
                           [--username USERNAME] [--password PASSWORD] [--timeout SEC] [--no-db-proxy]
        """
        if not args:
            print("Usage: register-http SERVICE --url URL [--email MAILBOX | --provision outlook|hotmail]")
            return
        service = args[0]
        # Parse flags
        url = None
        mailbox = None
        provision = None
        username = None
        password = None
        timeout = 300
        use_db_proxy = True

        i = 1
        while i < len(args):
            a = args[i]
            if a == "--url" and i + 1 < len(args):
                url = args[i+1]; i += 2; continue
            if a == "--email" and i + 1 < len(args):
                mailbox = args[i+1]; i += 2; continue
            if a == "--provision" and i + 1 < len(args):
                provision = args[i+1]; i += 2; continue
            if a == "--username" and i + 1 < len(args):
                username = args[i+1]; i += 2; continue
            if a == "--password" and i + 1 < len(args):
                password = args[i+1]; i += 2; continue
            if a == "--timeout" and i + 1 < len(args):
                try:
                    timeout = int(args[i+1])
                except Exception:
                    pass
                i += 2; continue
            if a == "--no-db-proxy":
                use_db_proxy = False; i += 1; continue
            i += 1

        if not url:
            print("Missing --url")
            return
        if not mailbox and not provision:
            print("Provide --email or --provision outlook|hotmail")
            return

        # Call API orchestration
        from servbot.api import register_service_account_http

        result = register_service_account_http(
            service=service,
            website_url=url,
            mailbox_email=mailbox,
            provision_new=bool(provision),
            account_type=(provision or 'outlook'),
            username=username,
            password=password,
            timeout_seconds=timeout,
            use_db_proxy=use_db_proxy,
        )
        if not result:
            print("Registration failed")
            return
        print("\n" + "=" * 70)
        print("REGISTRATION RESULT")
        print("=" * 70)
        print(f"Service:         {result['service']}")
        print(f"Mailbox:         {result['mailbox_email']}")
        print(f"Service Username:{result.get('service_username', '')}")
        print(f"Status:          {result['status']}")
        print(f"Registration ID: {result['registration_id']}")
        print("=" * 70)

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
        """Helper to fetch verification codes for an account via Microsoft Graph only.
        
        Args:
            email: Email address to fetch codes for
        """
        # Get account details from database
        accounts = get_accounts()
        account = next((acc for acc in accounts if acc['email'].lower() == email.lower()), None)
        if not account:
            print(f"Account not found in database: {email}")
            return
        
        print(f"Fetching messages for {email} via Microsoft Graph...")
        
        try:
            # First, check what messages are in the database to show fetching status
            from servbot.data.database import _connect
            conn = _connect()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM messages WHERE mailbox = ?", (email,))
            before_count = cur.fetchone()[0]
            conn.close()
            
            # Fetch verification codes (Graph-only)
            verifications = fetch_verification_codes(
                username=email,
                unseen_only=False,
                limit=50,  # Increased limit
                prefer_graph=True,
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

    def cmd_cards(self, args: List[str]):
        """Manage Flashmail card aliases securely.

        Usage:
          cards                      - list cards
          cards add <alias>          - add card (secure prompt)
          cards rm <alias> [--delete-secret]
          cards default <alias>
          cards balance              - refresh and display balances
        """
        if not args:
            # List cards
            rows = cards_list()
            if not rows:
                print("\nNo cards found. Use 'cards add <alias>' to register.")
                return
            print("\nFlashmail Cards:")
            for r in rows:
                mark = " [DEFAULT]" if r.get('is_default') else ""
                bal = r.get('last_known_balance', 0)
                checked = r.get('last_checked_at') or 'never'
                print(f"  • {r['alias']}{mark} — balance={bal}, last_checked={checked}")
            return

        sub = args[0]
        if sub == 'add' and len(args) >= 2:
            alias = args[1]
            import getpass
            try:
                secret = getpass.getpass(prompt=f"Enter Flashmail card for alias '{alias}': ")
                if not secret:
                    print("No secret entered.")
                    return
                cards_register(alias, secret, set_default=False)
                print(f"Added card alias: {alias}")
            except Exception as e:
                print(f"Error adding card: {e}")
            return
        if sub == 'rm' and len(args) >= 2:
            alias = args[1]
            delete_secret = '--delete-secret' in args[2:]
            try:
                cards_remove(alias, delete_secret=delete_secret)
                print(f"Removed card alias: {alias}")
            except Exception as e:
                print(f"Error removing card: {e}")
            return
        if sub == 'default' and len(args) >= 2:
            alias = args[1]
            try:
                cards_set_default(alias)
                print(f"Default card set to: {alias}")
            except Exception as e:
                print(f"Error setting default: {e}")
            return
        if sub == 'balance':
            try:
                rows = cards_list()
                if not rows:
                    print("No cards found.")
                    return
                print("\nUpdating balances...")
                for r in rows:
                    alias = r['alias']
                    bal = cards_update_balance(alias)
                    mark = " [DEFAULT]" if r.get('is_default') else ""
                    print(f"  • {alias}{mark}: {bal if bal is not None else r.get('last_known_balance', 0)} credits")
            except Exception as e:
                print(f"Error updating balances: {e}")
            return

        print("Unknown 'cards' usage. Type 'help' for commands.")



def main():
    """Main entry point for CLI."""
    cli = ServbotCLI()
    cli.run()


if __name__ == "__main__":
    main()

