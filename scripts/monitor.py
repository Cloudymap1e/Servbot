#!/usr/bin/env python
"""Email monitoring service with multi-threaded continuous polling.

This module provides a background service that continuously monitors all email
accounts in the database for new messages and automatically extracts verification
codes and links in real-time.

Key Features:
- Multi-threaded: One worker thread per email account for parallel monitoring
- Configurable interval: Default 10 seconds between checks
- Unread-only mode: Process only unread messages by default
- Real-time output: Print new messages and verifications to console as they arrive
- Thread-safe: Each thread has its own database session
- Graceful shutdown: Handles stop signals and cleans up resources properly

Usage:
    from servbot.monitor import EmailMonitor
    
    monitor = EmailMonitor(interval=10, unread_only=True)
    monitor.start()
    
    try:
        monitor.join()  # Block until stopped
    except KeyboardInterrupt:
        monitor.stop()
        monitor.join(timeout=5)
"""

import datetime as dt
import logging
import threading
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .data.database import get_accounts
from .core.verification import fetch_verification_codes, _process_email_for_verifications, _save_message_and_verifications
from .core.models import EmailMessage


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


@dataclass
class AccountStats:
    """Statistics for a single monitored account."""
    email: str
    total_polls: int = 0
    messages_fetched: int = 0
    messages_processed: int = 0
    verifications_found: int = 0
    errors: int = 0
    last_poll_time: Optional[dt.datetime] = None
    last_error: Optional[str] = None


@dataclass
class MonitorStats:
    """Overall monitoring statistics."""
    start_time: dt.datetime = field(default_factory=dt.datetime.now)
    accounts_monitored: int = 0
    total_polls: int = 0
    total_messages_fetched: int = 0
    total_messages_processed: int = 0
    total_verifications_found: int = 0
    total_errors: int = 0
    account_stats: Dict[str, AccountStats] = field(default_factory=dict)


class EmailMonitor:
    """Multi-threaded email monitoring service.
    
    Continuously polls all email accounts in the database for new messages,
    extracts verification codes and links, and saves them to the database
    while providing real-time console output.
    
    Attributes:
        interval: Seconds between each poll (default: 10)
        unread_only: Only process unread messages (default: True)
        account_filter: Optional list of email addresses to monitor (default: all)
        prefer_graph: Try Microsoft Graph API first when available (default: True)
        use_ai: Enable AI fallback for parsing (default: True)
    """
    
    def __init__(
        self,
        interval: int = 10,
        unread_only: bool = True,
        account_filter: Optional[List[str]] = None,
        prefer_graph: bool = True,
        use_ai: bool = True,
    ):
        """Initialize the email monitor.
        
        Args:
            interval: Seconds between polls (default: 10)
            unread_only: Only fetch unread messages (default: True)
            account_filter: List of email addresses to monitor, or None for all
            prefer_graph: Try Graph API first when available (default: True)
            use_ai: Use AI fallback for parsing (default: True)
        """
        self.interval = max(1, interval)  # Minimum 1 second
        self.unread_only = unread_only
        self.account_filter = [a.lower() for a in account_filter] if account_filter else None
        self.prefer_graph = prefer_graph
        self.use_ai = use_ai
        
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []
        self._print_lock = threading.Lock()
        self._stats = MonitorStats()
        self._stats_lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
    
    def start(self) -> None:
        """Start monitoring all accounts in separate threads."""
        if self._threads:
            raise RuntimeError("Monitor is already running")
        
        # Load accounts from database
        accounts = get_accounts()
        
        # Apply filter if specified
        if self.account_filter:
            accounts = [
                acc for acc in accounts
                if acc['email'].lower() in self.account_filter
            ]
        
        if not accounts:
            self._logger.warning("No accounts found to monitor!")
            return
        
        # Initialize stats
        with self._stats_lock:
            self._stats.accounts_monitored = len(accounts)
            for acc in accounts:
                self._stats.account_stats[acc['email']] = AccountStats(email=acc['email'])
        
        # Start one thread per account
        for account in accounts:
            thread = threading.Thread(
                target=self._monitor_account,
                args=(account,),
                daemon=True,
                name=f"Monitor-{account['email']}"
            )
            thread.start()
            self._threads.append(thread)
        
        self._print(f"🚀 Monitor started for {len(accounts)} account(s)")
        self._print(f"   Interval: {self.interval}s | Unread only: {self.unread_only} | Prefer Graph: {self.prefer_graph}")
    
    def stop(self) -> None:
        """Stop all monitoring threads."""
        if not self._threads:
            return
        
        self._print("🛑 Stopping monitor...")
        self._stop_event.set()
    
    def join(self, timeout: Optional[float] = None) -> None:
        """Wait for all monitoring threads to complete.
        
        Args:
            timeout: Maximum seconds to wait (None = wait forever)
        """
        for thread in self._threads:
            thread.join(timeout=timeout)
        
        if timeout and any(t.is_alive() for t in self._threads):
            self._logger.warning("Some threads did not stop within timeout")
    
    def is_running(self) -> bool:
        """Check if monitor is currently running.
        
        Returns:
            True if any threads are still alive
        """
        return any(t.is_alive() for t in self._threads)
    
    def get_stats(self) -> MonitorStats:
        """Get current monitoring statistics.
        
        Returns:
            Copy of current statistics
        """
        with self._stats_lock:
            # Return a copy to avoid race conditions
            import copy
            return copy.deepcopy(self._stats)
    
    def _monitor_account(self, account: Dict[str, Any]) -> None:
        """Worker thread that monitors a single email account.
        
        Args:
            account: Account dict from database
        """
        email = account['email']
        password = account.get('password', '')
        imap_server = account.get('imap_server')
        
        self._logger.info(f"[{email}] Monitoring started")
        
        while not self._stop_event.is_set():
            try:
                self._poll_account(email, password, imap_server)
            except Exception as e:
                self._record_error(email, str(e))
                self._logger.error(f"[{email}] Error: {e}", exc_info=True)
            
            # Sleep with interruptible wait
            self._stop_event.wait(self.interval)
        
        self._logger.info(f"[{email}] Monitoring stopped")
    
    def _poll_account(self, email: str, password: str, imap_server: Optional[str]) -> None:
        """Poll a single account for new messages.
        
        Args:
            email: Email address
            password: Account password
            imap_server: IMAP server address (optional)
        """
        poll_time = dt.datetime.now()
        
        # Update poll count
        with self._stats_lock:
            self._stats.total_polls += 1
            if email in self._stats.account_stats:
                self._stats.account_stats[email].total_polls += 1
                self._stats.account_stats[email].last_poll_time = poll_time
        
        self._logger.debug(f"[{email}] Checking for new messages...")
        
        try:
            # Fetch verification codes (which also fetches messages)
            verifications = fetch_verification_codes(
                imap_server=imap_server,
                username=email,
                password=password,
                unseen_only=self.unread_only,
                prefer_graph=self.prefer_graph,
                use_ai=self.use_ai,
                limit=50,  # Limit per poll
            )
            
            # Update stats
            with self._stats_lock:
                if email in self._stats.account_stats:
                    self._stats.account_stats[email].messages_fetched += len(verifications)
                    self._stats.account_stats[email].messages_processed += len(verifications)
                    self._stats.account_stats[email].verifications_found += len(verifications)
                    
                    self._stats.total_messages_fetched += len(verifications)
                    self._stats.total_messages_processed += len(verifications)
                    self._stats.total_verifications_found += len(verifications)
            
            # Print new verifications
            if verifications:
                self._print(f"\n📧 [{email}] Found {len(verifications)} verification(s):")
                for i, v in enumerate(verifications, 1):
                    v_type = "🔗 Link" if v.is_link else "🔢 Code"
                    self._print(f"   {i}. {v_type} | {v.service}")
                    self._print(f"      Value:   {v.code}")
                    self._print(f"      Subject: {v.subject}")
                    self._print(f"      From:    {v.from_addr}")
                    self._print(f"      Date:    {v.date or 'N/A'}")
            
        except Exception as e:
            raise  # Re-raise for outer error handling
    
    def _record_error(self, email: str, error_msg: str) -> None:
        """Record an error for an account.
        
        Args:
            email: Email address
            error_msg: Error message
        """
        with self._stats_lock:
            self._stats.total_errors += 1
            if email in self._stats.account_stats:
                self._stats.account_stats[email].errors += 1
                self._stats.account_stats[email].last_error = error_msg
    
    def _print(self, message: str) -> None:
        """Thread-safe console printing.
        
        Args:
            message: Message to print
        """
        with self._print_lock:
            print(message, flush=True)


def main():
    """Simple test entry point."""
    import sys
    
    print("=" * 70)
    print("EMAIL MONITOR - Test Mode")
    print("=" * 70)
    print("\nThis will monitor all accounts for 30 seconds...")
    print("Press Ctrl+C to stop early.\n")
    
    monitor = EmailMonitor(interval=10, unread_only=True)
    monitor.start()
    
    try:
        # Run for 30 seconds
        time.sleep(30)
        monitor.stop()
        monitor.join(timeout=5)
        
        # Print stats
        stats = monitor.get_stats()
        print("\n" + "=" * 70)
        print("MONITORING SUMMARY")
        print("=" * 70)
        print(f"Runtime: {(dt.datetime.now() - stats.start_time).total_seconds():.1f}s")
        print(f"Accounts: {stats.accounts_monitored}")
        print(f"Total Polls: {stats.total_polls}")
        print(f"Messages Processed: {stats.total_messages_processed}")
        print(f"Verifications Found: {stats.total_verifications_found}")
        print(f"Errors: {stats.total_errors}")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        monitor.stop()
        monitor.join(timeout=5)
        print("Monitor stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
