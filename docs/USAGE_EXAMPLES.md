# Servbot CLI - Usage Examples

## Starting the CLI

### Option 1: Python Module (Recommended)
```bash
cd d:\servbot
python -m servbot
```

### Option 2: Direct Execution
```bash
cd d:\servbot\servbot
python main.py
```

### Option 3: Startup Script
```bash
# Windows
cd d:\servbot\servbot
run.bat

# Linux/Mac
cd d:\servbot\servbot
./run.sh
```

## Example 1: Basic Workflow

```
servbot> help
[Shows all commands]

servbot> accounts
No accounts found in database.

servbot> add myemail@gmail.com mypassword imap.gmail.com
Account added: myemail@gmail.com

servbot> accounts
======================================================================
EMAIL ACCOUNTS (1 total)
======================================================================

1. myemail@gmail.com
   Type: other
   Source: manual
   IMAP Server: imap.gmail.com
   Created: 2024-10-17 12:30:00
======================================================================

servbot> check myemail@gmail.com
Checking verification codes for myemail@gmail.com...
No verification codes found for myemail@gmail.com.

Trying to fetch new codes from inbox...
Connecting to imap.gmail.com...
[Fetches emails and extracts codes]

servbot> exit
Goodbye!
```

## Example 2: Using Flashmail

```
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

Email:    abc123@outlook.com
Password: RandomPass456
Type:     outlook
IMAP:     outlook.office365.com

Account saved to database.
======================================================================

servbot> check abc123@outlook.com
Checking verification codes for abc123@outlook.com...
No verification codes found for abc123@outlook.com.

servbot> inbox abc123@outlook.com
Fetching inbox for abc123@outlook.com...
Connecting to outlook.office365.com...
No verification codes found in recent emails.
```

## Example 3: Monitoring Multiple Accounts

```
servbot> accounts
======================================================================
EMAIL ACCOUNTS (3 total)
======================================================================

1. user1@outlook.com
   Type: outlook
   Source: flashmail
   Created: 2024-10-17 10:00:00
   Graph API: ✓ Configured

2. user2@hotmail.com
   Type: hotmail
   Source: flashmail
   Created: 2024-10-17 10:05:00
   Graph API: ✓ Configured

3. user3@gmail.com
   Type: other
   Source: manual
   IMAP Server: imap.gmail.com
   Created: 2024-10-17 10:10:00
======================================================================

servbot> check-all
Checking verification codes for 3 account(s)...

======================================================================
Checking: user1@outlook.com
======================================================================
  • GitHub: 123456 (Code)
  • Google: https://accounts.google.com/verify?token=xyz (Link)

======================================================================
Checking: user2@hotmail.com
======================================================================
  • Discord: 789012 (Code)

======================================================================
Checking: user3@gmail.com
======================================================================
  No verification codes found.

======================================================================
```

## Example 4: Database Inspection

```
servbot> database
======================================================================
DATABASE CONTENTS
======================================================================

Total Accounts:       3
Total Messages:       15
Total Verifications:  8
Total Graph Accounts: 0

----------------------------------------------------------------------
RECENT VERIFICATIONS (Last 10)
----------------------------------------------------------------------

• GitHub
  Value:   123456
  Type:    Code
  Mailbox: user1@outlook.com
  Date:    2024-10-17 11:30:00

• Google
  Value:   https://accounts.google.com/verify?token=xyz
  Type:    Link
  Mailbox: user1@outlook.com
  Date:    2024-10-17 11:25:00

• Discord
  Value:   789012
  Type:    Code
  Mailbox: user2@hotmail.com
  Date:    2024-10-17 11:20:00

[... more entries ...]

======================================================================
```

## Example 5: Command Aliases

All of these are equivalent:

```
# List accounts
servbot> accounts
servbot> acc
servbot> list

# Provision account
servbot> provision outlook
servbot> prov outlook
servbot> new outlook

# Check balance
servbot> balance
servbot> bal
servbot> credits

# Check inventory
servbot> inventory
servbot> inv
servbot> stock

# Exit program
servbot> exit
servbot> quit
servbot> q
```

## Example 6: Real-World Automation Flow

```
# 1. Check balance
servbot> balance
Flashmail API Balance: 100 credits

# 2. Provision multiple accounts
servbot> provision outlook
[Account 1 created: acc1@outlook.com]

servbot> provision outlook
[Account 2 created: acc2@outlook.com]

servbot> provision hotmail
[Account 3 created: acc3@hotmail.com]

# 3. View all accounts
servbot> accounts
[Shows 3 accounts]

# 4. Use accounts for verification
# (At this point, you'd use these accounts on various websites)

# 5. Check all accounts for codes
servbot> check-all
[Shows verification codes from all accounts]

# 6. Check specific account
servbot> check acc1@outlook.com
======================================================================
VERIFICATION CODES FOR acc1@outlook.com
======================================================================

1. Twitter
   Value: 654321
   Type:  Code
   Date:  2024-10-17 12:45:00

2. Facebook
   Value: https://www.facebook.com/confirmemail.php?c=abc123
   Type:  Link
   Date:  2024-10-17 12:40:00
======================================================================

# 7. Fetch fresh emails
servbot> inbox acc1@outlook.com
Fetching inbox for acc1@outlook.com...
Connecting to outlook.office365.com...

======================================================================
VERIFICATION CODES FOUND (2 total)
======================================================================

1. Instagram
   Value:   987654
   Type:    Code
   Subject: Your Instagram verification code
   From:    no-reply@mail.instagram.com
   Date:    2024-10-17 12:50:00

2. LinkedIn
   Value:   456789
   Type:    Code
   Subject: LinkedIn verification code
   From:    security-noreply@linkedin.com
   Date:    2024-10-17 12:48:00

======================================================================
Codes saved to database.

# 8. View complete database
servbot> database
[Shows all accounts, messages, and verifications]

# 9. Check balance again
servbot> balance
Flashmail API Balance: 97 credits

# 10. Exit
servbot> exit
Goodbye!
```

## Error Handling Examples

### Missing Configuration
```
servbot> balance
Error: Flashmail API key not configured!
Please add FLASHMAIL_CARD to data/ai.api
Format: FLASHMAIL_CARD = "your_api_key"
```

### Unknown Command
```
servbot> unknowncmd
Unknown command: unknowncmd
Type 'help' for available commands.
```

### Invalid Usage
```
servbot> check
Usage: check <email>
```

### Network Error
```
servbot> inbox user@gmail.com
Fetching inbox for user@gmail.com...
Connecting to imap.gmail.com...
Error fetching inbox: [Errno 11001] getaddrinfo failed
```

## Interactive Features

### Keyboard Interrupts
```
servbot> ^C

Use 'exit' or 'quit' to exit.

servbot>
```

### Command History
Use ↑ and ↓ arrow keys to navigate through previous commands (shell feature).

## Integration with Python API

You can mix CLI and Python API usage:

### Use CLI to add accounts
```
servbot> add test@gmail.com password imap.gmail.com
servbot> exit
```

### Use Python API to check them
```python
from servbot import get_account_verifications

codes = get_account_verifications('test@gmail.com')
for code in codes:
    print(code)
```

### Or vice versa

Use Python API to provision:
```python
from servbot import provision_flashmail_account

result = provision_flashmail_account(
    card="your_key",
    target_service="GitHub"
)
```

Use CLI to check:
```
servbot> accounts
[Shows the provisioned account]

servbot> check <provisioned-email>
[Shows GitHub verification code]
```

## Tips for Power Users

1. **Quick Check Workflow**
   ```
   servbot> check-all
   ```
   Get overview of all accounts instantly.

2. **Database First**
   CLI always checks database first (fast), then fetches if needed.

3. **Command Chaining**
   Execute related commands in sequence:
   ```
   servbot> provision outlook
   servbot> accounts
   servbot> check <new-email>
   ```

4. **Monitoring Pattern**
   ```
   servbot> check-all
   [Wait for new verification emails]
   servbot> check-all
   [See new codes that arrived]
   ```

5. **Bulk Account Management**
   ```
   servbot> provision outlook
   servbot> provision outlook
   servbot> provision hotmail
   servbot> accounts
   servbot> check-all
   ```

## Summary

The CLI provides:
- ✓ Easy account management
- ✓ Quick verification checking
- ✓ Database inspection
- ✓ Flashmail integration
- ✓ No programming required
- ✓ Interactive and intuitive
- ✓ Full feature access

Perfect for both casual users and power users who need quick access to verification codes!

