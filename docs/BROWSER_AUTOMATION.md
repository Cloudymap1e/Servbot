# Browser Automation Guide

Complete guide to servbot's browser automation system for automated service registration workflows.

## Overview

Servbot's browser automation system uses Playwright to perform complete end-to-end registration flows on websites, including:

- Form filling with intelligent field detection
- Email verification code retrieval via Microsoft Graph
- Verification link clicking and OTP submission
- Session persistence (cookies and storage state)
- Traffic optimization for bandwidth reduction
- Network usage metering
- Debug screenshot capture with visual highlighting

## Quick Start

### Basic Registration Flow

```python
from servbot import register_service_account

result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,  # Auto-provision email from Flashmail
    headless=True
)

if result and result['status'] == 'success':
    print(f"✓ Registration successful!")
    print(f"  Email: {result['mailbox_email']}")
    print(f"  Username: {result['service_username']}")
```

### With Existing Email Account

```python
result = register_service_account(
    service="GitHub",
    website_url="https://github.com/signup",
    mailbox_email="existing@outlook.com",  # Use existing account
    headless=True
)
```

### With Custom Form Configuration

```python
from servbot.automation.flows.generic import FlowConfig

config = FlowConfig(
    email_input="input[name='email']",
    username_input="input[name='username']",
    password_input="input[name='password']",
    submit_button="button[type='submit']",
    otp_input="input[name='otp_token']",
    success_selector=".dashboard-home"
)

result = register_service_account(
    service="CustomService",
    website_url="https://example.com/register",
    provision_new=True,
    flow_config=config
)
```

## Architecture

### Core Components

#### 1. BrowserBot (engine.py)

The orchestrator that manages Playwright browser context and runs registration flows.

**Features:**
- Persistent browser contexts with profile directories
- Proxy support (HTTP/HTTPS/SOCKS5)
- Anti-detection stealth measures
- Traffic optimization profiles
- Network traffic metering
- Debug artifact collection

**Key Methods:**
```python
from servbot.automation.engine import BrowserBot

bot = BrowserBot(
    headless=True,
    user_data_dir="/path/to/profile",
    proxy={"server": "http://proxy:8080"},
    default_timeout=300,
    traffic_profile="minimal",
    measure_network=True
)

result = bot.run_flow(
    flow=my_flow,
    email_account=email_account,
    timeout_sec=300,
    prefer_link=True
)
```

#### 2. RegistrationFlow (Abstract Base)

Base class for implementing registration workflows.

**Required Method:**
```python
def perform_registration(
    self,
    page,                    # Playwright page object
    actions: ActionHelper,   # Helper for debug-friendly actions
    email_account: EmailAccount,
    fetch_verification: Callable,
    timeout_sec: int,
    prefer_link: bool
) -> RegistrationResult:
    # Implementation here
    pass
```

#### 3. GenericEmailCodeFlow (flows/generic.py)

Pre-built flow for email+OTP registration patterns.

**Flow Steps:**
1. Navigate to signup page
2. Accept cookies (if configured)
3. Fill email, username, password fields
4. Submit form
5. Fetch verification (code or link) via Microsoft Graph
6. Submit verification
7. Wait for success indicator

**Configuration:**
```python
from servbot.automation.flows.generic import FlowConfig

config = FlowConfig(
    # Required
    email_input="input[type=email]",
    submit_button="button[type=submit]",
    
    # Optional pre-email button
    email_start_button="button:has-text('Continue with email')",
    
    # Optional fields
    username_input="input[name=username]",
    password_input="input[name=password]",
    password_confirm_input="input[name=password_confirm]",
    accept_cookies_button="#accept-cookies",
    
    # OTP submission (single input)
    otp_input="input[name=otp]",
    otp_submit_button="button:has-text('Verify')",
    
    # OR multiple OTP inputs (digit-by-digit)
    otp_inputs=["#digit1", "#digit2", "#digit3", "#digit4", "#digit5", "#digit6"],
    
    # Success detection
    success_selector=".dashboard",
    
    # Timing
    pre_submit_pause_ms=1500,
    post_submit_wait_ms=4000
)
```

#### 4. ActionHelper (engine.py)

Provides debug-friendly interactions with visual feedback.

**Features:**
- Red outline highlighting on elements
- Before/after screenshots for each action
- Automatic scrolling to elements
- Activity timestamp tracking

**Methods:**
```python
actions.screenshot("label")
actions.click("button#submit", label="submit_form")
actions.fill("input#email", "user@example.com", label="email_input")
```

#### 5. VisionHelper (vision.py)

Fallback mechanism for intelligent form filling when selectors fail.

**Features:**
- DOM-based element labeling
- Semantic field detection (email, username, password, OTP)
- Coordinate-based clicking when selectors fail
- Label text extraction from associated `<label>` tags

**Usage (automatic fallback):**
```python
# GenericEmailCodeFlow automatically uses VisionHelper when:
# - CSS selector fails to find element
# - Element is not visible
# - Click/fill action throws exception
```

## Traffic Optimization

### Traffic Profiles

Three modes for bandwidth reduction:

#### Off (Default)
```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="off"  # or None
)
```
- Normal browsing behavior
- All resources loaded
- No blocking

#### Minimal Mode
```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="minimal"
)
```

**Blocks:**
- Images (`--blink-settings=imagesEnabled=false`)
- Fonts
- Media (video/audio)
- Analytics/tracking domains
- Prefetch/preload hints

**Adds Headers:**
- `Save-Data: on`

**Reduction:** ~60-80% bandwidth savings

#### Ultra Mode
```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="ultra"
)
```

**Blocks (in addition to minimal):**
- Stylesheets (CSS)

**Reduction:** ~80-90% bandwidth savings

**⚠️ Warning:** May break some sites. Test thoroughly.

### Third-Party Blocking

Block all requests except allowed domains:

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    block_third_party=True,
    allowed_domains=["reddit.com", "redditstatic.com", "redditmedia.com", "redd.it"]
)
```

**Auto-detection for Reddit:**
If `block_third_party=True` and `allowed_domains=None`, Reddit flows automatically use:
```python
["reddit.com", "redditstatic.com", "redditmedia.com", "redd.it"]
```

**Analytics Blocking:**
The following tracking domains are always blocked when traffic profiles are enabled:
- `googletagmanager.com`, `google-analytics.com`
- `doubleclick.net`, `g.doubleclick.net`
- `sentry.io`, `newrelic.com`, `datadoghq.com`
- `intercom.io`, `hotjar.com`
- `amplitude.com`, `mixpanel.com`, `segment.io`
- `facebook.net`, `facebook.com`
- Reddit telemetry: `w3-reporting.reddit.com`, `error-tracking.reddit.com`, `events.reddit.com`

## Network Metering

Track bandwidth consumption in real-time using Chrome DevTools Protocol.

### Enable Metering

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="minimal",
    measure_network=True  # Enable metering
)
```

### Output

Metering data is saved to `servbot/data/network/{timestamp}_net_{profile}.json`:

```json
{
  "profile": {
    "traffic_profile": "minimal",
    "allowed_domains": ["reddit.com"]
  },
  "totals": {
    "encoded_bytes": 1234567,
    "requests": 42
  },
  "per_type": {
    "document": {"bytes": 50000, "requests": 1},
    "script": {"bytes": 800000, "requests": 15},
    "xhr": {"bytes": 150000, "requests": 10}
  },
  "per_domain": {
    "reddit.com": {"bytes": 900000, "requests": 30},
    "redditstatic.com": {"bytes": 334567, "requests": 12}
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
    "meter_start": 1760889052.011,
    "meter_stop": 1760889232.314
  }
}
```

### Interpreting Results

- **encoded_bytes**: On-wire compressed bytes (actual bandwidth used)
- **per_type**: Breakdown by resource type (document, script, xhr, stylesheet, font, image, etc.)
- **per_domain**: Breakdown by hostname
- **blocked**: Count of blocked requests by category

**Note:** When metering is enabled, screenshots are disabled to avoid extra overhead.

## Anti-Detection Features

BrowserBot includes stealth measures to avoid detection:

### 1. WebDriver Masking
```javascript
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
```

### 2. Chrome Runtime
```javascript
window.chrome = { runtime: {} };
```

### 3. Realistic Navigator Properties
```javascript
navigator.languages = ['en-US','en']
navigator.plugins = [1,2,3,4,5]
navigator.hardwareConcurrency = 4
navigator.deviceMemory = 8
```

### 4. WebGL Vendor/Renderer Spoofing
```javascript
UNMASKED_VENDOR_WEBGL: 'Intel Inc.'
UNMASKED_RENDERER_WEBGL: 'Intel(R) UHD Graphics'
```

### 5. Realistic User Agent
```python
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
```

### 6. Standard Browser Args
```python
args = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--window-size=1280,900"
]
```

## Session Persistence

### Browser Profiles

Reuse browser profiles to maintain login state:

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/login",
    mailbox_email="user@outlook.com",
    user_data_dir="/path/to/reddit/profile"  # Persist cookies/storage
)

# Later, reuse the same profile
result2 = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/submit",
    mailbox_email="user@outlook.com",
    user_data_dir="/path/to/reddit/profile"  # Already logged in!
)
```

### Stored Data

The `registrations` database table stores:
- `cookies_json`: All cookies from the session
- `storage_state_json`: localStorage and sessionStorage
- `user_agent`: User agent string used
- `profile_dir`: Path to browser profile
- `debug_dir`: Path to debug screenshots

### Retrieving Session Data

```python
from servbot.data.database import get_registration_by_id
import json

reg = get_registration_by_id(registration_id)
cookies = json.loads(reg['cookies_json'])
storage_state = json.loads(reg['storage_state_json'])
```

## Debug Artifacts

### Screenshot Capture

Every action creates before/after screenshots with red outlines:

**Location:** `servbot/data/screenshots/run-{timestamp}-{id}/`

**Files:**
- `{timestamp}_01_open.png` - Initial page load
- `{timestamp}_before_email.png` - Before filling email
- `{timestamp}_after_email.png` - After filling email
- `{timestamp}_before_submit_form.png` - Before submitting form
- `{timestamp}_after_submit_form.png` - After submitting form
- `{timestamp}_error.png` - On error (if any)

### Visual Highlighting

Elements are outlined in red during actions:

```css
.servbot-highlight {
  outline: 4px solid rgba(255, 0, 0, 0.8) !important;
  outline-offset: 2px !important;
}
```

### Disable Screenshots

When network metering is enabled, screenshots are automatically disabled to reduce overhead:

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    measure_network=True  # Screenshots disabled
)
```

## Proxy Integration

### Using Proxies with Browser Automation

```python
from servbot.proxy import load_provider_configs, ProxyManager
from servbot import register_service_account

# Setup proxy manager
configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

# Acquire proxy
endpoint = pm.acquire(region='US', purpose='reddit-registration')

# Use proxy in registration
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

### Playwright Proxy Format

```python
proxy = {
    "server": "http://proxy.example.com:8080",
    "username": "user",
    "password": "pass"
}
```

## Advanced Configuration

### Custom Flow Implementation

```python
from servbot.automation.engine import RegistrationFlow, RegistrationResult

class MyCustomFlow(RegistrationFlow):
    service_name = "MyService"
    entry_url = "https://myservice.com/signup"
    
    def perform_registration(self, page, actions, email_account, fetch_verification, timeout_sec, prefer_link):
        # Navigate
        page.goto(self.entry_url)
        actions.screenshot("01_start")
        
        # Custom logic here
        actions.fill("#email", email_account.email, label="email")
        actions.click("button.submit", label="submit")
        
        # Fetch verification
        code = fetch_verification(self.service_name, timeout_sec, prefer_link)
        
        if not code:
            raise RuntimeError("No verification received")
        
        # Submit code
        actions.fill("#code", code, label="otp")
        actions.click("#verify", label="verify")
        
        return RegistrationResult(
            success=True,
            service=self.service_name,
            website_url=self.entry_url,
            mailbox_email=email_account.email,
            service_username=email_account.email,
            service_password="generated-password"
        )
```

### Fallback Strategy

The system implements an automatic fallback:

1. **First Attempt:** Headless mode with stealth
2. **On Failure:** Headed mode (visible browser) for debugging

```python
# Automatic fallback is built-in
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    headless=True  # Will retry with headless=False if this fails
)
```

### Timeout Configuration

```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    timeout_seconds=600  # Total flow timeout (default: 300)
    # Individual step timeout is fixed at 10s
)
```

## Error Handling

### Common Errors

**1. "Verification not received within timeout"**
- Email verification didn't arrive in time
- Increase `timeout_seconds`
- Check mailbox credentials

**2. "Blocked by network security"**
- Site detected automation
- Try using a proxy
- Use residential proxy instead of datacenter

**3. "OTP entry failed: no suitable selector detected"**
- Form structure doesn't match selectors
- Provide custom `flow_config`
- Check debug screenshots for actual form structure

**4. "playwright not installed"**
- Run: `playwright install chromium`

### Error Recovery

Registration results include error details:

```python
result = register_service_account(...)

if not result or result['status'] == 'failed':
    # Access error details in database
    from servbot.data.database import get_registration_by_id
    reg = get_registration_by_id(result['registration_id'])
    print(f"Error: {reg['error']}")
    print(f"Debug dir: {reg['debug_dir']}")
    # Check screenshots in debug_dir
```

## Best Practices

### 1. Start Simple
```python
# First attempt without optimization
result = register_service_account(
    service="MyService",
    website_url="https://myservice.com/register",
    provision_new=True,
    headless=False  # Watch it work
)
```

### 2. Optimize Gradually
```python
# Then add traffic optimization
result = register_service_account(
    service="MyService",
    website_url="https://myservice.com/register",
    provision_new=True,
    headless=True,
    traffic_profile="minimal",
    measure_network=True  # Measure savings
)
```

### 3. Test Third-Party Blocking
```python
# Test allowlist carefully
result = register_service_account(
    service="MyService",
    website_url="https://myservice.com/register",
    provision_new=True,
    block_third_party=True,
    allowed_domains=["myservice.com"],  # May need to add CDN domains
    measure_network=True
)
```

### 4. Use Proxies for Scale
```python
# For production, use proxies
from servbot.proxy import load_provider_configs, ProxyManager

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs)

for i in range(100):
    endpoint = pm.acquire(region='US')
    result = register_service_account(
        service="MyService",
        website_url="https://myservice.com/register",
        provision_new=True,
        proxy=endpoint.as_playwright_proxy(),
        traffic_profile="minimal"
    )
    pm.release(endpoint)
```

### 5. Monitor Artifacts
```python
# Check debug dir after failures
result = register_service_account(...)
if result:
    print(f"Debug dir: {result.get('debug_dir')}")
    # Review screenshots at that location
```

## Performance Considerations

### Memory Usage
- Each browser instance uses ~200-500 MB RAM
- Headless mode uses slightly less than headed
- Close browsers by not reusing `user_data_dir`

### Bandwidth Usage
| Profile | Typical Site | Reddit |
|---------|-------------|--------|
| off | 2-5 MB | ~3 MB |
| minimal | 0.5-1.5 MB | ~800 KB |
| ultra | 0.2-0.8 MB | ~400 KB |

### Execution Time
- Average registration: 20-60 seconds
- Email verification fetch: 5-30 seconds
- Total with retries: 1-3 minutes

## Integration Examples

### Bulk Registration

```python
from servbot import register_service_account
from servbot.proxy import load_provider_configs, ProxyManager

configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs, enable_metering=True)

services = [
    {"name": "Reddit", "url": "https://www.reddit.com/register"},
    {"name": "GitHub", "url": "https://github.com/signup"},
    {"name": "Discord", "url": "https://discord.com/register"}
]

results = []
for svc in services:
    endpoint = pm.acquire(region='US')
    try:
        result = register_service_account(
            service=svc["name"],
            website_url=svc["url"],
            provision_new=True,
            proxy=endpoint.as_playwright_proxy(),
            traffic_profile="minimal",
            measure_network=True
        )
        results.append(result)
    finally:
        pm.release(endpoint)

# View usage summary
stats = pm.get_stats()
print(f"Total data used: {stats['usage_summary']['total_gb']} GB")
print(f"Estimated cost: ${stats['usage_summary']['total_cost_estimate']}")
```

### With Error Handling

```python
import time
from servbot import register_service_account

max_retries = 3
for attempt in range(max_retries):
    try:
        result = register_service_account(
            service="MyService",
            website_url="https://myservice.com/register",
            provision_new=True,
            traffic_profile="minimal"
        )
        
        if result and result['status'] == 'success':
            print(f"✓ Success on attempt {attempt + 1}")
            break
        else:
            print(f"✗ Failed attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(30)  # Wait before retry
    except Exception as e:
        print(f"✗ Error on attempt {attempt + 1}: {e}")
        if attempt < max_retries - 1:
            time.sleep(30)
```

## Troubleshooting

### Screenshots Show Wrong Elements Highlighted
- CSS selectors may have changed
- Provide custom `flow_config` with correct selectors
- Use VisionHelper fallback (automatic)

### Registration Succeeds But Status is "failed"
- Check `success_selector` in flow config
- May need to adjust success detection

### High Bandwidth Usage Despite "minimal" Profile
- Check `allowed_domains` - may be too permissive
- Review network metering output to identify heavy domains
- Consider "ultra" profile

### Proxies Not Working
- Verify proxy format: `{"server": "http://host:port", "username": "user", "password": "pass"}`
- Test proxy separately with `ProxyTester`
- Check firewall/network settings

## See Also

- [Proxy System Documentation](PROXIES.md)
- [Network Metering Documentation](NETWORK_METERING.md)
- [CLI Guide](CLI_GUIDE.md)
- [Main README](../README.md)

