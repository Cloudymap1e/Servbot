from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict


class ProxyType(str, Enum):
    """Proxy type classification."""
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"
    ISP = "isp"  # Static residential
    MOBILE = "mobile"


class IPVersion(str, Enum):
    """IP protocol version."""
    IPV4 = "ipv4"
    IPV6 = "ipv6"


class RotationType(str, Enum):
    """Session rotation type."""
    ROTATING = "rotating"  # Changes IP on each request or periodically
    STICKY = "sticky"      # Maintains same IP for session duration


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
        proxy_type: type of proxy (residential, datacenter, ISP, mobile)
        ip_version: IPv4 or IPv6
        rotation_type: rotating or sticky session
        region: country/region code (e.g., "US", "GB")
        metadata: arbitrary provider-specific metadata
    """

    scheme: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    provider: Optional[str] = None
    session: Optional[str] = None
    proxy_type: Optional[ProxyType] = None
    ip_version: Optional[IPVersion] = None
    rotation_type: Optional[RotationType] = None
    region: Optional[str] = None
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
