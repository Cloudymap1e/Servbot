"""Minimal IMAP client stub for tests.

This module provides a thin wrapper class so tests can import and/or mock
`servbot.clients.imap.IMAPClient`. It is not used in production paths.
"""
from __future__ import annotations

from typing import List


class IMAPClient:
    """Minimal IMAP client interface used in tests."""

    def __init__(
        self,
        *,
        server: str,
        username: str,
        password: str,
        port: int = 993,
        use_ssl: bool = True,
    ) -> None:
        self.server = server
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl

    def fetch_messages(
        self,
        *,
        folder: str = "INBOX",
        unseen_only: bool = True,
        limit: int = 50,
    ) -> List:
        """Placeholder; real functionality is mocked in tests."""
        raise NotImplementedError("IMAPClient.fetch_messages is a test stub; mock it in tests")


