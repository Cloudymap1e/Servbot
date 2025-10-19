import os
import pytest

from servbot.ai.groq import is_groq_available, _client

def test_groq_healthcheck():
    if not is_groq_available():
        pytest.skip("GROQ key not configured; skipping")
    c = _client()
    assert c is not None
