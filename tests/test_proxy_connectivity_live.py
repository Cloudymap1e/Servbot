from __future__ import annotations

"""
Live proxy connectivity tests: iterate DB proxies and verify connectivity to
several random websites to assess general health beyond httpbin.

Enable with SERVBOT_RUN_LIVE=1 or creating RUN_LIVE file.
"""

import os
import random
import time
from pathlib import Path

import pytest

from servbot.proxy.database import ProxyDatabase
from servbot.proxy.tester import ProxyTester


TARGETS = [
    "https://example.com/",
    "https://www.wikipedia.org/",
    "https://www.cloudflare.com/cdn-cgi/trace",
    "https://httpbin.org/ip",
]


def _allow_live() -> bool:
    return (
        os.environ.get("SERVBOT_RUN_LIVE") in {"1", "true", "yes"}
        or Path("RUN_LIVE").exists()
        or Path(__file__).parent.joinpath("RUN_LIVE").exists()
    )


@pytest.mark.live
def test_db_proxies_connectivity_smoke():
    if not _allow_live():
        pytest.skip("live disabled")

    db = ProxyDatabase("data/proxies.db")
    try:
        endpoints = db.get_working_proxies()
        if not endpoints:
            endpoints = db.get_all_proxies(active_only=True)
        assert endpoints, "No proxies in DB"

        # Sample up to 8 proxies
        sample = endpoints[:8]

        successes = 0
        for ep in sample:
            target = random.choice(TARGETS)
            res = ProxyTester.test_single_proxy(ep, test_url=target, timeout=10)
            print(f"tested {ep.host}:{ep.port} -> {target} ok={res.success} code={res.status_code} err={res.error}")
            if res.success:
                successes += 1
            # brief pause to avoid rate-limits
            time.sleep(0.5)

        assert successes >= 1, "No proxies could reach any target"
    finally:
        db.close()


