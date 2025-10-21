from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from ..models import ProxyEndpoint, ProviderConfig, ProxyType, IPVersion, RotationType
from ..base import ProxyProvider


logger = logging.getLogger(__name__)


class BrightDataProvider(ProxyProvider):
    """Builds session-based endpoints for Bright Data (Luminati) residential proxies.

    Expected ProviderConfig.options keys:
      - host: proxy host (e.g., zproxy.lum-superproxy.io)
      - port: proxy port (e.g., 22225)
      - username: your zone username (without session=)
      - password: your password (DO NOT hardcode secrets in code; load from env)
      - country: optional two-letter country code
      - city: optional city code
      - zone: optional zone (if implied in username, can omit)
      - proxy_type: type of proxy (default: residential) - residential, datacenter, isp, mobile
      - ip_version: ipv4 or ipv6 (default: ipv4)

    Usage yields endpoints like:
      http://username-session-<id>-country-XX:password@host:port
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        opts = config.options or {}
        self._host = opts.get("host", "zproxy.lum-superproxy.io")
        self._port = int(opts.get("port", "22225"))
        # Allow env var indirection for secrets
        self._username = _resolve_secret(opts.get("username"))
        self._password = _resolve_secret(opts.get("password"))
        self._country = opts.get("country")
        self._city = opts.get("city")

        # Proxy type configuration
        proxy_type_str = opts.get("proxy_type", "residential").lower()
        self._proxy_type = ProxyType(proxy_type_str)

        ip_version_str = opts.get("ip_version", "ipv4").lower()
        self._ip_version = IPVersion(ip_version_str)

        if not self._username or not self._password:
            logger.error("BrightDataProvider requires username and password")
            raise ValueError("BrightDataProvider requires username and password")

        logger.info(
            "Initialized BrightData provider: name=%s host=%s:%d type=%s ip_version=%s country=%s",
            config.name,
            self._host,
            self._port,
            self._proxy_type.value,
            self._ip_version.value,
            self._country or "any",
        )

    def acquire(self, *, purpose: str | None = None, region: str | None = None) -> ProxyEndpoint:
        session_id = secrets.token_hex(6)
        username = self._username
        parts = [username, f"session-{session_id}"]
        cc = region or self._country
        if cc:
            parts.append(f"country-{cc}")
        if self._city:
            parts.append(f"city-{self._city}")
        user = "-".join(parts)

        logger.debug(
            "Creating BrightData session: id=%s region=%s purpose=%s username=%s",
            session_id,
            cc or "any",
            purpose or "general",
            user,
        )

        endpoint = ProxyEndpoint(
            scheme="http",
            host=self._host,
            port=self._port,
            username=user,
            password=self._password,
            provider=self.config.name,
            session=session_id,
            proxy_type=self._proxy_type,
            ip_version=self._ip_version,
            rotation_type=RotationType.ROTATING,
            region=cc,
            metadata={
                "kind": "metered",
                "provider": "brightdata",
                "purpose": purpose or "general",
            },
        )

        logger.info(
            "BrightData endpoint acquired: session=%s type=%s ip_version=%s region=%s",
            session_id,
            self._proxy_type.value,
            self._ip_version.value,
            cc or "any",
        )

        return endpoint


def _resolve_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    # Allow format: env:VAR_NAME to read from environment
    if value.startswith("env:"):
        env_var = value.split(":", 1)[1]
        resolved = os.getenv(env_var)
        if resolved:
            logger.debug("Resolved secret from env var: %s", env_var)
        else:
            logger.warning("Env var not found: %s", env_var)
        return resolved
    return value
