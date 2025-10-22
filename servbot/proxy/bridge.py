"""Bridge utilities to supply proxies from the proxy database.

Provides:
- get_playwright_proxy_from_db: pick a (working) proxy and return Playwright dict
- get_requests_proxies_from_db: pick a (working) proxy and return requests proxies mapping
- get_proxy_endpoint_from_db: pick and return the raw ProxyEndpoint
"""
from __future__ import annotations

from typing import Optional, Dict

from .database import ProxyDatabase
from .models import ProxyEndpoint


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


def get_requests_proxies_from_db(*, only_working: bool = True) -> Optional[Dict[str, str]]:
    """Return a requests-compatible proxies mapping from proxies DB.

    Args:
        only_working: If True, prefer proxies that passed their last test

    Returns:
        requests-compatible proxies dict or None if none available
    """
    db = ProxyDatabase("data/proxies.db")
    try:
        endpoints = db.get_working_proxies() if only_working else db.get_all_proxies(active_only=True)
        if not endpoints:
            return None
        ep = endpoints[0]
        return ep.as_requests_proxies()
    finally:
        db.close()


def get_proxy_endpoint_from_db(*, only_working: bool = True) -> Optional[ProxyEndpoint]:
    """Return a ProxyEndpoint selected from the proxies DB.

    Args:
        only_working: If True, prefer proxies that passed their last test

    Returns:
        ProxyEndpoint or None
    """
    db = ProxyDatabase("data/proxies.db")
    try:
        endpoints = db.get_working_proxies() if only_working else db.get_all_proxies(active_only=True)
        if not endpoints:
            return None
        return endpoints[0]
    finally:
        db.close()