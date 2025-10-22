"""Servbot - Email verification code extraction system.

Servbot is a comprehensive email automation tool that:
- Fetches emails via Microsoft Graph API
- Extracts verification codes and magic links
- Identifies services using regex patterns and AI
- Integrates with Flashmail for account provisioning

Basic Usage (Graph-only):
    >>> from servbot import fetch_verification_codes
    >>> verifications = fetch_verification_codes(
    ...     username="user@outlook.com",
    ...     prefer_graph=True,
    ... )
    >>> for v in verifications:
    ...     print(v.as_pair())  # <Service, Code>

Advanced Usage:
    >>> from servbot import get_verification_for_service
    >>> code = get_verification_for_service(
    ...     target_service="GitHub",
    ...     username="user@outlook.com",
    ...     timeout_seconds=60,
    ...     prefer_graph=True,
    ... )
    >>> print(code)  # 123456 or https://...

For more information, see individual module documentation.
"""

from .api import (
    # Core functions
    fetch_verification_codes,
    get_verification_for_service,
    get_latest_verification,
                                                                                                                                     
    # Flashmail integration
    provision_flashmail_account,
    get_flashmail_inventory,
    get_flashmail_balance,
    
    # Database utilities
    list_database,
    get_account_verifications,
    
    # Models
    Verification,
    EmailAccount,
    
    # Clients (for advanced usage)
    GraphClient,
    FlashmailClient,
)

__version__ = "2.0.0"

__all__ = [
    # Core functions
    'fetch_verification_codes',
    'get_verification_for_service',
    'get_latest_verification',
    
    # Flashmail
    'provision_flashmail_account',
    'get_flashmail_inventory',
    'get_flashmail_balance',
    
    # Database utilities
    'list_database',
    'get_account_verifications',
    
    # Models
    'Verification',
    'EmailAccount',
    
    # Clients
    'GraphClient',
    'FlashmailClient',
    
    # Version
    '__version__',
]

# Auto-instrumentation
try:
    from . import instrumentation as _inst  # noqa: F401
except Exception:
    _inst = None  # type: ignore
