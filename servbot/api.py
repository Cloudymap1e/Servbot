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

