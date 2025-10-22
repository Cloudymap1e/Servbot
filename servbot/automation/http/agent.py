from __future__ import annotations

import contextlib
import random
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse


class BrowserLikeSession:
    """HTTP session that mimics a desktop Chrome browser.

    Uses curl_cffi (TLS fingerprinting) when available; falls back to requests.
    Supports rotating JA3/ClientHello presets and integrates with requests-style
    proxy mappings (http/https).
    """

    def __init__(
        self,
        *,
        proxies: Optional[Dict[str, str]] = None,
        timeout: int = 25,
        user_agent: Optional[str] = None,
        accept_language: str = "en-US,en;q=0.9",
        referer: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._use_curl, self._http = self._init_backend()
        self.timeout = timeout
        self.user_agent = (
            user_agent
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        self.accept_language = accept_language
        self.referer = referer
        self.session = self._http.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": self.accept_language,
                "Accept-Encoding": "gzip, deflate, br",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                # Client Hints (static defaults; servers may ignore unless requested)
                "sec-ch-ua": '"Chromium";v="124", "Not(A:Brand";v="24", "Google Chrome";v="124"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
        )
        if headers:
            self.session.headers.update(headers)
        if referer:
            self.session.headers["Referer"] = referer
        if proxies:
            self.session.proxies.update(proxies)

        # curl_cffi-specific options
        self._impersonate = None
        if self._use_curl:
            # cycle a few realistic Chrome impersonations
            self._impersonate = random.choice([
                "chrome124",
                "chrome123",
                "chrome120",
            ])

    @staticmethod
    def _init_backend():
        with contextlib.suppress(Exception):
            import curl_cffi.requests as curl_requests  # type: ignore

            return True, curl_requests
        import requests  # type: ignore

        return False, requests

    def _request(self, method: str, url: str, **kwargs):
        # Merge timeouts and curl_cffi impersonation
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        if self._use_curl and self._impersonate:
            kwargs.setdefault("impersonate", self._impersonate)
        # Ensure we do not auto-redirect across origins too aggressively; keep cookies
        if "allow_redirects" not in kwargs:
            kwargs["allow_redirects"] = True
        # Default Origin/Referer for POST
        if method.upper() == "POST":
            hdrs = kwargs.setdefault("headers", {})
            if "Origin" not in hdrs:
                o = urlparse(url)
                if o.scheme and o.netloc:
                    hdrs["Origin"] = f"{o.scheme}://{o.netloc}"
            if "Referer" not in hdrs and self.referer:
                hdrs["Referer"] = self.referer
        # Random small delay to mimic user pacing
        time.sleep(random.uniform(0.25, 0.9))
        resp = self.session.request(method.upper(), url, **kwargs)
        # Update referer to last visited URL
        with contextlib.suppress(Exception):
            self.referer = getattr(resp, "url", self.referer)
        return resp

    def get(self, url: str, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url: str, data=None, json=None, **kwargs):
        return self._request("POST", url, data=data, json=json, **kwargs)

    def head(self, url: str, **kwargs):
        return self._request("HEAD", url, **kwargs)

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.session.close()

    # Convenience helpers
    def get_text(self, url: str) -> Tuple[int, str, str]:
        r = self.get(url)
        ct = r.headers.get("Content-Type", "")
        return r.status_code, r.text, ct

    def post_form(self, url: str, form: Dict[str, str]) -> Tuple[int, str, str]:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = self.post(url, data=form, headers=headers)
        ct = r.headers.get("Content-Type", "")
        return r.status_code, r.text, ct

    def warm_up(self, base_url: str) -> None:
        """Visit base_url to establish cookies and realistic referer."""
        try:
            self.get(base_url)
        except Exception:
            return


