"""
Configuration loader for API keys and credentials.

Loads settings from the data directory.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any


def get_data_dir() -> Path:
    """Get the data directory path."""
    return Path(__file__).parent / "data"


def load_cerebras_key() -> Optional[str]:
    """Load Cerebras API key from data/ai.api file."""
    try:
        ai_api_file = get_data_dir() / "ai.api"
        if not ai_api_file.exists():
            return None
        
        content = ai_api_file.read_text()
        for line in content.split('\n'):
            if line.startswith('CEREBRAS_KEY'):
                # Extract key from line like: CEREBRAS_KEY = "key"
                return line.split('=')[1].strip().strip('"\'')
        return None
    except Exception:
        return None


def load_flashmail_card() -> Optional[str]:
    """Load Flashmail API card from data/ai.api file."""
    try:
        ai_api_file = get_data_dir() / "ai.api"
        if not ai_api_file.exists():
            return None
        
        content = ai_api_file.read_text()
        for line in content.split('\n'):
            if line.startswith('FLASHMAIL_CARD'):
                # Extract key from line like: FLASHMAIL_CARD = "key"
                return line.split('=')[1].strip().strip('"\'')
        return None
    except Exception:
        return None


def load_graph_account() -> Optional[Dict[str, str]]:
    """
    Load Microsoft Graph API account credentials.
    
    DEPRECATED: Use load_account_credentials() for new code.
    This function is kept for backward compatibility.
    
    Priority:
    1) SQLite DB (servbot.db -> accounts table - preferred)
    2) SQLite DB (servbot.db -> graph_accounts table - legacy)
    3) Environment variables fallback
    
    Returns:
        Dict with keys: email, refresh_token, client_id
        Returns None if no credentials found
    """
    try:
        # 1) Try accounts table first (new unified storage)
        try:
            from .data.database import ensure_db, get_accounts
            ensure_db()
            
            # Get first account with Graph credentials
            accounts = get_accounts()
            for acc in accounts:
                if acc.get('refresh_token') and acc.get('client_id'):
                    return {
                        'email': acc['email'],
                        'refresh_token': acc['refresh_token'],
                        'client_id': acc['client_id'],
                    }
        except Exception:
            pass
        
        # 2) Try legacy graph_accounts table
        try:
            from .data.database import get_graph_account as db_get_graph_account
            acct = db_get_graph_account()
            if acct and acct.get('email') and acct.get('refresh_token') and acct.get('client_id'):
                return acct
        except Exception:
            pass
        
        # 3) Environment variables fallback
        # Prefer single combined string if provided: GRAPH_ACCOUNT = "email----password----refresh_token----client_id"
        combined = os.getenv('GRAPH_ACCOUNT')
        if combined and '----' in combined:
            try:
                parts = [p.strip() for p in combined.split('----')]
                if len(parts) == 4:
                    email, _pw, rt, cid = parts
                    if email and rt and cid:
                        return {
                            'email': email,
                            'refresh_token': rt,
                            'client_id': cid,
                        }
            except Exception:
                pass
        
        # Legacy separate vars
        email = os.getenv('GRAPH_EMAIL')
        refresh_token = os.getenv('GRAPH_REFRESH_TOKEN')
        client_id = os.getenv('GRAPH_CLIENT_ID')
        
        if email and refresh_token and client_id:
            return {
                'email': email,
                'refresh_token': refresh_token,
                'client_id': client_id
            }
        
        return None
    except Exception:
        return None


def load_account_credentials(email: str) -> Optional[Dict[str, str]]:
    """Load credentials for a specific email account.
    
    This is the preferred method for loading account credentials.
    Checks the unified accounts table first, with fallbacks.
    
    Args:
        email: Email address to load credentials for
        
    Returns:
        Dict with account credentials including:
        - email: Email address
        - password: Account password (if IMAP)
        - refresh_token: OAuth refresh token (if Microsoft Graph)
        - client_id: OAuth client ID (if Microsoft Graph)
        - imap_server: IMAP server address (if IMAP)
        - type: Account type (outlook, hotmail, other)
        - source: Account source (flashmail, manual, file, migrated)
        
        Returns None if account not found
        
    Example:
        >>> creds = load_account_credentials("user@outlook.com")
        >>> if creds and creds.get('refresh_token'):
        ...     # Use Microsoft Graph API
        ...     client = GraphClient.from_credentials(
        ...         creds['refresh_token'],
        ...         creds['client_id'],
        ...         mailbox=creds['email']
        ...     )
        >>> elif creds and creds.get('password'):
        ...     # Use IMAP
        ...     client = IMAPClient(
        ...         creds['imap_server'],
        ...         creds['email'],
        ...         creds['password']
        ...     )
    """
    try:
        from .data.database import ensure_db, get_accounts
        ensure_db()
        
        accounts = get_accounts()
        for acc in accounts:
            if acc['email'].lower() == email.lower():
                return acc
        
        return None
    except Exception:
        return None


# Global config cache
_CONFIG_CACHE: Dict[str, Any] = {}


def get_config(key: str, loader_func=None, default=None):
    """Get configuration value with caching."""
    if key not in _CONFIG_CACHE:
        if loader_func:
            _CONFIG_CACHE[key] = loader_func()
        else:
            _CONFIG_CACHE[key] = default
    return _CONFIG_CACHE[key] or default


def load_groq_key() -> Optional[str]:
    """Load Groq API key from env or data/ai.api.
    Checks env: GROQ_API_KEY, GROQ_API; then data/ai.api line GROQ_API = "...".
    """
    import os
    # Env first
    key = os.getenv('GROQ_API_KEY') or os.getenv('GROQ_API')
    if key:
        return key.strip()
    try:
        ai_api_file = get_data_dir() / "ai.api"
        if not ai_api_file.exists():
            return None
        content = ai_api_file.read_text()
        for line in content.split('\n'):
            if line.strip().startswith('GROQ_API') and '=' in line:
                return line.split('=', 1)[1].strip().strip('"\'')
    except Exception:
        pass
    return None
