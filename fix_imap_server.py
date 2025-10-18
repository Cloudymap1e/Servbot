#!/usr/bin/env python
"""Fix IMAP server for existing Flashmail accounts."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from servbot.data.database import get_accounts, _connect

print("=" * 80)
print("FIXING IMAP SERVER FOR FLASHMAIL ACCOUNTS")
print("=" * 80)

accounts = get_accounts(source='flashmail')

if not accounts:
    print("\nNo Flashmail accounts found.")
    sys.exit(0)

print(f"\nFound {len(accounts)} Flashmail account(s)")

conn = _connect()
cur = conn.cursor()

for acc in accounts:
    old_server = acc.get('imap_server', 'N/A')
    new_server = 'imap.shanyouxiang.com'
    
    print(f"\nAccount: {acc['email']}")
    print(f"  Old IMAP server: {old_server}")
    print(f"  New IMAP server: {new_server}")
    
    if old_server != new_server:
        cur.execute(
            "UPDATE accounts SET imap_server = ? WHERE email = ?",
            (new_server, acc['email'])
        )
        print("  [UPDATED]")
    else:
        print("  [OK] Already correct")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("UPDATE COMPLETE")
print("=" * 80)
print("\nAll Flashmail accounts now use: imap.shanyouxiang.com")
print("This is Flashmail's IMAP proxy that bypasses Microsoft restrictions.")

