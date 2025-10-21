"""Bridge utilities to supply Playwright proxy from the proxy database.

Provides:
- get_playwright_proxy_from_db: pick a (working) proxy from SQLite and return Playwright dict
"""
from __future__ import annotations

from typing import Optional, Dict

from .database import ProxyDatabase


def get_playwright_proxy_from_db(*, only_working: bool = True) -> Optional[Dict[str, str]]:
    """Return a Playwright proxy dict from proxies DB.

    Args:
        only_working: If True, prefer proxies that passed their last test

    Returns:
        Playwright-compatible proxy dict or None if none available
    """
    db = ProxyDatabase("data/proxies.db")
    try:
        endpoints = db.get_working_proxies() if only_working else db.get_all_proxies(active_only=True)
        if not endpoints:
            return None
        # Pick the first
        ep = endpoints[0]
        return ep.as_playwright_proxy()
    finally:
        db.close()