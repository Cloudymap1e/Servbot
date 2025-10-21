from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass(frozen=True)
class ProxyEndpoint:
    """Represents a concrete proxy endpoint.

    Attributes:
        scheme: http or https
        host: hostname or IP
        port: integer port
        username: optional username for auth
        password: optional password for auth
        provider: logical provider name (e.g., "brightdata", "static")
        session: optional session identifier if the provider supports rotation
        metadata: arbitrary provider-specific metadata (e.g., price, region)
    """

    scheme: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    provider: Optional[str] = None
    session: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

    def as_requests_proxies(self) -> Dict[str, str]:
        """Return a requests-compatible proxies mapping."""
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        netloc = f"{auth}{self.host}:{self.port}"
        url = f"{self.scheme}://{netloc}"
        return {"http": url, "https": url}

    def as_playwright_proxy(self) -> Dict[str, str]:
        """Return a Playwright-compatible proxy dict."""
        server = f"{self.scheme}://{self.host}:{self.port}"
        out: Dict[str, str] = {"server": server}
        if self.username:
            out["username"] = self.username
        if self.password:
            out["password"] = self.password
        return out


@dataclass
class ProviderConfig:
    """Configuration for a proxy provider."""

    name: str
    type: str  # e.g. "static_list", "brightdata", "oxylabs"
    price_per_gb: Optional[float] = None
    concurrency_limit: Optional[int] = None
    # Provider-specific fields (kept generic; providers may read from this dict)
    options: Optional[Dict[str, str]] = None
