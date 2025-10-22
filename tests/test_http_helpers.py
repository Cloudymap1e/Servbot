from __future__ import annotations

"""
Small unit tests for helper functions in registrar.
"""

from servbot.automation.http.registrar import _join_url


def test_join_url_absolute_and_relative():
    base = "https://example.com/path/page"
    assert _join_url(base, "https://other.com/x") == "https://other.com/x"
    assert _join_url(base, "/signup") == "https://example.com/signup"
    # Relative path should resolve against the base path directory
    assert _join_url(base, "submit") == "https://example.com/path/submit"
    assert _join_url("https://example.com/", "submit") == "https://example.com/submit"


