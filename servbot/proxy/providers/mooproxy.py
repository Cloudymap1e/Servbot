from __future__ import annotations

import secrets
import threading
import itertools
from typing import List, Optional

from ..models import ProxyEndpoint, ProviderConfig
from ..base import ProxyProvider


class MooProxyProvider(ProxyProvider):
    """Provider for MooProxy session-based proxies.

    Supports two modes:
    1. Pre-generated sessions: provide a list via "entries" option
    2. Dynamic sessions: provide base credentials and generate sessions on-demand

    Expected ProviderConfig.options:
      Mode 1 - Pre-generated (use static list):
        - entries: newline/comma-separated list like:
            us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-ABC

      Mode 2 - Dynamic generation:
        - host: proxy hostname (e.g., us.mooproxy.net)
        - port: proxy port (e.g., 55688)
        - username: base username (e.g., specu1)
        - password: base password WITHOUT session suffix (e.g., XJrImxWe7O)
        - country: country code (e.g., US, GB)
        - scheme: http or https (default: http)
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        opts = config.options or {}

        # Check if using pre-generated entries
        entries_raw = opts.get("entries", "").strip()
        if entries_raw:
            self._mode = "static"
            self._endpoints = self._parse_entries(entries_raw)
            if not self._endpoints:
                raise ValueError("MooProxyProvider entries list is empty")
            self._lock = threading.Lock()
            self._cycle = itertools.cycle(self._endpoints)
        else:
            # Dynamic mode
            self._mode = "dynamic"
            self._host = opts.get("host")
            self._port = opts.get("port")
            self._username = opts.get("username")
            self._password = opts.get("password")
            self._country = opts.get("country", "US")
            self._scheme = opts.get("scheme", "http")

            if not all([self._host, self._port, self._username, self._password]):
                raise ValueError(
                    "MooProxyProvider requires either 'entries' or (host, port, username, password)"
                )

    def _parse_entries(self, raw: str) -> List[ProxyEndpoint]:
        """Parse pre-generated MooProxy entries in format: host:port:username:password"""
        entries: List[ProxyEndpoint] = []
        for line in [s.strip() for s in raw.replace(",", "\n").splitlines() if s.strip()]:
            parts = line.split(":")
            if len(parts) < 4:
                continue
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                continue
            username = parts[2]
            password = ":".join(parts[3:])  # password might contain colons

            entries.append(
                ProxyEndpoint(
                    scheme="http",
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    provider=self.config.name,
                    session=self._extract_session_id(password),
                    metadata={"kind": "mooproxy", "mode": "static"},
                )
            )
        return entries

    def _extract_session_id(self, password: str) -> Optional[str]:
        """Extract session ID from password like: XJrImxWe7O_country-US_session-ABC -> ABC"""
        if "_session-" in password:
            return password.split("_session-")[-1]
        return None

    def acquire(self, *, purpose: str | None = None, region: str | None = None) -> ProxyEndpoint:
        if self._mode == "static":
            with self._lock:
                return next(self._cycle)

        # Dynamic mode: generate new session
        session_id = secrets.token_urlsafe(8)
        country = region or self._country
        password = f"{self._password}_country-{country}_session-{session_id}"

        return ProxyEndpoint(
            scheme=self._scheme,
            host=self._host,
            port=int(self._port),
            username=self._username,
            password=password,
            provider=self.config.name,
            session=session_id,
            metadata={"kind": "mooproxy", "mode": "dynamic", "country": country},
        )
