"""Servbot - Email verification code extraction system.

Servbot is a comprehensive email automation tool that:
- Fetches emails via IMAP or Microsoft Graph API
- Extracts verification codes and magic links
- Identifies services using regex patterns and AI
- Integrates with Flashmail for account provisioning

Basic Usage:
    >>> from servbot import fetch_verification_codes
    >>> 
    >>> verifications = fetch_verification_codes(
    ...     imap_server="imap.gmail.com",
    ...     username="user@gmail.com",
    ...     password="password"
    ... )
    >>> 
    >>> for v in verifications:
    ...     print(v.as_pair())  # <Service, Code>

Advanced Usage:
    >>> from servbot import get_verification_for_service
    >>> 
    >>> code = get_verification_for_service(
    ...     target_service="GitHub",
    ...     imap_server="imap.gmail.com",
    ...     username="user@gmail.com",
    ...     password="password",
    ...     timeout_seconds=60
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
    IMAPClient,
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
    'IMAPClient',
    'GraphClient',
    'FlashmailClient',
    
    # Version
    '__version__',
]

