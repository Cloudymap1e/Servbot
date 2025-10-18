"""Flashmail (Shanyouxiang) API client.

Provides account provisioning via Flashmail/Shanyouxiang service.
Base URL: https://zizhu.shanyouxiang.com/
"""

import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..core.models import EmailAccount
from ..constants import (
    FLASHMAIL_BASE_URL,
    FLASHMAIL_MIN_QUANTITY,
    FLASHMAIL_MAX_QUANTITY,
    FLASHMAIL_DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
)

try:
    import requests
except ImportError:
    requests = None  # type: ignore

BASE_URL = FLASHMAIL_BASE_URL


def _http_get(path: str, params: Optional[Dict[str, str]] = None, timeout: int = FLASHMAIL_DEFAULT_TIMEOUT) -> Tuple[int, str, Dict[str, str]]:
    """Performs HTTP GET request.
    
    Args:
        path: URL path
        params: Query parameters
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (status_code, response_body, headers)
    """
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    
    # Try requests first
    if requests:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)  # type: ignore
            return (
                response.status_code,
                response.text or "",
                {k.lower(): v for k, v in response.headers.items()},
            )
        except Exception:
            pass
    
    # Fallback to urllib
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout) as resp:  # type: ignore
        status = getattr(resp, "status", 200)
        body = resp.read().decode("utf-8", errors="replace")
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        return status, body, hdrs


class FlashmailClient:
    """Flashmail API client for provisioning email accounts.
    
    Attributes:
        card: API key for Flashmail service
    """

    def __init__(self, card: str):
        """Initializes Flashmail client.
        
        Args:
            card: API key/card for Flashmail service
        """
        if not card:
            raise ValueError("card parameter is required")
        self.card = card

    def get_inventory(self) -> Dict[str, int]:
        """Queries available account inventory.
        
        Returns:
            Dict with keys "hotmail" and "outlook" containing counts
            
        Raises:
            RuntimeError: If inventory request fails
        """
        status, body, _ = _http_get("/kucun")
        if status != 200:
            raise RuntimeError(f"Inventory request failed with status {status}")
        
        try:
            data = json.loads(body)
            return {
                "hotmail": int(data.get("hotmail", 0)),
                "outlook": int(data.get("outlook", 0)),
            }
        except Exception:
            # Parse simple text format as fallback
            result = {"hotmail": 0, "outlook": 0}
            for line in body.splitlines():
                if "hotmail" in line:
                    try:
                        result["hotmail"] = int("".join(c for c in line if c.isdigit()))
                    except Exception:
                        pass
                if "outlook" in line:
                    try:
                        result["outlook"] = int("".join(c for c in line if c.isdigit()))
                    except Exception:
                        pass
            return result

    def get_balance(self) -> int:
        """Queries remaining account credits.
        
        Returns:
            Number of remaining credits
            
        Raises:
            RuntimeError: If balance request fails
        """
        status, body, _ = _http_get("/yue", params={"card": self.card})
        if status != 200:
            raise RuntimeError(f"Balance request failed with status {status}")
        
        try:
            data = json.loads(body)
            return int(data.get("num", 0))
        except Exception:
            # Extract digits as fallback
            digits = "".join(c for c in body if c.isdigit())
            return int(digits) if digits else 0

    def fetch_accounts(self, quantity: int, account_type: str = "outlook") -> List[EmailAccount]:
        """Fetches email accounts from Flashmail.
        
        Args:
            quantity: Number of accounts to fetch (1-2000)
            account_type: Type of account ("outlook" or "hotmail")
            
        Returns:
            List of EmailAccount objects
            
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If fetch request fails
        """
        if account_type not in {"outlook", "hotmail"}:
            raise ValueError("account_type must be 'outlook' or 'hotmail'")
        if not (FLASHMAIL_MIN_QUANTITY <= quantity <= FLASHMAIL_MAX_QUANTITY):
            raise ValueError(f"quantity must be between {FLASHMAIL_MIN_QUANTITY} and {FLASHMAIL_MAX_QUANTITY}")
        
        status, body, _ = _http_get(
            "/huoqu",
            params={
                "card": self.card,
                "shuliang": str(quantity),
                "leixing": account_type,
            },
            timeout=60,
        )
        
        if status != 200:
            raise RuntimeError(f"Fetch accounts failed with status {status}")
        
        accounts: List[EmailAccount] = []
        
        # Try JSON parsing first
        try:
            data = json.loads(body)
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    email = item.get("email") or item.get("username") or ""
                    password = item.get("password") or item.get("pass") or ""
                    rt = item.get("refresh_token") or item.get("refreshToken")
                    cid = item.get("client_id") or item.get("clientId")
                    if email and password:
                        accounts.append(
                            EmailAccount(
                                email=email,
                                password=password,
                                account_type=account_type,
                                source="flashmail",
                                card=self.card,
                                refresh_token=rt,
                                client_id=cid,
                            )
                        )
            elif isinstance(data, dict) and "accounts" in data:
                for item in data.get("accounts", []):
                    email = item.get("email")
                    password = item.get("password")
                    rt = item.get("refresh_token") or item.get("refreshToken")
                    cid = item.get("client_id") or item.get("clientId")
                    if email and password:
                        accounts.append(
                            EmailAccount(
                                email=email,
                                password=password,
                                account_type=account_type,
                                source="flashmail",
                                card=self.card,
                                refresh_token=rt,
                                client_id=cid,
                            )
                        )
            
            if accounts:
                return accounts
        except Exception:
            pass
        
        # Fallback: parse plain text format "email----password"
        for line in body.splitlines():
            line = line.strip()
            if not line or "@" not in line:
                continue
            
            # Try different separators
            parts = []
            if "----" in line:
                parts = line.split("----", 1)
            elif ":" in line:
                parts = line.split(":", 1)
            elif "," in line:
                parts = line.split(",", 1)
            
            if len(parts) >= 2:
                email = parts[0].strip()
                password = parts[1].strip()
                rt = parts[2].strip() if len(parts) >= 3 else None
                cid = parts[3].strip() if len(parts) >= 4 else None
                if email and password:
                    accounts.append(
                        EmailAccount(
                            email=email,
                            password=password,
                            account_type=account_type,
                            source="flashmail",
                            card=self.card,
                            refresh_token=rt,
                            client_id=cid,
                        )
                    )
        
        if not accounts:
            raise RuntimeError("No accounts parsed from response")
        
        return accounts

    @staticmethod
    def infer_imap_server(email: str) -> str:
        """Infers IMAP server address from email domain.
        
        For Flashmail accounts, MUST use imap.shanyouxiang.com proxy!
        This is Flashmail's IMAP proxy that handles OAuth and Microsoft restrictions.
        
        According to Flashmail docs:
        - IMAP address: imap.shanyouxiang.com
        - Port 993 (SSL) or Port 143 (no SSL)
        
        Args:
            email: Email address
            
        Returns:
            IMAP server address (imap.shanyouxiang.com for all Flashmail accounts)
        """
        # ALL Flashmail accounts (outlook/hotmail/live) use Flashmail proxy
        return "imap.shanyouxiang.com"

