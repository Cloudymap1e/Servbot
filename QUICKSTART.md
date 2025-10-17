# Servbot Quick Start Guide

Get up and running with Servbot in minutes!

## Installation

```bash
pip install -r requirements.txt
```

## Basic Usage

### 1. Fetch Verification Codes from Existing Email

```python
from servbot import fetch_verification_codes

# Fetch all verification codes from IMAP
verifications = fetch_verification_codes(
    imap_server="imap.gmail.com",
    username="your-email@gmail.com",
    password="your-password"
)

for v in verifications:
    print(v.as_pair())  # Output: <Google, 123456>
```

### 2. Wait for Specific Service Verification

```python
from servbot import get_verification_for_service

# Wait for GitHub verification (polls for 60 seconds)
code = get_verification_for_service(
    target_service="GitHub",
    imap_server="imap.gmail.com",
    username="your-email@gmail.com",
    password="your-password",
    timeout_seconds=60
)

if code:
    print(f"GitHub verification code: {code}")
```

### 3. Provision Fresh Email Account

If you have a Flashmail API key, you can automatically provision new accounts:

```python
from servbot import provision_flashmail_account

result = provision_flashmail_account(
    card="your-flashmail-api-key",
    target_service="Discord",
    timeout_seconds=120
)

if result:
    print(f"Email: {result['email']}")
    print(f"Password: {result['password']}")
    print(f"Verification: {result['value']}")
```

## Configuration

### Optional: AI Parsing

Create `data/ai.api` with your Cerebras API key for intelligent fallback:

```
CEREBRAS_KEY = "your-cerebras-api-key"
```

### Optional: Flashmail Integration

Add your Flashmail API key to `data/ai.api`:

```
FLASHMAIL_CARD = "your-flashmail-api-key"
```

### Optional: Microsoft Graph API

For better Outlook/Office365 support, configure Graph API credentials:

```python
from servbot.data import upsert_graph_account

upsert_graph_account(
    email="your-email@outlook.com",
    refresh_token="your-refresh-token",
    client_id="your-client-id"
)
```

## Provisioning New Accounts

Use the built-in provisioning script:

```bash
# Provision 2 new Outlook accounts
python provision_new_accounts.py -n 2

# Check Flashmail balance
python provision_new_accounts.py --balance

# Check available inventory
python provision_new_accounts.py --inventory
```

Provisioned accounts are automatically saved to the database at `data/servbot.db`.

## Database Management

All accounts, messages, and verifications are stored in SQLite:

```python
from servbot.data import get_accounts, get_latest_verifications

# View stored accounts
accounts = get_accounts()
for acc in accounts:
    print(f"{acc['email']} - {acc['source']}")

# View recent verifications
verifications = get_latest_verifications("your-email@outlook.com", limit=10)
for v in verifications:
    print(f"{v['service']}: {v['value']}")
```

## Testing

Run the integration test to verify everything works:

```bash
python integration_test.py
```

## Common Use Cases

### 1. Discord Account Verification

```python
from servbot import provision_flashmail_account

result = provision_flashmail_account(
    card="your-api-key",
    target_service="Discord"
)
# Use result['email'] and result['value'] for Discord signup
```

### 2. GitHub Email Verification

```python
from servbot import get_verification_for_service

code = get_verification_for_service(
    target_service="GitHub",
    imap_server="outlook.office365.com",
    username="your@outlook.com",
    password="your-password"
)
```

### 3. Bulk Verification Code Extraction

```python
from servbot import fetch_verification_codes

verifications = fetch_verification_codes(
    prefer_graph=True,  # Use Graph API if configured
    limit=100,
    use_ai=False  # Disable AI to save costs
)

for v in verifications:
    print(f"{v.service}: {v.code}")
```

## Troubleshooting

### IMAP Connection Issues

- Ensure your email provider allows IMAP access
- Check if you need an app-specific password (Gmail, Outlook)
- Verify server address and port (usually 993 for SSL)

### No Verification Codes Found

- Check `unseen_only` parameter (may need `False` for testing)
- Verify the service name matches (use `servbot.data.services.SERVICES` to see all)
- Enable AI fallback with `use_ai=True`

### Flashmail Issues

- Check your balance: `python provision_new_accounts.py --balance`
- Check inventory: `python provision_new_accounts.py --inventory`
- Verify your API key in `data/ai.api`

## Next Steps

- Read the full [README.md](README.md) for detailed API reference
- Check `data/services.py` for the list of 100+ supported services
- Explore the `clients/`, `parsers/`, and `core/` modules for advanced usage

## Support

For issues and questions, please open an issue on GitHub or consult the README.md.
