"""
Network metering for Playwright (sync) using Chrome DevTools Protocol.

Captures on-wire bytes via Network.loadingFinished. Aggregates totals by
resource type and domain. Designed to be light-weight and opt-in.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def _domain_from_url(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        return host.lower()
    except Exception:
        return ""


@dataclass
class _Req:
    url: str
    rtype: str
    domain: str


class NetworkMeter:
    """CDP-based network meter.

    Usage (sync Playwright):
        meter = NetworkMeter(profile_name="ultra", allowlist=[...])
        meter.start(page)
        ... do work ...
        meter.stop()
        meter.save_json(path)
    """

    def __init__(self, *, profile_name: str = "off", allowlist: Optional[list[str]] = None):
        self._session = None
        self._started = False
        self._by_id: Dict[str, _Req] = {}
        self._totals_bytes = 0
        self._totals_count = 0
        self._per_type: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"bytes": 0, "requests": 0})
        self._per_domain: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"bytes": 0, "requests": 0})
        self.blocked = {"images": 0, "fonts": 0, "media": 0, "stylesheets": 0, "third_party": 0, "analytics": 0}
        self._timings: Dict[str, float] = {}
        self._profile_name = profile_name
        self._allowlist = [d.lower() for d in (allowlist or [])]

    def start(self, page) -> None:
        if self._started:
            return
        try:
            ctx = page.context
            self._session = ctx.new_cdp_session(page)
            self._session.send("Network.enable")
            # Timings
            self._timings["meter_start"] = time.time()

            def _on_response(params: Dict[str, Any]):
                try:
                    req_id = params.get("requestId")
                    resp = params.get("response", {})
                    url = resp.get("url", "")
                    rtype = (params.get("type") or "other").lower()
                    domain = _domain_from_url(url)
                    if req_id:
                        self._by_id[req_id] = _Req(url=url, rtype=rtype, domain=domain)
                except Exception:
                    pass

            def _on_finished(params: Dict[str, Any]):
                try:
                    req_id = params.get("requestId")
                    size = int(params.get("encodedDataLength") or 0)
                    meta = self._by_id.get(req_id)
                    if not meta:
                        return
                    self._totals_count += 1
                    self._totals_bytes += size
                    tbin = self._per_type[meta.rtype]
                    tbin["bytes"] += size
                    tbin["requests"] += 1
                    dbin = self._per_domain[meta.domain]
                    dbin["bytes"] += size
                    dbin["requests"] += 1
                except Exception:
                    pass

            # Hook events
            self._session.on("Network.responseReceived", _on_response)
            self._session.on("Network.loadingFinished", _on_finished)
        except Exception:
            # If CDP not available, meter stays inactive
            self._session = None
        self._started = True

    def stop(self) -> None:
        self._timings["meter_stop"] = time.time()
        try:
            if self._session:
                # Best-effort detach
                self._session.detach()
        except Exception:
            pass

    def set_blocked_counters(self, counters: Dict[str, int]) -> None:
        try:
            for k in self.blocked.keys():
                if k in counters:
                    self.blocked[k] = int(counters[k])
        except Exception:
            pass

    def get_summary(self) -> Dict[str, Any]:
        return {
            "profile": {
                "traffic_profile": self._profile_name,
                "allowed_domains": self._allowlist,
            },
            "totals": {
                "encoded_bytes": self._totals_bytes,
                "requests": self._totals_count,
            },
            "per_type": self._per_type,
            "per_domain": self._per_domain,
            "blocked": self.blocked,
            "timings": self._timings,
        }

    def save_json(self, path: str) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.get_summary(), f, indent=2)
        except Exception:
            pass
