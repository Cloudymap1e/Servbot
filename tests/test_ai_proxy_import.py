from __future__ import annotations

"""
Unit tests for AI-assisted proxy importer pipeline (mocked AI).
"""

from servbot.proxy.batch_import import ProxyBatchImporter


def test_batch_import_parses_mooproxy_line():
    lines = [
        "us.mooproxy.net:55688:specu1:XJrImxWe7O_country-US_session-ABC",
        "username:password@1.2.3.4:8080",
        "5.6.7.8:9000",
    ]
    eps = ProxyBatchImporter.import_from_list(lines, provider_name="test-import")
    assert len(eps) == 3
    assert eps[0].host == "us.mooproxy.net"
    assert eps[0].port == 55688
    assert eps[0].username == "specu1"
    assert "_session-ABC" in (eps[0].password or "")


