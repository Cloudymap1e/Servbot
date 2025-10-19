"""
Unit test: BrowserBot orchestration captures storage state, cookies, user agent,
sets debug directory, and propagates artifacts.
"""
from __future__ import annotations

import json
import types
from pathlib import Path

import builtins
import importlib
import sys

import pytest

from servbot.automation.engine import BrowserBot, RegistrationFlow, RegistrationResult, ActionHelper
from servbot.core.models import EmailAccount


class FakePage:
    def __init__(self):
        self._ua = "TestAgent/1.0"
        self.screenshots = []

    def set_default_timeout(self, ms: int):
        return None

    def add_style_tag(self, **kwargs):
        return None

    def eval_on_selector(self, selector, fnstr):
        return None

    def screenshot(self, path: str, full_page: bool = False):
        self.screenshots.append(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"fakepng")

    def wait_for_selector(self, selector, state="visible"):
        return None

    def click(self, selector):
        return None

    def fill(self, selector, value):
        return None

    def evaluate(self, script):
        return self._ua

    def goto(self, url, wait_until="load"):
        return None

    def wait_for_load_state(self, state):
        return None


class FakeContext:
    def __init__(self):
        self._page = FakePage()

    def new_page(self):
        return self._page

    def storage_state(self):
        return {"cookies": [{"name": "a", "value": "b"}]}

    def cookies(self):
        return [{"name": "a", "value": "b"}]

    def close(self):
        return None


class FakeBrowserModule:
    def __init__(self):
        self._context = FakeContext()

    def chromium(self):
        raise NotImplementedError


class FakeSyncPlaywright:
    def __init__(self):
        self._context = FakeContext()

    def __enter__(self):
        class _P:
            def __init__(self, ctx):
                self._ctx = ctx

            def chromium(self):
                return self

            def launch_persistent_context(self, user_dir, headless=True, proxy=None, viewport=None, accept_downloads=True):
                return self._ctx

        return _P(self._context)

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyFlow(RegistrationFlow):
    def __init__(self):
        self.service_name = "DemoService"
        self.entry_url = "https://example.com/signup"

    def perform_registration(self, page, actions: ActionHelper, email_account: EmailAccount, fetch_verification, timeout_sec: int, prefer_link: bool) -> RegistrationResult:
        # simulate interactions
        actions.screenshot("initial")
        return RegistrationResult(
            success=True,
            service=self.service_name,
            website_url=self.entry_url,
            mailbox_email=email_account.email,
            service_username=email_account.email,
            service_password=None,
        )


def test_browserbot_captures_artifacts(monkeypatch, tmp_path):
    # Monkeypatch sync_playwright in the module
    import servbot.automation.engine as engine

    monkeypatch.setattr(engine, "sync_playwright", lambda: FakeSyncPlaywright())

    bot = BrowserBot(headless=True, user_data_dir=str(tmp_path / "profile"), default_timeout=5)
    flow = DummyFlow()
    acc = EmailAccount(email="user@example.com", password="x")

    result = bot.run_flow(flow=flow, email_account=acc, timeout_sec=5, prefer_link=True)

    assert result.success is True
    assert result.cookies_json
    assert result.storage_state_json
    cookies = json.loads(result.cookies_json)
    assert isinstance(cookies, list)
    assert result.user_agent == "TestAgent/1.0"
    assert result.debug_dir and Path(result.debug_dir).exists()
    assert any(Path(a).exists() for a in (result.artifacts or []))
