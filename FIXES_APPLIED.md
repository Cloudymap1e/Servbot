# Fixes Applied - Email Fetching Issues

## Date
October 17, 2025

## Problems Identified

### 1. ❌ Graph API Failing Silently
- **Issue**: `GraphClient.from_credentials()` was not finding account-specific credentials
- **Root Cause**: Code only checked global config, not account-specific credentials in database
- **Impact**: Graph API never worked for Flashmail accounts

### 2. ❌ IMAP Parameter Error
- **Issue**: `TypeError: IMAPClient.__init__() got an unexpected keyword argument 'ssl'`
- **Root Cause**: Wrong parameter name (should be `use_ssl=` not just `ssl`)
- **Impact**: IMAP fallback completely broken

### 3. ❌ Result
- Both Graph API and IMAP were failing
- **0 messages fetched** even though emails existed in the inbox

## Fixes Applied

### Fix #1: Graph API Credentials Lookup
**File**: `core/verification.py` lines 193-221

**Before**:
```python
# Only checked global config
graph_creds = load_graph_account()
if graph_creds:
    graph_client = GraphClient.from_credentials(...)
```

**After**:
```python
# First check account-specific credentials
if username:
    accounts = get_accounts()
    for acc in accounts:
        if acc['email'].lower() == username.lower():
            if acc.get('refresh_token') and acc.get('client_id'):
                graph_client = GraphClient.from_credentials(
                    acc['refresh_token'],
                    acc['client_id'],
                )
            break

# Fallback to global config if needed
if not graph_client:
    graph_creds = load_graph_account()
    ...
```

### Fix #2: IMAP Parameter Fix
**File**: `core/verification.py` line 234

**Before**:
```python
client = IMAPClient(imap_server, username, password, port, ssl)  # Wrong!
```

**After**:
```python
client = IMAPClient(imap_server, username, password, port, use_ssl=ssl)  # Correct!
```

### Enhancement: Improved CLI Account Display
**File**: `cli.py` lines 145-220

**Added**:
- Verbose mode: `accounts -v` shows all credentials
- Password length display
- Refresh token and client ID status
- Clear indicators of what's configured

## Verification

### Account Data Saved Correctly ✓
```
Account: fgmzknbmmt7648@outlook.com
  Type: outlook
  Source: flashmail
  Password: ********** (length: 480)
  IMAP Server: outlook.office365.com

  Graph API Credentials:
    Has refresh_token: True (424 chars) ✓
    Matches FLASHMAIL constant: True ✓
    Has client_id: True (36 chars) ✓
    Matches FLASHMAIL constant: True ✓
```

**Conclusion**: All data IS being saved correctly!

## How to Use

### 1. Restart CLI
```bash
# Exit if running
servbot> exit

# Start fresh
python main.py
```

### 2. Check Account Credentials
```bash
servbot> accounts
# Shows basic info

servbot> accounts -v
# Shows detailed credential information including:
# - Password length
# - Refresh token status and preview
# - Client ID (full value)
# - All credential lengths
```

### 3. Test Email Fetching
```bash
servbot> inbox fgmzknbmmt7648@outlook.com
# Should now show:
# - Number of messages fetched
# - List of email subjects
# - Verification codes if found
```

## Expected Results

### Before Fixes:
```
servbot> inbox fgmzknbmmt7648@outlook.com
Fetching inbox for fgmzknbmmt7648@outlook.com...
Connecting to outlook.office365.com...
Fetched 0 total messages (0 new)    ❌
```

### After Fixes:
```
servbot> inbox fgmzknbmmt7648@outlook.com
Fetching inbox for fgmzknbmmt7648@outlook.com...
Connecting to outlook.office365.com...
Fetched 3 total messages (3 new)    ✓

======================================================================
RECENT MESSAGES IN INBOX
======================================================================

1. Your Reddit verification code
   From: noreply@reddit.com
   Date: 2024-10-17 12:30:00
   Preview: Your verification code is 123456...

======================================================================
VERIFICATION CODES FOUND (1 total)
======================================================================

1. Reddit
   Value:   123456
   Type:    Code
   Subject: Your Reddit verification code
   From:    noreply@reddit.com
======================================================================
```

## New CLI Commands

### View Accounts (Basic)
```
servbot> accounts
```
Shows email, type, source, IMAP server, Graph API status

### View Accounts (Detailed)
```
servbot> accounts -v
```
Shows everything including:
- Password length
- Refresh token status and preview
- Full client ID
- All credential verification

### View Specific Source
```
servbot> accounts flashmail
servbot> accounts flashmail -v
```

## Technical Details

### Graph API Flow Now:
1. Check if username provided
2. Look up account in database by email
3. If account has `refresh_token` and `client_id`, use them
4. Call `GraphClient.from_credentials(refresh_token, client_id)`
5. Graph client exchanges refresh token for access token
6. Fetch messages via Graph API
7. If fails, fall back to IMAP

### IMAP Flow Now:
1. Create IMAPClient with correct parameters
2. Connect to IMAP server
3. Fetch messages
4. Parse and extract verification codes

## Testing Checklist

- [x] Verify account data is saved (refresh_token, client_id, password)
- [x] Fix Graph API credential lookup
- [x] Fix IMAP parameter error
- [x] Add verbose account display
- [ ] Test: Restart CLI and run `inbox` command
- [ ] Test: Verify messages are fetched
- [ ] Test: Verify Reddit email appears
- [ ] Test: Verify verification code is extracted

## Next Steps

1. **Restart the CLI** to load the fixed code
2. **Run** `accounts -v` to verify credentials are showing
3. **Run** `inbox fgmzknbmmt7648@outlook.com` to test fetching
4. **Verify** messages are now being fetched
5. **Check** if Reddit verification code is extracted

If messages still don't fetch, we'll need to debug Graph API token exchange.

