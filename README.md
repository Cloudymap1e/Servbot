# Servbot - Email Verification Code Extraction System

A comprehensive, production-ready email automation tool for fetching and extracting verification codes from emails.

## Features

- **Multi-Protocol Support**: IMAP and Microsoft Graph API
- **Intelligent Parsing**: Regex patterns with AI fallback (Cerebras)
- **100+ Services**: Pre-configured patterns for popular services
- **Account Provisioning**: Integration with Flashmail/Shanyouxiang API
- **Database Persistence**: SQLite storage for messages and verifications
- **Clean Architecture**: Modular, well-documented, Google Style compliant

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

- **accounts**: Provisioned email accounts
- **messages**: Fetched email messages
- **verifications**: Extracted verification codes/links
- **graph_accounts**: Microsoft Graph credentials

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

1. **Environment Variables**: Store credentials in environment variables
2. **Rate Limiting**: Respect email server rate limits (use `limit` parameter)
3. **Mark As Read**: Use `mark_seen=True` to avoid reprocessing
4. **Database**: Regularly backup `data/servbot.db`
5. **AI Usage**: AI fallback has API costs; disable with `use_ai=False` if needed

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

## Support

For issues and questions, please [open an issue on GitHub].

