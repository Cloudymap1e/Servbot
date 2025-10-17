"""Core verification code extraction logic.

Provides high-level functions for fetching and processing verification codes
from various email sources.
"""

import datetime as dt
import time
from typing import List, Optional

from .models import Verification, EmailMessage
from ..clients import IMAPClient, GraphClient
from ..parsers import (
    parse_verification_codes,
    parse_verification_links,
    identify_service,
    canonical_service_name,
    services_equal,
)
from ..parsers.code_parser import visit_verification_link
from ..data import save_message, save_verification
from ..config import load_graph_account
from ..constants import (
    DEFAULT_IMAP_PORT,
    DEFAULT_IMAP_SSL,
    DEFAULT_IMAP_FOLDER,
    DEFAULT_MESSAGE_LIMIT,
    DEFAULT_POLL_TIMEOUT_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    MIN_POLL_INTERVAL_SECONDS,
    GRAPH_API_MAX_MESSAGES,
)


def _process_email_for_verifications(
    msg: EmailMessage,
    use_ai: bool = True,
) -> List[Verification]:
    """Processes an email message to extract verifications.
    
    Args:
        msg: Email message to process
        use_ai: Whether to use AI fallback
        
    Returns:
        List of Verification objects found in the message
    """
    results: List[Verification] = []
    
    # Combine plain and HTML text
    body_text = f"{msg.body_text}\n\n{msg.body_html}".strip()
    
    # Extract codes
    codes = parse_verification_codes(
        body_text,
        email_subject=msg.subject,
        email_body=body_text,
        from_addr=msg.from_addr,
        use_ai_fallback=use_ai,
    )
    
    # Also check subject line
    if not codes:
        codes = parse_verification_codes(
            msg.subject,
            email_subject=msg.subject,
            from_addr=msg.from_addr,
            use_ai_fallback=False,
        )
    
    # Extract links
    links = parse_verification_links(body_text, email_subject=msg.subject)
    
    if not codes and not links:
        return results
    
    # Identify service
    service = identify_service(
        msg.from_addr,
        msg.subject,
        body_text,
        use_ai_fallback=use_ai,
    )
    
    # Create Verification objects
    for code in codes:
        results.append(
            Verification(
                service=service,
                code=code,
                subject=msg.subject,
                from_addr=msg.from_addr,
                date=msg.received_date,
                is_link=False,
            )
        )
    
    for link in links:
        results.append(
            Verification(
                service=service,
                code=link,
                subject=msg.subject,
                from_addr=msg.from_addr,
                date=msg.received_date,
                is_link=True,
            )
        )
    
    return results


def _save_message_and_verifications(
    msg: EmailMessage,
    verifications: List[Verification],
) -> None:
    """Persists message and verifications to database.
    
    Args:
        msg: Email message
        verifications: List of verifications found
    """
    try:
        # Save message
        msg_id = save_message(
            mailbox=msg.mailbox,
            provider=msg.provider,
            provider_msg_id=msg.message_id,
            subject=msg.subject,
            from_addr=msg.from_addr,
            received_date=msg.received_date,
            body_text=msg.body_text,
            body_html=msg.body_html,
            is_read=msg.is_read,
            service=verifications[0].service if verifications else "",
        )
        
        # Save verifications
        if msg_id:
            for v in verifications:
                save_verification(
                    message_id=msg_id,
                    service=v.service,
                    value=v.code,
                    is_link=v.is_link,
                )
    except Exception:
        pass  # Don't fail if database save fails


def fetch_verification_codes(
    imap_server: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: int = DEFAULT_IMAP_PORT,
    ssl: bool = DEFAULT_IMAP_SSL,
    folder: str = DEFAULT_IMAP_FOLDER,
    unseen_only: bool = True,
    since: Optional[dt.datetime] = None,
    mark_seen: bool = False,
    limit: int = DEFAULT_MESSAGE_LIMIT,
    prefer_graph: bool = True,
    use_ai: bool = True,
) -> List[Verification]:
    """Fetches verification codes from email.
    
    Automatically tries the best available method (Graph API or IMAP).
    
    Args:
        imap_server: IMAP server address
        username: Email username (or full Graph credential string)
        password: Email password (or part of Graph credential string)
        port: IMAP port (default 993)
        ssl: Use SSL for IMAP
        folder: Mail folder name
        unseen_only: Only fetch unread messages
        since: Only fetch messages since this datetime
        mark_seen: Mark messages as read after processing
        limit: Maximum messages to fetch
        prefer_graph: Try Graph API first if available
        use_ai: Use AI fallback for parsing
        
    Returns:
        List of Verification objects, deduplicated and sorted by newest first
    """
    results: List[Verification] = []
    messages: List[EmailMessage] = []
    
    # Try Graph API first if preferred
    if prefer_graph:
        graph_client = None
        
        # First, try to get Graph credentials from the loaded account config
        try:
            graph_creds = load_graph_account()
            if graph_creds:
                # Check if username matches the loaded account
                if not username or username == graph_creds.get('email'):
                    graph_client = GraphClient.from_credentials(
                        graph_creds['refresh_token'],
                        graph_creds['client_id'],
                    )
        except Exception:
            pass
        
        # If we have a Graph client, use it
        if graph_client:
            try:
                messages = graph_client.fetch_messages(
                    folder=folder.lower(),
                    unseen_only=unseen_only,
                    since=since,
                    limit=min(limit, GRAPH_API_MAX_MESSAGES),
                )
                
                # Process messages
                for msg in messages:
                    verifs = _process_email_for_verifications(msg, use_ai)
                    if verifs:
                        results.extend(verifs)
                        _save_message_and_verifications(msg, verifs)
                        
                        if mark_seen:
                            graph_client.mark_as_read(msg.message_id)
                
                if results:
                    return _deduplicate_verifications(results)
            except Exception:
                pass  # Fall through to IMAP
    
    # Try IMAP
    if username and password and imap_server:
        try:
            client = IMAPClient(imap_server, username, password, port, ssl)
            messages = client.fetch_messages(
                folder=folder,
                unseen_only=unseen_only,
                since=since,
                limit=limit,
            )
            
            # Process messages
            for msg in messages:
                verifs = _process_email_for_verifications(msg, use_ai)
                if verifs:
                    results.extend(verifs)
                    _save_message_and_verifications(msg, verifs)
                    
                    if mark_seen:
                        client.mark_as_read(msg.message_id)
        
        except Exception:
            pass
    
    return _deduplicate_verifications(results)


def get_verification_for_service(
    target_service: str,
    imap_server: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: int = DEFAULT_IMAP_PORT,
    ssl: bool = DEFAULT_IMAP_SSL,
    folder: str = DEFAULT_IMAP_FOLDER,
    unseen_only: bool = True,
    timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
    prefer_link: bool = True,
    prefer_graph: bool = True,
) -> Optional[str]:
    """Fetches verification code/link for a specific service.
    
    Polls for verification until found or timeout is reached.
    
    Args:
        target_service: Service to find verification for
        imap_server: IMAP server address
        username: Email username
        password: Email password
        port: IMAP port
        ssl: Use SSL
        folder: Mail folder
        unseen_only: Only fetch unread messages
        timeout_seconds: How long to poll for verification
        poll_interval_seconds: Seconds between poll attempts
        prefer_link: Prefer verification links over codes
        prefer_graph: Try Graph API first
        
    Returns:
        Verification code/link or None if not found within timeout
    """
    canonical = canonical_service_name(target_service)
    deadline = dt.datetime.utcnow() + dt.timedelta(seconds=max(0, timeout_seconds))
    
    while True:
        verifications = fetch_verification_codes(
            imap_server=imap_server,
            username=username,
            password=password,
            port=port,
            ssl=ssl,
            folder=folder,
            unseen_only=unseen_only,
            limit=100,
            prefer_graph=prefer_graph,
        )
        
        # Find matching service
        candidates = [
            v for v in verifications
            if services_equal(v.service, canonical)
        ]
        
        if candidates:
            # Prefer links if requested
            if prefer_link:
                for v in candidates:
                    if v.is_link:
                        # Visit the link
                        visit_verification_link(v.code)
                        return v.code
            
            # Return first match
            return candidates[0].code
        
        # Check timeout
        if dt.datetime.utcnow() >= deadline:
            return None
        
        # Wait before next poll
        time.sleep(max(MIN_POLL_INTERVAL_SECONDS, poll_interval_seconds))


def get_latest_verification(
    target_service: str,
    imap_server: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    port: int = DEFAULT_IMAP_PORT,
    ssl: bool = DEFAULT_IMAP_SSL,
    folder: str = DEFAULT_IMAP_FOLDER,
    prefer_graph: bool = True,
) -> Optional[Verification]:
    """Gets the latest verification for a service (single fetch, no polling).
    
    Args:
        target_service: Service to find verification for
        imap_server: IMAP server address
        username: Email username
        password: Email password
        port: IMAP port
        ssl: Use SSL
        folder: Mail folder
        prefer_graph: Try Graph API first
        
    Returns:
        Verification object or None if not found
    """
    canonical = canonical_service_name(target_service)
    
    verifications = fetch_verification_codes(
        imap_server=imap_server,
        username=username,
        password=password,
        port=port,
        ssl=ssl,
        folder=folder,
        unseen_only=True,
        limit=DEFAULT_MESSAGE_LIMIT,
        prefer_graph=prefer_graph,
    )
    
    # Find first matching service
    for v in verifications:
        if services_equal(v.service, canonical):
            return v
    
    return None


def _deduplicate_verifications(verifs: List[Verification]) -> List[Verification]:
    """Deduplicates verifications by (service, code) while preserving newest first.
    
    Args:
        verifs: List of verifications
        
    Returns:
        Deduplicated list sorted by date (newest first)
    """
    # Sort by date descending
    sorted_verifs = sorted(verifs, key=lambda v: v.date or '', reverse=True)
    
    # Deduplicate by (service, code)
    seen = set()
    unique: List[Verification] = []
    
    for v in sorted_verifs:
        key = (v.service, v.code)
        if key not in seen:
            seen.add(key)
            unique.append(v)
    
    return unique

