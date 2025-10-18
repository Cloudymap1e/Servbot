#!/usr/bin/env python
"""Register Flashmail card secrets from environment variables into keyring.

Environment variables used:
- SERVBOT_FM_PRIMARY: primary card value
- SERVBOT_FM_BACKUP:  backup card value

Usage (PowerShell example):
  $env:SERVBOT_FM_PRIMARY = "{{FLASHMAIL_CARD_PRIMARY}}"
  $env:SERVBOT_FM_BACKUP  = "{{FLASHMAIL_CARD_BACKUP}}"
  python scripts/register_cards_from_env.py
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from servbot.flashmail_cards import register_card, set_default, list_cards
from servbot.logging_config import setup_logging
import logging


def main() -> int:
    setup_logging()
    primary = os.getenv("SERVBOT_FM_PRIMARY")
    backup = os.getenv("SERVBOT_FM_BACKUP")
    
    if not primary and not backup:
        print("No env variables found. Set SERVBOT_FM_PRIMARY and/or SERVBOT_FM_BACKUP.")
        return 2
    
    if primary:
        register_card("fm_primary", primary, set_default=True)
        logging.info("Registered fm_primary (len=%d)", len(primary))
    if backup:
        register_card("fm_backup", backup, set_default=False)
        logging.info("Registered fm_backup (len=%d)", len(backup))
    
    # Show summary
    cards = list_cards()
    print("\nRegistered cards:")
    for c in cards:
        mark = " [DEFAULT]" if c.get('is_default') else ""
        print(f"  • {c['alias']}{mark}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())