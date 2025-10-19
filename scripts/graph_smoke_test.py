#!/usr/bin/env python
"""Graph smoke test using GRAPH_ACCOUNT environment variable.

Expected env var:
  GRAPH_ACCOUNT = "email----password----refresh_token----client_id"

This script prints a few recent inbox messages via Microsoft Graph.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure local package is importable when running from repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servbot.clients import GraphClient


def main() -> int:
    acct = os.getenv("GRAPH_ACCOUNT")
    if not acct:
        print("GRAPH_ACCOUNT not set; please export your account string.", file=sys.stderr)
        return 2

    client = GraphClient.from_account_string(acct)
    if not client:
        print("GRAPH_ACCOUNT is invalid; expected 'email----password----refresh_token----client_id'.", file=sys.stderr)
        return 2

    try:
        msgs = client.fetch_messages(folder="inbox", unseen_only=False, limit=10)
    except Exception as e:
        print(f"Failed to fetch messages: {e}", file=sys.stderr)
        return 1

    if not msgs:
        print("No messages returned.")
        return 1

    for m in msgs[:5]:
        text = (m.body_text or m.body_html or "").strip()
        preview = text[:200] + ("..." if len(text) > 200 else "")
        print(f"Subject: {m.subject}")
        print(f"From: {m.from_addr}")
        print(f"Text: {preview}")
        print("-" * 50)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
