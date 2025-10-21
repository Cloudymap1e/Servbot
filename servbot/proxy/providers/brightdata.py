from __future__ import annotations

import os
import secrets
from typing import Optional

from ..models import ProxyEndpoint, ProviderConfig
from ..base import ProxyProvider


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

        if not self._username or not self._password:
            raise ValueError("BrightDataProvider requires username and password")

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
        return ProxyEndpoint(
            scheme="http",
            host=self._host,
            port=self._port,
            username=user,
            password=self._password,
            provider=self.config.name,
            session=session_id,
            metadata={"kind": "metered", "provider": "brightdata"},
        )


def _resolve_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    # Allow format: env:VAR_NAME to read from environment
    if value.startswith("env:"):
        return os.getenv(value.split(":", 1)[1])
    return value
