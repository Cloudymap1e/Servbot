"""Email client implementations for different providers."""

from .graph import GraphClient
from .flashmail import FlashmailClient

__all__ = ['GraphClient', 'FlashmailClient']

