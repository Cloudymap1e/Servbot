# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Quick Setup
- Python: 3.11 (matches CI)
- Install dependencies:
  - pip install -r requirements.txt

## Common Commands
- Install
  - pip install -r requirements.txt
- Lint
  - ruff check .
  - black --check .
  - To format: black .
- Test
  - Run entire suite: pytest -q
  - Mirror CI selection: pytest -q tests/test_config.py tests/test_db.py tests/test_models.py tests/test_parsers.py
- Run a single test
  - pytest -q tests/test_complete_flow.py::TestCompleteEmailFlow::test_01_provision_account_mock
- Run CLI
  - python -m servbot
  - Windows: .\run.bat
  - Linux/Mac: ./run.sh

## Architecture Overview
- Layers
  - CLI → API → Core → Clients & Parsers → Data (SQLite)
- Key modules
  - Orchestration/flows: servbot/automation/engine.py, servbot/automation/flows/generic.py
  - Clients (external services): servbot/clients/{graph.py, imap.py, flashmail.py} via servbot/clients/base.py
  - Core domain: servbot/core/{models.py, verification.py}
  - Data/persistence: servbot/data/{database.py, services.py} (SQLite)
  - Parsers (extraction): servbot/parsers/{code_parser.py, service_parser.py, email_parser.py, ai_parser.py}
- Behavior highlights
  - Protocol prefers Microsoft Graph when available; falls back to IMAP (e.g., outlook.office365.com)
  - CLI calls into API, then core; clients fetch messages; parsers extract codes/links; data layer persists

## Integration/Environment Notes
- Configuration: create data/ai.api with keys (no secrets in repo)
  - FLASHMAIL_CARD = "..."
  - CEREBRAS_KEY = "..." (optional)
- Database: SQLite at data/servbot.db (tables include accounts, messages, verifications)
- Test markers (see pytest.ini)
  - live, integration, slow, unit
  - Example: run unit-only: pytest -q -m "not live and not integration"

## References to Docs
- README.md
- docs/QUICKSTART.md
- docs/QUICKSTART_CLI.md
- docs/CLI_GUIDE.md
- docs/USAGE_EXAMPLES.md
- docs/DATABASE_AND_TESTING.md

## CI Parity
- Python version: 3.11
- Lint: ruff check .; black --check .
- Tests (unit focus): pytest -q tests/test_config.py tests/test_db.py tests/test_models.py tests/test_parsers.py
