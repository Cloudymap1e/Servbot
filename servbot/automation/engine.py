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
from urllib.parse import urlparse

from ..core.models import EmailAccount
from ..core import verification as core_verification
from .netmeter import NetworkMeter

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

    def __init__(self, page, debug_dir: str, on_activity: Optional[Callable[[], None]] = None, *, enable_screenshots: bool = True):
        self.page = page
        self.debug_dir = debug_dir
        self.artifacts: List[str] = []
        self._on_activity = on_activity
        self._enable_screenshots = enable_screenshots
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
        if not self._enable_screenshots:
            # Do not create screenshots to avoid extra disk/network overhead during measurements
            return path
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
        # Traffic controls
        traffic_profile: Optional[str] = None,  # None/off|minimal|ultra
        block_third_party: bool = False,
        allowed_domains: Optional[List[str]] = None,
        measure_network: bool = False,
        disable_debug_artifacts: bool = False,
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
        # Traffic settings
        self.traffic_profile = (traffic_profile or "off").lower()
        self.block_third_party = bool(block_third_party)
        self.allowed_domains = [d.lower() for d in (allowed_domains or [])]
        self.measure_network = bool(measure_network)
        self.disable_debug_artifacts = bool(disable_debug_artifacts)
        self._blocked_counters = {"images": 0, "fonts": 0, "media": 0, "stylesheets": 0, "third_party": 0, "analytics": 0}
        # Apply Chromium arg to disable image decoding at renderer level in minimal/ultra
        if self.traffic_profile in ("minimal", "ultra"):
            if "--blink-settings=imagesEnabled=false" not in self.args:
                self.args.append("--blink-settings=imagesEnabled=false")

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
            # Ensure Save-Data header in minimal/ultra
            if self.traffic_profile in ("minimal", "ultra"):
                self.extra_headers = self.extra_headers or {}
                self.extra_headers["Save-Data"] = "on"
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
            # Support both real Playwright (property) and test double (method)
            chromium_obj = p.chromium if not callable(getattr(p, "chromium", None)) else p.chromium()
            if self.channel:
                context = chromium_obj.launch_persistent_context(channel=self.channel, **launch_kwargs)
            else:
                # Playwright's signature expects user_data_dir as first positional
                try:
                    context = chromium_obj.launch_persistent_context(
                        user_dir,
                        headless=self.headless,
                        proxy=self.proxy,
                        viewport={"width": 1280, "height": 900},
                        accept_downloads=True,
                        user_agent=self.user_agent,
                        args=self.args,
                    )
                except TypeError:
                    # Fallback for simplified test doubles
                    context = chromium_obj.launch_persistent_context(
                        user_dir,
                        headless=self.headless,
                        proxy=self.proxy,
                    )
            page = context.new_page()
            # Ensure headers set even if context ignored launch extra headers
            try:
                if self.extra_headers:
                    context.set_extra_http_headers(self.extra_headers)
            except Exception:
                pass
            # Request routing for minimal traffic
            if self.traffic_profile in ("minimal", "ultra") or self.block_third_party:
                # Default allowlist for Reddit when not provided
                try:
                    entry_host = urlparse(getattr(flow, "entry_url", "") or "").hostname or ""
                except Exception:
                    entry_host = ""
                if self.block_third_party and not self.allowed_domains:
                    if "reddit" in entry_host:
                        self.allowed_domains = [
                            "reddit.com",
                            "redditstatic.com",
                            "redditmedia.com",
                            "redd.it",
                        ]
                    elif entry_host:
                        base = entry_host.split(".")[-2:]
                        self.allowed_domains = [".".join(base)]
                analytics_domains = {
                    "googletagmanager.com",
                    "google-analytics.com",
                    "doubleclick.net",
                    "g.doubleclick.net",
                    "sentry.io",
                    "newrelic.com",
                    "datadoghq.com",
                    "intercom.io",
                    "hotjar.com",
                    "braze.com",
                    "branch.io",
                    "amplitude.com",
                    "segment.io",
                    "mixpanel.com",
                    "facebook.net",
                    "facebook.com",
                    # Reddit first-party telemetry/reporting hosts
                    "w3-reporting.reddit.com",
                    "error-tracking.reddit.com",
                    "events.reddit.com",
                    "pixel.reddit.com",
                }
                def _host_allowed(url: str) -> bool:
                    if not self.block_third_party or not self.allowed_domains:
                        return True
                    try:
                        host = urlparse(url).hostname or ""
                    except Exception:
                        host = ""
                    host = host.lower()
                    for d in self.allowed_domains:
                        d = d.lstrip(".").lower()
                        if host.endswith(d):
                            return True
                    return False
                def _is_analytics(url: str) -> bool:
                    try:
                        host = urlparse(url).hostname or ""
                    except Exception:
                        host = ""
                    host = host.lower()
                    return any(host.endswith(d) for d in analytics_domains)
                def _route_handler(route, request):
                    try:
                        rtype = (request.resource_type or "other").lower()
                        url = request.url
                        if rtype in ("image", "font", "media", "ping"):
                            if rtype == "image":
                                self._blocked_counters["images"] += 1
                            elif rtype == "font":
                                self._blocked_counters["fonts"] += 1
                            else:
                                self._blocked_counters["media"] += 1
                            return route.abort()
                        if self.traffic_profile == "ultra" and rtype == "stylesheet":
                            self._blocked_counters["stylesheets"] += 1
                            return route.abort()
                        if not _host_allowed(url):
                            self._blocked_counters["third_party"] += 1
                            return route.abort()
                        if _is_analytics(url):
                            self._blocked_counters["analytics"] += 1
                            return route.abort()
                        return route.fallback()
                    except Exception:
                        try:
                            return route.fallback()
                        except Exception:
                            pass
                try:
                    page.route("**/*", _route_handler)
                except Exception:
                    pass
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
                # Optional traffic minimization JS stubs
                if self.traffic_profile in ("minimal", "ultra"):
                    page.add_init_script(
                        """
                        (function(){
                          try {
                            // Disable sendBeacon to avoid pings
                            Object.defineProperty(navigator, 'sendBeacon', { writable: true, value: function(){ return false; } });
                            // Block fetch/XHR to known telemetry/reporting hosts
                            const BLOCK_RE = /(?:w3-reporting\.reddit\.com|error-tracking\.reddit\.com|sentry\.io)/i;
                            const _fetch = window.fetch;
                            window.fetch = function(input, init){
                              try {
                                const url = (typeof input === 'string') ? input : (input && input.url) || '';
                                if (BLOCK_RE.test(url)) {
                                  return Promise.resolve(new Response('', {status: 204}));
                                }
                              } catch(e) {}
                              return _fetch.apply(this, arguments);
                            };
                            const _open = XMLHttpRequest.prototype.open;
                            XMLHttpRequest.prototype.open = function(method, url){
                              try {
                                if (BLOCK_RE.test(String(url))) {
                                  // Abort immediately
                                  this.abort();
                                  return;
                                }
                              } catch(e) {}
                              return _open.apply(this, arguments);
                            };
                            // Remove prefetch/preload hints dynamically
                            new MutationObserver(function(list){
                              list.forEach(function(m){
                                m.addedNodes && m.addedNodes.forEach(function(n){
                                  try {
                                    if (n && n.tagName === 'LINK'){
                                      const rel = (n.getAttribute('rel')||'').toLowerCase();
                                      if (rel === 'prefetch' || rel === 'preload' || rel === 'modulepreload'){
                                        n.parentNode && n.parentNode.removeChild(n);
                                      }
                                    }
                                  } catch(e) {}
                                });
                              });
                            }).observe(document.documentElement, {childList:true, subtree:true});
                          } catch(e) {}
                        })();
                        """
                    )
            except Exception:
                pass
            # Cap step timeout to 10s per user requirement
            page.set_default_timeout(10000)

            actions = ActionHelper(page, self.session_debug_dir, on_activity=_touch, enable_screenshots=(not self.disable_debug_artifacts))

            # Network metering
            meter = None
            net_json_path = None
            if self.measure_network:
                try:
                    meter = NetworkMeter(profile_name=self.traffic_profile, allowlist=self.allowed_domains)
                    meter.start(page)
                except Exception:
                    meter = None

            try:
                result = flow.perform_registration(
                    page,
                    actions,
                    email_account,
                    lambda service, t, pref: self._fetch_verification(service, t, pref, email_account.email),
                    timeout_sec,
                    prefer_link,
                )
                # Stop meter after flow finishes
                if meter:
                    try:
                        meter.stop()
                        meter.set_blocked_counters(self._blocked_counters)
                        # Save JSON artifact under data/network
                        net_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "network"))
                        os.makedirs(net_base, exist_ok=True)
                        net_json_path = os.path.join(net_base, f"{int(time.time()*1000)}_net_{self.traffic_profile or 'off'}.json")
                        meter.save_json(net_json_path)
                        actions.artifacts.append(net_json_path)
                    except Exception:
                        pass
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
                # Best-effort meter stop/save if an exception occurred above
                try:
                    if meter and not net_json_path:
                        try:
                            meter.stop()
                            meter.set_blocked_counters(self._blocked_counters)
                            net_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "network"))
                            os.makedirs(net_base, exist_ok=True)
                            net_json_path = os.path.join(net_base, f"{int(time.time()*1000)}_net_{self.traffic_profile or 'off'}.json")
                            meter.save_json(net_json_path)
                            actions.artifacts.append(net_json_path)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    context.close()
                except Exception:
                    pass
