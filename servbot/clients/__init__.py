"""Email client implementations for supported providers (Graph-only)."""

from .graph import GraphClient
from .flashmail import FlashmailClient

__all__ = ['GraphClient', 'FlashmailClient']

