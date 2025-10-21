# Proxy Interface

This module provides a provider-agnostic proxy interface with comprehensive features:
- Static IP lists (round-robin)
- Dynamic metered providers (e.g., Bright Data, MooProxy sessions)
- **Detailed usage metering and cost tracking**
- **Comprehensive logging at all levels**
- **Concurrency limit enforcement**
- **Multiple proxy types** (residential, datacenter, ISP, mobile)
- **IP version support** (IPv4, IPv6)
- **Session rotation tracking**

## Supported Providers

### 1. StaticListProvider
Cycles through a fixed list of proxies in round-robin fashion.

**Features:**
- Round-robin load balancing
- Support for authenticated proxies
- Configurable proxy types (datacenter, residential, ISP, mobile)
- IPv4/IPv6 support

### 2. BrightDataProvider
Generates session-based endpoints for Bright Data residential proxies.

**Features:**
- Automatic session rotation
- Country/city targeting
- Residential, datacenter, ISP, and mobile proxy types
- IPv4/IPv6 support
- Environment variable secret management

### 3. MooProxyProvider
Supports MooProxy in two modes:
- **Static mode**: Use pre-generated session list (cycles through provided entries)
- **Dynamic mode**: Generate new sessions on-demand

**Features:**
- Sticky sessions
- Country targeting
- Session ID tracking
- Automatic region extraction

## Proxy Types

The system supports four proxy types:

- **`residential`**: Residential IPs from ISPs (highest anonymity, moderate speed)
- **`datacenter`**: Datacenter IPs (fastest, lowest cost, lower anonymity)
- **`isp`**: Static residential IPs (ISP proxies, good balance)
- **`mobile`**: Mobile carrier IPs (highest anonymity, higher cost)

## IP Versions

- **`ipv4`**: IPv4 addresses (default, widest compatibility)
- **`ipv6`**: IPv6 addresses (less common, some providers charge less)

## Rotation Types

- **`rotating`**: IP changes on each request or periodically
- **`sticky`**: Same IP maintained for session duration

## Setup

1. Copy config/proxies.example.json to config/proxies.json
2. Fill in your credentials
3. For secrets, use environment variables (e.g., `"env:BRIGHTDATA_PASSWORD"`)

## Usage

### Basic Usage

```python
from servbot.proxy import load_provider_configs, ProxyManager

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

# Acquire cheapest provider by default
endpoint = pm.acquire()
print(endpoint.as_requests_proxies())       # for requests
print(endpoint.as_playwright_proxy())       # for Playwright

# Acquire by provider name and region
bd = pm.acquire(name='brightdata-resi', region='US', purpose='scraping')
moo = pm.acquire(name='mooproxy-dynamic', region='GB', purpose='verification')

# Release when done
pm.release(endpoint, reason='done')
```

### With Usage Tracking

```python
from servbot.proxy import ProxyManager, load_provider_configs

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs, enable_metering=True)

# Acquire and use proxy
endpoint = pm.acquire(name='brightdata-resi', purpose='data-collection')

# Record usage
meter = pm.get_meter()
meter.record_request(
    endpoint,
    bytes_sent=1024,
    bytes_received=4096,
    success=True
)

# Release
pm.release(endpoint, reason='complete')

# Get usage summary
summary = meter.get_summary()
print(f"Total requests: {summary['total_requests']}")
print(f"Total GB: {summary['total_gb']}")
print(f"Total cost: ${summary['total_cost_estimate']}")

# Get detailed metrics by provider
metrics = meter.get_metrics(provider='brightdata-resi')
for endpoint_id, m in metrics.items():
    print(f"{endpoint_id}: {m.requests_count} requests, ${m.cost_estimate:.2f}")
```

### With Concurrency Limits

```python
# In your config JSON:
{
  "name": "brightdata-resi",
  "type": "brightdata",
  "price_per_gb": 12.0,
  "concurrency_limit": 10,  # Max 10 concurrent connections
  "options": { ... }
}

# Usage will automatically enforce the limit
try:
    endpoint = pm.acquire(name='brightdata-resi')
    # Use the endpoint...
    pm.release(endpoint)
except RuntimeError as e:
    print(f"Concurrency limit reached: {e}")
```

### Statistics and Monitoring

```python
# Get current stats
stats = pm.get_stats()
print(f"Total active connections: {stats['total_active']}")

for provider_name, provider_stats in stats['providers'].items():
    print(f"{provider_name}:")
    print(f"  Type: {provider_stats['type']}")
    print(f"  Active: {provider_stats['active_connections']}")
    print(f"  Limit: {provider_stats['concurrency_limit']}")

# Usage summary (if metering enabled)
if 'usage_summary' in stats:
    summary = stats['usage_summary']
    print(f"\nUsage Summary:")
    print(f"  Total requests: {summary['total_requests']}")
    print(f"  Total GB: {summary['total_gb']}")
    print(f"  Success rate: {summary['overall_success_rate']}%")
    print(f"  Estimated cost: ${summary['total_cost_estimate']}")
```

## Configuration Examples

### Static List (Datacenter Proxies)

```json
{
  "name": "datacenter-us",
  "type": "static_list",
  "price_per_gb": 0.5,
  "concurrency_limit": 50,
  "options": {
    "scheme": "http",
    "entries": "user:pass@1.2.3.4:8000, user:pass@5.6.7.8:9000",
    "proxy_type": "datacenter",
    "ip_version": "ipv4",
    "rotation_type": "sticky"
  }
}
```

### BrightData (Residential Proxies)

```json
{
  "name": "brightdata-resi-us",
  "type": "brightdata",
  "price_per_gb": 12.0,
  "concurrency_limit": 100,
  "options": {
    "host": "zproxy.lum-superproxy.io",
    "port": "22225",
    "username": "env:BRIGHTDATA_USERNAME",
    "password": "env:BRIGHTDATA_PASSWORD",
    "country": "US",
    "proxy_type": "residential",
    "ip_version": "ipv4"
  }
}
```

### BrightData (ISP Proxies)

```json
{
  "name": "brightdata-isp",
  "type": "brightdata",
  "price_per_gb": 8.0,
  "options": {
    "host": "zproxy.lum-superproxy.io",
    "port": "22225",
    "username": "env:BRIGHTDATA_ISP_USERNAME",
    "password": "env:BRIGHTDATA_ISP_PASSWORD",
    "proxy_type": "isp",
    "ip_version": "ipv4"
  }
}
```

### MooProxy (Static Mode)

```json
{
  "name": "mooproxy-static",
  "type": "mooproxy",
  "price_per_gb": 5.0,
  "concurrency_limit": 20,
  "options": {
    "entries": "us.mooproxy.net:55688:user:pass_country-US_session-ABC\nus.mooproxy.net:55688:user:pass_country-US_session-XYZ",
    "proxy_type": "residential",
    "ip_version": "ipv4"
  }
}
```

### MooProxy (Dynamic Mode)

```json
{
  "name": "mooproxy-dynamic",
  "type": "mooproxy",
  "price_per_gb": 5.0,
  "options": {
    "host": "us.mooproxy.net",
    "port": "55688",
    "username": "specu1",
    "password": "XJrImxWe7O",
    "country": "US",
    "proxy_type": "residential",
    "ip_version": "ipv4"
  }
}
```

## MooProxy Format

MooProxy uses the format: `host:port:username:password_country-XX_session-ID`

Example:
```
us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-feDzDLCT
```

## Logging

The proxy module provides comprehensive logging at multiple levels:

### INFO Level
- Provider initialization
- Endpoint acquisition/release
- Concurrency limit changes
- Metering summaries

### DEBUG Level
- Session generation details
- Round-robin cycling
- Request/response byte counts
- Detailed metrics

### WARNING Level
- Invalid configuration entries
- Missing environment variables
- Concurrency limits reached
- High error rates

### ERROR Level
- Provider initialization failures
- Acquisition failures
- Configuration errors

### Example Log Output

```
2025-10-21 10:30:15 [INFO] servbot.proxy.manager: Initializing ProxyManager with 3 provider configs
2025-10-21 10:30:15 [INFO] servbot.proxy.providers.brightdata: Initialized BrightData provider: name=brightdata-resi host=zproxy.lum-superproxy.io:22225 type=residential ip_version=ipv4 country=US
2025-10-21 10:30:15 [INFO] servbot.proxy.manager: Provider loaded: name=brightdata-resi type=brightdata price_per_gb=$12.0
2025-10-21 10:30:15 [INFO] servbot.proxy.meter: ProxyMeter initialized
2025-10-21 10:30:20 [DEBUG] servbot.proxy.manager: Acquiring proxy from specific provider: name=brightdata-resi region=US purpose=scraping
2025-10-21 10:30:20 [DEBUG] servbot.proxy.providers.brightdata: Creating BrightData session: id=a3f7e2 region=US purpose=scraping
2025-10-21 10:30:20 [INFO] servbot.proxy.providers.brightdata: BrightData endpoint acquired: session=a3f7e2 type=residential ip_version=ipv4 region=US
2025-10-21 10:30:20 [INFO] servbot.proxy.manager: Proxy acquired: provider=brightdata-resi host=zproxy.lum-superproxy.io:22225 type=ProxyType.RESIDENTIAL region=US session=a3f7e2 purpose=scraping
2025-10-21 10:30:25 [DEBUG] servbot.proxy.meter: Proxy request recorded: provider=brightdata-resi requests=1 sent=1024B recv=4096B total=0.0000GB cost=$0.0001 success=True
2025-10-21 10:30:30 [INFO] servbot.proxy.manager: Proxy released: provider=brightdata-resi host=zproxy.lum-superproxy.io:22225 session=a3f7e2 reason=complete
```

## Design

- Providers implement `ProxyProvider.acquire()` returning a `ProxyEndpoint`
- `ProxyEndpoint` provides adapters for requests and Playwright
- Environment variable indirection for secrets (`env:VAR_NAME`)
- Price-based automatic provider selection
- Thread-safe round-robin for static providers
- Session ID extraction and metadata tracking
- **Detailed usage metering with `ProxyMeter`**
- **Comprehensive logging throughout the stack**
- **Concurrency limit enforcement per provider**
- **Multiple proxy types, IP versions, and rotation strategies**

## Proxy Testing

### Testing Individual Proxies

```python
from servbot.proxy import ProxyManager, load_provider_configs
from servbot.proxy.tester import ProxyTester

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

# Acquire proxy
endpoint = pm.acquire(name='mooproxy-us')

# Test it
result = ProxyTester.test_single_proxy(
    endpoint,
    test_url='http://httpbin.org/ip',
    timeout=10
)

print(f"Success: {result.success}")
print(f"Response time: {result.response_time_ms}ms")
print(f"IP: {result.response_ip}")

# Release
pm.release(endpoint)
```

### Batch Testing

```python
from servbot.proxy import ProxyManager, load_provider_configs
from servbot.proxy.tester import ProxyTester

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

# Acquire multiple proxies
endpoints = []
for i in range(10):
    endpoints.append(pm.acquire(name='brightdata-resi'))

# Test in parallel
results = ProxyTester.test_batch(
    endpoints,
    test_url='http://httpbin.org/ip',
    timeout=10,
    max_workers=10
)

# Print summary
ProxyTester.print_test_summary(results)

# Release all
for endpoint in endpoints:
    pm.release(endpoint)
```

### Testing Before Production

```python
import json
from servbot.proxy import load_provider_configs, ProxyManager
from servbot.proxy.tester import ProxyTester

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

# Test each provider
for config in configs:
    print(f"\nTesting provider: {config.name}")
    
    # Acquire 5 proxies
    endpoints = []
    try:
        for i in range(5):
            endpoints.append(pm.acquire(name=config.name))
    except Exception as e:
        print(f"  Failed to acquire: {e}")
        continue
    
    # Test
    results = ProxyTester.test_batch(endpoints, max_workers=5)
    
    # Analyze
    successful = sum(1 for r in results if r.success)
    if successful > 0:
        avg_time = sum(r.response_time_ms for r in results if r.success) / successful
        print(f"  Success rate: {successful}/{len(results)}")
        print(f"  Avg response time: {avg_time:.0f}ms")
    
    # Save results
    with open(f'proxy_test_{config.name}.json', 'w') as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    
    # Release
    for endpoint in endpoints:
        pm.release(endpoint)
```

### Continuous Monitoring

```python
import time
from servbot.proxy import ProxyManager, load_provider_configs
from servbot.proxy.tester import ProxyTester

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs, enable_metering=True)

def monitor_proxies(interval_seconds=300):
    """Monitor proxy health every interval_seconds."""
    while True:
        stats = pm.get_stats()
        
        for provider_name in stats['providers']:
            endpoint = pm.acquire(name=provider_name)
            result = ProxyTester.test_single_proxy(endpoint)
            
            if result.success:
                print(f"[{provider_name}] OK - {result.response_time_ms:.0f}ms")
            else:
                print(f"[{provider_name}] FAIL - {result.error}")
            
            pm.release(endpoint)
        
        time.sleep(interval_seconds)

# Run monitoring
monitor_proxies()
```

## Integration with Browser Automation

### Basic Integration

```python
from servbot.proxy import load_provider_configs, ProxyManager
from servbot import register_service_account

# Setup proxies
configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs, enable_metering=True)

# Acquire proxy
endpoint = pm.acquire(region='US', purpose='reddit-registration')

# Use in browser automation
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    proxy=endpoint.as_playwright_proxy(),
    traffic_profile="minimal"
)

# Release proxy
pm.release(endpoint, reason='complete')
```

### Advanced: Retry with Different Proxies

```python
from servbot.proxy import load_provider_configs, ProxyManager
from servbot import register_service_account

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

max_retries = 3
endpoint = None

for attempt in range(max_retries):
    try:
        # Acquire new proxy for each attempt
        if endpoint:
            pm.release(endpoint, reason='failed')
        endpoint = pm.acquire(region='US')
        
        # Attempt registration
        result = register_service_account(
            service="Reddit",
            website_url="https://www.reddit.com/register",
            provision_new=True,
            proxy=endpoint.as_playwright_proxy(),
            traffic_profile="minimal"
        )
        
        if result and result['status'] == 'success':
            pm.release(endpoint, reason='success')
            print(f"✓ Success on attempt {attempt + 1}")
            break
    except Exception as e:
        print(f"✗ Attempt {attempt + 1} failed: {e}")
```

### Proxy Rotation Strategy

```python
from servbot.proxy import load_provider_configs, ProxyManager
from servbot import register_service_account

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs, enable_metering=True)

# Register 100 accounts with automatic proxy rotation
for i in range(100):
    # Auto-select cheapest available proxy
    endpoint = pm.acquire(region='US', purpose=f'registration-{i}')
    
    try:
        result = register_service_account(
            service="Reddit",
            website_url="https://www.reddit.com/register",
            provision_new=True,
            proxy=endpoint.as_playwright_proxy(),
            traffic_profile="minimal",
            measure_network=True
        )
        
        if result and result['status'] == 'success':
            pm.release(endpoint, reason='success')
            print(f"[{i+1}/100] ✓ Success")
        else:
            pm.release(endpoint, reason='failed')
            print(f"[{i+1}/100] ✗ Failed")
    except Exception as e:
        pm.release(endpoint, reason='error')
        print(f"[{i+1}/100] ✗ Error: {e}")
    
    # View progress
    if (i + 1) % 10 == 0:
        stats = pm.get_stats()
        summary = stats['usage_summary']
        print(f"\n=== Progress Report ({i+1}/100) ===")
        print(f"Total data: {summary['total_gb']:.4f} GB")
        print(f"Estimated cost: ${summary['total_cost_estimate']:.2f}")
        print(f"Avg per registration: {summary['total_gb']/summary['total_requests']:.4f} GB\n")
```

## Best Practices

### 1. Cost Optimization

```python
# Use auto-selection to pick cheapest provider
endpoint = pm.acquire()  # Automatically selects cheapest

# OR manually choose datacenter for non-critical tasks
endpoint = pm.acquire(name='datacenter-cheap')

# Reserve expensive residential for critical tasks
endpoint = pm.acquire(name='brightdata-resi', purpose='important-task')
```

### 2. Concurrency Management

```python
# Set limits in config
{
  "name": "brightdata-resi",
  "concurrency_limit": 100,  # Max 100 concurrent connections
  ...
}

# Handle concurrency errors
try:
    endpoint = pm.acquire(name='brightdata-resi')
except RuntimeError as e:
    if "Concurrency limit reached" in str(e):
        print("Too many active connections, waiting...")
        time.sleep(5)
        endpoint = pm.acquire(name='brightdata-resi')
```

### 3. Error Handling

```python
from servbot.proxy import ProxyManager, load_provider_configs
from servbot.proxy.tester import ProxyTester

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

def acquire_tested_proxy(provider_name, max_attempts=3):
    """Acquire and test proxy before use."""
    for attempt in range(max_attempts):
        endpoint = pm.acquire(name=provider_name)
        
        # Test proxy
        result = ProxyTester.test_single_proxy(endpoint, timeout=5)
        
        if result.success:
            return endpoint
        else:
            pm.release(endpoint, reason='test-failed')
            print(f"Proxy test failed (attempt {attempt + 1}): {result.error}")
    
    raise RuntimeError(f"Failed to acquire working proxy after {max_attempts} attempts")

# Use it
endpoint = acquire_tested_proxy('mooproxy-us')
# ... use endpoint ...
pm.release(endpoint)
```

### 4. Regional Targeting

```python
# Target specific regions for better relevance
us_endpoint = pm.acquire(region='US', purpose='us-registration')
uk_endpoint = pm.acquire(region='GB', purpose='uk-registration')
```

### 5. Metric Tracking

```python
# Enable metering for all production usage
pm = ProxyManager(configs, enable_metering=True)

# Regularly check usage
stats = pm.get_stats()
summary = stats['usage_summary']

if summary['total_cost_estimate'] > 100:  # $100 threshold
    print("WARNING: Proxy costs exceeding budget!")
```

## Troubleshooting

### "Proxy provider not found"

**Cause:** Provider name in `acquire()` doesn't match config.

**Solution:**
```python
# List available providers
stats = pm.get_stats()
print("Available providers:", list(stats['providers'].keys()))
```

### "Concurrency limit reached"

**Cause:** Too many active connections to a provider.

**Solution:**
- Increase `concurrency_limit` in config
- Release proxies when done: `pm.release(endpoint)`
- Use different provider: `pm.acquire()  # auto-selects`

### Proxy Test Failures

**Cause:** Proxy credentials invalid, network issues, or proxy provider down.

**Solution:**
1. Verify credentials in config
2. Check environment variables
3. Test manually with curl:
   ```bash
   curl -x http://user:pass@proxy:port http://httpbin.org/ip
   ```

### High Costs

**Cause:** Inefficient bandwidth usage.

**Solution:**
- Enable traffic profiles: `traffic_profile="minimal"`
- Use network metering: `measure_network=True`
- Switch to cheaper providers for non-critical tasks
- Optimize allowlists to reduce third-party requests

## API Reference

### ProxyManager

**Methods:**
- `acquire(name=None, region=None, purpose=None)` - Acquire a proxy endpoint
- `release(endpoint, reason=None)` - Release a proxy endpoint
- `get_meter()` - Get the ProxyMeter instance
- `get_stats()` - Get current statistics

### ProxyMeter

**Methods:**
- `record_acquire(endpoint)` - Record endpoint acquisition
- `record_request(endpoint, bytes_sent, bytes_received, success)` - Record request
- `record_release(endpoint, reason)` - Record endpoint release
- `get_metrics(provider=None)` - Get metrics, optionally filtered by provider
- `get_summary()` - Get aggregated summary

### ProxyTester

**Methods:**
- `test_single_proxy(endpoint, test_url, timeout)` - Test a single proxy
- `test_batch(endpoints, test_url, timeout, max_workers, progress_callback)` - Test multiple proxies in parallel
- `print_test_summary(results)` - Print formatted summary of test results

### ProxyEndpoint

**Attributes:**
- `scheme`, `host`, `port` - Connection details
- `username`, `password` - Authentication
- `provider` - Provider name
- `session` - Session ID
- `proxy_type` - ProxyType enum (residential, datacenter, isp, mobile)
- `ip_version` - IPVersion enum (ipv4, ipv6)
- `rotation_type` - RotationType enum (rotating, sticky)
- `region` - Country/region code
- `metadata` - Additional provider-specific data

**Methods:**
- `as_requests_proxies()` - Format for requests library
- `as_playwright_proxy()` - Format for Playwright

## See Also

- [Browser Automation Guide](BROWSER_AUTOMATION.md)
- [Network Metering Guide](NETWORK_METERING.md)
- [Main README](../README.md)
