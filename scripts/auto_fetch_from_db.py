#!/usr/bin/env python
"""
Auto-fetch inbox using the first database account that has Graph credentials.

- Prefers Microsoft Graph API using refresh_token + client_id from DB
- Falls back to IMAP username/password if Graph fails
- Prints a concise success summary without exposing secrets

Usage:
  python scripts/auto_fetch_from_db.py
"""
from __future__ import annotations

import sys
from typing import Optional

import pathlib
import sys as _sys
# Ensure project root is on path
_project_root = pathlib.Path(__file__).resolve().parents[1]
if str(_project_root) not in _sys.path:
    _sys.path.insert(0, str(_project_root))

from servbot.data.database import ensure_db, get_accounts
from servbot.clients import GraphClient, IMAPClient


def pick_accounts() -> list[dict]:
    ensure_db()
    accounts = get_accounts()
    # Prefer accounts with Graph creds first
    prioritized: list[dict] = []
    for acc in accounts:
        if acc.get("refresh_token") and acc.get("client_id") and acc.get("email"):
            prioritized.append(acc)
    # Append remaining accounts (IMAP-only)
    for acc in accounts:
        if acc not in prioritized:
            prioritized.append(acc)
    return prioritized


def fetch_via_graph(acc: dict) -> Optional[int]:
    email = acc.get("email", "")
    rt = acc.get("refresh_token")
    cid = acc.get("client_id")
    if not (email and rt and cid):
        return None

    client = GraphClient.from_credentials(rt, cid, mailbox=email)
    if not client:
        return None

    msgs = client.fetch_messages(folder="inbox", unseen_only=False, limit=20)
    # Print a small summary without secrets
    print(f"Graph: fetched {len(msgs)} messages for {email}")
    for i, m in enumerate(msgs[:5], 1):
        subj = (m.subject or "")[:80]
        print(f"  {i}. {subj} — from {m.from_addr}")
    return len(msgs)


def infer_imap_server(email: str, source: str = "") -> str:
    # Use Flashmail proxy for Flashmail-provisioned accounts
    if (source or "").lower() == "flashmail":
        return "imap.shanyouxiang.com"
    e = email.lower()
    if any(x in e for x in ("outlook", "hotmail", "live", "msn")):
        return "outlook.office365.com"
    if "gmail" in e:
        return "imap.gmail.com"
    return "outlook.office365.com"


def fetch_via_imap(acc: dict) -> Optional[int]:
    email = acc.get("email", "")
    password = acc.get("password") or ""
    if not (email and password):
        return None
    server = acc.get("imap_server") or infer_imap_server(email, acc.get("source", ""))

    print(f"Using IMAP server: {server}")
    # Try SSL first (993)
    try:
        client = IMAPClient(server, email, password, port=993, use_ssl=True)
        msgs = client.fetch_messages(folder="INBOX", unseen_only=False, limit=20)
        print(f"IMAP: fetched {len(msgs)} messages for {email}")
        for i, m in enumerate(msgs[:5], 1):
            subj = (m.subject or "")[:80]
            print(f"  {i}. {subj} — from {m.from_addr}")
        return len(msgs)
    except Exception as e:
        print(f"IMAP SSL failed: {e}")
    # Try STARTTLS/plain port 143 (no SSL)
    try:
        print("Trying IMAP on port 143 without SSL...")
        client = IMAPClient(server, email, password, port=143, use_ssl=False)
        msgs = client.fetch_messages(folder="INBOX", unseen_only=False, limit=20)
        print(f"IMAP (no SSL): fetched {len(msgs)} messages for {email}")
        for i, m in enumerate(msgs[:5], 1):
            subj = (m.subject or "")[:80]
            print(f"  {i}. {subj} — from {m.from_addr}")
        return len(msgs)
    except Exception as e:
        print(f"IMAP (no SSL) failed: {e}")
    return None


def main() -> int:
    accounts = pick_accounts()
    if not accounts:
        print("No accounts found in database.")
        return 2

    for acc in accounts:
        email = acc.get("email")
        src = acc.get("source", "")
        print(f"Selected account: {email} (source={src})")

        # Try Graph first
        try:
            n = fetch_via_graph(acc)
            if isinstance(n, int) and n >= 0:
                print("SUCCESS (Graph)")
                return 0
        except Exception as e:
            print(f"Graph failed: {e}")

        # Fallback to IMAP
        try:
            n = fetch_via_imap(acc)
            if isinstance(n, int) and n >= 0:
                print("SUCCESS (IMAP)")
                return 0
        except Exception as e:
            print(f"IMAP failed: {e}")

    print("All accounts failed (Graph and IMAP).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
