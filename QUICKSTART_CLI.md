# Quick Start Guide - Servbot CLI

## 1. Installation

Make sure you have Python installed, then install requirements:

```bash
cd servbot
pip install -r requirements.txt
```

## 2. Start the CLI

```bash
python -m servbot
```

You should see:

```
======================================================================
  SERVBOT - Email Verification Code Extraction System
======================================================================

Type 'help' for available commands or 'exit' to quit.

servbot>
```

## 3. First Steps

### Step 1: Check What's in Your Database

```
servbot> database
```

This shows all accounts, messages, and verification codes currently stored.

### Step 2: List Your Accounts

```
servbot> accounts
```

This lists all email accounts in the database.

### Step 3: Add an Account Manually (Optional)

If you have an existing email account:

```
servbot> add myemail@gmail.com mypassword imap.gmail.com
```

### Step 4: Provision a New Account from Flashmail (Optional)

If you have a Flashmail API key configured:

```
servbot> provision outlook
```

This provisions a new Outlook account.

### Step 5: Check for Verification Codes

For a specific account:

```
servbot> check myemail@outlook.com
```

For all accounts:

```
servbot> check-all
```

### Step 6: Fetch Fresh Emails

```
servbot> inbox myemail@outlook.com
```

This fetches the latest emails and extracts verification codes.

## Common Workflows

### Workflow 1: Using Existing Email Account

1. Add your email:
   ```
   servbot> add myemail@gmail.com mypassword imap.gmail.com
   ```

2. Fetch verification codes:
   ```
   servbot> inbox myemail@gmail.com
   ```

3. View the codes:
   ```
   servbot> check myemail@gmail.com
   ```

### Workflow 2: Using Flashmail

1. Check your balance:
   ```
   servbot> balance
   ```

2. Check inventory:
   ```
   servbot> inventory
   ```

3. Provision a new account:
   ```
   servbot> provision outlook
   ```

4. Use the provisioned account (it's automatically added to database):
   ```
   servbot> accounts
   servbot> check <new-email-address>
   ```

### Workflow 3: Monitor All Accounts

1. List all accounts:
   ```
   servbot> accounts
   ```

2. Check all at once:
   ```
   servbot> check-all
   ```

3. View complete database:
   ```
   servbot> database
   ```

## Configuration

### Setup Flashmail API Key

Create or edit `data/ai.api`:

```
FLASHMAIL_CARD = "your_api_key_here"
```

### Setup Cerebras AI (Optional)

Add to `data/ai.api`:

```
CEREBRAS_KEY = "your_cerebras_key_here"
```

## Tips

1. **Command Shortcuts**: Most commands have short aliases:
   - `accounts` → `acc` or `list`
   - `provision` → `prov` or `new`
   - `balance` → `bal` or `credits`
   - `inventory` → `inv` or `stock`

2. **History**: Use ↑/↓ arrow keys to recall previous commands

3. **Exit**: Type `exit`, `quit`, or `q` to exit

4. **Help**: Type `help` anytime to see all commands

## Troubleshooting

### "Flashmail API key not configured"

Create `data/ai.api` and add:
```
FLASHMAIL_CARD = "your_key"
```

### "Account not found in database"

Use `accounts` to see what's available, or `add` to add an account.

### "Error fetching inbox"

Check:
- Email and password are correct
- IMAP server is correct
- Network connection is working
- Email provider allows IMAP

### "No verification codes found"

This is normal if:
- No verification emails have been received yet
- All emails are too old
- The account is empty

## Next Steps

Once you're comfortable with the CLI:

1. Read the full [CLI_GUIDE.md](CLI_GUIDE.md) for all features
2. Check out the Python API in [README.md](README.md)
3. Review [QUICKSTART.md](QUICKSTART.md) for programmatic usage
4. Explore [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details

## Example Session

Here's a complete example session:

```
servbot> help
[Shows help menu]

servbot> balance
Flashmail API Balance: 50 credits

servbot> inventory
======================================================================
FLASHMAIL INVENTORY
======================================================================
Outlook accounts: 1234
Hotmail accounts: 567
======================================================================

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

servbot> accounts
======================================================================
EMAIL ACCOUNTS (1 total)
======================================================================

1. test123@outlook.com
   Type: outlook
   Source: flashmail
   Created: 2024-01-15 10:30:00
   Graph API: ✓ Configured
======================================================================

servbot> check test123@outlook.com
Checking verification codes for test123@outlook.com...
No verification codes found for test123@outlook.com.

Trying to fetch new codes from inbox...
Connecting to outlook.office365.com...
No verification codes found in recent emails.

servbot> database
======================================================================
DATABASE CONTENTS
======================================================================

Total Accounts:       1
Total Messages:       0
Total Verifications:  0
Total Graph Accounts: 0
======================================================================

servbot> exit
Goodbye!
```

## Need Help?

- Type `help` in the CLI for command list
- Read [CLI_GUIDE.md](CLI_GUIDE.md) for detailed documentation
- Check [README.md](README.md) for architecture and API reference

