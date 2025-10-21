import pytest

# Ignore manual and live tests by default (they require external services or credentials)
collect_ignore = [
    'test_fetch_detailed.py',
    'test_correct_password.py',
    'test_complete_flow.py',
    'test_integration_live.py',
    'test_credential_fixes.py',
    'test_fixes_standalone.py',
]


def pytest_collection_modifyitems(items):
    for item in items:
        if 'live' in item.keywords:
            item.add_marker(pytest.mark.skip(reason='Live integration tests disabled by default'))