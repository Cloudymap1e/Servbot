"""Comprehensive proxy management system for servbot.

This package provides a provider-agnostic proxy interface with advanced features:

Providers:
    StaticListProvider: Round-robin cycling through static IP lists
    BrightDataProvider: Session-based BrightData residential/ISP/mobile proxies
    MooProxyProvider: MooProxy with static or dynamic session generation

Key Classes:
    ProxyManager: Factory and selector with usage metering and concurrency control
    ProxyEndpoint: Concrete proxy endpoint with format adapters
    ProxyProvider: Abstract base for implementing custom providers
    ProxyMeter: Usage tracking and cost estimation
    ProxyTester: Batch testing and validation utilities
    ProviderConfig: Configuration dataclass for providers

Models:
    ProxyType: Enum (residential, datacenter, isp, mobile)
    IPVersion: Enum (ipv4, ipv6)
    RotationType: Enum (rotating, sticky)

Features:
    - Multi-provider support with automatic selection
    - Detailed usage metering and cost tracking
    - Concurrency limit enforcement per provider
    - Region/country targeting
    - Batch testing and validation
    - Environment variable secret management
    - Comprehensive logging at all levels
    - Integration with browser automation

Usage:
    from servbot.proxy import load_provider_configs, ProxyManager
    
    configs = load_provider_configs('config/proxies.json')
    pm = ProxyManager(configs, enable_metering=True)
    
    # Acquire cheapest provider
    endpoint = pm.acquire(region='US', purpose='registration')
    
    # Use with requests
    response = requests.get('http://httpbin.org/ip', 
                           proxies=endpoint.as_requests_proxies())
    
    # Use with Playwright
    result = register_service_account(
        service="Reddit",
        website_url="https://www.reddit.com/register",
        proxy=endpoint.as_playwright_proxy()
    )
    
    # Release when done
    pm.release(endpoint, reason='complete')
    
    # View usage stats
    stats = pm.get_stats()
    summary = stats['usage_summary']
    print(f"Total cost: ${summary['total_cost_estimate']}")

Configuration:
    Create config/proxies.json:
    
    [
      {
        "name": "brightdata-resi",
        "type": "brightdata",
        "price_per_gb": 12.0,
        "concurrency_limit": 100,
        "options": {
          "host": "zproxy.lum-superproxy.io",
          "port": "22225",
          "username": "env:BRIGHTDATA_USERNAME",
          "password": "env:BRIGHTDATA_PASSWORD",
          "country": "US",
          "proxy_type": "residential"
        }
      }
    ]

See Also:
    docs/PROXIES.md: Comprehensive proxy documentation
    docs/BROWSER_AUTOMATION.md: Integration with browser automation
"""

from .models import ProxyEndpoint, ProviderConfig, ProxyType, IPVersion, RotationType
from .base import ProxyProvider
from .manager import ProxyManager
from .config_loader import load_provider_configs
from .batch_import import ProxyBatchImporter, ProxyDetector
from .tester import ProxyTester, ProxyTestResult

__all__ = [
    "ProxyEndpoint",
    "ProviderConfig",
    "ProxyType",
    "IPVersion",
    "RotationType",
    "ProxyProvider",
    "ProxyManager",
    "load_provider_configs",
    "ProxyBatchImporter",
    "ProxyDetector",
    "ProxyTester",
    "ProxyTestResult",
]
