from __future__ import annotations

import itertools
import threading
from typing import List

from ..models import ProxyEndpoint, ProviderConfig
from ..base import ProxyProvider


class StaticListProvider(ProxyProvider):
    """Cycles through a provided static list of proxies (round-robin).

    Expected ProviderConfig.options keys:
      - entries: comma-or-newline-separated list of endpoints in one of forms:
          username:password@host:port
          host:port
          scheme://username:password@host:port
          scheme://host:port
      - scheme: default scheme (http) if not set per-entry
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        raw = (config.options or {}).get("entries", "")
        self._scheme_default = (config.options or {}).get("scheme", "http").lower()
        self._endpoints: List[ProxyEndpoint] = self._parse_entries(raw)
        if not self._endpoints:
            raise ValueError("StaticListProvider requires at least one proxy entry")
        self._lock = threading.Lock()
        self._cycle = itertools.cycle(self._endpoints)

    def _parse_entries(self, raw: str) -> List[ProxyEndpoint]:
        entries: List[ProxyEndpoint] = []
        for line in [s.strip() for s in raw.replace(",", "\n").splitlines() if s.strip()]:
            scheme = self._scheme_default
            rest = line
            if "://" in line:
                scheme, rest = line.split("://", 1)
            username = password = None
            hostport = rest
            if "@" in rest:
                creds, hostport = rest.split("@", 1)
                if ":" in creds:
                    username, password = creds.split(":", 1)
                else:
                    username = creds
            if ":" not in hostport:
                continue
            host, port_s = hostport.rsplit(":", 1)
            try:
                port = int(port_s)
            except ValueError:
                continue
            entries.append(
                ProxyEndpoint(
                    scheme=scheme,
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    provider=self.config.name,
                    metadata={"kind": "static"},
                )
            )
        return entries

    def acquire(self, *, purpose: str | None = None, region: str | None = None) -> ProxyEndpoint:
        with self._lock:
            return next(self._cycle)
