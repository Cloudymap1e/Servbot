from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from .agent import BrowserLikeSession
from .forms import FormParser


def _join_url(base: str, path: str) -> str:
    if not path:
        return base
    if path.startswith("http://") or path.startswith("https://"):
        return path
    # naive join
    if path.startswith("/"):
        m = re.match(r"^(https?://[^/]+)", base)
        if m:
            return m.group(1) + path
    if base.endswith("/"):
        return base + path.lstrip("/")
    return base.rsplit("/", 1)[0] + "/" + path


def register_http(
    *,
    service: str,
    website_url: str,
    mailbox_email: str,
    password: Optional[str] = None,
    username: Optional[str] = None,
    proxies: Optional[Dict[str, str]] = None,
    prefer_link: bool = True,
    timeout_seconds: int = 60,
) -> Tuple[bool, str]:
    """Attempt to perform a simple HTTP-based registration.

    Strategy:
    1) GET signup page, parse first form
    2) Fill known fields: email, username, password (if present)
    3) POST form to action, follow redirects
    4) Return (success, error_or_status)

    Email verification completion is left to the caller (browserless cannot
    solve JS challenges or CAPTCHA). This is a best-effort path for sites
    that allow basic form POST flows.
    """
    session = BrowserLikeSession(proxies=proxies, timeout=timeout_seconds)
    try:
        # basic warm up to set cookies
        session.warm_up(website_url)
        status, html_text, ctype = session.get_text(website_url)
        if status >= 400:
            return False, f"GET failed: {status}"
        form = FormParser.find_first_form(html_text)
        if not form:
            return False, "No form detected"

        # Heuristics to map common field names
        values: Dict[str, str] = {}
        name_map = {k.lower(): k for k in form.inputs.keys()}
        # email
        for cand in ("email", "email_address", "mail", "login", "username"):
            if cand in name_map:
                values[name_map[cand]] = mailbox_email
                break
        # password
        if password:
            for cand in ("password", "pass", "passwd"):
                if cand in name_map:
                    values[name_map[cand]] = password
                    break
        # username (service handle)
        if username:
            for cand in ("username", "user", "login", "handle", "screen_name"):
                if cand in name_map:
                    values[name_map[cand]] = username
                    break

        payload = form.fill(values)

        action_url = _join_url(website_url, form.action)
        p_status, p_text, p_ctype = session.post_form(action_url, payload)
        if p_status in (301, 302, 303, 307, 308):
            # requests/curl_cffi follows by default when allow_redirects=True
            # so if we still see redirect code here, treat as soft success
            return True, f"redirect:{p_status}"
        if p_status < 400:
            # naive success heuristic: look for error markers
            lowered = p_text.lower()
            if any(s in lowered for s in ("error", "invalid", "blocked", "captcha", "verify you are human")):
                return False, "Server indicates an error or challenge"
            return True, str(p_status)
        return False, f"POST failed: {p_status}"
    except Exception as e:
        return False, str(e)
    finally:
        session.close()


