"""
Tests for the registrations DB helpers.
"""
from __future__ import annotations

import json
from servbot.data.database import ensure_db, save_registration, list_registrations, get_registration, update_registration_status


def test_registrations_roundtrip(tmp_path, monkeypatch):
    ensure_db()
    rid = save_registration(
        service="DemoService",
        website_url="https://example.com/signup",
        mailbox_email="test@example.com",
        service_username="user123",
        service_password="secret",
        status="success",
        error="",
        cookies_json=json.dumps([{"k":"v"}]),
        storage_state_json=json.dumps({"cookies": []}),
        user_agent="UA",
        profile_dir=str(tmp_path),
        debug_dir=str(tmp_path / "shots"),
        artifacts_json=json.dumps([]),
    )
    assert rid > 0

    rows = list_registrations(service="DemoService", mailbox_email="test@example.com")
    assert rows and rows[0]["service"] == "DemoService"

    row = get_registration("DemoService", "test@example.com")
    assert row is not None and row["mailbox_email"] == "test@example.com"

    assert update_registration_status(rid, "failed", error="oops") is True
