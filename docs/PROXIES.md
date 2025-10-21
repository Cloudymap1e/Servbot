# Proxy Interface

This adds a provider-agnostic proxy interface with support for:
- Static IP lists (round-robin)
- Dynamic metered providers (e.g., Bright Data sessions)

How to use:
- Copy config/proxies.example.json to config/proxies.json and fill credentials.
- Optionally export secrets as environment variables (see env: references in the file).

Code example:
```python
from servbot.proxy import load_provider_configs, ProxyManager

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

# Acquire cheapest provider by default
endpoint = pm.acquire()
print(endpoint.as_requests_proxies())       # for requests
print(endpoint.as_playwright_proxy())       # for Playwright

# Acquire by provider name
bd = pm.acquire(name='brightdata-resi', region='US')
```

Design notes:
- Providers implement ProxyProvider.acquire() returning a ProxyEndpoint.
- ProxyEndpoint provides adapters for requests and Playwright.
- BrightDataProvider supports env:VAR indirection for secrets.
- Simple price-based selection; extend as needed.
