"""IMAP email client implementation.

Provides email fetching via IMAP protocol using either imapclient or imaplib.
"""

import datetime as dt
import email
import imaplib
import ssl as ssl_module
from typing import List, Optional

from .base import EmailClient
from ..core.models import EmailMessage
from ..parsers.email_parser import extract_text_from_message, parse_addresses
from ..constants import DEFAULT_IMAP_PORT, DEFAULT_IMAP_SSL, DEFAULT_IMAP_FOLDER

try:
    import imapclient  # type: ignore
except ImportError:
    imapclient = None  # type: ignore


def _build_ssl_context() -> ssl_module.SSLContext:
    """Builds SSL context for secure IMAP connections."""
    return ssl_module.create_default_context()


def _is_imapclient_available() -> bool:
    """Checks if imapclient library is available."""
    return imapclient is not None


class IMAPClient(EmailClient):
    """IMAP email client.
    
    Connects to IMAP servers and fetches email messages. Prefers imapclient
    library but falls back to standard imaplib if unavailable.
    
    Attributes:
        server: IMAP server address
        username: Email username
        password: Email password
        port: IMAP port (default 993 for SSL)
        use_ssl: Whether to use SSL connection
    """

    def __init__(
        self,
        server: str,
        username: str,
        password: str,
        port: int = DEFAULT_IMAP_PORT,
        use_ssl: bool = DEFAULT_IMAP_SSL,
    ):
        """Initializes IMAP client.
        
        Args:
            server: IMAP server address
            username: Email username
            password: Email password
            port: IMAP port (default from constants)
            use_ssl: Use SSL connection (default from constants)
        """
        self.server = server
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self._use_imapclient = _is_imapclient_available()
    
    def _parse_email_to_message(self, raw_msg: bytes, uid_or_num: int, folder: str) -> Optional[EmailMessage]:
        """Parses raw email bytes into EmailMessage object.
        
        Args:
            raw_msg: Raw email message bytes
            uid_or_num: UID or message number
            folder: Folder name
            
        Returns:
            EmailMessage object or None if parsing fails
        """
        try:
            msg = email.message_from_bytes(raw_msg)
        except Exception:
            return None
        
        subject = msg.get('Subject', '')
        from_header = msg.get('From', '')
        from_addrs = parse_addresses(from_header)
        from_addr = from_addrs[0] if from_addrs else ''
        date_hdr = msg.get('Date', '')
        
        plain, html = extract_text_from_message(msg)
        
        return EmailMessage(
            message_id=f"{self.username}:{folder}:{uid_or_num}",
            provider="imap",
            mailbox=self.username,
            subject=subject,
            from_addr=from_addr,
            received_date=date_hdr,
            body_text=plain,
            body_html=html,
            is_read=False,
        )

    def fetch_messages(
        self,
        folder: str = DEFAULT_IMAP_FOLDER,
        unseen_only: bool = True,
        since: Optional[dt.datetime] = None,
        limit: int = 200,
    ) -> List[EmailMessage]:
        """Fetches messages from IMAP server.
        
        Args:
            folder: Mail folder name (default "INBOX")
            unseen_only: Only fetch unread messages
            since: Only fetch messages since this datetime
            limit: Maximum messages to fetch
            
        Returns:
            List of EmailMessage objects
            
        Raises:
            RuntimeError: If IMAP connection fails
        """
        if self._use_imapclient:
            return self._fetch_with_imapclient(folder, unseen_only, since, limit)
        else:
            return self._fetch_with_imaplib(folder, unseen_only, since, limit)

    def _fetch_with_imapclient(
        self,
        folder: str,
        unseen_only: bool,
        since: Optional[dt.datetime],
        limit: int,
    ) -> List[EmailMessage]:
        """Fetches messages using imapclient library."""
        client = imapclient.IMAPClient(  # type: ignore
            self.server,
            port=self.port,
            ssl=self.use_ssl,
            use_uid=True,
            ssl_context=_build_ssl_context() if self.use_ssl else None,
        )
        client.login(self.username, self.password)
        
        try:
            client.select_folder(folder)
            
            # Build search criteria
            criteria: List = []
            if unseen_only:
                criteria.append('UNSEEN')
            if since is not None:
                criteria.extend(['SINCE', since.strftime('%d-%b-%Y')])
            if not criteria:
                criteria = ['ALL']
            
            uids = list(client.search(criteria))
            uids = sorted(uids, reverse=True)[:limit]
            
            if not uids:
                return []
            
            messages = []
            fetch_data = client.fetch(uids, [b'RFC822', b'ENVELOPE'])
            
            for uid in uids:
                data = fetch_data.get(uid, {})
                raw = data.get(b'RFC822')
                if not raw:
                    continue
                
                email_msg = self._parse_email_to_message(raw, uid, folder)
                if email_msg:
                    messages.append(email_msg)
            
            return messages
        finally:
            try:
                client.logout()
            except Exception:
                pass

    def _fetch_with_imaplib(
        self,
        folder: str,
        unseen_only: bool,
        since: Optional[dt.datetime],
        limit: int,
    ) -> List[EmailMessage]:
        """Fetches messages using standard imaplib."""
        if self.use_ssl:
            M = imaplib.IMAP4_SSL(
                self.server, self.port, ssl_context=_build_ssl_context()
            )
        else:
            M = imaplib.IMAP4(self.server, self.port)
        
        M.login(self.username, self.password)
        
        try:
            M.select(folder)
            
            # Build search criteria
            criteria = []
            if unseen_only:
                criteria.append('UNSEEN')
            if since is not None:
                criteria.extend(['SINCE', since.strftime('%d-%b-%Y')])
            if not criteria:
                criteria = ['ALL']
            
            typ, data = M.search(None, *criteria)
            if typ != 'OK' or not data or not data[0]:
                return []
            
            nums = [int(x) for x in data[0].split()]
            nums = sorted(nums, reverse=True)[:limit]
            
            messages = []
            for num in nums:
                typ, msg_data = M.fetch(str(num), '(RFC822)')
                if typ != 'OK' or not msg_data:
                    continue
                
                raw = msg_data[0][1]
                if not raw:
                    continue
                
                email_msg = self._parse_email_to_message(raw, num, folder)
                if email_msg:
                    messages.append(email_msg)
            
            return messages
        finally:
            try:
                M.logout()
            except Exception:
                pass

    def mark_as_read(self, message_id: str) -> bool:
        """Marks message as read via IMAP.
        
        Args:
            message_id: Message ID in format "username:folder:uid"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse message_id to extract UID
            parts = message_id.split(':')
            if len(parts) < 3:
                return False
            
            folder = parts[1]
            uid = parts[2]
            
            if self._use_imapclient:
                client = imapclient.IMAPClient(  # type: ignore
                    self.server,
                    port=self.port,
                    ssl=self.use_ssl,
                    use_uid=True,
                    ssl_context=_build_ssl_context() if self.use_ssl else None,
                )
                client.login(self.username, self.password)
                client.select_folder(folder)
                client.add_flags(int(uid), [imapclient.SEEN])  # type: ignore
                client.logout()
            else:
                if self.use_ssl:
                    M = imaplib.IMAP4_SSL(
                        self.server, self.port, ssl_context=_build_ssl_context()
                    )
                else:
                    M = imaplib.IMAP4(self.server, self.port)
                M.login(self.username, self.password)
                M.select(folder)
                M.store(uid, '+FLAGS', '\\Seen')
                M.logout()
            
            return True
        except Exception:
            return False

