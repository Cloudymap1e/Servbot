#!/usr/bin/env python
from __future__ import annotations

"""
Test proxies for a specific provider from the DB against a set of targets.

Usage:
  py -3 scripts/maintenance/test_provider_proxies.py --provider mooproxy-sg --limit 20
"""

import argparse
import random
import time

from servbot.proxy.database import ProxyDatabase
from servbot.proxy.tester import ProxyTester


TARGETS = [
    "https://example.com/",
    "https://www.wikipedia.org/",
    "https://www.cloudflare.com/cdn-cgi/trace",
    "https://httpbin.org/ip",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    db = ProxyDatabase("data/proxies.db")
    try:
        endpoints = [ep for ep in db.get_all_proxies(active_only=True) if (ep.provider or '').lower() == args.provider.lower()]
        if not endpoints:
            print(f"No endpoints found for provider '{args.provider}'.")
            return 1
        sample = endpoints[: args.limit]
        print(f"Testing {len(sample)} proxies for provider '{args.provider}'...")
        ok = 0
        for i, ep in enumerate(sample, 1):
            target = random.choice(TARGETS)
            res = ProxyTester.test_single_proxy(ep, test_url=target, timeout=10)
            print(f"[{i:02d}] {ep.host}:{ep.port} -> {target} ok={res.success} code={res.status_code} err={res.error}")
            ok += 1 if res.success else 0
            time.sleep(0.2)
        print(f"Working: {ok}/{len(sample)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())


