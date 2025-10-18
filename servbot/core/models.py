"""Data models for servbot.

This module defines the core data structures used throughout servbot,
following Google Python Style Guide conventions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Verification:
    """Represents an extracted verification code or link.
    
    Attributes:
        service: Name of the service (e.g., "Google", "GitHub")
        code: Verification code or URL
        uid: Optional message UID from mail server
        subject: Optional email subject line
        from_addr: Optional sender email address
        date: Optional email date string
        is_link: True if code is a verification link, False if OTP code
    """
    service: str
    code: str
    uid: Optional[int] = None
    subject: Optional[str] = None
    from_addr: Optional[str] = None
    date: Optional[str] = None
    is_link: bool = False

    def as_pair(self) -> str:
        """Returns formatted string representation: <Service, Code>."""
        return f"<{self.service}, {self.code}>"


@dataclass
class EmailAccount:
    """Represents an email account configuration.
    
    Attributes:
        email: Email address
        password: Account password
        account_type: Type of account (e.g., "outlook", "hotmail")
        source: Where account came from (e.g., "flashmail", "manual")
        imap_server: IMAP server address
        card: Optional API card ID (for Flashmail accounts)
        refresh_token: Optional Microsoft Graph OAuth refresh token (per-account)
        client_id: Optional Microsoft Graph OAuth client ID (per-account)
    """
    email: str
    password: str
    account_type: str = "other"
    source: str = "manual"
    imap_server: Optional[str] = None
    card: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None


@dataclass
class EmailMessage:
    """Represents a fetched email message.
    
    Attributes:
        message_id: Unique message identifier
        provider: Email provider ("imap" or "graph")
        mailbox: Mailbox email address
        subject: Email subject line
        from_addr: Sender email address
        received_date: Date message was received
        body_text: Plain text body
        body_html: HTML body
        is_read: Whether message has been read
    """
    message_id: str
    provider: str
    mailbox: str
    subject: str
    from_addr: str
    received_date: str
    body_text: str = ""
    body_html: str = ""
    is_read: bool = False

