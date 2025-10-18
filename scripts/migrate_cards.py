#!/usr/bin/env python
"""One-time migration script to import secrets and normalize DB.

This script:
1. Imports FLASHMAIL_CARD secrets from ai.api file to Windows Credential Manager
2. Creates metadata entries in the flashmail_cards table  
3. Normalizes account passwords in the database
4. Optionally cleans up plaintext secrets from ai.api

Run with: python scripts/migrate_cards.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servbot.secure_store import (
    set_secret, 
    get_secret, 
    FLASHMAIL_SERVICE,
    get_keyring_status,
    redact
)
from servbot.data.database import ensure_db, migrate_normalize_flashmail_passwords
from servbot.flashmail_cards import register_card, list_cards
from servbot.logging_config import setup_logging
import logging


def import_from_ai_api() -> None:
    """Import FLASHMAIL_CARD from ai.api file to keyring."""
    ai_api_path = Path(__file__).parent.parent / "servbot" / "data" / "ai.api"
    
    if not ai_api_path.exists():
        logging.info("No ai.api file found - nothing to import")
        return
    
    content = ai_api_path.read_text()
    imported = False
    
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('FLASHMAIL_CARD') and '=' in line:
            value = line.split('=', 1)[1].strip().strip('"\'')
            if value and len(value) > 10:  # Basic validation
                # Register as primary card
                alias = "fm_primary"
                logging.info("Importing FLASHMAIL_CARD as %s (length: %d)", alias, len(value))
                register_card(alias, value, set_default=True)
                imported = True
                break
    
    if not imported:
        logging.warning("No valid FLASHMAIL_CARD found in ai.api file")
    else:
        logging.info("Successfully imported Flashmail card to secure storage")


def show_keyring_status() -> None:
    """Display keyring backend information."""
    status = get_keyring_status()
    logging.info("Keyring status: %s", status)
    
    if not status["available"]:
        logging.error("Keyring not available! Install with: pip install keyring")
        sys.exit(1)
    
    if status.get("backend_name"):
        logging.info("Using keyring backend: %s", status["backend_name"])


def prompt_cleanup_ai_api() -> None:
    """Ask user if they want to remove plaintext secrets from ai.api."""
    ai_api_path = Path(__file__).parent.parent / "servbot" / "data" / "ai.api"
    
    if not ai_api_path.exists():
        return
    
    print("\nSecrets have been migrated to secure storage.")
    print("Would you like to remove the plaintext FLASHMAIL_CARD from ai.api? (recommended)")
    response = input("Remove plaintext secrets? [Y/n]: ").strip().lower()
    
    if response in ('', 'y', 'yes'):
        try:
            content = ai_api_path.read_text()
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                if line.strip().startswith('FLASHMAIL_CARD'):
                    new_lines.append('# FLASHMAIL_CARD migrated to secure keyring storage')
                else:
                    new_lines.append(line)
            
            ai_api_path.write_text('\n'.join(new_lines))
            logging.info("Removed plaintext FLASHMAIL_CARD from ai.api")
            print("✓ Plaintext secrets removed from ai.api")
        except Exception as e:
            logging.error("Failed to clean up ai.api: %s", e)
    else:
        logging.info("Keeping plaintext secrets in ai.api (not recommended for production)")


def main() -> None:
    setup_logging(debug=False)
    logging.info("Starting Flashmail cards migration")
    
    print("=" * 60)
    print("Servbot Flashmail Cards Migration")  
    print("=" * 60)
    
    # Check keyring
    show_keyring_status()
    
    # Initialize database
    ensure_db()
    
    # Import secrets
    import_from_ai_api()
    
    # Normalize passwords
    migrate_normalize_flashmail_passwords()
    
    # Show current state
    cards = list_cards()
    if cards:
        print(f"\nRegistered cards ({len(cards)}):")
        for card in cards:
            default_mark = " [DEFAULT]" if card.get('is_default') else ""
            print(f"  • {card['alias']}{default_mark}")
            print(f"    Balance: {card.get('last_known_balance', 0)} credits")
            print(f"    Created: {card.get('created_at', 'unknown')}")
    else:
        print("\nNo cards found. Use CLI 'cards add' command to register cards.")
    
    # Optional cleanup
    prompt_cleanup_ai_api()
    
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run 'python -m servbot' to use the CLI")
    print("2. Use 'cards' command to manage your Flashmail API keys")
    print("3. Use 'balance' to check credits")
    print("4. Use 'provision' to create new accounts")


if __name__ == "__main__":
    main()