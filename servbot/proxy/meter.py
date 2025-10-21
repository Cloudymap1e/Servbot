"""Proxy usage metering and tracking."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List

from .models import ProxyEndpoint


logger = logging.getLogger(__name__)


@dataclass
class ProxyUsageMetrics:
    """Detailed proxy usage metrics for a specific endpoint."""

    endpoint_id: str
    provider: str
    host: str
    port: int
    proxy_type: Optional[str] = None
    region: Optional[str] = None
    requests_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors_count: int = 0
    first_used: Optional[datetime] = None
    last_used: Optional[datetime] = None
    cost_estimate: float = 0.0
    sessions: List[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        """Total bytes transferred (sent + received)."""
        return self.bytes_sent + self.bytes_received

    @property
    def total_gb(self) -> float:
        """Total gigabytes transferred."""
        return self.total_bytes / (1024**3)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage (0-100)."""
        if self.requests_count == 0:
            return 0.0
        successful = self.requests_count - self.errors_count
        return (successful / self.requests_count) * 100

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for serialization."""
        return {
            "endpoint_id": self.endpoint_id,
            "provider": self.provider,
            "host": self.host,
            "port": self.port,
            "proxy_type": self.proxy_type,
            "region": self.region,
            "requests_count": self.requests_count,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "total_gb": round(self.total_gb, 4),
            "errors_count": self.errors_count,
            "success_rate": round(self.success_rate, 2),
            "first_used": self.first_used.isoformat() if self.first_used else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "cost_estimate": round(self.cost_estimate, 4),
            "unique_sessions": len(set(self.sessions)),
        }


class ProxyMeter:
    """Tracks proxy usage at the most detailed level.

    Records all proxy operations including:
    - Request counts
    - Bandwidth usage (bytes sent/received)
    - Error rates
    - Cost estimates
    - Session tracking
    """

    def __init__(self):
        self._metrics: Dict[str, ProxyUsageMetrics] = {}
        self._provider_prices: Dict[str, float] = {}
        self._logger = logging.getLogger(__name__)
        self._logger.info("ProxyMeter initialized")

    def register_provider_price(self, provider: str, price_per_gb: float) -> None:
        """Register a provider's price per GB for cost calculations."""
        self._provider_prices[provider] = price_per_gb
        self._logger.debug("Registered provider price: %s = $%.2f/GB", provider, price_per_gb)

    def record_acquire(self, endpoint: ProxyEndpoint) -> None:
        """Record when a proxy endpoint is acquired."""
        key = self._get_endpoint_key(endpoint)
        now = datetime.now()

        if key not in self._metrics:
            self._metrics[key] = ProxyUsageMetrics(
                endpoint_id=key,
                provider=endpoint.provider or "unknown",
                host=endpoint.host,
                port=endpoint.port,
                proxy_type=endpoint.proxy_type.value if endpoint.proxy_type else None,
                region=endpoint.region,
                first_used=now,
            )
            self._logger.info(
                "New proxy endpoint acquired: provider=%s host=%s:%d type=%s region=%s",
                endpoint.provider,
                endpoint.host,
                endpoint.port,
                endpoint.proxy_type,
                endpoint.region,
            )

        # Track session
        if endpoint.session and endpoint.session not in self._metrics[key].sessions:
            self._metrics[key].sessions.append(endpoint.session)
            self._logger.debug(
                "New session tracked: provider=%s session=%s (total: %d)",
                endpoint.provider,
                endpoint.session,
                len(self._metrics[key].sessions),
            )

    def record_request(
        self,
        endpoint: ProxyEndpoint,
        bytes_sent: int = 0,
        bytes_received: int = 0,
        success: bool = True,
    ) -> None:
        """Record detailed proxy usage for a single request.

        Args:
            endpoint: The proxy endpoint used
            bytes_sent: Number of bytes sent through proxy
            bytes_received: Number of bytes received through proxy
            success: Whether the request succeeded
        """
        key = self._get_endpoint_key(endpoint)

        if key not in self._metrics:
            # Auto-create if not exists (in case acquire wasn't called)
            self.record_acquire(endpoint)

        m = self._metrics[key]
        m.requests_count += 1
        m.bytes_sent += bytes_sent
        m.bytes_received += bytes_received
        m.last_used = datetime.now()

        if not success:
            m.errors_count += 1
            self._logger.warning(
                "Proxy request failed: provider=%s host=%s:%d errors=%d/%d (%.1f%%)",
                m.provider,
                m.host,
                m.port,
                m.errors_count,
                m.requests_count,
                (m.errors_count / m.requests_count) * 100,
            )

        # Update cost estimate
        total_gb = (bytes_sent + bytes_received) / (1024**3)
        price_per_gb = self._provider_prices.get(m.provider, 0.0)
        m.cost_estimate += total_gb * price_per_gb

        self._logger.debug(
            "Proxy request recorded: provider=%s requests=%d sent=%dB recv=%dB total=%.4fGB cost=$%.4f success=%s",
            m.provider,
            m.requests_count,
            bytes_sent,
            bytes_received,
            m.total_gb,
            m.cost_estimate,
            success,
        )

    def record_release(self, endpoint: ProxyEndpoint, reason: Optional[str] = None) -> None:
        """Record when a proxy endpoint is released.

        Args:
            endpoint: The proxy endpoint being released
            reason: Optional reason for release (e.g., "error", "timeout", "done")
        """
        key = self._get_endpoint_key(endpoint)

        if key in self._metrics:
            m = self._metrics[key]
            self._logger.info(
                "Proxy released: provider=%s host=%s:%d session=%s reason=%s requests=%d errors=%d",
                m.provider,
                m.host,
                m.port,
                endpoint.session,
                reason or "normal",
                m.requests_count,
                m.errors_count,
            )
        else:
            self._logger.warning(
                "Release called for unknown endpoint: %s (reason=%s)", key, reason
            )

    def get_metrics(self, provider: Optional[str] = None) -> Dict[str, ProxyUsageMetrics]:
        """Get usage metrics, optionally filtered by provider.

        Args:
            provider: Optional provider name to filter by

        Returns:
            Dictionary of endpoint_id -> ProxyUsageMetrics
        """
        if provider:
            return {k: v for k, v in self._metrics.items() if v.provider == provider}
        return self._metrics.copy()

    def get_summary(self) -> Dict:
        """Get aggregated summary of all proxy usage.

        Returns:
            Dictionary with aggregated statistics
        """
        total_requests = sum(m.requests_count for m in self._metrics.values())
        total_bytes = sum(m.total_bytes for m in self._metrics.values())
        total_errors = sum(m.errors_count for m in self._metrics.values())
        total_cost = sum(m.cost_estimate for m in self._metrics.values())

        summary = {
            "total_endpoints": len(self._metrics),
            "total_requests": total_requests,
            "total_bytes": total_bytes,
            "total_gb": round(total_bytes / (1024**3), 4),
            "total_errors": total_errors,
            "overall_success_rate": round(
                ((total_requests - total_errors) / total_requests * 100)
                if total_requests > 0
                else 0.0,
                2,
            ),
            "total_cost_estimate": round(total_cost, 4),
            "by_provider": {},
        }

        # Aggregate by provider
        for m in self._metrics.values():
            if m.provider not in summary["by_provider"]:
                summary["by_provider"][m.provider] = {
                    "endpoints": 0,
                    "requests": 0,
                    "bytes": 0,
                    "errors": 0,
                    "cost": 0.0,
                }
            prov = summary["by_provider"][m.provider]
            prov["endpoints"] += 1
            prov["requests"] += m.requests_count
            prov["bytes"] += m.total_bytes
            prov["errors"] += m.errors_count
            prov["cost"] += m.cost_estimate

        # Convert bytes to GB for each provider
        for prov_data in summary["by_provider"].values():
            prov_data["gb"] = round(prov_data["bytes"] / (1024**3), 4)
            prov_data["cost"] = round(prov_data["cost"], 4)

        return summary

    def reset(self) -> None:
        """Reset all metrics. Use with caution."""
        count = len(self._metrics)
        self._metrics.clear()
        self._logger.warning("ProxyMeter reset: cleared %d endpoint metrics", count)

    def _get_endpoint_key(self, endpoint: ProxyEndpoint) -> str:
        """Generate unique key for endpoint tracking."""
        return f"{endpoint.provider}:{endpoint.host}:{endpoint.port}"
