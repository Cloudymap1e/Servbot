"""Flashmail card alias management and balance utilities.

This module manages Flashmail API card aliases using secure_store for secret
storage and the database.flashmail_cards table for metadata (no secrets).
"""
from __future__ import annotations

import datetime as dt
from typing import Optional, Dict, List

from .secure_store import (
    set_secret,
    get_secret,
    secret_exists,
    redact,
    FLASHMAIL_SERVICE,
)
from .clients.flashmail import FlashmailClient
from .data.database import (
    ensure_db,
    add_flashmail_card as db_add_card,
    list_flashmail_cards as db_list_cards,
    set_default_flashmail_card as db_set_default,
    update_flashmail_card_balance as db_update_balance,
    remove_flashmail_card as db_remove_card,
)


def register_card(alias: str, card_value: str, set_default: bool = False) -> bool:
    """Register a Flashmail card under an alias and persist metadata.

    Args:
        alias: Alias to store under (e.g., 'fm_primary')
        card_value: Raw Flashmail card value (will be stored securely)
        set_default: Whether to mark this alias as the default
    """
    ensure_db()
    set_secret(FLASHMAIL_SERVICE, alias, card_value)
    db_add_card(alias, storage="keyring")
    if set_default:
        db_set_default(alias)
    return True


def list_cards() -> List[Dict[str, str]]:
    ensure_db()
    rows = db_list_cards()
    # Do not include secrets; only metadata
    return rows


def set_default(alias: str) -> bool:
    ensure_db()
    return db_set_default(alias)


def remove_card(alias: str, delete_secret: bool = False) -> bool:
    from .secure_store import delete_secret as sec_delete
    ok = db_remove_card(alias)
    if delete_secret:
        sec_delete(FLASHMAIL_SERVICE, alias)
    return ok


def get_client_by_alias(alias: str) -> Optional[FlashmailClient]:
    secret = get_secret(FLASHMAIL_SERVICE, alias)
    if not secret:
        return None
    return FlashmailClient(secret)


def update_balance(alias: str) -> Optional[int]:
    client = get_client_by_alias(alias)
    if not client:
        return None
    bal = client.get_balance()
    db_update_balance(alias, bal, dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
    return bal


def pick_card(min_required_credits: int = 1) -> Optional[str]:
    """Pick the best card alias that meets the required credits.

    Strategy:
    - Prefer default alias if it has sufficient credits (if known)
    - Otherwise update balances for all and pick the one with enough credits
      with maximum balance; tie-breaker: default, then alias name
    """
    ensure_db()
    cards = db_list_cards()
    if not cards:
        return None

    # Check default first
    default_alias = None
    for c in cards:
        if c.get("is_default"):
            default_alias = c["alias"]
            bal = int(c.get("last_known_balance") or 0)
            if bal >= min_required_credits:
                return default_alias
            break

    # Refresh balances
    with_balances = []
    for c in cards:
        alias = c["alias"]
        bal = update_balance(alias)
        with_balances.append((alias, bal or 0, bool(c.get("is_default"))))

    # Filter by requirement
    candidates = [x for x in with_balances if x[1] >= min_required_credits]
    if not candidates:
        # If none meet requirement, still return default or the first
        return default_alias or (cards[0]["alias"])  # type: ignore

    # Sort: max balance desc, default first, alias asc
    candidates.sort(key=lambda x: (-x[1], not x[2], x[0]))
    return candidates[0][0]
