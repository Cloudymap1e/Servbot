# Proxy Interface

This adds a provider-agnostic proxy interface with support for:
- Static IP lists (round-robin)
- Dynamic metered providers (e.g., Bright Data, MooProxy sessions)

## Supported Providers

### 1. StaticListProvider
Cycles through a fixed list of proxies in round-robin fashion.

### 2. BrightDataProvider
Generates session-based endpoints for Bright Data residential proxies.

### 3. MooProxyProvider
Supports MooProxy in two modes:
- **Static mode**: Use pre-generated session list (cycles through provided entries)
- **Dynamic mode**: Generate new sessions on-demand

## Setup

1. Copy config/proxies.example.json to config/proxies.json
2. Fill in your credentials
3. For secrets, use environment variables (e.g., `"env:BRIGHTDATA_PASSWORD"`)

## Usage

```python
from servbot.proxy import load_provider_configs, ProxyManager

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

# Acquire cheapest provider by default
endpoint = pm.acquire()
print(endpoint.as_requests_proxies())       # for requests
print(endpoint.as_playwright_proxy())       # for Playwright

# Acquire by provider name and region
bd = pm.acquire(name='brightdata-resi', region='US')
moo = pm.acquire(name='mooproxy-dynamic', region='GB')
```

## MooProxy Format

MooProxy uses the format: `host:port:username:password_country-XX_session-ID`

Example:
```
us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-feDzDLCT
```

**Static mode** (use provided list):
```json
{
  "name": "mooproxy-static",
  "type": "mooproxy",
  "options": {
    "entries": "us.mooproxy.net:55688:user:pass_country-US_session-ABC\nus.mooproxy.net:55688:user:pass_country-US_session-XYZ"
  }
}
```

**Dynamic mode** (generate sessions):
```json
{
  "name": "mooproxy-dynamic",
  "type": "mooproxy",
  "options": {
    "host": "us.mooproxy.net",
    "port": "55688",
    "username": "specu1",
    "password": "XJrImxWe7O",
    "country": "US"
  }
}
```

## Design

- Providers implement `ProxyProvider.acquire()` returning a `ProxyEndpoint`
- `ProxyEndpoint` provides adapters for requests and Playwright
- Environment variable indirection for secrets (`env:VAR_NAME`)
- Price-based automatic provider selection
- Thread-safe round-robin for static providers
- Session ID extraction and metadata tracking
