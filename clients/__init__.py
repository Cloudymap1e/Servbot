"""Email client implementations for different providers."""

from .imap import IMAPClient
from .graph import GraphClient
from .flashmail import FlashmailClient

__all__ = ['IMAPClient', 'GraphClient', 'FlashmailClient']

