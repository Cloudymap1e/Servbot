"""Public API for servbot email verification system.

This module provides the main entry points for using servbot programmatically.
All functionality is exposed through clean, well-documented functions following
Google Python Style Guide conventions.
"""

import datetime as dt
from typing import List, Optional, Dict

from .core.models import Verification, EmailAccount
from .core.verification import (
    fetch_verification_codes,
    get_verification_for_service,
    get_latest_verification,
)
from .clients import GraphClient, FlashmailClient
from .data import ensure_db, upsert_account, find_verification, get_accounts, get_latest_verifications


# Initialize database on import
ensure_db()


# Re-export main functions for convenience
__all__ = [
    # Core functionality
    'fetch_verification_codes',
    'get_verification_for_service',
    'get_latest_verification',
    
    # Flashmail integration
    'provision_flashmail_account',
    'get_flashmail_inventory',
    'get_flashmail_balance',
    
    # Database utilities
    'list_database',
    'get_account_verifications',
    
    # Models
    'Verification',
    'EmailAccount',
    
    # Clients (for advanced usage)
    'GraphClient',
    'FlashmailClient',

    # Browser automation
    'register_service_account',
]


def provision_flashmail_account(
    card: str,
    target_service: str,
    account_type: str = "outlook",
    timeout_seconds: int = 120,
    poll_interval_seconds: int = 5,
    prefer_link: bool = True,
) -> Optional[Dict[str, str]]:
    """Provisions a new Flashmail account and fetches verification for a service.
    
    This is a convenience function that:
    1. Provisions a new email account from Flashmail
    2. Waits for verification email from target service
    3. Extracts and returns the verification code/link
    
    Args:
        card: Flashmail API key
        target_service: Service to fetch verification for (e.g., "Google", "GitHub")
        account_type: Type of account ("outlook" or "hotmail")
        timeout_seconds: How long to wait for verification email
        poll_interval_seconds: Seconds between poll attempts
        prefer_link: Prefer verification links over codes
        
    Returns:
        Dict with keys: email, password, service, value, is_link
        Returns None if provisioning fails or verification times out
        
    Example:
        >>> result = provision_flashmail_account(
        ...     card="your-api-key",
        ...     target_service="GitHub"
        ... )
        >>> if result:
        ...     print(f"Email: {result['email']}")
        ...     print(f"Code: {result['value']}")
    """
    try:
        # Provision account
        client = FlashmailClient(card)
        accounts = client.fetch_accounts(quantity=1, account_type=account_type)
        
        if not accounts:
            return None
        
        account = accounts[0]
        imap_server = FlashmailClient.infer_imap_server(account.email)
        
        # Save complete account credentials (email, password, refresh_token, client_id)
        # All credentials are stored together in the accounts table
        # Use update_only_if_provided=False to ensure all fields are set
        upsert_account(
            email=account.email,
            password=account.password,
            type=account.account_type,
            source="flashmail",
            card=card,
            imap_server=imap_server,
            refresh_token=account.refresh_token,
            client_id=account.client_id,
            update_only_if_provided=False,  # Allow direct updates
        )
        
        # Fetch verification
        # Prefer Graph API if credentials are available, fallback to IMAP
        value = get_verification_for_service(
            target_service=target_service,
            imap_server=imap_server,
            username=account.email,
            password=account.password,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            prefer_link=prefer_link,
            prefer_graph=True,  # Try Graph API first since we just saved Graph credentials
        )
        
        if not value:
            return None
        
        is_link = value.lower().startswith("http://") or value.lower().startswith("https://")
        
        return {
            "email": account.email,
            "password": account.password,
            "service": target_service,
            "value": value,
            "is_link": "true" if is_link else "false",
        }
    
    except Exception:
        return None


def get_flashmail_inventory() -> Dict[str, int]:
    """Gets available account inventory from Flashmail.
    
    Note: This endpoint doesn't require authentication.
    
    Returns:
        Dict with keys "hotmail" and "outlook" containing counts
        
    Example:
        >>> inventory = get_flashmail_inventory()
        >>> print(f"Outlook accounts: {inventory['outlook']}")
    """
    # Create temporary client without card (inventory is public)
    try:
        from .clients.flashmail import _http_get
        import json
        
        status, body, _ = _http_get("/kucun")
        if status == 200:
            data = json.loads(body)
            return {
                "hotmail": int(data.get("hotmail", 0)),
                "outlook": int(data.get("outlook", 0)),
            }
    except Exception:
        pass
    
    return {"hotmail": 0, "outlook": 0}


def get_flashmail_balance(card: str) -> int:
    """Gets remaining credits for Flashmail API key.
    
    Args:
        card: Flashmail API key
        
    Returns:
        Number of remaining credits
        
    Example:
        >>> balance = get_flashmail_balance("your-api-key")
        >>> print(f"Credits remaining: {balance}")
    """
    try:
        client = FlashmailClient(card)
        return client.get_balance()
    except Exception:
        return 0


def list_database(source: Optional[str] = None) -> Dict[str, any]:
    """Lists all data stored in the database.
    
    Args:
        source: Optional filter for account source (e.g., "flashmail", "manual", "file")
        
    Returns:
        Dict with keys "accounts", "messages", "verifications" containing database contents
        
    Example:
        >>> db_contents = list_database()
        >>> print(f"Total accounts: {len(db_contents['accounts'])}")
        >>> for acc in db_contents['accounts']:
        ...     print(f"  {acc['email']} ({acc['source']})")
        >>> 
        >>> print(f"Total verifications: {len(db_contents['verifications'])}")
        >>> for v in db_contents['verifications']:
        ...     print(f"  {v['service']}: {v['value']}")
    """
    import sqlite3
    from .data.database import _connect
    
    try:
        conn = _connect()
        cur = conn.cursor()
        
        # Get accounts (with ALL credentials)
        accounts_query = "SELECT id, email, password, type, source, card, imap_server, refresh_token, client_id, created_at, last_seen_at FROM accounts"
        params = []
        if source:
            accounts_query += " WHERE source = ?"
            params.append(source)
        accounts_query += " ORDER BY created_at DESC"
        
        cur.execute(accounts_query, params)
        accounts = [dict(row) for row in cur.fetchall()]
        
        # Get messages
        cur.execute("""
            SELECT id, provider, mailbox, provider_msg_id, subject, from_addr, 
                   received_date, body_preview, is_read, service, created_at
            FROM messages
            ORDER BY created_at DESC
        """)
        messages = [dict(row) for row in cur.fetchall()]
        
        # Get verifications with joined message info
        cur.execute("""
            SELECT v.id, v.service, v.value, v.is_link, v.created_at,
                   m.mailbox, m.subject, m.from_addr
            FROM verifications v
            JOIN messages m ON v.message_id = m.id
            ORDER BY v.created_at DESC
        """)
        verifications = [dict(row) for row in cur.fetchall()]
        
        # Get graph accounts
        cur.execute("""
            SELECT id, email, client_id, added_at
            FROM graph_accounts
            ORDER BY added_at DESC
        """)
        graph_accounts = [dict(row) for row in cur.fetchall()]
        
        conn.close()
        
        return {
            "accounts": accounts,
            "messages": messages,
            "verifications": verifications,
            "graph_accounts": graph_accounts,
            "summary": {
                "total_accounts": len(accounts),
                "total_messages": len(messages),
                "total_verifications": len(verifications),
                "total_graph_accounts": len(graph_accounts),
            }
        }
    except Exception as e:
        return {
            "accounts": [],
            "messages": [],
            "verifications": [],
            "graph_accounts": [],
            "summary": {"error": str(e)},
        }


def get_account_verifications(email: str, limit: int = 20) -> List[Dict[str, any]]:
    """Gets all verification codes and links for a specific email account.
    
    Args:
        email: Email address to query
        limit: Maximum number of verifications to return (default: 20)
        
    Returns:
        List of verification dicts with service, value, is_link, created_at
        
    Example:
        >>> verifications = get_account_verifications("test@outlook.com")
        >>> for v in verifications:
        ...     vtype = "Link" if v['is_link'] else "Code"
        ...     print(f"{v['service']}: {v['value']} ({vtype})")
    """
    return get_latest_verifications(email, limit)


# Browser automation orchestration

def register_service_account(
    *,
    service: str,
    website_url: str,
    mailbox_email: str | None = None,
    provision_new: bool = False,
    account_type: str = "outlook",
    headless: bool = True,
    timeout_seconds: int = 300,
    prefer_link: bool = True,
    flow_config: Dict | None = None,
    user_data_dir: str | None = None,
    proxy: Dict | None = None,
) -> Optional[Dict[str, any]]:
    """Run a full registration flow for a service website using Playwright.

    - Optionally provisions a new Flashmail mailbox when provision_new is True.
    - Fills the registration form, fetches email verification via Microsoft Graph,
      and completes the sign-up.
    - Persists cookies/storage state and credentials into the registrations table.
    """
    try:
        from .clients.flashmail import FlashmailClient
        from .config import load_flashmail_card
        from .core.models import EmailAccount
        from .automation.engine import BrowserBot
        from .automation.flows.generic import GenericEmailCodeFlow, FlowConfig
        from .data.database import (
            get_accounts,
            upsert_account,
            save_registration,
        )

        # Determine mailbox
        email_acc: EmailAccount | None = None
        if provision_new:
            card = load_flashmail_card()
            if not card:
                return None
            client = FlashmailClient(card)
            accts = client.fetch_accounts(quantity=1, account_type=account_type)
            if not accts:
                return None
            acct = accts[0]
            # Persist account so Graph fetch can use it
            upsert_account(
                email=acct.email,
                password=acct.password,
                type=acct.account_type,
                source="flashmail",
                card=card,
                imap_server=FlashmailClient.infer_imap_server(acct.email),
                refresh_token=acct.refresh_token,
                client_id=acct.client_id,
                update_only_if_provided=False,
            )
            email_acc = EmailAccount(
                email=acct.email,
                password=acct.password,
                account_type=acct.account_type,
                source="flashmail",
                imap_server=FlashmailClient.infer_imap_server(acct.email),
                refresh_token=acct.refresh_token,
                client_id=acct.client_id,
            )
        else:
            if not mailbox_email:
                return None
            acc = None
            for a in get_accounts():
                if a['email'].lower() == mailbox_email.lower():
                    acc = a
                    break
            if not acc:
                return None
            email_acc = EmailAccount(
                email=acc['email'],
                password=acc.get('password', ''),
                account_type=acc.get('type', 'other'),
                source=acc.get('source', 'manual'),
                imap_server=acc.get('imap_server'),
                refresh_token=acc.get('refresh_token'),
                client_id=acc.get('client_id'),
            )

        if not email_acc:
            return None

        # Build flow config
        cfg = FlowConfig(**flow_config) if flow_config else FlowConfig(
            email_input="input[type=email], input[name=email]",
            submit_button="button[type=submit], button:has-text('Sign up'), button:has-text('Create')",
            otp_input="input[name=code], input[name=otp], input[type=tel]",
            success_selector='[data-test="account-home"], .account, .dashboard'
        )
        flow = GenericEmailCodeFlow(
            service_name=service,
            entry_url=website_url,
            config=cfg,
        )

        # First attempt
        # Stealth headless attempt first
        stealth_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--window-size=1280,900",
        ]
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        bot = BrowserBot(
            headless=True,
            user_data_dir=user_data_dir,
            proxy=proxy,
            default_timeout=timeout_seconds,
            user_agent=ua,
            args=stealth_args,
            locale="en-US",
        )
        # Add common headers
        bot.extra_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
        }
        result = bot.run_flow(flow=flow, email_account=email_acc, timeout_sec=timeout_seconds, prefer_link=prefer_link)

        # If concealment fails, fallback to headed complete mode
        if not result.success:
            try:
                bot2 = BrowserBot(
                    headless=False,
                    user_data_dir=user_data_dir,
                    proxy=proxy,
                    default_timeout=timeout_seconds,
                    user_agent=ua,
                    args=stealth_args,
                    locale="en-US",
                )
                bot2.extra_headers = bot.extra_headers
                result = bot2.run_flow(flow=flow, email_account=email_acc, timeout_sec=timeout_seconds, prefer_link=prefer_link)
            except Exception:
                pass

        # Persist registration row
        import json
        reg_id = save_registration(
            service=service,
            website_url=website_url,
            mailbox_email=email_acc.email,
            service_username=result.service_username or "",
            service_password=result.service_password or "",
            status="success" if result.success else "failed",
            error=result.error or "",
            cookies_json=result.cookies_json or "",
            storage_state_json=result.storage_state_json or "",
            user_agent=result.user_agent or "",
            profile_dir=result.profile_dir or "",
            debug_dir=result.debug_dir or "",
            artifacts_json=json.dumps(result.artifacts or []),
        )

        return {
            "registration_id": reg_id,
            "service": service,
            "website_url": website_url,
            "mailbox_email": email_acc.email,
            "service_username": result.service_username,
            "status": "success" if result.success else "failed",
        }
    except Exception as e:
        try:
            import traceback
            print(f"[register_service_account ERROR] {e}")
            traceback.print_exc()
        except Exception:
            pass
        return None

