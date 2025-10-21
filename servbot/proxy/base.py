from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import ProxyEndpoint, ProviderConfig


class ProxyProvider(ABC):
    """Abstract provider that can acquire and release proxy endpoints."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    def acquire(self, *, purpose: str | None = None, region: str | None = None) -> ProxyEndpoint:
        """Acquire a proxy endpoint ready for use."""
        raise NotImplementedError

    def release(self, endpoint: ProxyEndpoint, *, reason: Optional[str] = None) -> None:  # pragma: no cover
        """Optional release hook for providers that maintain leases."""
        return
