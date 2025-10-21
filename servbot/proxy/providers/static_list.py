from __future__ import annotations

import itertools
import logging
import threading
from typing import List

from ..models import ProxyEndpoint, ProviderConfig, ProxyType, IPVersion, RotationType
from ..base import ProxyProvider


logger = logging.getLogger(__name__)


class StaticListProvider(ProxyProvider):
    """Cycles through a provided static list of proxies (round-robin).

    Expected ProviderConfig.options keys:
      - entries: comma-or-newline-separated list of endpoints in one of forms:
          username:password@host:port
          host:port
          scheme://username:password@host:port
          scheme://host:port
      - scheme: default scheme (http) if not set per-entry
      - proxy_type: type of proxy (default: datacenter) - residential, datacenter, isp, mobile
      - ip_version: ipv4 or ipv6 (default: ipv4)
      - rotation_type: rotating or sticky (default: sticky for static lists)
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        raw = (config.options or {}).get("entries", "")
        self._scheme_default = (config.options or {}).get("scheme", "http").lower()

        # Proxy type configuration
        opts = config.options or {}
        proxy_type_str = opts.get("proxy_type", "datacenter").lower()
        self._proxy_type = ProxyType(proxy_type_str)

        ip_version_str = opts.get("ip_version", "ipv4").lower()
        self._ip_version = IPVersion(ip_version_str)

        rotation_type_str = opts.get("rotation_type", "sticky").lower()
        self._rotation_type = RotationType(rotation_type_str)

        self._endpoints: List[ProxyEndpoint] = self._parse_entries(raw)
        if not self._endpoints:
            logger.error("StaticListProvider requires at least one proxy entry")
            raise ValueError("StaticListProvider requires at least one proxy entry")

        self._lock = threading.Lock()
        self._cycle = itertools.cycle(self._endpoints)

        logger.info(
            "Initialized StaticList provider: name=%s entries=%d type=%s ip_version=%s",
            config.name,
            len(self._endpoints),
            self._proxy_type.value,
            self._ip_version.value,
        )

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
                logger.warning("Skipping invalid static proxy entry (no port): %s", line)
                continue
            host, port_s = hostport.rsplit(":", 1)
            try:
                port = int(port_s)
            except ValueError:
                logger.warning("Skipping invalid static proxy entry (bad port): %s", line)
                continue

            entries.append(
                ProxyEndpoint(
                    scheme=scheme,
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    provider=self.config.name,
                    proxy_type=self._proxy_type,
                    ip_version=self._ip_version,
                    rotation_type=self._rotation_type,
                    metadata={"kind": "static"},
                )
            )
            logger.debug(
                "Parsed static proxy entry: %s://%s:%d auth=%s",
                scheme,
                host,
                port,
                "yes" if username else "no",
            )
        return entries

    def acquire(self, *, purpose: str | None = None, region: str | None = None) -> ProxyEndpoint:
        with self._lock:
            endpoint = next(self._cycle)

        logger.debug(
            "StaticList endpoint acquired: host=%s:%d purpose=%s",
            endpoint.host,
            endpoint.port,
            purpose or "general",
        )

        return endpoint
