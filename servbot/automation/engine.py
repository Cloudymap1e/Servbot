"""
Playwright-based browser automation engine for servbot.

Provides:
- RegistrationResult dataclass to carry flow outputs and artifacts
- ActionHelper for debug-friendly interactions (screenshots with red outlines)
- RegistrationFlow ABC for implementing flows
- BrowserBot to orchestrate Playwright context, run flows, and capture cookies/storage
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from ..core.models import EmailAccount
from ..core import verification as core_verification

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception:  # pragma: no cover - handled at runtime if missing
    sync_playwright = None  # type: ignore
    PlaywrightTimeoutError = Exception  # type: ignore


@dataclass
class RegistrationResult:
    success: bool
    service: str
    website_url: Optional[str]
    mailbox_email: str
    service_username: Optional[str] = None
    service_password: Optional[str] = None
    storage_state_json: Optional[str] = None
    cookies_json: Optional[str] = None
    user_agent: Optional[str] = None
    profile_dir: Optional[str] = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    debug_dir: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)


class ActionHelper:
    """Helper to perform actions with debug screenshots and red-outline highlights."""

    def __init__(self, page, debug_dir: str, on_activity: Optional[Callable[[], None]] = None):
        self.page = page
        self.debug_dir = debug_dir
        self.artifacts: List[str] = []
        self._on_activity = on_activity
        self._ensure_dir()
        self._install_highlight_css()

    def _ensure_dir(self):
        os.makedirs(self.debug_dir, exist_ok=True)

    def _install_highlight_css(self):
        try:
            self.page.add_style_tag(content="""
                :root {
                  --servbot-highlight-color: rgba(255, 0, 0, 0.8);
                }
                .servbot-highlight {
                  outline: 4px solid var(--servbot-highlight-color) !important;
                  outline-offset: 2px !important;
                  transition: outline-color 0.2s ease-in-out;
                }
            """)
        except Exception:
            pass

    def _highlight(self, selector: str):
        try:
            # Ensure CSS exists on current document (after navigations)
            try:
                self.page.add_style_tag(content="""
                    :root {
                      --servbot-highlight-color: rgba(255, 0, 0, 0.8);
                    }
                    .servbot-highlight {
                      outline: 4px solid var(--servbot-highlight-color) !important;
                      outline-offset: 2px !important;
                      transition: outline-color 0.2s ease-in-out;
                    }
                """)
            except Exception:
                pass
            self.page.eval_on_selector(selector, "(el) => { el.classList.add('servbot-highlight'); el.scrollIntoView({behavior:'instant', block:'center'});}")
        except Exception:
            pass

    def _unhighlight(self, selector: str):
        try:
            self.page.eval_on_selector(selector, "(el) => el.classList.remove('servbot-highlight')")
        except Exception:
            pass

    def screenshot(self, label: str) -> str:
        path = os.path.join(self.debug_dir, f"{int(time.time()*1000)}_{label}.png")
        try:
            self.page.screenshot(path=path, full_page=True)
            self.artifacts.append(path)
            if self._on_activity:
                self._on_activity()
        except Exception:
            pass
        return path

    def click(self, selector: str, label: str = "click"):
        self.page.wait_for_selector(selector, state="visible")
        self._highlight(selector)
        self.screenshot(f"before_{label}")
        self.page.click(selector)
        # leave highlighted briefly for context
        self.screenshot(f"after_{label}")
        self._unhighlight(selector)
        if self._on_activity:
            self._on_activity()

    def fill(self, selector: str, value: str, label: str = "fill"):
        self.page.wait_for_selector(selector, state="visible")
        self._highlight(selector)
        self.screenshot(f"before_{label}")
        self.page.fill(selector, value)
        self.screenshot(f"after_{label}")
        self._unhighlight(selector)
        if self._on_activity:
            self._on_activity()


class RegistrationFlow:
    """Abstract registration workflow."""

    service_name: str
    entry_url: str

    def perform_registration(
        self,
        page,
        actions: ActionHelper,
        email_account: EmailAccount,
        fetch_verification: Callable[[str, int, bool], Optional[str]],
        timeout_sec: int,
        prefer_link: bool,
    ) -> RegistrationResult:  # pragma: no cover - interface
        raise NotImplementedError


class BrowserBot:
    """Orchestrates Playwright browser context and runs flows with debug artifacts."""

    def __init__(
        self,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
        default_timeout: int = 300,
        channel: Optional[str] = None,
        user_agent: Optional[str] = None,
        args: Optional[List[str]] = None,
        is_mobile: bool = False,
        has_touch: bool = False,
        locale: Optional[str] = "en-US",
        idle_timeout_sec: int = 10,
    ):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.proxy = proxy
        self.default_timeout = default_timeout
        self.channel = channel
        self.user_agent = user_agent
        self.args = args or []
        self.is_mobile = is_mobile
        self.has_touch = has_touch
        self.locale = locale
        self.idle_timeout_sec = idle_timeout_sec
        self.extra_headers: Optional[Dict[str, str]] = None
        # session debug directory
        base = os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")
        base = os.path.abspath(base)
        ts = time.strftime("%Y%m%d-%H%M%S")
        self.session_debug_dir = os.path.join(base, f"run-{ts}-{uuid.uuid4().hex[:6]}")
        os.makedirs(self.session_debug_dir, exist_ok=True)

    def _screenshot_on_error(self, page, label: str = "error") -> Optional[str]:
        try:
            path = os.path.join(self.session_debug_dir, f"{int(time.time()*1000)}_{label}.png")
            page.screenshot(path=path, full_page=True)
            return path
        except Exception:
            return None

    def _fetch_verification(self, service: str, timeout_sec: int, prefer_link: bool, mailbox_email: str) -> Optional[str]:
        try:
            return core_verification.get_verification_for_service(
                target_service=service,
                username=mailbox_email,
                timeout_seconds=timeout_sec,
                prefer_link=prefer_link,
                prefer_graph=True,
            )
        except Exception:
            return None

    def run_flow(
        self,
        *,
        flow: RegistrationFlow,
        email_account: EmailAccount,
        timeout_sec: int = 300,
        prefer_link: bool = True,
    ) -> RegistrationResult:
        if sync_playwright is None:
            return RegistrationResult(
                success=False,
                service=flow.service_name,
                website_url=flow.entry_url,
                mailbox_email=email_account.email,
                error="playwright not installed",
                debug_dir=self.session_debug_dir,
            )

        with sync_playwright() as p:
            user_dir = self.user_data_dir or tempfile.mkdtemp(prefix="servbot-profile-")
            last_activity = time.time()
            def _touch():
                nonlocal last_activity
                last_activity = time.time()
            launch_kwargs = dict(
                user_data_dir=user_dir,
                headless=self.headless,
                proxy=self.proxy,
                viewport={"width": 1280, "height": 900} if not self.is_mobile else {"width": 390, "height": 844},
                is_mobile=self.is_mobile,
                has_touch=self.has_touch,
                locale=self.locale,
                accept_downloads=True,
                user_agent=self.user_agent,
                args=self.args,
                extra_http_headers=self.extra_headers,
            )
            if self.channel:
                context = p.chromium.launch_persistent_context(channel=self.channel, **launch_kwargs)
            else:
                # Playwright's signature expects user_data_dir as first positional
                context = p.chromium.launch_persistent_context(
                    user_dir,
                    headless=self.headless,
                    proxy=self.proxy,
                    viewport={"width": 1280, "height": 900},
                    accept_downloads=True,
                    user_agent=self.user_agent,
                    args=self.args,
                )
            page = context.new_page()
            # Stealth init scripts (mask automation hints)
            try:
                page.add_init_script(
                    """
                    // webdriver
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    // chrome runtime
                    window.chrome = { runtime: {} };
                    // languages
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
                    // plugins
                    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                    // permissions
                    const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
                    if (originalQuery) {
                      window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ? Promise.resolve({ state: 'denied' }) : originalQuery(parameters)
                      );
                    }
                    // WebGL vendor/renderer
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function (parameter) {
                      if (parameter === 37445) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
                      if (parameter === 37446) return 'Intel(R) UHD Graphics'; // UNMASKED_RENDERER_WEBGL
                      return getParameter.apply(this, [parameter]);
                    };
                    // hardware
                    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
                    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                    """
                )
            except Exception:
                pass
            # Cap step timeout to 10s per user requirement
            page.set_default_timeout(10000)

            actions = ActionHelper(page, self.session_debug_dir, on_activity=_touch)

            try:
                result = flow.perform_registration(
                    page,
                    actions,
                    email_account,
                    lambda service, t, pref: self._fetch_verification(service, t, pref, email_account.email),
                    timeout_sec,
                    prefer_link,
                )
                # Capture storage/cookies/user agent
                try:
                    storage_state = context.storage_state()
                except Exception:
                    storage_state = {}
                try:
                    cookies = context.cookies()
                except Exception:
                    cookies = []
                try:
                    user_agent = page.evaluate("() => navigator.userAgent")
                except Exception:
                    user_agent = ""

                result.storage_state_json = json.dumps(storage_state)
                result.cookies_json = json.dumps(cookies)
                result.user_agent = user_agent
                result.profile_dir = user_dir
                result.debug_dir = self.session_debug_dir
                result.artifacts = actions.artifacts
                return result
            except Exception as e:
                shot = self._screenshot_on_error(page)
                return RegistrationResult(
                    success=False,
                    service=flow.service_name,
                    website_url=flow.entry_url,
                    mailbox_email=email_account.email,
                    error=str(e),
                    screenshot_path=shot,
                    debug_dir=self.session_debug_dir,
                    service_username=None,
                    service_password=None,
                )
            finally:
                try:
                    context.close()
                except Exception:
                    pass
