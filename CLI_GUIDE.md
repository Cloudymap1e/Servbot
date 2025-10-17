# Servbot Interactive CLI Guide

## Overview

Servbot now includes an interactive command-line interface (CLI) that allows you to manage email accounts and retrieve verification codes through an easy-to-use command prompt.

## Starting the CLI

There are multiple ways to start the interactive CLI:

### Method 1: Using Python Module
```bash
python -m servbot
```

### Method 2: Direct Execution
```bash
python servbot/main.py
```

### Method 3: Using Startup Scripts
**Windows:**
```cmd
run.bat
```

**Linux/Mac:**
```bash
./run.sh
```

## Available Commands

### Account Management

#### `accounts` (aliases: `acc`, `list`)
List all email accounts stored in the database.

```
servbot> accounts
```

Optional: Filter by source
```
servbot> accounts flashmail
```

#### `provision [type]` (aliases: `prov`, `new`)
Provision a new email account from Flashmail API.

```
servbot> provision
servbot> provision outlook
servbot> provision hotmail
```

**Requirements:**
- Flashmail API key configured in `data/ai.api`
- Sufficient API credits

#### `add <email> <password> [imap_server]`
Manually add an email account to the database.

```
servbot> add user@example.com mypassword
servbot> add user@gmail.com mypassword imap.gmail.com
```

### Verification Code Checking

#### `check <email>` (aliases: `verify`)
Check verification codes for a specific email account.

```
servbot> check test@outlook.com
```

This command:
1. First checks the database for recent verification codes
2. If none found, fetches fresh emails from the inbox
3. Extracts and displays all verification codes/links

#### `check-all`
Check verification codes for ALL accounts in the database.

```
servbot> check-all
```

Useful for getting a quick overview of all verification codes across all accounts.

#### `inbox <email>` (aliases: `fetch`, `mail`)
Fetch the latest emails from an account's inbox and extract verification codes.

```
servbot> inbox test@outlook.com
```

### Flashmail API

#### `balance` (aliases: `bal`, `credits`)
Check your Flashmail API credit balance.

```
servbot> balance
```

**Requirements:**
- Flashmail API key configured in `data/ai.api`

#### `inventory` (aliases: `inv`, `stock`)
Check available Flashmail account inventory.

```
servbot> inventory
```

Shows how many Outlook and Hotmail accounts are currently available for provisioning.

### Database

#### `database` (aliases: `db`)
Show complete database contents including accounts, messages, and verification codes.

```
servbot> database
```

Displays:
- Total counts of accounts, messages, and verifications
- Recent verification codes (last 10)

### General Commands

#### `help` (aliases: `h`, `?`)
Display help message with all available commands.

```
servbot> help
```

#### `exit` (aliases: `quit`, `q`)
Exit the interactive CLI.

```
servbot> exit
```

## Usage Examples

### Example 1: Provision and Check New Account

```
servbot> provision outlook
Provisioning outlook account from Flashmail...
======================================================================
ACCOUNT PROVISIONED SUCCESSFULLY
======================================================================

Email:    test123@outlook.com
Password: SecurePass123
Type:     outlook
IMAP:     outlook.office365.com

Account saved to database.
======================================================================

servbot> check test123@outlook.com
Checking verification codes for test123@outlook.com...
No verification codes found for test123@outlook.com.

Trying to fetch new codes from inbox...
```

### Example 2: Check Existing Account

```
servbot> accounts
======================================================================
EMAIL ACCOUNTS (3 total)
======================================================================

1. user1@outlook.com
   Type: outlook
   Source: flashmail
   Created: 2024-01-15 10:30:00

2. user2@hotmail.com
   Type: hotmail
   Source: flashmail
   Created: 2024-01-14 09:15:00

3. manual@gmail.com
   Type: other
   Source: manual
   Created: 2024-01-10 14:20:00
======================================================================

servbot> check user1@outlook.com
Checking verification codes for user1@outlook.com...
======================================================================
VERIFICATION CODES FOR user1@outlook.com
======================================================================

1. GitHub
   Value: 123456
   Type:  Code
   Date:  2024-01-15 11:00:00

2. Google
   Value: https://accounts.google.com/verify?token=abc123
   Type:  Link
   Date:  2024-01-15 10:45:00

======================================================================
```

### Example 3: Check All Accounts

```
servbot> check-all
Checking verification codes for 3 account(s)...

======================================================================
Checking: user1@outlook.com
======================================================================
  • GitHub: 123456 (Code)
  • Google: https://accounts.google.com/verify?token=abc123 (Link)

======================================================================
Checking: user2@hotmail.com
======================================================================
  No verification codes found.

======================================================================
Checking: manual@gmail.com
======================================================================
  • Discord: 789012 (Code)

======================================================================
```

### Example 4: Check Balance and Inventory

```
servbot> balance
Flashmail API Balance: 45 credits

servbot> inventory
======================================================================
FLASHMAIL INVENTORY
======================================================================
Outlook accounts: 1234
Hotmail accounts: 567
======================================================================
```

## Configuration

### Flashmail API Key

To use Flashmail features, add your API key to `data/ai.api`:

```
FLASHMAIL_CARD = "your_api_key_here"
```

### Supported Email Providers

The CLI automatically detects and configures:
- **Outlook/Hotmail/Live**: `outlook.office365.com`
- **Gmail**: `imap.gmail.com`
- Custom IMAP servers can be specified manually

### Microsoft Graph API

For accounts with Graph API credentials, the CLI will automatically use Graph API instead of IMAP for better performance and reliability.

Graph credentials are stored in the database when provisioning from Flashmail or can be configured manually.

## Tips and Tricks

1. **Tab Completion**: While not built-in, you can use your shell's history (↑/↓ arrows) to recall previous commands.

2. **Quick Check**: Use `check-all` for a quick overview of all accounts.

3. **Database First**: The CLI always checks the database first before fetching from servers, making it fast for recently-checked codes.

4. **Automatic Saving**: All fetched verification codes are automatically saved to the database for future reference.

5. **Error Recovery**: If a command fails, the CLI continues running. Just try again or use a different command.

## Troubleshooting

### "Flashmail API key not configured"
Add your API key to `data/ai.api` as shown in the Configuration section.

### "Account not found in database"
Use `accounts` to list available accounts, or `add` to add a new account manually.

### "Error fetching inbox"
Check:
- Account credentials are correct
- IMAP server is correct for the email provider
- Network connection is working
- Email provider allows IMAP access

### "No verification codes found"
This can happen if:
- No verification emails have been received
- Emails are older than the default time window
- The parsing didn't detect the codes (consider checking raw emails)

## Advanced Usage

### Using with Python Scripts

You can also import and use the CLI programmatically:

```python
from servbot.cli import ServbotCLI

cli = ServbotCLI()
cli.cmd_accounts([])  # List accounts
cli.cmd_check(['test@outlook.com'])  # Check specific account
```

### Database Access

The CLI uses the same SQLite database as the Python API, so you can use both interchangeably:

```python
from servbot import list_database, get_account_verifications

# Use API functions
db = list_database()
codes = get_account_verifications('test@outlook.com')
```

Then check results in CLI:
```
servbot> database
```

## Future Enhancements

Planned features:
- Auto-complete for commands and email addresses
- Colored output for better readability
- Export commands (CSV, JSON)
- Search/filter verification codes by service
- Bulk operations
- Real-time monitoring mode

## Support

For issues or questions:
1. Check the main README.md
2. Review the QUICKSTART.md guide
3. Examine the code in `servbot/cli.py`

