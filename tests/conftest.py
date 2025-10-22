import os
from pathlib import Path
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
    allow_live = os.environ.get('SERVBOT_RUN_LIVE') in {'1', 'true', 'yes'}
    # Also allow enabling via sentinel file in repo root or tests directory
    if not allow_live:
        allow_live = Path('RUN_LIVE').exists() or Path(__file__).parent.joinpath('RUN_LIVE').exists()
    for item in items:
        if 'live' in item.keywords and not allow_live:
            item.add_marker(pytest.mark.skip(reason='Live integration tests disabled by default (set SERVBOT_RUN_LIVE=1 to enable)'))