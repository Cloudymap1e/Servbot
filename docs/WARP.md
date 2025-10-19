# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Servbot is a Python-based email verification code extraction system that supports multiple email protocols (IMAP, Microsoft Graph API) and integrates with Flashmail for account provisioning. The system uses regex patterns with AI fallback (Cerebras) to extract verification codes from 100+ services.

## Essential Commands

### Installation
```pwsh
pip install -r requirements.txt
```

### Running the Application

**Interactive CLI (primary interface):**
```pwsh
# Windows
python -m servbot
# or
.\run.bat
```

```bash
# Unix/Linux/Mac
python -m servbot
# or
./run.sh
```

**Python API (programmatic usage):**
```python
from servbot import fetch_verification_codes
```

### Testing

**Run all tests:**
```pwsh
pytest tests/
```

**Run integration test:**
```pwsh
python integration_test.py
```

**Run specific test:**
```pwsh
pytest tests/test_parsers.py
pytest tests/test_verification.py -v
```

### Account Provisioning

**Provision Flashmail accounts:**
```pwsh
python provision_new_accounts.py -n 2
```

**Check Flashmail balance:**
```pwsh
python provision_new_accounts.py --balance
```

## Architecture Overview

### Multi-Layered Design

The codebase follows a clean architecture pattern with clear separation of concerns:

```
API Layer (api.py) → Core Logic (core/) → Clients (clients/) → External Services
                   ↓
              Parsers (parsers/) → AI Fallback
                   ↓
              Data Layer (data/) → SQLite DB
```

**Flow for Verification Code Extraction:**
1. `api.py` exposes high-level functions (e.g., `fetch_verification_codes`)
2. `core/verification.py` orchestrates the fetching and processing logic
3. `clients/` implement email protocol handlers (IMAP, Graph API, Flashmail)
4. `parsers/` extract codes and identify services using regex and AI
5. `data/database.py` persists messages and verifications to SQLite

### Key Architectural Patterns

**Client Pattern (clients/)**
- `base.py` defines the `EmailClient` abstract interface
- `imap.py` implements IMAP protocol
- `graph.py` implements Microsoft Graph API
- `flashmail.py` handles account provisioning
- All clients return `EmailMessage` objects

**Parser Pipeline (parsers/)**
- `code_parser.py`: Extracts codes using regex patterns
- `service_parser.py`: Identifies service from email metadata
- `email_parser.py`: Parses email structure
- `ai_parser.py`: AI fallback when regex fails (Cerebras API)

**Data Models (core/models.py)**
- `Verification`: Extracted code/link with metadata
- `EmailAccount`: Email account configuration
- `EmailMessage`: Fetched email with parsed content

**Protocol Selection Logic**
The system automatically selects the best available protocol:
1. If `prefer_graph=True` (default), tries Microsoft Graph API first
   - Searches for credentials in `accounts` table by matching email
   - Falls back to global config if no account-specific credentials
2. Falls back to IMAP if Graph credentials unavailable or Graph API fails
3. Microsoft Graph API is faster and more reliable for Outlook/Hotmail accounts
4. Flashmail accounts support both protocols:
   - Graph API using shared OAuth credentials (preferred)
   - IMAP via Flashmail proxy: `imap.shanyouxiang.com`

**FIXED BUGS:**
- ✅ GraphClient now accepts `mailbox` parameter and populates EmailMessage.mailbox
- ✅ Flashmail accounts now use Graph API by default (was forcing IMAP)
- ✅ Database upsert allows clearing credentials with NULL (removed COALESCE blocker)
- ✅ Credential storage consolidated in `accounts` table (graph_accounts deprecated)

### Configuration & Credentials

**Configuration file: `data/ai.api`**
```
CEREBRAS_KEY = "your-cerebras-api-key"
FLASHMAIL_CARD = "your-flashmail-api-key"
```

**Graph API credentials:**
Stored in SQLite database (`data/servbot.db` → `graph_accounts` table). Flashmail-provisioned accounts automatically include Graph credentials.

**Database schema:**
- `accounts`: Email account credentials and metadata
- `messages`: Fetched email messages
- `verifications`: Extracted codes/links
- `graph_accounts`: Microsoft Graph API credentials

## Development Guidelines

### Adding New Service Patterns

Edit `data/services.py` to add regex patterns for new services:
```python
SERVICES = [
    ServiceInfo(
        name="ServiceName",
        from_patterns=[r"@service\.com", r"noreply@service\.io"],
        subject_patterns=[r"verification", r"code"],
        body_patterns=[r"\\b\\d{6}\\b"],
    ),
]
```

### Testing Verification Extraction

Use the integration test to verify parsing:
```python
# integration_test.py demonstrates the complete flow
python integration_test.py
```

### CLI Commands Reference

The CLI (`cli.py`) provides these command categories:
- Account management: `accounts`, `provision`, `add`
- Verification checking: `check`, `check-all`, `inbox`
- Flashmail API: `balance`, `inventory`
- Database: `database`

## Important Implementation Notes

### Microsoft Graph API vs IMAP
- **Microsoft Graph API** (https://graph.microsoft.com):
  - Uses OAuth2: requires `refresh_token` and `client_id` to obtain access tokens
  - Preferred for Outlook/Hotmail/Office 365 accounts (faster, more reliable, modern auth)
  - Flashmail accounts include Graph credentials by default (shared credentials)
  - Messages fetched via Graph must have `mailbox` field set for proper tracking
- **IMAP**:
  - Traditional protocol: requires server address, username, password
  - Fallback when Graph credentials unavailable
  - Flashmail accounts can use special IMAP proxy: `imap.shanyouxiang.com`

### AI Fallback Behavior
- AI parsing (Cerebras) is used only when regex patterns fail
- Controlled via `use_ai` parameter (default: True)
- AI calls have API costs; can be disabled if needed
- API key must be in `data/ai.api`

### Database Persistence
- All fetched messages are saved to avoid reprocessing
- **CRITICAL**: Messages fetched via Graph API MUST have `mailbox` field populated (was previously empty)
- Verifications are queried by `mailbox` field - empty mailbox = verifications not retrievable
- Verifications are deduplicated by service and value
- CLI always checks database first before fetching from servers
- Database operations fail gracefully without crashing

### Credential Storage and Updates
- Single source of truth: `accounts` table (includes password, refresh_token, client_id)
- Legacy `graph_accounts` table is deprecated (auto-migrated on startup)
- `upsert_account()` has two modes:
  - `update_only_if_provided=False` (default): Direct updates, allows clearing fields with NULL
  - `update_only_if_provided=True` (legacy): Only updates non-empty values (COALESCE behavior)
- When updating credentials, use the default mode to allow token rotation/clearing

### Polling Pattern
The `get_verification_for_service()` function implements polling:
- Default timeout: 60 seconds
- Default interval: 5 seconds
- Useful for waiting for specific verification emails

## File Path Patterns

- Configuration: `data/ai.api`, `config.py`, `constants.py`
- Entry points: `__main__.py`, `main.py`, `api.py`
- Tests: `tests/test_*.py`
- Core business logic: `core/verification.py`
- Public API: `__init__.py` exports all public functions

## Common Development Scenarios

### Adding a New Email Client
1. Create `clients/new_client.py`
2. Inherit from `EmailClient` base class
3. Implement `fetch_messages()` and `mark_as_read()`
4. Return `EmailMessage` objects
5. Export from `clients/__init__.py`

### Debugging Verification Extraction
1. Check regex patterns in `data/services.py`
2. Review parser logic in `parsers/code_parser.py`
3. Enable AI fallback to test alternative extraction
4. Use `integration_test.py` with sample emails

### Working with the Database
```python
from servbot.data import get_accounts, get_latest_verifications, ensure_db

ensure_db()  # Initialize database
accounts = get_accounts()  # List all accounts
verifications = get_latest_verifications("email@example.com", limit=10)
```

## Environment

- **Platform**: Python 3.12+ (uses dataclasses, type hints)
- **Database**: SQLite (automatic initialization)
- **Dependencies**: imapclient, requests, cerebras-cloud-sdk
- **OS Support**: Windows (PowerShell), Unix/Linux (Bash)
