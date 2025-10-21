from __future__ import annotations

from typing import Dict, Type, Optional, List

from .base import ProxyProvider
from .models import ProviderConfig, ProxyEndpoint
from .providers.static_list import StaticListProvider
from .providers.brightdata import BrightDataProvider


_PROVIDER_REGISTRY: Dict[str, Type[ProxyProvider]] = {
    "static_list": StaticListProvider,
    "brightdata": BrightDataProvider,
}


class ProxyManager:
    """Factory and selector for proxy providers.

    - Register provider types
    - Instantiate providers from configs
    - Choose providers based on simple criteria (e.g., price)
    """

    def __init__(self, configs: List[ProviderConfig]):
        self._providers: Dict[str, ProxyProvider] = {}
        for cfg in configs:
            self._providers[cfg.name] = self._build_provider(cfg)

    def _build_provider(self, cfg: ProviderConfig) -> ProxyProvider:
        cls = _PROVIDER_REGISTRY.get(cfg.type)
        if not cls:
            raise ValueError(f"Unknown proxy provider type: {cfg.type}")
        return cls(cfg)

    def get(self, name: str) -> ProxyProvider:
        if name not in self._providers:
            raise KeyError(f"Proxy provider not found: {name}")
        return self._providers[name]

    def acquire(self, *, name: Optional[str] = None, region: Optional[str] = None, purpose: Optional[str] = None) -> ProxyEndpoint:
        if name:
            return self.get(name).acquire(purpose=purpose, region=region)
        # naive selection: pick lowest price_per_gb if available
        candidates = sorted(
            self._providers.values(),
            key=lambda p: (p.config.price_per_gb if p.config.price_per_gb is not None else 1e9),
        )
        if not candidates:
            raise RuntimeError("No proxy providers configured")
        return candidates[0].acquire(purpose=purpose, region=region)
