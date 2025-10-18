"""Microsoft Graph API email client.

Provides modern OAuth2-based email fetching via Microsoft Graph API.

NOTE: This is Microsoft's Graph API (https://graph.microsoft.com),
not to be confused with other graph APIs. It uses OAuth2 refresh tokens
to obtain access tokens for API requests.

For Outlook/Hotmail/Office 365 accounts, this is preferred over IMAP
for better reliability and modern authentication support.
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
        mailbox: Email address of the mailbox being accessed
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        mailbox: Optional[str] = None,
    ):
        """Initializes Graph API client.
        
        Args:
            access_token: OAuth2 access token
            refresh_token: OAuth2 refresh token (for token renewal)
            client_id: Application client ID (for token renewal)
            mailbox: Email address of the mailbox (for message tracking)
        """
        if not requests:
            raise RuntimeError("requests library required for Graph API client")
        
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.mailbox = mailbox or ""

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
        
        Raises:
            RuntimeError: If mailbox is not set or API request fails after retry
        """
        # Validate mailbox is set
        if not self.mailbox:
            raise RuntimeError(
                "Mailbox not set for GraphClient. Messages cannot be tracked without mailbox email address. "
                "Initialize GraphClient with mailbox parameter or use from_credentials() with mailbox."
            )
        
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
            
            # First attempt
            response = requests.get(  # type: ignore
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params,
                timeout=30,
            )
            
            # Handle 401 Unauthorized - token may be expired
            if response.status_code == 401:
                # Try to refresh token
                new_token = self.refresh_access_token()
                if new_token:
                    # Retry with new token
                    response = requests.get(  # type: ignore
                        url,
                        headers={"Authorization": f"Bearer {new_token}"},
                        params=params,
                        timeout=30,
                    )
            
            # Handle errors
            if response.status_code == 403:
                raise RuntimeError(
                    f"Insufficient permissions to access mailbox '{self.mailbox}'. "
                    "Required scopes: Mail.Read or Mail.ReadWrite"
                )
            elif response.status_code == 404:
                raise RuntimeError(
                    f"Mailbox or folder not found: mailbox='{self.mailbox}', folder='{folder}'"
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
                    mailbox=self.mailbox,  # Use client's mailbox
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
        
        Attempts to refresh the OAuth access token using the stored refresh token.
        If successful, updates the client's access_token and optionally persists
        to database if mailbox is known.
        
        Microsoft Graph may rotate refresh tokens - if a new refresh_token is
        returned, it will be stored and the old one should be discarded.
        
        Returns:
            New access token or None if refresh fails
        """
        if not self.refresh_token or not self.client_id:
            return None
        
        try:
            # Per Microsoft identity platform v2.0, the "scope" parameter is optional on
            # refresh_token redemption. If omitted, the originally granted scopes are reused.
            # Avoid using ".default" here (reserved for client credentials/app perms).
            response = requests.post(  # type: ignore
                GRAPH_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")  # May be rotated
            
            if new_access_token:
                self.access_token = new_access_token
                
                # If refresh token was rotated, update it
                if new_refresh_token and new_refresh_token != self.refresh_token:
                    self.refresh_token = new_refresh_token
                    
                    # Persist to database if mailbox is known
                    if self.mailbox:
                        try:
                            self._persist_tokens_to_db(new_access_token, new_refresh_token)
                        except Exception:
                            # Don't fail refresh if persistence fails
                            pass
            
            return new_access_token
        except Exception:
            return None
    
    def _persist_tokens_to_db(self, access_token: str, refresh_token: str) -> None:
        """Persists refreshed tokens to database.
        
        Args:
            access_token: New access token (not stored, just for future use)
            refresh_token: New or rotated refresh token to persist
        
        Note: Access tokens are short-lived and not stored. Only refresh token
        and client_id are persisted for future token refresh operations.
        """
        try:
            # Import here to avoid circular dependency
            from ..data.database import upsert_account
            
            # Update only the refresh_token, keeping other fields unchanged
            # Use update_only_if_provided=True to preserve other fields
            upsert_account(
                email=self.mailbox,
                refresh_token=refresh_token,
                client_id=self.client_id,
                update_only_if_provided=True,  # Don't clear other fields
            )
        except Exception:
            # Silently fail - token refresh itself succeeded
            # The in-memory token is still valid for this session
            pass

    @classmethod
    def from_credentials(cls, refresh_token: str, client_id: str, mailbox: Optional[str] = None) -> Optional['GraphClient']:
        """Creates a GraphClient from refresh token credentials.
        
        Args:
            refresh_token: OAuth2 refresh token
            client_id: Application client ID
            mailbox: Email address of the mailbox (optional)
            
        Returns:
            GraphClient instance or None if token refresh fails
        """
        try:
            # For delegated flows, omit "scope" during refresh so previously granted
            # scopes are reused. Do NOT use ".default" here.
            response = requests.post(  # type: ignore
                GRAPH_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                timeout=10,
            )
            response.raise_for_status()
            access_token = response.json().get("access_token")
            if access_token:
                return cls(access_token, refresh_token, client_id, mailbox)
        except Exception:
            pass
        return None

