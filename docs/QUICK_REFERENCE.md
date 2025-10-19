# Quick Reference - Credential Handling Fixes

## What Was Fixed?

### 🔴 Bug #1: Graph API Messages Lost in Database
**Before:** Graph-fetched verifications couldn't be retrieved by email
**After:** Mailbox field properly populated, all verifications retrievable

### 🔴 Bug #2: Credentials Couldn't Be Cleared  
**Before:** Passing NULL kept old values (COALESCE blocked updates)
**After:** Can clear/update credentials properly with new upsert mode

### 🔴 Bug #3: Flashmail Wasted Graph Credentials
**Before:** Saved Graph credentials but immediately used IMAP
**After:** Prefers Graph API for better performance (IMAP as fallback)

### 🔴 Bug #4: Duplicate Credential Tables
**Before:** Two tables, confusing and error-prone
**After:** Single `accounts` table, auto-migration on startup

---

## Quick Usage Examples

### Use New Upsert Mode (Allow NULL)
```python
from servbot.data import upsert_account

# Update credentials, clearing old token
upsert_account(
    email="user@example.com",
    password="new_password",
    refresh_token=None,  # ✅ Clears the token!
    update_only_if_provided=False,  # NEW: Direct update mode
)
```

### Use Legacy Mode (Keep Non-Empty)
```python
# Only update provided values (old behavior)
upsert_account(
    email="user@example.com",
    password="new_password",
    update_only_if_provided=True,  # Legacy COALESCE mode
)
```

### Graph API Now Includes Mailbox
```python
from servbot.clients import GraphClient

# Mailbox parameter now supported
client = GraphClient.from_credentials(
    refresh_token="...",
    client_id="...",
    mailbox="user@outlook.com",  # ✅ NEW
)

messages = client.fetch_messages()
for msg in messages:
    print(msg.mailbox)  # ✅ "user@outlook.com" not ""
```

---

## Migration

### Automatic (Recommended)
Just run your app normally:
```bash
python -m servbot
```

The migration runs automatically on startup via `ensure_db()`.

### Manual
```python
from servbot.data.database import migrate_graph_accounts_to_accounts
migrate_graph_accounts_to_accounts()
```

---

## Testing Your Setup

### Check Mailbox Population
```python
from servbot.data.database import _connect

conn = _connect()
cur = conn.cursor()
cur.execute("SELECT mailbox, subject FROM messages WHERE provider='graph'")
messages = cur.fetchall()

for msg in messages:
    assert msg[0] != "", f"Empty mailbox for: {msg[1]}"
    print(f"✅ {msg[0]}: {msg[1]}")
```

### Check Credential Storage
```python
from servbot.data import get_accounts

accounts = get_accounts()
for acc in accounts:
    print(f"{acc['email']}:")
    print(f"  Password: {'YES' if acc['password'] else 'NO'}")
    print(f"  Graph Token: {'YES' if acc['refresh_token'] else 'NO'}")
    print(f"  Graph Client: {'YES' if acc['client_id'] else 'NO'}")
```

---

## CLI Changes

### Provisioning Now Shows Graph Status
```
servbot> provision outlook
...
Email:    test@outlook.com
Password: ********
Type:     outlook
IMAP:     imap.shanyouxiang.com

Microsoft Graph API: Enabled (OAuth credentials saved)
  → Supports both IMAP and Graph API for email fetching
...
```

### Verbose Account Listing
```
servbot> accounts -v
...
1. user@outlook.com
   Type: outlook
   Source: flashmail
   Password: ********** (16 chars)
   IMAP Server: imap.shanyouxiang.com
   Created: 2025-10-18 09:30:00

   Credentials Status:
     Password: YES (16 chars)
     Refresh Token: YES (384 chars)
     Client ID: YES (36 chars)
       Client ID: 8b4ba9dd-3ea5-4e5f-86f1-ddba2230dcf2
       Refresh Token: M.C555_BAY.0.U.-CuM67nex5EBQ...
   
   Graph API: [OK] Configured
...
```

---

## Terminology Clarification

**"Graph API" = Microsoft Graph API**
- Official Microsoft OAuth2 API for Office 365/Outlook
- URL: https://graph.microsoft.com
- Uses refresh_token + client_id → access_token
- NOT Google's API or any other "graph" API

---

## Files You Should Know About

### Modified
- `clients/graph.py` - GraphClient with mailbox support
- `core/verification.py` - Passes mailbox to GraphClient
- `data/database.py` - New upsert modes + migration
- `api.py` - Flashmail uses Graph API now
- `cli.py` - Better messaging and new upsert mode
- `WARP.md` - Updated architecture docs

### New
- `FIXES_SUMMARY.md` - Detailed explanation (this is the main doc)
- `QUICK_REFERENCE.md` - This file

---

## Backward Compatibility

✅ All changes are backward compatible:
- Old code still works (mailbox is optional)
- Legacy upsert mode available if needed
- Migration is automatic and safe
- No breaking changes to public API

---

## Next Steps (Optional)

See `FIXES_SUMMARY.md` for:
- Detailed technical explanations
- Testing recommendations
- Future improvement ideas
- Complete credential flow documentation

---

## Questions?

1. Check `FIXES_SUMMARY.md` for detailed explanations
2. Check `WARP.md` for architecture overview
3. Check `cli.py` for usage examples
4. Use `accounts -v` to inspect credential status
