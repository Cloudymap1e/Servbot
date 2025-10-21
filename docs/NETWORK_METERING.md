# Network Metering Guide

Comprehensive guide to servbot's network traffic measurement and optimization system.

## Overview

Servbot includes a lightweight network metering system that uses Chrome DevTools Protocol (CDP) to measure real bandwidth consumption during browser automation workflows. This helps you:

- Track actual bandwidth usage per registration
- Measure effectiveness of traffic optimization
- Estimate proxy costs accurately
- Identify bandwidth-heavy domains and resource types
- Optimize traffic profiles for specific sites

## Quick Start

### Enable Metering

```python
from servbot import register_service_account

result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    measure_network=True  # Enable metering
)
```

### View Results

Metering data is automatically saved to `servbot/data/network/{timestamp}_net_{profile}.json`:

```bash
$ cat servbot/data/network/1761050076879_net_minimal.json
```

## How It Works

### Chrome DevTools Protocol Integration

The `NetworkMeter` class hooks into Playwright's CDP session to capture real network events:

1. **Network.enable**: Enable CDP network tracking
2. **Network.responseReceived**: Capture response metadata (URL, type, domain)
3. **Network.loadingFinished**: Capture actual bytes transferred (`encodedDataLength`)

**Key Metric: `encodedDataLength`**
- This is the on-wire compressed byte count
- Represents actual bandwidth used (not uncompressed size)
- Matches what proxy providers measure and bill for

### Automatic Integration

When `measure_network=True` is set:

1. Meter starts before page navigation
2. Events are captured throughout the flow
3. Meter stops after registration completes
4. Blocked request counters are injected from BrowserBot
5. JSON report is saved to `data/network/`
6. Path is added to registration artifacts

## Output Format

### Complete JSON Structure

```json
{
  "profile": {
    "traffic_profile": "minimal",
    "allowed_domains": ["reddit.com", "redditstatic.com"]
  },
  "totals": {
    "encoded_bytes": 823456,
    "requests": 47
  },
  "per_type": {
    "document": {
      "bytes": 45123,
      "requests": 1
    },
    "script": {
      "bytes": 512000,
      "requests": 18
    },
    "xhr": {
      "bytes": 124000,
      "requests": 12
    },
    "fetch": {
      "bytes": 98000,
      "requests": 8
    },
    "other": {
      "bytes": 44333,
      "requests": 8
    }
  },
  "per_domain": {
    "reddit.com": {
      "bytes": 678000,
      "requests": 35
    },
    "redditstatic.com": {
      "bytes": 123456,
      "requests": 10
    },
    "redditmedia.com": {
      "bytes": 22000,
      "requests": 2
    }
  },
  "blocked": {
    "images": 45,
    "fonts": 8,
    "media": 2,
    "stylesheets": 0,
    "third_party": 67,
    "analytics": 12
  },
  "timings": {
    "meter_start": 1761050076.879,
    "meter_stop": 1761050110.068
  }
}
```

### Field Descriptions

#### profile
- `traffic_profile`: Traffic optimization mode ("off", "minimal", "ultra")
- `allowed_domains`: Allowlist when third-party blocking is enabled

#### totals
- `encoded_bytes`: Total compressed bytes transferred (actual bandwidth)
- `requests`: Total number of requests completed

#### per_type
Breakdown by resource type:
- `document`: HTML pages
- `script`: JavaScript files
- `stylesheet`: CSS files (if not blocked)
- `image`: Images (if not blocked)
- `font`: Fonts (if not blocked)
- `media`: Video/audio (if not blocked)
- `xhr`: XMLHttpRequest calls
- `fetch`: Fetch API calls
- `other`: Other resource types

#### per_domain
Breakdown by hostname - useful for identifying:
- Heavy third-party resources
- CDN usage patterns
- API call volumes

#### blocked
Count of requests blocked by traffic optimization:
- `images`: Image requests blocked
- `fonts`: Font requests blocked
- `media`: Media requests blocked
- `stylesheets`: CSS requests blocked (ultra mode only)
- `third_party`: Third-party domain requests blocked
- `analytics`: Analytics/tracking requests blocked

#### timings
- `meter_start`: Unix timestamp when metering started
- `meter_stop`: Unix timestamp when metering stopped

## Traffic Profiles Comparison

### Baseline (off)

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="off",
    measure_network=True
)
```

**Typical Reddit Results:**
```json
{
  "totals": {
    "encoded_bytes": 3200000,  // ~3.2 MB
    "requests": 180
  },
  "blocked": {
    "images": 0,
    "fonts": 0,
    "media": 0,
    "stylesheets": 0,
    "third_party": 0,
    "analytics": 0
  }
}
```

### Minimal Mode

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="minimal",
    measure_network=True
)
```

**Typical Reddit Results:**
```json
{
  "totals": {
    "encoded_bytes": 820000,  // ~820 KB (~74% reduction)
    "requests": 47
  },
  "blocked": {
    "images": 45,
    "fonts": 8,
    "media": 2,
    "stylesheets": 0,
    "third_party": 67,
    "analytics": 12
  }
}
```

**Savings:** ~2.4 MB (74% reduction)

### Ultra Mode

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="ultra",
    measure_network=True
)
```

**Typical Reddit Results:**
```json
{
  "totals": {
    "encoded_bytes": 410000,  // ~410 KB (~87% reduction)
    "requests": 35
  },
  "blocked": {
    "images": 45,
    "fonts": 8,
    "media": 2,
    "stylesheets": 12,
    "third_party": 67,
    "analytics": 12
  }
}
```

**Savings:** ~2.8 MB (87% reduction)

**⚠️ Note:** Ultra mode may break some sites due to missing CSS.

## Analysis Techniques

### Calculate Bandwidth Costs

```python
import json

# Load metering data
with open('data/network/1761050076879_net_minimal.json') as f:
    data = json.load(f)

# Calculate costs (example: $12/GB residential proxy)
bytes_used = data['totals']['encoded_bytes']
gb_used = bytes_used / (1024 ** 3)
cost_per_gb = 12.0
total_cost = gb_used * cost_per_gb

print(f"Bandwidth: {bytes_used:,} bytes ({gb_used:.4f} GB)")
print(f"Cost: ${total_cost:.4f}")
```

### Compare Profiles

```python
import json

profiles = ['off', 'minimal', 'ultra']
results = {}

for profile in profiles:
    # Load each profile's results
    with open(f'data/network/example_{profile}.json') as f:
        data = json.load(f)
        results[profile] = data['totals']['encoded_bytes']

baseline = results['off']
for profile in ['minimal', 'ultra']:
    savings = baseline - results[profile]
    pct = (savings / baseline) * 100
    print(f"{profile}: {results[profile]:,} bytes (saved {savings:,} bytes, {pct:.1f}%)")
```

### Identify Heavy Domains

```python
import json

with open('data/network/result.json') as f:
    data = json.load(f)

# Sort domains by bytes
domains = sorted(
    data['per_domain'].items(),
    key=lambda x: x[1]['bytes'],
    reverse=True
)

print("Top 10 domains by bandwidth:")
for domain, stats in domains[:10]:
    mb = stats['bytes'] / (1024 * 1024)
    print(f"  {domain}: {mb:.2f} MB ({stats['requests']} requests)")
```

### Identify Heavy Resource Types

```python
import json

with open('data/network/result.json') as f:
    data = json.load(f)

# Sort resource types by bytes
types = sorted(
    data['per_type'].items(),
    key=lambda x: x[1]['bytes'],
    reverse=True
)

print("Resource types by bandwidth:")
for rtype, stats in types:
    mb = stats['bytes'] / (1024 * 1024)
    print(f"  {rtype}: {mb:.2f} MB ({stats['requests']} requests)")
```

## Integration with Proxy Metering

### Combined Usage Tracking

```python
from servbot.proxy import load_provider_configs, ProxyManager
from servbot import register_service_account

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs, enable_metering=True)

# Acquire proxy
endpoint = pm.acquire(region='US', purpose='reddit-reg')

# Run registration with network metering
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    proxy=endpoint.as_playwright_proxy(),
    traffic_profile="minimal",
    measure_network=True
)

# Record bandwidth in proxy meter
import json
if result and 'artifacts' in result:
    for artifact in result['artifacts']:
        if artifact.endswith('.json') and 'net_' in artifact:
            with open(artifact) as f:
                net_data = json.load(f)
                bytes_used = net_data['totals']['encoded_bytes']
                
                # Record in proxy meter
                pm.get_meter().record_request(
                    endpoint,
                    bytes_sent=bytes_used // 10,  # Estimate upload
                    bytes_received=bytes_used,
                    success=True
                )

# Release proxy
pm.release(endpoint, reason='complete')

# View combined stats
stats = pm.get_stats()
summary = stats['usage_summary']
print(f"Total GB: {summary['total_gb']}")
print(f"Total cost: ${summary['total_cost_estimate']}")
```

## Best Practices

### 1. Baseline Measurement First

Always measure without optimization first:

```python
# Step 1: Measure baseline
baseline = register_service_account(
    service="MyService",
    website_url="https://myservice.com/register",
    provision_new=True,
    traffic_profile="off",
    measure_network=True
)

# Step 2: Measure with minimal
minimal = register_service_account(
    service="MyService",
    website_url="https://myservice.com/register",
    provision_new=True,
    traffic_profile="minimal",
    measure_network=True
)

# Compare results
```

### 2. Test Traffic Profiles Thoroughly

Different sites have different requirements:

```python
profiles = ["off", "minimal", "ultra"]
test_results = {}

for profile in profiles:
    result = register_service_account(
        service="MyService",
        website_url="https://myservice.com/register",
        provision_new=True,
        traffic_profile=profile if profile != "off" else None,
        measure_network=True
    )
    
    test_results[profile] = {
        "success": result and result['status'] == 'success',
        "artifacts": result.get('artifacts', []) if result else []
    }

# Analyze which profile works best
```

### 3. Monitor Blocked Counters

High blocked counts indicate effective optimization:

```python
import json

with open('data/network/result.json') as f:
    data = json.load(f)

blocked = data['blocked']
total_blocked = sum(blocked.values())

print(f"Total blocked: {total_blocked} requests")
print(f"  Images: {blocked['images']}")
print(f"  Third-party: {blocked['third_party']}")
print(f"  Analytics: {blocked['analytics']}")
```

### 4. Tune Allowlists Based on Data

Use per_domain data to refine allowlists:

```python
import json

with open('data/network/result.json') as f:
    data = json.load(f)

# Find domains that should be allowed
for domain, stats in data['per_domain'].items():
    if stats['bytes'] > 100000:  # >100 KB
        print(f"Consider allowing: {domain} ({stats['bytes']:,} bytes)")
```

### 5. Disable Screenshots During Metering

Screenshots add overhead and are automatically disabled:

```python
# Screenshots automatically disabled when measure_network=True
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    measure_network=True  # Screenshots disabled for accurate measurement
)
```

## Advanced Usage

### Custom Meter Integration

```python
from servbot.automation.netmeter import NetworkMeter
from servbot.automation.engine import BrowserBot
from servbot.automation.flows.generic import GenericEmailCodeFlow, FlowConfig

# Create custom meter
meter = NetworkMeter(profile_name="custom", allowlist=["example.com"])

# Create bot
bot = BrowserBot(
    headless=True,
    traffic_profile="minimal",
    block_third_party=True,
    allowed_domains=["example.com"],
    measure_network=False  # We'll manage meter manually
)

# Run flow with manual meter control
with sync_playwright() as p:
    # ... setup context and page ...
    
    # Start meter
    meter.start(page)
    
    # Run flow
    flow = GenericEmailCodeFlow(...)
    result = flow.perform_registration(...)
    
    # Stop meter
    meter.stop()
    meter.set_blocked_counters(bot._blocked_counters)
    
    # Save
    meter.save_json('custom_result.json')
```

### Aggregate Multiple Runs

```python
import json
import glob

# Collect all minimal profile results
pattern = 'data/network/*_net_minimal.json'
total_bytes = 0
total_requests = 0
count = 0

for filepath in glob.glob(pattern):
    with open(filepath) as f:
        data = json.load(f)
        total_bytes += data['totals']['encoded_bytes']
        total_requests += data['totals']['requests']
        count += 1

if count > 0:
    avg_bytes = total_bytes / count
    avg_requests = total_requests / count
    print(f"Average per registration:")
    print(f"  Bytes: {avg_bytes:,.0f} ({avg_bytes / (1024**2):.2f} MB)")
    print(f"  Requests: {avg_requests:.0f}")
```

### Cost Estimation Dashboard

```python
import json
import glob
from collections import defaultdict

# Group by profile
by_profile = defaultdict(list)

for filepath in glob.glob('data/network/*_net_*.json'):
    with open(filepath) as f:
        data = json.load(f)
        profile = data['profile']['traffic_profile']
        bytes_used = data['totals']['encoded_bytes']
        by_profile[profile].append(bytes_used)

# Calculate stats
cost_per_gb = 12.0  # $12/GB residential proxy

for profile, bytes_list in by_profile.items():
    avg_bytes = sum(bytes_list) / len(bytes_list)
    avg_gb = avg_bytes / (1024 ** 3)
    avg_cost = avg_gb * cost_per_gb
    
    print(f"\n{profile.upper()} Profile:")
    print(f"  Registrations: {len(bytes_list)}")
    print(f"  Avg bandwidth: {avg_bytes:,.0f} bytes ({avg_gb:.4f} GB)")
    print(f"  Avg cost: ${avg_cost:.4f}")
    print(f"  Cost per 1000: ${avg_cost * 1000:.2f}")
```

## Troubleshooting

### Meter Shows 0 Bytes

**Cause:** CDP session failed to attach or network events not firing.

**Solution:**
- Ensure Playwright is up to date
- Check that Chromium is being used (not Firefox/WebKit)
- Verify page actually loads (check debug screenshots)

### Blocked Counters Don't Match per_domain

**Cause:** Blocked requests are counted before CDP sees them (route.abort()).

**Solution:**
- Blocked counters are separate from successful requests
- `per_domain` only shows requests that completed
- Sum both for total request attempt count

### Timings Show Negative Duration

**Cause:** Clock skew or meter not properly stopped.

**Solution:**
- Always call `meter.stop()` after flow completes
- Check system clock

### High Bandwidth Despite "ultra" Mode

**Cause:** Allowed domains are too broad or site uses heavy API calls.

**Solution:**
- Review `per_domain` to identify heavy domains
- Narrow `allowed_domains` if possible
- Some sites have unavoidable API overhead

## Performance Impact

### Overhead of Metering

Metering has minimal performance impact:

- **CPU:** <1% additional CPU usage
- **Memory:** <10 MB additional memory
- **Latency:** No measurable impact on page load times
- **Screenshot Overhead:** Automatically disabled when metering enabled

### When to Disable Metering

Disable metering for:
- Production high-volume scenarios (after baseline measurement)
- When screenshots are more important than metrics
- When debugging registration flow (screenshots provide more value)

### When to Enable Metering

Enable metering for:
- Baseline measurements
- Traffic profile optimization
- Cost estimation
- Proxy provider comparison
- Bandwidth-limited scenarios

## See Also

- [Browser Automation Guide](BROWSER_AUTOMATION.md)
- [Proxy System Guide](PROXIES.md)
- [Main README](../README.md)

