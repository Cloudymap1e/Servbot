from __future__ import annotations

import logging
import threading
from typing import Dict, Type, Optional, List

from .base import ProxyProvider
from .models import ProviderConfig, ProxyEndpoint
from .meter import ProxyMeter
from .providers.static_list import StaticListProvider
from .providers.brightdata import BrightDataProvider
from .providers.mooproxy import MooProxyProvider


logger = logging.getLogger(__name__)


_PROVIDER_REGISTRY: Dict[str, Type[ProxyProvider]] = {
    "static_list": StaticListProvider,
    "brightdata": BrightDataProvider,
    "mooproxy": MooProxyProvider,
}


class ProxyManager:
    """Factory and selector for proxy providers.

    Features:
    - Register provider types
    - Instantiate providers from configs
    - Choose providers based on criteria (e.g., price)
    - Track usage with detailed metering
    - Enforce concurrency limits per provider
    - Comprehensive logging
    """

    def __init__(self, configs: List[ProviderConfig], enable_metering: bool = True):
        """Initialize ProxyManager.

        Args:
            configs: List of provider configurations
            enable_metering: Enable usage metering (default: True)
        """
        self._providers: Dict[str, ProxyProvider] = {}
        self._meter = ProxyMeter() if enable_metering else None
        self._concurrency_locks: Dict[str, threading.Semaphore] = {}
        self._active_counts: Dict[str, int] = {}
        self._count_locks: Dict[str, threading.Lock] = {}

        logger.info("Initializing ProxyManager with %d provider configs", len(configs))

        for cfg in configs:
            try:
                provider = self._build_provider(cfg)
                self._providers[cfg.name] = provider

                # Setup concurrency tracking
                if cfg.concurrency_limit:
                    self._concurrency_locks[cfg.name] = threading.Semaphore(cfg.concurrency_limit)
                    self._active_counts[cfg.name] = 0
                    self._count_locks[cfg.name] = threading.Lock()
                    logger.info(
                        "Provider loaded with concurrency limit: name=%s type=%s limit=%d",
                        cfg.name,
                        cfg.type,
                        cfg.concurrency_limit,
                    )
                else:
                    logger.info(
                        "Provider loaded: name=%s type=%s price_per_gb=%s",
                        cfg.name,
                        cfg.type,
                        f"${cfg.price_per_gb}" if cfg.price_per_gb else "N/A",
                    )

                # Register pricing for metering
                if self._meter and cfg.price_per_gb is not None:
                    self._meter.register_provider_price(cfg.name, cfg.price_per_gb)

            except Exception as e:
                logger.error("Failed to load provider %s: %s", cfg.name, e, exc_info=True)
                raise

        logger.info("ProxyManager initialized successfully with %d providers", len(self._providers))

    def _build_provider(self, cfg: ProviderConfig) -> ProxyProvider:
        """Build provider instance from config."""
        cls = _PROVIDER_REGISTRY.get(cfg.type)
        if not cls:
            logger.error("Unknown proxy provider type: %s", cfg.type)
            raise ValueError(f"Unknown proxy provider type: {cfg.type}")
        return cls(cfg)

    def get(self, name: str) -> ProxyProvider:
        """Get provider by name."""
        if name not in self._providers:
            logger.error("Proxy provider not found: %s (available: %s)", name, list(self._providers.keys()))
            raise KeyError(f"Proxy provider not found: {name}")
        return self._providers[name]

    def acquire(
        self,
        *,
        name: Optional[str] = None,
        region: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> ProxyEndpoint:
        """Acquire a proxy endpoint.

        Args:
            name: Specific provider name, or None for auto-selection
            region: Desired region/country code
            purpose: Purpose/context for this proxy usage

        Returns:
            ProxyEndpoint ready for use

        Raises:
            RuntimeError: If no providers configured or concurrency limit reached
            KeyError: If named provider not found
        """
        provider_name = name

        if name:
            logger.debug(
                "Acquiring proxy from specific provider: name=%s region=%s purpose=%s",
                name,
                region,
                purpose,
            )
        else:
            # Auto-select cheapest provider
            candidates = sorted(
                self._providers.values(),
                key=lambda p: (p.config.price_per_gb if p.config.price_per_gb is not None else 1e9),
            )
            if not candidates:
                logger.error("No proxy providers configured")
                raise RuntimeError("No proxy providers configured")

            provider_name = candidates[0].config.name
            logger.debug(
                "Auto-selected cheapest provider: name=%s price_per_gb=%s",
                provider_name,
                f"${candidates[0].config.price_per_gb}" if candidates[0].config.price_per_gb else "N/A",
            )

        # Check and acquire concurrency slot
        if provider_name in self._concurrency_locks:
            lock = self._concurrency_locks[provider_name]
            if not lock.acquire(blocking=False):
                with self._count_locks[provider_name]:
                    active = self._active_counts[provider_name]
                logger.warning(
                    "Concurrency limit reached for provider: name=%s active=%d",
                    provider_name,
                    active,
                )
                raise RuntimeError(
                    f"Concurrency limit reached for provider {provider_name} (active: {active})"
                )

            with self._count_locks[provider_name]:
                self._active_counts[provider_name] += 1
                logger.debug(
                    "Acquired concurrency slot: provider=%s active=%d",
                    provider_name,
                    self._active_counts[provider_name],
                )

        try:
            # Acquire from provider
            endpoint = self.get(provider_name).acquire(purpose=purpose, region=region)

            # Record in meter
            if self._meter:
                self._meter.record_acquire(endpoint)

            logger.info(
                "Proxy acquired: provider=%s host=%s:%d type=%s region=%s session=%s purpose=%s",
                endpoint.provider,
                endpoint.host,
                endpoint.port,
                endpoint.proxy_type,
                endpoint.region,
                endpoint.session,
                purpose,
            )

            return endpoint

        except Exception as e:
            # Release concurrency slot on error
            if provider_name in self._concurrency_locks:
                self._concurrency_locks[provider_name].release()
                with self._count_locks[provider_name]:
                    self._active_counts[provider_name] -= 1

            logger.error(
                "Failed to acquire proxy from provider %s: %s",
                provider_name,
                e,
                exc_info=True,
            )
            raise

    def release(self, endpoint: ProxyEndpoint, *, reason: Optional[str] = None) -> None:
        """Release a proxy endpoint.

        Args:
            endpoint: The endpoint to release
            reason: Optional reason for release (e.g., "error", "timeout", "done")
        """
        provider_name = endpoint.provider

        logger.debug(
            "Releasing proxy: provider=%s host=%s:%d session=%s reason=%s",
            provider_name,
            endpoint.host,
            endpoint.port,
            endpoint.session,
            reason or "normal",
        )

        # Call provider's release hook
        if provider_name in self._providers:
            try:
                self._providers[provider_name].release(endpoint, reason=reason)
            except Exception as e:
                logger.warning("Provider release hook failed: %s", e, exc_info=True)

        # Record in meter
        if self._meter:
            self._meter.record_release(endpoint, reason=reason)

        # Release concurrency slot
        if provider_name in self._concurrency_locks:
            self._concurrency_locks[provider_name].release()
            with self._count_locks[provider_name]:
                self._active_counts[provider_name] -= 1
                logger.debug(
                    "Released concurrency slot: provider=%s active=%d",
                    provider_name,
                    self._active_counts[provider_name],
                )

        logger.info(
            "Proxy released: provider=%s host=%s:%d session=%s reason=%s",
            provider_name,
            endpoint.host,
            endpoint.port,
            endpoint.session,
            reason or "normal",
        )

    def get_meter(self) -> Optional[ProxyMeter]:
        """Get the meter instance for usage tracking.

        Returns:
            ProxyMeter instance or None if metering disabled
        """
        return self._meter

    def get_stats(self) -> Dict:
        """Get current statistics for all providers.

        Returns:
            Dictionary with provider stats including active connections
        """
        stats = {
            "providers": {},
            "total_active": 0,
        }

        for name, provider in self._providers.items():
            provider_stats = {
                "type": provider.config.type,
                "price_per_gb": provider.config.price_per_gb,
                "concurrency_limit": provider.config.concurrency_limit,
                "active_connections": 0,
            }

            if name in self._active_counts:
                with self._count_locks[name]:
                    provider_stats["active_connections"] = self._active_counts[name]
                    stats["total_active"] += self._active_counts[name]

            stats["providers"][name] = provider_stats

        # Add metering summary if available
        if self._meter:
            stats["usage_summary"] = self._meter.get_summary()

        return stats
