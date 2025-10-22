from __future__ import annotations

"""
Unit tests for HTTP registrar components: FormParser, BrowserLikeSession plumbing,
and register_http orchestration. Uses a tiny local HTML sample and monkeypatches
network calls for determinism.
"""

import types
import pytest

from servbot.automation.http.forms import FormParser, ParsedForm
from servbot.automation.http.registrar import register_http


HTML_SIMPLE_FORM = """
<!doctype html>
<html>
  <body>
    <form action="/submit" method="post">
      <input type="hidden" name="csrf" value="abc123"/>
      <input type="text" name="email" value=""/>
      <input type="password" name="password" value=""/>
      <button id="submit" type="submit">Go</button>
    </form>
  </body>
</html>
"""


def test_formparser_finds_inputs_and_hidden():
    form = FormParser.find_first_form(HTML_SIMPLE_FORM)
    assert form is not None
    assert isinstance(form, ParsedForm)
    assert form.action == "/submit"
    assert form.method == "post"
    # inputs/hidden parsed
    assert "email" in form.inputs
    assert "password" in form.inputs
    assert form.hidden.get("csrf") == "abc123"


def test_register_http_success(monkeypatch):
    # Monkeypatch BrowserLikeSession used inside registrar
    import servbot.automation.http.registrar as registrar

    class FakeResp:
        def __init__(self, status, text, headers=None):
            self.status_code = status
            self.text = text
            self.headers = headers or {"Content-Type": "text/html"}
            self.url = "https://example.com/submit"

    class FakeSession:
        def __init__(self, **kwargs):
            self.proxies = kwargs.get("proxies")
            self.closed = False

        def warm_up(self, url):
            return None

        def get_text(self, url):
            return 200, HTML_SIMPLE_FORM, "text/html"

        def post_form(self, url, payload):
            assert url.endswith("/submit")
            # Expect email/password + hidden
            assert payload.get("email") == "user@example.com"
            assert payload.get("password") == "pw"
            assert payload.get("csrf") == "abc123"
            return 200, "OK", "text/html"

        def close(self):
            self.closed = True

    monkeypatch.setattr(registrar, "BrowserLikeSession", FakeSession)

    ok, status = register_http(
        service="demo",
        website_url="https://example.com/signup",
        mailbox_email="user@example.com",
        password="pw",
        proxies={"http": "http://localhost:8080"},
        timeout_seconds=5,
    )

    assert ok is True
    assert status in {"200", "redirect:302", "redirect:301"} or status.startswith("redirect:") is False


def test_register_http_error_on_no_form(monkeypatch):
    import servbot.automation.http.registrar as registrar

    class FakeSessionNoForm:
        def __init__(self, **kwargs):
            pass

        def warm_up(self, url):
            return None

        def get_text(self, url):
            return 200, "<html><body>No form here</body></html>", "text/html"

        def close(self):
            return None

    monkeypatch.setattr(registrar, "BrowserLikeSession", FakeSessionNoForm)

    ok, err = register_http(
        service="demo",
        website_url="https://example.com/signup",
        mailbox_email="user@example.com",
        password="pw",
        timeout_seconds=5,
    )

    assert ok is False
    assert "No form" in err


