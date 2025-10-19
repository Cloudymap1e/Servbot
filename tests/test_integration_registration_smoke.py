"""
Integration smoke test: end-to-end registration using existing mailbox.

Requires environment:
- SERVBOT_RUN_SMOKE=1
- SERVBOT_TEST_SERVICE
- SERVBOT_TEST_SIGNUP_URL
- SERVBOT_TEST_EMAIL  (must exist in DB with Graph credentials)
- SERVBOT_TEST_FLOW_CONFIG  (path to JSON selectors file)
"""
from __future__ import annotations

import json
import os
import pytest

from servbot.api import register_service_account


run_smoke = os.getenv("SERVBOT_RUN_SMOKE") == "1"
service = os.getenv("SERVBOT_TEST_SERVICE")
url = os.getenv("SERVBOT_TEST_SIGNUP_URL")
email = os.getenv("SERVBOT_TEST_EMAIL")
flow_config_path = os.getenv("SERVBOT_TEST_FLOW_CONFIG")


@pytest.mark.skipif(not run_smoke, reason="Set SERVBOT_RUN_SMOKE=1 to enable smoke test")
def test_integration_registration_smoke():
    assert service and url and email and flow_config_path, "Missing required environment variables for smoke test"

    with open(flow_config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    result = register_service_account(
        service=service,
        website_url=url,
        mailbox_email=email,
        provision_new=False,
        headless=True,
        timeout_seconds=420,
        prefer_link=True,
        flow_config=cfg,
    )

    assert result is not None
    assert result["status"] == "success"
    assert result["registration_id"] > 0
