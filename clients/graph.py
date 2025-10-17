"""Microsoft Graph API email client.

Provides modern OAuth2-based email fetching via Microsoft Graph API.
"""

import datetime as dt
from typing import List, Optional

from .base import EmailClient
from ..core.models import EmailMessage
from ..parsers.email_parser import html_to_text
from ..constants import (
    GRAPH_API_BASE_URL,
    GRAPH_TOKEN_URL,
    GRAPH_API_SCOPE,
    GRAPH_API_MAX_MESSAGES,
)

try:
    import requests
except ImportError:
    requests = None  # type: ignore


class GraphClient(EmailClient):
    """Microsoft Graph API email client.
    
    Uses OAuth2 access tokens to fetch emails via Microsoft Graph API.
    More modern and reliable than IMAP for Microsoft accounts.
    
    Attributes:
        access_token: OAuth2 access token
        refresh_token: Optional OAuth2 refresh token
        client_id: Optional application client ID
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
    ):
        """Initializes Graph API client.
        
        Args:
            access_token: OAuth2 access token
            refresh_token: OAuth2 refresh token (for token renewal)
            client_id: Application client ID (for token renewal)
        """
        if not requests:
            raise RuntimeError("requests library required for Graph API client")
        
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id

    def fetch_messages(
        self,
        folder: str = "inbox",
        unseen_only: bool = True,
        since: Optional[dt.datetime] = None,
        limit: int = GRAPH_API_MAX_MESSAGES,
    ) -> List[EmailMessage]:
        """Fetches messages from Microsoft Graph API.
        
        Args:
            folder: Mail folder name (default "inbox")
            unseen_only: Only fetch unread messages
            since: Only fetch messages since this datetime
            limit: Maximum messages to fetch (max from constants)
            
        Returns:
            List of EmailMessage objects
        """
        try:
            # Build filter query
            filters = []
            if unseen_only:
                filters.append("isRead eq false")
            if since:
                since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
                filters.append(f"receivedDateTime ge {since_str}")
            
            filter_query = " and ".join(filters) if filters else None
            
            # Build request URL
            url = f"{GRAPH_API_BASE_URL}/me/mailFolders/{folder}/messages"
            params = {
                "$top": min(limit, GRAPH_API_MAX_MESSAGES),
                "$select": "id,subject,from,body,bodyPreview,receivedDateTime,isRead",
                "$orderby": "receivedDateTime desc"
            }
            if filter_query:
                params["$filter"] = filter_query
            
            response = requests.get(  # type: ignore
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            
            raw_messages = response.json().get("value", [])
            
            # Convert to EmailMessage objects
            messages = []
            for msg in raw_messages:
                from_email = msg.get("from", {}).get("emailAddress", {})
                from_addr = from_email.get("address", "")
                
                body_preview = msg.get("bodyPreview", "")
                body_html = msg.get("body", {}).get("content", "")
                body_type = msg.get("body", {}).get("contentType", "text")
                
                # Convert HTML to text if needed
                if body_html and body_type == "html":
                    body_text = html_to_text(body_html)
                else:
                    body_text = body_preview
                
                email_msg = EmailMessage(
                    message_id=str(msg.get("id", "")),
                    provider="graph",
                    mailbox="",  # Graph API doesn't expose mailbox directly
                    subject=msg.get("subject", ""),
                    from_addr=from_addr,
                    received_date=msg.get("receivedDateTime", ""),
                    body_text=body_text,
                    body_html=body_html,
                    is_read=bool(msg.get("isRead", False)),
                )
                messages.append(email_msg)
            
            return messages
        
        except Exception:
            return []

    def mark_as_read(self, message_id: str) -> bool:
        """Marks message as read via Graph API.
        
        Args:
            message_id: Message ID from Graph API
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{GRAPH_API_BASE_URL}/me/messages/{message_id}"
            response = requests.patch(  # type: ignore
                url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={"isRead": True},
                timeout=10,
            )
            response.raise_for_status()
            return True
        except Exception:
            return False

    def refresh_access_token(self) -> Optional[str]:
        """Refreshes the access token using refresh token.
        
        Returns:
            New access token or None if refresh fails
        """
        if not self.refresh_token or not self.client_id:
            return None
        
        try:
            response = requests.post(  # type: ignore
                GRAPH_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "scope": GRAPH_API_SCOPE,
                },
                timeout=10,
            )
            response.raise_for_status()
            new_token = response.json().get("access_token")
            if new_token:
                self.access_token = new_token
            return new_token
        except Exception:
            return None

    @classmethod
    def from_credentials(cls, refresh_token: str, client_id: str) -> Optional['GraphClient']:
        """Creates a GraphClient from refresh token credentials.
        
        Args:
            refresh_token: OAuth2 refresh token
            client_id: Application client ID
            
        Returns:
            GraphClient instance or None if token refresh fails
        """
        try:
            response = requests.post(  # type: ignore
                GRAPH_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "scope": GRAPH_API_SCOPE,
                },
                timeout=10,
            )
            response.raise_for_status()
            access_token = response.json().get("access_token")
            if access_token:
                return cls(access_token, refresh_token, client_id)
        except Exception:
            pass
        return None

