#!/usr/bin/env python
"""
Provision a new Flashmail account, save it to DB, then attempt inbox fetch via Graph then IMAP.
"""
from __future__ import annotations

import pathlib
import sys

# Ensure project root on path
root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from servbot.config import load_flashmail_card
from servbot.clients.flashmail import FlashmailClient
from servbot.data.database import upsert_account

from scripts.auto_fetch_from_db import main as auto_fetch_main


def main() -> int:
    card = load_flashmail_card()
    if not card:
        print("Flashmail API card not configured (data/ai.api)")
        return 2

    print("Provisioning one Outlook account from Flashmail...")
    client = FlashmailClient(card)
    accounts = client.fetch_accounts(quantity=1, account_type="outlook")
    if not accounts:
        print("Provisioning returned no accounts")
        return 1
    acct = accounts[0]

    # Save to DB with per-account Graph credentials from Flashmail
    acc_id = upsert_account(
        email=acct.email,
        password=acct.password,
        type=acct.account_type,
        source="flashmail",
        card=card,
        imap_server=FlashmailClient.infer_imap_server(acct.email),
        refresh_token=acct.refresh_token,
        client_id=acct.client_id,
        update_only_if_provided=False,
    )
    print(f"Saved account id={acc_id} email={acct.email}")
    print("Credentials:")
    print(f"  password      : {acct.password}")
    print(f"  refresh_token : {acct.refresh_token}")
    print(f"  client_id     : {acct.client_id}")

    # Try fetch
    return auto_fetch_main()


if __name__ == "__main__":
    sys.exit(main())
