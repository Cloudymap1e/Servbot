from __future__ import annotations

"""
Live verification that Playwright Chromium uses the configured proxy
(not system/Proxifier), by comparing egress IP from browser vs direct (requests).

Enable with SERVBOT_RUN_LIVE=1 or RUN_LIVE sentinel.
"""

import os
from pathlib import Path

import pytest
import requests

from servbot.automation.engine import BrowserBot
from servbot.proxy.database import ProxyDatabase
from servbot.proxy.models import ProxyEndpoint


IP_ECHO = "https://httpbin.org/ip"
IP_ECHO_ALT = "https://api.ipify.org?format=json"


def _allow_live() -> bool:
    return (
        os.environ.get("SERVBOT_RUN_LIVE") in {"1", "true", "yes"}
        or Path("RUN_LIVE").exists()
        or Path(__file__).parent.joinpath("RUN_LIVE").exists()
    )


@pytest.mark.live
def test_browser_uses_configured_proxy_ip():
    if not _allow_live():
        pytest.skip("live disabled")

    # Direct IP (no proxy)
    direct_ip = None
    try:
        direct_ip = requests.get(IP_ECHO, timeout=10).json().get("origin")
    except Exception:
        pass

    # Pick a proxy from DB (prefer mooproxy SG)
    db = ProxyDatabase("data/proxies.db")
    try:
        eps = db.get_working_proxies() or db.get_all_proxies(active_only=True)
        # Prefer SG region
        eps = [e for e in eps if isinstance(e, ProxyEndpoint) and ((e.region or '').upper() == 'SG' or ('_country-SG_' in (e.password or '')))] or eps
        # Prefer mooproxy provider
        eps = [e for e in eps if (e.provider or '').lower().startswith('mooproxy')] or eps
        assert eps, "No proxies in DB"
        ep = eps[0]
        pw_proxy = ep.as_playwright_proxy()
    finally:
        db.close()

    # Launch headless for speed
    bot = BrowserBot(
        headless=True,
        proxy=pw_proxy,
        traffic_profile="off",
        block_third_party=False,
        measure_network=False,
        default_timeout=15,
    )

    # Minimal flow: just open an ip echo page and read IP via page content
    from servbot.automation.engine import RegistrationFlow, RegistrationResult, ActionHelper
    from servbot.core.models import EmailAccount

    class EchoFlow(RegistrationFlow):
        def __init__(self):
            self.service_name = "Echo"
            self.entry_url = IP_ECHO
        def perform_registration(self, page, actions: ActionHelper, email_account: EmailAccount, fetch_verification, timeout_sec: int, prefer_link: bool) -> RegistrationResult:
            # Fetch via JS to reduce page overhead
            txt = "{}"
            for url in (IP_ECHO, IP_ECHO_ALT):
                try:
                    page.goto("about:blank")
                    data = page.evaluate("(u) => fetch(u, {cache:'no-store'}).then(r=>r.json())", url)
                    import json as _json
                    txt = _json.dumps(data)
                    break
                except Exception:
                    continue
            import json as _json
            try:
                ip = _json.loads(txt).get("origin")
            except Exception:
                try:
                    ip = _json.loads(txt).get("ip")
                except Exception:
                    ip = None
            return RegistrationResult(success=bool(ip), service=self.service_name, website_url=self.entry_url, mailbox_email=email_account.email or "n/a", service_username=ip)

    acc = EmailAccount(email="nobody@example.com", password="x")
    result = bot.run_flow(flow=EchoFlow(), email_account=acc, timeout_sec=30, prefer_link=False)
    proxy_ip = result.service_username

    assert result.success and proxy_ip, "Failed to read browser egress IP"
    if direct_ip:
        assert proxy_ip != direct_ip, f"Browser IP {proxy_ip} should differ from direct IP {direct_ip} when proxy is used"
