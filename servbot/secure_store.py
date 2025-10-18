"""Secure secrets storage and redaction utilities.

This module provides secure storage for sensitive data like API keys and passwords
using OS-level credential stores (Windows Credential Manager on Windows) with
fallback to environment variables for development.

Key features:
- Windows Credential Manager integration via keyring library
- Comprehensive redaction for logging and display
- Development fallbacks with security warnings
- Never stores secrets in SQLite database
"""

import os
import re
import logging
from typing import Optional, Dict, Any, Set, Union

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None  # type: ignore

# Constants
FLASHMAIL_SERVICE = "servbot.flashmail"
ENV_PREFIX = "SERVBOT"

# Sensitive key patterns for redaction
SENSITIVE_KEYS = {
    'password', 'refresh', 'token', 'client', 'card', 'secret', 'authorization',
    'api_key', 'auth', 'credential', 'key', 'pass', 'pwd', 'oauth', 'bearer'
}


class SecureStoreError(Exception):
    """Base exception for secure store operations."""
    pass


class RedactionFilter(logging.Filter):
    """Logging filter that redacts sensitive information from log records."""
    
    def __init__(self):
        super().__init__()
        # Patterns to redact in log messages
        self.patterns = [
            # API keys and tokens (20+ alphanumeric chars)
            (re.compile(r'\b[A-Za-z0-9]{20,}\b'), lambda m: redact(m.group(0), show=4)),
            # Bearer tokens
            (re.compile(r'Bearer\s+([A-Za-z0-9._-]+)', re.IGNORECASE), 
             lambda m: f"Bearer {redact(m.group(1), show=4)}"),
            # Authorization headers
            (re.compile(r'Authorization:\s*([^\s]+)', re.IGNORECASE),
             lambda m: f"Authorization: {redact(m.group(1), show=4)}"),
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive data from log record."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            msg = record.msg
            for pattern, replacer in self.patterns:
                msg = pattern.sub(replacer, msg)
            record.msg = msg
        
        # Also redact args if present
        if hasattr(record, 'args') and record.args:
            try:
                record.args = tuple(
                    redact(str(arg), show=4) if _looks_sensitive(str(arg)) else arg
                    for arg in record.args
                )
            except (TypeError, ValueError):
                pass  # Leave args unchanged if can't process
        
        return True


def _looks_sensitive(value: str) -> bool:
    """Check if a string value looks like sensitive data."""
    if not isinstance(value, str):
        return False
    
    # Check for long alphanumeric strings (likely tokens/keys)
    if len(value) >= 20 and re.match(r'^[A-Za-z0-9._-]+$', value):
        return True
    
    # Check for known sensitive patterns
    value_lower = value.lower()
    return any(sensitive in value_lower for sensitive in SENSITIVE_KEYS)


def set_secret(service: str, name: str, value: str) -> None:
    """Store a secret in the OS credential store.
    
    Args:
        service: Service name (e.g., FLASHMAIL_SERVICE)
        name: Secret name/alias (e.g., "fm_primary")
        value: Secret value to store
        
    Raises:
        SecureStoreError: If storage fails
    """
    if not KEYRING_AVAILABLE:
        raise SecureStoreError(
            "keyring library not available. Install with: pip install keyring"
        )
    
    if not value or not value.strip():
        raise SecureStoreError("Cannot store empty secret value")
    
    try:
        keyring.set_password(service, name, value.strip())
        logging.info(f"Stored secret for {service}:{name} (length: {len(value)})")
    except Exception as e:
        raise SecureStoreError(f"Failed to store secret: {e}")


def get_secret(service: str, name: str, allow_fallbacks: bool = True) -> Optional[str]:
    """Retrieve a secret from the OS credential store with fallbacks.
    
    Args:
        service: Service name
        name: Secret name/alias
        allow_fallbacks: Whether to check env vars and files as fallback
        
    Returns:
        Secret value or None if not found
    """
    # Try keyring first
    if KEYRING_AVAILABLE:
        try:
            value = keyring.get_password(service, name)
            if value:
                logging.debug(f"Retrieved secret from keyring: {service}:{name} (length: {len(value)})")
                return value
        except Exception as e:
            logging.warning(f"Failed to retrieve from keyring {service}:{name}: {e}")
    
    if not allow_fallbacks:
        return None
    
    # Fallback 1: Environment variable
    env_key = f"{ENV_PREFIX}_{name.upper()}"
    env_value = os.getenv(env_key)
    if env_value:
        logging.warning(
            f"Using environment variable {env_key} for {service}:{name}. "
            "Consider migrating to secure keyring storage."
        )
        return env_value.strip()
    
    # Fallback 2: Legacy ai.api file (development only)
    if service == FLASHMAIL_SERVICE and name in ("fm_primary", "fm_backup", "FLASHMAIL_CARD"):
        try:
            from pathlib import Path
            ai_api_file = Path(__file__).parent / "data" / "ai.api"
            if ai_api_file.exists():
                content = ai_api_file.read_text()
                for line in content.split('\n'):
                    if line.strip().startswith('FLASHMAIL_CARD') and '=' in line:
                        value = line.split('=', 1)[1].strip().strip('"\'')
                        if value:
                            logging.warning(
                                f"Using ai.api file for {service}:{name}. "
                                "This is insecure for production. Run 'cards add' to migrate."
                            )
                            return value
        except Exception as e:
            logging.debug(f"Failed to read ai.api fallback: {e}")
    
    logging.debug(f"Secret not found: {service}:{name}")
    return None


def delete_secret(service: str, name: str, delete_fallbacks: bool = False) -> bool:
    """Delete a secret from the credential store.
    
    Args:
        service: Service name
        name: Secret name/alias  
        delete_fallbacks: Also remove from env/file fallbacks
        
    Returns:
        True if deleted successfully
    """
    success = True
    
    # Delete from keyring
    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(service, name)
            logging.info(f"Deleted secret from keyring: {service}:{name}")
        except Exception as e:
            logging.warning(f"Failed to delete from keyring {service}:{name}: {e}")
            success = False
    
    # Optionally clean up fallbacks
    if delete_fallbacks:
        # Environment variables can't be deleted from other processes
        env_key = f"{ENV_PREFIX}_{name.upper()}"
        if os.getenv(env_key):
            logging.warning(f"Environment variable {env_key} still set - remove manually")
        
        # Note: We don't auto-modify ai.api file for safety
    
    return success


def secret_exists(service: str, name: str) -> bool:
    """Check if a secret exists in the credential store.
    
    Args:
        service: Service name
        name: Secret name/alias
        
    Returns:
        True if secret exists
    """
    return get_secret(service, name, allow_fallbacks=False) is not None


def redact(value: str, show: int = 4) -> str:
    """Redact a sensitive value for safe display.
    
    Args:
        value: Value to redact
        show: Number of characters to show at start/end
        
    Returns:
        Redacted string like "abcd...wxyz (len=50)"
    """
    if not isinstance(value, str):
        value = str(value)
    
    if not value:
        return "[empty]"
    
    length = len(value)
    
    # For very short values, don't show any characters
    if length <= show * 2:
        return f"[redacted len={length}]"
    
    # Show first/last N characters with ellipsis
    start = value[:show]
    end = value[-show:] if show > 0 else ""
    return f"{start}…{end} (len={length})"


def sanitize_mapping(data: Dict[str, Any], sensitive_keys: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Recursively sanitize a dictionary by redacting sensitive values.
    
    Args:
        data: Dictionary to sanitize
        sensitive_keys: Set of keys considered sensitive (uses defaults if None)
        
    Returns:
        Sanitized dictionary with sensitive values redacted
    """
    if sensitive_keys is None:
        sensitive_keys = SENSITIVE_KEYS
    
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        is_sensitive = any(sensitive in key_lower for sensitive in sensitive_keys)
        
        if isinstance(value, dict):
            result[key] = sanitize_mapping(value, sensitive_keys)
        elif isinstance(value, list):
            result[key] = [
                sanitize_mapping(item, sensitive_keys) if isinstance(item, dict)
                else redact(str(item)) if is_sensitive and item
                else item
                for item in value
            ]
        elif is_sensitive and value:
            result[key] = redact(str(value))
        else:
            result[key] = value
    
    return result


def get_keyring_status() -> Dict[str, Any]:
    """Get status information about keyring availability and backend.
    
    Returns:
        Dictionary with keyring status information
    """
    status = {
        "available": KEYRING_AVAILABLE,
        "backend": None,
        "backend_name": None,
    }
    
    if KEYRING_AVAILABLE:
        try:
            backend = keyring.get_keyring()
            status["backend"] = str(backend)
            status["backend_name"] = getattr(backend, 'name', type(backend).__name__)
        except Exception as e:
            status["error"] = str(e)
    
    return status


# Development convenience functions
def migrate_from_ai_api(alias: str = "fm_primary") -> bool:
    """Migrate FLASHMAIL_CARD from ai.api file to secure storage.
    
    Args:
        alias: Alias to use for the migrated secret
        
    Returns:
        True if migration successful
    """
    try:
        from pathlib import Path
        ai_api_file = Path(__file__).parent / "data" / "ai.api"
        
        if not ai_api_file.exists():
            logging.info("No ai.api file found to migrate")
            return False
        
        content = ai_api_file.read_text()
        for line in content.split('\n'):
            if line.strip().startswith('FLASHMAIL_CARD') and '=' in line:
                value = line.split('=', 1)[1].strip().strip('"\'')
                if value:
                    set_secret(FLASHMAIL_SERVICE, alias, value)
                    logging.info(f"Migrated FLASHMAIL_CARD to keyring as {alias}")
                    return True
        
        logging.warning("No FLASHMAIL_CARD found in ai.api file")
        return False
    
    except Exception as e:
        logging.error(f"Failed to migrate from ai.api: {e}")
        return False


def setup_logging_redaction() -> None:
    """Set up logging redaction filter on the root logger."""
    redaction_filter = RedactionFilter()
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(redaction_filter)
    
    # Add to all existing handlers
    for handler in root_logger.handlers:
        handler.addFilter(redaction_filter)