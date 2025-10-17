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
    
    Priority:
    1) SQLite DB (servbot.db -> graph_accounts)
    2) graph_email.py example holder
    3) Environment variables
    """
    try:
        # 1) Try database first
        try:
            from .data.database import ensure_db, get_graph_account as db_get_graph_account
            ensure_db()
            acct = db_get_graph_account()
            if acct and acct.get('email') and acct.get('refresh_token') and acct.get('client_id'):
                return acct
        except Exception:
            pass


        
        # 3) Environment variables fallback
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
