"""
Generic email+OTP registration flow using selectors.

This flow navigates to entry_url, fills email/username/password, submits, waits,
fetches verification (code or link), completes verification, and returns result.
Always captures debug screenshots with red outlines via ActionHelper.
"""
from __future__ import annotations

import random
import string
import time
from dataclasses import dataclass
from typing import List, Optional, Callable

from ..engine import RegistrationFlow, RegistrationResult, ActionHelper
from ...core.models import EmailAccount


@dataclass
class FlowConfig:
    email_input: str
    # Optional pre-email button to reveal email form (e.g., "Continue with email")
    email_start_button: Optional[str] = None
    username_input: Optional[str] = None
    password_input: Optional[str] = None
    password_confirm_input: Optional[str] = None
    accept_cookies_button: Optional[str] = None
    submit_button: str = "#submit"
    otp_input: Optional[str] = None
    otp_inputs: Optional[List[str]] = None
    otp_submit_button: Optional[str] = None
    success_selector: Optional[str] = None
    pre_submit_pause_ms: int = 1500
    post_submit_wait_ms: int = 4000


def _random_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$_-"
    return "".join(random.choice(alphabet) for _ in range(length))


def _random_username(email: str) -> str:
    base = email.split("@", 1)[0]
    suffix = ''.join(random.choice(string.digits) for _ in range(4))
    return f"{base}{suffix}"


class GenericEmailCodeFlow(RegistrationFlow):
    def __init__(self, *, service_name: str, entry_url: str, config: FlowConfig):
        self.service_name = service_name
        self.entry_url = entry_url
        self.config = config

    def perform_registration(
        self,
        page,
        actions: ActionHelper,
        email_account: EmailAccount,
        fetch_verification: Callable[[str, int, bool], Optional[str]],
        timeout_sec: int,
        prefer_link: bool,
    ) -> RegistrationResult:
        # Navigate to signup page
        page.goto(self.entry_url, wait_until="domcontentloaded")
        actions.screenshot("01_open")
        # If network security block page appears, try to proceed by clicking any continue buttons if present.
        try:
            if page.locator("text=You've been blocked by network security").first.is_visible():
                # Nothing actionable here; raise for retry logic upstream
                raise RuntimeError("Blocked by network security")
        except Exception:
            pass

        # Accept cookies/banner if provided
        if self.config.accept_cookies_button:
            try:
                actions.click(self.config.accept_cookies_button, label="accept_cookies")
            except Exception:
                pass

        # Optional: click a start button to reveal email form
        if self.config.email_start_button:
            try:
                actions.click(self.config.email_start_button, label="email_start")
            except Exception:
                pass

        # Fill email (selector-first)
        try:
            actions.fill(self.config.email_input, email_account.email, label="email")
        except Exception:
            # Vision-assisted fallback
            try:
                from ..vision import VisionHelper
                vh = VisionHelper(page)
                if not vh.fill_by_label('email', email_account.email):
                    raise
            except Exception:
                raise

        # Username (optional)
        chosen_username = None
        if self.config.username_input:
            chosen_username = _random_username(email_account.email)
            try:
                actions.fill(self.config.username_input, chosen_username, label="username")
            except Exception:
                chosen_username = None

        # Password (optional)
        chosen_password = None
        if self.config.password_input:
            chosen_password = _random_password()
            actions.fill(self.config.password_input, chosen_password, label="password")
            if self.config.password_confirm_input:
                actions.fill(self.config.password_confirm_input, chosen_password, label="password_confirm")

        # Submit form
        time.sleep(self.config.pre_submit_pause_ms / 1000.0)
        try:
            actions.click(self.config.submit_button, label="submit_form")
        except Exception:
            try:
                from ..vision import VisionHelper
                vh = VisionHelper(page)
                if not vh.click_submit():
                    raise
            except Exception:
                raise
        time.sleep(self.config.post_submit_wait_ms / 1000.0)

        # Fetch verification with code-first strategy and fallback to link
        deadline = time.time() + max(1, timeout_sec)
        value = None

        # Try to fetch code first
        remaining = int(max(1, deadline - time.time()))
        try:
            value = fetch_verification(self.service_name, remaining, False)
        except Exception:
            value = None

        if not value:
            # Fallback to link
            remaining = int(max(1, deadline - time.time()))
            value = fetch_verification(self.service_name, remaining, True)
        if not value:
            raise RuntimeError("Verification not received within timeout")

        # If link, navigate to it for completion; otherwise fill OTP
        if isinstance(value, str) and (value.lower().startswith("http://") or value.lower().startswith("https://")):
            actions.screenshot("02_before_open_link")
            page.goto(value, wait_until="load")
            actions.screenshot("03_after_open_link")
        else:
            # Code path: fill OTP inputs (with vision fallback)
            code = (value or "").strip()
            filled = False
            if self.config.otp_inputs:
                for i, sel in enumerate(self.config.otp_inputs):
                    if i < len(code):
                        try:
                            actions.fill(sel, code[i], label=f"otp_digit_{i}")
                            filled = True
                        except Exception:
                            pass
                if self.config.otp_submit_button:
                    try:
                        actions.click(self.config.otp_submit_button, label="otp_submit")
                    except Exception:
                        pass
            elif self.config.otp_input:
                try:
                    actions.fill(self.config.otp_input, code, label="otp_code")
                    filled = True
                except Exception:
                    filled = False
                if self.config.otp_submit_button:
                    try:
                        actions.click(self.config.otp_submit_button, label="otp_submit")
                    except Exception:
                        pass
            if not filled:
                try:
                    from ..vision import VisionHelper
                    vh = VisionHelper(page)
                    if vh.fill_by_label('otp', code):
                        vh.click_submit()
                        filled = True
                except Exception:
                    filled = False
            if not filled:
                raise RuntimeError("OTP entry failed: no suitable selector detected")

        # Confirm success
        if self.config.success_selector:
            page.wait_for_selector(self.config.success_selector, state="visible")
            actions.screenshot("04_success_visible")
        else:
            # Fallback: wait for network to become idle
            page.wait_for_load_state("networkidle")
            actions.screenshot("04_success_networkidle")

        return RegistrationResult(
            success=True,
            service=self.service_name,
            website_url=self.entry_url,
            mailbox_email=email_account.email,
            service_username=chosen_username or email_account.email,
            service_password=chosen_password,
        )
