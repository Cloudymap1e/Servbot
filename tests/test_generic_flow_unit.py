"""
Unit test: GenericEmailCodeFlow basic path (OTP code) using mock page/actions.
"""
from __future__ import annotations

from pathlib import Path

from servbot.automation.flows.generic import GenericEmailCodeFlow, FlowConfig
from servbot.automation.engine import ActionHelper
from servbot.core.models import EmailAccount


class MinimalPage:
    def __init__(self, tmpdir: str):
        self.tmpdir = tmpdir

    def goto(self, url, wait_until="domcontentloaded"):
        return None

    def add_style_tag(self, **kwargs):
        return None

    def eval_on_selector(self, selector, fn):
        return None

    def wait_for_selector(self, selector, state="visible"):
        return None

    def click(self, selector):
        return None

    def fill(self, selector, value):
        return None

    def screenshot(self, path: str, full_page: bool = True):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"fake")

    def wait_for_load_state(self, state: str):
        return None


def test_generic_flow_otp_path(tmp_path):
    page = MinimalPage(str(tmp_path))
    actions = ActionHelper(page, str(tmp_path / "shots"))

    cfg = FlowConfig(
        email_input="#email",
        username_input="#username",
        password_input="#password",
        password_confirm_input="#password2",
        submit_button="#submit",
        otp_input="#otp",
        success_selector="#ok",
    )

    flow = GenericEmailCodeFlow(service_name="Demo", entry_url="https://example.com/signup", config=cfg)
    acc = EmailAccount(email="user@example.com", password="pw")

    result = flow.perform_registration(
        page=page,
        actions=actions,
        email_account=acc,
        fetch_verification=lambda service, t, prefer: "123456",
        timeout_sec=10,
        prefer_link=False,
    )

    assert result.success is True
    assert result.service == "Demo"
    assert result.mailbox_email == "user@example.com"
    assert result.service_username
