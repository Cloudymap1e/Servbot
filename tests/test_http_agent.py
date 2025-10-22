from __future__ import annotations

"""
Unit tests for BrowserLikeSession basic behaviors: default headers and proxies mapping
without performing real network I/O.
"""

from servbot.automation.http.agent import BrowserLikeSession


def test_session_initial_headers_and_proxies_mapping():
    proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
    s = BrowserLikeSession(proxies=proxies, timeout=5)

    # Headers should include a desktop UA and common browser headers
    h = s.session.headers
    assert "User-Agent" in h and "Chrome" in h["User-Agent"]
    for key in ("Accept", "Accept-Language", "Accept-Encoding"):
        assert key in h

    # Proxies mapping applied to underlying session
    assert s.session.proxies.get("http") == proxies["http"]
    assert s.session.proxies.get("https") == proxies["https"]

    s.close()


