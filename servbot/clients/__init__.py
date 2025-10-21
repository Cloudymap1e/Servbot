"""Email client implementations for different providers."""

from .graph import GraphClient
from .flashmail import FlashmailClient
from .imap import IMAPClient  # test stub

__all__ = ['GraphClient', 'FlashmailClient', 'IMAPClient']

