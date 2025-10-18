#!/usr/bin/env python
"""
Examples: Access Outlook/Hotmail mailboxes via IMAP OAuth2 and Microsoft Graph.

- Approach A (recommended): Microsoft Graph API using a refresh token
- Approach B (optional): IMAP with OAuth2 (XOAUTH2) using an access token minted for IMAP

Environment variables (set before running):
  EMAIL            - target mailbox (e.g. user@hotmail.com)
  CLIENT_ID        - app registration client ID
  REFRESH_TOKEN    - delegated refresh token for the user
  TENANT           - optional tenant (default: common)

Security: This script reads secrets from environment variables only and does not print them.
"""
from __future__ import annotations

import base64
import imaplib
import os
import sys
from typing import Optional

import requests

# Prefer project Graph client if running inside repo
try:
    from servbot.clients import GraphClient  # type: ignore
except Exception:
    GraphClient = None  # type: ignore


def _env(name: str, required: bool = True) -> Optional[str]:
    val = os.getenv(name)
    if required and not val:
        print(f"Missing required env var: {name}")
        sys.exit(1)
    return val


def get_access_token_v2_with_refresh(tenant: str, client_id: str, refresh_token: str) -> str:
    """Redeem a delegated refresh token for a new access token (Graph scopes are reused)."""
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        # IMPORTANT: do not send ".default" for delegated refresh; omit scope to reuse prior grants
    }
    r = requests.post(url, data=data, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def get_access_token_for_imap(tenant: str, client_id: str, refresh_token: str) -> str:
    """Acquire an access token suitable for IMAP XOAUTH2 (delegated). Requires IMAP permission.

    Scopes required at consent time typically include:
      - https://outlook.office.com/IMAP.AccessAsUser.All
      - offline_access
    """
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        # Request an IMAP token audience; will fail if app/user lacks IMAP permissions/consent
        "scope": "https://outlook.office.com/IMAP.AccessAsUser.All",
    }
    r = requests.post(url, data=data, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def _xoauth2_auth_string(user: str, access_token: str) -> bytes:
    return (f"user={user}\x01auth=Bearer {access_token}\x01\x01").encode("utf-8")


def try_imap_xoauth2(email: str, access_token: str) -> None:
    print("\n[IMAP] Connecting to outlook.office365.com via XOAUTH2...")
    M = imaplib.IMAP4_SSL("outlook.office365.com", 993)
    try:
        M.authenticate("XOAUTH2", lambda _: _xoauth2_auth_string(email, access_token))
        typ, _ = M.select("INBOX")
        print(f"[IMAP] INBOX select: {typ}")
        typ, data = M.search(None, "ALL")
        if typ == "OK" and data and data[0]:
            ids = data[0].split()
            print(f"[IMAP] Message count: {len(ids)}")
        else:
            print("[IMAP] No messages or search failed")
    finally:
        try:
            M.logout()
        except Exception:
            pass


def try_graph(email: str, client_id: str, refresh_token: str) -> None:
    if GraphClient is None:
        print("GraphClient not available in this environment; skipping Graph test")
        return
    print("\n[Graph] Fetching latest messages via Microsoft Graph...")
    gc = GraphClient.from_credentials(refresh_token, client_id, mailbox=email)
    if not gc:
        print("[Graph] Failed to create client from credentials")
        return
    msgs = gc.fetch_messages(folder="inbox", unseen_only=False, limit=10)
    print(f"[Graph] Received {len(msgs)} messages")
    for i, m in enumerate(msgs[:5], 1):
        print(f"  {i}. {m.subject} — from {m.from_addr}")


if __name__ == "__main__":
    EMAIL = _env("EMAIL") or ""
    CLIENT_ID = _env("CLIENT_ID") or ""
    REFRESH_TOKEN = _env("REFRESH_TOKEN") or ""
    TENANT = os.getenv("TENANT", "common")

    # A) Graph (recommended)
    try_graph(EMAIL, CLIENT_ID, REFRESH_TOKEN)

    # B) IMAP XOAUTH2 (optional; requires IMAP delegated permission and consent)
    try:
        imap_token = get_access_token_for_imap(TENANT, CLIENT_ID, REFRESH_TOKEN)
        masked = imap_token[:6] + "..." + imap_token[-6:]
        print(f"[IMAP] Access token acquired (masked): {masked}")
        try_imap_xoauth2(EMAIL, imap_token)
    except Exception as e:
        print(f"[IMAP] Failed to acquire token or connect: {e}")
