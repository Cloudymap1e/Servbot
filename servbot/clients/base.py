"""Base email client interface.

Defines the abstract interface that all email clients must implement.
"""

import datetime as dt
from abc import ABC, abstractmethod
from typing import List, Optional

from ..core.models import EmailMessage


class EmailClient(ABC):
    """Abstract base class for email clients.
    
    All email clients (IMAP, Graph API, etc.) should inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    def fetch_messages(
        self,
        folder: str = "INBOX",
        unseen_only: bool = True,
        since: Optional[dt.datetime] = None,
        limit: int = 200,
    ) -> List[EmailMessage]:
        """Fetches email messages from the server.
        
        Args:
            folder: Mail folder to fetch from
            unseen_only: Only fetch unread messages
            since: Only fetch messages since this datetime
            limit: Maximum number of messages to fetch
            
        Returns:
            List of EmailMessage objects
        """
        pass

    @abstractmethod
    def mark_as_read(self, message_id: str) -> bool:
        """Marks a message as read.
        
        Args:
            message_id: Message identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass

