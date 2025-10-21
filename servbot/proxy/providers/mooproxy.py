from __future__ import annotations

import logging
import secrets
import threading
import itertools
from typing import List, Optional

from ..models import ProxyEndpoint, ProviderConfig, ProxyType, IPVersion, RotationType
from ..base import ProxyProvider


logger = logging.getLogger(__name__)


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
        - proxy_type: type of proxy (default: residential) - residential, datacenter, isp, mobile
        - ip_version: ipv4 or ipv6 (default: ipv4)
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        opts = config.options or {}

        # Proxy type configuration
        proxy_type_str = opts.get("proxy_type", "residential").lower()
        self._proxy_type = ProxyType(proxy_type_str)

        ip_version_str = opts.get("ip_version", "ipv4").lower()
        self._ip_version = IPVersion(ip_version_str)

        # Check if using pre-generated entries
        entries_raw = opts.get("entries", "").strip()
        if entries_raw:
            self._mode = "static"
            self._endpoints = self._parse_entries(entries_raw)
            if not self._endpoints:
                logger.error("MooProxyProvider entries list is empty")
                raise ValueError("MooProxyProvider entries list is empty")
            self._lock = threading.Lock()
            self._cycle = itertools.cycle(self._endpoints)
            logger.info(
                "Initialized MooProxy provider (static mode): name=%s entries=%d type=%s",
                config.name,
                len(self._endpoints),
                self._proxy_type.value,
            )
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
                logger.error("MooProxyProvider dynamic mode requires host, port, username, password")
                raise ValueError(
                    "MooProxyProvider requires either 'entries' or (host, port, username, password)"
                )

            logger.info(
                "Initialized MooProxy provider (dynamic mode): name=%s host=%s:%s type=%s ip_version=%s country=%s",
                config.name,
                self._host,
                self._port,
                self._proxy_type.value,
                self._ip_version.value,
                self._country,
            )

    def _parse_entries(self, raw: str) -> List[ProxyEndpoint]:
        """Parse pre-generated MooProxy entries in format: host:port:username:password"""
        entries: List[ProxyEndpoint] = []
        for line in [s.strip() for s in raw.replace(",", "\n").splitlines() if s.strip()]:
            parts = line.split(":")
            if len(parts) < 4:
                logger.warning("Skipping invalid MooProxy entry: %s", line)
                continue
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                logger.warning("Invalid port in MooProxy entry: %s", line)
                continue
            username = parts[2]
            password = ":".join(parts[3:])  # password might contain colons

            session_id = self._extract_session_id(password)
            region = self._extract_region(password)

            entries.append(
                ProxyEndpoint(
                    scheme="http",
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    provider=self.config.name,
                    session=session_id,
                    proxy_type=self._proxy_type,
                    ip_version=self._ip_version,
                    rotation_type=RotationType.STICKY,  # Pre-generated sessions are sticky
                    region=region,
                    metadata={"kind": "mooproxy", "mode": "static"},
                )
            )
            logger.debug(
                "Parsed MooProxy entry: host=%s:%d session=%s region=%s",
                host,
                port,
                session_id or "unknown",
                region or "unknown",
            )
        return entries

    def _extract_session_id(self, password: str) -> Optional[str]:
        """Extract session ID from password like: XJrImxWe7O_country-US_session-ABC -> ABC"""
        if "_session-" in password:
            return password.split("_session-")[-1]
        return None

    def _extract_region(self, password: str) -> Optional[str]:
        """Extract country code from password like: XJrImxWe7O_country-US_session-ABC -> US"""
        if "_country-" in password:
            parts = password.split("_country-")
            if len(parts) > 1:
                # Get the part after _country- and before the next _
                country_part = parts[1].split("_")[0]
                return country_part
        return None

    def acquire(self, *, purpose: str | None = None, region: str | None = None) -> ProxyEndpoint:
        if self._mode == "static":
            with self._lock:
                endpoint = next(self._cycle)
            logger.debug(
                "MooProxy static endpoint acquired: session=%s region=%s",
                endpoint.session,
                endpoint.region,
            )
            return endpoint

        # Dynamic mode: generate new session
        session_id = secrets.token_urlsafe(8)
        country = region or self._country
        password = f"{self._password}_country-{country}_session-{session_id}"

        logger.debug(
            "Creating MooProxy dynamic session: id=%s region=%s purpose=%s",
            session_id,
            country,
            purpose or "general",
        )

        endpoint = ProxyEndpoint(
            scheme=self._scheme,
            host=self._host,
            port=int(self._port),
            username=self._username,
            password=password,
            provider=self.config.name,
            session=session_id,
            proxy_type=self._proxy_type,
            ip_version=self._ip_version,
            rotation_type=RotationType.STICKY,  # MooProxy sessions are sticky
            region=country,
            metadata={
                "kind": "mooproxy",
                "mode": "dynamic",
                "country": country,
                "purpose": purpose or "general",
            },
        )

        logger.info(
            "MooProxy dynamic endpoint acquired: session=%s type=%s region=%s",
            session_id,
            self._proxy_type.value,
            country,
        )

        return endpoint
