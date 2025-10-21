# Servbot - Email Verification Code Extraction System

A comprehensive, production-ready email automation tool for fetching and extracting verification codes from emails, with advanced browser automation capabilities for complete service registration workflows.

## Features

### Core Email Features
- **Multi-Protocol Support**: IMAP and Microsoft Graph API
- **Intelligent Parsing**: Regex patterns with AI fallback (Cerebras)
- **100+ Services**: Pre-configured patterns for popular services
- **Account Provisioning**: Integration with Flashmail/Shanyouxiang API
- **Database Persistence**: SQLite storage for messages and verifications

### Browser Automation (NEW!)
- **Automated Registration**: Complete signup flows for websites using Playwright
- **Vision-Assisted Forms**: Intelligent form filling with fallback mechanisms
- **Email Verification Integration**: Automatic verification code retrieval and submission
- **Traffic Optimization**: Minimal/ultra modes for bandwidth reduction
- **Session Persistence**: Cookie and storage state management
- **Debug Artifacts**: Screenshot capture with visual element highlighting

### Proxy Management (NEW!)
- **Multi-Provider Support**: Static lists, BrightData, MooProxy
- **Advanced Metering**: Detailed usage tracking and cost estimation
- **Concurrency Control**: Per-provider connection limits
- **Proxy Types**: Residential, datacenter, ISP, and mobile proxies
- **Region Targeting**: Country/city-based proxy selection
- **Comprehensive Testing**: Built-in proxy testing and validation

### Network Optimization (NEW!)
- **Traffic Profiling**: Minimal and ultra modes for bandwidth reduction
- **Network Metering**: Real-time bandwidth tracking via Chrome DevTools Protocol
- **Third-Party Blocking**: Selective domain allowlisting
- **Analytics Blocking**: Automatic blocking of telemetry and tracking
- **Resource Filtering**: Image, font, stylesheet, and media blocking

### Architecture
- **Clean Architecture**: Modular, well-documented, Google Style compliant
- **Type Safety**: Comprehensive type hints throughout
- **Extensible Design**: Easy to add new providers, flows, and parsers

## Installation

```bash
pip install -r requirements.txt
```

## Usage Options

Servbot can be used in two ways:

1. **Interactive CLI** (NEW!) - Command-line interface for easy management
2. **Python API** - Programmatic integration in your code

### Interactive CLI

Start the interactive command-line interface:

```bash
python -m servbot
```

Or use the startup scripts:
```bash
# Windows
run.bat

# Linux/Mac
./run.sh
```

The CLI provides commands for:
- Managing email accounts (`accounts`, `provision`, `add`)
- Checking verification codes (`check`, `check-all`, `inbox`)
- Flashmail operations (`balance`, `inventory`)
- Database queries (`database`)

**See [docs/CLI_GUIDE.md](docs/CLI_GUIDE.md) for complete documentation.**

### Python API

Import and use Servbot in your Python code:

```python
from servbot import fetch_verification_codes

verifications = fetch_verification_codes(
    imap_server="imap.gmail.com",
    username="your-email@gmail.com",
    password="your-password"
)
```

### Browser Automation

Automate complete registration flows with built-in verification:

```python
from servbot import register_service_account

result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,  # Auto-provision new email
    traffic_profile="minimal",  # Reduce bandwidth usage
    measure_network=True  # Track bandwidth consumption
)

if result:
    print(f"✓ Account created: {result['mailbox_email']}")
    print(f"✓ Status: {result['status']}")
```

## Quick Start

### Basic Usage

```python
from servbot import fetch_verification_codes

# Fetch all verification codes
verifications = fetch_verification_codes(
    imap_server="imap.gmail.com",
    username="your-email@gmail.com",
    password="your-password"
)

for v in verifications:
    print(v.as_pair())  # Output: <Service, Code>
```

### Get Verification for Specific Service

```python
from servbot import get_verification_for_service

# Wait for verification from specific service
code = get_verification_for_service(
    target_service="GitHub",
    imap_server="imap.gmail.com",
    username="your-email@gmail.com",
    password="your-password",
    timeout_seconds=60
)

print(f"GitHub verification: {code}")
```

### Flashmail Integration

```python
from servbot import provision_flashmail_account

# Provision account and get verification in one call
result = provision_flashmail_account(
    card="your-flashmail-api-key",
    target_service="Discord"
)

if result:
    print(f"Email: {result['email']}")
    print(f"Code: {result['value']}")
```

### Browser Automation - Complete Registration Flow

```python
from servbot import register_service_account

# Automated registration with all features
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,              # Auto-provision email from Flashmail
    headless=True,                   # Run in headless mode
    traffic_profile="minimal",       # Reduce bandwidth (blocks images, fonts, etc.)
    block_third_party=True,          # Block third-party domains
    allowed_domains=["reddit.com"],  # Allowlist for third-party blocking
    measure_network=True,            # Measure bandwidth consumption
    timeout_seconds=300
)

if result and result['status'] == 'success':
    print(f"✓ Registration successful!")
    print(f"  Email: {result['mailbox_email']}")
    print(f"  Username: {result['service_username']}")
    print(f"  Registration ID: {result['registration_id']}")
```

### Proxy Management

```python
from servbot.proxy import load_provider_configs, ProxyManager

# Load proxy configurations
configs = load_provider_configs('config/proxies.json')
pm = ProxyManager(configs, enable_metering=True)

# Acquire proxy (auto-selects cheapest)
endpoint = pm.acquire(region='US', purpose='registration')

# Use with browser automation
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    proxy=endpoint.as_playwright_proxy(),
    provision_new=True
)

# Release proxy when done
pm.release(endpoint, reason='complete')

# Get usage statistics
stats = pm.get_stats()
print(f"Active connections: {stats['total_active']}")
if 'usage_summary' in stats:
    summary = stats['usage_summary']
    print(f"Total requests: {summary['total_requests']}")
    print(f"Total data: {summary['total_gb']} GB")
    print(f"Estimated cost: ${summary['total_cost_estimate']}")
```

## Architecture

### Directory Structure

```
servbot/
├── __init__.py           # Public API exports
├── __main__.py           # CLI entry point (python -m servbot)
├── api.py                # High-level API functions
├── cli.py                # Interactive CLI implementation
├── main.py               # Direct CLI entry point
├── config.py             # Configuration loader
�?
├── core/                 # Core business logic
�?  ├── __init__.py
�?  ├── models.py         # Data classes (Verification, EmailAccount)
�?  └── verification.py   # Verification extraction logic
�?
├── clients/              # Email client implementations
�?  ├── __init__.py
�?  ├── base.py           # Abstract base client
�?  ├── imap.py           # IMAP client
�?  ├── graph.py          # Microsoft Graph API client
�?  └── flashmail.py      # Flashmail/Shanyou API client
�?
├── parsers/              # Content parsing modules
�?  ├── __init__.py
�?  ├── code_parser.py    # Regex-based code extraction
�?  ├── email_parser.py   # Email structure parsing
�?  ├── service_parser.py # Service identification
�?  └── ai_parser.py      # AI-powered fallback
�?
└── data/                 # Data layer
    ├── __init__.py
    ├── services.py       # Service catalog (100+ services)
    └── database.py       # SQLite operations
```

### Design Principles

1. **Separation of Concerns**: Clear boundaries between clients, parsers, and business logic
2. **Dependency Injection**: Clients and parsers are loosely coupled
3. **Single Responsibility**: Each module has one clear purpose
4. **Open/Closed**: Easy to extend (add new clients/parsers) without modification
5. **Type Safety**: Comprehensive type hints throughout

## API Reference

### Core Functions

#### `fetch_verification_codes()`

Fetches all verification codes from email.

**Parameters:**
- `imap_server` (str, optional): IMAP server address
- `username` (str, optional): Email username
- `password` (str, optional): Email password
- `port` (int): IMAP port (default: 993)
- `ssl` (bool): Use SSL (default: True)
- `folder` (str): Mail folder (default: "INBOX")
- `unseen_only` (bool): Only unread messages (default: True)
- `since` (datetime, optional): Only messages since this date
- `mark_seen` (bool): Mark as read after processing (default: False)
- `limit` (int): Max messages to fetch (default: 200)
- `prefer_graph` (bool): Try Graph API first (default: True)
- `use_ai` (bool): Use AI fallback (default: True)

**Returns:** `List[Verification]`

#### `get_verification_for_service()`

Fetches verification for a specific service with polling.

**Parameters:**
- `target_service` (str): Service name (e.g., "Google", "GitHub")
- `imap_server` (str, optional): IMAP server address
- `username` (str, optional): Email username
- `password` (str, optional): Email password
- `timeout_seconds` (int): Polling timeout (default: 60)
- `poll_interval_seconds` (int): Seconds between polls (default: 5)
- `prefer_link` (bool): Prefer links over codes (default: True)
- `prefer_graph` (bool): Try Graph API first (default: True)
- Additional IMAP parameters...

**Returns:** `Optional[str]` - Verification code/link or None

#### `provision_flashmail_account()`

Provisions Flashmail account and fetches verification.

**Parameters:**
- `card` (str): Flashmail API key
- `target_service` (str): Service to verify
- `account_type` (str): "outlook" or "hotmail" (default: "outlook")
- `timeout_seconds` (int): Verification timeout (default: 120)
- `poll_interval_seconds` (int): Poll interval (default: 5)
- `prefer_link` (bool): Prefer links (default: True)

**Returns:** `Optional[Dict]` with keys: email, password, service, value, is_link

#### `register_service_account()` (NEW!)

Runs a complete automated registration flow for a service website using Playwright.

**Parameters:**
- `service` (str): Service name (for identification)
- `website_url` (str): Registration page URL
- `mailbox_email` (str | None): Existing email to use (default: None)
- `provision_new` (bool): Auto-provision new Flashmail email (default: False)
- `account_type` (str): "outlook" or "hotmail" for new accounts (default: "outlook")
- `headless` (bool): Run browser in headless mode (default: True)
- `timeout_seconds` (int): Maximum time for registration (default: 300)
- `prefer_link` (bool): Prefer verification links over codes (default: True)
- `flow_config` (Dict | None): Custom FlowConfig for form selectors
- `user_data_dir` (str | None): Browser profile directory
- `proxy` (Dict | None): Proxy configuration (Playwright format)
- `traffic_profile` (str | None): Traffic optimization mode: "off", "minimal", "ultra" (default: None)
- `block_third_party` (bool): Block third-party domains (default: False)
- `allowed_domains` (List[str] | None): Allowlist for third-party blocking
- `measure_network` (bool): Enable network traffic metering (default: False)

**Returns:** `Optional[Dict]` with keys:
- `registration_id` (int): Database ID for this registration
- `service` (str): Service name
- `website_url` (str): Registration URL
- `mailbox_email` (str): Email used for registration
- `service_username` (str): Created username on service
- `status` (str): "success" or "failed"

**Example:**
```python
result = register_service_account(
    service="Reddit",
    website_url="https://www.reddit.com/register",
    provision_new=True,
    traffic_profile="minimal",
    block_third_party=True,
    allowed_domains=["reddit.com"],
    measure_network=True
)
```

**Traffic Profiles:**
- **off** (default): No traffic optimization
- **minimal**: Blocks images, fonts, media, analytics; enables Save-Data header
- **ultra**: Blocks images, fonts, media, stylesheets, analytics; enables Save-Data header

**Third-Party Blocking:**
When `block_third_party=True`, only requests to `allowed_domains` are permitted. Reddit uses a default allowlist if not specified: `["reddit.com", "redditstatic.com", "redditmedia.com", "redd.it"]`

### Models

#### `Verification`

Represents an extracted verification code or link.

**Attributes:**
- `service` (str): Service name
- `code` (str): Verification code or URL
- `uid` (int, optional): Message UID
- `subject` (str, optional): Email subject
- `from_addr` (str, optional): Sender address
- `date` (str, optional): Email date
- `is_link` (bool): True if code is a URL

**Methods:**
- `as_pair()`: Returns formatted string `<Service, Code>`

#### `EmailAccount`

Represents an email account configuration.

**Attributes:**
- `email` (str): Email address
- `password` (str): Account password
- `account_type` (str): Account type
- `source` (str): Source ("flashmail", "manual")
- `imap_server` (str, optional): IMAP server
- `card` (str, optional): Flashmail card ID

### Clients (Advanced Usage)

#### `IMAPClient`

Direct IMAP client for advanced use cases.

```python
from servbot import IMAPClient

client = IMAPClient(
    server="imap.gmail.com",
    username="user@gmail.com",
    password="password"
)

messages = client.fetch_messages(folder="INBOX", limit=50)
```

#### `GraphClient`

Microsoft Graph API client for Outlook/Office365.

```python
from servbot import GraphClient

client = GraphClient.from_credentials(
    refresh_token="your-refresh-token",
    client_id="your-client-id"
)

messages = client.fetch_messages(folder="inbox", limit=50)
```

#### `FlashmailClient`

Flashmail account provisioning client.

```python
from servbot import FlashmailClient

client = FlashmailClient(card="your-api-key")

# Check inventory
inventory = client.get_inventory()
print(f"Outlook accounts: {inventory['outlook']}")

# Provision accounts
accounts = client.fetch_accounts(quantity=5, account_type="outlook")
```

## Configuration

### AI Parsing (Optional)

Create `data/ai.api` with your Cerebras API key:

```
CEREBRAS_KEY = "your-api-key"
```

AI is used as an intelligent fallback when regex patterns fail.

### Microsoft Graph API (Optional)

For Outlook/Office365 via Graph API, store credentials in database:

```python
from servbot.data import upsert_graph_account

upsert_graph_account(
    email="your-email@outlook.com",
    refresh_token="your-refresh-token",
    client_id="your-client-id"
)
```

### Proxy Configuration (NEW!)

Create `config/proxies.json` for proxy providers:

```json
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
      "proxy_type": "residential",
      "ip_version": "ipv4"
    }
  },
  {
    "name": "mooproxy-us",
    "type": "mooproxy",
    "price_per_gb": 5.0,
    "concurrency_limit": 20,
    "options": {
      "host": "us.mooproxy.net",
      "port": "55688",
      "username": "your-username",
      "password": "your-password",
      "country": "US",
      "proxy_type": "residential",
      "ip_version": "ipv4"
    }
  }
]
```

**Environment Variables for Secrets:**
Use `"env:VAR_NAME"` syntax to reference environment variables for sensitive data.

**See [docs/PROXIES.md](docs/PROXIES.md) for complete proxy documentation.**

### Browser Automation Setup

Install Playwright browsers:

```bash
playwright install chromium
```

Or use the built-in installer:

```python
from servbot.automation.engine import mcp_cursor_playwright_browser_install
# Browser will be installed automatically on first use
```

## Service Catalog

Servbot includes pre-configured patterns for 100+ popular services:

- **Identity**: Google, Microsoft, Apple, GitHub, GitLab
- **Social**: Facebook, Instagram, WhatsApp, Twitter/X, TikTok
- **Finance**: PayPal, Stripe, Coinbase, Robinhood
- **Cloud**: AWS, Azure, Google Cloud, Cloudflare
- **Gaming**: Steam, Epic Games, PlayStation, Xbox
- **Productivity**: Notion, Slack, Zoom, Trello
- And many more...

## Database

Servbot automatically maintains a SQLite database (`data/servbot.db`) storing:

- **accounts**: Provisioned email accounts (with Graph API credentials)
- **messages**: Fetched email messages
- **verifications**: Extracted verification codes/links
- **graph_accounts**: Legacy Microsoft Graph credentials
- **registrations** (NEW!): Browser automation registration results and artifacts
- **flashmail_cards** (NEW!): Flashmail API card metadata (secrets stored in keyring)

## Error Handling

All functions handle errors gracefully:

- Network failures return empty results or None
- Invalid credentials raise clear exceptions
- Database errors don't crash the application
- AI fallback silently fails if unavailable

## Testing

Run the integration test:

```bash
python integration_test.py
```

Run unit tests:

```bash
pytest tests/
```

## Best Practices

### Email Operations
1. **Environment Variables**: Store credentials in environment variables or secure keyring
2. **Rate Limiting**: Respect email server rate limits (use `limit` parameter)
3. **Mark As Read**: Use `mark_seen=True` to avoid reprocessing
4. **Database**: Regularly backup `data/servbot.db`
5. **AI Usage**: AI fallback has API costs; disable with `use_ai=False` if needed

### Browser Automation
1. **Headless First**: Start with headless mode; use headed mode only for debugging
2. **Traffic Profiles**: Use `"minimal"` or `"ultra"` to reduce bandwidth costs when using proxies
3. **Network Metering**: Enable `measure_network=True` to track actual bandwidth consumption
4. **Stealth Features**: BrowserBot includes anti-detection measures (webdriver masking, realistic headers)
5. **Debug Artifacts**: Screenshots with red outlines are saved to `data/screenshots/run-*` directories
6. **Timeout Management**: Default step timeout is 10s; adjust `timeout_seconds` for slow networks
7. **Session Persistence**: Reuse `user_data_dir` to maintain login state across runs

### Proxy Management
1. **Cost Tracking**: Enable metering with `ProxyManager(configs, enable_metering=True)`
2. **Concurrency Limits**: Set `concurrency_limit` in config to prevent overloading providers
3. **Auto-Selection**: Omit `name` parameter in `acquire()` to auto-select cheapest provider
4. **Regional Targeting**: Specify `region` parameter for location-specific proxies
5. **Testing**: Use `ProxyTester.test_batch()` to validate proxies before production use
6. **Environment Secrets**: Use `"env:VAR_NAME"` syntax in config for sensitive credentials
7. **Release Proxies**: Always call `pm.release()` to properly track usage and free concurrency slots

### Network Optimization
1. **Profile Selection**:
   - **off**: Normal browsing (default)
   - **minimal**: ~60-80% bandwidth reduction (blocks images, fonts, media)
   - **ultra**: ~80-90% bandwidth reduction (also blocks CSS)
2. **Third-Party Blocking**: Use `block_third_party=True` with careful `allowed_domains` configuration
3. **Measure First**: Run with `measure_network=True` to understand baseline usage before optimization
4. **Trade-offs**: Ultra mode may break some sites; test thoroughly before production use

## Migration from v1.x

The v2.0 refactor maintains backward compatibility for core functions:

```python
# Old (still works)
from servbot.emailbot import fetch_verification_codes

# New (recommended)
from servbot import fetch_verification_codes
```

Internal imports have changed:
- `servbot.code_parser` �?`servbot.parsers`
- `servbot.imap_client` �?`servbot.clients`
- `servbot.db` �?`servbot.data`

## Contributing

Servbot follows Google Python Style Guide:

- Comprehensive docstrings for all public functions
- Type hints for all parameters and returns
- Clear separation of concerns
- Modular architecture for easy extension

## License

[Specify your license here]

## Additional Documentation

- **[CLI Guide](docs/CLI_GUIDE.md)**: Complete interactive CLI documentation
- **[Quickstart Guide](docs/QUICKSTART.md)**: Get started quickly with common use cases
- **[Proxy System](docs/PROXIES.md)**: Comprehensive proxy configuration and usage guide
- **[Browser Automation](docs/BROWSER_AUTOMATION.md)**: Detailed browser automation documentation (NEW!)
- **[Network Metering](docs/NETWORK_METERING.md)**: Traffic measurement and optimization guide (NEW!)

## Support

For issues and questions, please [open an issue on GitHub].

